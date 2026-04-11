"""Save crime area region crops for visual inspection"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cv2

FIR_DIR = r"D:\FYP\FIR_Images\upload"
FIRS = ['FIR_001.jpg', 'FIR_006.jpg', 'FIR_010.jpg', 'FIR_014.jpg', 'FIR_015.jpg']

# Current region coordinates from fir_specialized_ocr.py
CRIME_TOP = 0.38
CRIME_BOTTOM = 0.451
CRIME_LEFT = 0.29
CRIME_RIGHT = 0.62

print("="*70)
print("SAVING CRIME AREA REGION CROPS")
print(f"Region: left={CRIME_LEFT}, right={CRIME_RIGHT}, top={CRIME_TOP}, bottom={CRIME_BOTTOM}")
print("="*70)

for fir_name in FIRS:
    fir_path = os.path.join(FIR_DIR, fir_name)
    if not os.path.exists(fir_path):
        print(f"\n{fir_name}: NOT FOUND")
        continue
    
    img = cv2.imread(fir_path)
    h, w = img.shape[:2]
    
    y1 = int(h * CRIME_TOP)
    y2 = int(h * CRIME_BOTTOM)
    x1 = int(w * CRIME_LEFT)
    x2 = int(w * CRIME_RIGHT)
    
    region = img[y1:y2, x1:x2]
    rh, rw = region.shape[:2]
    
    out_name = f"_region_{fir_name.replace('.jpg','')}.png"
    cv2.imwrite(out_name, region)
    
    # Also save full image with rectangle drawn on it
    marked = img.copy()
    cv2.rectangle(marked, (x1, y1), (x2, y2), (0, 0, 255), 3)
    marked_name = f"_marked_{fir_name.replace('.jpg','')}.png"
    cv2.imwrite(marked_name, marked)
    
    print(f"{fir_name} ({w}x{h}) -> crop ({x1},{y1})-({x2},{y2}) = {rw}x{rh}px")
    print(f"  Saved: {out_name}, {marked_name}")

print("\nDone! Open the _region_*.png and _marked_*.png files to inspect.")
