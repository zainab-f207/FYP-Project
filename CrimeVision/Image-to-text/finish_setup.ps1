# Finish EasyOCR Setup
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Finishing EasyOCR Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Installing EasyOCR and PyTorch (CPU)..." -ForegroundColor Yellow
Write-Host "This may take a few minutes. Please wait..." -ForegroundColor Gray

# Install dependencies
& .\backend\venv\Scripts\pip.exe install easyocr --find-links https://download.pytorch.org/whl/cpu

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✅ Installation Complete!" -ForegroundColor Green
    
    # Restart Backend
    Write-Host "Restarting Backend Server..." -ForegroundColor Yellow
    
    # Kill existing python processes
    Stop-Process -Name "python" -ErrorAction SilentlyContinue
    
    # Start backend
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd backend; .\venv\Scripts\Activate.ps1; python main.py"
    
    Write-Host "Backend restarted with EasyOCR support!" -ForegroundColor Green
    Write-Host "You can now use the application." -ForegroundColor Cyan
} else {
    Write-Host ""
    Write-Host "❌ Installation Failed!" -ForegroundColor Red
    Write-Host "Please check your internet connection and try again." -ForegroundColor Red
}

Write-Host ""
Write-Host "Press any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
