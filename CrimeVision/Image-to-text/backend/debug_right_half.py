"""Simple approach: take right portion of crime area for location text"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cv2
import numpy as np
import pytesseract

FIR_DIR = r"F:\FYP2\Project\CrimeVision\OCRModel\app\data\raw"
FIRS = ['FIR_001.png', 'FIR_006.png', 'FIR_010.png', 'FIR_014.png', 'FIR_015.png']

CRIME_TOP = 0.38
CRIME_BOTTOM = 0.451
CRIME_LEFT = 0.29
CRIME_RIGHT = 0.62

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "crime_right_half")
os.makedirs(OUT_DIR, exist_ok=True)

print("="*70)
print("RIGHT PORTION OCR (location text only)")
print("="*70)

for fir_name in FIRS:
    fir_path = os.path.join(FIR_DIR, fir_name)
    if not os.path.exists(fir_path):
        continue
    
    img = cv2.imread(fir_path)
    h, w = img.shape[:2]
    
    y1 = int(h * CRIME_TOP)
    y2 = int(h * CRIME_BOTTOM)
    x1 = int(w * CRIME_LEFT)
    x2 = int(w * CRIME_RIGHT)
    
    region = img[y1:y2, x1:x2]
    rh, rw = region.shape[:2]
    gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
    
    print(f"\n{'='*60}")
    print(f"{fir_name} -> region {rw}x{rh}px")
    
    # Try different right portion ratios (50%, 55%, 60%, 65%, 70%)
    for pct in [0.45, 0.50, 0.55, 0.60, 0.65, 0.70]:
        cut_x = int(rw * (1 - pct))  # Cut from left, keep right portion
        right_part = region[:, cut_x:]
        
        rg = cv2.cvtColor(right_part, cv2.COLOR_BGR2GRAY)
        
        # Try with minimal preprocessing (these are high-res images)
        _, thresh = cv2.threshold(rg, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        txt = pytesseract.image_to_string(thresh, lang='urd', config='--psm 6 --oem 1').strip().replace('\n', ' ')
        
        # Also try raw (no threshold)
        txt_raw = pytesseract.image_to_string(rg, lang='urd', config='--psm 6 --oem 1').strip().replace('\n', ' ')
        
        # Pick the better one
        best = txt if len(txt) >= len(txt_raw) else txt_raw
        
        print(f"  Right {int(pct*100)}% ({right_part.shape[1]}x{right_part.shape[0]}): [{best[:80]}]")
        
        # Save the 60% crop for inspection
        if pct == 0.60:
            cv2.imwrite(os.path.join(OUT_DIR, f"{fir_name.split('.')[0]}_right60.png"), right_part)
            cv2.imwrite(os.path.join(OUT_DIR, f"{fir_name.split('.')[0]}_right60_thresh.png"), thresh)

print(f"\nAll crops saved to: {OUT_DIR}")
print("Done!")
