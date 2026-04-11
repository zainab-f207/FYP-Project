"""Debug: Try cropping at vertical line before OCR"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cv2
import numpy as np
import pytesseract

FIR_DIR = r"D:\FYP\FIR_Images\upload"
FIRS = ['FIR_001.jpg', 'FIR_006.jpg', 'FIR_010.jpg', 'FIR_014.jpg', 'FIR_015.jpg']

CRIME_TOP = 0.38
CRIME_BOTTOM = 0.451
CRIME_LEFT = 0.29
CRIME_RIGHT = 0.62

print("="*70)
print("TESTING: Crop at vertical line, then OCR right side only")
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
    print(f"{fir_name} - region {rw}x{rh}px")
    
    # Detect vertical line
    edges = cv2.Canny(gray, 50, 150)
    lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=30, 
                            minLineLength=int(rh*0.5), maxLineGap=5)
    
    vert_line_x = None
    if lines is not None:
        for line in lines:
            lx1, ly1, lx2, ly2 = line[0]
            # Vertical line: x1 ≈ x2 and covers most of height
            if abs(lx1 - lx2) < 10 and abs(ly2 - ly1) > rh * 0.4:
                # Take the rightmost vertical line that's not at the very edge
                if lx1 < rw * 0.95:  # Not at right border
                    if vert_line_x is None or lx1 > vert_line_x:
                        vert_line_x = lx1
    
    if vert_line_x is not None:
        print(f"  Vertical line at x={vert_line_x}/{rw}")
        # In Urdu (RTL), text BEFORE dash is on the RIGHT side
        # But the right side of image = right side of cell
        # Actually, let me check: the vertical line separates two columns
        # Right of vertical line = usually the row label
        # Left of vertical line = the data
        
        # Crop LEFT of vertical line (the data portion, not the label)
        right_part = region[:, :vert_line_x-5]
        left_part = region[:, vert_line_x+5:]
        
        # Save both for inspection
        cv2.imwrite(f"_crime_left_{fir_name.replace('.jpg','')}.png", right_part)
        cv2.imwrite(f"_crime_right_{fir_name.replace('.jpg','')}.png", left_part)
        
        # OCR both
        for name, part in [("LEFT_OF_LINE", right_part), ("RIGHT_OF_LINE", left_part)]:
            if part.shape[1] < 10:
                continue
            g = cv2.cvtColor(part, cv2.COLOR_BGR2GRAY)
            sf = 4 if rh < 100 else 3
            sc = cv2.resize(g, None, fx=sf, fy=sf, interpolation=cv2.INTER_CUBIC)
            dn = cv2.fastNlMeansDenoising(sc, None, h=10)
            bl = cv2.GaussianBlur(dn, (3,3), 0)
            _, ot = cv2.threshold(bl, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            txt = pytesseract.image_to_string(ot, lang='urd', config='--psm 6 --oem 1')
            print(f"  {name} ({part.shape[1]}x{part.shape[0]}): [{txt.strip()[:100]}]")
    else:
        print(f"  No vertical line found")
        # Try OCR on full region
        sf = 4 if rh < 100 else 3
        sc = cv2.resize(gray, None, fx=sf, fy=sf, interpolation=cv2.INTER_CUBIC)
        dn = cv2.fastNlMeansDenoising(sc, None, h=10)
        bl = cv2.GaussianBlur(dn, (3,3), 0)
        _, ot = cv2.threshold(bl, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        txt = pytesseract.image_to_string(ot, lang='urd', config='--psm 6 --oem 1')
        print(f"  FULL: [{txt.strip()[:100]}]")

print("\nDone! Check _crime_left_*.png and _crime_right_*.png")
