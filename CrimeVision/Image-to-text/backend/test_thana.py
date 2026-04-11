"""Test Thana extraction from FIR images with debug visualization"""
import cv2
import sys
import os
sys.path.insert(0, '.')
from fir_specialized_ocr import FIRExtractor, FIRRegions

# Create output folder for debug images
debug_dir = "thana_debug_regions"
os.makedirs(debug_dir, exist_ok=True)

extractor = FIRExtractor(debug_mode=True)

firs = ['FIR_001', 'FIR_004', 'FIR_006', 'FIR_010', 'FIR_014', 'FIR_015', 'FIR_15', 'FIR_16', 'FIR_13']

print("=" * 60)
print("THANA EXTRACTION TEST WITH DEBUG REGIONS")
print("=" * 60)
print(f"Debug images will be saved to: {os.path.abspath(debug_dir)}")
print()

regions = FIRRegions()

for fir in firs:
    img_path = f'D:/FYP/Project/CrimeVision/OCRModel/app/data/raw/{fir}.png'
    img = cv2.imread(img_path)
    if img is None:
        print(f'{fir}: ERROR - Image not loaded')
        continue
    
    h, w = img.shape[:2]
    
    # Save image with thana region marked
    marked = img.copy()
    y1 = int(h * regions.THANA_TOP)
    y2 = int(h * regions.THANA_BOTTOM)
    x1 = int(w * regions.THANA_LEFT)
    x2 = int(w * regions.THANA_RIGHT)
    
    # Draw thana region rectangle (cyan)
    cv2.rectangle(marked, (x1, y1), (x2, y2), (255, 255, 0), 5)
    cv2.putText(marked, f"THANA REGION", (x1, y1-15), 
                cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 0), 3)
    
    # Save marked full image (scaled down)
    scale = 0.3
    small = cv2.resize(marked, None, fx=scale, fy=scale)
    cv2.imwrite(f"{debug_dir}/{fir}_marked.png", small)
    
    # Save thana region crop
    thana_crop = img[y1:y2, x1:x2]
    cv2.imwrite(f"{debug_dir}/{fir}_thana_crop.png", thana_crop)
    
    # Extract thana
    thana = extractor.extract_thana(img)
    print(f'{fir}: {thana if thana else "NOT FOUND"}')
    print(f'  Region saved: {debug_dir}/{fir}_thana_crop.png')
    print()

print("=" * 60)
print(f"All debug images saved to: {os.path.abspath(debug_dir)}")
print("=" * 60)
