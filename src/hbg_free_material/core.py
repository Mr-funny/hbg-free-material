from __future__ import annotations

import ipaddress
import json
import mimetypes
import os
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests


PROVIDERS = ("pexels", "unsplash", "pixabay")
VIDEO_PROVIDERS = ("pexels", "pixabay")
MUSIC_PROVIDERS = ("pixabay",)
VIDEO_QUALITIES = ("best", "hd", "sd", "small")
KEY_ENV = {
    "pexels": "PEXELS_API_KEY",
    "unsplash": "UNSPLASH_API_KEY",
    "pixabay": "PIXABAY_API_KEY",
}
LICENSE_URLS = {
    "pexels": "https://www.pexels.com/license/",
    "unsplash": "https://unsplash.com/license",
    "pixabay": "https://pixabay.com/service/license-summary/",
}
USER_AGENT = "hbg-free-material/1.0 (+https://github.com/Mr-funny/hbg-free-material)"


class StockImagesError(RuntimeError):
    pass


def _env(name: str, legacy_name: str, default: str = "") -> str:
    """Read the public HBG setting while preserving local legacy compatibility."""
    return os.getenv(name, os.getenv(legacy_name, default))


def _timeouts() -> tuple[float, float]:
    return (
        float(_env("HBG_MATERIAL_CONNECT_TIMEOUT", "STOCK_IMAGES_CONNECT_TIMEOUT", "10")),
        float(_env("HBG_MATERIAL_READ_TIMEOUT", "STOCK_IMAGES_READ_TIMEOUT", "120")),
    )


def _key(provider: str) -> str:
    value = os.getenv(KEY_ENV[provider], "").strip()
    if not value or value.startswith("your_"):
        raise StockImagesError(f"{KEY_ENV[provider]} is not configured")
    return value


def provider_status() -> dict[str, bool]:
    status: dict[str, bool] = {}
    for provider, env_name in KEY_ENV.items():
        value = os.getenv(env_name, "").strip()
        status[provider] = bool(value and not value.startswith("your_"))
    return status


def _request_json(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    request_headers = {"User-Agent": USER_AGENT, **(headers or {})}
    try:
        response = requests.get(
            url,
            headers=request_headers,
            params=params,
            timeout=_timeouts(),
        )
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError) as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        suffix = f" (HTTP {status})" if status else ""
        raise StockImagesError(f"Request to {urlparse(url).netloc} failed{suffix}") from exc


def _search_pexels(query: str, per_page: int) -> list[dict[str, Any]]:
    data = _request_json(
        "https://api.pexels.com/v1/search",
        headers={"Authorization": _key("pexels")},
        params={"query": query, "per_page": min(per_page, 50)},
    )
    return [
        {
            "id": str(photo["id"]),
            "media_type": "image",
            "platform": "pexels",
            "download_url": photo["src"]["original"],
            "preview_url": photo["src"]["medium"],
            "source_url": photo.get("url", f"https://www.pexels.com/photo/{photo['id']}/"),
            "photographer": photo.get("photographer", ""),
            "photographer_url": photo.get("photographer_url", ""),
            "alt": photo.get("alt", ""),
            "width": photo.get("width"),
            "height": photo.get("height"),
            "license_url": LICENSE_URLS["pexels"],
        }
        for photo in data.get("photos", [])
    ]


def _search_unsplash(query: str, per_page: int) -> list[dict[str, Any]]:
    data = _request_json(
        "https://api.unsplash.com/search/photos",
        headers={"Authorization": f"Client-ID {_key('unsplash')}"},
        params={"query": query, "per_page": min(per_page, 30)},
    )
    return [
        {
            "id": str(photo["id"]),
            "media_type": "image",
            "platform": "unsplash",
            "download_url": photo["urls"]["full"],
            "preview_url": photo["urls"]["regular"],
            "source_url": photo.get("links", {}).get("html", f"https://unsplash.com/photos/{photo['id']}"),
            "download_location": photo.get("links", {}).get("download_location", ""),
            "photographer": photo.get("user", {}).get("name", ""),
            "photographer_url": photo.get("user", {}).get("links", {}).get("html", ""),
            "alt": photo.get("alt_description") or photo.get("description") or "",
            "width": photo.get("width"),
            "height": photo.get("height"),
            "license_url": LICENSE_URLS["unsplash"],
        }
        for photo in data.get("results", [])
    ]


