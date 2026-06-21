"""Automated Google Search Console report for cloudpull.cloud.

Queries the Search Console API with a service account (no browser, no user
OAuth) and produces a short progress report: search performance, top queries
and pages, sitemap status and index coverage of key URLs. Writes it to
data/gsc-report.md and, when a Telegram chat is configured, sends it via the bot.

Auth: a service-account key whose email has been added as a user on the GSC
property (Settings -> Users and permissions). Read-only scope.

Environment (loaded from the project .env):
  GSC_SA_JSON          path to the service-account key JSON              (required)
  GSC_PROPERTY         property id, default 'sc-domain:cloudpull.cloud'
  GSC_SITEMAP          sitemap URL, default 'https://cloudpull.cloud/sitemap.xml'
  GSC_INSPECT_URLS     comma list of URLs to inspect, default the homepage
  BOT_TOKEN            Telegram bot token (reused from the bot config)
  GSC_REPORT_CHAT_ID   Telegram chat id to send the report to            (optional)

Usage:
  python scripts/gsc_report.py            build the report, write it, send it
  python scripts/gsc_report.py --whoami   list recent Telegram chat ids (to find
                                          GSC_REPORT_CHAT_ID: message the bot first)
"""

from __future__ import annotations

import datetime as dt
import json
import os
import sys
import urllib.request
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # noqa: BLE001 - dotenv is optional at runtime
    pass

SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]
PROPERTY = os.environ.get("GSC_PROPERTY", "sc-domain:cloudpull.cloud")
SITEMAP = os.environ.get("GSC_SITEMAP", "https://cloudpull.cloud/sitemap.xml")
INSPECT_URLS = [
    u.strip()
    for u in os.environ.get("GSC_INSPECT_URLS", "https://cloudpull.cloud/").split(",")
    if u.strip()
]
_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
REPORT_PATH = _DATA_DIR / "gsc-report.md"
REPORT_JSON = _DATA_DIR / "gsc-report.json"  # read by the admin panel


def _date(days_ago: int) -> str:
    return (dt.date.today() - dt.timedelta(days=days_ago)).isoformat()


def _service():
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    key = os.environ.get("GSC_SA_JSON")
    if not key or not os.path.exists(key):
        sys.exit("Set GSC_SA_JSON to the service-account key file path (the .json key).")
    creds = service_account.Credentials.from_service_account_file(key, scopes=SCOPES)
    webmasters = build("webmasters", "v3", credentials=creds, cache_discovery=False)
    searchconsole = build("searchconsole", "v1", credentials=creds, cache_discovery=False)
    return webmasters, searchconsole


def _totals(wm, start: str, end: str) -> dict:
    r = wm.searchanalytics().query(
        siteUrl=PROPERTY,
        body={"startDate": start, "endDate": end, "dataState": "all"},
    ).execute()
    rows = r.get("rows") or []
    if not rows:
        return {"clicks": 0, "impressions": 0, "ctr": 0.0, "position": 0.0}
    row = rows[0]
    return {
        "clicks": int(row.get("clicks", 0)),
        "impressions": int(row.get("impressions", 0)),
        "ctr": float(row.get("ctr", 0.0)) * 100,
        "position": float(row.get("position", 0.0)),
    }


def _top(wm, dim: str, start: str, end: str, n: int = 5) -> list:
    r = wm.searchanalytics().query(
        siteUrl=PROPERTY,
        body={
            "startDate": start,
            "endDate": end,
            "dimensions": [dim],
            "rowLimit": n,
            "dataState": "all",
        },
    ).execute()
    out = []
    for row in r.get("rows") or []:
        out.append(
            {
                "key": row["keys"][0],
                "clicks": int(row.get("clicks", 0)),
                "impressions": int(row.get("impressions", 0)),
                "position": float(row.get("position", 0.0)),
            }
        )
    return out


def _sitemap(wm) -> dict:
    try:
        s = wm.sitemaps().get(siteUrl=PROPERTY, feedpath=SITEMAP).execute()
        contents = (s.get("contents") or [{}])[0]
        return {
            "lastDownloaded": s.get("lastDownloaded", "-"),
            "errors": s.get("errors", "0"),
            "warnings": s.get("warnings", "0"),
            "submitted": contents.get("submitted", "-"),
            "indexed": contents.get("indexed", "-"),
            "isPending": s.get("isPending", False),
        }
    except Exception as exc:  # noqa: BLE001 - report, don't crash
        return {"error": str(exc)[:140]}


def _inspect(sc, url: str) -> str:
    # URL Inspection needs the service account to be an Owner/Full user.
    try:
        r = sc.urlInspection().index().inspect(
            body={"inspectionUrl": url, "siteUrl": PROPERTY}
        ).execute()
        idx = r.get("inspectionResult", {}).get("indexStatusResult", {})
        return idx.get("coverageState", "unknown")
    except Exception as exc:  # noqa: BLE001
        return f"n/a ({str(exc)[:60]})"


