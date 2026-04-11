"""
Test thana extraction with the updated code on multiple FIR images
"""
import cv2
import sys
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(message)s')

from fir_specialized_ocr import FIRExtractor

# Test images
test_images = [
    (r'D:\FYP\Project\CrimeVision\OCRModel\app\data\raw\FIR_001.png', "FIR_001"),
    (r'D:\FYP\Project\CrimeVision\OCRModel\app\data\raw\FIR_002.png', "FIR_002"),
    (r'D:\FYP\Project\CrimeVision\OCRModel\app\data\raw\FIR_003.png', "FIR_003"),
]

# Initialize OCR
print("Initializing FIR OCR...")
ocr = FIRExtractor(debug_mode=False)  # Disable debug mode for cleaner output

print("\n" + "=" * 70)
print("TESTING THANA EXTRACTION ON MULTIPLE FIRS")
print("=" * 70)

results = []
for img_path, name in test_images:
    print(f"\n{'-' * 50}")
    print(f"Testing: {name}")
    print(f"{'-' * 50}")
    
    img = cv2.imread(img_path)
    if img is None:
        print(f"  ERROR: Could not load {img_path}")
        results.append((name, "ERROR", "Could not load"))
        continue
    
    print(f"  Image size: {img.shape[1]}x{img.shape[0]}")
    
    # Extract thana
    thana = ocr.extract_thana(img)
    
    print(f"\n  RESULT: Thana = '{thana}'")
    results.append((name, thana, "OK"))

# Summary
print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
for name, thana, status in results:
    print(f"  {name}: '{thana}' ({status})")
