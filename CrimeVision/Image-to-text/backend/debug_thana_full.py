"""Debug script to see exactly what OCR extracts from FIR_004.png"""
import sys
import cv2
import numpy as np

sys.path.insert(0, '.')
from fir_specialized_ocr import FIRExtractor

# Create extractor with debug mode
extractor = FIRExtractor()
extractor.debug_mode = True

# Load image
img_path = sys.argv[1] if len(sys.argv) > 1 else "D:/FYP/Project/CrimeVision/OCRModel/app/data/raw/FIR_004.png"
print(f"Loading image: {img_path}")

img = cv2.imread(img_path)
if img is None:
    print("Failed to load image!")
    sys.exit(1)

print(f"Image shape: {img.shape}")
print("=" * 60)

# Call extract_thana with detailed output
thana = extractor.extract_thana(img)

print("=" * 60)
print(f"FINAL THANA RESULT: {thana}")
print("=" * 60)

# Check if غالب is in the returned value
if thana:
    if "غالب" in thana:
        print("WARNING: Result contains 'غالب' (Ghalib)")
    if "گلشن" in thana or "راوی" in thana or "Gulshan" in thana.lower():
        print("GOOD: Result contains Gulshan Ravi")
