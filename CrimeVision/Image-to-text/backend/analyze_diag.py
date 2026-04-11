
import cv2
import sys
import os
import io

# Fix windows encoding
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.append('f:/Image-to-text/backend')
from fir_specialized_ocr import MultiEngineOCR

def analyze_diag_crops():
    ocr = MultiEngineOCR()
    
    print("--- Header Crops Analysis ---")
    for f in sorted(os.listdir('.')):
        if f.startswith('diag_header_') and f.endswith('.png'):
            img = cv2.imread(f)
            text_tess, _ = ocr.extract_text_tesseract(img)
            text_easy, _ = ocr.extract_text_easyocr(img)
            print(f"File: {f}")
            print(f"  Tess: {repr(text_tess)}")
            print(f"  Easy: {repr(text_easy)}")

    print("\n--- Sections Crops Analysis ---")
    for f in sorted(os.listdir('.')):
        if f.startswith('diag_sections_') and f.endswith('.png'):
            img = cv2.imread(f)
            text_tess, _ = ocr.extract_text_tesseract(img)
            text_easy, _ = ocr.extract_text_easyocr(img)
            print(f"File: {f}")
            print(f"  Tess: {repr(text_tess)}")
            print(f"  Easy: {repr(text_easy)}")

if __name__ == "__main__":
    analyze_diag_crops()
