# CloudPull 

Download music from SoundCloud in popular formats (mp3, m4a, flac, wav, opus).
Supports single tracks and whole sets/playlists, embeds cover art and tags.

The front end is a single **CloudPull** landing page where the paste bar is the
real, working downloader. The architecture is built so the web app and the
future Telegram bot share one core:

```
scsaver/
├─ core/          shared logic over yt-dlp (get_info, download)
├─ api/           FastAPI backend (REST + progress via SSE)
├─ web/           CloudPull landing (Next.js + Tailwind); the hero is the live downloader
├─ bot/           Phase 2: Telegram bot (reuses core/)
└─ downloads/     finished files (created automatically)
```

## Requirements

- Python 3.12+
- Node.js 20.9+
- ffmpeg on PATH (needed to convert to mp3 etc.)
- 
## API endpoints

| Method | Path                    | Purpose                             |
| ------ | ----------------------- | ----------------------------------- |
| GET    | `/api/health`           | liveness check                      |
| GET    | `/api/formats`          | available formats and bitrates      |
| POST   | `/api/info`             | metadata for a link                 |
| POST   | `/api/download`         | start a job, returns `job_id`       |
| GET    | `/api/progress/{id}`    | progress stream (SSE)               |
| GET    | `/api/file/{id}`        | download the finished file          |


## Disclaimer

A tool for personal use. Respect copyright and the SoundCloud terms of use.
