"""
Test script: Crime area extraction (first part, NOT thana) + geocoding (lat/long).
Tests on FIR_17, FIR_024, FIR_025, FIR_026 from raw images.
"""
import os
import sys
import cv2
import gc

sys.path.insert(0, os.path.dirname(__file__))

IMAGE_DIR = r"F:\FYP\Project\CrimeVision\OCRModel\app\data\raw"

# Expected FIRST PART of crime location (NOT thana name)
EXPECTED = {
    "FIR_17.png":  "مین بلیوارڈ",          # NOT گارڈن ٹاؤن
    "FIR_024.png": "ہربنس پورہ",           # NOT حسین چوک or فیکٹری ایریا  
    "FIR_025.png": "غری شاہو",             # NOT اقبال ٹاؤن or شاہدرہ ٹاؤن
    "FIR_026.png": "شاہدرہ ٹاؤن",          # This IS the first part
    "FIR_001.png": "ایس ایم سن روڈ",       # Specific location
    "FIR_004.png": "گلشن راوی",            # Specific location  
}

def test_crime_area():
    """Test extract_crime_area on multiple images and geocode each result."""
    # Import just the pieces we need (avoid loading EasyOCR)
    import pytesseract
    import numpy as np
    
    # Import the production module
    from fir_specialized_ocr import (
        CRIME_STRIPS, detect_structured_location, detect_location_fragments,
        geocode_crime_area
    )
    from urdu_location_dictionary import correct_location_text, KNOWN_LOCATIONS, _urdu_similarity, _normalize_text
    import re
    
    # Minimal _clean_crime_area_text (from production, no class needed)
    def clean_text(raw_text):
        text = raw_text.strip()
        if not text:
            return ""
        text = re.sub(r'[\u200e\u200f\u200b\u200c\u200d\u202a-\u202e\u2066-\u2069\ufeff]', '', text)
        lines = text.split('\n')
        if len(lines) > 1:
            location_keywords = ['روڈ', 'مارکیٹ', 'چوک', 'گیٹ', 'ٹاؤن', 'بازار', 'بلاک',
                                 'پارک', 'کالونی', 'نگر', 'پورہ', 'فیز', 'سیکٹر',
                                 'آباد', 'سوسائٹی', 'ہاؤسنگ', 'دربار', 'ایونیو', 'انٹرچینج']
            negative_keywords = ['اطلاع', 'فون', 'بزریعہ', 'ذریعہ', 'موصول',
                                'عوائی', 'ٹریفک', 'صورتحال']
            best_line, best_score = "", -1
            for line in lines:
                line = line.strip()
                if not line: continue
                urdu = sum(1 for c in line if '\u0600' <= c <= '\u06FF')
                keywords_found = sum(1 for kw in location_keywords if kw in line)
                sc = urdu + keywords_found * 5
                for nk in negative_keywords:
                    if nk in line: sc -= 20
                if sc > best_score: best_score, best_line = sc, line
            if best_line: text = best_line
        
        text = re.sub(r'^[^\u0600-\u06FF]+', '', text)
        text = re.split(r'\s+سے\s+', text)[0]
        text = re.split(r'(?:سے|ے)\s*(?:تقر|نقر|تھر|تمر|تپ|تر|نر|۲ر|تت)', text)[0]
        for pat in [r'^(.*?)[\-]{2,}', r'^(.*?)[ـ]{3,}', r'^(.*?)[\.۔]{4,}']:
            m = re.search(pat, text, re.UNICODE)
            if m: text = m.group(1).strip(); break
        text = re.sub(r'[\d٠-٩\.]+\s*کلو\s*میٹر', '', text)
        text = re.sub(r'[\d٠-٩\.]+\s*کاو\s*می', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        text = re.sub(r'^[\s\-_=.:،۔/\d٠-٩۰-۹]+', '', text)
        text = re.sub(r'[\s\-_=.:،۔]+$', '', text)
        text = re.sub(r'[\[\]{}()!@#$%^&*;:<>|/\\]', '', text)
        text = re.sub(r'[\d٠-٩۰-۹]+\s*$', '', text)
        text = re.sub(r'[a-zA-Z]{1,2}\s*$', '', text)
        return text.strip()
    
    test_files = ["FIR_17.png", "FIR_024.png", "FIR_025.png", "FIR_026.png"]
    
    print("=" * 80)
    print("CRIME AREA EXTRACTION + GEOCODING TEST")
    print("=" * 80)
    
    results = {}
    
    for fname in test_files:
        img_path = os.path.join(IMAGE_DIR, fname)
        if not os.path.exists(img_path):
            print(f"\n❌ {fname}: File not found")
            continue
        
        print(f"\n{'='*60}")
        print(f"📂 {fname}")
        print(f"   Expected: {EXPECTED.get(fname, '?')}")
        print(f"{'='*60}")
        
        image = cv2.imread(img_path)
        h, w = image.shape[:2]
        
        # Downsample if needed
        if max(h, w) > 5000:
            s = 3000.0 / max(h, w)
            image = cv2.resize(image, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
            h, w = image.shape[:2]
            print(f"   Downsampled to {w}x{h}")
            gc.collect()
        
        all_candidates = []
        
        for strip_idx, (top, bottom, left, right) in enumerate(CRIME_STRIPS):
            y1, y2 = int(h * top), int(h * bottom)
            x1, x2 = int(w * left), int(w * right)
            region = image[y1:y2, x1:x2]
            rh, rw = region.shape[:2]
            if rh < 20 or rw < 50: continue
            
            gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY) if len(region.shape) == 3 else region
            
            if rw > 1500: scale = 2.0
            elif rw > 800: scale = 3.0
            else: scale = 4.0
            
            try:
                scaled = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                enhanced = clahe.apply(scaled)
                del scaled
            except (cv2.error, MemoryError):
                continue
            
            strip_texts = []
            # PSM6
            try:
                text = pytesseract.image_to_string(enhanced, lang='urd', config='--oem 3 --psm 6')
                if text and text.strip():
                    ur = sum(1 for c in text.strip() if '\u0600' <= c <= '\u06FF')
                    if ur >= 3: strip_texts.append((text.strip(), f'S{strip_idx}-PSM6'))
            except: pass
            # PSM7
            try:
                text = pytesseract.image_to_string(enhanced, lang='urd', config='--oem 3 --psm 7')
                if text and text.strip():
                    ur = sum(1 for c in text.strip() if '\u0600' <= c <= '\u06FF')
                    if ur >= 3: strip_texts.append((text.strip(), f'S{strip_idx}-PSM7'))
            except: pass
            # Adaptive
            try:
                adaptive = cv2.adaptiveThreshold(enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 10)
                text = pytesseract.image_to_string(adaptive, lang='urd', config='--oem 3 --psm 6')
                if text and text.strip():
                    ur = sum(1 for c in text.strip() if '\u0600' <= c <= '\u06FF')
                    if ur >= 3: strip_texts.append((text.strip(), f'S{strip_idx}-Adapt'))
                del adaptive
            except: pass
            # Otsu
            try:
                _, otsu = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                text = pytesseract.image_to_string(otsu, lang='urd', config='--oem 3 --psm 6')
                if text and text.strip():
                    ur = sum(1 for c in text.strip() if '\u0600' <= c <= '\u06FF')
                    if ur >= 3: strip_texts.append((text.strip(), f'S{strip_idx}-Otsu'))
                del otsu
            except: pass
            
            del enhanced
            gc.collect()
            
            for raw_text, engine in strip_texts:
                # Show raw text (first 80 chars)
                raw_preview = raw_text.replace('\n', ' ')[:80]
                
                # Structured
                structured = detect_structured_location(raw_text)
                if structured:
                    all_candidates.append((structured, 0.99, engine + '-Struct'))
                
                # Fragment - ALL matches with positions
                all_frags = detect_location_fragments(raw_text, return_all=True)
                if all_frags:
                    print(f"   🔍 {engine} frags: {[(loc, pos) for loc, pos in all_frags]}")
                if all_frags:
                    multi_bonus = min(0.04, len(all_frags) * 0.015)
                    first_loc = all_frags[0][0]
                    first_score = 0.95 + multi_bonus
                    all_candidates.append((first_loc, first_score, engine + '-Frag1st'))
                    for loc, pos in all_frags[1:]:
                        all_candidates.append((loc, 0.85, engine + '-FragLater'))
                
                # Clean
                cleaned = clean_text(raw_text)
                if not cleaned or len(cleaned) < 3: continue
                
                if not all_frags:
                    all_frags_c = detect_location_fragments(cleaned, return_all=True)
                    if all_frags_c:
                        first_loc_c = all_frags_c[0][0]
                        all_candidates.append((first_loc_c, 0.92, engine + '-FragC1st'))
                        for loc, pos in all_frags_c[1:]:
                            all_candidates.append((loc, 0.83, engine + '-FragCLater'))
                
                # Cleaned text as fallback
                urdu_chars = sum(1 for c in cleaned if '\u0600' <= c <= '\u06FF')
                if urdu_chars >= 3:
                    clean_score = min(0.78, 0.60 + urdu_chars * 0.01)
                    all_candidates.append((cleaned, clean_score, engine + '-Clean'))
                
                # Fuzzy (capped at 0.70)
                corrected = correct_location_text(cleaned)
                if corrected and len(corrected) >= 2:
                    norm_corrected = _normalize_text(corrected)
                    match_score = 0.0
                    for loc in KNOWN_LOCATIONS:
                        sim = _urdu_similarity(norm_corrected, _normalize_text(loc))
                        if sim > match_score: match_score = sim
                    fuzzy_score = min(0.70, match_score * 0.65)
                    all_candidates.append((corrected, fuzzy_score, engine + '-Fuzzy'))
            
            del gray
            gc.collect()
        
        if not all_candidates:
            print(f"   ❌ No candidates found!")
            results[fname] = ("", False)
            continue
        
        all_candidates.sort(key=lambda x: x[1], reverse=True)
        
        # Show top candidates
        print(f"\n   Top candidates:")
        for i, (text, score, eng) in enumerate(all_candidates[:10]):
            marker = " ⬅️ WINNER" if i == 0 else ""
            print(f"   {i+1}. [{score:.3f}] {eng}: {text}{marker}")
        
        best = all_candidates[0]
        crime_area = best[0] if best[1] >= 0.15 else ""
        expected = EXPECTED.get(fname, "")
        
        # Check if expected is contained in result or vice versa
        match = expected in crime_area or crime_area in expected if crime_area and expected else False
        status = "✅" if match else "❌"
        
        print(f"\n   {status} Result: {crime_area}")
        print(f"   Expected: {expected}")
        
        # Geocode
        if crime_area:
            print(f"\n   🌐 Geocoding '{crime_area}'...")
            geo = geocode_crime_area(crime_area)
            if geo['success']:
                print(f"   ✅ Lat: {geo['latitude']}, Long: {geo['longitude']}")
                print(f"   📍 Address: {geo['display_name']}")
            else:
                print(f"   ❌ Geocoding failed")
            results[fname] = (crime_area, match, geo)
        else:
            results[fname] = (crime_area, match, None)
    
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    for fname, res in results.items():
        if len(res) == 3:
            area, match, geo = res
            status = "✅" if match else "❌"
            geo_str = f"({geo['latitude']}, {geo['longitude']})" if geo and geo.get('success') else "No coords"
            print(f"  {status} {fname}: {area} -> {geo_str}")
        else:
            area, match = res
            status = "✅" if match else "❌"
            print(f"  {status} {fname}: {area}")


if __name__ == "__main__":
    test_crime_area()
