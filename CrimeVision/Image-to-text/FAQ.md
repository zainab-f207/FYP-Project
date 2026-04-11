# Troubleshooting FAQ - Urdu OCR

## 🔧 Common Issues and Solutions

### Installation Issues

#### Q: "Python is not recognized as an internal or external command"
**A:** Python is not in your PATH.
- **Solution**: Reinstall Python and check "Add Python to PATH" during installation
- **Or**: Add Python manually to PATH:
  1. Find Python installation (usually `C:\Users\[YourName]\AppData\Local\Programs\Python\Python3x`)
  2. Add to System Environment Variables → Path

#### Q: "Node is not recognized as an internal or external command"
**A:** Node.js is not in your PATH.
- **Solution**: Reinstall Node.js (it should add itself to PATH automatically)
- **Verify**: Open new terminal and run `node --version`

#### Q: "Tesseract is not installed or not in PATH"
**A:** Tesseract is not found.
- **Solution 1**: Add Tesseract to PATH
- **Solution 2**: Edit `backend/main.py` line 23:
  ```python
  pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
  ```

---

### Backend Issues

#### Q: "ModuleNotFoundError: No module named 'fastapi'"
**A:** Backend dependencies not installed.
- **Solution**:
  ```bash
  cd backend
  venv\Scripts\activate
  pip install -r requirements.txt
  ```

#### Q: "Address already in use" on port 8000
**A:** Port 8000 is occupied.
- **Solution 1**: Find and kill the process using port 8000:
  ```bash
  netstat -ano | findstr :8000
  taskkill /PID [PID_NUMBER] /F
  ```
- **Solution 2**: Change port in `backend/main.py` (last line):
  ```python
  uvicorn.run(app, host="0.0.0.0", port=8001, reload=True)
  ```

#### Q: "TesseractNotFoundError"
**A:** Tesseract executable not found.
- **Solution**: Set the path in `backend/main.py`:
  ```python
  pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
  ```
- **Verify installation**: Run `tesseract --version` in terminal

#### Q: Backend starts but shows "urdu_support: false"
**A:** Urdu language data not installed.
- **Solution**: Reinstall Tesseract and select "Additional language data" → "Urdu"
- **Verify**: Run `tesseract --list-langs` (should show 'urd')

---

### Frontend Issues

#### Q: "npm: command not found"
**A:** npm is not installed or not in PATH.
- **Solution**: Reinstall Node.js (npm comes with Node.js)

#### Q: "Cannot find module" errors when running npm install
**A:** Corrupted node_modules or package-lock.json.
- **Solution**:
  ```bash
  cd frontend
  rmdir /s node_modules
  del package-lock.json
  npm install
  ```

#### Q: Frontend won't start - "EADDRINUSE: address already in use :::3000"
**A:** Port 3000 is already in use.
- **Solution**: Change port in `frontend/vite.config.js`:
  ```javascript
  server: {
    port: 3001,  // Change to any available port
    ...
  }
  ```

#### Q: "Failed to fetch" or CORS errors in browser console
**A:** Backend is not running or CORS is misconfigured.
- **Solution 1**: Ensure backend is running on port 8000
- **Solution 2**: Check CORS settings in `backend/main.py`:
  ```python
  allow_origins=["http://localhost:3000", "http://localhost:5173"]
  ```
  Add your frontend URL if different.

---

### OCR Processing Issues

#### Q: Extracted text is blank or empty
**A:** Multiple possible causes:
1. **Image quality too low**
   - Solution: Use higher resolution image (300 DPI+)
2. **Wrong language detected**
   - Solution: Verify Urdu language is installed
3. **Image is upside down or severely rotated**
   - Solution: Rotate image before uploading

#### Q: Extracted text has wrong characters or gibberish
**A:** Language detection issue.
- **Solution**: 
  - Ensure image contains Urdu text
  - Verify Tesseract Urdu language is installed
  - Check image quality and contrast

#### Q: Low confidence scores (< 50%)
**A:** Poor image quality or processing issues.
- **Solutions**:
  - Use clearer, higher resolution images
  - Ensure good contrast between text and background
  - Avoid handwritten text (OCR works best with printed text)
  - Remove image noise/artifacts
  - Ensure text is not too small

#### Q: Some characters or words are missing
**A:** Image preprocessing or OCR limitations.
- **Solutions**:
  - Ensure text has margins (not too close to edges)
  - Use standard Urdu fonts (avoid decorative fonts)
  - Increase image resolution
  - Ensure text is not overlapping

