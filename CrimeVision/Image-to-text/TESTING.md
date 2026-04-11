# Testing Guide - Urdu OCR Application

## 🧪 Pre-Launch Checklist

Before testing the application, ensure:

- [ ] Python 3.8+ is installed
- [ ] Node.js 16+ is installed
- [ ] Tesseract OCR is installed with Urdu language data
- [ ] Backend dependencies are installed (`pip install -r requirements.txt`)
- [ ] Frontend dependencies are installed (`npm install`)

## 🚀 Starting the Application

### Option 1: Using the Setup Script (Recommended)

```bash
cd f:\Image-to-text
start.bat
```

Follow the prompts and select "y" to start both servers.

### Option 2: Manual Start

**Terminal 1 - Backend:**
```bash
cd f:\Image-to-text\backend
venv\Scripts\activate
python main.py
```

Wait for: `Uvicorn running on http://0.0.0.0:8000`

**Terminal 2 - Frontend:**
```bash
cd f:\Image-to-text\frontend
npm run dev
```

Wait for: `Local: http://localhost:3000/`

## ✅ Testing Steps

### 1. Backend Health Check

**Test the API directly:**

Open browser and navigate to:
- http://localhost:8000 - Should show API info
- http://localhost:8000/docs - Should show Swagger UI
- http://localhost:8000/api/health - Should show health status

**Expected Response from /api/health:**
```json
{
  "status": "healthy",
  "tesseract_version": "5.x.x",
  "urdu_support": true,
  "available_languages": ["eng", "urd", ...]
}
```

⚠️ **If `urdu_support` is false:**
- Reinstall Tesseract with Urdu language data
- Run: `tesseract --list-langs` to verify

### 2. Frontend Access

**Open the application:**
- Navigate to: http://localhost:3000
- You should see:
  - ✅ "Urdu OCR" gradient title
  - ✅ "Convert Urdu Images to Editable Text" subtitle
  - ✅ Upload area with drag & drop zone
  - ✅ Three feature cards at the bottom
  - ✅ Dark theme with purple/blue gradients

### 3. Upload Functionality Test

**Test drag & drop:**
1. Drag an Urdu image over the upload area
2. The border should turn blue and scale slightly
3. Drop the image
4. Image preview should appear

**Test file browser:**
1. Click "Browse Files" button
2. Select an Urdu image (PNG, JPG, or JPEG)
3. Image preview should appear
4. File details should show below (name and size)

**Test file validation:**
1. Try uploading a non-image file (e.g., .txt)
   - Should show error: "Please upload a PNG or JPEG image"
2. Try uploading a very large file (> 10MB)
   - Should show error: "File size must be less than 10MB"

### 4. OCR Processing Test

**Using your sample Urdu document:**

1. Upload the Urdu image you provided
2. Click "Extract Text" button
3. Button should show loading spinner: "Processing..."
4. Wait 2-5 seconds
5. Results should appear below:
   - ✅ "Extracted Text" section appears
   - ✅ Confidence score badge shows (e.g., "85%")
   - ✅ Urdu text appears in the text box
   - ✅ Text is right-aligned (RTL)
   - ✅ Text uses Noto Nastaliq Urdu font

**Verify the extracted text:**
- Check if the text matches the image content
- Verify Urdu characters are properly displayed
- Check if numbers and dates are extracted correctly
- Verify table structure is maintained (if applicable)

### 5. Copy Functionality Test

1. After text extraction, click the "Copy" button (top-left of text box)
2. Open a text editor (Notepad, Word, etc.)
3. Paste (Ctrl+V)
4. Verify the Urdu text is copied correctly

### 6. Clear and Retry Test

1. Click the red "X" button on the image preview
2. Image should be removed
3. Upload area should return to initial state
4. Upload a different image
5. Extract text again
6. Verify new results appear

### 7. Error Handling Test

**Test backend connection error:**
1. Stop the backend server (Ctrl+C in backend terminal)
2. Try to extract text from an image
3. Should show error: "No response from server. Please ensure the backend is running."
4. Restart backend server

**Test invalid image:**
1. Create a blank/corrupted image file
2. Try to upload and extract
3. Should show appropriate error message

### 8. Responsive Design Test

**Desktop (1920x1080):**
- Layout should be centered
- All elements properly spaced
- Feature cards in a row

**Tablet (768px):**
- Layout should adjust
- Feature cards may stack

**Mobile (375px):**
- Single column layout
- Feature cards stacked vertically
- Text remains readable

## 📊 Performance Testing

### Test Different Image Types:

1. **High Quality Image (300 DPI)**
   - Expected: High confidence (85-95%)
   - Processing: 3-5 seconds

2. **Medium Quality Image (150 DPI)**
   - Expected: Medium confidence (70-85%)
   - Processing: 2-4 seconds

3. **Low Quality Image (72 DPI)**
   - Expected: Lower confidence (50-70%)
   - Processing: 2-3 seconds

4. **Skewed Image (rotated)**
   - Expected: Automatic deskewing
   - Confidence may be slightly lower

5. **Noisy Image (with artifacts)**
   - Expected: Denoising applied
   - Confidence may vary

## 🐛 Common Issues and Solutions

### Issue: Blank text output
**Possible Causes:**
- Image quality too low
- Text too small
- Image is upside down

**Solutions:**
- Use higher resolution image
- Ensure text is right-side up
- Check image contrast

### Issue: Gibberish characters
**Possible Causes:**
- Wrong language detected
- Image has mixed languages

**Solutions:**
- Ensure image contains Urdu text
- Check Tesseract language configuration

### Issue: Low confidence scores
**Possible Causes:**
- Poor image quality
- Low contrast
- Handwritten text (OCR works best with printed text)

**Solutions:**
- Use clearer images
- Increase image contrast before upload
- Use printed documents for best results

### Issue: Missing characters or words
**Possible Causes:**
- Text too close to image edges
- Overlapping text
- Decorative fonts

**Solutions:**
- Ensure text has margins
- Use standard Urdu fonts
- Crop image to focus on text

## 📝 Test Results Template

Use this template to document your testing:

```
Date: _______________
Tester: _______________

Backend Health Check:
[ ] API accessible
[ ] Swagger UI working
[ ] Urdu support enabled

Frontend Access:
[ ] Page loads correctly
[ ] UI elements visible
[ ] Responsive design working

Upload Functionality:
[ ] Drag & drop works
[ ] File browser works
[ ] File validation works

OCR Processing:
[ ] Text extraction successful
[ ] Confidence score displayed
[ ] Urdu text properly formatted

Copy Functionality:
[ ] Copy button works
[ ] Text pastes correctly

Error Handling:
[ ] Invalid file types rejected
[ ] Large files rejected
[ ] Backend errors handled gracefully

Performance:
Average processing time: _____ seconds
Average confidence score: _____ %

Issues Found:
1. _______________
2. _______________
3. _______________

Overall Status: [ ] Pass [ ] Fail
```

## 🎯 Success Criteria

The application is working correctly if:

✅ Backend API is accessible and healthy
✅ Frontend loads without errors
✅ Images can be uploaded via drag & drop or file browser
✅ OCR processing completes within 10 seconds
✅ Extracted text is displayed in proper Urdu format (RTL)
✅ Confidence scores are shown
✅ Copy functionality works
✅ Error messages are clear and helpful
✅ UI is responsive on different screen sizes

## 📞 Getting Help

If tests fail:
1. Check the console for error messages (F12 in browser)
2. Review backend terminal for errors
3. Verify all prerequisites are installed
4. Check SETUP.md for troubleshooting
5. Review README.md for detailed documentation

---

**Happy Testing! 🚀**
