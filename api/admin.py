"""Admin panel: analytics dashboard + proxy/settings management.

Auth is a username + password + TOTP 2FA, then a signed HttpOnly session cookie.
Mounted under /admin (Caddy routes /admin* to this API).
"""

from __future__ import annotations

import time
from collections import deque

from fastapi import APIRouter, Form, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel

from api import store
from api.netutil import client_ip as _client_ip

router = APIRouter()
COOKIE = "cp_admin"

# Per-IP login throttle to slow brute force.
_LOGIN_MAX = 8
_LOGIN_WINDOW = 900  # 15 minutes
_login_hits: dict[str, deque] = {}


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


@router.get("/admin/login")
def admin_login_get() -> RedirectResponse:
    # /admin/login is the POST target of the sign-in form. A bare GET (typed
    # URL or bookmark) should land on the login page, not dump a raw 422.
    return RedirectResponse(url="/admin", status_code=307)


@router.post("/admin/login")
def admin_login(
    request: Request,
    response: Response,
    username: str = Form(""),
    password: str = Form(""),
    code: str = Form(""),
) -> Response:
    ip = _client_ip(request)
    if not _login_allowed(ip):
        return HTMLResponse(_login_html("Too many attempts. Try again later."), status_code=429)

    # Empty fields render the friendly login page, not FastAPI's raw JSON error.
    if not (username.strip() and password.strip() and code.strip()):
        return HTMLResponse(
            _login_html("Enter your username, password and 2FA code."),
            status_code=400,
        )

    user_ok = username.strip() == (store.get_setting("admin_user") or "")
    pw_ok = store.verify_password(password, store.get_setting("admin_pw"))
    # Only consume (and advance) the TOTP counter once the username and password
    # are correct, so a wrong-password attempt cannot burn the admin's code.
    code_ok = user_ok and pw_ok and store.consume_totp(code)

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
    # Bump the session version so the cookie is revoked server-side, not just
    # cleared in the browser - a copied cookie stops working immediately.
    store.bump_session_version()
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
    try:
        store.set_proxies(body.proxies)
    except ValueError as exc:
        # Rejected for pointing at a private/loopback host or an unsupported
        # scheme (anti-SSRF). Tell the admin which entries failed.
        return JSONResponse({"error": str(exc)}, status_code=400)
    return JSONResponse({"proxies": store.list_proxies()})


# --- html -------------------------------------------------------------------

