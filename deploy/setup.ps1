# CloudPull one-shot installer for a Windows VPS.
#
# Run in an ADMINISTRATOR PowerShell on the VPS:
#   irm https://raw.githubusercontent.com/tuwulalo/cloudpull/main/deploy/setup.ps1 | iex
#
# It installs Node, Python, ffmpeg, Caddy and NSSM, clones the repo, builds the
# app, and runs the API + web + bot + reverse proxy as auto-start services.
# Safe to re-run to update (git pull + rebuild + restart). It asks for the bot
# token only once and stores it in C:\cloudpull\.env (never committed).

$ErrorActionPreference = 'Stop'
$Root  = 'C:\cloudpull'
$Repo  = 'https://github.com/tuwulalo/cloudpull.git'
$Bin   = Join-Path $Root 'bin'

function Step($m) { Write-Host "`n==== $m ====" -ForegroundColor Cyan }
function RefreshPath {
  $env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' +
              [Environment]::GetEnvironmentVariable('Path', 'User')
}

# --- must be admin ---
$isAdmin = ([Security.Principal.WindowsPrincipal] `
  [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
  [Security.Principal.WindowsBuiltinRole]::Administrator)
if (-not $isAdmin) {
  Write-Error 'Please run this in an Administrator PowerShell window.'
  return
}

Step 'Installing prerequisites via winget'
foreach ($p in 'Git.Git', 'OpenJS.NodeJS.LTS', 'Python.Python.3.12', 'Gyan.FFmpeg') {
  Write-Host "  $p ..."
  winget install -e --id $p --accept-source-agreements --accept-package-agreements --silent
}
RefreshPath

Step 'Fetching Caddy + NSSM'
New-Item -ItemType Directory -Force -Path $Bin | Out-Null
if (-not (Test-Path "$Bin\caddy.exe")) {
  Invoke-WebRequest -Uri 'https://caddyserver.com/api/download?os=windows&arch=amd64' -OutFile "$Bin\caddy.exe"
}
if (-not (Test-Path "$Bin\nssm.exe")) {
  $zip = Join-Path $env:TEMP 'nssm.zip'
  $dst = Join-Path $env:TEMP 'nssm'
  Invoke-WebRequest -Uri 'https://nssm.cc/release/nssm-2.24.zip' -OutFile $zip
  Expand-Archive -Path $zip -DestinationPath $dst -Force
  Copy-Item (Join-Path $dst 'nssm-2.24\win64\nssm.exe') "$Bin\nssm.exe" -Force
}
$nssm  = "$Bin\nssm.exe"
$caddy = "$Bin\caddy.exe"

Step 'Getting the code'
if (Test-Path (Join-Path $Root '.git')) {
  git -C $Root pull
} else {
  git clone $Repo $Root
}

Step 'Python backend (venv + deps)'
$py = Join-Path $Root '.venv\Scripts\python.exe'
if (-not (Test-Path $py)) { python -m venv (Join-Path $Root '.venv') }
& $py -m pip install --upgrade pip
& $py -m pip install -r (Join-Path $Root 'requirements.txt')

Step 'Bot token'
$envFile = Join-Path $Root '.env'
if (-not (Test-Path $envFile)) {
  $tok = Read-Host 'Paste a FRESH Telegram bot token from @BotFather'
  "BOT_TOKEN=$($tok.Trim())" | Out-File -FilePath $envFile -Encoding ascii
  Write-Host '  saved to C:\cloudpull\.env (gitignored)'
} else {
  Write-Host '  .env already exists, keeping it'
}

Step 'Building the web app'
Push-Location (Join-Path $Root 'web')
npm ci
npm run build
Pop-Location

Step 'Installing services (NSSM)'
$node    = (Get-Command node).Source
$nextBin = Join-Path $Root 'web\node_modules\next\dist\bin\next'
$caddyfile = Join-Path $Root 'deploy\Caddyfile'

function Set-Svc($name, $exe, $svcArgs, $dir) {
  & $nssm stop $name 2>$null | Out-Null
  & $nssm remove $name confirm 2>$null | Out-Null
  & $nssm install $name $exe | Out-Null
  & $nssm set $name AppParameters $svcArgs | Out-Null
  & $nssm set $name AppDirectory $dir | Out-Null
  & $nssm set $name Start SERVICE_AUTO_START | Out-Null
  & $nssm set $name AppStdout (Join-Path $Root "logs\$name.log") | Out-Null
  & $nssm set $name AppStderr (Join-Path $Root "logs\$name.log") | Out-Null
  & $nssm start $name | Out-Null
}

New-Item -ItemType Directory -Force -Path (Join-Path $Root 'logs') | Out-Null
Set-Svc 'cloudpull-api'   $py    '-m uvicorn api.main:app --host 127.0.0.1 --port 8000' $Root
Set-Svc 'cloudpull-web'   $node  "$nextBin start -p 3000" (Join-Path $Root 'web')
Set-Svc 'cloudpull-bot'   $py    '-m bot.main' $Root
Set-Svc 'cloudpull-caddy' $caddy "run --config $caddyfile" $Root

Step 'Opening firewall (80/443)'
foreach ($port in 80, 443) {
  if (-not (Get-NetFirewallRule -DisplayName "CloudPull $port" -ErrorAction SilentlyContinue)) {
    New-NetFirewallRule -DisplayName "CloudPull $port" -Direction Inbound -Protocol TCP -LocalPort $port -Action Allow | Out-Null
  }
}

Step 'Status'
foreach ($s in 'cloudpull-api', 'cloudpull-web', 'cloudpull-bot', 'cloudpull-caddy') {
  Write-Host ("  {0,-18} {1}" -f $s, (& $nssm status $s))
}

Write-Host "`nAll set. Open https://cloudpull.cloud" -ForegroundColor Green
Write-Host 'Caddy issues the TLS certificate automatically on the first request (DNS already points here).' -ForegroundColor Green
Write-Host "`nSECURITY: now rotate the Administrator password and the bot token." -ForegroundColor Yellow
