# Restart Backend Server
Write-Host "Restarting Backend Server..." -ForegroundColor Yellow

# Kill any existing uvicorn processes on port 8000
$processes = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
if ($processes) {
    foreach ($proc in $processes) {
        Stop-Process -Id $proc -Force -ErrorAction SilentlyContinue
        Write-Host "Stopped process $proc" -ForegroundColor Gray
    }
    Start-Sleep -Seconds 2
}

# Start backend
Set-Location backend
Start-Process powershell -ArgumentList "-NoExit", "-Command", ".\venv\Scripts\python.exe -m uvicorn main:app --reload --host 0.0.0.0 --port 8000"
Set-Location ..

Write-Host "Backend server restarted!" -ForegroundColor Green
Write-Host "Backend: http://localhost:8000" -ForegroundColor Cyan
