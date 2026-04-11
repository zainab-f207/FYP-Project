"""Scan FIR_004.png to find Gulshan Ravi text"""
import cv2
import numpy as np
import easyocr
import sys

# Load image
img_path = sys.argv[1] if len(sys.argv) > 1 else r"D:\FYP\Project\CrimeVision\OCRModel\app\data\raw\FIR_004.png"
img = cv2.imread(img_path)
h, w = img.shape[:2]
print(f'Image size: {w}x{h}')

reader = easyocr.Reader(['ur', 'en'])

# Extract different regions to find thana
regions = [
    ('row2_right', 0.03, 0.06, 0.55, 0.98),  # Very top, right side
    ('row3_right', 0.05, 0.08, 0.55, 0.98),  # Top area  
    ('row4', 0.06, 0.10, 0.00, 0.98),  # Full row
    ('thana_cell', 0.03, 0.08, 0.70, 0.98),  # Thana cell area
    ('full_top', 0.02, 0.12, 0.00, 1.00),  # Full top header
]

for name, top, bottom, left, right in regions:
    y1 = int(h * top)
    y2 = int(h * bottom)
    x1 = int(w * left)
    x2 = int(w * right)
    
    region = img[y1:y2, x1:x2]
    cv2.imwrite(f'debug_{name}.png', region)
    
    print(f'\n=== {name} (y={top}-{bottom}, x={left}-{right}) ===')
    
    results = reader.readtext(region, paragraph=False)
    for bbox, text, conf in results:
        if len(text.strip()) > 1:
            urdu = any('\u0600' <= c <= '\u06FF' for c in text)
            marker = "U" if urdu else "E"
            print(f'  [{marker}] {text.strip()} (conf={conf:.2f})')
            
            # Check for Gulshan Ravi patterns
            if any(p in text for p in ['گلشن', 'راوی', 'مرادی', 'Gulshan', 'Ravi']):
                print(f'    ^^^ POTENTIAL MATCH')