def _search_pixabay(query: str, per_page: int) -> list[dict[str, Any]]:
    data = _request_json(
        "https://pixabay.com/api/",
        params={
            "key": _key("pixabay"),
            "q": query,
            "per_page": max(3, min(per_page, 50)),
            "image_type": "photo",
            "safesearch": "true",
        },
    )
    return [
        {
            "id": str(hit["id"]),
            "media_type": "image",
            "platform": "pixabay",
            "download_url": hit["largeImageURL"],
            "preview_url": hit["webformatURL"],
            "source_url": hit.get("pageURL", ""),
            "photographer": hit.get("user", ""),
            "photographer_url": f"https://pixabay.com/users/{hit.get('user', '')}-{hit.get('user_id', '')}/",
            "alt": hit.get("tags", ""),
            "width": hit.get("imageWidth"),
            "height": hit.get("imageHeight"),
            "license_url": LICENSE_URLS["pixabay"],
        }
        for hit in data.get("hits", [])[:per_page]
    ]


def _variant_area(variant: dict[str, Any]) -> int:
    return int(variant.get("width") or 0) * int(variant.get("height") or 0)


def _pexels_video_variants(video: dict[str, Any]) -> list[dict[str, Any]]:
    variants: list[dict[str, Any]] = []
    for file in video.get("video_files", []):
        url = file.get("link")
        if not url or file.get("file_type") not in {None, "video/mp4"}:
            continue
        variants.append(
            {
                "quality": file.get("quality") or "unknown",
                "download_url": url,
                "width": file.get("width"),
                "height": file.get("height"),
                "fps": file.get("fps"),
                "file_type": file.get("file_type") or "video/mp4",
                "size": file.get("size"),
            }
        )
    return variants


def _pick_pexels_variant(variants: list[dict[str, Any]], quality: str) -> dict[str, Any]:
    if not variants:
        raise StockImagesError("Pexels video has no downloadable MP4 variant")
    ranked = sorted(variants, key=_variant_area)
    if quality == "best":
        return ranked[-1]
    if quality == "small":
        return ranked[0]
    matching = [variant for variant in ranked if variant.get("quality") == quality]
    if quality == "hd" and matching:
        bounded = [variant for variant in matching if int(variant.get("width") or 0) <= 1920]
        return (bounded or matching)[-1]
    if matching:
        return matching[-1]
    return ranked[-1] if quality == "hd" else ranked[0]


def _search_pexels_videos(query: str, per_page: int, quality: str) -> list[dict[str, Any]]:
    data = _request_json(
        "https://api.pexels.com/videos/search",
        headers={"Authorization": _key("pexels")},
        params={"query": query, "per_page": min(per_page, 50)},
    )
    results: list[dict[str, Any]] = []
    for video in data.get("videos", []):
        variants = _pexels_video_variants(video)
        if not variants:
            continue
        selected = _pick_pexels_variant(variants, quality)
        user = video.get("user", {})
        results.append(
            {
                "id": str(video["id"]),
                "media_type": "video",
                "platform": "pexels",
                "download_url": selected["download_url"],
                "preview_url": video.get("image", ""),
                "thumbnail_url": video.get("image", ""),
                "source_url": video.get("url", f"https://www.pexels.com/video/{video['id']}/"),
                "photographer": user.get("name", ""),
                "photographer_url": user.get("url", ""),
                "alt": query,
                "width": selected.get("width") or video.get("width"),
                "height": selected.get("height") or video.get("height"),
                "duration": video.get("duration"),
                "fps": selected.get("fps"),
                "quality": quality,
                "selected_variant": selected,
                "variants": variants,
                "license_url": LICENSE_URLS["pexels"],
            }
        )
    return results


def _pixabay_video_variants(hit: dict[str, Any]) -> list[dict[str, Any]]:
    variants: list[dict[str, Any]] = []
    for name in ("large", "medium", "small", "tiny"):
        video = hit.get("videos", {}).get(name) or {}
        if not video.get("url"):
            continue
        variants.append(
            {
                "quality": name,
                "download_url": video["url"],
                "width": video.get("width"),
                "height": video.get("height"),
                "size": video.get("size"),
                "thumbnail_url": video.get("thumbnail", ""),
                "file_type": "video/mp4",
            }
        )
    return variants


