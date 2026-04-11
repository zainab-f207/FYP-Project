# Quick Manual Setup - PowerShell

## ⚠️ IMPORTANT: Install Python First!

You need to install Python before proceeding.

1. Download: https://www.python.org/downloads/
2. Run installer
3. **✓ Check "Add Python to PATH"** (very important!)
4. Click "Install Now"
5. **Restart PowerShell** after installation

---

## Once Python is Installed:

### Option 1: Use PowerShell Script (Recommended)

```powershell
cd f:\Image-to-text
.\setup.ps1
```

If you get an execution policy error, run this first:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

### Option 2: Manual Setup

#### Backend Setup:
```powershell
cd f:\Image-to-text\backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

#### Frontend Setup:
```powershell
cd f:\Image-to-text\frontend
npm install
```

---

## Running the Application

### Terminal 1 - Backend:
```powershell
cd f:\Image-to-text\backend
.\venv\Scripts\Activate.ps1
python main.py
```

Wait for: `Uvicorn running on http://0.0.0.0:8000`

### Terminal 2 - Frontend:
```powershell
cd f:\Image-to-text\frontend
npm run dev
```

Wait for: `Local: http://localhost:3000/`

---

## Then Open:
**http://localhost:3000**

---

## Current Status:

✅ Node.js - Installed (v22.18.0)
✅ Tesseract - Installed with Urdu support
❌ Python - **NEEDS TO BE INSTALLED**

---

## After Installing Python:

Run this to verify:
```powershell
python --version
```

Should show: `Python 3.x.x`

Then run:
```powershell
.\setup.ps1
```
