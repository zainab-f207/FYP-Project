# Urdu OCR - Image to Text Converter

A complete, production-ready web application for converting Urdu images to editable text using OCR (Optical Character Recognition).

## 🌟 Features

- **High Accuracy OCR**: Powered by Tesseract OCR with Urdu language support
- **Image Preprocessing**: Automatic denoising, thresholding, and deskewing for better accuracy
- **Drag & Drop Upload**: Modern, intuitive interface with drag-and-drop support
- **Real-time Preview**: See your uploaded image before processing
- **Confidence Score**: Get accuracy metrics for extracted text
- **Copy to Clipboard**: Easy text copying functionality
- **Responsive Design**: Works seamlessly on desktop and mobile devices
- **Modern UI**: Beautiful glassmorphism design with smooth animations

## 🛠️ Tech Stack

### Backend
- **FastAPI**: Modern, fast web framework for building APIs
- **Python 3.8+**: Core programming language
- **Tesseract OCR**: Industry-standard OCR engine
- **OpenCV**: Image preprocessing and manipulation
- **Pillow**: Python Imaging Library

### Frontend
- **React 18**: Modern UI library
- **Vite**: Next-generation frontend tooling
- **Axios**: HTTP client for API calls
- **CSS3**: Custom styling with glassmorphism effects

## 📋 Prerequisites

Before you begin, ensure you have the following installed:

1. **Python 3.8 or higher**
   - Download from: https://www.python.org/downloads/

2. **Node.js 16 or higher**
   - Download from: https://nodejs.org/

3. **Tesseract OCR with Urdu language support**
   - **Windows**: 
     - Download installer from: https://github.com/UB-Mannheim/tesseract/wiki
     - During installation, select "Urdu" in the language data options
     - Note the installation path (usually `C:\Program Files\Tesseract-OCR`)
   
   - **Linux (Ubuntu/Debian)**:
     ```bash
     sudo apt-get update
     sudo apt-get install tesseract-ocr tesseract-ocr-urd
     ```
   
   - **macOS**:
     ```bash
     brew install tesseract tesseract-lang
     ```

4. **Verify Tesseract Installation**:
   ```bash
   tesseract --version
   tesseract --list-langs  # Should show 'urd' in the list
   ```

## 🚀 Installation & Setup

### 1. Clone or Download the Project

```bash
cd f:\Image-to-text
```

### 2. Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

**Important for Windows Users**: If Tesseract is not in your PATH, edit `backend/main.py` and uncomment this line (around line 23):

```python
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
```

Adjust the path if your Tesseract installation is in a different location.

### 3. Frontend Setup

```bash
# Open a new terminal and navigate to frontend directory
cd frontend

# Install dependencies
npm install
```

## 🎯 Running the Application

You need to run both the backend and frontend servers simultaneously.

### Terminal 1: Start Backend Server

```bash
cd backend
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac
python main.py
```

The backend API will be available at: **http://localhost:8000**

You can access the API documentation at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Terminal 2: Start Frontend Server

```bash
cd frontend
npm run dev
```

The frontend will be available at: **http://localhost:3000**

## 📱 Usage

1. **Open the Application**: Navigate to http://localhost:3000 in your web browser

2. **Upload an Image**:
   - Drag and drop an Urdu image onto the upload area, OR
   - Click "Browse Files" to select an image from your computer
   - Supported formats: PNG, JPG, JPEG (max 10MB)

3. **Extract Text**:
   - Click the "Extract Text" button
   - Wait for the processing to complete (usually 2-5 seconds)

4. **View Results**:
   - The extracted Urdu text will appear in the text box below
   - You'll see a confidence score indicating the accuracy
   - The text is editable if you need to make corrections

5. **Copy Text**:
   - Click the "Copy" button to copy the text to your clipboard

## 🔧 Configuration

### Backend Configuration

Edit `backend/main.py` to customize:

- **CORS Origins**: Add your production domain to the `allow_origins` list
- **File Size Limit**: Modify the 10MB limit in the `/api/ocr/extract` endpoint
- **OCR Parameters**: Adjust Tesseract configuration in the `UrduOCR` class

### Frontend Configuration

Edit `frontend/vite.config.js` to change:

- **Port**: Default is 3000
- **API Proxy**: Points to backend at localhost:8000

## 📊 API Endpoints

### POST /api/ocr/extract
Extract text from an uploaded image.

**Request:**
- Method: `POST`
- Content-Type: `multipart/form-data`
- Body: `file` (image file)

**Response:**
```json
{
  "text": "extracted urdu text...",
  "confidence": 85.5,
  "status": "success"
}
```

### GET /api/health
Check API health and Tesseract configuration.

**Response:**
```json
{
  "status": "healthy",
  "tesseract_version": "5.3.0",
  "urdu_support": true,
  "available_languages": ["eng", "urd", ...]
}
```

### GET /
Root endpoint with version information.

## 🐛 Troubleshooting

### Issue: "Tesseract not found"
**Solution**: 
- Ensure Tesseract is installed and in your PATH
- On Windows, set the path in `main.py`:
  ```python
  pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
  ```

### Issue: "Urdu language not available"
**Solution**: 
- Reinstall Tesseract and ensure you select Urdu language data during installation
- Verify with: `tesseract --list-langs`

### Issue: "CORS error" in browser console
**Solution**: 
- Ensure backend is running on port 8000
- Check CORS configuration in `backend/main.py`

### Issue: Low accuracy results
**Solution**: 
- Ensure image is clear and high resolution
- Image should have good contrast
- Text should be properly aligned (not skewed)
- Try preprocessing the image (increase contrast, remove noise)

### Issue: Backend not connecting
**Solution**: 
- Verify backend is running: http://localhost:8000
- Check if port 8000 is already in use
- Review backend terminal for error messages

## 📦 Building for Production

### Backend
```bash
cd backend
pip install gunicorn  # For Linux/Mac
# For Windows, use waitress instead:
pip install waitress

# Run with gunicorn (Linux/Mac):
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker

# Run with waitress (Windows):
waitress-serve --port=8000 main:app
```

### Frontend
```bash
cd frontend
npm run build
# The production build will be in the 'dist' folder
npm run preview  # Preview the production build
```

## 🎨 Customization

### Changing Colors
Edit `frontend/src/index.css` and modify the CSS variables:

```css
:root {
  --primary: #6366f1;
  --secondary: #8b5cf6;
  --accent: #ec4899;
  /* ... more colors */
}
```

### Changing Fonts
Edit `frontend/index.html` to use different Google Fonts for Urdu text.

## 📄 License

This project is open source and available for personal and commercial use.

## 🤝 Contributing

Contributions, issues, and feature requests are welcome!

## 📧 Support

If you encounter any issues or have questions, please check the troubleshooting section above.

## 🙏 Acknowledgments

- Tesseract OCR team for the amazing OCR engine
- FastAPI team for the excellent web framework
- React team for the powerful UI library

---

**Made with ❤️ for the Urdu-speaking community**
