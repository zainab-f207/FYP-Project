"""
Batch test: Verify crime area extraction returns FIRST PART (specific location)
not the thana/area name (last part).
Tests against fir_summary.txt expected values.
"""
import sys
import os
import cv2
import re

sys.path.insert(0, os.path.dirname(__file__))

from fir_specialized_ocr import (
    CRIME_STRIPS, detect_structured_location, detect_location_fragments,
    geocode_crime_area
)
import pytesseract

IMAGE_DIR = r"F:\FYP\Project\CrimeVision\OCRModel\app\data\raw"
SUMMARY_FILE = os.path.join(os.path.dirname(__file__), "fir_summary.txt")

def load_expected():
    """Load expected crime locations from fir_summary.txt (first comma-separated part)"""
    expected = {}
    with open(SUMMARY_FILE, 'r', encoding='utf-8') as f:
        lines = f.read().strip().split('\n')
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith('FIR_') and line.endswith('.png'):
            filename = line
            if i + 1 < len(lines):
                full_text = lines[i + 1].strip()
                # Extract FIRST part (before first comma)
                parts = re.split(r'[،,]', full_text)
                first_part = parts[0].strip() if parts else full_text.strip()
                # Also get last part (thana name) for comparison
                last_part = parts[-1].strip() if len(parts) > 1 else ""
                expected[filename] = {
                    'first_part': first_part,
                    'full': full_text,
                    'last_part': last_part
                }
                i += 2
            else:
                i += 1
        else:
            i += 1
    return expected

def extract_crime_area_standalone(image_path):
    """Extract crime area from image (standalone version of extract_crime_area)"""
    image = cv2.imread(image_path)
    if image is None:
        return ""
    
    h, w = image.shape[:2]
    
    # Downsample large images
    max_dim = max(h, w)
    if max_dim > 5000:
        scale = 3000 / max_dim
        image = cv2.resize(image, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
        h, w = image.shape[:2]
    
    best_result = ""
    best_score = 0
    
    for si, (y1f, y2f, x1f, x2f) in enumerate(CRIME_STRIPS):
        y1, y2 = int(h * y1f), int(h * y2f)
        x1, x2 = int(w * x1f), int(w * x2f)
        
        if y2 <= y1 or x2 <= x1:
            continue
        
        row_crop = image[y1:y2, x1:x2]
        rh, rw = row_crop.shape[:2]
        
        if rw > 1500:
            scale_factor = 2.0
        elif rw > 800:
            scale_factor = 3.0
        else:
            scale_factor = 4.0
        
        resized = cv2.resize(row_crop, None, fx=scale_factor, fy=scale_factor, interpolation=cv2.INTER_CUBIC)
        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
        
        strategies = []
        
        # PSM6 + CLAHE
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        cl = clahe.apply(gray)
        strategies.append((cl, '--psm 6 --oem 3 -l urd', f'S{si}-PSM6'))
        
        # PSM7
        strategies.append((cl, '--psm 7 --oem 3 -l urd', f'S{si}-PSM7'))
        
        # Adaptive threshold
        adapt = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 8)
        strategies.append((adapt, '--psm 6 --oem 3 -l urd', f'S{si}-Adapt'))
        
        # Otsu
        _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        strategies.append((otsu, '--psm 6 --oem 3 -l urd', f'S{si}-Otsu'))
        
        for proc_img, config, label in strategies:
            try:
                raw = pytesseract.image_to_string(proc_img, config=config).strip()
            except:
                continue
            
            if not raw or len(raw) < 3:
                continue
            
            # Check structured
            struct = detect_structured_location(raw)
            if struct:
                score = 0.99
                if score > best_score:
                    best_score = score
                    best_result = struct
                continue
            
            # Fragment detection with return_all
            all_frags = detect_location_fragments(raw, return_all=True)
            if all_frags:
                for idx, (frag, pos) in enumerate(all_frags):
                    if idx == 0:
                        multi_bonus = min(0.03, len(all_frags) * 0.015)
                        score = 0.95 + multi_bonus
                    else:
                        score = 0.85
                    
                    if score > best_score:
                        best_score = score
                        best_result = frag
                continue
            
            # Clean text
            clean = raw
            for p in [r'جائے?\s*وقوعہ', r'جائ[ےی]\s*اور\s*علاق', r'وقوعہ\s*کا\s*مقام']:
                clean = re.sub(p, '', clean)
            clean = re.sub(r'[0-9۰-۹٠-٩.,:;/\\()\[\]{}|!@#$%^&*+=<>?~`\'\"_\-]+', ' ', clean)
            clean = re.sub(r'\s+', ' ', clean).strip()
            
            if clean and len(clean) >= 3:
                score = 0.78
                if score > best_score:
                    best_score = score
                    best_result = clean
    
    return best_result


