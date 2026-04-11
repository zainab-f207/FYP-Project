"""Test Surya OCR on crime area region - should be much better than Tesseract for Urdu"""
import os
import sys
import time

# Set low batch sizes for CPU/limited GPU
os.environ["RECOGNITION_BATCH_SIZE"] = "4"
os.environ["DETECTOR_BATCH_SIZE"] = "2"

from PIL import Image
import cv2
import numpy as np

print("=" * 60)
print("SURYA OCR TEST - Crime Area Region")
print("=" * 60)

# Test 1: Direct on crime_area_best.png
img_path = "crime_area_best.png"
if not os.path.exists(img_path):
    print(f"ERROR: {img_path} not found")
    sys.exit(1)

print(f"\nLoading image: {img_path}")
img = cv2.imread(img_path)
h, w = img.shape[:2]
print(f"Image size: {w}x{h}")

# Surya recommends max 2048px width
if w > 2048:
    scale = 2048 / w
    img_resized = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    print(f"Resized to: {img_resized.shape[1]}x{img_resized.shape[0]} (Surya recommends max 2048px)")
else:
    img_resized = img

# Convert to PIL
pil_img = Image.fromarray(cv2.cvtColor(img_resized, cv2.COLOR_BGR2RGB))

print("\nLoading Surya models (first run downloads ~300MB)...")
t0 = time.time()

from surya.foundation import FoundationPredictor
from surya.recognition import RecognitionPredictor
from surya.detection import DetectionPredictor

foundation = FoundationPredictor()
recognition = RecognitionPredictor(foundation)
detection = DetectionPredictor()

print(f"Models loaded in {time.time()-t0:.1f}s")

# Run OCR
print("\n--- Running Surya OCR (with detection) ---")
t1 = time.time()
predictions = recognition([pil_img], det_predictor=detection)
print(f"OCR completed in {time.time()-t1:.1f}s")

if predictions:
    pred = predictions[0]
    print(f"\nDetected {len(pred.text_lines)} text lines:")
    print("-" * 50)
    
    all_text = []
    for i, line in enumerate(pred.text_lines):
        conf = line.confidence if hasattr(line, 'confidence') else 0
        text = line.text if hasattr(line, 'text') else str(line)
        print(f"  Line {i+1} [conf={conf:.3f}]: {text}")
        all_text.append(text)
    
    full_text = " ".join(all_text)
    print(f"\n{'='*50}")
    print(f"FULL TEXT: {full_text}")
    print(f"{'='*50}")
else:
    print("No predictions returned!")

# Test 2: Also try with preprocessed versions
print("\n\n--- Testing with preprocessed images ---")
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

variants = {}

# Variant A: Denoised + contrast boost
denoised = cv2.fastNlMeansDenoising(gray, None, h=10, templateWindowSize=7, searchWindowSize=21)
clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
enhanced = clahe.apply(denoised)
variants["denoised_clahe"] = enhanced

# Variant B: Otsu binarization  
_, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
variants["otsu"] = otsu

# Variant C: Adaptive threshold
adaptive = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 51, 15)
variants["adaptive_b51_o15"] = adaptive

for name, processed in variants.items():
    # Resize if needed
    ph, pw = processed.shape[:2]
    if pw > 2048:
        scale = 2048 / pw
        processed = cv2.resize(processed, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    
    # Convert grayscale to RGB PIL
    rgb = cv2.cvtColor(processed, cv2.COLOR_GRAY2RGB)
    pil_proc = Image.fromarray(rgb)
    
    print(f"\n--- Variant: {name} ({processed.shape[1]}x{processed.shape[0]}) ---")
    t2 = time.time()
    preds = recognition([pil_proc], det_predictor=detection)
    print(f"  Time: {time.time()-t2:.1f}s")
    
    if preds and preds[0].text_lines:
        lines = []
        for line in preds[0].text_lines:
            conf = line.confidence if hasattr(line, 'confidence') else 0
            text = line.text if hasattr(line, 'text') else str(line)
            print(f"  [conf={conf:.3f}]: {text}")
            lines.append(text)
        print(f"  FULL: {' '.join(lines)}")
    else:
        print("  No text detected")

print("\n\nDONE!")
