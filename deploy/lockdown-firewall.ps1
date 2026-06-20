# Restrict inbound HTTP/HTTPS (80/443) to Cloudflare's edge ranges only.
#
# After cloudpull.cloud went behind Cloudflare (proxied/orange), all legitimate
# web traffic reaches the origin FROM Cloudflare. Locking 80/443 to Cloudflare's
# published ranges hides the origin (89.144.53.253) and blocks direct-to-origin
# DDoS / scanning that bypasses Cloudflare. RDP (3389) and everything else are
# untouched.
#
# Run on the VPS as Administrator:
#   powershell -ExecutionPolicy Bypass -File C:\cloudpull\deploy\lockdown-firewall.ps1
#
# ROLLBACK (re-open 80/443 to everyone, e.g. if you ever move off Cloudflare):
#   Set-NetFirewallRule -DisplayName 'CloudPull 80','CloudPull 443' -RemoteAddress Any
#
# Note: this does NOT affect Let's Encrypt renewal. Caddy renews via HTTP-01,
# which Let's Encrypt validates against the public hostname -> Cloudflare edge ->
# proxied to the origin from a Cloudflare IP (allowed here). Refresh these ranges
# if Cloudflare ever publishes new ones: https://www.cloudflare.com/ips

$ErrorActionPreference = 'Stop'

# Cloudflare edge ranges (v4 + v6). Source: cloudflare.com/ips-v4 + /ips-v6 (2026-06-21).
$cf = @(
  '173.245.48.0/20','103.21.244.0/22','103.22.200.0/22','103.31.4.0/22','141.101.64.0/18',
  '108.162.192.0/18','190.93.240.0/20','188.114.96.0/20','197.234.240.0/22','198.41.128.0/17',
  '162.158.0.0/15','104.16.0.0/13','104.24.0.0/14','172.64.0.0/13','131.0.72.0/22',
  '2400:cb00::/32','2606:4700::/32','2803:f800::/32','2405:b500::/32','2405:8100::/32',
  '2a06:98c0::/29','2c0f:f248::/32'
)

foreach ($name in 'CloudPull 80','CloudPull 443') {
  if (Get-NetFirewallRule -DisplayName $name -ErrorAction SilentlyContinue) {
    Set-NetFirewallRule -DisplayName $name -RemoteAddress $cf
    Write-Host "Restricted '$name' to Cloudflare ranges." -ForegroundColor Green
  } else {
    Write-Host "Rule '$name' not found - creating it, restricted to Cloudflare." -ForegroundColor Yellow
    $port = if ($name -match '443') { 443 } else { 80 }
    New-NetFirewallRule -DisplayName $name -Direction Inbound -Protocol TCP -LocalPort $port -Action Allow -RemoteAddress $cf | Out-Null
  }
}

Write-Host "`nVerifying remote scope on 80/443 rules:" -ForegroundColor Cyan
foreach ($name in 'CloudPull 80','CloudPull 443') {
  $ra = (Get-NetFirewallRule -DisplayName $name | Get-NetFirewallAddressFilter).RemoteAddress
  Write-Host ("  {0}: {1} ranges" -f $name, @($ra).Count)
}

# Surface any OTHER inbound allow rule that still exposes 80/443 to the world,
# so a forgotten open rule can't silently defeat this lockdown.
Write-Host "`nOther inbound allow rules touching 80/443 (review if any 'Any'):" -ForegroundColor Cyan
$others = Get-NetFirewallRule -Direction Inbound -Action Allow -Enabled True |
  Where-Object { $_.DisplayName -notin 'CloudPull 80','CloudPull 443' } |
  Where-Object {
    $lp = ($_ | Get-NetFirewallPortFilter -ErrorAction SilentlyContinue).LocalPort
    $lp -and (($lp -contains '80') -or ($lp -contains '443'))
  }
if ($others) {
  $others | ForEach-Object {
    $ra = ($_ | Get-NetFirewallAddressFilter).RemoteAddress
    Write-Host ("  [!] {0}  remote={1}" -f $_.DisplayName, ($ra -join ',')) -ForegroundColor Yellow
  }
} else {
  Write-Host "  none - good." -ForegroundColor Green
}

Write-Host "`nDone. Origin 80/443 now accept Cloudflare only. RDP (3389) untouched." -ForegroundColor Green
Write-Host "Test: https://cloudpull.cloud should work; direct http://89.144.53.253 should time out." -ForegroundColor Green
