"""Debug: Show raw OCR output from crime area strips."""
import cv2, os, sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
import pytesseract

IMAGE_DIR = r"D:\FYP\Project\CrimeVision\OCRModel\app\data\raw"

CRIME_STRIPS = [
    (0.38, 0.451, 0.29, 0.62),
    (0.39, 0.49, 0.20, 0.70),
    (0.41, 0.49, 0.20, 0.70),
    (0.43, 0.50, 0.20, 0.70),
]

for fname in ['FIR_17.png', 'FIR_024.png', 'FIR_025.png', 'FIR_026.png']:
    img_path = os.path.join(IMAGE_DIR, fname)
    if not os.path.exists(img_path):
        continue
    file_size = os.path.getsize(img_path)
    img = cv2.imread(img_path, cv2.IMREAD_REDUCED_COLOR_2) if file_size > 15_000_000 else cv2.imread(img_path)
    if img is None:
        continue
    h, w = img.shape[:2]
    if max(h, w) > 5000:
        s = 3000.0 / max(h, w)
        img = cv2.resize(img, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
        h, w = img.shape[:2]
    
    print(f'\n{"="*60}')
    print(f'=== {fname} ({w}x{h}) ===')
    print(f'{"="*60}')
    for si, (top, bottom, left, right) in enumerate(CRIME_STRIPS[:2]):
        y1, y2 = int(h * top), int(h * bottom)
        x1, x2 = int(w * left), int(w * right)
        region = img[y1:y2, x1:x2]
        gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
        rh, rw = gray.shape[:2]
        scale = 2.0 if rw > 1500 else (3.0 if rw > 800 else 4.0)
        scaled = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
        enhanced = clahe.apply(scaled)
        text = pytesseract.image_to_string(enhanced, lang='urd', config='--oem 1 --psm 6')
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        joined = ' | '.join(lines)
        print(f'  S{si}-PSM6: {joined}')
