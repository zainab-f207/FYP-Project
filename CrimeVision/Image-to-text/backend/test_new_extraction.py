"""Test the redesigned crime area extraction on problem images."""
import sys
import os
import glob

sys.path.insert(0, os.path.dirname(__file__))

# Suppress excessive logging
import logging
logging.basicConfig(level=logging.WARNING)
logging.getLogger('fir_specialized_ocr').setLevel(logging.WARNING)

import cv2
import pytesseract
from fir_specialized_ocr import (
    CRIME_STRIPS, detect_structured_location, detect_location_fragments,
    geocode_crime_area
)

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


def extract_crime_area_test(image_path):
    """Extract crime area with detailed output showing all candidates."""
    import gc
    
    image = cv2.imread(image_path)
    if image is None:
        return "ERROR: Could not read image", []
    
    h, w = image.shape[:2]
    
    # Downsample large images to prevent OOM
    if max(h, w) > 5000:
        s = 3000.0 / max(h, w)
        image = cv2.resize(image, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
        h, w = image.shape[:2]
    elif max(h, w) > 4000:
        s = 2500.0 / max(h, w)
        image = cv2.resize(image, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
        h, w = image.shape[:2]
    
    all_candidates = []
    
    for strip_idx, (top, bottom, left, right) in enumerate(CRIME_STRIPS):
        y1, y2 = int(h * top), int(h * bottom)
        x1, x2 = int(w * left), int(w * right)
        
        region = image[y1:y2, x1:x2]
        rh, rw = region.shape[:2]
        if rh < 20 or rw < 50:
            continue
        
        gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY) if len(region.shape) == 3 else region
        
        if rw > 1500:
            scale = 2.0
        elif rw > 800:
            scale = 3.0
        else:
            scale = 4.0
        
        try:
            scaled = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(scaled)
            del scaled
        except (cv2.error, MemoryError):
            continue
        
        strip_texts = []
        
        # PSM6 on CLAHE
        try:
            text = pytesseract.image_to_string(enhanced, lang='urd', config='--oem 1 --psm 6')
            if text and text.strip():
                ur = sum(1 for c in text.strip() if '\u0600' <= c <= '\u06FF')
                if ur >= 3:
                    strip_texts.append((text.strip(), f'S{strip_idx}-PSM6'))
        except Exception:
            pass
        
        # PSM7
        try:
            text = pytesseract.image_to_string(enhanced, lang='urd', config='--oem 1 --psm 7')
            if text and text.strip():
                ur = sum(1 for c in text.strip() if '\u0600' <= c <= '\u06FF')
                if ur >= 3:
                    strip_texts.append((text.strip(), f'S{strip_idx}-PSM7'))
        except Exception:
            pass
        
        # Adaptive
        try:
            adaptive = cv2.adaptiveThreshold(enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                              cv2.THRESH_BINARY, 31, 10)
            text = pytesseract.image_to_string(adaptive, lang='urd', config='--oem 1 --psm 6')
            if text and text.strip():
                ur = sum(1 for c in text.strip() if '\u0600' <= c <= '\u06FF')
                if ur >= 3:
                    strip_texts.append((text.strip(), f'S{strip_idx}-Adapt'))
            del adaptive
        except Exception:
            pass
        
        # Otsu
        try:
            _, otsu = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            text = pytesseract.image_to_string(otsu, lang='urd', config='--oem 1 --psm 6')
            if text and text.strip():
                ur = sum(1 for c in text.strip() if '\u0600' <= c <= '\u06FF')
                if ur >= 3:
                    strip_texts.append((text.strip(), f'S{strip_idx}-Otsu'))
            del otsu
        except Exception:
            pass
        
        del enhanced
        gc.collect()
        
        for raw_text, engine in strip_texts:
            # Structured
            structured = detect_structured_location(raw_text)
            if structured:
                score = 0.99 + (0.005 if strip_idx == 0 else 0.0)
                all_candidates.append((structured, score, engine + '-Struct'))
            
            # Fragment - ALL matches with positions
            all_frags = detect_location_fragments(raw_text, return_all=True)
            if all_frags:
                multi_frag_bonus = min(0.04, len(all_frags) * 0.015)
                first_loc = all_frags[0][0]
                first_score = 0.95 + multi_frag_bonus
                all_candidates.append((first_loc, first_score, engine + '-Frag1st'))
                
                for loc, pos in all_frags[1:]:
                    all_candidates.append((loc, 0.85, engine + '-FragLater'))
        
        del gray
        gc.collect()
    
    if not all_candidates:
        return "", []
    
    all_candidates.sort(key=lambda x: x[1], reverse=True)
    return all_candidates[0][0], all_candidates[:10]


# Expected answers from fir_summary.txt (first comma-separated part)
EXPECTED = {
    'FIR_17': 'مین بلیوارڈ',
    'FIR_024': 'ہربنس پورہ',
    'FIR_025': 'غری شاہو',
    'FIR_026': 'شاہدرہ ٹاؤن',
}

# Find test images
image_dir = r'D:\FYP\Project\CrimeVision\OCRModel\app\data\raw'

print("=" * 70)
print("TESTING REDESIGNED CRIME AREA EXTRACTION")
print("=" * 70)

for fir_id, expected in EXPECTED.items():
    # Find image file
    patterns = [
        os.path.join(image_dir, f'{fir_id}.*'),
        os.path.join(image_dir, f'{fir_id.lower()}.*'),
    ]
    
    image_path = None
    for pat in patterns:
        matches = glob.glob(pat)
        if matches:
            image_path = matches[0]
            break
    
    if not image_path:
        print(f"\n{fir_id}: IMAGE NOT FOUND")
        continue
    
    print(f"\n{'='*50}")
    print(f"{fir_id}: {os.path.basename(image_path)}")
    print(f"Expected: {expected}")
    
    try:
        result, top_candidates = extract_crime_area_test(image_path)
    except (cv2.error, MemoryError) as e:
        print(f"Result:   ERROR: {e}")
        continue
    
    print(f"Result:   {result}")
    match = expected in result or result in expected
    print(f"Match:    {'✓ PASS' if match else '✗ FAIL'}")
    
    if top_candidates:
        print(f"Top 5 candidates:")
        for text, score, engine in top_candidates[:5]:
            print(f"  {score:.3f} [{engine}] -> {text}")

# Test geocoding
print(f"\n{'='*50}")
print("TESTING GEOCODING (Nominatim - 100% Free)")
print(f"{'='*50}")

test_locations = ['Garden Town', 'مین بلیوارڈ', 'ہربنس پورہ', 'غڑی شاہو']
for loc in test_locations:
    print(f"\nGeocoding: {loc}")
    geo = geocode_crime_area(loc)
    if geo['success']:
        print(f"  ✓ Lat: {geo['latitude']}, Long: {geo['longitude']}")
        print(f"  Address: {geo['display_name'][:80]}")
    else:
        print(f"  ✗ Not found")

print(f"\n{'='*50}")
print("TEST COMPLETE")
print(f"{'='*50}")
