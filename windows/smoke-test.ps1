# Starts the app, builds a mission through its API, fetches the print pack and the Settings
# page, then stops it. Used by CI for python -m app, the built .exe and the installed .exe:
#     ./windows/smoke-test.ps1 -Command "dist\DCS Mission Maker\DCS Mission Maker.exe" -Arguments "--no-tray", "--background"
param(
    [Parameter(Mandatory)] [string] $Command,
    [string[]] $Arguments = @(),
    [int] $Port = 8080
)
$ErrorActionPreference = "Stop"
$data = Join-Path $env:RUNNER_TEMP ("dmm-" + [guid]::NewGuid())
$env:DATA_DIR = $data
$env:OUTPUT_DIR = Join-Path $data "missions"
$base = "http://127.0.0.1:$Port"

$app = Start-Process $Command -ArgumentList $Arguments -PassThru -NoNewWindow
try {
    $health = $null
    foreach ($i in 1..60) {
        try { $health = Invoke-RestMethod "$base/healthz" -TimeoutSec 5; break } catch { Start-Sleep 2 }
    }
    if (-not $health) { throw "the app didn't start" }
    Write-Output "running: $($health.app) $($health.version)"
    $body = '{"theater": "syria", "mission_type": "sead", "flights": [{"aircraft": "F-16C_50", "slots": 2}], "scripts": ["skynet"]}'
    $r = Invoke-RestMethod "$base/api/generate" -Method Post -Body $body -ContentType application/json -TimeoutSec 180
    Write-Output "built $($r.filename), $($r.size) bytes"
    $stem = $r.filename -replace '\.miz$', ''
    Invoke-WebRequest "$base/missions/$stem/pack.pdf" -UseBasicParsing -TimeoutSec 120 | Out-Null
    Invoke-WebRequest "$base/settings" -UseBasicParsing -TimeoutSec 30 | Out-Null
    Write-Output "print pack and Settings page OK"
}
finally {
    Stop-Process $app.Id -ErrorAction SilentlyContinue
    $log = Join-Path $data "logs\app.log"
    if (Test-Path $log) { Get-Content $log -Tail 8 }
}
exit 0
