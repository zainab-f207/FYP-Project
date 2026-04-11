"""
Debug: print the raw OCR text from the date+time region for a given FIR image.
Usage:
    python debug_datetime_region.py FIR_001
    python debug_datetime_region.py FIR_001 FIR_005 FIR_010
"""
import sys
import cv2
import numpy as np
import os

FIR_DIR = r"D:\FYP\FIR_Images\output"

# ── Same region confirmed by user ──────────────────────────────────────────
TOP    = 0.10
BOTTOM = 0.15
LEFT   = 0.02
RIGHT  = 0.57

def process(fir_name):
    path = os.path.join(FIR_DIR, f"{fir_name}.png")
    img = cv2.imread(path)
    if img is None:
        print(f"[SKIP] {path} not found"); return

    h, w = img.shape[:2]
    y1, y2 = int(h * TOP), int(h * BOTTOM)
    x1, x2 = int(w * LEFT), int(w * RIGHT)
    region = img[y1:y2, x1:x2]

    print(f"\n{'='*60}")
    print(f"  {fir_name}  —  region {x2-x1}×{y2-y1} px")
    print(f"{'='*60}")

    # Try EasyOCR first
    try:
        import easyocr
        reader = easyocr.Reader(['ur', 'en'], gpu=False, verbose=False)
        results = reader.readtext(region, paragraph=False, detail=1)
        print("\n[EasyOCR]")
        for bbox, text, conf in results:
            print(f"  [{conf:.2f}] {repr(text)}")
        full = " ".join(t for _, t, _ in results)
        print(f"\n  FULL TEXT: {repr(full)}")
    except Exception as e:
        print(f"[EasyOCR error] {e}")

    # Also try Tesseract
    try:
        import pytesseract
        gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
        tess_out = pytesseract.image_to_string(gray, lang='urd+eng', config='--psm 6')
        print(f"\n[Tesseract]\n  {repr(tess_out.strip())}")
    except Exception as e:
        print(f"[Tesseract error] {e}")

if __name__ == "__main__":
    firs = sys.argv[1:] if len(sys.argv) > 1 else ["FIR_001", "FIR_005", "FIR_010"]
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    for f in firs:
        process(f.replace(".png", ""))
