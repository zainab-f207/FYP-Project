"""Test FIR section extraction"""
import cv2
import sys
import gc

# Test mode
if len(sys.argv) > 1 and sys.argv[1] == 'fir':
    from fir_specialized_ocr import FIRExtractor
    extractor = FIRExtractor()

    for fir in ['FIR_001', 'FIR_004', 'FIR_006', 'FIR_010', 'FIR_014', 'FIR_015', 'FIR_15', 'FIR_16', 'FIR_13']:
        img = cv2.imread(f'D:/FYP/Project/CrimeVision/OCRModel/app/data/raw/{fir}.png')
        if img is None:
            print(f'{fir}: ERROR - Image not loaded')
        else:
            sections = extractor.extract_sections(img)
            del img  # Free memory immediately
            gc.collect()  # Force garbage collection
            print(f'{fir}: {sections}')
    sys.exit(0)

# Region test mode
import easyocr
import re

img_path = sys.argv[1] if len(sys.argv) > 1 else 'check_region_001.png'
img = cv2.imread(img_path)
if img is None:
    print(f"ERROR: Cannot load {img_path}")
    sys.exit(1)

h, w = img.shape[:2]
print(f'Region size: {w}x{h}')

if w > 1200:
    scale = 1000 / w
    img = cv2.resize(img, None, fx=scale, fy=scale)
    print(f'Downscaled to: {img.shape[1]}x{img.shape[0]}')

print('\n=== ENGLISH ONLY ===')
reader_en = easyocr.Reader(['en'], gpu=False, verbose=False)
results_en = reader_en.readtext(img)
for bbox, text, conf in results_en:
    has_digits = any(c.isdigit() for c in text)
    marker = '***' if has_digits else '   '
    print(f'{marker} "{text}" (conf: {conf:.2f})')

print('\n=== URDU + ENGLISH ===')
reader_ur = easyocr.Reader(['en', 'ur'], gpu=False, verbose=False)
results_ur = reader_ur.readtext(img)
for bbox, text, conf in results_ur:
    has_digits = any(c.isdigit() for c in text)
    marker = '***' if has_digits else '   '
    print(f'{marker} "{text}" (conf: {conf:.2f})')

