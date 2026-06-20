"""yt-dlp wrapper: fetch metadata and download audio from SoundCloud.

Public module API:
    get_info(url)  -> dict with metadata (track or playlist/set)
    download(...)  -> list of paths to the produced audio files

The logic deliberately knows nothing about HTTP/Telegram, so that both
FastAPI and the bot can use it the same way.
"""

from __future__ import annotations

import os
from typing import Any, Callable, Optional
from urllib.parse import urlparse

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError as _YtDownloadError


class DownloadError(Exception):
    """Single error type for the upper layers (API, bot)."""


def is_supported_url(url: str) -> bool:
    """Only accept SoundCloud links.

    This is the SSRF guard: without it, an arbitrary URL handed to yt-dlp could
    make the server fetch internal addresses (cloud metadata, localhost, etc.).
    """
    try:
        parsed = urlparse((url or "").strip())
    except ValueError:
        return False
    if parsed.scheme not in ("http", "https"):
        return False
    host = (parsed.hostname or "").lower()
    return host == "soundcloud.com" or host.endswith(".soundcloud.com")


# Supported formats. lossless -> quality (bitrate) is ignored.
# thumb -> whether cover art can be embedded into this container.
AUDIO_FORMATS: dict[str, dict[str, Any]] = {
    "mp3":  {"codec": "mp3",  "lossless": False, "thumb": True},
    "m4a":  {"codec": "m4a",  "lossless": False, "thumb": True},
    "opus": {"codec": "opus", "lossless": False, "thumb": True},
    "flac": {"codec": "flac", "lossless": True,  "thumb": True},
    "wav":  {"codec": "wav",  "lossless": True,  "thumb": False},
}

# Bitrates for lossy formats (kbps). "0" = best available (VBR).
QUALITIES: list[str] = ["320", "256", "192", "128"]

# Speed + resilience. Concurrent fragment downloads make HLS streams much faster;
# retries (with yt-dlp's own backoff) absorb transient SoundCloud 429s without an
# artificial per-request delay. Use proxies (admin panel) if you hit limits hard.
_RESILIENCE: dict[str, Any] = {
    "retries": 5,
    "extractor_retries": 3,
    "fragment_retries": 5,
    "concurrent_fragment_downloads": 5,
}


def max_workers() -> int:
    """How many downloads to run in parallel, tuned to the host.

    Each job is mostly network wait plus a short ffmpeg transcode, so we allow
    roughly two per core. Override with the CLOUDPULL_MAX_CONCURRENCY env var
    (a positive integer) to push the VPS harder or hold it back.
    """
    env = os.environ.get("CLOUDPULL_MAX_CONCURRENCY", "").strip()
    if env.isdigit() and int(env) > 0:
        return int(env)
    cpu = os.cpu_count() or 2
    return min(12, max(2, cpu * 2))


def _best_thumb(info: dict[str, Any] | None) -> Optional[str]:
    """Pick the highest-resolution cover image."""
    if not info:
        return None
    thumbs = info.get("thumbnails")
    if thumbs:
        def _area(t: dict[str, Any]) -> int:
            return (t.get("width") or 0) * (t.get("height") or 0)
        best = max(thumbs, key=_area)
        if best.get("url"):
            return best["url"]
    return info.get("thumbnail")


def _track_brief(info: dict[str, Any]) -> dict[str, Any]:
    """Short track card for the frontend."""
    return {
        "id": info.get("id"),
        "title": info.get("title"),
        "uploader": info.get("uploader") or info.get("channel") or info.get("artist"),
        "duration": info.get("duration"),
        "thumbnail": _best_thumb(info),
        "webpage_url": info.get("webpage_url") or info.get("url"),
    }


def _normalize_info(info: dict[str, Any]) -> dict[str, Any]:
    """Normalize the yt-dlp response into one shape: track or playlist."""
    is_playlist = info.get("_type") == "playlist" or info.get("entries") is not None
    if is_playlist:
        entries = [e for e in (info.get("entries") or []) if e]
        return {
            "type": "playlist",
            "title": info.get("title"),
            "uploader": info.get("uploader") or info.get("channel"),
            "webpage_url": info.get("webpage_url"),
            "thumbnail": _best_thumb(info)
            or (_best_thumb(entries[0]) if entries else None),
            "track_count": len(entries),
            "tracks": [_track_brief(e) for e in entries],
        }
    return {"type": "track", **_track_brief(info)}


def get_info(url: str, proxy: Optional[str] = None) -> dict[str, Any]:
    """Return metadata for a link without downloading the file."""
    if not is_supported_url(url):
        raise DownloadError("Only SoundCloud links are supported")
    opts: dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": False,
        "extract_flat": False,
        **_RESILIENCE,
    }
    if proxy:
        opts["proxy"] = proxy
    try:
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except _YtDownloadError as exc:
        raise DownloadError(str(exc)) from exc
    if info is None:
        raise DownloadError("Could not fetch data for this link")
    return _normalize_info(info)


def _build_postprocessors(
    fmt: str, quality: str, embed_thumbnail: bool
) -> list[dict[str, Any]]:
    spec = AUDIO_FORMATS[fmt]
    pps: list[dict[str, Any]] = [
        {
            "key": "FFmpegExtractAudio",
            "preferredcodec": spec["codec"],
            "preferredquality": "0" if spec["lossless"] else str(quality),
        },
        {"key": "FFmpegMetadata"},
    ]
    if embed_thumbnail and spec["thumb"]:
        pps.append({"key": "EmbedThumbnail"})
    return pps


def _collect_files(info: dict[str, Any]) -> list[str]:
    """Extract paths to the final audio files after postprocessing."""
    entries = info.get("entries")
    items = entries if entries is not None else [info]
    files: list[str] = []
    for item in items:
        if not item:
            continue
        for rd in item.get("requested_downloads") or []:
            path = rd.get("filepath")
            if path and os.path.exists(path):
                files.append(path)
    return files


def download(
    url: str,
    fmt: str = "mp3",
    quality: str = "320",
    out_dir: str = "downloads",
    embed_thumbnail: bool = True,
    progress_hook: Optional[Callable[[dict[str, Any]], None]] = None,
    proxy: Optional[str] = None,
) -> list[str]:
    """Download a track or a whole set/playlist and convert to the chosen format.

    Returns a list of paths to the produced audio files.
    progress_hook receives raw yt-dlp dicts (status/downloaded_bytes/...).
    """
    if not is_supported_url(url):
        raise DownloadError("Only SoundCloud links are supported")
    fmt = fmt.lower()
    if fmt not in AUDIO_FORMATS:
        raise DownloadError(f"Unsupported format: {fmt}")

    os.makedirs(out_dir, exist_ok=True)

    opts: dict[str, Any] = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(out_dir, "%(title)s.%(ext)s"),
        "windowsfilenames": True,
        "writethumbnail": embed_thumbnail,
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": False,
        "noprogress": True,
        "postprocessors": _build_postprocessors(fmt, quality, embed_thumbnail),
        **_RESILIENCE,
    }
    if proxy:
        opts["proxy"] = proxy
    if progress_hook:
        opts["progress_hooks"] = [progress_hook]

    try:
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
    except _YtDownloadError as exc:
        raise DownloadError(str(exc)) from exc

    if info is None:
        raise DownloadError("Download returned no data")

    files = _collect_files(info)
    if not files:
        raise DownloadError("Could not produce the final files")
    return files
