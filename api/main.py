"""scsaver FastAPI backend.

A thin HTTP layer over core.downloader. Downloading runs in a background
thread, progress is streamed via Server-Sent Events, and the finished file
(or a zip for a set) is served by a separate endpoint.

Run:
    uvicorn api.main:app --reload --port 8000
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import sys
import threading
import time
import uuid
import zipfile
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

# Make the core package importable when running from the project root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core import (  # noqa: E402
    AUDIO_FORMATS,
    QUALITIES,
    DownloadError,
    downloader,
    is_supported_url,
    max_workers,
)
from api import admin, store  # noqa: E402

BASE_DIR = Path(__file__).resolve().parent.parent
DOWNLOADS_DIR = BASE_DIR / "downloads"
DOWNLOADS_DIR.mkdir(exist_ok=True)

# Allowed browser origins. Tightened from "*" so arbitrary sites cannot drive
# the API from a browser. Override with CLOUDPULL_ALLOWED_ORIGINS (comma list).
ALLOWED_ORIGINS = [
    o.strip()
    for o in os.environ.get(
        "CLOUDPULL_ALLOWED_ORIGINS",
        "https://cloudpull.cloud,https://www.cloudpull.cloud,"
        "http://localhost:3000,http://127.0.0.1:3000",
    ).split(",")
    if o.strip()
]

DOWNLOAD_TTL = 1800  # keep a finished download this many seconds, then prune


@asynccontextmanager
async def lifespan(_app: FastAPI):
    store.init()
    cleaner = asyncio.create_task(_cleanup_loop())
    try:
        yield
    finally:
        cleaner.cancel()


app = FastAPI(title="CloudPull API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

# Admin panel (analytics + proxies), mounted at /admin.
app.include_router(admin.router)

# In-memory job state. Good enough for a single user / dev mode.
_jobs: dict[str, dict[str, Any]] = {}
_jobs_lock = threading.Lock()

# Bounded worker pool: downloads run in parallel up to the host limit; any extra
# requests wait in the queue (status stays "queued" until a worker frees up).
_executor = ThreadPoolExecutor(
    max_workers=max_workers(), thread_name_prefix="cloudpull-dl"
)

# Simple in-memory per-IP rate limit for the expensive endpoints, so a public
# no-account service cannot be trivially spammed into a denial of service.
_RATE_MAX = int(os.environ.get("CLOUDPULL_RATE_MAX", "40"))
_RATE_WINDOW = 300  # seconds
_rate_hits: dict[str, deque] = {}
_rate_lock = threading.Lock()


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _rate_ok(ip: str) -> bool:
    now = time.time()
    with _rate_lock:
        hits = _rate_hits.setdefault(ip, deque())
        while hits and now - hits[0] > _RATE_WINDOW:
            hits.popleft()
        if len(hits) >= _RATE_MAX:
            return False
        hits.append(now)
        return True


async def _cleanup_loop() -> None:
    """Delete old download folders and prune dead jobs so the disk cannot fill."""
    while True:
        await asyncio.sleep(300)
        cutoff = time.time() - DOWNLOAD_TTL
        try:
            for entry in DOWNLOADS_DIR.iterdir():
                try:
                    if entry.is_dir() and entry.stat().st_mtime < cutoff:
                        shutil.rmtree(entry, ignore_errors=True)
                except OSError:
                    pass
        except OSError:
            pass
        with _jobs_lock:
            for jid in list(_jobs):
                result = _jobs[jid].get("result")
                if result and not os.path.exists(result):
                    _jobs.pop(jid, None)


class InfoRequest(BaseModel):
    url: str


class DownloadRequest(BaseModel):
    url: str
    format: str = "mp3"
    quality: str = "320"
    embed_thumbnail: bool = True


# Dedupe cache: identical (url, format, quality) requests reuse an already
# produced file while it still exists, cutting repeat load on SoundCloud and CPU.
_cache: dict[str, dict[str, Any]] = {}
_cache_lock = threading.Lock()


def _cache_key(req: DownloadRequest) -> str:
    return f"{req.url.strip()}|{req.format.lower()}|{req.quality}"


def _set_job(job_id: str, **fields: Any) -> None:
    with _jobs_lock:
        _jobs[job_id].update(fields)


def _get_job(job_id: str) -> Optional[dict[str, Any]]:
    with _jobs_lock:
        job = _jobs.get(job_id)
        return dict(job) if job else None


def _safe_name(name: str) -> str:
    name = re.sub(r'[<>:"/\\|?*]', "_", name or "tracks").strip()
    return name or "tracks"


def _run_job(job_id: str, req: DownloadRequest) -> None:
    out_dir = DOWNLOADS_DIR / job_id

    def hook(d: dict[str, Any]) -> None:
        status = d.get("status")
        info = d.get("info_dict") or {}
        if status == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            done = d.get("downloaded_bytes") or 0
            percent = round(done / total * 100, 1) if total else 0.0
            _set_job(
                job_id,
                status="downloading",
                percent=percent,
                speed=d.get("speed"),
                eta=d.get("eta"),
                title=info.get("title"),
                track_index=info.get("playlist_index"),
                track_total=info.get("n_entries"),
                playlist_title=info.get("playlist") or None,
            )
        elif status == "finished":
            # Raw file is downloaded, ffmpeg conversion comes next.
            _set_job(job_id, status="processing", percent=100.0)

    try:
        _set_job(job_id, status="downloading")
        files = downloader.download(
            req.url,
            fmt=req.format,
            quality=req.quality,
            out_dir=str(out_dir),
            embed_thumbnail=req.embed_thumbnail,
            progress_hook=hook,
            proxy=store.pick_proxy(),
        )

        if len(files) == 1:
            result_path = files[0]
            filename = os.path.basename(result_path)
        else:
            job = _get_job(job_id) or {}
            base = _safe_name(job.get("playlist_title") or "scsaver-set")
            zip_path = out_dir / f"{base}.zip"
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for fpath in files:
                    zf.write(fpath, arcname=os.path.basename(fpath))
            result_path = str(zip_path)
            filename = os.path.basename(result_path)

        _set_job(
            job_id,
            status="done",
            percent=100.0,
            result=result_path,
            filename=filename,
            file_count=len(files),
        )
        with _cache_lock:
            _cache[_cache_key(req)] = {
                "result": result_path,
                "filename": filename,
                "file_count": len(files),
            }
        store.record("download", fmt=req.format, ok=True)
    except DownloadError as exc:
        _set_job(job_id, status="error", error=str(exc))
        store.record("download", fmt=req.format, ok=False)
    except Exception:  # noqa: BLE001 - never leak internal details to the client
        _set_job(job_id, status="error", error="Internal error during download")
        store.record("download", fmt=req.format, ok=False)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/hit")
def api_hit() -> dict[str, bool]:
    """Lightweight visit beacon called once per landing page load."""
    store.record("visit")
    return {"ok": True}


@app.get("/api/formats")
def formats() -> dict[str, Any]:
    return {
        "formats": [
            {"id": fmt, "lossless": spec["lossless"]}
            for fmt, spec in AUDIO_FORMATS.items()
        ],
        "qualities": QUALITIES,
    }


@app.post("/api/info")
def api_info(req: InfoRequest, request: Request) -> dict[str, Any]:
    url = req.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="Empty link")
    if not is_supported_url(url):
        raise HTTPException(status_code=400, detail="Only SoundCloud links are supported")
    if not _rate_ok(_client_ip(request)):
        raise HTTPException(status_code=429, detail="Too many requests, slow down")
    try:
        return downloader.get_info(url, proxy=store.pick_proxy())
    except DownloadError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail="Could not read this link") from exc


@app.post("/api/download")
def api_download(req: DownloadRequest, request: Request) -> dict[str, str]:
    url = req.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="Empty link")
    if not is_supported_url(url):
        raise HTTPException(status_code=400, detail="Only SoundCloud links are supported")
    if req.format.lower() not in AUDIO_FORMATS:
        raise HTTPException(status_code=400, detail=f"Unknown format: {req.format}")
    if req.quality not in QUALITIES and req.quality != "0":
        raise HTTPException(status_code=400, detail="Invalid quality")
    if not _rate_ok(_client_ip(request)):
        raise HTTPException(status_code=429, detail="Too many requests, slow down")

    # Serve from cache if this exact request was produced recently.
    with _cache_lock:
        hit = _cache.get(_cache_key(req))
    if hit and os.path.exists(hit["result"]):
        try:
            os.utime(os.path.dirname(hit["result"]), None)  # defer cleanup
        except OSError:
            pass
        job_id = uuid.uuid4().hex[:12]
        with _jobs_lock:
            _jobs[job_id] = {
                "id": job_id,
                "status": "done",
                "percent": 100.0,
                "result": hit["result"],
                "filename": hit["filename"],
                "file_count": hit.get("file_count", 1),
                "cached": True,
            }
        store.record("download", fmt=req.format, ok=True)
        return {"job_id": job_id}

    job_id = uuid.uuid4().hex[:12]
    with _jobs_lock:
        _jobs[job_id] = {"id": job_id, "status": "queued", "percent": 0.0}

    _executor.submit(_run_job, job_id, req)
    return {"job_id": job_id}


@app.get("/api/progress/{job_id}")
async def api_progress(job_id: str) -> StreamingResponse:
    if _get_job(job_id) is None:
        raise HTTPException(status_code=404, detail="Job not found")

    async def event_stream():
        last_payload = None
        while True:
            job = _get_job(job_id)
            if job is None:
                break
            payload = {k: v for k, v in job.items() if k != "result"}
            data = json.dumps(payload, default=str, ensure_ascii=False)
            if data != last_payload:
                yield f"data: {data}\n\n"
                last_payload = data
            if job.get("status") in ("done", "error"):
                break
            await asyncio.sleep(0.3)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/file/{job_id}")
def api_file(job_id: str) -> FileResponse:
    job = _get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.get("status") != "done" or not job.get("result"):
        raise HTTPException(status_code=409, detail="File is not ready yet")
    result = job["result"]
    if not os.path.exists(result):
        raise HTTPException(status_code=410, detail="File is no longer available")
    return FileResponse(
        result,
        filename=job.get("filename") or os.path.basename(result),
        media_type="application/octet-stream",
    )
