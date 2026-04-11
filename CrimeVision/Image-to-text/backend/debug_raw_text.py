"""Debug: Show raw OCR text for problem images to find recoverable fragments"""
import sys, os, cv2, re
sys.path.insert(0, os.path.dirname(__file__))
from fir_specialized_ocr import CRIME_STRIPS
import pytesseract

IMAGE_DIR = r"F:\FYP\Project\CrimeVision\OCRModel\app\data\raw"

IMAGES = [
    ("FIR_007.png", "ریگل چوک"),
    ("FIR_008.png", "نیلا گنبد"),
    ("FIR_009.png", "ہال روڈ"),
    ("FIR_010.png", "لبرٹی مارکیٹ"),
    ("FIR_014.png", "ماڈل ٹاؤن پارک"),
    ("FIR_017.png", "جوہر ٹاؤن"),
    ("FIR_018.png", "ٹاؤن شپ"),
    ("FIR_019.png", "والٹن روڈ"),
    ("FIR_021.png", "جیل روڈ"),
    ("FIR_027.png", "راوی روڈ"),
    ("FIR_029.png", "باغبانپورہ"),
]

def main():
    for filename, expected in IMAGES:
        img_path = os.path.join(IMAGE_DIR, filename)
        if not os.path.exists(img_path):
            continue
        
        image = cv2.imread(img_path)
        if image is None:
            continue
        h, w = image.shape[:2]
        max_dim = max(h, w)
        if max_dim > 5000:
            scale = 3000 / max_dim
            image = cv2.resize(image, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
            h, w = image.shape[:2]
        
        print(f"\n{'='*70}")
        print(f"📂 {filename} (expected: {expected})")
        print(f"{'='*70}")
        
        # Only check S0 and S1 (first 2 strips - most likely to have crime area)
        for si, (y1f, y2f, x1f, x2f) in enumerate(CRIME_STRIPS[:2]):
            y1, y2 = int(h * y1f), int(h * y2f)
            x1, x2 = int(w * x1f), int(w * x2f)
            if y2 <= y1 or x2 <= x1:
                continue
            row_crop = image[y1:y2, x1:x2]
            rh, rw = row_crop.shape[:2]
            sf = 2.0 if rw > 1500 else (3.0 if rw > 800 else 4.0)
            resized = cv2.resize(row_crop, None, fx=sf, fy=sf, interpolation=cv2.INTER_CUBIC)
            gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            cl = clahe.apply(gray)
            _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            for proc, label in [(cl, f'S{si}-PSM6'), (cl, f'S{si}-PSM7'), (otsu, f'S{si}-Otsu')]:
                config = '--psm 6 --oem 3 -l urd' if 'PSM6' in label else ('--psm 7 --oem 3 -l urd' if 'PSM7' in label else '--psm 6 --oem 3 -l urd')
                try:
                    raw = pytesseract.image_to_string(proc, config=config).strip()
                except:
                    continue
                if raw and len(raw) > 5:
                    # Show first 150 chars
                    display = raw[:150].replace('\n', ' ↵ ')
                    print(f"  {label}: {display}")

if __name__ == '__main__':
    main()
