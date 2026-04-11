"""
Test exact preprocessing pipeline for crime area OCR:
  Grayscale → Denoise → Contrast boost → Adaptive threshold → Sharpen → Deskew
Then strong OCR + text cleanup
"""
import cv2
import sys
import os
import io
import numpy as np

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

img_path = 'crime_area_best.png'
img = cv2.imread(img_path)
if img is None:
    print(f"ERROR: Cannot load {img_path}")
    sys.exit(1)

print(f"Image: {img_path}, Size: {img.shape[1]}x{img.shape[0]}")

# ===== EXACT PIPELINE: Grayscale → Denoise → Contrast → Adaptive Thresh → Sharpen → Deskew =====

# Step 1: Grayscale
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
cv2.imwrite("pipeline_1_gray.png", gray)
print("Step 1: Grayscale done")

# Step 2: Denoise (non-local means - best for preserving text edges)
denoised = cv2.fastNlMeansDenoising(gray, None, h=12, templateWindowSize=7, searchWindowSize=21)
cv2.imwrite("pipeline_2_denoised.png", denoised)
print("Step 2: Denoise done")

# Step 3: Contrast boost (CLAHE - adaptive contrast)
clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
contrast = clahe.apply(denoised)
cv2.imwrite("pipeline_3_contrast.png", contrast)
print("Step 3: Contrast boost done")

# Step 4: Adaptive threshold (binary - critical for OCR)
thresh = cv2.adaptiveThreshold(contrast, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                cv2.THRESH_BINARY, 21, 10)
cv2.imwrite("pipeline_4_threshold.png", thresh)
print("Step 4: Adaptive threshold done")

# Step 5: Sharpen
kernel_sharp = np.array([[-1, -1, -1],
                          [-1,  9, -1],
                          [-1, -1, -1]])
sharpened = cv2.filter2D(thresh, -1, kernel_sharp)
cv2.imwrite("pipeline_5_sharpened.png", sharpened)
print("Step 5: Sharpen done")

# Step 6: Deskew
def deskew(image):
    coords = np.column_stack(np.where(image < 128))
    if len(coords) < 50:
        return image
    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
    # Only deskew small angles - large angles mean the image is fine
    if abs(angle) > 10 or abs(angle) < 0.3:
        print(f"   Deskew: skipped (angle={angle:.2f} degrees)")
        return image
    h, w = image.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    deskewed = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, 
                               borderMode=cv2.BORDER_REPLICATE)
    print(f"   Deskew angle: {angle:.2f} degrees")
    return deskewed

deskewed = deskew(sharpened)
cv2.imwrite("pipeline_6_deskewed.png", deskewed)
print("Step 6: Deskew done")

# Also try at 2x and 3x upscale BEFORE the pipeline
# And try multiple adaptive threshold settings
print("\n--- Testing upscaled + different threshold settings ---")
ocr_images = {}

for scale in [1, 2, 3]:
    if scale > 1:
        upscaled = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    else:
        upscaled = gray.copy()
    
    d = cv2.fastNlMeansDenoising(upscaled, None, h=12, templateWindowSize=7, searchWindowSize=21)
    c = clahe.apply(d)
    
    # Try different adaptive threshold block sizes and offsets
    for block in [11, 21, 31, 41, 51]:
        for offset in [5, 10, 15, 20]:
            t = cv2.adaptiveThreshold(c, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                       cv2.THRESH_BINARY, block, offset)
            s = cv2.filter2D(t, -1, kernel_sharp)
            dk = deskew(s)
            key = f'{scale}x_b{block}_o{offset}'
            ocr_images[key] = dk
    
    # Also try Otsu instead of adaptive (was best before)
    blurred = cv2.GaussianBlur(c, (3, 3), 0)
    _, otsu = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    s2 = cv2.filter2D(otsu, -1, kernel_sharp)
    dk2 = deskew(s2)
    ocr_images[f'{scale}x_otsu'] = dk2

# Add the fixed pipeline results
ocr_images['1x_pipeline'] = deskewed

# Save best candidates for visual inspection
cv2.imwrite("pipeline_2x_b21_o10.png", ocr_images.get('2x_b21_o10', deskewed))
cv2.imwrite("pipeline_2x_b31_o15.png", ocr_images.get('2x_b31_o15', deskewed))
cv2.imwrite("pipeline_2x_otsu.png", ocr_images.get('2x_otsu', deskewed))
cv2.imwrite("pipeline_3x_b31_o15.png", ocr_images.get('3x_b31_o15', deskewed))

print(f"  Total variants: {len(ocr_images)}")

# ===== OCR on all pipeline outputs =====
print("\n" + "="*60)
print("OCR RESULTS")
print("="*60)

import pytesseract

results = []
for name, ocr_img in ocr_images.items():
    try:
        text = pytesseract.image_to_string(ocr_img, lang='urd', config='--psm 6 --oem 1')
        # Text cleanup (as specified)
        text = text.replace("\n", " ").strip()
        text = ' '.join(text.split())
        if text and len(text) > 3:
            urdu = sum(1 for c in text if '\u0600' <= c <= '\u06FF')
            garbage = sum(1 for c in text if c in '[]{}()؟!@#$%^&*;:<>|\'')
            words = text.split()
            unique = len(set(words))
            total = max(len(words), 1)
            rep = unique / total
            score = urdu * rep - garbage * 5
            if len(text) > 300:
                score -= (len(text) - 300) * 0.5
            results.append({
                'name': name, 'text': text, 'urdu': urdu,
                'score': round(score, 1), 'len': len(text)
            })
    except:
        pass

results.sort(key=lambda x: x['score'], reverse=True)

print(f"\nTotal methods: {len(results)}")
print("\nTOP 15:")
print("-"*60)
for i, r in enumerate(results[:15]):
    print(f"\n#{i+1} [{r['name']}] score={r['score']}, urdu={r['urdu']}, len={r['len']}")
    print(f"  {r['text'][:250]}")

if results:
    print(f"\n\nBEST: {results[0]['name']}")
    print(f"TEXT: {results[0]['text']}")
print("="*60)
