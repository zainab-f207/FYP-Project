
import cv2
import numpy as np
import sys
import os

sys.path.append('f:/Image-to-text/backend')
from fir_specialized_ocr import MultiEngineOCR

def find_302_exhaustive():
    image_path = r"D:\FYP\Project\CrimeVision\OCRModel\app\data\raw\FIR_001.png"
    img = cv2.imread(image_path)
    h, w = img.shape[:2]
    ocr = MultiEngineOCR()
    
    # Target area: y=0.2 to 0.7, x=0.4 to 0.7
    # Use small windows to pinpoint
    for y in range(20, 70, 5):
        y_percent = y/100.0
        for x in range(40, 70, 5):
            x_percent = x/100.0
            crop = img[int(h*y_percent):int(h*(y_percent+0.05)), int(w*x_percent):int(w*(x_percent+0.10))]
            text, _ = ocr.extract_text_tesseract(crop)
            if '302' in text or '30' in text or '02' in text:
                print(f"AT y={y_percent:.2f}, x={x_percent:.2f} -> Found: {repr(text)}")
                cv2.imwrite(f"found_302_y{y}_x{x}.png", crop)

if __name__ == "__main__":
    find_302_exhaustive()
