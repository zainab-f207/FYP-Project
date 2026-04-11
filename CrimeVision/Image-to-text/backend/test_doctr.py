"""Test doctr (Mindee) OCR on crime area - uses deep learning models (~50MB)"""
import os
import sys
import time
import cv2
import numpy as np

print("=" * 60)
print("DOCTR OCR TEST - Crime Area Region")
print("=" * 60)

img_path = "crime_area_best.png"
if not os.path.exists(img_path):
    print(f"ERROR: {img_path} not found")
    sys.exit(1)

img = cv2.imread(img_path)
h, w = img.shape[:2]
print(f"Image: {w}x{h}")

# Import doctr
print("\nLoading doctr models...")
t0 = time.time()

from doctr.io import DocumentFile
from doctr.models import ocr_predictor

# Use multilingual/Arabic model if available
try:
    # Try Arabic-specific model first
    model = ocr_predictor(det_arch='db_resnet50', reco_arch='crnn_mobilenet_v3_large', pretrained=True)
    print(f"Loaded default model in {time.time()-t0:.1f}s")
except Exception as e:
    print(f"Error loading model: {e}")
    sys.exit(1)

# Test 1: Direct on original image
print("\n--- Test 1: Original image ---")
doc = DocumentFile.from_images([img_path])
t1 = time.time()
result = model(doc)
print(f"OCR time: {time.time()-t1:.1f}s")

# Extract text
for page in result.pages:
    for block in page.blocks:
        for line in block.lines:
            text = " ".join([w.value for w in line.words])
            confs = [w.confidence for w in line.words]
            avg_conf = sum(confs) / len(confs) if confs else 0
            print(f"  Line [conf={avg_conf:.3f}]: {text}")
            print(f"    Words: {[(w.value, f'{w.confidence:.2f}') for w in line.words]}")

full_text = result.render()
print(f"\nFULL TEXT: {full_text}")

# Test 2: Preprocessed images
print("\n\n--- Testing preprocessed variants ---")
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

preprocessed = {}

# Otsu
_, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
preprocessed['otsu'] = otsu

# Denoised + Otsu
denoised = cv2.fastNlMeansDenoising(gray, None, h=10, templateWindowSize=7, searchWindowSize=21)
_, dn_otsu = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
preprocessed['dn_otsu'] = dn_otsu

# Sharpen
kernel_sharp = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
sharpened = cv2.filter2D(denoised, -1, kernel_sharp)
preprocessed['sharp'] = sharpened

# CLAHE
clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
enhanced = clahe.apply(gray)
preprocessed['clahe'] = enhanced

# 2x upscale + denoise + otsu
scaled2x = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
dn2x = cv2.fastNlMeansDenoising(scaled2x, None, h=10)
_, otsu2x = cv2.threshold(dn2x, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
preprocessed['2x_dn_otsu'] = otsu2x

for name, proc_img in preprocessed.items():
    print(f"\n--- Variant: {name} ---")
    # Save temp file for doctr
    temp_path = f"temp_doctr_{name}.png"
    cv2.imwrite(temp_path, proc_img)
    
    doc = DocumentFile.from_images([temp_path])
    t2 = time.time()
    result = model(doc)
    elapsed = time.time() - t2
    
    lines = []
    for page in result.pages:
        for block in page.blocks:
            for line in block.lines:
                text = " ".join([w.value for w in line.words])
                confs = [w.confidence for w in line.words]
                avg_conf = sum(confs) / len(confs) if confs else 0
                lines.append((text, avg_conf))
    
    full = result.render().strip()
    print(f"  Time: {elapsed:.1f}s, Lines: {len(lines)}")
    for text, conf in lines:
        print(f"  [conf={conf:.3f}]: {text}")
    print(f"  FULL: {full[:200]}")
    
    # Cleanup
    os.remove(temp_path)

print("\n\nDONE!")
