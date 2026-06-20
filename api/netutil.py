"""Trusted client-IP resolution for rate limiting, login throttling and visit
counting.

The backend binds to 127.0.0.1 and sits behind Caddy. Caddy sets `X-Real-IP` to
the real TCP peer (`header_up X-Real-IP {remote_host}`) - a value the client
cannot forge, because Caddy overwrites any client-supplied header. So the peer
seen by the app is always trustworthy.

Two deployment modes:

  * Direct / grey-cloud (Cloudflare DNS-only or no proxy): the peer IS the real
    visitor. Use it.
  * Behind Cloudflare proxy (orange cloud): the peer is a Cloudflare edge IP, and
    the real visitor IP arrives in the `CF-Connecting-IP` header. We trust that
    header ONLY when the connection actually came from a Cloudflare range -
    otherwise an attacker hitting the origin directly could spoof
    `CF-Connecting-IP` to bypass the per-IP throttle. The range check makes the
    header unspoofable without needing an origin firewall.

We never trust `X-Forwarded-For`: a client can prepend arbitrary entries to it,
and reading the left-most one (as older code did) let an attacker spoof the
throttle key and brute force /admin/login from a single IP.
"""

from __future__ import annotations

import ipaddress

from fastapi import Request

# Cloudflare's published edge ranges. Source: https://www.cloudflare.com/ips-v4
# and /ips-v6 (fetched 2026-06-21). These change very rarely; refresh if visitor
# IPs ever start showing as a Cloudflare address (a sign a new range was added).
_CLOUDFLARE_CIDRS = (
    "173.245.48.0/20", "103.21.244.0/22", "103.22.200.0/22", "103.31.4.0/22",
    "141.101.64.0/18", "108.162.192.0/18", "190.93.240.0/20", "188.114.96.0/20",
    "197.234.240.0/22", "198.41.128.0/17", "162.158.0.0/15", "104.16.0.0/13",
    "104.24.0.0/14", "172.64.0.0/13", "131.0.72.0/22",
    "2400:cb00::/32", "2606:4700::/32", "2803:f800::/32", "2405:b500::/32",
    "2405:8100::/32", "2a06:98c0::/29", "2c0f:f248::/32",
)
_CLOUDFLARE_NETS = tuple(ipaddress.ip_network(c) for c in _CLOUDFLARE_CIDRS)


def _from_cloudflare(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return any(addr in net for net in _CLOUDFLARE_NETS)


def client_ip(request: Request) -> str:
    # The real TCP peer as seen by Caddy (or the direct client in dev).
    peer = request.headers.get("x-real-ip", "").split(",")[0].strip()
    if not peer:
        peer = request.client.host if request.client else ""

    # Only trust CF-Connecting-IP when the request genuinely arrived from a
    # Cloudflare edge; otherwise it is attacker-controlled and ignored.
    if peer and _from_cloudflare(peer):
        cf = request.headers.get("cf-connecting-ip", "").strip()
        if cf:
            return cf

    return peer or "unknown"
