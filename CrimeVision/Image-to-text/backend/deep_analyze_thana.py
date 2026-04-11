"""Deep analysis of FIR structure to find thana location"""
import cv2
import numpy as np
import easyocr

# Use FIR_001 as reference
img_path = r'D:\FYP\Project\CrimeVision\OCRModel\app\data\raw\FIR_001.png'
img = cv2.imread(img_path)

if img is None:
    print("ERROR: Could not load image")
    exit(1)

h, w = img.shape[:2]
print(f"Image size: {w}x{h}")

# Initialize EasyOCR
print("Initializing EasyOCR...")
reader = easyocr.Reader(['ur', 'en'], gpu=False)

# ======================================================
# Scan the FULL image for "تھانہ" label 
# ======================================================
print("\n" + "=" * 70)
print("FULL IMAGE SCAN - Looking for 'تھانہ' label anywhere")
print("=" * 70)

# Run on full image (downsized for speed)
scale = 0.5
img_small = cv2.resize(img, None, fx=scale, fy=scale)
print(f"Scanning image at {img_small.shape[1]}x{img_small.shape[0]}...")

results = reader.readtext(img_small, paragraph=False)
print(f"\nFound {len(results)} text blocks. Looking for thana-related text:")

thana_candidates = []
for bbox, text, conf in results:
    # Scale bbox back to original coordinates
    x_center = (float(bbox[0][0]) + float(bbox[2][0])) / 2 / scale
    y_center = (float(bbox[0][1]) + float(bbox[2][1])) / 2 / scale
    
    # Check for various thana-related patterns
    thana_patterns = ['تھانہ', 'ٹھانہ', 'تھانا', 'ٹاؤن', 'Town', 'پولیس', 'سٹیشن', 'Station']
    for pattern in thana_patterns:
        if pattern in text:
            x_pct = x_center / w * 100
            y_pct = y_center / h * 100
            print(f"  >>> '{text}' @ x={x_pct:.1f}%, y={y_pct:.1f}% (conf={conf:.2f})")
            thana_candidates.append({
                'text': text,
                'x_pct': x_pct,
                'y_pct': y_pct,
                'conf': conf
            })
            break

# ======================================================
# Also look for what looks like location/area names
# These typically contain: ٹاؤن, روڈ, کالونی, etc.
# ======================================================
print("\n" + "=" * 70)
print("Looking for location/area name patterns")
print("=" * 70)

location_patterns = ['ٹاؤن', 'روڈ', 'کالونی', 'نگر', 'آباد', 'پورہ', 'گڑھ', 'Model']

for bbox, text, conf in results:
    x_center = (float(bbox[0][0]) + float(bbox[2][0])) / 2 / scale
    y_center = (float(bbox[0][1]) + float(bbox[2][1])) / 2 / scale
    x_pct = x_center / w * 100
    y_pct = y_center / h * 100
    
    for pattern in location_patterns:
        if pattern in text:
            print(f"  >>> '{text}' @ x={x_pct:.1f}%, y={y_pct:.1f}% (conf={conf:.2f})")
            break

# ======================================================
# List ALL high-confidence detections in header area (y < 20%)
# ======================================================
print("\n" + "=" * 70)
print("HIGH CONFIDENCE DETECTIONS IN HEADER (conf > 0.3, y < 25%)")
print("=" * 70)

for bbox, text, conf in results:
    x_center = (float(bbox[0][0]) + float(bbox[2][0])) / 2 / scale
    y_center = (float(bbox[0][1]) + float(bbox[2][1])) / 2 / scale
    x_pct = x_center / w * 100
    y_pct = y_center / h * 100
    
    if float(conf) > 0.3 and y_pct < 25:
        print(f"  '{text}' @ x={x_pct:.1f}%, y={y_pct:.1f}% (conf={conf:.2f})")

# ======================================================
# Try TESSERACT with Urdu on specific regions
# ======================================================
print("\n" + "=" * 70)
print("TESSERACT SCAN ON HEADER ROWS")
print("=" * 70)

try:
    import pytesseract
    
    # Check rows 1-5
    for row_num in range(1, 8):
        top_pct = (row_num - 1) * 0.05 + 0.08
        bottom_pct = row_num * 0.05 + 0.08
        
        y1 = int(h * top_pct)
        y2 = int(h * bottom_pct)
        row = img[y1:y2, 0:w]
        
        # Preprocess
        gray = cv2.cvtColor(row, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        text = pytesseract.image_to_string(binary, lang='urd', config='--psm 6')
        text = text.strip().replace('\n', ' ')
        
        if text:
            print(f"\nRow {row_num} ({top_pct*100:.0f}%-{bottom_pct*100:.0f}%):")
            print(f"  {text[:150]}")
            
            # Check for thana-related words
            if 'تھانہ' in text or 'ٹھانہ' in text or 'ٹاؤن' in text or 'پولیس' in text:
                print(f"  >>> THANA FOUND IN ROW {row_num}!")
                cv2.imwrite(f"found_thana_row{row_num}.png", row)
                
except ImportError:
    print("pytesseract not available")
except Exception as e:
    print(f"Tesseract error: {e}")

# ======================================================
# Extract and analyze specific cells in the FIR table header
# ======================================================
print("\n" + "=" * 70)
print("ANALYZING TABLE CELLS")
print("=" * 70)

# In Pakistani FIRs, thana is typically in a cell labeled "تھانہ"
# Let's check specific regions based on typical FIR layouts

# Cell regions to check (based on FIR structure)
cells = [
    ("Top-right cell", 0.08, 0.14, 0.75, 0.98),
    ("Top-middle cell", 0.08, 0.14, 0.50, 0.75),
    ("Second row right", 0.14, 0.20, 0.75, 0.98),
    ("Second row middle", 0.14, 0.20, 0.50, 0.75),
]

for cell_name, top, bottom, left, right in cells:
    y1, y2 = int(h * top), int(h * bottom)
    x1, x2 = int(w * left), int(w * right)
    cell = img[y1:y2, x1:x2]
    
    print(f"\n{cell_name} ({left*100:.0f}%-{right*100:.0f}% x, {top*100:.0f}%-{bottom*100:.0f}% y):")
    cv2.imwrite(f"cell_{cell_name.replace(' ', '_').lower()}.png", cell)
    
    # EasyOCR on this cell
    results = reader.readtext(cell, paragraph=False)
    for bbox, text, conf in results:
        marker = "<<< THANA?" if ('تھانہ' in text or 'ٹھانہ' in text) else ""
        print(f"  '{text}' (conf={conf:.2f}) {marker}")

print("\n" + "=" * 70)
print("Check generated PNG files for visual inspection")
print("=" * 70)
