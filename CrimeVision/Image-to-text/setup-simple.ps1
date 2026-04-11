# Simple Setup Script for Urdu OCR
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Urdu OCR - Quick Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Backend Setup
Write-Host "[1/2] Setting up Backend..." -ForegroundColor Yellow
Set-Location backend

if (-Not (Test-Path "venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Cyan
    py -m venv venv
}

Write-Host "Installing backend dependencies..." -ForegroundColor Cyan
.\venv\Scripts\pip.exe install -r requirements.txt

Write-Host "✓ Backend setup complete" -ForegroundColor Green
Set-Location ..

# Frontend Setup
Write-Host ""
Write-Host "[2/2] Setting up Frontend..." -ForegroundColor Yellow
Set-Location frontend

Write-Host "Installing frontend dependencies..." -ForegroundColor Cyan
npm install

Write-Host "✓ Frontend setup complete" -ForegroundColor Green
Set-Location ..

# Done
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "To start the application, run:" -ForegroundColor Cyan
Write-Host "  .\run.ps1" -ForegroundColor White
Write-Host ""
