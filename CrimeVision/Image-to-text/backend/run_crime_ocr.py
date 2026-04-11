"""Run crime area OCR on FIR images with updated region"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cv2
import numpy as np
from fir_specialized_ocr import FIRExtractor, FIRRegions

FIR_DIR = r"F:\FYP2\Project\CrimeVision\OCRModel\app\data\raw"
FIRS = ['FIR_001.png', 'FIR_006.png', 'FIR_010.png', 'FIR_014.png', 'FIR_015.png']

ocr = FIRExtractor(debug_mode=True)
regions = FIRRegions()

# Output folder for cropped regions
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "crime_region_crops")
os.makedirs(OUT_DIR, exist_ok=True)

print("="*70)
print("RUNNING CRIME AREA OCR WITH UPDATED REGION")
print(f"Region: TOP={regions.CRIME_AREA_TOP}, BOTTOM={regions.CRIME_AREA_BOTTOM}, LEFT={regions.CRIME_AREA_LEFT}, RIGHT={regions.CRIME_AREA_RIGHT}")
print(f"Saving cropped regions to: {OUT_DIR}")
print("="*70)

for fir_name in FIRS:
    fir_path = os.path.join(FIR_DIR, fir_name)
    if not os.path.exists(fir_path):
        print(f"\n{fir_name}: NOT FOUND")
        continue
    img = cv2.imread(fir_path)
    h, w = img.shape[:2]
    
    # Crop the crime area region
    y1 = int(h * regions.CRIME_AREA_TOP)
    y2 = int(h * regions.CRIME_AREA_BOTTOM)
    x1 = int(w * regions.CRIME_AREA_LEFT)
    x2 = int(w * regions.CRIME_AREA_RIGHT)
    crime_region = img[y1:y2, x1:x2]
    
    # Save only the cropped region (full)
    base = os.path.splitext(fir_name)[0]
    crop_path = os.path.join(OUT_DIR, f"{base}_crime_region.png")
    cv2.imwrite(crop_path, crime_region)
    
    # Also save the right-side-only crop (what OCR actually reads)
    # Replicate the split logic from extract_crime_area
    gray_full = cv2.cvtColor(crime_region, cv2.COLOR_BGR2GRAY)
    _, bin_full = cv2.threshold(gray_full, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    rh, rw = crime_region.shape[:2]
    mid_y1 = int(rh * 0.30)
    mid_y2 = int(rh * 0.70)
    mid_strip = bin_full[mid_y1:mid_y2, :]
    col_density = np.sum(mid_strip, axis=0) / 255
    win = max(10, rw // 40)
    col_smooth = np.convolve(col_density, np.ones(win)/win, mode='same')
    mean_d = np.mean(col_smooth)
    text_threshold = mean_d * 0.5
    gap_threshold = mean_d * 0.2
    split_x = rw // 2
    in_text = False
    for col_x in range(rw - 1, rw // 4, -1):
        if col_smooth[col_x] > text_threshold:
            in_text = True
        elif in_text and col_smooth[col_x] < gap_threshold:
            gap_len = max(15, rw // 40)
            check_start = max(0, col_x - gap_len)
            avg_ahead = np.mean(col_smooth[check_start:col_x])
            if avg_ahead < gap_threshold:
                split_x = col_x
                break
    split_x = max(int(rw * 0.35), min(int(rw * 0.60), split_x))
    
    location_crop = crime_region[:, split_x:]
    loc_path = os.path.join(OUT_DIR, f"{base}_location_only.png")
    cv2.imwrite(loc_path, location_crop)
    
    # Save marked version showing the split line
    marked = crime_region.copy()
    cv2.line(marked, (split_x, 0), (split_x, rh), (0, 0, 255), 3)
    marked_path = os.path.join(OUT_DIR, f"{base}_split_marked.png")
    cv2.imwrite(marked_path, marked)
    
    # Run OCR
    print(f"\n--- {fir_name} ({w}x{h}) | region: {rw}x{rh}px | location crop: {location_crop.shape[1]}x{location_crop.shape[0]}px ---")
    result = ocr.extract_crime_area(img)
    print(f"  RESULT: \"{result}\"")
    print(f"  SAVED:  {crop_path}")
    print(f"          {loc_path}")
    print(f"          {marked_path}")

print("\nDone!")
