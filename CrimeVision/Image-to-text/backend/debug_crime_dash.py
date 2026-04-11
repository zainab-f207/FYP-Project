"""Debug: Show raw OCR output for crime area to understand dash patterns"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cv2
import numpy as np

FIR_DIR = r"D:\FYP\FIR_Images\upload"
FIRS = ['FIR_001.jpg', 'FIR_006.jpg', 'FIR_010.jpg', 'FIR_014.jpg', 'FIR_015.jpg']

# Current region
CRIME_TOP = 0.38
CRIME_BOTTOM = 0.451
CRIME_LEFT = 0.29
CRIME_RIGHT = 0.62

import pytesseract

print("="*70)
print("RAW OCR OUTPUT FOR CRIME AREA (checking dash patterns)")
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
    gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
    
    # Scale up
    rh = region.shape[0]
    sf = 4 if rh < 100 else 3
    scaled = cv2.resize(gray, None, fx=sf, fy=sf, interpolation=cv2.INTER_CUBIC)
    
    # Best preprocessing
    denoised = cv2.fastNlMeansDenoising(scaled, None, h=10, templateWindowSize=7, searchWindowSize=21)
    blurred = cv2.GaussianBlur(denoised, (3, 3), 0)
    _, otsu = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # Get raw OCR
    raw_text = pytesseract.image_to_string(otsu, lang='urd', config='--psm 6 --oem 1')
    
    print(f"\n{'='*60}")
    print(f"{fir_name} ({w}x{h}) region={region.shape[1]}x{region.shape[0]}px")
    print(f"RAW TEXT:")
    print(f"  [{raw_text.strip()}]")
    print(f"\nCHAR ANALYSIS:")
    for i, c in enumerate(raw_text.strip()):
        if c in '-–—ـ_.۔،:' or ord(c) in range(0x2010, 0x2030):
            print(f"  pos={i}: char='{c}' unicode=U+{ord(c):04X} ({c.__repr__()})")
    
    # Also try to find the dash visually by looking for a long horizontal line
    print(f"\nLooking for vertical line separator in region...")
    edges = cv2.Canny(gray, 50, 150)
    # Look for vertical lines using HoughLines
    lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=30, minLineLength=region.shape[0]*0.5, maxLineGap=5)
    if lines is not None:
        for line in lines:
            x1l, y1l, x2l, y2l = line[0]
            # Check if it's roughly vertical (x1 ≈ x2)
            if abs(x1l - x2l) < 10:
                print(f"  Vertical line at x={x1l} from y={y1l} to y={y2l}")

print("\nDone!")
