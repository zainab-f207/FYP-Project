@echo off
echo ========================================
echo Urdu OCR - Quick Start Script
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Check if Node.js is installed
node --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js is not installed or not in PATH
    echo Please install Node.js from https://nodejs.org/
    pause
    exit /b 1
)

REM Check if Tesseract is installed
tesseract --version >nul 2>&1
if errorlevel 1 (
    echo WARNING: Tesseract OCR is not found in PATH
    echo Please install Tesseract from https://github.com/UB-Mannheim/tesseract/wiki
    echo Make sure to select Urdu language during installation
    echo.
    echo You can continue, but you may need to configure the path in backend/main.py
    echo.
    pause
)

echo [1/4] Setting up Backend...
cd backend

REM Create virtual environment if it doesn't exist
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment and install dependencies
echo Installing backend dependencies...
call venv\Scripts\activate.bat
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install backend dependencies
    pause
    exit /b 1
)

echo.
echo [2/4] Setting up Frontend...
cd ..\frontend

REM Install frontend dependencies
if not exist "node_modules" (
    echo Installing frontend dependencies...
    call npm install
    if errorlevel 1 (
        echo ERROR: Failed to install frontend dependencies
        pause
        exit /b 1
    )
)

echo.
echo [3/4] Setup Complete!
echo.
echo ========================================
echo To run the application:
echo ========================================
echo.
echo Terminal 1 - Backend:
echo   cd backend
echo   venv\Scripts\activate
echo   python main.py
echo.
echo Terminal 2 - Frontend:
echo   cd frontend
echo   npm run dev
echo.
echo Then open: http://localhost:3000
echo ========================================
echo.

REM Ask if user wants to start the servers now
set /p START="Do you want to start the servers now? (y/n): "
if /i "%START%"=="y" (
    echo.
    echo [4/4] Starting servers...
    echo.
    echo Starting Backend Server...
    cd ..\backend
    start cmd /k "venv\Scripts\activate && python main.py"
    
    timeout /t 3 /nobreak >nul
    
    echo Starting Frontend Server...
    cd ..\frontend
    start cmd /k "npm run dev"
    
    echo.
    echo Servers are starting in separate windows...
    echo Please wait a few seconds, then open http://localhost:3000
) else (
    echo.
    echo Setup complete! Start the servers manually when ready.
)

echo.
pause
