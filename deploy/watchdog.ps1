# CloudPull watchdog. Restarts a local service if its health check fails or its
# task is not running. Registered to run every ~2 minutes (see setup.ps1). This
# catches "alive but hung" processes that plain crash-restart does not.

function Test-Up($url) {
    try {
        return ((Invoke-WebRequest -Uri $url -TimeoutSec 6 -UseBasicParsing).StatusCode -lt 500)
    } catch {
        return $false
    }
}

function Restart-Svc($name) {
    try { Stop-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue } catch {}
    Start-Sleep -Seconds 2
    try { Start-ScheduledTask -TaskName $name } catch {}
}

function Ensure-Running($name) {
    $t = Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
    if ($t -and $t.State -ne 'Running') {
        try { Start-ScheduledTask -TaskName $name } catch {}
    }
}

if (-not (Test-Up 'http://127.0.0.1:8000/api/health')) { Restart-Svc 'cloudpull-api' }
if (-not (Test-Up 'http://127.0.0.1:3000/'))           { Restart-Svc 'cloudpull-web' }
if (-not (Test-Up 'http://127.0.0.1:80'))              { Restart-Svc 'cloudpull-caddy' }
Ensure-Running 'cloudpull-bot'
