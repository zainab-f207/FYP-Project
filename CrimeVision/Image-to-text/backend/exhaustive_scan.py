
import cv2
import sys
import os
import io

if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.append('f:/Image-to-text/backend')
from fir_specialized_ocr import MultiEngineOCR

def exhaustive_scan():
    image_path = r"D:\FYP\Project\CrimeVision\OCRModel\app\data\raw\FIR_001.png"
    img = cv2.imread(image_path)
    h, w = img.shape[:2]
    ocr = MultiEngineOCR()
    
    # Grid search
    print("X_Start | X_End | Found Sections")
    print("-" * 30)
    for x in range(0, 95, 2):
        left = x / 100.0
        right = (x + 10) / 100.0
        crop = img[int(h*0.15):int(h*0.80), int(w*left):int(w*right)]
        text, _ = ocr.extract_text_easyocr(crop)
        # Find 3-digit numbers
        import re
        nums = re.findall(r'\d{3}', text)
        if nums:
             print(f"{left:.2f} | {right:.2f} | {nums} | Raw: {repr(text[:50])}")

if __name__ == "__main__":
    exhaustive_scan()
