"""Analyze header region of FIR to understand OCR output"""
import cv2
import easyocr
import sys

# Load the FIR image
img_path = sys.argv[1] if len(sys.argv) > 1 else r'D:\FYP\Project\CrimeVision\OCRModel\app\data\raw\FIR_001.png'
img = cv2.imread(img_path)
h, w = img.shape[:2]
print(f'Image size: {w}x{h}')

# Extract header region (top 15% of image)
header = img[0:int(h*0.15), :]
cv2.imwrite('debug_full_header.png', header)
print('Saved: debug_full_header.png')

# Initialize EasyOCR
print('\nInitializing EasyOCR...')
reader = easyocr.Reader(['ur', 'en'], gpu=False)

# Read all text from header
print('\nRunning OCR on header...')
results = reader.readtext(header, paragraph=False)

print('\n' + '='*60)
print('ALL TEXT DETECTED IN HEADER')
print('='*60)
for i, (bbox, text, conf) in enumerate(results):
    x_center = (bbox[0][0] + bbox[2][0]) / 2
    y_center = (bbox[0][1] + bbox[2][1]) / 2
    print(f'[{i:2d}] "{text}" (conf={conf:.2f}) at x={x_center:.0f}, y={y_center:.0f}')

# Also try with just Urdu
print('\n' + '='*60)
print('TRYING URDU-ONLY OCR')
print('='*60)
reader_ur = easyocr.Reader(['ur'], gpu=False)
results_ur = reader_ur.readtext(header, paragraph=False)
for i, (bbox, text, conf) in enumerate(results_ur):
    print(f'[{i:2d}] "{text}" (conf={conf:.2f})')