#### Q: Processing takes too long (> 30 seconds)
**A:** Large image or system performance issue.
- **Solutions**:
  - Resize image to smaller dimensions
  - Compress image (but maintain quality)
  - Check system resources (CPU, RAM)
  - Restart backend server

---

### Upload Issues

#### Q: "Invalid file type" error
**A:** File format not supported.
- **Solution**: Convert image to PNG, JPG, or JPEG format

#### Q: "File size exceeds 10MB limit" error
**A:** Image is too large.
- **Solution**: 
  - Compress image using online tools
  - Resize image to smaller dimensions
  - Or increase limit in `backend/main.py` line 126

#### Q: Drag and drop not working
**A:** Browser compatibility or JavaScript issue.
- **Solution**: 
  - Try using "Browse Files" button instead
  - Clear browser cache
  - Try different browser (Chrome, Firefox, Edge)

---

### Display Issues

#### Q: Urdu text not displaying correctly (boxes or question marks)
**A:** Font not loaded or browser encoding issue.
- **Solution**:
  - Ensure internet connection (font loads from Google Fonts)
  - Clear browser cache
  - Check browser console for font loading errors
  - Try different browser

#### Q: Text is left-to-right instead of right-to-left
**A:** RTL styling not applied.
- **Solution**: Check `frontend/src/components/UrduOCR.css` has:
  ```css
  .urdu-text {
    direction: rtl;
    text-align: right;
  }
  ```

#### Q: UI looks broken or unstyled
**A:** CSS not loading.
- **Solution**:
  - Check browser console for errors
  - Clear browser cache
  - Restart frontend server
  - Verify all CSS files exist

---

### Performance Issues

#### Q: Application is slow or laggy
**A:** System resources or large files.
- **Solutions**:
  - Close unnecessary applications
  - Use smaller images
  - Restart both servers
  - Check system RAM and CPU usage

#### Q: Browser becomes unresponsive during processing
**A:** Large image processing.
- **Solution**: 
  - Use smaller images
  - Increase browser memory limit
  - Try different browser

---

### Development Issues

#### Q: Changes to code not reflecting
**A:** Hot reload not working or cache issue.
- **Solutions**:
  - **Backend**: Restart server (Ctrl+C, then `python main.py`)
  - **Frontend**: Clear browser cache (Ctrl+Shift+R)
  - Check terminal for errors

#### Q: Virtual environment activation fails
**A:** Execution policy restriction (Windows).
- **Solution**:
  ```powershell
  Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
  ```
  Then try activating again:
  ```bash
  venv\Scripts\activate
  ```

---

### Testing Issues

#### Q: Health check endpoint returns "unhealthy"
**A:** Tesseract configuration issue.
- **Solution**: 
  - Verify Tesseract installation
  - Check Tesseract path in `main.py`
  - Run `tesseract --version` to verify

#### Q: API documentation (Swagger) not loading
**A:** Backend not running or port issue.
- **Solution**:
  - Ensure backend is running
  - Navigate to correct URL: http://localhost:8000/docs
  - Check for errors in backend terminal

---

## 🆘 Still Having Issues?

### Debugging Steps:

1. **Check Prerequisites**:
   ```bash
   python --version
   node --version
   npm --version
   tesseract --version
   tesseract --list-langs
   ```

2. **Check Backend Logs**:
   - Look at the terminal running `python main.py`
   - Check for error messages or stack traces

3. **Check Frontend Logs**:
   - Open browser DevTools (F12)
   - Check Console tab for errors
   - Check Network tab for failed requests

4. **Verify File Structure**:
   - Ensure all files from PROJECT_STRUCTURE.md exist
   - Check file permissions

5. **Clean Install**:
   ```bash
   # Backend
   cd backend
   rmdir /s venv
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt

   # Frontend
   cd frontend
   rmdir /s node_modules
   del package-lock.json
   npm install
   ```

### Getting More Help:

1. Review **README.md** for detailed documentation
2. Check **TESTING.md** for testing procedures
3. Review **SETUP.md** for installation steps
4. Check error messages carefully
5. Search for specific error messages online

---

## 📝 Reporting Issues

If you find a bug, please note:
- What you were trying to do
- What happened (error message)
- What you expected to happen
- Your environment (OS, Python version, Node version, Tesseract version)
- Steps to reproduce

---

**Most issues can be resolved by:**
1. ✅ Ensuring all prerequisites are properly installed
2. ✅ Following setup instructions carefully
3. ✅ Checking error messages in terminal and browser console
4. ✅ Restarting servers after making changes

**Good luck! 🍀**
