"""Quick debug for FIR_025 regression"""
import sys, os, cv2, re
sys.path.insert(0, os.path.dirname(__file__))
from fir_specialized_ocr import CRIME_STRIPS, detect_location_fragments
import pytesseract

img = cv2.imread(r'F:\FYP\Project\CrimeVision\OCRModel\app\data\raw\FIR_025.png')
h, w = img.shape[:2]
scale = 3000 / max(h, w)
img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
h, w = img.shape[:2]

for si, (y1f, y2f, x1f, x2f) in enumerate(CRIME_STRIPS[:3]):
    y1, y2 = int(h * y1f), int(h * y2f)
    x1, x2 = int(w * x1f), int(w * x2f)
    if y2 <= y1 or x2 <= x1:
        continue
    crop = img[y1:y2, x1:x2]
    rh, rw = crop.shape[:2]
    sf = 2.0 if rw > 1500 else (3.0 if rw > 800 else 4.0)
    resized = cv2.resize(crop, None, fx=sf, fy=sf, interpolation=cv2.INTER_CUBIC)
    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    raw = pytesseract.image_to_string(otsu, config='--psm 6 --oem 3 -l urd').strip()
    
    print(f"S{si}-Otsu raw ({len(raw)} chars):")
    print(f"  {raw[:200]}")
    
    # Check for key patterns
    for pat in ['غڑی', 'غری', 'شاہ', 'شاو', 'شاہدر', 'شاہدرہ']:
        pos = raw.find(pat)
        if pos >= 0:
            print(f"  FOUND '{pat}' at pos {pos}")
    
    frags = detect_location_fragments(raw, return_all=True)
    print(f"  Fragments: {frags}")
    print()
