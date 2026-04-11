"""
Simplified advanced preprocessing for thana text
"""
import cv2
import numpy as np
import easyocr
import gc

# Load FIR image
img_path = r'D:\FYP\Project\CrimeVision\OCRModel\app\data\raw\FIR_001.png'
img = cv2.imread(img_path)

h, w = img.shape[:2]
print(f"Image size: {w}x{h}")

# Extract the thana region (Row 3, x=75%-92%)
y1, y2 = int(h * 0.10), int(h * 0.16)
x1, x2 = int(w * 0.75), int(w * 0.92)
thana_region = img[y1:y2, x1:x2]

print(f"Thana region: {thana_region.shape[1]}x{thana_region.shape[0]}px")

# Initialize EasyOCR
print("\nInitializing EasyOCR...")
reader = easyocr.Reader(['ur', 'en'], gpu=False)

# Convert to grayscale
gray = cv2.cvtColor(thana_region, cv2.COLOR_BGR2GRAY)

# Try 3x upscale (not too large)
upscaled = cv2.resize(gray, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)

print("\n" + "=" * 70)
print("TESTING PREPROCESSING METHODS")
print("=" * 70)

# 1. Raw upscaled
print("\n1. Raw upscaled (3x):")
results = reader.readtext(upscaled, paragraph=False)
for _, text, conf in results:
    if len(text.strip()) >= 2:
        print(f"   '{text}' (conf={conf:.2f})")

gc.collect()

# 2. CLAHE
print("\n2. CLAHE enhanced:")
clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
enhanced = clahe.apply(upscaled)
cv2.imwrite("test_clahe.png", enhanced)
results = reader.readtext(enhanced, paragraph=False)
for _, text, conf in results:
    if len(text.strip()) >= 2:
        print(f"   '{text}' (conf={conf:.2f})")

gc.collect()

# 3. Denoised + CLAHE
print("\n3. Denoised + CLAHE:")
denoised = cv2.fastNlMeansDenoising(upscaled, None, h=8)
denoised_enhanced = clahe.apply(denoised)
cv2.imwrite("test_denoised_clahe.png", denoised_enhanced)
results = reader.readtext(denoised_enhanced, paragraph=False)
for _, text, conf in results:
    if len(text.strip()) >= 2:
        print(f"   '{text}' (conf={conf:.2f})")

gc.collect()

# 4. Binary + invert
print("\n4. Binary threshold:")
_, binary = cv2.threshold(upscaled, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
cv2.imwrite("test_binary.png", binary)
results = reader.readtext(binary, paragraph=False)
for _, text, conf in results:
    if len(text.strip()) >= 2:
        print(f"   '{text}' (conf={conf:.2f})")

gc.collect()

# 5. Bilateral filter
print("\n5. Bilateral filter:")
bilateral = cv2.bilateralFilter(thana_region, 9, 75, 75)
bilateral_gray = cv2.cvtColor(bilateral, cv2.COLOR_BGR2GRAY)
bilateral_up = cv2.resize(bilateral_gray, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
cv2.imwrite("test_bilateral.png", bilateral_up)
results = reader.readtext(bilateral_up, paragraph=False)
for _, text, conf in results:
    if len(text.strip()) >= 2:
        print(f"   '{text}' (conf={conf:.2f})")

print("\n" + "=" * 70)
print("Now trying Tesseract...")
print("=" * 70)

import pytesseract

# Best preprocessing for Tesseract
_, binary_tess = cv2.threshold(denoised_enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
cv2.imwrite("test_binary_tess.png", binary_tess)

print("\nTesseract results:")
for psm in [6, 7, 11]:
    text = pytesseract.image_to_string(binary_tess, lang='urd', config=f'--psm {psm}')
    text = text.strip().replace('\n', ' ')
    if text:
        print(f"   PSM {psm}: '{text}'")

print("\nDone!")
