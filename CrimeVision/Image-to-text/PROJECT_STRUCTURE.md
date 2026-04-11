# Project Structure

```
Image-to-text/
│
├── backend/                      # FastAPI Backend
│   ├── main.py                   # Main FastAPI application
│   ├── requirements.txt          # Python dependencies
│   ├── README.md                 # Backend documentation
│   └── venv/                     # Virtual environment (created during setup)
│
├── frontend/                     # React Frontend
│   ├── src/
│   │   ├── components/
│   │   │   ├── UrduOCR.jsx      # Main OCR component
│   │   │   └── UrduOCR.css      # Component styles
│   │   ├── services/
│   │   │   └── api.js           # API service layer
│   │   ├── App.jsx              # Root App component
│   │   ├── main.jsx             # React entry point
│   │   └── index.css            # Global styles
│   ├── index.html               # HTML template
│   ├── package.json             # Node dependencies
│   ├── vite.config.js           # Vite configuration
│   └── node_modules/            # Node packages (created during setup)
│
├── .gitignore                   # Git ignore rules
├── README.md                    # Main documentation
├── SETUP.md                     # Quick setup guide
└── start.bat                    # Windows setup script
```

## File Descriptions

### Backend Files

- **main.py**: Core FastAPI application with OCR endpoints and image preprocessing
- **requirements.txt**: All Python package dependencies
- **README.md**: Backend-specific documentation

### Frontend Files

- **UrduOCR.jsx**: Main component handling file upload, OCR processing, and results display
- **UrduOCR.css**: Styling for the OCR component with glassmorphism effects
- **api.js**: Axios-based API service for backend communication
- **App.jsx**: Root component that renders UrduOCR
- **main.jsx**: React application entry point
- **index.css**: Global CSS variables, animations, and utility classes
- **index.html**: HTML template with Urdu font imports
- **vite.config.js**: Vite configuration with proxy setup
- **package.json**: Node.js dependencies and scripts

### Configuration Files

- **.gitignore**: Excludes node_modules, venv, and build artifacts
- **start.bat**: Automated setup and launch script for Windows

## Technology Stack

### Backend
- FastAPI 0.104.1
- Uvicorn (ASGI server)
- Pytesseract 0.3.10
- OpenCV 4.8.1
- Pillow 10.1.0
- NumPy 1.26.2

### Frontend
- React 18.2.0
- Vite 5.0.8
- Axios 1.6.2

### External Dependencies
- Tesseract OCR (with Urdu language data)
- Node.js 16+
- Python 3.8+
