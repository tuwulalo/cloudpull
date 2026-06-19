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
import sys
import threading
import uuid
import zipfile
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

# Make the core package importable when running from the project root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core import AUDIO_FORMATS, QUALITIES, DownloadError, downloader  # noqa: E402

BASE_DIR = Path(__file__).resolve().parent.parent
DOWNLOADS_DIR = BASE_DIR / "downloads"
DOWNLOADS_DIR.mkdir(exist_ok=True)

app = FastAPI(title="scsaver API", version="1.0.0")

# In dev the Next.js frontend runs on :3000, the API on :8000.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory job state. Good enough for a single user / dev mode.
_jobs: dict[str, dict[str, Any]] = {}
_jobs_lock = threading.Lock()


class InfoRequest(BaseModel):
    url: str


class DownloadRequest(BaseModel):
    url: str
    format: str = "mp3"
    quality: str = "320"
    embed_thumbnail: bool = True


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
    except DownloadError as exc:
        _set_job(job_id, status="error", error=str(exc))
    except Exception as exc:  # noqa: BLE001 - catch all in the worker to report to the client
        _set_job(job_id, status="error", error=f"Internal error: {exc}")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


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
def api_info(req: InfoRequest) -> dict[str, Any]:
    url = req.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="Empty link")
    try:
        return downloader.get_info(url)
    except DownloadError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/download")
def api_download(req: DownloadRequest) -> dict[str, str]:
    if not req.url.strip():
        raise HTTPException(status_code=400, detail="Empty link")
    if req.format.lower() not in AUDIO_FORMATS:
        raise HTTPException(status_code=400, detail=f"Unknown format: {req.format}")

    job_id = uuid.uuid4().hex[:12]
    with _jobs_lock:
        _jobs[job_id] = {"id": job_id, "status": "queued", "percent": 0.0}

    thread = threading.Thread(target=_run_job, args=(job_id, req), daemon=True)
    thread.start()
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
