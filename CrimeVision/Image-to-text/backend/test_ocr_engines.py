"""Test all available OCR engines on location-only crops for best quality"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cv2
import numpy as np
import pytesseract

FIR_DIR = r"F:\FYP2\Project\CrimeVision\OCRModel\app\data\raw"
FIRS = ['FIR_001.png', 'FIR_006.png', 'FIR_010.png', 'FIR_014.png', 'FIR_015.png']
CROP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "crime_region_crops")

# Try EasyOCR
try:
    import easyocr
    reader_ur = easyocr.Reader(['ur'], gpu=False)
    reader_ur_en = easyocr.Reader(['ur', 'en'], gpu=False)
    reader_ar = easyocr.Reader(['ar'], gpu=False)  # Arabic model sometimes better for Nastaliq
    EASYOCR = True
    print("EasyOCR: Available (ur, ur+en, ar)")
except Exception as e:
    EASYOCR = False
    print(f"EasyOCR: {e}")

print("="*70)

for fir_name in FIRS:
    base = fir_name.split('.')[0]
    loc_path = os.path.join(CROP_DIR, f"{base}_location_only.png")
    full_path = os.path.join(CROP_DIR, f"{base}_crime_region.png")
    
    if not os.path.exists(loc_path):
        print(f"\n{base}: location crop NOT FOUND")
        continue
    
    loc_img = cv2.imread(loc_path)
    full_img = cv2.imread(full_path)
    rh, rw = loc_img.shape[:2]
    gray = cv2.cvtColor(loc_img, cv2.COLOR_BGR2GRAY)
    
    print(f"\n{'='*60}")
    print(f"{base} - location crop {rw}x{rh}px")
    
    # ===== TESSERACT variations =====
    print("\n  --- Tesseract ---")
    
    preprocess = {
        "raw": gray,
    }
    
    # Otsu threshold
    _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    preprocess["otsu"] = otsu
    
    # Adaptive threshold
    adapt = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 10)
    preprocess["adaptive"] = adapt
    
    # Inverted (white text on black)
    preprocess["otsu_inv"] = cv2.bitwise_not(otsu)
    
    # Downscale 50% (sometimes helps with high-res)
    small = cv2.resize(gray, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)
    _, small_otsu = cv2.threshold(small, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    preprocess["0.5x_otsu"] = small_otsu
    preprocess["0.5x_raw"] = small
    
    # Denoise + Otsu
    denoised = cv2.fastNlMeansDenoising(gray, None, h=10)
    _, dn_otsu = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    preprocess["denoise_otsu"] = dn_otsu
    
    # CLAHE
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    cl = clahe.apply(gray)
    _, cl_otsu = cv2.threshold(cl, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    preprocess["clahe_otsu"] = cl_otsu
    
    # Sharpen
    kernel = np.array([[-1,-1,-1],[-1,9,-1],[-1,-1,-1]])
    sharp = cv2.filter2D(gray, -1, kernel)
    _, sharp_otsu = cv2.threshold(sharp, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    preprocess["sharp_otsu"] = sharp_otsu
    
    configs = [
        ('psm6', '--psm 6 --oem 1', 'urd'),
        ('psm4', '--psm 4 --oem 1', 'urd'),
        ('psm3', '--psm 3 --oem 1', 'urd'),
        ('psm7', '--psm 7 --oem 1', 'urd'),  # single line
        ('psm13', '--psm 13 --oem 1', 'urd'),  # raw line
    ]
    
    best_score = -1
    best_result = ""
    best_method = ""
    
    for pp_name, pp_img in preprocess.items():
        for cfg_name, cfg, lang in configs:
            try:
                text = pytesseract.image_to_string(pp_img, lang=lang, config=cfg).strip().replace('\n', ' ')
                if text:
                    # Score: count Urdu chars, penalize garbage
                    urdu = sum(1 for c in text if '\u0600' <= c <= '\u06FF')
                    garbage = sum(1 for c in text if c in '[]{}()!@#$%^&*;:<>|0123456789')
                    score = urdu - garbage * 3
                    if score > best_score:
                        best_score = score
                        best_result = text
                        best_method = f"{pp_name}+{cfg_name}"
            except:
                pass
    
    print(f"  BEST: [{best_method}] score={best_score}")
    print(f"  TEXT: {best_result[:120]}")
    
    # ===== EASYOCR =====
    if EASYOCR:
        print("\n  --- EasyOCR ---")
        for rdr_name, rdr in [("ur", reader_ur), ("ur+en", reader_ur_en), ("ar", reader_ar)]:
            for img_name, test_img in [("location", loc_img), ("loc_gray", gray)]:
                try:
                    results = rdr.readtext(test_img)
                    texts = [(r[1], r[2]) for r in results]
                    all_text = ' '.join([t[0] for t in texts])
                    avg_conf = np.mean([t[1] for t in texts]) if texts else 0
                    if all_text.strip():
                        print(f"  [{rdr_name}|{img_name}] conf={avg_conf:.2f}: {all_text[:100]}")
                except Exception as e:
                    print(f"  [{rdr_name}|{img_name}] ERROR: {e}")

print("\nDone!")
