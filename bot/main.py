"""CloudPull Telegram bot (Phase 2).

Reuses the shared core/ engine. Two ways to use it:
  - Send a SoundCloud link, then pick a format with inline buttons.
  - Use a direct command: /mp3 <link>, /m4a, /flac, /wav, /opus.

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
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import (
    BotCommand,
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
WEB_APP = "https://cloudpull.cloud"

FORMATS = ["mp3", "m4a", "flac", "wav", "opus"]
SC_RE = re.compile(r"https?://(?:www\.|m\.|on\.)?soundcloud\.com/\S+", re.IGNORECASE)

dp = Dispatcher()

# Short-lived map of inline-button key -> request data (callback_data is limited
# to 64 bytes, so we cannot put the URL in it directly).
PENDING: dict[str, dict] = {}


def format_keyboard(key: str) -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(text=f.upper(), callback_data=f"dl:{key}:{f}")
        for f in FORMATS
    ]
    rows = [buttons[i : i + 3] for i in range(0, len(buttons), 3)]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _safe(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', "_", name or "").strip() or "cloudpull-set"


async def _run_download(url: str, fmt: str) -> list[str]:
    out_dir = DOWNLOADS / uuid.uuid4().hex[:10]
    return await asyncio.to_thread(download, url, fmt, "320", str(out_dir), True)


async def _deliver(
    status: Message,
    files: list[str],
    title: str | None = None,
    uploader: str | None = None,
) -> None:
    """Send the produced file(s) and clean up. `status` is the progress message."""
    out_dir = Path(files[0]).parent
    try:
        if len(files) == 1:
            path = files[0]
            if os.path.getsize(path) > TELEGRAM_LIMIT:
                await status.edit_text(
                    "This file is over Telegram's 50 MB limit for bots. "
                    f"Grab it on the web app: {WEB_APP}"
                )
                return
            await status.edit_text("⬆️ Uploading...")
            await status.answer_audio(
                audio=FSInputFile(path),
                title=title or None,
                performer=uploader or None,
            )
        else:
            zip_path = out_dir / f"{_safe(title or 'cloudpull-set')}.zip"
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for f in files:
                    zf.write(f, arcname=os.path.basename(f))
            if zip_path.stat().st_size > TELEGRAM_LIMIT:
                await status.edit_text(
                    f"This set's zip is over Telegram's 50 MB bot limit. "
                    f"Grab the whole set on the web app: {WEB_APP}"
                )
                return
            await status.edit_text("⬆️ Uploading...")
            await status.answer_document(document=FSInputFile(str(zip_path)))
        await status.delete()
    finally:
        shutil.rmtree(out_dir, ignore_errors=True)


@dp.message(CommandStart())
async def on_start(message: Message) -> None:
    await message.answer(
        "👋 <b>CloudPull</b>\n\n"
        "Download <b>SoundCloud</b> tracks and sets with cover art and tags.\n\n"
        "<b>Two ways:</b>\n"
        "• Send a link, then tap a format.\n"
        "• Or use a direct command, e.g. <code>/mp3 https://soundcloud.com/...</code>\n\n"
        "Formats: /mp3 /m4a /flac /wav /opus"
    )


@dp.message(Command("help"))
async def on_help(message: Message) -> None:
    await message.answer(
        "<b>How to use</b>\n\n"
        "Send a SoundCloud track or set link, then pick a format with the buttons.\n\n"
        "Or download straight away with a command:\n"
        "<code>/mp3 &lt;link&gt;</code>, <code>/m4a</code>, <code>/flac</code>, "
        "<code>/wav</code>, <code>/opus</code>\n\n"
        "Single tracks arrive as audio; a set arrives as a zip. "
        "Telegram limits bot uploads to 50 MB; bigger files are on "
        f"{WEB_APP}."
    )


@dp.message(Command(*FORMATS))
async def on_format_command(message: Message, command: CommandObject) -> None:
    fmt = (command.command or "").lower()
    if fmt not in FORMATS:
        return
    match = SC_RE.search(command.args or "")
    if not match:
        await message.reply(f"Send the link too:\n<code>/{fmt} https://soundcloud.com/...</code>")
        return

    status = await message.reply(f"⏳ Downloading {fmt.upper()}...")
    try:
        files = await _run_download(match.group(0), fmt)
    except DownloadError as exc:
        await status.edit_text(f"Download failed: {html.escape(str(exc))}")
        return
    except Exception:  # noqa: BLE001
        await status.edit_text("Download failed unexpectedly. Try again.")
        return
    await _deliver(status, files)


@dp.message(F.text)
async def on_text(message: Message) -> None:
    match = SC_RE.search(message.text or "")
    if not match:
        await message.answer(
            "Send a SoundCloud link, or use /mp3 /m4a /flac /wav /opus with a link."
        )
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
    try:
        files = await _run_download(data["url"], fmt)
    except DownloadError as exc:
        await message.edit_text(f"Download failed: {html.escape(str(exc))}")
        return
    except Exception:  # noqa: BLE001
        await message.edit_text("Download failed unexpectedly. Try again.")
        return
    finally:
        PENDING.pop(key, None)
    await _deliver(message, files, data.get("title"), data.get("uploader"))


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
    await bot.set_my_commands(
        [
            BotCommand(command="mp3", description="Download as mp3 (320)"),
            BotCommand(command="m4a", description="Download as m4a"),
            BotCommand(command="flac", description="Download as FLAC (lossless)"),
            BotCommand(command="wav", description="Download as WAV (lossless)"),
            BotCommand(command="opus", description="Download as opus"),
            BotCommand(command="help", description="How to use the bot"),
        ]
    )
    me = await bot.get_me()
    print(f"CloudPull bot online as @{me.username}. Polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
