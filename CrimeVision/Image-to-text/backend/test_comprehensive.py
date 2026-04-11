"""
Comprehensive batch test: ALL images in fir_summary.txt
Tests extract_crime_area production method matches expected first part.
"""
import sys
import os
import cv2
import re
import time

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')  # type: ignore[attr-defined]
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')  # type: ignore[attr-defined]
sys.path.insert(0, os.path.dirname(__file__))

from fir_specialized_ocr import (
    CRIME_STRIPS, detect_structured_location, detect_location_fragments
)
import pytesseract
import importlib
import importlib.util

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
                parts = re.split(r'[،,]', full_text)
                first_part = parts[0].strip() if parts else full_text.strip()
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


def extract_standalone(image_path):
    """Extract crime area using the same logic as the production method"""
    image = cv2.imread(image_path)
    if image is None:
        return ""
    
    h, w = image.shape[:2]
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
            sf = 2.0
        elif rw > 800:
            sf = 3.0
        else:
            sf = 4.0
        
        resized = cv2.resize(row_crop, None, fx=sf, fy=sf, interpolation=cv2.INTER_CUBIC)
        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
        
        strategies = []
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        cl = clahe.apply(gray)
        strategies.append((cl, '--psm 6 --oem 3 -l urd'))
        strategies.append((cl, '--psm 7 --oem 3 -l urd'))
        adapt = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 8)
        strategies.append((adapt, '--psm 6 --oem 3 -l urd'))
        _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        strategies.append((otsu, '--psm 6 --oem 3 -l urd'))
        
        for proc_img, config in strategies:
            try:
                raw = pytesseract.image_to_string(proc_img, config=config).strip()
            except:
                continue
            if not raw or len(raw) < 3:
                continue
            
            struct = detect_structured_location(raw)
            if struct:
                score = 0.99
                if score > best_score:
                    best_score = score
                    best_result = struct
                continue
            
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


def is_match(extracted, expected_first):
    """Check if extracted text matches expected first part (lenient)"""
    if not extracted or not expected_first:
        return False
    
    def norm(t):
        t = re.sub(r'\s+', ' ', t).strip()
        t = t.replace('ی', 'ی').replace('ک', 'ک').replace('ہ', 'ہ')
        return t
    
    ext = norm(extracted)
    exp = norm(expected_first)
    
    if ext == exp:
        return True
    if exp in ext or ext in exp:
        return True
    
    # Word overlap
    exp_words = [w for w in exp.split() if len(w) > 2]
    ext_words = [w for w in ext.split() if len(w) > 2]
    
    if exp_words:
        matches = sum(1 for w in exp_words if any(w in ew or ew in w for ew in ext_words))
        if matches >= max(1, len(exp_words) * 0.5):
            return True
    
    return False


def main():
    expected = load_expected()
    print(f"Loaded {len(expected)} expected values")
    
    # Only test images that exist
    existing = []
    for filename in sorted(expected.keys()):
        if os.path.exists(os.path.join(IMAGE_DIR, filename)):
            existing.append(filename)
    
    print(f"Found {len(existing)} images on disk")
    
    # Parse command line for range
    start_idx = 0
    end_idx = len(existing)
    if len(sys.argv) > 1:
        start_idx = int(sys.argv[1])
    if len(sys.argv) > 2:
        end_idx = int(sys.argv[2])
    
    test_files = existing[start_idx:end_idx]
    print(f"Testing images [{start_idx}:{end_idx}] = {len(test_files)} images")
    
    correct = 0
    wrong = 0
    no_result = 0
    total = 0
    failures = []
    
    for filename in test_files:
        img_path = os.path.join(IMAGE_DIR, filename)
        total += 1
        info = expected[filename]
        
        extracted = extract_standalone(img_path)
        matched = is_match(extracted, info['first_part'])
        
        if matched:
            correct += 1
            status = "OK"
        elif not extracted:
            no_result += 1
            status = "EMPTY"
            failures.append((filename, extracted, info['first_part']))
        else:
            wrong += 1
            status = "WRONG"
            failures.append((filename, extracted, info['first_part']))
        
        pct = 100 * correct / total
        print(f"[{total:3d}] {status:5s} | {filename:15s} | got='{extracted[:40]}' | exp='{info['first_part'][:40]}' | {pct:.0f}%")
    
    print(f"\n{'='*70}")
    print(f"RESULTS: {correct}/{total} ({100*correct/total:.1f}%)")
    print(f"  Correct: {correct}")
    print(f"  Wrong:   {wrong}")
    print(f"  Empty:   {no_result}")
    print(f"{'='*70}")
    
    if failures:
        print(f"\nFAILURES ({len(failures)}):")
        for fn, got, exp in failures:
            print(f"  {fn}: got='{got}' expected='{exp}'")
    
    # Save results
    with open('comprehensive_test_results.txt', 'w', encoding='utf-8') as f:
        f.write(f"RESULTS: {correct}/{total} ({100*correct/total:.1f}%)\n")
        f.write(f"Correct: {correct}, Wrong: {wrong}, Empty: {no_result}\n\n")
        if failures:
            f.write(f"FAILURES ({len(failures)}):\n")
            for fn, got, exp in failures:
                f.write(f"  {fn}: got='{got}' expected='{exp}'\n")


if __name__ == '__main__':
    main()
