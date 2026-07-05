# One-glance health check: are the servers up, and is the database healthy?
#
#   pwsh scripts\health.ps1

$ErrorActionPreference = "SilentlyContinue"

function Test-Port($port) {
    $null -ne (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue)
}

Write-Host ""
Write-Host "FORLAS CRQ — health" -ForegroundColor Cyan
Write-Host "----------------------"

# Backend
$backendUp = Test-Port 8765
if ($backendUp) {
    try {
        $r = Invoke-RestMethod -Uri "http://127.0.0.1:8765/api/health" -TimeoutSec 3
        Write-Host ("  Backend   : UP    ({0} v{1})" -f $r.name, $r.version) -ForegroundColor Green
    } catch {
        Write-Host "  Backend   : PORT OPEN but /api/health not responding" -ForegroundColor Yellow
    }
} else {
    Write-Host "  Backend   : DOWN  (port 8765)" -ForegroundColor Red
}

# Frontend
if (Test-Port 5173) {
    Write-Host "  Frontend  : UP    (http://localhost:5173)" -ForegroundColor Green
} else {
    Write-Host "  Frontend  : DOWN  (port 5173)" -ForegroundColor Red
}

# Database + backups
$dataDir = Join-Path $env:LOCALAPPDATA "FORLAS\CRQ"
$liveDb  = Join-Path $dataDir "forlas_crq.db"
$backups = Join-Path $dataDir "backups"

if (Test-Path $liveDb) {
    $sizeKb = [math]::Round((Get-Item $liveDb).Length / 1KB)
    Write-Host ("  Database  : present ({0:N0} KB)" -f $sizeKb) -ForegroundColor Green
} else {
    Write-Host "  Database  : MISSING" -ForegroundColor Red
}

if (Test-Path $backups) {
    $b = Get-ChildItem $backups -Filter "forlas_crq_*.db" | Sort-Object LastWriteTime -Descending
    if ($b) {
        Write-Host ("  Backups   : {0} available, newest {1}" -f $b.Count, $b[0].LastWriteTime) -ForegroundColor Green
    } else {
        Write-Host "  Backups   : none yet" -ForegroundColor Yellow
    }
} else {
    Write-Host "  Backups   : none yet" -ForegroundColor Yellow
}

Write-Host ""
if (-not $backendUp) {
    Write-Host "To start:   pwsh scripts\start-dev.ps1" -ForegroundColor DarkGray
}
