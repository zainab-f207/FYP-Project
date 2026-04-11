"""Comprehensive OCR quality test for crime area region"""
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

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "crime_debug_crops")
os.makedirs(OUT_DIR, exist_ok=True)

# Check if EasyOCR is available
try:
    import easyocr
    EASYOCR_AVAILABLE = True
    easy_reader = easyocr.Reader(['ur', 'en'], gpu=False)
    print("EasyOCR: Available")
except:
    EASYOCR_AVAILABLE = False
    print("EasyOCR: Not available")

print("="*70)
print("TESTING MULTIPLE OCR APPROACHES ON CRIME AREA")
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
    gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
    
    print(f"\n{'='*60}")
    print(f"{fir_name} ({w}x{h}) -> region {rw}x{rh}px")
    
    # ===== APPROACH 1: Try to find the horizontal dash line and crop RIGHT side only =====
    print(f"\n--- Finding horizontal dash/line separator ---")
    
    # Use horizontal projection to find the dash line
    # The dash is a thin horizontal line roughly in the middle of the region
    edges = cv2.Canny(gray, 50, 150)
    
    # Look for horizontal lines
    horiz_lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=50, 
                                   minLineLength=int(rw*0.1), maxLineGap=20)
    
    dash_x_positions = []
    if horiz_lines is not None:
        for line in horiz_lines:
            lx1, ly1, lx2, ly2 = line[0]
            # Horizontal line: y1 ≈ y2
            if abs(ly1 - ly2) < 10:
                # Not at the very top/bottom border
                if ly1 > rh * 0.15 and ly1 < rh * 0.85:
                    length = abs(lx2 - lx1)
                    if length > rw * 0.05:  # At least 5% of width
                        dash_x_positions.append((min(lx1, lx2), max(lx1, lx2), ly1, length))
                        
    if dash_x_positions:
        # Sort by length (longest first)
        dash_x_positions.sort(key=lambda x: x[3], reverse=True)
        print(f"  Found {len(dash_x_positions)} horizontal lines")
        for dx in dash_x_positions[:5]:
            print(f"    x={dx[0]}-{dx[1]}, y={dx[2]}, len={dx[3]}")
        
        # The dash separates left (distance) from right (location) in RTL
        # Find the main dash - it should be roughly in the middle area
        main_dash = dash_x_positions[0]
        dash_right_x = main_dash[1]  # Right end of dash
        dash_left_x = main_dash[0]   # Left end of dash
        
        # Crop RIGHT of the dash (location text in RTL)
        right_crop = region[:, dash_right_x+10:]
        # Crop LEFT of the dash (distance text)
        left_crop = region[:, :dash_left_x-10]
        
        if right_crop.shape[1] > 50:
            cv2.imwrite(os.path.join(OUT_DIR, f"{fir_name.split('.')[0]}_right_of_dash.png"), right_crop)
            print(f"  Saved right_of_dash ({right_crop.shape[1]}x{right_crop.shape[0]})")
        if left_crop.shape[1] > 50:
            cv2.imwrite(os.path.join(OUT_DIR, f"{fir_name.split('.')[0]}_left_of_dash.png"), left_crop)
            print(f"  Saved left_of_dash ({left_crop.shape[1]}x{left_crop.shape[0]})")
    else:
        print(f"  No horizontal dash lines found")
        right_crop = region
    
    # Save full region too
    cv2.imwrite(os.path.join(OUT_DIR, f"{fir_name.split('.')[0]}_full_region.png"), region)
    
    # ===== APPROACH 2: Tesseract with different configs on the RIGHT portion =====
    print(f"\n--- Tesseract approaches ---")
    
    test_images = {
        "full": gray,
    }
    if dash_x_positions and right_crop.shape[1] > 50:
        test_images["right_only"] = cv2.cvtColor(right_crop, cv2.COLOR_BGR2GRAY)
    
    for img_name, test_gray in test_images.items():
        th, tw = test_gray.shape[:2]
        
        configs = [
            ("psm6_urd", '--psm 6 --oem 1', 'urd'),
            ("psm4_urd", '--psm 4 --oem 1', 'urd'),
            ("psm3_urd", '--psm 3 --oem 1', 'urd'),
            ("psm6_urd+eng", '--psm 6 --oem 1', 'urd+eng'),
            ("psm6_nopreprocess", '--psm 6 --oem 1', 'urd'),
        ]
        
        for cname, config, lang in configs:
            try:
                if cname == "psm6_nopreprocess":
                    # Direct OCR without any preprocessing
                    text = pytesseract.image_to_string(test_gray, lang=lang, config=config)
                else:
                    # Light preprocessing: just threshold
                    _, thresh = cv2.threshold(test_gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                    text = pytesseract.image_to_string(thresh, lang=lang, config=config)
                
                text = text.strip().replace('\n', ' ')
                if text:
                    print(f"  [{img_name}] {cname}: {text[:100]}")
            except Exception as e:
                print(f"  [{img_name}] {cname}: ERROR - {e}")
        
        # Also try with scale DOWN for high-res images
        if tw > 1000:
            scale = 0.5
            small = cv2.resize(test_gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
            _, thresh_s = cv2.threshold(small, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            text = pytesseract.image_to_string(thresh_s, lang='urd', config='--psm 6 --oem 1')
            text = text.strip().replace('\n', ' ')
            if text:
                print(f"  [{img_name}] 0.5x_scaled: {text[:100]}")
    
    # ===== APPROACH 3: EasyOCR =====
    if EASYOCR_AVAILABLE:
        print(f"\n--- EasyOCR approaches ---")
        for img_name, test_img in [("full", region)]:
            try:
                results = easy_reader.readtext(test_img)
                all_text = ' '.join([r[1] for r in results])
                print(f"  [{img_name}] EasyOCR: {all_text[:100]}")
                for r in results:
                    print(f"    conf={r[2]:.2f}: {r[1]}")
            except Exception as e:
                print(f"  [{img_name}] EasyOCR ERROR: {e}")
        
        if dash_x_positions and right_crop.shape[1] > 50:
            try:
                results = easy_reader.readtext(right_crop)
                all_text = ' '.join([r[1] for r in results])
                print(f"  [right_only] EasyOCR: {all_text[:100]}")
                for r in results:
                    print(f"    conf={r[2]:.2f}: {r[1]}")
            except Exception as e:
                print(f"  [right_only] EasyOCR ERROR: {e}")

print(f"\n\nAll debug crops saved to: {OUT_DIR}")
print("Done!")
