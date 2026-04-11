"""Analyze thana extraction - find correct region and OCR approach"""
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
print("=" * 70)

# Initialize EasyOCR with Urdu
print("Initializing EasyOCR...")
reader = easyocr.Reader(['ur', 'en'], gpu=False)

# ======================================================
# First, let's scan the HEADER area to find where thana actually is
# ======================================================
print("\n" + "=" * 70)
print("SCANNING HEADER AREA (top 20%) TO LOCATE THANA")
print("=" * 70)

header_region = img[0:int(h * 0.20), 0:w]
cv2.imwrite("analyze_01_header.png", header_region)
print(f"Header region: {header_region.shape[1]}x{header_region.shape[0]}")

# Run EasyOCR on header
results = reader.readtext(header_region, paragraph=False)
print(f"\nFound {len(results)} text blocks in header:")

thana_label_found = False
for i, (bbox, text, conf) in enumerate(results):
    x1 = int(bbox[0][0])
    y1 = int(bbox[0][1])
    x2 = int(bbox[2][0])
    y2 = int(bbox[2][1])
    x_pct = (x1 + x2) / 2 / header_region.shape[1] * 100
    y_pct = (y1 + y2) / 2 / header_region.shape[0] * 100
    
    # Highlight if it contains thana-related text
    is_thana = any(label in text for label in ['تھانہ', 'ٹھانہ', 'تھانا', 'Town', 'ٹاؤن'])
    marker = ">>> THANA <<<" if is_thana else ""
    
    print(f"  [{i:2d}] '{text}' (conf={conf:.2f}) @ x={x_pct:.1f}%, y={y_pct:.1f}% {marker}")
    
    if is_thana:
        thana_label_found = True
        # Draw rectangle around thana text
        cv2.rectangle(header_region, (x1, y1), (x2, y2), (0, 255, 0), 3)

cv2.imwrite("analyze_02_header_annotated.png", header_region)

# ======================================================
# Now let's check specific rows of the FIR table
# FIR forms typically have the thana in the header row
# ======================================================
print("\n" + "=" * 70)
print("ANALYZING FIR ROWS SEPARATELY")
print("=" * 70)

# Common FIR row positions (percentages of image height)
rows = [
    ("Row 1 (header)", 0.00, 0.06),
    ("Row 2 (sub-header)", 0.06, 0.10),
    ("Row 3 (date/thana row)", 0.10, 0.15),
    ("Row 4 (details)", 0.15, 0.20),
]

for row_name, top_pct, bottom_pct in rows:
    y1 = int(h * top_pct)
    y2 = int(h * bottom_pct)
    row = img[y1:y2, 0:w]
    
    print(f"\n{row_name}: y={top_pct*100:.0f}%-{bottom_pct*100:.0f}% ({row.shape[1]}x{row.shape[0]}px)")
    
    results = reader.readtext(row, paragraph=False)
    for bbox, text, conf in results:
        x_center = (float(bbox[0][0]) + float(bbox[2][0])) / 2 / row.shape[1] * 100
        is_thana = any(label in text for label in ['تھانہ', 'ٹھانہ', 'تھانا', 'Town', 'ٹاؤن'])
        marker = ">>> THANA <<<" if is_thana else ""
        print(f"    '{text}' (conf={conf:.2f}) @ x={x_center:.1f}% {marker}")

# ======================================================
# Look for the EXACT thana value cell
# Usually thana name appears to the LEFT of the تھانہ label (RTL)
# ======================================================
print("\n" + "=" * 70)
print("EXTRACTING THANA VALUE (looking for name to LEFT of label)")
print("=" * 70)

# Row 3 is typically where thana info is
row3_top = 0.10
row3_bottom = 0.16
row3 = img[int(h * row3_top):int(h * row3_bottom), 0:w]
cv2.imwrite("analyze_03_row3.png", row3)

print(f"Row 3 (thana row): {row3.shape[1]}x{row3.shape[0]}px")

