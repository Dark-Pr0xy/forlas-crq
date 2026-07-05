# FORLAS CRQ — one-click dev launcher (Windows).
#
# Starts the FastAPI backend (uvicorn) and the Vite frontend each in its own
# PowerShell window, so they stay visible and you can Ctrl+C to stop. Closing
# either window stops just that service.
#
# Run from anywhere:
#     pwsh E:\FORLAS-CRQ-Beta\scripts\start-dev.ps1
# Or double-click it in Explorer (you may need to allow scripts via
# `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`).

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"
$venvActivate = Join-Path $backend ".venv\Scripts\Activate.ps1"

if (-not (Test-Path $venvActivate)) {
    Write-Host "Backend virtualenv not found at $venvActivate" -ForegroundColor Red
    Write-Host "Create it first:" -ForegroundColor Yellow
    Write-Host "    cd $backend; python -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -e .[dev]"
    exit 1
}

$nodeModules = Join-Path $frontend "node_modules"
if (-not (Test-Path $nodeModules)) {
    Write-Host "Frontend dependencies not installed. Running 'npm install'..." -ForegroundColor Yellow
    Push-Location $frontend
    npm install --no-audit --no-fund
    Pop-Location
}

Write-Host ""
Write-Host "Starting FORLAS CRQ dev servers" -ForegroundColor Cyan
Write-Host "  Backend:  http://127.0.0.1:8765  (uvicorn)"
Write-Host "  Frontend: http://localhost:5173  (vite)"
Write-Host ""

# Clean up any orphaned processes from a previous run that didn't release
# their ports (common when closing a PowerShell window mid-server).
foreach ($port in @(5173, 8765)) {
    $conns = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    foreach ($conn in $conns) {
        $proc = Get-Process -Id $conn.OwningProcess -ErrorAction SilentlyContinue
        if ($proc) {
            Write-Host "  Releasing port $port from PID $($conn.OwningProcess) ($($proc.ProcessName))" -ForegroundColor Yellow
            Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
        }
    }
}
Start-Sleep -Milliseconds 500

$backendCmd = "Set-Location '$backend'; . '$venvActivate'; " +
              "Write-Host 'Backend starting...' -ForegroundColor Cyan; " +
              "uvicorn app.main:app --reload --port 8765"

$frontendCmd = "Set-Location '$frontend'; " +
               "Write-Host 'Frontend starting...' -ForegroundColor Cyan; " +
               "npm run dev"

Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd
Start-Sleep -Seconds 2
Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd

Write-Host "Both windows opened. Allow ~10 seconds, then visit:" -ForegroundColor Green
Write-Host "    http://localhost:5173/" -ForegroundColor Green
Write-Host ""
Write-Host "Login as owner@local. On first run the owner password is printed" -ForegroundColor Yellow
Write-Host "once to the BACKEND window's output. Change it from Settings after login." -ForegroundColor Yellow
