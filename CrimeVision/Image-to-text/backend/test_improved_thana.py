"""Test the improved thana extraction"""
import cv2
import sys
import logging

# Setup logging to see detailed output
logging.basicConfig(level=logging.INFO, format='%(message)s')

# Import the FIR OCR module
from fir_specialized_ocr import FIRExtractor

# Test on FIR_001
img_path = r'D:\FYP\Project\CrimeVision\OCRModel\app\data\raw\FIR_001.png'
print(f"Testing on: {img_path}")
print("=" * 70)

# Load image
img = cv2.imread(img_path)
if img is None:
    print(f"ERROR: Could not load {img_path}")
    sys.exit(1)

print(f"Image size: {img.shape[1]}x{img.shape[0]}")

# Initialize OCR (with debug mode)
print("\nInitializing FIR OCR...")
ocr = FIRExtractor(debug_mode=True)

# Extract thana
print("\n" + "=" * 70)
print("EXTRACTING THANA")
print("=" * 70)
thana = ocr.extract_thana(img)

print("\n" + "=" * 70)
print(f"RESULT: Thana = '{thana}'")
print("=" * 70)

# Test on another FIR
print("\n\n" + "=" * 70)
print("TESTING ON FIR_002")
print("=" * 70)

img_path2 = r'D:\FYP\Project\CrimeVision\OCRModel\app\data\raw\FIR_002.png'
img2 = cv2.imread(img_path2)
if img2 is not None:
    print(f"Image size: {img2.shape[1]}x{img2.shape[0]}")
    thana2 = ocr.extract_thana(img2)
    print(f"\nRESULT: Thana = '{thana2}'")
else:
    print("Could not load FIR_002")