_HEAD = """<!doctype html><html lang=en><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<meta name=robots content="noindex,nofollow">
<title>CloudPull admin</title>
<link rel=preconnect href="https://fonts.googleapis.com">
<link rel=preconnect href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Hanken+Grotesk:wght@400;500;600;700&display=swap" rel=stylesheet>
<style>
:root{--orange:#ff5500;--ink:#16161a;--slate:#6b6b73;--muted:#9a9aa0;--line:#e7e7e3;--paper:#f7f7f5;}
*{box-sizing:border-box}
body{margin:0;background:#f1f1ee;color:var(--ink);
  font-family:'Hanken Grotesk',ui-sans-serif,system-ui,sans-serif;-webkit-font-smoothing:antialiased}
code{font-family:'Space Grotesk',ui-monospace,monospace;background:#f3f3f1;color:var(--orange);
  padding:1.5px 6px;border-radius:5px;font-size:12px}
a{color:var(--orange)}
.head{font-family:'Space Grotesk',sans-serif;font-weight:600;letter-spacing:-.01em}
.mono{font-family:'Space Grotesk',sans-serif}
.tnum{font-variant-numeric:tabular-nums}

/* top bar */
.topbar{height:64px;background:#fff;border-bottom:1px solid #ededea;
  display:flex;align-items:center;justify-content:space-between;padding:0 24px}
.brand{display:flex;align-items:center;gap:10px}
.brand b{font-family:'Space Grotesk',sans-serif;font-weight:600;font-size:18px}
.brand .sub{font-size:13px;color:var(--muted);font-weight:500}
.live{display:flex;align-items:center;gap:7px;font-size:12.5px;color:var(--slate);font-weight:500}
.dot{width:7px;height:7px;border-radius:50%;background:#22a04a;box-shadow:0 0 0 3px rgba(34,160,74,.15)}

/* layout */
.wrap{max-width:1100px;margin:0 auto;padding:24px}
.grid{display:grid;gap:14px}.g4{grid-template-columns:repeat(4,1fr)}
.g2{grid-template-columns:1.45fr 1fr}
@media(max-width:760px){.g4{grid-template-columns:1fr 1fr}.g2{grid-template-columns:1fr}}
.card{background:#fff;border:1px solid var(--line);border-radius:13px;padding:18px}

/* stat cards */
.k{font-size:11.5px;font-weight:600;letter-spacing:.1em;text-transform:uppercase;color:var(--muted)}
.v{font-family:'Space Grotesk',sans-serif;font-weight:600;font-size:32px;letter-spacing:-.02em;
  margin-top:8px;font-variant-numeric:tabular-nums}
.sub{font-size:12px;color:#a6a6ac;margin-top:2px}

/* section titles */
.ct{font-family:'Space Grotesk',sans-serif;font-weight:600;font-size:15px}
.cs{font-size:12.5px;color:var(--muted);margin-top:2px}

/* chart */
.legend{display:flex;align-items:center;gap:16px}
.leg{display:inline-flex;align-items:center;gap:7px;font-size:12.5px;font-weight:600;color:var(--slate)}
.sw{width:10px;height:10px;border-radius:3px}
.plot{display:flex;align-items:stretch}
.yax{width:42px;flex:none;display:flex;flex-direction:column;justify-content:space-between;
  height:208px;padding-bottom:24px;text-align:right}
.yax span{font-size:11px;color:#b4b4ba;font-family:'Space Grotesk',sans-serif}
.bars-area{flex:1;position:relative;height:208px}
.gl{position:absolute;left:0;right:0;height:1px;background:#f0f0ec}
.cols{position:absolute;inset:0;display:flex;align-items:flex-end;justify-content:space-around;padding-bottom:24px}
.col{flex:1;display:flex;flex-direction:column;align-items:center;height:100%;justify-content:flex-end}
.bars{display:flex;align-items:flex-end;gap:5px;height:184px}
.bars i{width:15px;border-radius:5px 5px 0 0;display:block;transition:height .5s cubic-bezier(.2,.7,.2,1)}
.bd{background:linear-gradient(180deg,#ff7a3c,#ff5500)}.bv{background:#3b3b46}
.dl{font-size:11px;color:#a6a6ac;font-weight:600;margin-top:8px;font-family:'Space Grotesk',sans-serif}

/* by format */
.frow{display:flex;align-items:center;gap:12px;margin-bottom:11px}
.fname{width:38px;flex:none;font-family:'Space Grotesk',sans-serif;font-weight:700;font-size:13px}
.ftrack{flex:1;height:9px;border-radius:5px;background:#f1f1ed;overflow:hidden}
.ffill{height:100%;border-radius:5px;background:linear-gradient(90deg,#ff7a3c,#ff5500)}
.fcount{width:54px;flex:none;text-align:right;font-size:13px;font-weight:600;color:var(--slate);
  font-variant-numeric:tabular-nums;font-family:'Space Grotesk',sans-serif}

/* success ring */
.ring{position:relative;width:96px;height:96px;flex:none;border-radius:50%;background:#efe1d8}
.ring-c{position:absolute;inset:11px;background:#fff;border-radius:50%;display:flex;
  align-items:center;justify-content:center;font-family:'Space Grotesk',sans-serif;
  font-weight:600;font-size:23px;letter-spacing:-.02em}
.brk{display:flex;align-items:center;gap:8px;font-size:13px;color:var(--slate)}
.brk b{color:var(--ink);font-family:'Space Grotesk',sans-serif}
.bd9{width:9px;height:9px;border-radius:50%}

/* forms / buttons */
.btn{background:var(--orange);color:#fff;border:0;border-radius:10px;padding:11px 20px;
  font-family:'Hanken Grotesk',sans-serif;font-weight:600;font-size:14px;cursor:pointer}
.btn:hover{background:#f04e00}
.ghost{background:#fff;color:var(--ink);border:1px solid #e4e4e0;padding:8px 15px;
  border-radius:9px;font-weight:600;font-size:13.5px;cursor:pointer;font-family:inherit}
.ghost:hover{background:#f3f3f1}
label{font-size:12.5px;font-weight:600;color:var(--slate)}
input,textarea{width:100%;background:#fafafa;border:1px solid #e4e4e0;border-radius:9px;
  color:var(--ink);padding:11px 12px;font-family:'Hanken Grotesk',sans-serif;font-size:14px;
  margin-top:6px;outline:none}
input:focus,textarea:focus{border-color:var(--orange);background:#fff}
textarea{min-height:104px;resize:vertical;font-family:'Space Grotesk',sans-serif;font-size:13px;line-height:1.7}
.row{margin-bottom:14px}
.ok{color:#1c7a39;font-size:13px;font-weight:600;display:inline-flex;align-items:center;gap:6px}
.err{color:#c2410c;font-size:13px;font-weight:600;margin-top:8px}
.muted{color:var(--muted);font-size:12px}

/* login */
.center{min-height:100vh;display:flex;align-items:center;justify-content:center;padding:24px}
.auth{width:380px}
.logo{width:52px;height:52px;border-radius:14px;background:linear-gradient(150deg,#ff8636,#ff5500);
  display:flex;align-items:center;justify-content:center;margin:0 auto 16px;
  box-shadow:0 6px 18px rgba(255,85,0,.28)}
</style></head><body>"""

