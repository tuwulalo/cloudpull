# Deploying CloudPull to a Windows VPS (cloudpull.cloud)

This runs the whole stack on one Windows VPS behind Caddy (automatic HTTPS):

```
                      cloudpull.cloud  (Caddy :80/:443, HTTPS)
                       /                         \
        / (everything)                            /api/*
   Next.js landing :3000                  FastAPI backend :8000
                                          (yt-dlp + ffmpeg)
   Telegram bot (long polling, no public port needed)
```

The bot does not need the domain; it talks to Telegram directly.

> Security note: do the steps that require typing the Administrator password
> (RDP login) and the domain account (DNS) yourself. Rotate the VPS password
> after first login if it was ever shared in plain text.

---

## Quick install (one command)

DNS is already pointing at the server. RDP into the VPS, open an
**Administrator PowerShell**, and run:

```powershell
irm https://raw.githubusercontent.com/tuwulalo/cloudpull/main/deploy/setup.ps1 | iex
```

This installs everything, builds the app, and runs the API, web, bot and Caddy
reverse proxy as auto-start services. It asks for the bot token once. When it
finishes, open `https://cloudpull.cloud`.

The manual, step-by-step version of the same thing is below.

---

## 1. DNS on Spaceship

In the Spaceship dashboard for `cloudpull.cloud`, open **Advanced DNS** and add:

| Type  | Host | Value           | TTL  |
| ----- | ---- | --------------- | ---- |
| A     | `@`  | `89.144.53.253` | Auto |
| A     | `www`| `89.144.53.253` | Auto |

Remove any default parking / forwarding records. DNS can take a few minutes to
a couple of hours to propagate. You do not need the Spaceship hosting/email
upsells, the VPS does the hosting.

---

## 2. Connect to the VPS

Remote Desktop to `89.144.53.253:3389` as `Administrator`. (Windows: open
"Remote Desktop Connection", enter the address, then your credentials.)

Open **PowerShell as Administrator** for the rest.

---

## 3. Install prerequisites

```powershell
winget install -e --id Git.Git
winget install -e --id OpenJS.NodeJS.LTS
winget install -e --id Python.Python.3.12
winget install -e --id Gyan.FFmpeg
winget install -e --id CaddyServer.Caddy
winget install -e --id NSSM.NSSM
```

Close and reopen PowerShell so the new PATH entries load. Verify:

```powershell
git --version; node --version; python --version; ffmpeg -version; caddy version
```

---

## 4. Get the code

```powershell
cd C:\
git clone https://github.com/tuwulalo/cloudpull.git
cd C:\cloudpull
```

## 5. Backend (FastAPI core)

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## 6. Bot token

Create `C:\cloudpull\.env` (it is gitignored, never commit it):

```
BOT_TOKEN=<your fresh token from @BotFather>
```

## 7. Frontend (build)

The production URLs come from the committed `web/.env.production`
(`https://cloudpull.cloud`), so a plain build is correct on the server:

```powershell
cd C:\cloudpull\web
npm ci
npm run build
cd C:\cloudpull
```

---

## 8. Run the three processes as services (NSSM)

```powershell
# FastAPI on :8000
nssm install cloudpull-api "C:\cloudpull\.venv\Scripts\python.exe" "-m uvicorn api.main:app --host 127.0.0.1 --port 8000"
nssm set cloudpull-api AppDirectory C:\cloudpull
nssm start cloudpull-api

# Next.js landing on :3000
nssm install cloudpull-web "C:\Program Files\nodejs\npm.cmd" "run start"
nssm set cloudpull-web AppDirectory C:\cloudpull\web
nssm set cloudpull-web AppEnvironmentExtra PORT=3000
nssm start cloudpull-web

# Telegram bot (long polling)
nssm install cloudpull-bot "C:\cloudpull\.venv\Scripts\python.exe" "-m bot.main"
nssm set cloudpull-bot AppDirectory C:\cloudpull
nssm start cloudpull-bot
```

Check they are running: `nssm status cloudpull-api` (and `-web`, `-bot`).

---

## 9. Reverse proxy + HTTPS (Caddy)

```powershell
nssm install cloudpull-caddy "caddy.exe" "run --config C:\cloudpull\deploy\Caddyfile"
nssm set cloudpull-caddy AppDirectory C:\cloudpull
nssm start cloudpull-caddy
```

## 10. Firewall

```powershell
New-NetFirewallRule -DisplayName "HTTP"  -Direction Inbound -Protocol TCP -LocalPort 80  -Action Allow
New-NetFirewallRule -DisplayName "HTTPS" -Direction Inbound -Protocol TCP -LocalPort 443 -Action Allow
```

---

## 11. Verify

Once DNS has propagated, open `https://cloudpull.cloud`. Caddy obtains the TLS
certificate automatically on the first request. Test a real download, and
message the Telegram bot.

If `https` fails at first: confirm DNS resolves to `89.144.53.253`, ports 80/443
are open, and check `nssm status cloudpull-caddy` plus the Caddy logs.

---

## 12. Updating later

```powershell
cd C:\cloudpull
git pull
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
cd web; npm ci; npm run build; cd ..
nssm restart cloudpull-api
nssm restart cloudpull-web
nssm restart cloudpull-bot
```

---

## Notes and limitations

- A public downloader uses bandwidth and sits in a legal grey area. Keep the
  Privacy & Acceptable Use page (`/privacy`) visible and use it responsibly.
- The backend writes temporary files under `downloads/`. For a long-running
  public service, add a scheduled task to clear old job folders so the disk
  does not fill up.
- A Linux VPS (nginx/Caddy + systemd) is a smoother host for this stack if you
  ever switch; the app code is identical.
