# Stop the dev servers cleanly.
#
# Tries a GRACEFUL close first (so the backend can WAL-checkpoint and avoid the
# corruption a hard kill causes), then force-kills only if it won't exit.

$ports = @(8765, 5173)   # backend first so it checkpoints before the UI dies

foreach ($port in $ports) {
    $conns = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    foreach ($conn in $conns) {
        $procId = $conn.OwningProcess
        $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
        if (-not $proc) { continue }

        Write-Host "Stopping PID $procId ($($proc.ProcessName)) on port $port…" -ForegroundColor Yellow

        # 1) Graceful: CloseMainWindow / WM_CLOSE lets uvicorn run its shutdown
        #    handler (WAL checkpoint). Give it a moment to exit on its own.
        try { $proc.CloseMainWindow() | Out-Null } catch {}
        taskkill /PID $procId 2>$null | Out-Null

        $waited = 0
        while ((Get-Process -Id $procId -ErrorAction SilentlyContinue) -and $waited -lt 6) {
            Start-Sleep -Milliseconds 500
            $waited++
        }

        # 2) Force only if it's still alive.
        if (Get-Process -Id $procId -ErrorAction SilentlyContinue) {
            Write-Host "  Did not exit gracefully — forcing." -ForegroundColor DarkYellow
            Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
        } else {
            Write-Host "  Stopped cleanly." -ForegroundColor Green
        }
    }
}

Write-Host "Done." -ForegroundColor Green
