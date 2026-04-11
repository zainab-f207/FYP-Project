"""Test TrOCR Arabic model for Urdu crime area OCR"""
import cv2
import numpy as np
import os
import time

print("="*60)
print("TrOCR ARABIC TEST - Crime Area Region")
print("="*60)

img_path = "crime_area_best.png"
img = cv2.imread(img_path)
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
print(f"Image: {img.shape[1]}x{img.shape[0]}")

# Check if transformers is available
from transformers import TrOCRProcessor, VisionEncoderDecoderModel
from PIL import Image
import torch

print(f"PyTorch: {torch.__version__}")
print(f"CUDA: {torch.cuda.is_available()}")

# TrOCR needs line-level images, so let's split Row 4 into lines
# Row 4 is 6777x921 - extract individual text lines by horizontal analysis

# First detect text line regions
h, w = gray.shape
# Apply threshold to find text
_, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

# Find horizontal projection to detect text lines
h_proj = np.sum(binary, axis=1) / 255

# Find line boundaries (rows with text pixels)
threshold = w * 0.01  # at least 1% of width has ink
in_line = h_proj > threshold
lines = []
start = None
for i, v in enumerate(in_line):
    if v and start is None:
        start = i
    elif not v and start is not None:
        if i - start > 10:  # min height 10px
            lines.append((start, i))
        start = None
if start is not None and h - start > 10:
    lines.append((start, h))

print(f"Detected {len(lines)} text lines")
for i, (y1, y2) in enumerate(lines):
    print(f"  Line {i}: y={y1}-{y2} (h={y2-y1})")

# Try a small/fast Arabic OCR model first
print("\n--- Loading Arabic TrOCR model ---")
model_name = "microsoft/trocr-base-printed"  # Start with base, will try Arabic-specific

try:
    t0 = time.time()
    processor = TrOCRProcessor.from_pretrained(model_name)
    model = VisionEncoderDecoderModel.from_pretrained(model_name)
    t1 = time.time()
    print(f"Model loaded in {t1-t0:.1f}s")
    
    # Process each line
    for i, (y1, y2) in enumerate(lines):
        pad = 5  # padding
        y1p = max(0, y1 - pad)
        y2p = min(h, y2 + pad)
        line_img = img[y1p:y2p, :, :]
        
        # Convert to PIL
        pil_img = Image.fromarray(cv2.cvtColor(line_img, cv2.COLOR_BGR2RGB))
        
        # Process
        pixel_values = processor(images=pil_img, return_tensors="pt").pixel_values
        
        with torch.no_grad():
            generated_ids = model.generate(pixel_values, max_length=128)
        
        text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
        print(f"  Line {i}: '{text}'")
    
except Exception as e:
    print(f"  ERROR with {model_name}: {e}")

# Also try the whole image
print("\n--- Whole image ---")
try:
    pil_full = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    # TrOCR expects smaller images, resize
    pil_resized = pil_full.resize((384, 384))
    pixel_values = processor(images=pil_resized, return_tensors="pt").pixel_values
    
    with torch.no_grad():
        generated_ids = model.generate(pixel_values, max_length=256)
    
    text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
    print(f"  Full: '{text}'")
except Exception as e:
    print(f"  ERROR: {e}")

print("\nDONE!")
