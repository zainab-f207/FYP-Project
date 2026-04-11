
import cv2
import numpy as np
import sys
import os

sys.path.append('f:/Image-to-text/backend')
from fir_specialized_ocr import FIRImagePreprocessor, FIRRegions

def save_diagnostic_crops():
    image_path = r"D:\FYP\Project\CrimeVision\OCRModel\app\data\raw\FIR_001.png"
    img = cv2.imread(image_path)
    if img is None:
        print("Failed to load image")
        return
        
    preprocessor = FIRImagePreprocessor()
    
    # 1. Header Area (Thana) - Scan different bands
    for i in range(10):
        left = i * 0.1
        right = (i+1) * 0.1 + 0.1
        if right > 1.0: right = 1.0
        crop = preprocessor.extract_region_percent(img, 0.05, 0.20, left, right)
        cv2.imwrite(f"diag_header_{i}_{int(left*100)}-{int(right*100)}.png", crop)
        
    # 2. Sections Area - Scan different bands
    for i in range(5, 15):
        left = i * 0.05
        right = left + 0.15
        if right > 1.0: right = 1.0
        crop = preprocessor.extract_region_percent(img, 0.20, 0.70, left, right)
        cv2.imwrite(f"diag_sections_{i}_{int(left*100)}-{int(right*100)}.png", crop)

if __name__ == "__main__":
    save_diagnostic_crops()
