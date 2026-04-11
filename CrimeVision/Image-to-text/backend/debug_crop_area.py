"""
Diagnostic: Save the crime area region crop from FIR images 
to visualize what OCR is actually reading.
"""
import cv2
import sys
import os

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

IMAGE_DIR = r"D:\FYP\Project\CrimeVision\OCRModel\app\data\raw"
OUT_DIR = os.path.join(os.path.dirname(__file__), "debug_crops")
os.makedirs(OUT_DIR, exist_ok=True)

# Region coordinates from fir_specialized_ocr.py
CRIME_AREA_TOP = 0.38
CRIME_AREA_BOTTOM = 0.451
CRIME_AREA_LEFT = 0.29
CRIME_AREA_RIGHT = 0.62

files = sys.argv[1:] if len(sys.argv) > 1 else [
    "FIR_007.png", "FIR_011.png", "FIR_021.png", "FIR_027.png", 
    "FIR_033.png", "FIR_037.png", "FIR_101.png",
    "FIR_001.png", "FIR_014.png",  # known good for comparison
]

for fname in files:
    path = os.path.join(IMAGE_DIR, fname)
    if not os.path.exists(path):
        print(f"SKIP: {fname} not found")
        continue
    
    img = cv2.imread(path)
    if img is None:
        print(f"SKIP: {fname} failed to load")
        continue
    
    h, w = img.shape[:2]
    y1 = int(h * CRIME_AREA_TOP)
    y2 = int(h * CRIME_AREA_BOTTOM)
    x1 = int(w * CRIME_AREA_LEFT)
    x2 = int(w * CRIME_AREA_RIGHT)
    
    crop = img[y1:y2, x1:x2]
    
    out_path = os.path.join(OUT_DIR, f"crop_{fname}")
    cv2.imwrite(out_path, crop)
    print(f"OK: {fname} ({w}x{h}) -> crop ({x2-x1}x{y2-y1}) saved to {out_path}")
    
    del img
