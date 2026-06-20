# CloudPull updater for the VPS. Pulls the latest code, refreshes deps, rebuilds
# the web app, and restarts all services. Run in Administrator PowerShell:
#   irm https://raw.githubusercontent.com/tuwulalo/cloudpull/main/deploy/update.ps1 | iex

$ErrorActionPreference = 'Stop'
$Root = 'C:\cloudpull'
function Step($m) { Write-Host "`n==== $m ====" -ForegroundColor Cyan }

Step 'Pulling latest code'
git -C $Root fetch --depth 1 origin main
git -C $Root checkout -f -B main origin/main

Step 'Python deps'
& (Join-Path $Root '.venv\Scripts\python.exe') -m pip install -r (Join-Path $Root 'requirements.txt')

# Stop the web service first: a running `next start` locks node_modules and
# .next, which makes `npm ci` fail with EPERM while it wipes node_modules.
Step 'Stopping web for a clean rebuild'
Stop-ScheduledTask -TaskName cloudpull-web -ErrorAction SilentlyContinue
Start-Sleep -Seconds 3

Step 'Rebuilding web'
Push-Location (Join-Path $Root 'web')
npm ci
npm run build
Pop-Location

Step 'Restarting services'
foreach ($s in 'cloudpull-api', 'cloudpull-web', 'cloudpull-bot', 'cloudpull-caddy') {
  Stop-ScheduledTask -TaskName $s -ErrorAction SilentlyContinue
  Start-ScheduledTask -TaskName $s
  Write-Host ("  {0,-18} {1}" -f $s, (Get-ScheduledTask -TaskName $s -ErrorAction SilentlyContinue).State)
}
Write-Host "`nUpdated. https://cloudpull.cloud" -ForegroundColor Green
