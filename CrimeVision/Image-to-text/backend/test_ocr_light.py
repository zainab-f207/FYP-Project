"""Lightweight crime area OCR test - Tesseract only"""
import cv2
import pytesseract
import sys
import re

# Get image path
image_path = sys.argv[1] if len(sys.argv) > 1 else r'D:\FYP\Project\CrimeVision\OCRModel\app\data\raw\FIR_001.png'

# Load test image
img = cv2.imread(image_path)
if img is None:
    print(f"ERROR: Could not load {image_path}")
    sys.exit(1)

print(f"Image: {image_path}")
print(f"Size: {img.shape[1]}x{img.shape[0]}")

h, w = img.shape[:2]

# Extract Row 4 region (crime area)
# Row 4: 36-42% vertical, 2-63% horizontal
y1, y2 = int(h * 0.36), int(h * 0.42)
x1, x2 = int(w * 0.02), int(w * 0.63)

crime_region = img[y1:y2, x1:x2]
print(f"Crime Area Region: ({x1},{y1}) to ({x2},{y2}) = {x2-x1}x{y2-y1}px")

# Save debug image
cv2.imwrite('debug_crime_area_test.png', crime_region)
print("Saved: debug_crime_area_test.png")

# Convert to grayscale
gray = cv2.cvtColor(crime_region, cv2.COLOR_BGR2GRAY)

# OCR with Tesseract
print("\n" + "="*60)
print("TESSERACT OCR RESULTS:")
print("="*60)

# Try Urdu
text_urd = pytesseract.image_to_string(gray, lang='urd', config='--psm 6')
print(f"\nUrdu (psm 6):\n{text_urd.strip()}")

text_urd4 = pytesseract.image_to_string(gray, lang='urd', config='--psm 4')
print(f"\nUrdu (psm 4):\n{text_urd4.strip()}")

# Clean the best result
best_text = text_urd if len(text_urd) > len(text_urd4) else text_urd4

# Clean: remove row labels
best_text = re.sub(r'جائے\s*وقوعہ.*$', '', best_text, flags=re.UNICODE)
best_text = re.sub(r'[-ـ—]{3,}.*$', '', best_text, flags=re.UNICODE)
best_text = ' '.join(best_text.split()).strip()

print("\n" + "="*60)
print("CLEANED RESULT:")
print("="*60)
print(f"Crime Area: {best_text}")
print("="*60)
