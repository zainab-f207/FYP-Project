"""Detailed OCR analysis of the thana row"""
import cv2
import numpy as np
import pytesseract

# Load FIR image
img_path = r'D:\FYP\Project\CrimeVision\OCRModel\app\data\raw\FIR_001.png'
img = cv2.imread(img_path)

h, w = img.shape[:2]
print(f"Image size: {w}x{h}")

# Row 3 (where thana typically is): y=10%-16%
y1, y2 = int(h * 0.10), int(h * 0.16)
row3 = img[y1:y2, 0:w]
print(f"Row 3 size: {row3.shape[1]}x{row3.shape[0]}px")

# Save row for inspection
cv2.imwrite("row3_full_analysis.png", row3)

# Process for better OCR
gray = cv2.cvtColor(row3, cv2.COLOR_BGR2GRAY)

# Try Otsu threshold
_, binary_otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
cv2.imwrite("row3_binary_otsu.png", binary_otsu)

# Try adaptive threshold
adaptive = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
cv2.imwrite("row3_adaptive.png", adaptive)

# Upscale 2x
upscaled = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
_, binary_up = cv2.threshold(upscaled, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
cv2.imwrite("row3_upscaled_binary.png", binary_up)

print("\n" + "=" * 70)
print("TESSERACT OCR ON ROW 3 (Full row)")
print("=" * 70)

# Try different Tesseract configs
configs = [
    ('urd', '--psm 6', 'Urdu PSM6'),
    ('urd', '--psm 11', 'Urdu PSM11'),
    ('urd+eng', '--psm 6', 'Urdu+Eng PSM6'),
]

for lang, config, name in configs:
    print(f"\n{name}:")
    try:
        text = pytesseract.image_to_string(binary_up, lang=lang, config=config)
        text = text.strip()
        if text:
            lines = text.split('\n')
            for line in lines[:5]:  # Show first 5 lines
                if line.strip():
                    print(f"  {line.strip()}")
    except Exception as e:
        print(f"  Error: {e}")

# Now try to get word-level bounding boxes
print("\n" + "=" * 70)
print("WORD-LEVEL OCR WITH BOUNDING BOXES")
print("=" * 70)

try:
    # Get detailed data
    data = pytesseract.image_to_data(binary_up, lang='urd', config='--psm 6', output_type=pytesseract.Output.DICT)
    
    # Draw words on image
    row3_annotated = cv2.cvtColor(binary_up, cv2.COLOR_GRAY2BGR)
    
    print("\nDetected words (x position, text, confidence):")
    words = []
    for i in range(len(data['text'])):
        text = data['text'][i].strip()
        conf = int(data['conf'][i])
        x = data['left'][i]
        y = data['top'][i]
        w_box = data['width'][i]
        h_box = data['height'][i]
        
        if text and conf > 0:
            x_pct = x / row3_annotated.shape[1] * 100
            words.append((x_pct, text, conf, x, y, w_box, h_box))
            
            # Draw rectangle
            cv2.rectangle(row3_annotated, (x, y), (x + w_box, y + h_box), (0, 255, 0), 2)
    
    # Sort by x position (right to left for RTL)
    words.sort(key=lambda w: w[0], reverse=True)
    
    for x_pct, text, conf, *_ in words:
        marker = " <<< POSSIBLE THANA" if 75 < x_pct < 95 else ""
        print(f"  x={x_pct:5.1f}%: '{text}' (conf={conf}){marker}")
    
    cv2.imwrite("row3_words_annotated.png", row3_annotated)
    print("\nSaved: row3_words_annotated.png")

except Exception as e:
    print(f"Error: {e}")

# Focus on the right portion (where thana value should be)
print("\n" + "=" * 70)
print("FOCUSED OCR ON RIGHT PORTION (75-92% width)")
print("=" * 70)

x1, x2 = int(row3.shape[1] * 0.75), int(row3.shape[1] * 0.92)
right_portion = row3[:, x1:x2]
cv2.imwrite("row3_right_portion.png", right_portion)

# Process right portion
gray_right = cv2.cvtColor(right_portion, cv2.COLOR_BGR2GRAY)
upscaled_right = cv2.resize(gray_right, None, fx=3, fy=3, interpolation=cv2.INTER_LANCZOS4)
_, binary_right = cv2.threshold(upscaled_right, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
cv2.imwrite("row3_right_binary.png", binary_right)

# Invert if needed (detect if text is white on black)
mean_val = float(binary_right.mean())  # type: ignore[union-attr]
if mean_val > 127:
    print("Background is white (mean > 127)")
else:
    print("Background is dark, inverting...")
    binary_right = cv2.bitwise_not(binary_right)
    cv2.imwrite("row3_right_binary_inv.png", binary_right)

print("\nTesseract on right portion:")
for psm in [6, 7, 11, 13]:
    try:
        text = pytesseract.image_to_string(binary_right, lang='urd', config=f'--psm {psm}')
        text = text.strip().replace('\n', ' ')
        if text:
            print(f"  PSM {psm}: '{text}'")
    except:
        pass

print("\n" + "=" * 70)
print("Check generated PNG files for visual inspection")
print("=" * 70)
