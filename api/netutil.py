"""Trusted client-IP resolution for rate limiting and login throttling.

The backend binds to 127.0.0.1 and sits behind Caddy, which sets `X-Real-IP` to
the real TCP peer (`header_up X-Real-IP {remote_host}`) - a value the client
cannot forge, because Caddy overwrites any client-supplied header. We therefore
trust ONLY `X-Real-IP`.

We deliberately do NOT trust `X-Forwarded-For`: a client can prepend arbitrary
entries to it, and reading the left-most one (as older code did) let an attacker
spoof the throttle key and brute force /admin/login from a single IP. If
`X-Real-IP` is absent (local dev with no proxy), we fall back to the direct peer
address, which is correct there and fail-safe in production (all traffic would
share one bucket - over-throttling, never under-throttling).
"""

from __future__ import annotations

from fastapi import Request


def client_ip(request: Request) -> str:
    real = request.headers.get("x-real-ip", "").strip()
    if real:
        # Guard against a header that somehow carries a list; take the first.
        return real.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
