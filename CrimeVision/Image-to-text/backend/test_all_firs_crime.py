"""Test crime area extraction on all FIR images"""
import cv2
import numpy as np
import pytesseract
import os
import re

FIR_DIR = r"D:\FYP\FIR_Images\upload"
FIRS = ['FIR_001.jpg', 'FIR_006.jpg', 'FIR_010.jpg', 'FIR_014.jpg', 'FIR_015.jpg']

# Row 4 region coordinates (same as in fir_specialized_ocr.py)
CRIME_TOP = 0.36
CRIME_BOTTOM = 0.42
CRIME_LEFT = 0.02
CRIME_RIGHT = 0.63

print("="*70)
print("CRIME AREA EXTRACTION TEST - All FIR Images")
print("="*70)

for fir_name in FIRS:
    fir_path = os.path.join(FIR_DIR, fir_name)
    if not os.path.exists(fir_path):
        print(f"\n{fir_name}: NOT FOUND")
        continue
    
    img = cv2.imread(fir_path)
    h, w = img.shape[:2]
    
    # Extract Row 4
    y1 = int(h * CRIME_TOP)
    y2 = int(h * CRIME_BOTTOM)
    x1 = int(w * CRIME_LEFT)
    x2 = int(w * CRIME_RIGHT)
    region = img[y1:y2, x1:x2]
    rh, rw = region.shape[:2]
    
    print(f"\n{'='*70}")
    print(f"{fir_name} - Image: {w}x{h} | Row4: {rw}x{rh}")
    print(f"{'='*70}")
    
    gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
    
    # Save debug crop
    debug_name = f"_debug_crime_{fir_name.replace('.jpg','')}.png"
    cv2.imwrite(debug_name, region)
    
    # Best pipeline: 2x + denoise + Otsu + PSM 6
    s2x = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    dn = cv2.fastNlMeansDenoising(s2x, None, 10, 7, 21)
    blur = cv2.GaussianBlur(dn, (3, 3), 0)
    _, otsu = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # Run Tesseract PSM 6
    text1 = pytesseract.image_to_string(otsu, lang='urd', config='--psm 6 --oem 1').strip()
    print(f"  2x_dn_otsu PSM6: {text1[:200]}")
    
    # Pipeline 2: 3x + Otsu + PSM 6  
    s3x = cv2.resize(gray, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
    blur3 = cv2.GaussianBlur(s3x, (3, 3), 0)
    _, otsu3 = cv2.threshold(blur3, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    text2 = pytesseract.image_to_string(otsu3, lang='urd', config='--psm 6 --oem 1').strip()
    print(f"  3x_otsu PSM6:    {text2[:200]}")
    
    # Pipeline 3: 2x + bilateral + Otsu + PSM 6
    bil = cv2.bilateralFilter(s2x, 9, 75, 75)
    blur_b = cv2.GaussianBlur(bil, (3, 3), 0)
    _, otsu_b = cv2.threshold(blur_b, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    text3 = pytesseract.image_to_string(otsu_b, lang='urd', config='--psm 6 --oem 1').strip()
    print(f"  2x_bil_otsu PSM6: {text3[:200]}")
    
    # Clean up debug files
    if os.path.exists(debug_name):
        os.remove(debug_name)

print(f"\n{'='*70}")
print("DONE")
