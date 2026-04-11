
import cv2
import numpy as np
import sys
import os
import io
import re

if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.append('f:/Image-to-text/backend')
from fir_specialized_ocr import MultiEngineOCR

def detailed_scan():
    image_path = r"D:\FYP\Project\CrimeVision\OCRModel\app\data\raw\FIR_001.png"
    img = cv2.imread(image_path)
    h, w = img.shape[:2]
    ocr = MultiEngineOCR()
    
    sections_to_find = ['148', '149', '302', '379']
    
    print("--- Section Scan ---")
    for i in range(20, 85, 5):
        left = i / 100.0
        right = (i + 15) / 100.0
        crop = img[int(h*0.17):int(h*0.75), int(w*left):int(w*right)]
        text, _ = ocr.extract_text_tesseract(crop)
        found = [s for s in sections_to_find if s in text]
        print(f"X={left:.2f}: {found} | Raw: {repr(text[:80])}")

    print("\n--- Thana Scan ---")
    for i in range(0, 100, 10):
        left = i / 100.0
        right = (i + 15) / 100.0
        # Thana is usually in header y=0.10 to 0.16
        crop = img[int(h*0.08):int(h*0.16), int(w*left):int(w*right)]
        text, _ = ocr.extract_text_tesseract(crop)
        print(f"Header X={left:.2f}: {repr(text)}")

if __name__ == "__main__":
    detailed_scan()
