import cv2
import easyocr
import numpy as np
import sys
sys.path.insert(0, '.')
from fir_specialized_ocr import FIRImagePreprocessor

# Load FIR_13 image 
img = cv2.imread('D:/FYP/Project/CrimeVision/OCRModel/app/data/raw/FIR_13.png')
print('Full image shape:', img.shape)

preprocessor = FIRImagePreprocessor()

# Use right_expanded region
region = preprocessor.extract_region_percent(img, 0.15, 0.55, 0.35, 0.80)
cv2.imwrite('debug_regions/test_original.png', region)

# Try CLAHE enhancement to cut through stamp
gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
enhanced = clahe.apply(gray)
cv2.imwrite('debug_regions/test_clahe.png', enhanced)

# Try adaptive threshold
thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 21, 10)
cv2.imwrite('debug_regions/test_thresh.png', thresh)

# Try bilateral filter to remove stamp while keeping text edges
bilateral = cv2.bilateralFilter(gray, 9, 75, 75)
_, binar = cv2.threshold(bilateral, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
cv2.imwrite('debug_regions/test_bilateral.png', binar)

reader_en = easyocr.Reader(['en'], gpu=False, verbose=False)

# Downscale for OCR
def downscale(img):
    h, w = img.shape[:2] if len(img.shape) == 2 else img.shape[:2]
    if w > 1200:
        scale = 1000 / w
        return cv2.resize(img, None, fx=scale, fy=scale)
    return img

print('\n=== CLAHE Enhanced ===')
results = reader_en.readtext(downscale(cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)))
for bbox, text, conf in results:
    if any(c.isdigit() for c in text):
        print(f'"{text}" (conf: {conf:.2f})')

print('\n=== Adaptive Threshold ===')
results = reader_en.readtext(downscale(cv2.cvtColor(thresh, cv2.COLOR_GRAY2BGR)))
for bbox, text, conf in results:
    if any(c.isdigit() for c in text):
        print(f'"{text}" (conf: {conf:.2f})')

print('\n=== Bilateral + Otsu ===')
results = reader_en.readtext(downscale(cv2.cvtColor(binar, cv2.COLOR_GRAY2BGR)))
for bbox, text, conf in results:
    if any(c.isdigit() for c in text):
        print(f'"{text}" (conf: {conf:.2f})')