def _pick_pixabay_variant(variants: list[dict[str, Any]], quality: str) -> dict[str, Any]:
    if not variants:
        raise StockImagesError("Pixabay video has no downloadable MP4 variant")
    ranked = sorted(variants, key=_variant_area)
    if quality == "best":
        return ranked[-1]
    if quality == "hd":
        bounded = [variant for variant in ranked if int(variant.get("width") or 0) <= 1920]
        return (bounded or ranked[:1])[-1]
    return ranked[0]


def _search_pixabay_videos(query: str, per_page: int, quality: str) -> list[dict[str, Any]]:
    data = _request_json(
        "https://pixabay.com/api/videos/",
        params={
            "key": _key("pixabay"),
            "q": query,
            "per_page": max(3, min(per_page, 50)),
            "safesearch": "true",
        },
    )
    results: list[dict[str, Any]] = []
    for hit in data.get("hits", [])[:per_page]:
        variants = _pixabay_video_variants(hit)
        if not variants:
            continue
        selected = _pick_pixabay_variant(variants, quality)
        thumbnail = selected.get("thumbnail_url") or next(
            (variant.get("thumbnail_url") for variant in variants if variant.get("thumbnail_url")),
            "",
        )
        results.append(
            {
                "id": str(hit["id"]),
                "media_type": "video",
                "platform": "pixabay",
                "download_url": selected["download_url"],
                "preview_url": thumbnail,
                "thumbnail_url": thumbnail,
                "source_url": hit.get("pageURL", ""),
                "photographer": hit.get("user", ""),
                "photographer_url": f"https://pixabay.com/users/{hit.get('user', '')}-{hit.get('user_id', '')}/",
                "alt": hit.get("tags", ""),
                "width": selected.get("width"),
                "height": selected.get("height"),
                "duration": hit.get("duration"),
                "fps": None,
                "quality": quality,
                "selected_variant": selected,
                "variants": variants,
                "license_url": LICENSE_URLS["pixabay"],
            }
        )
    return results


SEARCHERS = {
    "pexels": _search_pexels,
    "unsplash": _search_unsplash,
    "pixabay": _search_pixabay,
}

VIDEO_SEARCHERS = {
    "pexels": _search_pexels_videos,
    "pixabay": _search_pixabay_videos,
}


def search(query: str, platform: str = "all", per_page: int = 10) -> dict[str, Any]:
    query = query.strip()
    if not query:
        raise StockImagesError("query cannot be empty")
    if platform not in (*PROVIDERS, "all"):
        raise StockImagesError(f"unsupported platform: {platform}")
    if not 1 <= per_page <= 50:
        raise StockImagesError("per_page must be between 1 and 50")

    selected = PROVIDERS if platform == "all" else (platform,)
    configured = provider_status()
    if not any(configured[name] for name in selected):
        required = ", ".join(KEY_ENV[name] for name in selected)
        raise StockImagesError(f"no configured provider key; set one of: {required}")

    results: list[dict[str, Any]] = []
    errors: dict[str, str] = {}
    counts: dict[str, int] = {}
    for name in selected:
        if not configured[name]:
            counts[name] = 0
            errors[name] = f"{KEY_ENV[name]} is not configured"
            continue
        try:
            provider_results = SEARCHERS[name](query, per_page)
            results.extend(provider_results)
            counts[name] = len(provider_results)
        except StockImagesError as exc:
            counts[name] = 0
            errors[name] = str(exc)

    if not results and errors:
        detail = "; ".join(f"{name}: {message}" for name, message in errors.items())
        raise StockImagesError(detail)
    return {
        "query": query,
        "platform": platform,
        "per_page": per_page,
        "counts": counts,
        "errors": errors,
        "results": results,
    }