_FOOT = "</body></html>"

_ICON = (
    "<svg width=24 height=24 viewBox='0 0 100 100' fill=none>"
    "<path d='M33 60 a14 14 0 0 1 -1 -28 a18 18 0 0 1 34 3 a12 12 0 0 1 1 25' "
    "stroke='#ff5500' stroke-width=9 stroke-linecap=round stroke-linejoin=round/>"
    "<path d='M50 48 L50 74' stroke='#ff5500' stroke-width=9 stroke-linecap=round/>"
    "<path d='M40 65 L50 76 L60 65' stroke='#ff5500' stroke-width=9 stroke-linecap=round stroke-linejoin=round/>"
    "</svg>"
)

_ICON_WHITE = (
    "<svg width=30 height=30 viewBox='8 12 80 80' fill=none>"
    "<path d='M33 60 a14 14 0 0 1 -1 -28 a18 18 0 0 1 34 3 a12 12 0 0 1 1 25' "
    "stroke='#fff' stroke-width=6.4 stroke-linecap=round stroke-linejoin=round/>"
    "<path d='M50 48 L50 74' stroke='#fff' stroke-width=6.4 stroke-linecap=round/>"
    "<path d='M40 65 L50 76 L60 65' stroke='#fff' stroke-width=6.4 stroke-linecap=round stroke-linejoin=round/>"
    "</svg>"
)


def _login_html(error: str = "") -> str:
    err = f"<div class=err style='text-align:center'>{error}</div>" if error else ""
    return (
        _HEAD
        + "<div class=center><div class=auth>"
        + "<div style='text-align:center;margin-bottom:26px'>"
        + f"<div class=logo>{_ICON_WHITE}</div>"
        + "<div class=head style='font-size:21px'>CloudPull admin</div>"
        + "<div class=muted style='margin-top:3px;font-size:13.5px'>Sign in to the analytics console</div>"
        + "</div>"
        + "<div class=card style='padding:24px'>"
        + "<form method=post action='/admin/login'>"
        + "<div class=row><label>Username</label>"
        + "<input name=username autocomplete=username></div>"
        + "<div class=row><label>Password</label>"
        + "<input name=password type=password autocomplete=current-password></div>"
        + "<div class=row><label>2FA code</label>"
        + "<input name=code inputmode=numeric autocomplete=one-time-code placeholder='6 digits' "
        + "style='font-family:Space Grotesk,sans-serif;letter-spacing:.3em'></div>"
        + f"{err}<button class=btn style='width:100%;margin-top:6px'>Sign in</button>"
        + "</form></div>"
        + "<div class=muted style='text-align:center;margin-top:16px'>"
        + "Protected area · not affiliated with SoundCloud</div>"
        + "</div></div>"
        + _FOOT
    )


