# Quick Setup Guide - Urdu OCR

## ⚡ Fast Track Setup (Windows)

### Step 1: Install Prerequisites

1. **Install Python 3.8+**
   - Download: https://www.python.org/downloads/
   - ✅ Check "Add Python to PATH" during installation

2. **Install Node.js 16+**
   - Download: https://nodejs.org/
   - Choose LTS version

3. **Install Tesseract OCR with Urdu**
   - Download: https://github.com/UB-Mannheim/tesseract/wiki
   - ⚠️ **IMPORTANT**: During installation, click "Additional language data" and select **Urdu**
   - Default path: `C:\Program Files\Tesseract-OCR`

### Step 2: Verify Installations

Open Command Prompt and run:

```bash
python --version
# Should show: Python 3.x.x

node --version
# Should show: v16.x.x or higher

tesseract --version
# Should show Tesseract version

tesseract --list-langs
# Should include 'urd' in the list
```

### Step 3: Run Setup Script

1. Open Command Prompt
2. Navigate to project folder:
   ```bash
   cd f:\Image-to-text
   ```
3. Run the setup script:
   ```bash
   start.bat
   ```
4. Follow the prompts

The script will:
- ✅ Create Python virtual environment
- ✅ Install all backend dependencies
- ✅ Install all frontend dependencies
- ✅ Optionally start both servers

### Step 4: Access the Application

Once both servers are running:
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

---

## 🔧 Manual Setup (If Script Fails)

### Backend Setup

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

**If Tesseract is not in PATH:**
Edit `backend/main.py` line 23:
```python
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
```

### Frontend Setup

```bash
cd frontend
npm install
```

### Running the Servers

**Terminal 1 - Backend:**
```bash
cd backend
venv\Scripts\activate
python main.py
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

---

## 🎯 Testing the Application

1. Open http://localhost:3000
2. Upload the sample Urdu image (the one you provided)
3. Click "Extract Text"
4. View the extracted Urdu text

---

## ❗ Common Issues

### Issue: "Tesseract not found"
**Fix**: 
- Reinstall Tesseract
- Add to PATH, or
- Set path in `backend/main.py` line 23

### Issue: "Urdu language not available"
**Fix**: 
- Reinstall Tesseract
- During installation, select "Additional language data" → "Urdu"

### Issue: Port already in use
**Fix**:
- Backend (8000): Change port in `backend/main.py` last line
- Frontend (3000): Change port in `frontend/vite.config.js`

### Issue: CORS error
**Fix**: 
- Ensure backend is running
- Check `backend/main.py` CORS configuration includes your frontend URL

---

## 📞 Need Help?

1. Check the main README.md for detailed documentation
2. Review the troubleshooting section
3. Ensure all prerequisites are properly installed

---

**Ready to go? Run `start.bat` and get started! 🚀**
