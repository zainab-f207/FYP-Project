"""Direct comparison: batch test function vs production method, same image."""
import sys, os, cv2, re
sys.path.insert(0, os.path.dirname(__file__))

import pytesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

from fir_specialized_ocr import CRIME_STRIPS, detect_location_fragments, detect_structured_location
import fir_specialized_ocr as fir_mod

IMAGE_DIR = r'F:\FYP\Project\CrimeVision\OCRModel\app\data\raw'

# Test with FIR_006 which should extract بھاٹی گیٹ
test_image = os.path.join(IMAGE_DIR, 'FIR_006.png')
image = cv2.imread(test_image)
h, w = image.shape[:2]

print(f"Image: {w}x{h}, channels: {image.shape[2] if len(image.shape)==3 else 1}")

# === BATCH TEST LOGIC (proven working) ===
print(f"\n{'='*60}")
print("BATCH TEST LOGIC")
print(f"{'='*60}")

max_dim = max(h, w)
if max_dim > 5000:
    scale = 3000 / max_dim
    image_d = cv2.resize(image, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
else:
    image_d = image.copy()
h2, w2 = image_d.shape[:2]

for si, (y1f, y2f, x1f, x2f) in enumerate(CRIME_STRIPS):
    y1, y2 = int(h2 * y1f), int(h2 * y2f)
    x1, x2 = int(w2 * x1f), int(w2 * x2f)
    row_crop = image_d[y1:y2, x1:x2]
    rh, rw = row_crop.shape[:2]
    
    if rw > 1500: scale_factor = 2.0
    elif rw > 800: scale_factor = 3.0
    else: scale_factor = 4.0
    
    resized = cv2.resize(row_crop, None, fx=scale_factor, fy=scale_factor, interpolation=cv2.INTER_CUBIC)
    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    cl = clahe.apply(gray)
    
    # Just test PSM6 on CLAHE
    raw = pytesseract.image_to_string(cl, config='--psm 6 --oem 3 -l urd').strip()
    if raw:
        short = raw[:80].replace('\n', ' ')
        frags = detect_location_fragments(raw, return_all=True)
        print(f"  S{si}-PSM6 [{rh}x{rw} scale={scale_factor}]: {short}")
        if frags:
            print(f"    -> FRAGS: {frags}")

# === PRODUCTION METHOD LOGIC ===
print(f"\n{'='*60}")
print("PRODUCTION METHOD LOGIC")
print(f"{'='*60}")


class LightOCR:
    @staticmethod
    def extract_crime_area(*args, **kwargs):
        return fir_mod.FIRExtractor.extract_crime_area(*args, **kwargs)
    @staticmethod
    def _clean_crime_area_text(*args, **kwargs):
        return fir_mod.FIRExtractor._clean_crime_area_text(*args, **kwargs)

ocr = LightOCR()
result = ocr.extract_crime_area(image)
print(f"\nProduction result: '{result}'")

# === ALSO TEST: what if we call extract_crime_area_standalone from batch test? ===
print(f"\n{'='*60}")
print("STANDALONE FUNCTION (batch_test_first_part.py)")
print(f"{'='*60}")

from batch_test_first_part import extract_crime_area_standalone
result2 = extract_crime_area_standalone(test_image)
print(f"Standalone result: '{result2}'")
