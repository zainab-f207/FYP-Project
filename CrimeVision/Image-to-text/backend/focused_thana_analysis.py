"""Focused thana analysis - scan header region only"""
import cv2
import numpy as np
import easyocr
import gc

# Use FIR_001 as reference
img_path = r'D:\FYP\Project\CrimeVision\OCRModel\app\data\raw\FIR_001.png'
img = cv2.imread(img_path)

if img is None:
    print("ERROR: Could not load image")
    exit(1)

h, w = img.shape[:2]
print(f"Image size: {w}x{h}")

# Extract only header (top 25%)
header = img[0:int(h * 0.25), 0:w]
print(f"Header size: {header.shape[1]}x{header.shape[0]}")
cv2.imwrite("header_full.png", header)

# Initialize EasyOCR
print("\nInitializing EasyOCR...")
reader = easyocr.Reader(['ur', 'en'], gpu=False)

# ======================================================
# Scan header for ALL text
# ======================================================
print("\n" + "=" * 70)
print("SCANNING HEADER FOR ALL TEXT")
print("=" * 70)

results = reader.readtext(header, paragraph=False)
print(f"\nFound {len(results)} text blocks:\n")

# Store all with positions
all_detections = []
for bbox, text, conf in results:
    x1 = int(bbox[0][0])
    y1 = int(bbox[0][1])
    x2 = int(bbox[2][0])
    y2 = int(bbox[2][1])
    
    x_pct = (x1 + x2) / 2 / header.shape[1] * 100
    y_pct = (y1 + y2) / 2 / header.shape[0] * 100
    
    all_detections.append({
        'text': text,
        'conf': conf,
        'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2,
        'x_pct': x_pct,
        'y_pct': y_pct
    })
    
    # Highlight thana-related
    thana_related = any(p in text for p in ['تھانہ', 'ٹھانہ', 'تھانا', 'ٹاؤن', 'Town', 'پولیس'])
    marker = " <<< THANA RELATED!" if thana_related else ""
    
    print(f"  '{text}' @ ({x_pct:.1f}%, {y_pct:.1f}%) conf={conf:.2f}{marker}")

# ======================================================
# Draw all detections on image
# ======================================================
header_annotated = header.copy()
for det in all_detections:
    color = (0, 255, 0) if det['conf'] > 0.5 else (0, 165, 255)  # Green for high conf, orange for low
    cv2.rectangle(header_annotated, (det['x1'], det['y1']), (det['x2'], det['y2']), color, 2)

cv2.imwrite("header_annotated.png", header_annotated)

# ======================================================
# Now try TESSERACT for Urdu text
# ======================================================
print("\n" + "=" * 70)
print("TESSERACT URDU ON HEADER")
print("=" * 70)

try:
    import pytesseract
    
    # Preprocess header
    gray = cv2.cvtColor(header, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    cv2.imwrite("header_binary.png", binary)
    
    # Full header OCR
    text = pytesseract.image_to_string(binary, lang='urd', config='--psm 6')
    print("\nFull header text:")
    print("-" * 50)
    print(text[:1000])
    print("-" * 50)
    
    # Search for thana patterns
    thana_patterns = ['تھانہ', 'ٹھانہ', 'تھانا', 'ٹاؤن', 'پولیس سٹیشن']
    for pattern in thana_patterns:
        if pattern in text:
            print(f"\n>>> FOUND '{pattern}' in text!")
            # Find context around it
            idx = text.find(pattern)
            context = text[max(0, idx-50):idx+50]
            print(f"    Context: ...{context}...")
            
except Exception as e:
    print(f"Tesseract error: {e}")

# ======================================================
# Check specific row regions with TESSERACT
# ======================================================
print("\n" + "=" * 70)
print("CHECKING SPECIFIC ROWS FOR THANA")
print("=" * 70)

try:
    import pytesseract
    
    # Row 3 is often where thana is in Punjab FIRs (y=10%-15%)
    rows_to_check = [
        ("row_2", 0.06, 0.10),
        ("row_3", 0.10, 0.16),
        ("row_4", 0.16, 0.22),
    ]
    
    for row_name, top_pct, bottom_pct in rows_to_check:
        y1 = int(h * top_pct)
        y2 = int(h * bottom_pct)
        row = img[y1:y2, 0:w]
        
        print(f"\n{row_name} (y={top_pct*100:.0f}%-{bottom_pct*100:.0f}%):")
        cv2.imwrite(f"{row_name}.png", row)
        
        # Convert and OCR
        gray = cv2.cvtColor(row, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        cv2.imwrite(f"{row_name}_binary.png", binary)
        
        text = pytesseract.image_to_string(binary, lang='urd', config='--psm 6')
        text = text.strip()
        if text:
            print(f"  {text[:200]}")
            
            # Check for thana
            if 'تھانہ' in text or 'ٹھانہ' in text:
                print("  >>> THANA LABEL FOUND!")
            if 'ٹاؤن' in text or 'Town' in text:
                print("  >>> TOWN PATTERN FOUND!")
                
        # Also try EasyOCR on this row
        gc.collect()  # Free memory
        results = reader.readtext(row, paragraph=False)
        print(f"  EasyOCR found {len(results)} text blocks:")
        for bbox, text, conf in results:
            x_pct = (float(bbox[0][0]) + float(bbox[2][0])) / 2 / row.shape[1] * 100
            marker = " <<<" if any(p in text for p in ['تھانہ', 'ٹھانہ', 'ٹاؤن']) else ""
            print(f"    '{text}' @ x={x_pct:.1f}% (conf={conf:.2f}){marker}")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

# ======================================================
# Check the right side of header (where thana usually is)
# ======================================================
print("\n" + "=" * 70)
print("CHECKING RIGHT SIDE OF HEADER (60%-100% width)")
print("=" * 70)

# Right portion of rows 2-4
right_header = img[int(h * 0.08):int(h * 0.20), int(w * 0.60):w]
print(f"Right header size: {right_header.shape[1]}x{right_header.shape[0]}")
cv2.imwrite("right_header.png", right_header)

gc.collect()
results = reader.readtext(right_header, paragraph=False)
print(f"\nEasyOCR on right header ({len(results)} blocks):")
for bbox, text, conf in results:
    x_pct = (float(bbox[0][0]) + float(bbox[2][0])) / 2 / right_header.shape[1] * 100
    y_pct = (float(bbox[0][1]) + float(bbox[2][1])) / 2 / right_header.shape[0] * 100
    marker = " <<<" if any(p in text for p in ['تھانہ', 'ٹھانہ', 'ٹاؤن', 'Town']) else ""
    print(f"  '{text}' @ ({x_pct:.1f}%, {y_pct:.1f}%) conf={conf:.2f}{marker}")

print("\n" + "=" * 70)
print("DONE - Check generated PNG files")
print("=" * 70)
