#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

import requests


ALLOWED_HOST = "cdn.pixabay.com"
ALLOWED_PATH_PREFIX = "/audio/"
UPSTREAM_HEADERS = {
    "accept-ranges",
    "cache-control",
    "content-disposition",
    "content-length",
    "content-range",
    "content-type",
    "etag",
    "expires",
    "last-modified",
}
USER_AGENT = "hbg-free-material-music-proxy/1.0"


def validate_audio_url(value: str) -> str:
    url = unquote(value.strip())
    parsed = urlparse(url)
    if parsed.scheme != "https" or (parsed.hostname or "").lower() != ALLOWED_HOST:
        raise ValueError("only HTTPS cdn.pixabay.com audio URLs are allowed")
    if not parsed.path.startswith(ALLOWED_PATH_PREFIX):
        raise ValueError("only Pixabay audio CDN paths are allowed")
    if not parsed.path.lower().endswith((".mp3", ".m4a", ".wav", ".ogg")):
        raise ValueError("unsupported audio file extension")
    return url


class MusicProxyHandler(BaseHTTPRequestHandler):
    server_version = "PixabayMusicProxy/1.0"

    def log_message(self, format: str, *args: object) -> None:
        print(f"music-proxy: {self.address_string()} {format % args}", flush=True)

    def _json(self, status: int, payload: dict[str, object]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, HEAD, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Range")
        self.send_header("Access-Control-Max-Age", "86400")
        self.end_headers()

    def do_HEAD(self) -> None:
        self._handle()

    def do_GET(self) -> None:
        self._handle()

    def _handle(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            self._json(200, {"ok": True, "service": "pixabay-music-proxy"})
            return
        if parsed.path != "/audio":
            self._json(404, {"error": "not found"})
            return

        values = parse_qs(parsed.query).get("url", [])
        if len(values) != 1:
            self._json(400, {"error": "one url query parameter is required"})
            return
        try:
            upstream_url = validate_audio_url(values[0])
        except ValueError as exc:
            self._json(400, {"error": str(exc)})
            return

        request_headers = {"User-Agent": USER_AGENT, "Accept-Encoding": "identity"}
        if self.headers.get("Range"):
            request_headers["Range"] = self.headers["Range"]
        try:
            response = requests.request(
                self.command,
                upstream_url,
                headers=request_headers,
                stream=True,
                timeout=(10, 120),
                allow_redirects=False,
            )
        except requests.RequestException:
            self._json(502, {"error": "Pixabay audio upstream request failed"})
            return

        try:
            content_type = response.headers.get("Content-Type", "")
            if response.status_code not in {200, 206} or not content_type.lower().startswith("audio/"):
                self._json(502, {"error": "Pixabay returned a non-audio response"})
                return
            max_bytes = int(
                float(os.getenv("HBG_MATERIAL_PROXY_MAX_MB", os.getenv("STOCK_MUSIC_PROXY_MAX_MB", "250")))
                * 1024
                * 1024
            )
            content_length = int(response.headers.get("Content-Length") or 0)
            if content_length and content_length > max_bytes:
                self._json(413, {"error": "audio response exceeds the configured proxy limit"})
                return

            self.send_response(response.status_code)
            for name, value in response.headers.items():
                if name.lower() in UPSTREAM_HEADERS:
                    self.send_header(name, value)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Expose-Headers", "Content-Length, Content-Range, Accept-Ranges")
            self.end_headers()
            if self.command == "HEAD":
                return

            written = 0
            for chunk in response.iter_content(chunk_size=128 * 1024):
                if not chunk:
                    continue
                written += len(chunk)
                if written > max_bytes:
                    break
                self.wfile.write(chunk)
        finally:
            response.close()


def main() -> None:
    host = os.getenv("HBG_MATERIAL_PROXY_HOST", os.getenv("STOCK_MUSIC_PROXY_HOST", "127.0.0.1"))
    port = int(os.getenv("HBG_MATERIAL_PROXY_PORT", os.getenv("STOCK_MUSIC_PROXY_PORT", "8765")))
    server = ThreadingHTTPServer((host, port), MusicProxyHandler)
    print(f"music-proxy: listening on {host}:{port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
