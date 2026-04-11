"""Find where thana information actually is in the FIR by scanning all rows"""
import cv2
import numpy as np
import pytesseract
import easyocr
import re

# Load FIR image
img_path = r'D:\FYP\Project\CrimeVision\OCRModel\app\data\raw\FIR_001.png'
img = cv2.imread(img_path)

h, w = img.shape[:2]
print(f"Image size: {w}x{h}")

# Initialize EasyOCR
print("\nInitializing EasyOCR...")
reader = easyocr.Reader(['ur', 'en'], gpu=False)

# Patterns that indicate thana-related text
thana_patterns = ['تھانہ', 'ٹھانہ', 'تھانا', 'پولیس', 'سٹیشن', 'ٹاؤن', 'Town', 'Defence', 'Model']

print("\n" + "=" * 70)
print("SCANNING ALL ROWS FOR THANA-RELATED TEXT")
print("=" * 70)

# Scan rows from 0% to 30% of image height
for row_start in range(0, 30, 3):  # 3% increments
    row_end = row_start + 5  # 5% height rows
    y1, y2 = int(h * row_start / 100), int(h * row_end / 100)
    
    if y2 > h:
        break
        
    row = img[y1:y2, 0:w]
    
    # Skip if row is too small
    if row.shape[0] < 50:
        continue
    
    # Process for OCR
    gray = cv2.cvtColor(row, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # Tesseract
    try:
        text_tess = pytesseract.image_to_string(binary, lang='urd', config='--psm 6')
        text_tess = text_tess.strip().replace('\n', ' ')
    except:
        text_tess = ""
    
    # Check for thana patterns
    found_patterns = []
    for pattern in thana_patterns:
        if pattern in text_tess:
            found_patterns.append(pattern)
    
    if found_patterns or row_start < 20:  # Always show first 20%
        print(f"\nRow {row_start}%-{row_end}%:")
        if text_tess:
            print(f"  Tesseract: {text_tess[:150]}")
        if found_patterns:
            print(f"  >>> FOUND: {found_patterns}")

# Now let's try EasyOCR on specific key rows
print("\n" + "=" * 70)
print("EASYOCR ON KEY ROWS")
print("=" * 70)

key_rows = [
    ("Header 1", 0.00, 0.06),
    ("Header 2", 0.06, 0.10),
    ("Row 3 (date/thana)", 0.10, 0.16),
    ("Row 4", 0.16, 0.22),
]

for name, top_pct, bottom_pct in key_rows:
    print(f"\n{name} ({top_pct*100:.0f}%-{bottom_pct*100:.0f}%):")
    y1, y2 = int(h * top_pct), int(h * bottom_pct)
    row = img[y1:y2, 0:w]
    
    # Focus on right half (where thana usually is)
    right_half = row[:, int(w * 0.50):]
    
    results = reader.readtext(right_half, paragraph=False)
    
    # Sort by x position (rightmost first) - bbox[0] is top-left corner
    sorted_results = sorted(results, key=lambda r: -float(r[0][0][0]))  # type: ignore[index]
    for bbox, text, conf in sorted_results[:10]:
        x_pct = (float(bbox[0][0]) + float(bbox[2][0])) / 2 / right_half.shape[1] * 100 + 50
        marker = ""
        for pattern in thana_patterns:
            if pattern.lower() in text.lower():
                marker = f" >>> {pattern}"
                break
        print(f"    '{text}' @ x={x_pct:.0f}% (conf={conf:.2f}){marker}")

# Finally, let's look for any English text that might be "Defence", "Model Town", etc.
print("\n" + "=" * 70)
print("LOOKING FOR COMMON THANA NAMES")
print("=" * 70)

# Common Lahore thana names (both Urdu and English transliterations)
common_thanas = [
    'Defence', 'Defense', 'DHA',
    'Model Town', 'Model',
    'Gulberg', 'Gulberg',
    'Cantt', 'Cantonment',
    'Iqbal Town', 'Iqbal',
    'Faisal Town', 'Faisal',
    'Garden Town', 'Garden',
    'Township', 'Town Ship',
    'Johar Town', 'Johar',
    'Sabzazar', 'Sabz Azar',
    # Urdu versions
    'ڈیفنس', 'ماڈل', 'گلبرگ', 'کینٹ', 'اقبال', 'فیصل', 'ٹاؤن شپ', 'جوہر'
]

# Scan the header for these names
header = img[0:int(h * 0.25), 0:w]
header_up = cv2.resize(header, None, fx=0.5, fy=0.5)  # Downscale for faster processing

# EasyOCR on header
results = reader.readtext(header_up, paragraph=False)

for bbox, text, conf in results:
    for thana in common_thanas:
        if thana.lower() in text.lower():
            x_pct = (float(bbox[0][0]) + float(bbox[2][0])) / 2 / header_up.shape[1] * 100
            y_pct = (float(bbox[0][1]) + float(bbox[2][1])) / 2 / header_up.shape[0] * 100 * 0.25
            print(f"  FOUND '{thana}' in '{text}' @ ({x_pct:.0f}%, {y_pct:.0f}%)")

print("\n" + "=" * 70)
print("DONE")
print("=" * 70)
