"""CloudPull Telegram bot (Phase 2).

Reuses the shared core/ engine. The user sends a SoundCloud link, picks a
format with inline buttons, and the bot downloads, converts and sends the audio.

Run from the project root:
    python -m bot.main

The bot token is read from BOT_TOKEN (see .env / .env.example). Never commit it.
"""

from __future__ import annotations

import asyncio
import html
import os
import re
import shutil
import sys
import uuid
import zipfile
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    CallbackQuery,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
load_dotenv(BASE_DIR / ".env")

from core import DownloadError, download, get_info  # noqa: E402

TOKEN = os.environ.get("BOT_TOKEN", "").strip()
DOWNLOADS = BASE_DIR / "downloads" / "bot"
TELEGRAM_LIMIT = 50 * 1024 * 1024  # bots may send files up to 50 MB

FORMATS = ["mp3", "m4a", "flac", "wav", "opus"]
SC_RE = re.compile(r"https?://(?:www\.|m\.|on\.)?soundcloud\.com/\S+", re.IGNORECASE)

dp = Dispatcher()

# Short-lived map of inline-button key -> request data, so callback_data stays
# within Telegram's 64-byte limit.
PENDING: dict[str, dict] = {}


def format_keyboard(key: str) -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(text=f.upper(), callback_data=f"dl:{key}:{f}")
        for f in FORMATS
    ]
    rows = [buttons[i : i + 3] for i in range(0, len(buttons), 3)]
    return InlineKeyboardMarkup(inline_keyboard=rows)


@dp.message(CommandStart())
async def on_start(message: Message) -> None:
    await message.answer(
        "👋 <b>CloudPull</b>\n\n"
        "Send me a <b>SoundCloud</b> track or set link and I will download the "
        "audio in the format you choose (mp3, m4a, flac, wav, opus), with cover "
        "art and tags embedded.\n\n"
        "Just paste a link to start."
    )


@dp.message(Command("help"))
async def on_help(message: Message) -> None:
    await message.answer(
        "Paste a SoundCloud track or set link. I will read the title and artist, "
        "then show format buttons. Pick one and I will send the file back.\n\n"
        "Single tracks come as audio; a set comes as a zip archive. "
        "Telegram limits bot uploads to 50 MB."
    )


@dp.message(F.text)
async def on_text(message: Message) -> None:
    match = SC_RE.search(message.text or "")
    if not match:
        await message.answer("Send me a SoundCloud track or set link to start.")
        return

    url = match.group(0)
    status = await message.reply("🔎 Reading the link...")
    try:
        info = await asyncio.to_thread(get_info, url)
    except DownloadError as exc:
        await status.edit_text(f"Could not read this link: {html.escape(str(exc))}")
        return
    except Exception:  # noqa: BLE001
        await status.edit_text("Could not read this link. Is it a public SoundCloud URL?")
        return

    key = uuid.uuid4().hex[:10]
    PENDING[key] = {
        "url": url,
        "type": info.get("type"),
        "title": info.get("title"),
        "uploader": info.get("uploader"),
    }

    if info.get("type") == "playlist":
        caption = (
            f"<b>{html.escape(info.get('title') or 'Set')}</b>\n"
            f"{info.get('track_count') or 0} tracks\n\nChoose a format:"
        )
    else:
        caption = (
            f"<b>{html.escape(info.get('title') or 'Track')}</b>\n"
            f"{html.escape(info.get('uploader') or '')}\n\nChoose a format:"
        )
    await status.edit_text(caption, reply_markup=format_keyboard(key))


@dp.callback_query(F.data.startswith("dl:"))
async def on_choose_format(callback: CallbackQuery) -> None:
    try:
        _, key, fmt = callback.data.split(":")
    except ValueError:
        await callback.answer()
        return

    data = PENDING.get(key)
    if not data:
        await callback.answer("This request expired. Send the link again.", show_alert=True)
        return
    await callback.answer()

    message = callback.message
    await message.edit_text(f"⏳ Downloading and converting to {fmt.upper()}...")

    out_dir = DOWNLOADS / key
    try:
        files = await asyncio.to_thread(
            download, data["url"], fmt, "320", str(out_dir), True
        )
    except DownloadError as exc:
        await message.edit_text(f"Download failed: {html.escape(str(exc))}")
        return
    except Exception:  # noqa: BLE001
        await message.edit_text("Download failed unexpectedly. Try again.")
        return

    try:
        if len(files) == 1:
            await _send_single(message, files[0], data)
        else:
            await _send_set(message, files, data, fmt)
    finally:
        shutil.rmtree(out_dir, ignore_errors=True)
        PENDING.pop(key, None)


async def _send_single(message: Message, path: str, data: dict) -> None:
    if os.path.getsize(path) > TELEGRAM_LIMIT:
        await message.edit_text(
            "This file is larger than Telegram's 50 MB limit for bots. "
            "Use the CloudPull web app for this one."
        )
        return
    await message.edit_text("⬆️ Uploading...")
    await message.answer_audio(
        audio=FSInputFile(path),
        title=data.get("title") or None,
        performer=data.get("uploader") or None,
    )
    await message.delete()


async def _send_set(message: Message, files: list[str], data: dict, fmt: str) -> None:
    out_dir = Path(files[0]).parent
    zip_path = out_dir / f"{_safe(data.get('title') or 'cloudpull-set')}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in files:
            zf.write(f, arcname=os.path.basename(f))

    if zip_path.stat().st_size > TELEGRAM_LIMIT:
        await message.edit_text(
            f"This set is {len(files)} tracks and the zip exceeds Telegram's 50 MB "
            "limit for bots. Use the CloudPull web app to grab the whole set."
        )
        return
    await message.edit_text("⬆️ Uploading...")
    await message.answer_document(document=FSInputFile(str(zip_path)))
    await message.delete()


def _safe(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', "_", name).strip() or "cloudpull-set"


async def main() -> None:
    if not TOKEN:
        print(
            "BOT_TOKEN is not set. Put it in a .env file at the project root:\n"
            "  BOT_TOKEN=123456:your-token-here\n"
            "or set it as an environment variable, then run: python -m bot.main"
        )
        return
    DOWNLOADS.mkdir(parents=True, exist_ok=True)
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    me = await bot.get_me()
    print(f"CloudPull bot online as @{me.username}. Polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