def search_videos(
    query: str,
    platform: str = "all",
    per_page: int = 10,
    quality: str = "hd",
) -> dict[str, Any]:
    query = query.strip()
    if not query:
        raise StockImagesError("query cannot be empty")
    if platform not in (*VIDEO_PROVIDERS, "all"):
        raise StockImagesError(f"unsupported video platform: {platform}")
    if not 1 <= per_page <= 50:
        raise StockImagesError("per_page must be between 1 and 50")
    if quality not in VIDEO_QUALITIES:
        raise StockImagesError(f"quality must be one of: {', '.join(VIDEO_QUALITIES)}")

    selected = VIDEO_PROVIDERS if platform == "all" else (platform,)
    configured = provider_status()
    if not any(configured[name] for name in selected):
        required = ", ".join(KEY_ENV[name] for name in selected)
        raise StockImagesError(f"no configured video provider key; set one of: {required}")

    results: list[dict[str, Any]] = []
    errors: dict[str, str] = {}
    counts: dict[str, int] = {}
    for name in selected:
        if not configured[name]:
            counts[name] = 0
            errors[name] = f"{KEY_ENV[name]} is not configured"
            continue
        try:
            provider_results = VIDEO_SEARCHERS[name](query, per_page, quality)
            results.extend(provider_results)
            counts[name] = len(provider_results)
        except StockImagesError as exc:
            counts[name] = 0
            errors[name] = str(exc)

    if not results and errors:
        detail = "; ".join(f"{name}: {message}" for name, message in errors.items())
        raise StockImagesError(detail)
    return {
        "query": query,
        "media_type": "video",
        "platform": platform,
        "quality": quality,
        "per_page": per_page,
        "counts": counts,
        "errors": errors,
        "results": results,
    }


def select_round_robin(results: list[dict[str, Any]], count: int) -> list[dict[str, Any]]:
    if count < 1:
        raise StockImagesError("count must be at least 1")
    buckets = {name: [item for item in results if item["platform"] == name] for name in PROVIDERS}
    selected: list[dict[str, Any]] = []
    while len(selected) < count:
        added = False
        for name in PROVIDERS:
            if buckets[name] and len(selected) < count:
                selected.append(buckets[name].pop(0))
                added = True
        if not added:
            break
    return selected


def _validate_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise StockImagesError("download URL must be an HTTP(S) URL")
    if parsed.hostname.lower() == "localhost":
        raise StockImagesError("local download URLs are not allowed")
    try:
        address = ipaddress.ip_address(parsed.hostname)
    except ValueError:
        return
    if not address.is_global:
        raise StockImagesError("private or local download URLs are not allowed")


def validate_pixabay_audio_url(url: str) -> None:
    _validate_url(url)
    parsed = urlparse(url)
    if parsed.scheme != "https" or (parsed.hostname or "").lower() != "cdn.pixabay.com":
        raise StockImagesError("Pixabay music must use an HTTPS cdn.pixabay.com URL")
    if not parsed.path.startswith("/audio/"):
        raise StockImagesError("Pixabay music URL must use the /audio/ CDN path")
    if not parsed.path.lower().endswith((".mp3", ".m4a", ".wav", ".ogg")):
        raise StockImagesError("unsupported Pixabay audio file extension")


def _slug(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()).strip("-._")
    return value[:80] or "stock-image"


def _extension(content_type: str, url: str, media_kind: str) -> str:
    content_media_type = content_type.split(";", 1)[0].strip().lower()
    known = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/gif": ".gif",
        "video/mp4": ".mp4",
        "video/webm": ".webm",
        "video/quicktime": ".mov",
        "audio/mpeg": ".mp3",
        "audio/mp4": ".m4a",
        "audio/x-m4a": ".m4a",
        "audio/wav": ".wav",
        "audio/x-wav": ".wav",
        "audio/ogg": ".ogg",
    }
    if content_media_type in known:
        return known[content_media_type]
    guessed = mimetypes.guess_extension(content_media_type) or Path(urlparse(url).path).suffix
    if guessed and len(guessed) <= 6:
        return guessed
    defaults = {"image": ".jpg", "video": ".mp4", "audio": ".mp3"}
    return defaults.get(media_kind, ".bin")


def _host_path(path: Path) -> str | None:
    host_root = _env("HBG_MATERIAL_HOST_OUTPUT_DIR", "STOCK_IMAGES_HOST_OUTPUT_DIR").strip()
    if not host_root:
        return None
    container_root = Path(_env("HBG_MATERIAL_DOWNLOAD_DIR", "STOCK_IMAGES_DOWNLOAD_DIR", "./downloads"))
    try:
        relative = path.resolve().relative_to(container_root.resolve())
    except ValueError:
        return None
    return str(Path(host_root).expanduser() / relative)


