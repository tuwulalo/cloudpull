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

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError as _YtDownloadError


class DownloadError(Exception):
    """Single error type for the upper layers (API, bot)."""


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


def get_info(url: str) -> dict[str, Any]:
    """Return metadata for a link without downloading the file."""
    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": False,
        "extract_flat": False,
    }
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
) -> list[str]:
    """Download a track or a whole set/playlist and convert to the chosen format.

    Returns a list of paths to the produced audio files.
    progress_hook receives raw yt-dlp dicts (status/downloaded_bytes/...).
    """
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
    }
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
