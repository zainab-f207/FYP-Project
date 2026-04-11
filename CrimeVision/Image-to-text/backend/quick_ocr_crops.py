"""Quick OCR on crop files to see what Tesseract reads."""
import sys
sys.stdout = open('CON', 'w', encoding='utf-8')
import cv2
import pytesseract
import os

crops = [
    'debug_crops/crop_FIR_001.png',
    'debug_crops/crop_FIR_007.png', 
    'debug_crops/crop_FIR_021.png',
    'debug_crops/crop_FIR_101.png',
    'debug_crops/crop_FIR_037.png',
    'debug_crops/crop_FIR_033.png',
]

for c in crops:
    img = cv2.imread(c)
    if img is None:
        print(f"SKIP: {c}")
        continue
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Raw OCR
    text = pytesseract.image_to_string(gray, lang='urd', config='--oem 1 --psm 6')
    text = text.strip().replace('\n', ' ')[:100]
    
    # 2x upscale OCR  
    scaled = cv2.resize(gray, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(scaled)
    text2x = pytesseract.image_to_string(enhanced, lang='urd', config='--oem 1 --psm 6')
    text2x = text2x.strip().replace('\n', ' ')[:100]
    
    fname = os.path.basename(c)
    print(f"\n{fname} ({w}x{h}):")
    print(f"  Raw:  {text}")
    print(f"  2x:   {text2x}")
