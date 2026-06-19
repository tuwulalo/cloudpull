# CloudPull Telegram bot (Phase 2)

An [aiogram](https://aiogram.dev) bot that reuses the shared `core/` engine.
Send it a SoundCloud link, pick a format with inline buttons, and it downloads,
converts and sends the audio back.

## Setup

1. Get a token from [@BotFather](https://t.me/BotFather).
2. Copy `.env.example` to `.env` in the project root and set `BOT_TOKEN`:

   ```
   BOT_TOKEN=123456:your-token-here
   ```

   The `.env` file is gitignored, so the token never gets committed.

3. Install dependencies (from the project root):

   ```powershell
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   ```

## Run

From the project root:

```powershell
.\.venv\Scripts\python.exe -m bot.main
```

The bot uses long polling, so no public URL is needed. It needs `ffmpeg` on
PATH (same as the web app).

## What it does

- Reads the title and artist of a track or set.
- Shows format buttons: mp3, m4a, flac, wav, opus.
- Single tracks are sent as audio; a set is zipped and sent as a document.
- Telegram limits bot uploads to 50 MB. Larger files are flagged, use the web
  app for those.

The download and conversion logic lives entirely in `core/`, so the bot and the
web app stay in sync.
