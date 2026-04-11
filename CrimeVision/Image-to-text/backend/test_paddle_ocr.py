"""Test PaddleOCR on crime area region - Arabic/Urdu text"""
import cv2
import numpy as np
import os
import time

os.environ['DISABLE_MODEL_SOURCE_CHECK'] = 'True'

print("="*60)
print("PADDLEOCR TEST - Crime Area Region (Urdu/Arabic)")
print("="*60)

img_path = "crime_area_best.png"
img = cv2.imread(img_path)
if img is None:
    print(f"ERROR: Cannot load {img_path}")
    exit(1)
print(f"Original: {img.shape[1]}x{img.shape[0]}")

from paddleocr import PaddleOCR

# Pre-resize to stay within limits 
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

# Try different sizes
for target_w in [2000, 3000, 3800]:
    scale = target_w / img.shape[1]
    img_s = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    tmp = f"_p_{target_w}.png"
    cv2.imwrite(tmp, img_s)
    print(f"\n--- Arabic, {target_w}px ({img_s.shape[1]}x{img_s.shape[0]}) ---")
    
    try:
        ocr = PaddleOCR(lang='ar', use_doc_orientation_classify=False, use_doc_unwarping=False)
        result = list(ocr.predict(tmp))
        for res in result:
            texts = getattr(res, 'rec_texts', [])
            scores = getattr(res, 'rec_scores', [])
            for t, s in zip(texts, scores):
                print(f"  [{s:.3f}] {t}")
            if texts:
                print(f"  FULL: {' '.join(texts)}")
            else:
                print("  No text found")
    except Exception as e:
        print(f"  ERROR: {e}")
    
    os.remove(tmp)

# Also try with preprocessing on best size
print(f"\n--- Preprocessed variants at 2000px ---")
scale = 2000 / img.shape[1]
gray_s = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

variants = {}
# Denoise
dn = cv2.fastNlMeansDenoising(gray_s, None, 10, 7, 21)
variants['denoise'] = dn
# CLAHE
clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8)).apply(gray_s)
variants['clahe'] = clahe
# Otsu
_, otsu = cv2.threshold(gray_s, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
variants['otsu'] = otsu
# Denoise+Otsu
_, dn_otsu = cv2.threshold(dn, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
variants['dn_otsu'] = dn_otsu

ocr = PaddleOCR(lang='ar', use_doc_orientation_classify=False, use_doc_unwarping=False)
for name, v in variants.items():
    tmp = f"_p_{name}.png"
    cv2.imwrite(tmp, v)
    print(f"\n  {name}:")
    try:
        result = list(ocr.predict(tmp))
        for res in result:
            texts = getattr(res, 'rec_texts', [])
            scores = getattr(res, 'rec_scores', [])
            for t, s in zip(texts, scores):
                print(f"    [{s:.3f}] {t}")
            if texts:
                print(f"    FULL: {' '.join(texts)}")
            else:
                print("    No text")
    except Exception as e:
        print(f"    ERROR: {e}")
    os.remove(tmp)

print("\nDONE!")
