"""Tiny SQLite-backed store for analytics, admin credentials and settings.

A new connection is opened per call (cheap at this scale and thread-safe, since
the API serves downloads from a thread pool). WAL mode allows concurrent reads.
The database lives under data/ and is gitignored (it holds the admin secrets).
"""

from __future__ import annotations

import hashlib
import hmac
import ipaddress
import json
import secrets
import socket
import sqlite3
import time
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

import pyotp

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


# Proxy schemes yt-dlp / requests understand. Anything else is rejected so an
# admin cannot (accidentally or post-compromise) point downloads at, say, a
# file:// or gopher:// URL.
_PROXY_SCHEMES = {"http", "https", "socks4", "socks4a", "socks5", "socks5h"}


def _ip_is_public(ip_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return False
    return not (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def validate_proxy(raw: str) -> Optional[str]:
    """Return None if the proxy URL is safe, else a human-readable reason.

    Blocks private/loopback/link-local/reserved targets so a configured proxy
    cannot be used to reach internal services (SSRF / port scanning from the
    server). DNS is resolved so a hostname pointing at an internal IP is caught
    too. (A determined rebind at use-time is still possible - yt-dlp resolves
    again later - but this stops the realistic admin-misconfig and basic SSRF.)
    """
    url = (raw or "").strip()
    if not url:
        return "empty entry"
    parsed = urlparse(url)
    scheme = (parsed.scheme or "").lower()
    if scheme not in _PROXY_SCHEMES:
        return f"unsupported scheme '{parsed.scheme or '(none)'}'"
    host = parsed.hostname
    if not host:
        return "missing host"

    # Literal IP address: check directly.
    try:
        ipaddress.ip_address(host)
        return None if _ip_is_public(host) else f"private/loopback address not allowed ({host})"
    except ValueError:
        pass

    low = host.lower()
    if low == "localhost" or low.endswith((".local", ".internal", ".localhost")):
        return f"internal hostname not allowed ({host})"

    # Hostname: resolve and reject if ANY resolved address is non-public.
    try:
        infos = socket.getaddrinfo(host, parsed.port or 80, proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        return f"cannot resolve host ({host})"
    for info in infos:
        addr = info[4][0]
        if not _ip_is_public(addr):
            return f"host resolves to a private address ({host} -> {addr})"
    return None


def set_proxies(proxies: list[str]) -> None:
    """Persist proxies after validation. Raises ValueError listing bad entries."""
    clean = [p.strip() for p in proxies if p and p.strip()]
    problems = [f"{p}: {reason}" for p in clean if (reason := validate_proxy(p))]
    if problems:
        raise ValueError("; ".join(problems))
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
    # Treat a credential change as a full reset / panic button: fresh TOTP secret
    # means the replay counter must restart, and rotating the session signing
    # secret locks out anyone who copied the old DB (they could otherwise forge
    # a cookie for any version). Re-running admin_setup is the recovery action
    # after a suspected DB or credential leak.
    set_setting("totp_last_ctr", "-1")
    rotate_session_secret()


def consume_totp(code: str) -> bool:
    """Verify a TOTP code AND reject replays (RFC 6238 5.2).

    The highest accepted time-step counter is persisted; a code is accepted only
    if its counter is strictly greater than the last one used. So a code that has
    already logged in once cannot be reused within its 30-90s validity window
    (e.g. if it leaked via a log, Referer or a malicious extension).
    """
    secret = get_setting("totp_secret") or ""
    code = (code or "").strip()
    if not secret or not code:
        return False
    totp = pyotp.TOTP(secret)
    now = int(time.time())
    step = 30
    current = now // step
    matched: Optional[int] = None
    # Accept the previous, current and next step (clock skew tolerance).
    for offset in (-1, 0, 1):
        if totp.verify(code, for_time=now + offset * step):
            matched = current + offset
            break
    if matched is None:
        return False
    try:
        last = int(get_setting("totp_last_ctr") or "-1")
    except ValueError:
        last = -1
    if matched <= last:
        return False  # replay or out-of-order reuse
    set_setting("totp_last_ctr", str(matched))
    return True


# --- signed admin session (HMAC, no extra deps) -----------------------------

def _session_secret() -> str:
    secret = get_setting("session_secret")
    if not secret:
        secret = secrets.token_hex(32)
        set_setting("session_secret", secret)
    return secret


def _session_version() -> int:
    try:
        return int(get_setting("admin_session_ver") or "1")
    except ValueError:
        return 1


def bump_session_version() -> None:
    """Cheap kill-switch (logout): invalidate all existing session cookies."""
    set_setting("admin_session_ver", str(_session_version() + 1))


def rotate_session_secret() -> None:
    """Strong reset: generate a new signing secret and bump the version.

    Unlike a version bump alone, this defends against a leaked database: an
    attacker who copied the old `session_secret` could forge a cookie for any
    version, but cannot sign one under a secret they have never seen.
    """
    set_setting("session_secret", secrets.token_hex(32))
    bump_session_version()


def make_session(ttl_seconds: int = 8 * 3600) -> str:
    expires = int(time.time()) + ttl_seconds
    message = f"admin.{_session_version()}.{expires}"
    sig = hmac.new(
        _session_secret().encode(), message.encode(), hashlib.sha256
    ).hexdigest()
    return f"{message}.{sig}"


def check_session(token: Optional[str]) -> bool:
    if not token:
        return False
    try:
        message, sig = token.rsplit(".", 1)
        prefix, version, expires = message.split(".")
        if prefix != "admin":
            return False
        if int(version) != _session_version():
            return False  # revoked by logout / credential change
        if int(expires) < time.time():
            return False
    except (ValueError, AttributeError):
        return False
    good = hmac.new(
        _session_secret().encode(), message.encode(), hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(sig, good)
