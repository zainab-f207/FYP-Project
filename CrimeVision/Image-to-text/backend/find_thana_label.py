
import cv2
import sys
import os
import io
import re

if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.append('f:/Image-to-text/backend')
from fir_specialized_ocr import MultiEngineOCR

def find_thana_label():
    image_path = r"D:\FYP\Project\CrimeVision\OCRModel\app\data\raw\FIR_001.png"
    img = cv2.imread(image_path)
    h, w = img.shape[:2]
    ocr = MultiEngineOCR()
    reader = ocr.easyocr_reader
    
    # Try different y-levels in the top 30%
    for y_start in [0.05, 0.10, 0.15, 0.20]:
        crop = img[int(h*y_start):int(h*(y_start+0.10)), 0:w]
        results = reader.readtext(crop)
        for res in results:
            text = res[1]
            if 'تھانہ' in text or 'تھان' in text or 'PS' in text.upper():
                print(f"FOUND LABEL: '{text}' at y={y_start:.2f}, x_range={res[0][0][0]/w:.2f}-{res[0][1][0]/w:.2f}")

if __name__ == "__main__":
    find_thana_label()
