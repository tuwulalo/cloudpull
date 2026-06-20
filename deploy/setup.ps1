# CloudPull one-shot installer for a Windows VPS.
#
# Run in an ADMINISTRATOR PowerShell on the VPS:
#   irm https://raw.githubusercontent.com/tuwulalo/cloudpull/main/deploy/setup.ps1 | iex
#
# Installs Node, Python, ffmpeg and Caddy, clones the repo, builds the app, and
# runs the API + web + bot + reverse proxy as auto-start Scheduled Tasks (SYSTEM,
# survive reboot/logoff). Safe to re-run to update. Asks for the bot token once
# and stores it in C:\cloudpull\.env (never committed). No NSSM dependency.

$ErrorActionPreference = 'Stop'
$Root  = 'C:\cloudpull'
$Repo  = 'https://github.com/tuwulalo/cloudpull.git'
$Bin   = Join-Path $Root 'bin'

function Step($m) { Write-Host "`n==== $m ====" -ForegroundColor Cyan }
function RefreshPath {
  $env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' +
              [Environment]::GetEnvironmentVariable('Path', 'User')
}

$isAdmin = ([Security.Principal.WindowsPrincipal] `
  [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
  [Security.Principal.WindowsBuiltinRole]::Administrator)
if (-not $isAdmin) { Write-Error 'Please run this in an Administrator PowerShell window.'; return }

New-Item -ItemType Directory -Force -Path $Bin | Out-Null

Step 'Installing prerequisites via winget'
foreach ($p in 'Git.Git', 'OpenJS.NodeJS.LTS', 'Python.Python.3.12', 'Gyan.FFmpeg') {
  Write-Host "  $p ..."
  winget install -e --id $p --accept-source-agreements --accept-package-agreements --silent
}
RefreshPath

Step 'Making ffmpeg available to background services'
# Copy ffmpeg next to the app and put it on the Machine PATH, so SYSTEM-run
# tasks (and yt-dlp) can find it regardless of the installing user's PATH.
foreach ($tool in 'ffmpeg', 'ffprobe') {
  $src = (Get-Command $tool -ErrorAction SilentlyContinue).Source
  $dst = Join-Path $Bin "$tool.exe"
  # Skip if it already resolves to our bin copy (avoids copy-onto-itself on re-run).
  if ($src -and ($src -ine $dst)) { Copy-Item $src $dst -Force }
}
$machinePath = [Environment]::GetEnvironmentVariable('Path', 'Machine')
if ($machinePath -notlike "*$Bin*") {
  [Environment]::SetEnvironmentVariable('Path', "$machinePath;$Bin", 'Machine')
}
RefreshPath

Step 'Fetching Caddy'
if (-not (Test-Path "$Bin\caddy.exe")) {
  Invoke-WebRequest -Uri 'https://caddyserver.com/api/download?os=windows&arch=amd64' -OutFile "$Bin\caddy.exe"
}
$caddy = "$Bin\caddy.exe"

Step 'Getting the code'
# Robust against any prior state: no dir, dir with files but no repo, a bare
# .git from a failed run, or a full clone. Avoids `2>$null` on git (which turns
# native stderr into a terminating error under ErrorActionPreference=Stop).
if (-not (Test-Path (Join-Path $Root '.git'))) { git -C $Root init }
if ((git -C $Root remote) -contains 'origin') {
  git -C $Root remote set-url origin $Repo
} else {
  git -C $Root remote add origin $Repo
}
git -C $Root fetch --depth 1 origin main
git -C $Root checkout -f -B main origin/main

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

Step 'Installing auto-start services (Scheduled Tasks, run as SYSTEM)'
$node      = (Get-Command node).Source
$nextBin   = Join-Path $Root 'web\node_modules\next\dist\bin\next'
$caddyfile = Join-Path $Root 'deploy\Caddyfile'

function Set-Svc($name, $exe, $svcArgs, $dir) {
  Unregister-ScheduledTask -TaskName $name -Confirm:$false -ErrorAction SilentlyContinue
  $action    = New-ScheduledTaskAction -Execute $exe -Argument $svcArgs -WorkingDirectory $dir
  $trigger   = New-ScheduledTaskTrigger -AtStartup
  $principal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
  $settings  = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
                 -StartWhenAvailable -ExecutionTimeLimit ([TimeSpan]::Zero) `
                 -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1)
  Register-ScheduledTask -TaskName $name -Action $action -Trigger $trigger `
                 -Principal $principal -Settings $settings | Out-Null
  Start-ScheduledTask -TaskName $name
}

Set-Svc 'cloudpull-api'   $py    '-m uvicorn api.main:app --host 127.0.0.1 --port 8000' $Root
Set-Svc 'cloudpull-web'   $node  "$nextBin start -H 127.0.0.1 -p 3000" (Join-Path $Root 'web')
Set-Svc 'cloudpull-bot'   $py    '-m bot.main' $Root
Set-Svc 'cloudpull-caddy' $caddy "run --config $caddyfile" $Root

Step 'Opening firewall (80/443)'
foreach ($port in 80, 443) {
  if (-not (Get-NetFirewallRule -DisplayName "CloudPull $port" -ErrorAction SilentlyContinue)) {
    New-NetFirewallRule -DisplayName "CloudPull $port" -Direction Inbound -Protocol TCP -LocalPort $port -Action Allow | Out-Null
  }
}

Step 'Installing watchdog (health check every 2 min)'
$wdAction = New-ScheduledTaskAction -Execute 'powershell.exe' `
  -Argument "-NoProfile -ExecutionPolicy Bypass -File $Root\deploy\watchdog.ps1"
$wdTrigger = New-ScheduledTaskTrigger -Once -At (Get-Date)
$wdTrigger.Repetition = (New-ScheduledTaskTrigger -Once -At (Get-Date) `
  -RepetitionInterval (New-TimeSpan -Minutes 2) `
  -RepetitionDuration (New-TimeSpan -Days 3650)).Repetition
$wdPrincipal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
$wdSettings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName 'cloudpull-watchdog' -Action $wdAction -Trigger $wdTrigger `
  -Principal $wdPrincipal -Settings $wdSettings -Force | Out-Null

Start-Sleep -Seconds 6
Step 'Status'
foreach ($s in 'cloudpull-api', 'cloudpull-web', 'cloudpull-bot', 'cloudpull-caddy') {
  $state = (Get-ScheduledTask -TaskName $s -ErrorAction SilentlyContinue).State
  Write-Host ("  {0,-18} {1}" -f $s, $state)
}
Write-Host 'Listening ports:'
Get-NetTCPConnection -State Listen -LocalPort 80, 443, 3000, 8000 -ErrorAction SilentlyContinue |
  Select-Object -ExpandProperty LocalPort | Sort-Object -Unique | ForEach-Object { Write-Host "  $_" }

Write-Host "`nAll set. Open https://cloudpull.cloud" -ForegroundColor Green
Write-Host 'Caddy issues the TLS certificate automatically on the first request (DNS already points here).' -ForegroundColor Green
Write-Host "`nSECURITY: now rotate the Administrator password and the bot token." -ForegroundColor Yellow
