#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys

from dotenv import load_dotenv

from .core import (
    KEY_ENV,
    MUSIC_PROVIDERS,
    PROVIDERS,
    VIDEO_PROVIDERS,
    VIDEO_QUALITIES,
    StockImagesError,
    download_item,
    item_from_url,
    provider_status,
    search,
    search_videos,
    select_round_robin,
    validate_pixabay_audio_url,
)


def emit(value: object) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def print_results(payload: dict) -> None:
    media_type = payload.get("media_type", "image")
    print(f"{media_type.title()} results for: {payload['query']}")
    if payload.get("errors"):
        for provider, message in payload["errors"].items():
            print(f"warning: {provider}: {message}", file=sys.stderr)
    for index, item in enumerate(payload["results"], 1):
        dimensions = f"{item.get('width') or '?'}x{item.get('height') or '?'}"
        duration = f" / {item.get('duration')}s" if item.get("duration") is not None else ""
        print(f"\n[{index}] {item['platform']} / {item['id']} / {dimensions}{duration}")
        print(f"Creator: {item.get('photographer') or '-'}")
        print(f"Description: {item.get('alt') or '-'}")
        print(f"Preview: {item.get('preview_url') or '-'}")
        print(f"Download: {item['download_url']}")
        print(f"Source: {item.get('source_url') or '-'}")


def add_common_output_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--json", action="store_true")


def add_music_fetch_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("url")
    parser.add_argument("--platform", choices=(*MUSIC_PROVIDERS, "unknown"), default="pixabay")
    parser.add_argument("--id", dest="image_id", default="")
    parser.add_argument("--artist", default="")
    parser.add_argument("--source-url", default="")
    parser.add_argument("--title", default="")
    parser.add_argument("--duration", type=float)
    parser.add_argument("--thumbnail-url", default="")
    parser.add_argument("--has-youtube-content-id", action="store_true")
    parser.add_argument("--filename", default="")
    add_common_output_arguments(parser)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hbg-free-material",
        description="Search and download free stock images, videos, and browser-selected Pixabay music.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("providers", help="Show which provider API keys are configured.")

    search_parser = subparsers.add_parser("search", help="Search stock image providers.")
    search_parser.add_argument("query")
    search_parser.add_argument("--platform", choices=("all", *PROVIDERS), default="all")
    search_parser.add_argument("--per-page", type=int, default=10)
    search_parser.add_argument("--json", action="store_true")

    download_parser = subparsers.add_parser("download", help="Search and download top image results.")
    download_parser.add_argument("query")
    download_parser.add_argument("--platform", choices=("all", *PROVIDERS), default="all")
    download_parser.add_argument("--count", type=int, default=1)
    add_common_output_arguments(download_parser)

    fetch_parser = subparsers.add_parser("fetch", help="Download one selected image URL.")
    fetch_parser.add_argument("url")
    fetch_parser.add_argument("--platform", choices=(*PROVIDERS, "unknown"), default="unknown")
    fetch_parser.add_argument("--id", dest="image_id", default="")
    fetch_parser.add_argument("--photographer", default="")
    fetch_parser.add_argument("--source-url", default="")
    fetch_parser.add_argument("--alt", default="")
    fetch_parser.add_argument("--download-location", default="")
    fetch_parser.add_argument("--filename", default="")
    add_common_output_arguments(fetch_parser)

    video_parser = subparsers.add_parser("video", help="Search and download Pexels/Pixabay videos.")
    video_subparsers = video_parser.add_subparsers(dest="video_command", required=True)

    video_search = video_subparsers.add_parser("search", help="Search stock videos.")
    video_search.add_argument("query")
    video_search.add_argument("--platform", choices=("all", *VIDEO_PROVIDERS), default="all")
    video_search.add_argument("--per-page", type=int, default=10)
    video_search.add_argument("--quality", choices=VIDEO_QUALITIES, default="hd")
    video_search.add_argument("--json", action="store_true")

    video_download = video_subparsers.add_parser("download", help="Search and download top video results.")
    video_download.add_argument("query")
    video_download.add_argument("--platform", choices=("all", *VIDEO_PROVIDERS), default="all")
    video_download.add_argument("--count", type=int, default=1)
    video_download.add_argument("--quality", choices=VIDEO_QUALITIES, default="hd")
    add_common_output_arguments(video_download)

    video_fetch = video_subparsers.add_parser("fetch", help="Download one selected video URL.")
    video_fetch.add_argument("url")
    video_fetch.add_argument("--platform", choices=(*VIDEO_PROVIDERS, "unknown"), default="unknown")
    video_fetch.add_argument("--id", dest="image_id", default="")
    video_fetch.add_argument("--photographer", default="")
    video_fetch.add_argument("--source-url", default="")
    video_fetch.add_argument("--alt", default="")
    video_fetch.add_argument("--duration", type=float)
    video_fetch.add_argument("--width", type=int)
    video_fetch.add_argument("--height", type=int)
    video_fetch.add_argument("--fps", type=float)
    video_fetch.add_argument("--quality", choices=VIDEO_QUALITIES, default="")
    video_fetch.add_argument("--thumbnail-url", default="")
    video_fetch.add_argument("--filename", default="")
    add_common_output_arguments(video_fetch)

    music_parser = subparsers.add_parser(
        "music",
        help="Download or proxy browser-selected Pixabay music.",
    )
    music_subparsers = music_parser.add_subparsers(dest="music_command", required=True)

    music_fetch = music_subparsers.add_parser(
        "fetch",
        help="Download one public Pixabay CDN audio URL.",
    )
    add_music_fetch_arguments(music_fetch)

    music_proxy_url = music_subparsers.add_parser(
        "proxy-url",
        help="Create a localhost reverse-proxy URL for a public Pixabay audio URL.",
    )
    music_proxy_url.add_argument("url")
    music_proxy_url.add_argument("--json", action="store_true")

    subparsers.add_parser("proxy", help="Run the localhost Pixabay audio range proxy.")
    return parser


