"""Smart dash detection: find where dash starts using row-based analysis"""
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

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "crime_smart_split")
os.makedirs(OUT_DIR, exist_ok=True)

print("="*70)
print("SMART DASH DETECTION - Find where dash starts")
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
    
    # The dash is thin horizontal lines in the MIDDLE vertical band
    # Focus on the middle 40% of height (where dash line sits)
    mid_y1 = int(rh * 0.30)
    mid_y2 = int(rh * 0.70)
    mid_strip = gray[mid_y1:mid_y2, :]
    
    # Binary threshold
    _, mid_bin = cv2.threshold(mid_strip, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
    # Column-wise sum of black pixels in this middle strip
    col_density = np.sum(mid_bin, axis=0) / 255
    
    # The dash area has LOW density (just thin dashes) compared to text areas
    # Text areas have HIGH density (thick Urdu strokes)
    
    # Smooth heavily
    win = max(20, rw // 30)
    col_smooth = np.convolve(col_density, np.ones(win)/win, mode='same')
    
    # Find where density drops significantly (transition from text to dash)
    max_density = np.max(col_smooth)
    mean_density = np.mean(col_smooth)
    
    # The dash region has very low density - find the boundary
    # Scan from RIGHT to LEFT (since Urdu text starts from right)
    # First high-density region = location text
    # Then drops to dash level
    
    text_threshold = mean_density * 0.5
    dash_threshold = mean_density * 0.3
    
    # Find the rightmost text block boundary (where text ends going left)
    in_text = False
    text_end_x = rw // 2  # default to middle
    
    for col_x in range(rw - 1, 0, -1):
        if col_smooth[col_x] > text_threshold:
            if not in_text:
                in_text = True
        elif in_text and col_smooth[col_x] < dash_threshold:
            # Transition from text to non-text (going leftward)
            # Check if this is sustained (not a brief gap between words)
            # Look ahead 30+ pixels
            lookahead = min(col_x, max(30, rw // 30))
            avg_ahead = np.mean(col_smooth[max(0, col_x - lookahead):col_x])
            if avg_ahead < dash_threshold:
                text_end_x = col_x
                break
    
    print(f"  Text ends at x={text_end_x}/{rw} ({text_end_x/rw*100:.0f}% from left)")
    
    # Add small margin
    cut_x = max(0, text_end_x - int(rw * 0.02))
    
    # Crop right portion (location text only) 
    right_part = region[:, cut_x:]
    
    cv2.imwrite(os.path.join(OUT_DIR, f"{fir_name.split('.')[0]}_location.png"), right_part)
    
    # Draw split line
    marked = region.copy()
    cv2.line(marked, (cut_x, 0), (cut_x, rh), (0, 0, 255), 3)
    cv2.imwrite(os.path.join(OUT_DIR, f"{fir_name.split('.')[0]}_marked.png"), marked)
    
    # OCR the right portion
    rg = cv2.cvtColor(right_part, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(rg, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    txt = pytesseract.image_to_string(thresh, lang='urd', config='--psm 6 --oem 1').strip().replace('\n', ' ')
    
    # Also try raw
    txt_raw = pytesseract.image_to_string(rg, lang='urd', config='--psm 6 --oem 1').strip().replace('\n', ' ')
    
    print(f"  Location crop: {right_part.shape[1]}x{right_part.shape[0]}px")
    print(f"  OCR (thresh):  [{txt[:100]}]")
    print(f"  OCR (raw):     [{txt_raw[:100]}]")

print(f"\nAll crops saved to: {OUT_DIR}")
print("Done!")
