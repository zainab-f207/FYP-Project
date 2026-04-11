
import sys
import os
import io
import cv2
import numpy as np

# Fix windows encoding issues
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Add backend to path
sys.path.append('f:/Image-to-text/backend')
from fir_specialized_ocr import FIRImagePreprocessor, MultiEngineOCR, FIRExtractor

def probe_sections():
    image_path = r"D:\FYP\Project\CrimeVision\OCRModel\app\data\raw\FIR_001.png"
    if not os.path.exists(image_path):
        print(f"Error: {image_path} not found")
        image_path = "debug_05_sections_raw.png"
        if not os.path.exists(image_path):
            print("No image to probe")
            return

    img = cv2.imread(image_path)
    if img is None:
        print("Failed to load image")
        return

    h, w = img.shape[:2]
    print(f"Probing image {w}x{h}")

    ocr = MultiEngineOCR()
    
    if "FIR_001.png" in image_path:
        for left in [0.05, 0.15, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.85]:
            right = left + 0.15
            if right > 1.0: right = 1.0
            
            crop = img[int(h*0.1):int(h*0.8), int(w*left):int(w*right)]
            # We use tesseract because it's faster for probing
            text, _ = ocr.extract_text_tesseract(crop)
            print(f"Col {left:.2f}-{right:.2f}: {repr(text)}")
    else:
        text, _ = ocr.extract_text_tesseract(img)
        print(f"Whole Debug Crop: {repr(text)}")

if __name__ == "__main__":
    probe_sections()