def is_first_part_match(extracted, expected_first):
    """Check if extracted text matches the expected first part"""
    if not extracted or not expected_first:
        return False
    
    # Normalize
    def norm(t):
        t = re.sub(r'\s+', ' ', t).strip()
        t = t.replace('ی', 'ی').replace('ک', 'ک').replace('ہ', 'ہ')
        return t
    
    ext = norm(extracted)
    exp = norm(expected_first)
    
    # Exact match
    if ext == exp:
        return True
    
    # Substring match (expected in extracted or vice versa)
    if exp in ext or ext in exp:
        return True
    
    # Check if any significant word from expected appears in extracted
    exp_words = [w for w in exp.split() if len(w) > 2]
    ext_words = [w for w in ext.split() if len(w) > 2]
    
    if exp_words:
        matches = sum(1 for w in exp_words if any(w in ew or ew in w for ew in ext_words))
        if matches >= len(exp_words) * 0.5:
            return True
    
    return False


def is_thana_match(extracted, expected_last):
    """Check if extracted matches the thana/last part (BAD - means we got the wrong thing)"""
    if not extracted or not expected_last:
        return False
    
    def norm(t):
        t = re.sub(r'\s+', ' ', t).strip()
        return t
    
    ext = norm(extracted)
    exp = norm(expected_last)
    
    if ext == exp or exp in ext or ext in exp:
        return True
    
    return False


def main():
    expected = load_expected()
    print(f"Loaded {len(expected)} expected values from fir_summary.txt")
    
    # Test a sample (first 30 images)
    test_files = sorted(expected.keys())[:30]
    
    correct_first = 0
    wrong_thana = 0
    no_result = 0
    other_wrong = 0
    total = 0
    
    results = []
    
    for filename in test_files:
        img_path = os.path.join(IMAGE_DIR, filename)
        if not os.path.exists(img_path):
            continue
        
        total += 1
        info = expected[filename]
        
        print(f"\n{'='*60}")
        print(f"📂 {filename}")
        print(f"   Expected first: {info['first_part']}")
        print(f"   Expected last:  {info['last_part']}")
        
        extracted = extract_crime_area_standalone(img_path)
        
        first_match = is_first_part_match(extracted, info['first_part'])
        thana_match = is_thana_match(extracted, info['last_part']) if info['last_part'] else False
        
        if first_match and not thana_match:
            status = "✅ CORRECT (first part)"
            correct_first += 1
        elif first_match and thana_match:
            status = "⚠️ AMBIGUOUS (matches both)"
            correct_first += 1  # Still count as correct
        elif thana_match and not first_match:
            status = "❌ WRONG (got thana name!)"
            wrong_thana += 1
        elif not extracted:
            status = "❌ NO RESULT"
            no_result += 1
        else:
            status = "❌ OTHER"
            other_wrong += 1
        
        print(f"   Extracted: {extracted}")
        print(f"   {status}")
        
        results.append({
            'file': filename,
            'expected_first': info['first_part'],
            'expected_last': info['last_part'],
            'extracted': extracted,
            'status': status
        })
    
    print(f"\n{'='*60}")
    print(f"BATCH TEST RESULTS (first 30 images)")
    print(f"{'='*60}")
    print(f"  Total tested:         {total}")
    print(f"  ✅ Correct (first part): {correct_first}/{total} ({100*correct_first/total:.1f}%)")
    print(f"  ❌ Wrong (got thana):    {wrong_thana}/{total}")
    print(f"  ❌ No result:            {no_result}/{total}")
    print(f"  ❌ Other wrong:          {other_wrong}/{total}")
    
    if wrong_thana > 0:
        print(f"\n⚠️ Images that returned THANA instead of specific location:")
        for r in results:
            if "WRONG (got thana" in r['status']:
                print(f"  {r['file']}: got '{r['extracted']}' should be '{r['expected_first']}'")
    
    if other_wrong > 0:
        print(f"\n⚠️ Images with other wrong results:")
        for r in results:
            if "OTHER" in r['status']:
                print(f"  {r['file']}: got '{r['extracted']}' should be '{r['expected_first']}'")


if __name__ == '__main__':
    main()