def checked_count(value: int) -> int:
    if value < 1 or value > 50:
        raise StockImagesError("count must be between 1 and 50")
    return value


def default_video_output_dir() -> str:
    root = os.getenv("HBG_MATERIAL_DOWNLOAD_DIR", os.getenv("STOCK_IMAGES_DOWNLOAD_DIR", "./downloads"))
    return os.path.join(root, "videos")


def default_music_output_dir() -> str:
    root = os.getenv("HBG_MATERIAL_DOWNLOAD_DIR", os.getenv("STOCK_IMAGES_DOWNLOAD_DIR", "./downloads"))
    return os.path.join(root, "music")


def main() -> int:
    load_dotenv()
    args = build_parser().parse_args()
    if args.command == "proxy":
        from .music_proxy import main as proxy_main

        proxy_main()
        return 0

    if args.command == "providers":
        status = provider_status()
        emit(
            {
                name: {
                    "configured": status[name],
                    "env": KEY_ENV[name],
                    "supports": [
                        "images",
                        *(["videos"] if name in VIDEO_PROVIDERS else []),
                        *(["music-download"] if name in MUSIC_PROVIDERS else []),
                    ],
                }
                for name in PROVIDERS
            }
        )
        return 0

    try:
        if args.command == "search":
            payload = search(args.query, args.platform, args.per_page)
            emit(payload) if args.json else print_results(payload)
            return 0

        if args.command == "download":
            count = checked_count(args.count)
            payload = search(args.query, args.platform, count)
            selected = select_round_robin(payload["results"], count)
            downloaded = [download_item(item, args.output_dir or None) for item in selected]
            result = {"query": args.query, "downloaded": downloaded, "errors": payload.get("errors", {})}
            if args.json:
                emit(result)
            else:
                for item in downloaded:
                    print(item.get("host_file") or item["file"])
            return 0

        if args.command == "fetch":
            item = item_from_url(
                args.url,
                platform=args.platform,
                image_id=args.image_id,
                photographer=args.photographer,
                source_url=args.source_url,
                alt=args.alt,
                download_location=args.download_location,
            )
            result = download_item(item, args.output_dir or None, args.filename or None)
            emit(result) if args.json else print(result.get("host_file") or result["file"])
            return 0

        if args.command == "video" and args.video_command == "search":
            payload = search_videos(args.query, args.platform, args.per_page, args.quality)
            emit(payload) if args.json else print_results(payload)
            return 0

        if args.command == "video" and args.video_command == "download":
            count = checked_count(args.count)
            payload = search_videos(args.query, args.platform, count, args.quality)
            selected = select_round_robin(payload["results"], count)
            output_dir = args.output_dir or default_video_output_dir()
            downloaded = [download_item(item, output_dir) for item in selected]
            result = {
                "query": args.query,
                "quality": args.quality,
                "downloaded": downloaded,
                "errors": payload.get("errors", {}),
            }
            if args.json:
                emit(result)
            else:
                for item in downloaded:
                    print(item.get("host_file") or item["file"])
            return 0

        if args.command == "video" and args.video_command == "fetch":
            item = item_from_url(
                args.url,
                platform=args.platform,
                image_id=args.image_id,
                photographer=args.photographer,
                source_url=args.source_url,
                alt=args.alt,
                media_type="video",
                duration=args.duration,
                thumbnail_url=args.thumbnail_url,
                width=args.width,
                height=args.height,
                fps=args.fps,
                quality=args.quality,
            )
            output_dir = args.output_dir or default_video_output_dir()
            result = download_item(item, output_dir, args.filename or None)
            emit(result) if args.json else print(result.get("host_file") or result["file"])
            return 0

        if args.command == "music" and args.music_command == "fetch":
            item = item_from_url(
                args.url,
                platform=args.platform,
                image_id=args.image_id,
                photographer=args.artist,
                source_url=args.source_url,
                alt=args.title,
                media_type="audio",
                duration=args.duration,
                thumbnail_url=args.thumbnail_url,
                has_youtube_content_id=args.has_youtube_content_id,
            )
            output_dir = args.output_dir or default_music_output_dir()
            result = download_item(item, output_dir, args.filename or None)
            emit(result) if args.json else print(result.get("host_file") or result["file"])
            return 0

        if args.command == "music" and args.music_command == "proxy-url":
            from urllib.parse import quote

            validate_pixabay_audio_url(args.url)
            base_url = os.getenv(
                "HBG_MATERIAL_PROXY_PUBLIC_BASE",
                os.getenv("STOCK_MUSIC_PROXY_PUBLIC_BASE", "http://127.0.0.1:8765"),
            ).rstrip("/")
            proxy_url = f"{base_url}/audio?url={quote(args.url, safe='')}"
            payload = {"source_url": args.url, "proxy_url": proxy_url}
            emit(payload) if args.json else print(proxy_url)
            return 0
    except StockImagesError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