# Get all text with positions
results = reader.readtext(row3, paragraph=False)
print(f"Found {len(results)} text blocks:")

# Store all detections with x positions
detections = []
for bbox, text, conf in results:
    x1 = float(bbox[0][0])
    x2 = float(bbox[2][0])
    x_center = (x1 + x2) / 2
    x_pct = x_center / row3.shape[1] * 100
    detections.append({
        'text': text,
        'conf': conf,
        'x1': x1,
        'x2': x2,
        'x_center': x_center,
        'x_pct': x_pct,
        'bbox': bbox
    })
    print(f"  '{text}' @ x={x_pct:.1f}% (conf={conf:.2f})")

# Sort by x position (right to left for RTL)
detections.sort(key=lambda d: d['x_center'], reverse=True)

# Find thana label
thana_label = None
for det in detections:
    if any(label in det['text'] for label in ['تھانہ', 'ٹھانہ', 'تھانا']):
        thana_label = det
        print(f"\n>>> Found thana label: '{det['text']}' at x={det['x_pct']:.1f}%")
        break

if thana_label:
    # The thana VALUE should be to the LEFT (smaller x) of the label
    print("\nLooking for thana value to the LEFT of label:")
    for det in detections:
        if det['x_center'] < thana_label['x_center']:
            # This is to the left of the label
            distance = thana_label['x_center'] - det['x_center']
            print(f"  Candidate: '{det['text']}' (conf={det['conf']:.2f}, distance={distance:.0f}px)")

# ======================================================
# Try different preprocessing on a focused thana region
# ======================================================
print("\n" + "=" * 70)
print("TRYING DIFFERENT OCR APPROACHES ON THANA REGION")
print("=" * 70)

# Focus on right 40% of row 3 (where thana typically is in Pakistani FIRs)
thana_focus = row3[:, int(row3.shape[1] * 0.50):]
cv2.imwrite("analyze_04_thana_focus.png", thana_focus)
print(f"Thana focus region: {thana_focus.shape[1]}x{thana_focus.shape[0]}px")

# Method 1: Raw image
print("\n1. RAW image (no preprocessing):")
results = reader.readtext(thana_focus, paragraph=False)
for bbox, text, conf in results:
    print(f"   '{text}' (conf={conf:.2f})")

# Method 2: Grayscale + light CLAHE
print("\n2. Grayscale + Light CLAHE:")
gray = cv2.cvtColor(thana_focus, cv2.COLOR_BGR2GRAY)
clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
enhanced = clahe.apply(gray)
cv2.imwrite("analyze_05_thana_clahe.png", enhanced)
results = reader.readtext(enhanced, paragraph=False)
for bbox, text, conf in results:
    print(f"   '{text}' (conf={conf:.2f})")

# Method 3: Upscale 2x (helps with small text)
print("\n3. Upscaled 2x:")
upscaled = cv2.resize(thana_focus, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
cv2.imwrite("analyze_06_thana_upscaled.png", upscaled)
results = reader.readtext(upscaled, paragraph=False)
for bbox, text, conf in results:
    print(f"   '{text}' (conf={conf:.2f})")

# Method 4: Upscale + CLAHE
print("\n4. Upscaled 2x + CLAHE:")
gray_up = cv2.cvtColor(upscaled, cv2.COLOR_BGR2GRAY)
enhanced_up = clahe.apply(gray_up)
cv2.imwrite("analyze_07_thana_up_clahe.png", enhanced_up)
results = reader.readtext(enhanced_up, paragraph=False)
for bbox, text, conf in results:
    print(f"   '{text}' (conf={conf:.2f})")

# Method 5: Binary threshold
print("\n5. Binary threshold (Otsu):")
_, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
cv2.imwrite("analyze_08_thana_binary.png", binary)
results = reader.readtext(binary, paragraph=False)
for bbox, text, conf in results:
    print(f"   '{text}' (conf={conf:.2f})")

print("\n" + "=" * 70)
print("ANALYSIS COMPLETE - Check analyze_*.png files for visual inspection")
print("=" * 70)
