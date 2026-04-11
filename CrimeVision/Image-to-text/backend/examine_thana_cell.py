"""Extract and closely examine the thana cell - what's actually there?"""
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

# Based on the analysis, the thana-related text seems to be around x=84% in row 3
# Let's extract that specific area

print("\n" + "=" * 70)
print("EXTRACTING THANA CELL (right side of row 3)")
print("=" * 70)

# Row 3: y=10%-16%, thana cell: x=70%-95%
y1, y2 = int(h * 0.10), int(h * 0.16)
x1, x2 = int(w * 0.70), int(w * 0.95)

thana_cell = img[y1:y2, x1:x2]
print(f"Thana cell size: {thana_cell.shape[1]}x{thana_cell.shape[0]}px")
cv2.imwrite("thana_cell_raw.png", thana_cell)

# Initialize EasyOCR with just Urdu for better accuracy
print("\nInitializing EasyOCR (Urdu only)...")
reader_ur = easyocr.Reader(['ur'], gpu=False)

# Also try with English for mixed text
print("Initializing EasyOCR (Urdu + English)...")
reader_ur_en = easyocr.Reader(['ur', 'en'], gpu=False)

# ======================================================
# Method 1: Raw image
# ======================================================
print("\n" + "-" * 50)
print("Method 1: RAW image")
print("-" * 50)
results = reader_ur_en.readtext(thana_cell, paragraph=False)
print(f"Found {len(results)} text blocks:")
for bbox, text, conf in results:
    print(f"  '{text}' (conf={conf:.2f})")

