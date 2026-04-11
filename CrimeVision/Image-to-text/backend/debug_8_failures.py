"""Debug raw OCR output for the 8 failing images."""
import cv2
import pytesseract
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))
from fir_specialized_ocr import detect_location_fragments, detect_structured_location

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
IMAGE_DIR = r'F:\FYP\Project\CrimeVision\OCRModel\app\data\raw'

CRIME_STRIPS = [
    (0.38, 0.451, 0.29, 0.62),
    (0.39, 0.49, 0.20, 0.70),
    (0.41, 0.49, 0.20, 0.70),
    (0.43, 0.50, 0.20, 0.70),
]

FAILURES = {
    'FIR_009.png': 'ہال روڈ',
    'FIR_010.png': 'لبرٹی مارکیٹ',
    'FIR_013.png': 'حفیظ سنٹر',
    'FIR_014.png': 'ماڈل ٹاؤن پارک',
    'FIR_015.png': 'فیصل ٹاؤن',
    'FIR_019.png': 'والٹن روڈ',
    'FIR_021.png': 'جیل روڈ',
    'FIR_029.png': 'باغبانپورہ',
}

for fname, expected in FAILURES.items():
    path = os.path.join(IMAGE_DIR, fname)
    if not os.path.exists(path):
        print(f"\n❌ {fname} not found")
        continue
    
    print(f"\n{'='*70}")
    print(f"📂 {fname} — Expected: {expected}")
    print(f"{'='*70}")
    
    image = cv2.imread(path)
    h, w = image.shape[:2]
    
    for strip_idx, (top, bottom, left, right) in enumerate(CRIME_STRIPS):
        y1, y2 = int(h * top), int(h * bottom)
        x1, x2 = int(w * left), int(w * right)
        region = image[y1:y2, x1:x2]
        rh, rw = region.shape[:2]
        if rh < 20 or rw < 50:
            continue
        
        gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY) if len(region.shape) == 3 else region
        
        if rw > 1500: scale = 2.0
        elif rw > 800: scale = 3.0
        else: scale = 4.0
        
        scaled = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(scaled)
        
        strategies = [
            ('PSM6', enhanced, '--oem 3 --psm 6'),
            ('PSM7', enhanced, '--oem 3 --psm 7'),
        ]
        
        # Adaptive
        adaptive = cv2.adaptiveThreshold(enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                          cv2.THRESH_BINARY, 31, 10)
        strategies.append(('Adapt', adaptive, '--oem 3 --psm 6'))
        
        # Otsu
        _, otsu = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        strategies.append(('Otsu', otsu, '--oem 3 --psm 6'))
        
        for sname, img, config in strategies:
            try:
                text = pytesseract.image_to_string(img, lang='urd', config=config)
                if text and text.strip():
                    ur = sum(1 for c in text.strip() if '\u0600' <= c <= '\u06FF')
                    if ur >= 3:
                        raw = text.strip().replace('\n', ' | ')
                        # Check for fragments
                        frags = detect_location_fragments(text.strip(), return_all=True)
                        struct = detect_structured_location(text.strip())
                        tag = ""
                        if struct:
                            tag = f" → STRUCT: {struct}"
                        if frags:
                            tag += f" → FRAG: {frags}"
                        print(f"  S{strip_idx}-{sname}: {raw}{tag}")
            except Exception:
                pass

print("\nDone.")
