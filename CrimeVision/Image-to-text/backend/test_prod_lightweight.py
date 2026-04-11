"""
Test crime area extraction using the EXACT production extract_crime_area code path,
but without loading heavy PaddleOCR/EasyOCR models.
"""
import sys, os, re, cv2, gc, io
import numpy as np

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(__file__))

import pytesseract
from fir_specialized_ocr import (
    CRIME_STRIPS, detect_structured_location, detect_location_fragments
)
from urdu_location_dictionary import correct_location_text, KNOWN_LOCATIONS, _urdu_similarity, _normalize_text

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
IMAGE_DIR = r"F:\FYP\Project\CrimeVision\OCRModel\app\data\raw"
SUMMARY_FILE = os.path.join(os.path.dirname(__file__), "fir_summary.txt")


def _clean_crime_area_text(raw_text):
    """Exact copy of FIRExtractor._clean_crime_area_text"""
    text = raw_text.strip()
    if not text:
        return ""
    text = re.sub(r'[\u200e\u200f\u200b\u200c\u200d\u202a-\u202e\u2066-\u2069\ufeff]', '', text)
    lines = text.split('\n')
    if len(lines) > 1:
        location_keywords = [
            'روڈ', 'مارکیٹ', 'چوک', 'گیٹ', 'ٹاؤن', 'بازار', 'بلاک',
            'پارک', 'کالونی', 'نگر', 'پورہ', 'فیز', 'سیکٹر',
            'آباد', 'سوسائٹی', 'ہاؤسنگ', 'دربار', 'ایونیو', 'انٹرچینج',
            'آسکاری', 'بحریہ', 'ڈی ایچ اے', 'والینشیا', 'واپڈا',
        ]
        negative_keywords = ['اطلاع', 'فون', 'بزریعہ', 'ذریعہ', 'موصول',
                            'عوائی', 'ٹریفک', 'صورتحال', 'ٹرییک', 'ہوئی', 'ہوئگی']
        best_line = ""
        best_score = -1
        for line in lines:
            line = line.strip()
            if not line:
                continue
            urdu = sum(1 for c in line if '\u0600' <= c <= '\u06FF')
            keywords_found = sum(1 for kw in location_keywords if kw in line)
            score = urdu + keywords_found * 5
            for nk in negative_keywords:
                if nk in line:
                    score -= 20
            if score > best_score:
                best_score = score
                best_line = line
        if best_line:
            text = best_line
    text = re.sub(r'^[^\u0600-\u06FF]+', '', text)
    labels = [r'جائے\s*وقوعہ', r'جائے\s*اور\s*علاقہ.*', r'تحصیل\s*و\s*ضلع', r'علاقہ\s*تحصیل']
    for label in labels:
        text = re.sub(label, '', text, flags=re.UNICODE)
    text = re.split(r'\s+سے\s+', text)[0]
    distance_pattern = r'(?:سے|ے)\s*(?:تقر|نقر|تھر|تمر|تپ|تر|نر|۲ر|تت)'
    text = re.split(distance_pattern, text)[0]
    dash_patterns = [r'^(.*?)[\-]{2,}', r'^(.*?)[ـ]{3,}', r'^(.*?)[\.۔]{4,}']
    for pattern in dash_patterns:
        match = re.search(pattern, text, re.UNICODE)
        if match:
            text = match.group(1).strip()
            break
    text = re.sub(r'[\d٠-٩\.]+\s*کلو\s*میٹر', '', text)
    text = re.sub(r'[\d٠-٩\.]+\s*کاو\s*می', '', text)
    text = re.sub(r'شمال\s*(?:مشرق|مغرب)?\.?\s*$', '', text)
    text = re.sub(r'جنوب\s*(?:مشرق|مغرب)?\.?\s*$', '', text)
    text = re.sub(r'مشرق[ی]?\s*$', '', text)
    text = re.sub(r'(?:مغرب|مطرب|وخرب|مخرب|مطضرب)\s*$', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    text = re.sub(r'^[\s\-_=.:،۔/\d٠-٩۰-۹]+', '', text)
    text = re.sub(r'[\s\-_=.:،۔]+$', '', text)
    text = re.sub(r'[\[\]{}()!@#$%^&*;:<>|/\\]', '', text)
    text = re.sub(r'[\d٠-٩۰-۹]+\s*$', '', text)
    text = re.sub(r'[a-zA-Z]{1,2}\s*$', '', text)
    return text.strip()


def extract_crime_area_production(image):
    """Exact replication of FIRExtractor.extract_crime_area with latest params."""
    h, w = image.shape[:2]
    if max(h, w) > 5000:
        s = 3000.0 / max(h, w)
        image = cv2.resize(image, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
        h, w = image.shape[:2]
        gc.collect()
    
    all_candidates = []
    
    for strip_idx, (top, bottom, left, right) in enumerate(CRIME_STRIPS):
        y1, y2 = int(h * top), int(h * bottom)
        x1, x2 = int(w * left), int(w * right)
        
        region = image[y1:y2, x1:x2]
        rh, rw = region.shape[:2]
        if rh < 20 or rw < 50:
            continue
        
        # Match production code: resize color → gray → CLAHE
        if rw > 1500:
            scale = 2.0
        elif rw > 800:
            scale = 3.0
        else:
            scale = 4.0
        
        try:
            resized = cv2.resize(region, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
            resized_gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY) if len(resized.shape) == 3 else resized
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(resized_gray)
        except (cv2.error, MemoryError):
            continue
        
        strip_texts = []
        
        # PSM6 on CLAHE
        try:
            text = pytesseract.image_to_string(enhanced, lang='urd', config='--oem 3 --psm 6')
            if text and text.strip():
                ur = sum(1 for c in text.strip() if '\u0600' <= c <= '\u06FF')
                if ur >= 3:
                    strip_texts.append((text.strip(), f'S{strip_idx}-PSM6'))
        except:
            pass
        
        # PSM7
        try:
            text = pytesseract.image_to_string(enhanced, lang='urd', config='--oem 3 --psm 7')
            if text and text.strip():
                ur = sum(1 for c in text.strip() if '\u0600' <= c <= '\u06FF')
                if ur >= 3:
                    strip_texts.append((text.strip(), f'S{strip_idx}-PSM7'))
        except:
            pass
        
        # Adaptive on raw gray (not CLAHE), blockSize=15, C=8
        try:
            adaptive = cv2.adaptiveThreshold(resized_gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                              cv2.THRESH_BINARY, 15, 8)
            text = pytesseract.image_to_string(adaptive, lang='urd', config='--oem 3 --psm 6')
            if text and text.strip():
                ur = sum(1 for c in text.strip() if '\u0600' <= c <= '\u06FF')
                if ur >= 3:
                    strip_texts.append((text.strip(), f'S{strip_idx}-Adapt'))
            del adaptive
        except:
            pass
        
        # Otsu on raw gray (not CLAHE)
        try:
            _, otsu = cv2.threshold(resized_gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            text = pytesseract.image_to_string(otsu, lang='urd', config='--oem 3 --psm 6')
            if text and text.strip():
                ur = sum(1 for c in text.strip() if '\u0600' <= c <= '\u06FF')
                if ur >= 3:
                    strip_texts.append((text.strip(), f'S{strip_idx}-Otsu'))
            del otsu
        except:
            pass
        
        del enhanced, resized_gray
        gc.collect()
        
        # Score candidates - exact production logic
        for raw_text, engine in strip_texts:
            structured = detect_structured_location(raw_text)
            if structured:
                struct_score = 0.99 + (0.005 if strip_idx == 0 else 0.0)
                all_candidates.append((structured, struct_score, engine + '-Struct'))
            
            all_frags = detect_location_fragments(raw_text, return_all=True)
            if all_frags:
                multi_frag_bonus = min(0.04, len(all_frags) * 0.015)
                first_loc = all_frags[0][0]
                first_score = 0.95 + multi_frag_bonus
                all_candidates.append((first_loc, first_score, engine + '-Frag1st'))
                for loc, pos in all_frags[1:]:
                    all_candidates.append((loc, 0.85, engine + '-FragLater'))
            
            cleaned = _clean_crime_area_text(raw_text)
            if not cleaned or len(cleaned) < 3:
                continue
            
            if not all_frags:
                all_frags_c = detect_location_fragments(cleaned, return_all=True)
                if all_frags_c:
                    multi_frag_bonus_c = min(0.03, len(all_frags_c) * 0.01)
                    first_loc_c = all_frags_c[0][0]
                    first_score_c = 0.92 + multi_frag_bonus_c
                    all_candidates.append((first_loc_c, first_score_c, engine + '-FragC1st'))
                    for loc, pos in all_frags_c[1:]:
                        all_candidates.append((loc, 0.83, engine + '-FragCLater'))
            
            urdu_chars = sum(1 for c in cleaned if '\u0600' <= c <= '\u06FF')
            if urdu_chars >= 3:
                clean_score = min(0.78, 0.60 + urdu_chars * 0.01)
                all_candidates.append((cleaned, clean_score, engine + '-Clean'))
            
            corrected = correct_location_text(cleaned)
            if corrected and len(corrected) >= 2:
                norm_corrected = _normalize_text(corrected)
                match_score = 0.0
                for loc in KNOWN_LOCATIONS:
                    sim = _urdu_similarity(norm_corrected, _normalize_text(loc))
                    if sim > match_score:
                        match_score = sim
                fuzzy_score = min(0.70, match_score * 0.65)
                all_candidates.append((corrected, fuzzy_score, engine + '-Fuzzy'))
    
    if not all_candidates:
        return ""
    
    all_candidates.sort(key=lambda x: x[1], reverse=True)
    best = all_candidates[0]
    if best[1] >= 0.15:
        return best[0]
    return ""


def load_expected():
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
                first_part = parts[0].strip()
                last_part = parts[-1].strip() if len(parts) > 1 else ""
                expected[filename] = {'first_part': first_part, 'last_part': last_part}
                i += 2
            else:
                i += 1
        else:
            i += 1
    return expected


def is_first_part_match(extracted, expected_first):
    if not extracted or not expected_first:
        return False
    e = extracted.strip()
    f = expected_first.strip()
    if f in e or e in f:
        return True
    e_words = set(e.split())
    f_words = set(f.split())
    if f_words and e_words:
        overlap = len(e_words & f_words)
        if overlap >= max(1, len(f_words) * 0.5):
            return True
    fuzzy_pairs = [
        ('غڑی', 'غری'), ('شاہو', 'شاھو'), ('گدائی', 'گدافی'),
        ('لوہاری', 'لزاری'), ('لبارٹ', 'لبرٹ'),
    ]
    for a, b in fuzzy_pairs:
        if (a in e and b in f) or (b in e and a in f):
            return True
    return False


def main():
    expected_data = load_expected()
    correct = 0; thana_match = 0; no_result = 0; other_wrong = 0; total = 0
    wrong_list = []
    test_count = 30
    tested = 0
    
    for fname in sorted(expected_data.keys()):
        if tested >= test_count:
            break
        path = os.path.join(IMAGE_DIR, fname)
        if not os.path.exists(path):
            continue
        
        total += 1; tested += 1
        exp = expected_data[fname]
        expected_first = exp['first_part']
        expected_last = exp['last_part']
        
        image = cv2.imread(path)
        if image is None:
            no_result += 1; continue
        
        result = extract_crime_area_production(image)
        
        print(f"\n{'='*60}")
        print(f"FIR: {fname}")
        print(f"   Expected first: {expected_first}")
        print(f"   Expected last:  {expected_last}")
        print(f"   Extracted: {result}")
        
        if not result:
            print(f"   >> NO RESULT"); no_result += 1
            wrong_list.append((fname, result, expected_first))
        elif is_first_part_match(result, expected_first):
            print(f"   >> CORRECT (first part)"); correct += 1
        elif is_first_part_match(result, expected_last):
            print(f"   >> WRONG (got thana!)"); thana_match += 1
            wrong_list.append((fname, result, expected_first))
        else:
            print(f"   >> OTHER"); other_wrong += 1
            wrong_list.append((fname, result, expected_first))
    
    print(f"\n{'='*60}")
    print(f"PRODUCTION CODE PATH TEST (first {test_count} images)")
    print(f"{'='*60}")
    print(f"  Total tested:       {total}")
    print(f"  Correct (1st part): {correct}/{total} ({100*correct/total:.1f}%)")
    print(f"  Wrong (thana):      {thana_match}/{total}")
    print(f"  No result:          {no_result}/{total}")
    print(f"  Other wrong:        {other_wrong}/{total}")
    
    if wrong_list:
        print(f"\nFailed images:")
        for fname, got, should_be in wrong_list:
            got_short = (got[:60] + '...') if got and len(got) > 60 else got
            print(f"  {fname}: got '{got_short}' expected '{should_be}'")


if __name__ == '__main__':
    main()