def download_item(
    item: dict[str, Any],
    output_dir: str | Path | None = None,
    filename: str | None = None,
) -> dict[str, Any]:
    url = str(item.get("download_url") or "")
    _validate_url(url)
    provider = str(item.get("platform") or "unknown")
    media_kind = str(item.get("media_type") or "image")
    if media_kind not in {"image", "video", "audio"}:
        raise StockImagesError(f"unsupported media type: {media_kind}")
    if media_kind == "audio" and provider == "pixabay":
        validate_pixabay_audio_url(url)
    if media_kind == "image" and provider == "unsplash" and item.get("download_location"):
        _request_json(
            str(item["download_location"]),
            headers={"Authorization": f"Client-ID {_key('unsplash')}"},
        )

    target_dir = Path(output_dir or _env("HBG_MATERIAL_DOWNLOAD_DIR", "STOCK_IMAGES_DOWNLOAD_DIR", "./downloads"))
    target_dir.mkdir(parents=True, exist_ok=True)
    limit_env = {
        "image": ("HBG_MATERIAL_MAX_IMAGE_MB", "STOCK_IMAGES_MAX_DOWNLOAD_MB"),
        "video": ("HBG_MATERIAL_MAX_VIDEO_MB", "STOCK_VIDEOS_MAX_DOWNLOAD_MB"),
        "audio": ("HBG_MATERIAL_MAX_AUDIO_MB", "STOCK_AUDIO_MAX_DOWNLOAD_MB"),
    }[media_kind]
    default_limit = {"image": "100", "video": "500", "audio": "250"}[media_kind]
    max_bytes = int(float(_env(limit_env[0], limit_env[1], default_limit)) * 1024 * 1024)
    try:
        response = requests.get(
            url,
            headers={"User-Agent": USER_AGENT},
            stream=True,
            timeout=_timeouts(),
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        suffix = f" (HTTP {status})" if status else ""
        raise StockImagesError(f"{media_kind} download failed from {urlparse(url).netloc}{suffix}") from exc

    content_type = response.headers.get("Content-Type", "")
    expected_prefix = f"{media_kind}/"
    if content_type and not content_type.lower().startswith(expected_prefix):
        response.close()
        raise StockImagesError(f"download returned non-{media_kind} content: {content_type}")
    extension = _extension(content_type, url, media_kind)
    base = _slug(filename or f"{provider}-{item.get('id') or media_kind}")
    allowed_suffixes = {
        "image": {".jpg", ".jpeg", ".png", ".webp", ".gif"},
        "video": {".mp4", ".webm", ".mov"},
        "audio": {".mp3", ".m4a", ".wav", ".ogg"},
    }
    if Path(base).suffix.lower() in allowed_suffixes[media_kind]:
        final_name = base
    else:
        final_name = f"{base}{extension}"
    target = target_dir / final_name
    partial = target.with_suffix(target.suffix + ".part")
    written = 0
    try:
        with partial.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 128):
                if not chunk:
                    continue
                written += len(chunk)
                if written > max_bytes:
                    raise StockImagesError("download exceeded configured size limit")
                handle.write(chunk)
        partial.replace(target)
    finally:
        response.close()
        if partial.exists():
            partial.unlink()

    record = {
        **item,
        "file": str(target),
        "host_file": _host_path(target),
        "bytes": written,
    }
    manifest_path = target_dir / "manifest.json"
    manifest: list[dict[str, Any]] = []
    if manifest_path.exists():
        try:
            loaded = json.loads(manifest_path.read_text(encoding="utf-8"))
            if isinstance(loaded, list):
                manifest = loaded
        except (OSError, ValueError):
            pass
    manifest.append(record)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    record["manifest"] = str(manifest_path)
    record["host_manifest"] = _host_path(manifest_path)
    return record


def item_from_url(
    url: str,
    *,
    platform: str = "unknown",
    image_id: str = "",
    photographer: str = "",
    source_url: str = "",
    alt: str = "",
    download_location: str = "",
    media_type: str = "image",
    duration: float | None = None,
    thumbnail_url: str = "",
    width: int | None = None,
    height: int | None = None,
    fps: float | None = None,
    quality: str = "",
    has_youtube_content_id: bool = False,
) -> dict[str, Any]:
    _validate_url(url)
    return {
        "id": image_id,
        "media_type": media_type,
        "platform": platform,
        "download_url": url,
        "preview_url": thumbnail_url or url,
        "thumbnail_url": thumbnail_url,
        "source_url": source_url,
        "download_location": download_location,
        "photographer": photographer,
        "photographer_url": "",
        "alt": alt,
        "width": width,
        "height": height,
        "duration": duration,
        "fps": fps,
        "quality": quality,
        "has_youtube_content_id": has_youtube_content_id,
        "license_url": LICENSE_URLS.get(platform, ""),
    }
