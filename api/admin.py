"""Admin panel: analytics dashboard + proxy/settings management.

Auth is a username + password + TOTP 2FA, then a signed HttpOnly session cookie.
Mounted under /admin (Caddy routes /admin* to this API).
"""

from __future__ import annotations

import time
from collections import deque

import pyotp
from fastapi import APIRouter, Form, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel

from api import store

router = APIRouter()
COOKIE = "cp_admin"

# Per-IP login throttle to slow brute force.
_LOGIN_MAX = 8
_LOGIN_WINDOW = 900  # 15 minutes
_login_hits: dict[str, deque] = {}


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for", "")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _login_allowed(ip: str) -> bool:
    now = time.time()
    hits = _login_hits.setdefault(ip, deque())
    while hits and now - hits[0] > _LOGIN_WINDOW:
        hits.popleft()
    if len(hits) >= _LOGIN_MAX:
        return False
    hits.append(now)
    return True


def _authed(request: Request) -> bool:
    return store.check_session(request.cookies.get(COOKIE))


def _require(request: Request) -> None:
    if not _authed(request):
        raise HTTPException(status_code=401, detail="Not authenticated")


# --- pages ------------------------------------------------------------------

@router.get("/admin", response_class=HTMLResponse)
def admin_root(request: Request) -> HTMLResponse:
    if not store.admin_configured():
        return HTMLResponse(_SETUP_HTML, status_code=200)
    if _authed(request):
        return HTMLResponse(_DASHBOARD_HTML)
    return HTMLResponse(_login_html())


@router.post("/admin/login")
def admin_login(
    request: Request,
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
    code: str = Form(...),
) -> Response:
    ip = _client_ip(request)
    if not _login_allowed(ip):
        return HTMLResponse(_login_html("Too many attempts. Try again later."), status_code=429)

    user_ok = username.strip() == (store.get_setting("admin_user") or "")
    pw_ok = store.verify_password(password, store.get_setting("admin_pw"))
    secret = store.get_setting("totp_secret") or ""
    code_ok = bool(secret) and pyotp.TOTP(secret).verify(code.strip(), valid_window=1)

    if not (user_ok and pw_ok and code_ok):
        return HTMLResponse(_login_html("Invalid username, password or code."), status_code=401)

    redirect = RedirectResponse(url="/admin", status_code=303)
    redirect.set_cookie(
        COOKIE,
        store.make_session(),
        max_age=8 * 3600,
        httponly=True,
        secure=True,
        samesite="strict",
        path="/admin",
    )
    return redirect


@router.post("/admin/logout")
def admin_logout() -> Response:
    redirect = RedirectResponse(url="/admin", status_code=303)
    redirect.delete_cookie(COOKIE, path="/admin")
    return redirect


# --- data api ---------------------------------------------------------------

@router.get("/admin/api/stats")
def admin_stats(request: Request) -> JSONResponse:
    _require(request)
    return JSONResponse(store.get_stats())


@router.get("/admin/api/proxies")
def admin_get_proxies(request: Request) -> JSONResponse:
    _require(request)
    return JSONResponse({"proxies": store.list_proxies()})


class ProxiesBody(BaseModel):
    proxies: list[str]


@router.post("/admin/api/proxies")
def admin_set_proxies(request: Request, body: ProxiesBody) -> JSONResponse:
    _require(request)
    store.set_proxies(body.proxies)
    return JSONResponse({"proxies": store.list_proxies()})


# --- html -------------------------------------------------------------------

_HEAD = """<!doctype html><html lang=en><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<meta name=robots content="noindex,nofollow">
<title>CloudPull admin</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#0b0b0f;color:#f4f4f6;
font-family:ui-sans-serif,system-ui,sans-serif;-webkit-font-smoothing:antialiased}
a{color:#ff8a00}.wrap{max-width:920px;margin:0 auto;padding:28px}
.card{background:#15151b;border:1px solid #24242c;border-radius:14px;padding:18px}
.grid{display:grid;gap:12px}.g4{grid-template-columns:repeat(4,1fr)}
.g2{grid-template-columns:1fr 1fr}@media(max-width:680px){.g4,.g2{grid-template-columns:1fr 1fr}}
.k{font-size:12px;color:#9a9aa6;text-transform:uppercase;letter-spacing:.08em}
.v{font-size:30px;font-weight:800;margin-top:4px;font-variant-numeric:tabular-nums}
h1{font-size:20px;margin:0 0 18px;display:flex;align-items:center;gap:8px}
h2{font-size:14px;color:#9a9aa6;margin:24px 0 10px;text-transform:uppercase;letter-spacing:.08em}
.btn{background:#ff5500;color:#fff;border:0;border-radius:9px;padding:10px 16px;
font-weight:600;cursor:pointer}.btn:hover{filter:brightness(1.1)}
.ghost{background:#24242c;color:#f4f4f6}
input,textarea{width:100%;background:#0e0e13;border:1px solid #2a2a33;border-radius:9px;
color:#f4f4f6;padding:11px 12px;font:inherit;margin-top:6px}textarea{min-height:120px;resize:vertical}
label{font-size:13px;color:#c7c7cf}.row{margin-bottom:14px}
.bar{height:120px;display:flex;align-items:flex-end;gap:8px}
.bar>div{flex:1;display:flex;flex-direction:column;justify-content:flex-end;gap:3px;text-align:center}
.bar i{display:block;background:#ff5500;border-radius:4px 4px 0 0;min-height:2px}
.bar i.v2{background:#7b6cff}.muted{color:#9a9aa6;font-size:12px}
.err{color:#ff6b6b;font-size:13px;margin-top:8px}.ok{color:#5fd17a;font-size:13px;margin-top:8px}
.pill{display:inline-block;background:#24242c;border-radius:6px;padding:3px 9px;margin:3px 4px 0 0;font-size:13px}
</style></head><body><div class=wrap>"""