def _delta(cur: int, prev: int) -> str:
    d = cur - prev
    if d > 0:
        return f"(+{d})"
    if d < 0:
        return f"({d})"
    return "(=)"


def collect() -> dict:
    wm, sc = _service()
    return {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "property": PROPERTY,
        "period": {"start": _date(7), "end": _date(1)},
        "current": _totals(wm, _date(7), _date(1)),    # last 7 days (lagged)
        "previous": _totals(wm, _date(14), _date(8)),  # the 7 days before that
        "queries": _top(wm, "query", _date(28), _date(1)),
        "pages": _top(wm, "page", _date(28), _date(1)),
        "sitemap": _sitemap(wm),
        "inspections": [{"url": u, "state": _inspect(sc, u)} for u in INSPECT_URLS],
    }


def to_html(d: dict) -> str:
    cur, prev = d["current"], d["previous"]
    lines = [
        f"<b>CloudPull - Search Console</b> ({d['period']['start']} .. {d['period']['end']})",
        "",
        "<b>Search (last 7 days vs previous 7)</b>",
        f"Clicks: {cur['clicks']} {_delta(cur['clicks'], prev['clicks'])}",
        f"Impressions: {cur['impressions']} {_delta(cur['impressions'], prev['impressions'])}",
        f"CTR: {cur['ctr']:.1f}%   Avg position: {cur['position']:.1f}",
    ]
    if d["queries"]:
        lines += ["", "<b>Top queries (28d)</b>"]
        for q in d["queries"]:
            lines.append(f"- {q['key']}: {q['clicks']} clk / {q['impressions']} imp, pos {q['position']:.1f}")
    if d["pages"]:
        lines += ["", "<b>Top pages (28d)</b>"]
        for p in d["pages"]:
            lines.append(f"- {p['key']}: {p['clicks']} clk / {p['impressions']} imp")
    sm = d["sitemap"]
    lines += ["", "<b>Sitemap</b>"]
    if "error" in sm:
        lines.append(f"error: {sm['error']}")
    else:
        pend = " (pending)" if sm.get("isPending") else ""
        lines.append(
            f"submitted {sm['submitted']} / indexed {sm['indexed']}, "
            f"errors {sm['errors']}, last read {sm['lastDownloaded']}{pend}"
        )
    lines += ["", "<b>Index status</b>"]
    for ins in d["inspections"]:
        lines.append(f"- {ins['url']}: {ins['state']}")
    if cur["impressions"] == 0 and not d["queries"]:
        lines += ["", "<i>No search data yet - normal for a new property; check back in a few days.</i>"]
    return "\n".join(lines)


def to_plain(d: dict) -> str:
    html = to_html(d)
    for tag in ("<b>", "</b>", "<i>", "</i>"):
        html = html.replace(tag, "")
    return html


def _send_telegram(html: str) -> bool:
    token = os.environ.get("BOT_TOKEN")
    chat = os.environ.get("GSC_REPORT_CHAT_ID")
    if not token or not chat:
        return False
    payload = json.dumps(
        {"chat_id": chat, "text": html, "parse_mode": "HTML", "disable_web_page_preview": True}
    ).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        urllib.request.urlopen(req, timeout=20)
        return True
    except Exception as exc:  # noqa: BLE001
        print("Telegram send failed:", exc)
        return False


def whoami() -> None:
    token = os.environ.get("BOT_TOKEN")
    if not token:
        sys.exit("BOT_TOKEN not set.")
    with urllib.request.urlopen(
        f"https://api.telegram.org/bot{token}/getUpdates", timeout=20
    ) as resp:
        data = json.load(resp)
    seen: dict = {}
    for upd in data.get("result", []):
        msg = upd.get("message") or upd.get("edited_message") or upd.get("channel_post") or {}
        chat = msg.get("chat") or {}
        if chat.get("id") is not None:
            seen[chat["id"]] = chat.get("username") or chat.get("first_name") or chat.get("title") or ""
    if not seen:
        print("No recent chats. Open Telegram, send any message to the bot, then re-run --whoami.")
        return
    print("Recent chats (use the id as GSC_REPORT_CHAT_ID):")
    for cid, name in seen.items():
        print(f"  chat_id={cid}  ({name})")


def main() -> None:
    if "--whoami" in sys.argv:
        whoami()
        return
    data = collect()
    _DATA_DIR.mkdir(exist_ok=True)
    # JSON for the admin panel, markdown for humans / the file log.
    REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    plain = to_plain(data)
    REPORT_PATH.write_text(plain, encoding="utf-8")
    sent = _send_telegram(to_html(data))
    print(plain)
    print("\n[wrote data/gsc-report.json + .md" + ("; sent to Telegram]" if sent else "; Telegram not configured]"))


if __name__ == "__main__":
    main()
