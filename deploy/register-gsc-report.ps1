# Register the weekly Google Search Console report as a Windows Scheduled Task.
# Runs scripts/gsc_report.py every Monday 09:00 as SYSTEM, which builds the
# report and (if GSC_REPORT_CHAT_ID is set) sends it to Telegram via the bot.
#
# Prereqs (one-time, see SEO.md "Auto GSC reports"):
#   1. pip install -r requirements.txt   (adds google-api-python-client, google-auth)
#   2. Put the service-account key at C:\cloudpull\data\gsc-sa.json
#   3. In C:\cloudpull\.env set:
#        GSC_SA_JSON=C:\cloudpull\data\gsc-sa.json
#        GSC_REPORT_CHAT_ID=<your Telegram chat id>   (find it: python scripts\gsc_report.py --whoami)
#
# Run on the VPS as Administrator:
#   powershell -ExecutionPolicy Bypass -File C:\cloudpull\deploy\register-gsc-report.ps1

$ErrorActionPreference = 'Stop'
$Root = 'C:\cloudpull'
$py = Join-Path $Root '.venv\Scripts\python.exe'
$script = Join-Path $Root 'scripts\gsc_report.py'

if (-not (Test-Path $py))     { throw "Python venv not found at $py" }
if (-not (Test-Path $script)) { throw "Report script not found at $script (git pull first)" }

$action = New-ScheduledTaskAction -Execute $py -Argument "`"$script`"" -WorkingDirectory $Root
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At 9:00AM
$principal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

Register-ScheduledTask -TaskName 'cloudpull-gsc-report' -Action $action -Trigger $trigger `
  -Principal $principal -Settings $settings -Force | Out-Null

Write-Host "Registered 'cloudpull-gsc-report' (Mondays 09:00)." -ForegroundColor Green
Write-Host "Test it now with:" -ForegroundColor Cyan
Write-Host "  Start-ScheduledTask -TaskName cloudpull-gsc-report" -ForegroundColor Cyan
Write-Host "  (or run directly: $py `"$script`")" -ForegroundColor Cyan
