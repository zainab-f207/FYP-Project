# Urdu OCR Backend

FastAPI backend for Urdu text extraction from images.

## Prerequisites

1. **Python 3.8+**
2. **Tesseract OCR** with Urdu language support

### Installing Tesseract on Windows

1. Download Tesseract installer from: https://github.com/UB-Mannheim/tesseract/wiki
2. Run the installer and note the installation path (usually `C:\Program Files\Tesseract-OCR`)
3. During installation, make sure to select **Urdu language data** in the language selection
4. Add Tesseract to your PATH or update the path in `main.py`

### Verifying Urdu Language Support

After installation, run:
```bash
tesseract --list-langs
```

You should see `urd` in the list.

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
```

2. Activate the virtual environment:
```bash
# Windows
venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Running the Server

```bash
python main.py
```

Or using uvicorn directly:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at: http://localhost:8000

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Endpoints

### POST /api/ocr/extract
Upload an image to extract Urdu text.

**Request:**
- Method: POST
- Content-Type: multipart/form-data
- Body: file (image/png, image/jpeg, image/jpg)

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

### GET /
Root endpoint with version info.
