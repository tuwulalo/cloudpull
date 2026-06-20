"""scsaver shared core: a wrapper around yt-dlp.

Reused by both the web API (FastAPI) and the Telegram bot (Phase 2),
so nothing here is tied to a specific frontend.
"""

from .downloader import (
    AUDIO_FORMATS,
    QUALITIES,
    DownloadError,
    download,
    get_info,
    max_workers,
)

__all__ = [
    "AUDIO_FORMATS",
    "QUALITIES",
    "DownloadError",
    "download",
    "get_info",
    "max_workers",
]