# ======================================================
# Method 2: Upscale 2x
# ======================================================
print("\n" + "-" * 50)
print("Method 2: Upscaled 2x")
print("-" * 50)
upscaled = cv2.resize(thana_cell, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
cv2.imwrite("thana_cell_upscaled.png", upscaled)
results = reader_ur_en.readtext(upscaled, paragraph=False)
print(f"Found {len(results)} text blocks:")
for bbox, text, conf in results:
    print(f"  '{text}' (conf={conf:.2f})")

# ======================================================
# Method 3: Grayscale + CLAHE
# ======================================================
print("\n" + "-" * 50)
print("Method 3: Grayscale + CLAHE")
print("-" * 50)
gray = cv2.cvtColor(thana_cell, cv2.COLOR_BGR2GRAY)
clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
enhanced = clahe.apply(gray)
cv2.imwrite("thana_cell_clahe.png", enhanced)
results = reader_ur_en.readtext(enhanced, paragraph=False)
print(f"Found {len(results)} text blocks:")
for bbox, text, conf in results:
    print(f"  '{text}' (conf={conf:.2f})")

# ======================================================
# Method 4: Upscaled + CLAHE
# ======================================================
print("\n" + "-" * 50)
print("Method 4: Upscaled 2x + CLAHE")
print("-" * 50)
gray_up = cv2.cvtColor(upscaled, cv2.COLOR_BGR2GRAY)
enhanced_up = clahe.apply(gray_up)
cv2.imwrite("thana_cell_up_clahe.png", enhanced_up)
results = reader_ur_en.readtext(enhanced_up, paragraph=False)
print(f"Found {len(results)} text blocks:")
for bbox, text, conf in results:
    print(f"  '{text}' (conf={conf:.2f})")

# ======================================================
# Method 5: Bilateral filter (denoising while preserving edges)
# ======================================================
print("\n" + "-" * 50)
print("Method 5: Bilateral filter + CLAHE")
print("-" * 50)
bilateral = cv2.bilateralFilter(thana_cell, 9, 75, 75)
gray_bi = cv2.cvtColor(bilateral, cv2.COLOR_BGR2GRAY)
enhanced_bi = clahe.apply(gray_bi)
cv2.imwrite("thana_cell_bilateral.png", enhanced_bi)
results = reader_ur_en.readtext(enhanced_bi, paragraph=False)
print(f"Found {len(results)} text blocks:")
for bbox, text, conf in results:
    print(f"  '{text}' (conf={conf:.2f})")

# ======================================================
# Method 6: Upscale 3x + sharpen
# ======================================================
print("\n" + "-" * 50)
print("Method 6: Upscaled 3x + Sharpen")
print("-" * 50)
upscaled_3x = cv2.resize(thana_cell, None, fx=3, fy=3, interpolation=cv2.INTER_LANCZOS4)
# Sharpen
kernel_sharp = np.array([[-1,-1,-1], [-1, 9,-1], [-1,-1,-1]])
sharpened = cv2.filter2D(upscaled_3x, -1, kernel_sharp)
cv2.imwrite("thana_cell_3x_sharp.png", sharpened)
results = reader_ur_en.readtext(sharpened, paragraph=False)
print(f"Found {len(results)} text blocks:")
for bbox, text, conf in results:
    print(f"  '{text}' (conf={conf:.2f})")

# ======================================================
# Method 7: Try Tesseract with different PSM modes
# ======================================================
print("\n" + "-" * 50)
print("Method 7: Tesseract with different modes")
print("-" * 50)

try:
    import pytesseract
    
    # Binary threshold
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    cv2.imwrite("thana_cell_binary.png", binary)
    
    for psm in [6, 7, 11, 13]:
        text = pytesseract.image_to_string(binary, lang='urd', config=f'--psm {psm}')
        text = text.strip().replace('\n', ' ')[:100]
        if text:
            print(f"  PSM {psm}: '{text}'")
            
    # Also try on upscaled binary
    _, binary_up = cv2.threshold(gray_up, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    cv2.imwrite("thana_cell_binary_up.png", binary_up)
    
    print("\n  Upscaled binary:")
    for psm in [6, 7, 11]:
        text = pytesseract.image_to_string(binary_up, lang='urd', config=f'--psm {psm}')
        text = text.strip().replace('\n', ' ')[:100]
        if text:
            print(f"  PSM {psm}: '{text}'")
            
except Exception as e:
    print(f"  Tesseract error: {e}")

# ======================================================
# Let's also check a wider region to see the full context
# ======================================================
print("\n" + "=" * 70)
print("WIDER VIEW - Looking at more context")
print("=" * 70)

# Extract row 3 columns - split into left/middle/right
row3 = img[int(h * 0.10):int(h * 0.16), 0:w]
cv2.imwrite("row3_full.png", row3)

# Left third (0-33%)
left = row3[:, 0:int(w * 0.33)]
cv2.imwrite("row3_left.png", left)

# Middle third (33-66%)
middle = row3[:, int(w * 0.33):int(w * 0.66)]
cv2.imwrite("row3_middle.png", middle)

# Right third (66-100%)
right = row3[:, int(w * 0.66):w]
cv2.imwrite("row3_right.png", right)

print("\nRow 3 - Right third (where thana should be):")
results = reader_ur_en.readtext(right, paragraph=False)
for bbox, text, conf in results:
    x_pct = (float(bbox[0][0]) + float(bbox[2][0])) / 2 / right.shape[1] * 100
    print(f"  '{text}' @ x={x_pct:.1f}% (conf={conf:.2f})")

# ======================================================
# Check if there's a label column and value column pattern
# ======================================================
print("\n" + "=" * 70)
print("LOOKING FOR LABEL:VALUE PATTERN")
print("=" * 70)

# In FIR forms, there's often a pattern like:
# | Label: Value | Label: Value |
# The right side usually has: | تھانہ: [name] | نمبر: [number] |

# Extract very right section (85-95%) where thana NAME would be
thana_value_area = row3[:, int(w * 0.75):int(w * 0.90)]
cv2.imwrite("thana_value_area.png", thana_value_area)

print("\nThana value area (75-90% width):")
# Upscale for better OCR
thana_val_up = cv2.resize(thana_value_area, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
results = reader_ur_en.readtext(thana_val_up, paragraph=False)
for bbox, text, conf in results:
    print(f"  '{text}' (conf={conf:.2f})")

# Also try Urdu-only reader
print("\nUrdu-only reader on thana value area:")
results = reader_ur.readtext(thana_val_up, paragraph=False)
for bbox, text, conf in results:
    print(f"  '{text}' (conf={conf:.2f})")

print("\n" + "=" * 70)
print("DONE - Check thana_cell_*.png files for visual inspection")
print("=" * 70)
