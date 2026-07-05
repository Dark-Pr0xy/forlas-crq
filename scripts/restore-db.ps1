# Restore the FORLAS CRQ database from a backup.
#
# Usage:
#   pwsh scripts\restore-db.ps1              # restore the NEWEST backup
#   pwsh scripts\restore-db.ps1 -List        # just list available backups
#   pwsh scripts\restore-db.ps1 -File "<path-to-backup.db>"
#
# The app must be STOPPED first (this script checks port 8765 and refuses if
# it's live, so you can't restore over an open database).

param(
    [switch]$List,
    [string]$File
)

$ErrorActionPreference = "Stop"

$dataDir = Join-Path $env:LOCALAPPDATA "FORLAS\CRQ"
$liveDb  = Join-Path $dataDir "forlas_crq.db"
$backups = Join-Path $dataDir "backups"

if (-not (Test-Path $backups)) {
    Write-Host "No backups directory found at $backups" -ForegroundColor Red
    exit 1
}

$all = Get-ChildItem -Path $backups -Filter "forlas_crq_*.db" | Sort-Object LastWriteTime -Descending

if ($List) {
    if (-not $all) { Write-Host "No backups found." -ForegroundColor Yellow; exit 0 }
    Write-Host "Available backups (newest first):" -ForegroundColor Cyan
    $all | ForEach-Object {
        "{0,-45} {1,8:N0} KB   {2}" -f $_.Name, ($_.Length / 1KB), $_.LastWriteTime
    }
    exit 0
}

# Refuse to restore while the backend is live.
$live = Get-NetTCPConnection -LocalPort 8765 -ErrorAction SilentlyContinue
if ($live) {
    Write-Host "Backend appears to be running on port 8765." -ForegroundColor Red
    Write-Host "Stop it first (scripts\stop-dev.ps1), then re-run this." -ForegroundColor Red
    exit 1
}

$source = if ($File) { Get-Item $File } else { $all | Select-Object -First 1 }
if (-not $source) {
    Write-Host "No backup available to restore." -ForegroundColor Red
    exit 1
}

# Preserve whatever is currently live before overwriting it.
if (Test-Path $liveDb) {
    $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $preserve = Join-Path $backups "forlas_crq_prerestore_$stamp.db"
    Copy-Item $liveDb $preserve
    Write-Host "Current DB preserved as $preserve" -ForegroundColor DarkGray
}

# Clear any stale WAL/shm so SQLite doesn't reapply a partial journal.
Remove-Item "$liveDb-wal", "$liveDb-shm" -ErrorAction SilentlyContinue
Copy-Item $source.FullName $liveDb -Force

Write-Host "Restored: $($source.Name)  ->  forlas_crq.db" -ForegroundColor Green
Write-Host "Start the app again with scripts\start-dev.ps1" -ForegroundColor Green
