# Urdu OCR Setup Script for PowerShell
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Urdu OCR - Setup Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check Python
Write-Host "[1/5] Checking Python..." -ForegroundColor Yellow
try {
    $pythonVersion = py --version 2>&1
    Write-Host "✓ Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Python not found!" -ForegroundColor Red
    Write-Host "Please install Python from https://www.python.org/downloads/" -ForegroundColor Red
    Write-Host "Make sure to check 'Add Python to PATH' during installation" -ForegroundColor Red
    exit 1
}

# Check Node.js
Write-Host "[2/5] Checking Node.js..." -ForegroundColor Yellow
try {
    $nodeVersion = node --version 2>&1
    Write-Host "✓ Node.js found: $nodeVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Node.js not found!" -ForegroundColor Red
    Write-Host "Please install Node.js from https://nodejs.org/" -ForegroundColor Red
    exit 1
}

# Check Tesseract
Write-Host "[3/5] Checking Tesseract..." -ForegroundColor Yellow
try {
    $tesseractVersion = tesseract --version 2>&1 | Select-Object -First 1
    Write-Host "✓ Tesseract found: $tesseractVersion" -ForegroundColor Green
    
    # Check for Urdu
    $langs = tesseract --list-langs 2>&1
    if ($langs -match "urd") {
        Write-Host "✓ Urdu language support found" -ForegroundColor Green
    } else {
        Write-Host "✗ Urdu language not found!" -ForegroundColor Red
        Write-Host "Please reinstall Tesseract and select Urdu language data" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "✗ Tesseract not found!" -ForegroundColor Red
    Write-Host "Please install Tesseract from https://github.com/UB-Mannheim/tesseract/wiki" -ForegroundColor Red
    exit 1
}

# Setup Backend
Write-Host ""
Write-Host "[4/5] Setting up Backend..." -ForegroundColor Yellow
Set-Location backend

if (-Not (Test-Path "venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Cyan
    py -m venv venv
}

Write-Host "Activating virtual environment..." -ForegroundColor Cyan
& .\venv\Scripts\Activate.ps1

Write-Host "Installing backend dependencies..." -ForegroundColor Cyan
pip install -r requirements.txt

if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Failed to install backend dependencies" -ForegroundColor Red
    exit 1
}

Write-Host "✓ Backend setup complete" -ForegroundColor Green
deactivate

Set-Location ..

# Setup Frontend
Write-Host ""
Write-Host "[5/5] Setting up Frontend..." -ForegroundColor Yellow
Set-Location frontend

if (-Not (Test-Path "node_modules")) {
    Write-Host "Installing frontend dependencies..." -ForegroundColor Cyan
    npm install
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "✗ Failed to install frontend dependencies" -ForegroundColor Red
        exit 1
    }
}

Write-Host "✓ Frontend setup complete" -ForegroundColor Green
Set-Location ..

# Done
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "To start the application:" -ForegroundColor Cyan
Write-Host ""
Write-Host "Terminal 1 - Backend:" -ForegroundColor Yellow
Write-Host "  cd backend" -ForegroundColor White
Write-Host "  .\venv\Scripts\Activate.ps1" -ForegroundColor White
Write-Host "  python main.py" -ForegroundColor White
Write-Host ""
Write-Host "Terminal 2 - Frontend:" -ForegroundColor Yellow
Write-Host "  cd frontend" -ForegroundColor White
Write-Host "  npm run dev" -ForegroundColor White
Write-Host ""
Write-Host "Then open: http://localhost:3000" -ForegroundColor Cyan
Write-Host ""

$start = Read-Host "Do you want to start the servers now? (y/n)"
if ($start -eq "y" -or $start -eq "Y") {
    Write-Host ""
    Write-Host "Starting Backend Server..." -ForegroundColor Yellow
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD\backend'; .\venv\Scripts\Activate.ps1; py main.py"
    
    Start-Sleep -Seconds 3
    
    Write-Host "Starting Frontend Server..." -ForegroundColor Yellow
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD\frontend'; npm run dev"
    
    Write-Host ""
    Write-Host "Servers are starting in separate windows..." -ForegroundColor Green
    Write-Host "Please wait a few seconds, then open http://localhost:3000" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "Press any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