_SETUP_HTML = (
    _HEAD
    + "<div class=center><div class=auth>"
    + "<div style='text-align:center;margin-bottom:26px'>"
    + f"<div class=logo>{_ICON_WHITE}</div>"
    + "<div class=head style='font-size:21px'>CloudPull admin</div>"
    + "<div class=muted style='margin-top:3px;font-size:13.5px'>First-time setup</div></div>"
    + "<div class=card style='padding:24px'>"
    + "<p style='margin:0 0 10px'>No admin account yet. On the server, run:</p>"
    + "<p style='margin:0 0 10px'><code>python -m api.admin_setup</code></p>"
    + "<p class=muted style='line-height:1.5'>It sets your username/password and shows a QR code "
    + "for 2FA. Then refresh this page.</p>"
    + "</div></div></div>"
    + _FOOT
)


# Raw string so the JS template literals (${...}) and the \n in the proxy
# split/join pass through to the browser unchanged.
_DASHBOARD_HTML = (
    _HEAD
    + r"""<div class=topbar>
  <div class=brand>""" + _ICON + r"""<b>CloudPull</b><span class=sub>Analytics</span></div>
  <div style="display:flex;align-items:center;gap:14px">
    <div class=live><span class=dot></span>Live · refreshes 30s</div>
    <form method=post action='/admin/logout'><button class=ghost>Log out</button></form>
  </div>
</div>
<div class=wrap>

  <div class="grid g4">
    <div class=card><div class=k>Visits total</div><div class=v tnum id=vt>-</div><div class=sub>all time</div></div>
    <div class=card><div class=k>Visits 24h</div><div class=v tnum id=v24>-</div><div class=sub>last 24 hours</div></div>
    <div class=card><div class=k>Downloads total</div><div class=v tnum id=dt>-</div><div class=sub>all time</div></div>
    <div class=card><div class=k>Downloads 24h</div><div class=v tnum id=d24>-</div><div class=sub>last 24 hours</div></div>
  </div>

  <div class=card style="margin-top:14px;padding:22px 24px 18px">
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:20px">
      <div><div class=ct>Last 7 days</div><div class=cs>Visits and completed downloads per day</div></div>
      <div class=legend>
        <span class=leg><span class=sw style="background:#ff5500"></span>Downloads</span>
        <span class=leg><span class=sw style="background:#3b3b46"></span>Visits</span>
      </div>
    </div>
    <div class=plot>
      <div class=yax><span id=ymax>-</span><span id=ymid>-</span><span>0</span></div>
      <div class=bars-area>
        <div class=gl style="top:0"></div><div class=gl style="top:92px"></div>
        <div class=gl style="top:184px;background:#ededea"></div>
        <div class=cols id=chart></div>
      </div>
    </div>
  </div>

  <div class="grid g2" style="margin-top:14px">
    <div class=card style="padding:20px 22px">
      <div class=ct style="margin-bottom:16px">By format</div>
      <div id=fmt></div>
    </div>
    <div class=card style="padding:20px 22px;display:flex;flex-direction:column">
      <div class=ct style="margin-bottom:14px">Success rate</div>
      <div style="display:flex;align-items:center;gap:18px;flex:1">
        <div class=ring id=ring><div class=ring-c id=sr>-</div></div>
        <div>
          <div class=brk style="margin-bottom:8px"><span class=bd9 style="background:#ff5500"></span><span><b id=okc>-</b> succeeded</span></div>
          <div class=brk><span class=bd9 style="background:#e3a0a0"></span><span><b id=failc>-</b> failed</span></div>
        </div>
      </div>
    </div>
  </div>

  <div class=card style="margin-top:14px;padding:20px 22px">
    <div style="display:flex;align-items:baseline;justify-content:space-between;gap:16px;margin-bottom:6px">
      <div class=ct>Proxies</div><div class=muted id=pcount></div>
    </div>
    <p style="margin:0 0 12px;font-size:13px;line-height:1.5;color:#8a8a92">One per line. Used to spread
      downloads across IPs and avoid rate limits. Format <code>http://user:pass@host:port</code>
      or <code>socks5://host:port</code></p>
    <textarea id=proxies placeholder="http://user:pass@1.2.3.4:8080"></textarea>
    <div style="display:flex;align-items:center;gap:14px;margin-top:12px">
      <button class=btn id=saveproxies>Save proxies</button>
      <span id=psaved></span>
    </div>
  </div>

</div>
<script>
const nf=n=>Number(n).toLocaleString('en-US');
const WD=['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];

async function load(){
  const s=await (await fetch('/admin/api/stats')).json();
  vt.textContent=nf(s.visits_total);  v24.textContent=nf(s.visits_24h);
  dt.textContent=nf(s.downloads_total);  d24.textContent=nf(s.downloads_24h);

  // success ring
  const rate=s.success_rate;
  sr.textContent=rate+'%';
  const deg=Math.round(rate/100*360);
  ring.style.background=`conic-gradient(#ff5500 ${deg}deg,#efe1d8 ${deg}deg)`;
  okc.textContent=nf(s.downloads_total);  failc.textContent=nf(s.downloads_failed);

  // chart
  const PLOT=184;
  const raw=Math.max(1,...s.daily.flatMap(d=>[d.visits,d.downloads]));
  const yMax=Math.max(500,Math.ceil(raw/500)*500);
  ymax.textContent=nf(yMax);  ymid.textContent=nf(yMax/2);
  const today=new Date();
  chart.innerHTML=s.daily.map((d,i)=>{
    const lab=WD[new Date(today.getTime()-(s.daily.length-1-i)*864e5).getDay()];
    const dh=Math.round(d.downloads/yMax*PLOT), vh=Math.round(d.visits/yMax*PLOT);
    return `<div class=col><div class=bars><i class=bd style="height:${dh}px"></i>`
      +`<i class=bv style="height:${vh}px"></i></div><span class=dl>${lab}</span></div>`;
  }).join('');

  // by format
  const ents=Object.entries(s.by_format);
  if(ents.length){
    const mx=Math.max(...ents.map(e=>e[1]));
    fmt.innerHTML=ents.map(([k,v])=>`<div class=frow><span class=fname>${k}</span>`
      +`<div class=ftrack><div class=ffill style="width:${Math.round(v/mx*100)}%"></div></div>`
      +`<span class=fcount>${nf(v)}</span></div>`).join('');
  }else{
    fmt.innerHTML='<div class=muted>No downloads yet</div>';
  }
}

async function loadProxies(){
  const p=await (await fetch('/admin/api/proxies')).json();
  const list=p.proxies||[];
  proxies.value=list.join('\n');
  pcount.textContent=list.length+' active';
}

saveproxies.onclick=async()=>{
  const lines=proxies.value.split('\n').map(x=>x.trim()).filter(Boolean);
  const r=await fetch('/admin/api/proxies',{method:'POST',
    headers:{'Content-Type':'application/json'},body:JSON.stringify({proxies:lines})});
  const el=document.getElementById('psaved');
  if(r.ok){el.className='ok';el.innerHTML='<svg width=15 height=15 viewBox="0 0 24 24" fill=none '
    +'stroke="#1c7a39" stroke-width=3 stroke-linecap=round stroke-linejoin=round>'
    +'<path d="m5 12 5 5L20 7"/></svg>Saved';
    pcount.textContent=lines.length+' active';
    setTimeout(()=>{el.textContent='';el.className='';},2200);}
  else{const j=await r.json().catch(()=>({}));el.className='err';
    el.textContent=j.error?('Rejected: '+j.error):'Error';
    setTimeout(()=>{el.textContent='';el.className='';},7000);}
};

load();loadProxies();setInterval(load,30000);
</script>"""
    + _FOOT
)
