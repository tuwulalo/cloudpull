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

## Running (Phase 1: web)

You need two processes: the backend on :8000 and the frontend on :3000.

### 1. Backend (FastAPI)

```powershell
# from the project root
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn api.main:app --port 8000
```

### 2. Frontend (Next.js)

```powershell
cd web
npm install      # first time only
npm run dev
```

Open in the browser: http://localhost:3000

Environment variables (`web/.env.local`):

- `NEXT_PUBLIC_API_URL` , address of the Python backend (default `http://127.0.0.1:8000`).
- `NEXT_PUBLIC_SITE_URL` , public site URL. Set this to your real domain before
  deploying so canonical URLs, the sitemap, robots.txt and Open Graph images are absolute.
- `NEXT_PUBLIC_REPO_URL` , optional source repo URL that wires up the GitHub / View source links.

## How it works

1. Paste a track or set link and press "Find": the backend uses `core.get_info`
   to fetch metadata (title, artist, cover, track list).
2. Pick a format on the card, press "Download".
3. The backend downloads and converts in the background, progress is streamed
   to the landing over SSE.
4. A single track is served as a file, a set is packed into a zip, and the
   browser saves it automatically.

## API endpoints

| Method | Path                    | Purpose                             |
| ------ | ----------------------- | ----------------------------------- |
| GET    | `/api/health`           | liveness check                      |
| GET    | `/api/formats`          | available formats and bitrates      |
| POST   | `/api/info`             | metadata for a link                 |
| POST   | `/api/download`         | start a job, returns `job_id`       |
| GET    | `/api/progress/{id}`    | progress stream (SSE)               |
| GET    | `/api/file/{id}`        | download the finished file          |

## SEO / GEO / AEO

The landing ships with search, AI-search and answer-engine optimization built in:

- Rich metadata (title, description, keywords, canonical, Open Graph, Twitter card)
  in `web/app/layout.tsx`, driven by `web/lib/site.ts`.
- `web/app/robots.ts` , `robots.txt` that also explicitly allows AI crawlers
  (GPTBot, PerplexityBot, ClaudeBot, Google-Extended, ...).
- `web/app/sitemap.ts` , `sitemap.xml`.
- `web/app/manifest.ts` , web app manifest (installable).
- `web/app/opengraph-image.tsx` , generated 1200x630 social share image.
- JSON-LD structured data in `web/lib/jsonld.ts` (Organization, WebSite,
  WebApplication, HowTo and FAQPage), plus a visible FAQ section for AEO.

Three SEO skills are installed under `.claude/skills/` (claude-seo, agentic-seo,
seo-geo-aeo). After deploying, run the `seo-geo-aeo` skill against the live URL
for a full SEO/GEO/AEO audit report.

## Phase 2: Telegram bot

The download logic already lives in `core/` and does not depend on the web.
The bot only needs the Telegram layer. See `bot/README.md` for details.

## Disclaimer

A tool for personal use. Respect copyright and the SoundCloud terms of use.
