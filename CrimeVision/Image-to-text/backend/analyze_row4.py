"""Analyze the location row (Row 4) of FIR to find thana name"""
import cv2
import easyocr
import sys
import re

# Load the FIR image
img_path = sys.argv[1] if len(sys.argv) > 1 else r'D:\FYP\Project\CrimeVision\OCRModel\app\data\raw\FIR_001.png'
img = cv2.imread(img_path)
h, w = img.shape[:2]
print(f'Image size: {w}x{h}')

# Extract Row 4 region (location row) - approximately 38-48% from top
# This row contains "اقبال ٹاؤن سے 2.8 کلومیٹر..." pattern
row4_top = int(h * 0.38)
row4_bottom = int(h * 0.48)
row4 = img[row4_top:row4_bottom, :]
cv2.imwrite('debug_row4_location.png', row4)
print(f'Extracted Row 4: y={row4_top}-{row4_bottom}')
print('Saved: debug_row4_location.png')

# Initialize EasyOCR
print('\nInitializing EasyOCR...')
reader = easyocr.Reader(['ur', 'en'], gpu=False)

# Read all text from Row 4
print('\nRunning OCR on Row 4 (location row)...')
results = reader.readtext(row4, paragraph=False)

print('\n' + '='*60)
print('ALL TEXT IN ROW 4 (LOCATION ROW)')
print('='*60)
for i, (bbox, text, conf) in enumerate(results):
    print(f'[{i:2d}] "{text}" (conf={conf:.2f})')

# Look for "ٹاؤن" pattern
print('\n' + '='*60)
print('SEARCHING FOR TOWN PATTERNS')
print('='*60)

combined_text = ' '.join([r[1] for r in results])
print(f'Combined text: {combined_text}')

# Patterns to find thana name
patterns = [
    r'(\S+)\s*ٹاؤن',           # X ٹاؤن
    r'(\S+)\s*[Tt]own',         # X Town
    r'(\S+)\s*سے\s*[\d\.]+',    # X سے 2.8 (X is likely the thana)
]

for pattern in patterns:
    matches = re.findall(pattern, combined_text)
    if matches:
        print(f'Pattern "{pattern}": {matches}')

# Also try full Urdu search
print('\n' + '='*60)
print('LOOKING FOR KNOWN LAHORE THANAS')
print('='*60)

known_thanas = [
    "اقبال ٹاؤن", "Iqbal Town", "ماڈل ٹاؤن", "Model Town", 
    "گلبرگ", "Gulberg", "جوہر ٹاؤن", "Johar Town",
    "صدر", "Saddar", "کینٹ", "Cantt", "ڈیفنس", "Defence",
    "شفیق آباد", "Shafiqabad", "شالیمار", "Shalimar",
]

for thana in known_thanas:
    if thana.lower() in combined_text.lower():
        print(f'FOUND: {thana}')
