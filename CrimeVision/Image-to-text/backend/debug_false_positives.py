"""Debug: What fragments are triggering for incorrectly matched images"""
import sys, os, cv2, re
sys.path.insert(0, os.path.dirname(__file__))
from fir_specialized_ocr import CRIME_STRIPS, detect_structured_location, detect_location_fragments
import pytesseract

IMAGE_DIR = r"F:\FYP\Project\CrimeVision\OCRModel\app\data\raw"

# Problem images that falsely match 'غڑی شاہو' or other wrong fragments
PROBLEM_IMAGES = [
    ("FIR_003.png", "شاہ عالمی مارکیٹ"),
    ("FIR_005.png", "دہلی گیٹ"),
    ("FIR_011.png", "مین بلیوارڈ گلبرگ"),
    ("FIR_015.png", "فیصل ٹاؤن"),
    ("FIR_009.png", "ہال روڈ"),
    ("FIR_010.png", "لبرٹی مارکیٹ"),
    ("FIR_013.png", "حفیظ سنٹر"),
    ("FIR_014.png", "ماڈل ٹاؤن پارک"),
    ("FIR_017.png", "جوہر ٹاؤن"),
    ("FIR_018.png", "ٹاؤن شپ"),
    ("FIR_029.png", "باغبانپورہ"),
]

def get_raw_ocr(image_path):
    """Get raw OCR text from all strips and strategies"""
    image = cv2.imread(image_path)
    if image is None:
        return []
    h, w = image.shape[:2]
    max_dim = max(h, w)
    if max_dim > 5000:
        scale = 3000 / max_dim
        image = cv2.resize(image, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
        h, w = image.shape[:2]
    
    results = []
    for si, (y1f, y2f, x1f, x2f) in enumerate(CRIME_STRIPS):
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
        adapt = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 8)
        _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        strategies = [
            (cl, '--psm 6 --oem 3 -l urd', f'S{si}-PSM6'),
            (cl, '--psm 7 --oem 3 -l urd', f'S{si}-PSM7'),
            (adapt, '--psm 6 --oem 3 -l urd', f'S{si}-Adapt'),
            (otsu, '--psm 6 --oem 3 -l urd', f'S{si}-Otsu'),
        ]
        for proc_img, config, label in strategies:
            try:
                raw = pytesseract.image_to_string(proc_img, config=config).strip()
            except:
                continue
            if raw and len(raw) >= 3:
                frags = detect_location_fragments(raw, return_all=True)
                results.append((label, raw, frags))
    return results


def main():
    # Search for specific fragments in raw text
    ghost_patterns = ['شاو', 'شاہو', 'غری', 'غڑی', 'غڑ', 'شاہ']
    
    for filename, expected in PROBLEM_IMAGES:
        img_path = os.path.join(IMAGE_DIR, filename)
        if not os.path.exists(img_path):
            continue
        
        print(f"\n{'='*70}")
        print(f"📂 {filename} (expected: {expected})")
        print(f"{'='*70}")
        
        results = get_raw_ocr(img_path)
        
        for label, raw, frags in results:
            # Check if any ghost patterns appear in the raw text
            ghost_found = []
            for gp in ghost_patterns:
                if gp in raw:
                    pos = raw.find(gp)
                    context = raw[max(0,pos-10):pos+len(gp)+10]
                    ghost_found.append(f"'{gp}' at pos {pos}: ...{context}...")
            
            if frags or ghost_found:
                print(f"\n  {label}:")
                if len(raw) > 100:
                    print(f"    Raw: {raw[:100]}...")
                else:
                    print(f"    Raw: {raw}")
                if frags:
                    print(f"    Frags: {frags}")
                for gf in ghost_found:
                    print(f"    ⚠️ Ghost pattern: {gf}")


if __name__ == '__main__':
    main()