_FOOT = "</div></body></html>"


def _login_html(error: str = "") -> str:
    err = f"<div class=err>{error}</div>" if error else ""
    return (
        _HEAD
        + "<h1>🔒 CloudPull admin</h1>"
        + "<div class=card style='max-width:380px;margin:40px auto'>"
        + "<form method=post action='/admin/login'>"
        + "<div class=row><label>Username</label><input name=username autocomplete=username></div>"
        + "<div class=row><label>Password</label><input name=password type=password autocomplete=current-password></div>"
        + "<div class=row><label>2FA code</label><input name=code inputmode=numeric autocomplete=one-time-code placeholder='6 digits'></div>"
        + f"{err}<button class=btn style='width:100%'>Sign in</button>"
        + "</form></div>"
        + _FOOT
    )


_SETUP_HTML = (
    _HEAD
    + "<h1>🔒 CloudPull admin</h1>"
    + "<div class=card style='max-width:460px;margin:40px auto'>"
    + "<p>No admin account yet. On the server, run:</p>"
    + "<p><code>python -m api.admin_setup</code></p>"
    + "<p class=muted>It sets your username/password and shows a QR code for 2FA. "
    + "Then refresh this page.</p></div>"
    + _FOOT
)


_DASHBOARD_HTML = (
    _HEAD
    + "<h1>📊 CloudPull <span class=muted style='font-weight:400'>analytics</span>"
    + "<form method=post action='/admin/logout' style='margin-left:auto'>"
    + "<button class='btn ghost'>Log out</button></form></h1>"
    + "<div class='grid g4'>"
    + "<div class=card><div class=k>Visits total</div><div class=v id=vt>-</div></div>"
    + "<div class=card><div class=k>Visits 24h</div><div class=v id=v24>-</div></div>"
    + "<div class=card><div class=k>Downloads total</div><div class=v id=dt>-</div></div>"
    + "<div class=card><div class=k>Downloads 24h</div><div class=v id=d24>-</div></div>"
    + "</div>"
    + "<h2>Last 7 days</h2><div class=card><div class=bar id=chart></div>"
    + "<div class=muted style='margin-top:10px'>"
    + "<span style='color:#ff5500'>■</span> downloads &nbsp; "
    + "<span style='color:#7b6cff'>■</span> visits</div></div>"
    + "<div class='grid g2' style='margin-top:12px'>"
    + "<div class=card><div class=k>By format</div><div id=fmt style='margin-top:8px'></div></div>"
    + "<div class=card><div class=k>Success rate</div><div class=v id=sr>-</div>"
    + "<div class=muted id=fail></div></div></div>"
    + "<h2>Proxies</h2><div class=card>"
    + "<label>One per line. Used to spread downloads across IPs and avoid rate limits. "
    + "Format: <code>http://user:pass@host:port</code> or <code>socks5://host:port</code></label>"
    + "<textarea id=proxies placeholder='http://user:pass@1.2.3.4:8080'></textarea>"
    + "<button class=btn id=saveproxies style='margin-top:10px'>Save proxies</button>"
    + "<span id=psaved></span></div>"
    + "<script>"
    + "async function load(){"
    + "const s=await (await fetch('/admin/api/stats')).json();"
    + "vt.textContent=s.visits_total;v24.textContent=s.visits_24h;"
    + "dt.textContent=s.downloads_total;d24.textContent=s.downloads_24h;"
    + "sr.textContent=s.success_rate+'%';fail.textContent=s.downloads_failed+' failed';"
    + "const mx=Math.max(1,...s.daily.flatMap(d=>[d.downloads,d.visits]));"
    + "chart.innerHTML=s.daily.map(d=>`<div><i style='height:${d.downloads/mx*100}px'></i>"
    + "<i class=v2 style='height:${d.visits/mx*100}px'></i></div>`).join('');"
    + "fmt.innerHTML=Object.entries(s.by_format).map(([k,v])=>`<span class=pill>${k}: <b>${v}</b></span>`).join('')||'<span class=muted>no data</span>';"
    + "}"
    + "async function loadProxies(){const p=await (await fetch('/admin/api/proxies')).json();"
    + "document.getElementById('proxies').value=(p.proxies||[]).join('\\n');}"
    + "saveproxies.onclick=async()=>{const lines=document.getElementById('proxies').value.split('\\n').map(x=>x.trim()).filter(Boolean);"
    + "const r=await fetch('/admin/api/proxies',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({proxies:lines})});"
    + "const el=document.getElementById('psaved');el.textContent=r.ok?'  saved':'  error';el.className=r.ok?'ok':'err';};"
    + "load();loadProxies();setInterval(load,30000);"
    + "</script>"
    + _FOOT
)
