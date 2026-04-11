
import cv2
import sys
import os
import io

# Fix windows encoding
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.append('f:/Image-to-text/backend')
from fir_specialized_ocr import MultiEngineOCR

def check_debug_crop():
    path = "f:/Image-to-text/backend/debug_05b_sections_no_lines.png"
    if not os.path.exists(path):
        print(f"Error: {path} not found")
        return
        
    img = cv2.imread(path)
    if img is None:
        print("Failed to load image")
        return
        
    h, w = img.shape[:2]
    print(f"Image {path}: {w}x{h}")
    
    ocr = MultiEngineOCR()
    print("--- EasyOCR ---")
    text_easy, _ = ocr.extract_text_easyocr(img)
    print(repr(text_easy))
    
    print("--- Tesseract ---")
    text_tess, _ = ocr.extract_text_tesseract(img)
    print(repr(text_tess))

if __name__ == "__main__":
    check_debug_crop()
