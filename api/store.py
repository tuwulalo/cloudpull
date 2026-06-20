"""Tiny SQLite-backed store for analytics, admin credentials and settings.

A new connection is opened per call (cheap at this scale and thread-safe, since
the API serves downloads from a thread pool). WAL mode allows concurrent reads.
The database lives under data/ and is gitignored (it holds the admin secrets).
"""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import sqlite3
import time
from pathlib import Path
from typing import Any, Optional

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "cloudpull.db"
_PBKDF2_ROUNDS = 200_000


def _conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init() -> None:
    with _conn() as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS events "
            "(id INTEGER PRIMARY KEY, ts REAL, type TEXT, fmt TEXT, ok INTEGER)"
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts)")
        conn.execute(
            "CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)"
        )


# --- events / analytics -----------------------------------------------------

def record(event_type: str, fmt: Optional[str] = None, ok: bool = True) -> None:
    try:
        with _conn() as conn:
            conn.execute(
                "INSERT INTO events (ts, type, fmt, ok) VALUES (?, ?, ?, ?)",
                (time.time(), event_type, fmt, 1 if ok else 0),
            )
    except sqlite3.Error:
        pass


def get_stats() -> dict[str, Any]:
    now = time.time()
    day = 86400.0
    with _conn() as conn:
        def scalar(sql: str, args: tuple = ()) -> int:
            return int(conn.execute(sql, args).fetchone()[0])

        visits_total = scalar("SELECT COUNT(*) FROM events WHERE type='visit'")
        dl_total = scalar("SELECT COUNT(*) FROM events WHERE type='download' AND ok=1")
        dl_failed = scalar("SELECT COUNT(*) FROM events WHERE type='download' AND ok=0")
        visits_24h = scalar(
            "SELECT COUNT(*) FROM events WHERE type='visit' AND ts>=?", (now - day,)
        )
        dl_24h = scalar(
            "SELECT COUNT(*) FROM events WHERE type='download' AND ok=1 AND ts>=?",
            (now - day,),
        )
        by_format = dict(
            conn.execute(
                "SELECT fmt, COUNT(*) FROM events "
                "WHERE type='download' AND ok=1 AND fmt IS NOT NULL GROUP BY fmt"
            ).fetchall()
        )
        daily = []
        for i in range(6, -1, -1):
            start, end = now - (i + 1) * day, now - i * day
            daily.append(
                {
                    "visits": scalar(
                        "SELECT COUNT(*) FROM events WHERE type='visit' AND ts>=? AND ts<?",
                        (start, end),
                    ),
                    "downloads": scalar(
                        "SELECT COUNT(*) FROM events "
                        "WHERE type='download' AND ok=1 AND ts>=? AND ts<?",
                        (start, end),
                    ),
                }
            )
    success = dl_total + dl_failed
    return {
        "visits_total": visits_total,
        "visits_24h": visits_24h,
        "downloads_total": dl_total,
        "downloads_24h": dl_24h,
        "downloads_failed": dl_failed,
        "success_rate": round(dl_total / success * 100, 1) if success else 100.0,
        "by_format": by_format,
        "daily": daily,
    }


# --- settings (key/value) ---------------------------------------------------

def get_setting(key: str, default: Optional[str] = None) -> Optional[str]:
    with _conn() as conn:
        row = conn.execute(
            "SELECT value FROM settings WHERE key=?", (key,)
        ).fetchone()
    return row[0] if row else default


def set_setting(key: str, value: str) -> None:
    with _conn() as conn:
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )


# --- proxies ----------------------------------------------------------------

def list_proxies() -> list[str]:
    try:
        return json.loads(get_setting("proxies", "[]") or "[]")
    except json.JSONDecodeError:
        return []


def set_proxies(proxies: list[str]) -> None:
    clean = [p.strip() for p in proxies if p and p.strip()]
    set_setting("proxies", json.dumps(clean))


def pick_proxy() -> Optional[str]:
    """Pick a proxy to spread load across IPs. Returns None if none configured."""
    proxies = list_proxies()
    if not proxies:
        return None
    # secrets.choice avoids importing random just for this.
    return secrets.choice(proxies)


# --- admin credentials + 2FA ------------------------------------------------

def hash_password(password: str, salt: Optional[str] = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), bytes.fromhex(salt), _PBKDF2_ROUNDS
    ).hex()
    return f"{salt}${digest}"


def verify_password(password: str, stored: Optional[str]) -> bool:
    if not stored or "$" not in stored:
        return False
    salt, digest = stored.split("$", 1)
    try:
        candidate = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt), _PBKDF2_ROUNDS
        ).hex()
    except ValueError:
        return False
    return hmac.compare_digest(candidate, digest)


def admin_configured() -> bool:
    return bool(get_setting("admin_user") and get_setting("admin_pw") and get_setting("totp_secret"))


def set_admin(user: str, password: str, totp_secret: str) -> None:
    set_setting("admin_user", user)
    set_setting("admin_pw", hash_password(password))
    set_setting("totp_secret", totp_secret)


# --- signed admin session (HMAC, no extra deps) -----------------------------

def _session_secret() -> str:
    secret = get_setting("session_secret")
    if not secret:
        secret = secrets.token_hex(32)
        set_setting("session_secret", secret)
    return secret


def make_session(ttl_seconds: int = 8 * 3600) -> str:
    expires = int(time.time()) + ttl_seconds
    message = f"admin.{expires}"
    sig = hmac.new(
        _session_secret().encode(), message.encode(), hashlib.sha256
    ).hexdigest()
    return f"{message}.{sig}"


def check_session(token: Optional[str]) -> bool:
    if not token:
        return False
    try:
        message, sig = token.rsplit(".", 1)
        _, expires = message.split(".", 1)
        if int(expires) < time.time():
            return False
    except (ValueError, AttributeError):
        return False
    good = hmac.new(
        _session_secret().encode(), message.encode(), hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(sig, good)
