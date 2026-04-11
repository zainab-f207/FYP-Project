"""Find the actual text dash separator (not table borders) and crop right side for OCR"""
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

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "crime_dash_split")
os.makedirs(OUT_DIR, exist_ok=True)

print("="*70)
print("DASH SEPARATOR DETECTION AND RIGHT-SIDE OCR")
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
    
    # ===== Find the dash separator using vertical projection =====
    # The dash is a series of short horizontal strokes with gaps
    # Use binary threshold and look at column-wise ink density
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
    # Calculate the vertical projection (sum of black pixels per column)
    vert_proj = np.sum(binary, axis=0) / 255  # Number of black pixels per column
    
    # The dash area will have a consistent moderate density across multiple columns
    # The text area will have varying high density
    # Empty area (between text and dash) will have very low density
    
    # Smooth the projection
    kernel_size = max(5, rw // 100)
    vert_proj_smooth = np.convolve(vert_proj, np.ones(kernel_size)/kernel_size, mode='same')
    
    # Find the gap between text regions (low density area)
    threshold = np.mean(vert_proj_smooth) * 0.3
    
    # Look for transition from high to low density in the middle area
    # The dash should be roughly in the middle third of the region
    mid_start = rw // 4
    mid_end = 3 * rw // 4
    
    # Find columns with very low ink in the middle region
    low_ink_cols = []
    for col in range(mid_start, mid_end):
        if vert_proj_smooth[col] < threshold:
            low_ink_cols.append(col)
    
    # Find the largest gap (consecutive low-ink columns)
    if low_ink_cols:
        gaps = []
        gap_start = low_ink_cols[0]
        prev = low_ink_cols[0]
        for col in low_ink_cols[1:]:
            if col - prev > 3:  # Allow small interruptions
                gaps.append((gap_start, prev))
                gap_start = col
            prev = col
        gaps.append((gap_start, prev))
        
        # Find the widest gap
        gaps.sort(key=lambda g: g[1]-g[0], reverse=True)
        if gaps and gaps[0][1] - gaps[0][0] > rw * 0.02:  # At least 2% of width
            gap = gaps[0]
            split_x = (gap[0] + gap[1]) // 2
            print(f"  Found gap at x={gap[0]}-{gap[1]} (width={gap[1]-gap[0]})")
            print(f"  Split point: x={split_x}/{rw}")
            
            # Right side = location (in RTL Urdu)
            right_part = region[:, split_x+5:]
            left_part = region[:, :split_x-5]
            
            cv2.imwrite(os.path.join(OUT_DIR, f"{fir_name.split('.')[0]}_right.png"), right_part)
            cv2.imwrite(os.path.join(OUT_DIR, f"{fir_name.split('.')[0]}_left.png"), left_part)
            cv2.imwrite(os.path.join(OUT_DIR, f"{fir_name.split('.')[0]}_full.png"), region)
            
            # Draw split line on region for visualization
            marked = region.copy()
            cv2.line(marked, (split_x, 0), (split_x, rh), (0, 0, 255), 3)
            cv2.imwrite(os.path.join(OUT_DIR, f"{fir_name.split('.')[0]}_marked.png"), marked)
            
            # OCR right side only
            rg = cv2.cvtColor(right_part, cv2.COLOR_BGR2GRAY)
            _, rt = cv2.threshold(rg, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            txt_right = pytesseract.image_to_string(rt, lang='urd', config='--psm 6 --oem 1').strip().replace('\n', ' ')
            
            # OCR left side
            lg = cv2.cvtColor(left_part, cv2.COLOR_BGR2GRAY)
            _, lt = cv2.threshold(lg, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            txt_left = pytesseract.image_to_string(lt, lang='urd', config='--psm 6 --oem 1').strip().replace('\n', ' ')
            
            print(f"  RIGHT (location): [{txt_right[:100]}]")
            print(f"  LEFT (distance):  [{txt_left[:100]}]")
        else:
            print(f"  No significant gap found in middle area")
    else:
        print(f"  No low-ink columns found")
    
    # Also try: look for the dash pattern using morphology
    # The dash is thin horizontal strokes - use horizontal kernel to detect
    horiz_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(20, rw//50), 1))
    horiz_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, horiz_kernel)
    
    # Find contours of horizontal line segments
    contours, _ = cv2.findContours(horiz_lines, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    dash_segments = []
    for cnt in contours:
        x, y, cw, ch = cv2.boundingRect(cnt)
        # Dash segments: wide but thin, not at borders
        if cw > rw * 0.02 and ch < rh * 0.15 and y > rh * 0.1 and y < rh * 0.9:
            if cw < rw * 0.9:  # Not a full-width border
                dash_segments.append((x, y, cw, ch))
    
    if dash_segments:
        # Sort by x position
        dash_segments.sort(key=lambda s: s[0])
        print(f"\n  Dash segments found: {len(dash_segments)}")
        for seg in dash_segments[:10]:
            print(f"    x={seg[0]}, y={seg[1]}, w={seg[2]}, h={seg[3]}")
        
        # The dash area spans from leftmost to rightmost segment
        dash_left = min(s[0] for s in dash_segments)
        dash_right = max(s[0] + s[2] for s in dash_segments)
        
        if dash_right - dash_left > rw * 0.05:
            print(f"  Dash spans: x={dash_left} to x={dash_right}")
            
            # Crop right of dash area (location text)
            right_of_dash = region[:, dash_right+10:]
            if right_of_dash.shape[1] > 50:
                cv2.imwrite(os.path.join(OUT_DIR, f"{fir_name.split('.')[0]}_morph_right.png"), right_of_dash)
                rg2 = cv2.cvtColor(right_of_dash, cv2.COLOR_BGR2GRAY)
                _, rt2 = cv2.threshold(rg2, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                txt = pytesseract.image_to_string(rt2, lang='urd', config='--psm 6 --oem 1').strip().replace('\n', ' ')
                print(f"  MORPH RIGHT: [{txt[:100]}]")

print(f"\nAll crops saved to: {OUT_DIR}")
print("Done!")
