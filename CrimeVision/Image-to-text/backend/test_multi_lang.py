"""Test Tesseract with multiple Arabic-script languages and tessdata_best"""
import cv2
import numpy as np
import pytesseract
import os
import sys

print("=" * 60)
print("TESSERACT MULTI-LANGUAGE + TESSDATA TEST")
print("=" * 60)

img_path = "crime_area_best.png"
if not os.path.exists(img_path):
    print(f"ERROR: {img_path} not found")
    sys.exit(1)

img = cv2.imread(img_path)
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
h, w = gray.shape
print(f"Image: {w}x{h}")

# Check tessdata path
tessdata = os.environ.get('TESSDATA_PREFIX', '')
print(f"TESSDATA_PREFIX: {tessdata}")

# Try to find tessdata path
try:
    info = pytesseract.get_tesseract_version()
    print(f"Tesseract version: {info}")
except:
    pass

# Best preprocessing from previous testing: 1x scale, adaptive block=51, offset=15
# Also test with Otsu and raw
preprocessed = {}

# 1. Raw grayscale
preprocessed['raw'] = gray

# 2. Otsu
_, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
preprocessed['otsu'] = otsu

# 3. Adaptive b51 o15 (best from previous test)
adaptive = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 51, 15)
preprocessed['adaptive'] = adaptive

# 4. Denoised + Otsu
denoised = cv2.fastNlMeansDenoising(gray, None, h=10, templateWindowSize=7, searchWindowSize=21)
_, dn_otsu = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
preprocessed['denoised_otsu'] = dn_otsu

# 5. CLAHE enhanced
clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
enhanced = clahe.apply(gray)
preprocessed['clahe'] = enhanced

# 6. Sharpen after denoise
kernel_sharp = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
sharpened = cv2.filter2D(denoised, -1, kernel_sharp)
preprocessed['sharpened'] = sharpened

# Language combinations to test
lang_combos = [
    'urd',         # Urdu only (current)
    'ara',         # Arabic only (often better trained)
    'urd+ara',     # Urdu + Arabic
    'ara+urd',     # Arabic + Urdu (priority order matters)
    'fas',         # Farsi/Persian (also Nastaliq)
    'urd+ara+fas', # All three
    'pus',         # Pashto
    'snd',         # Sindhi
]

# PSM modes to test
psm_modes = [6, 4, 3, 7, 11, 12, 13]

results = []

# Test each combination
for lang in lang_combos:
    for prep_name, prep_img in preprocessed.items():
        for psm in [6]:  # Start with PSM 6 (best from previous testing)
            try:
                config = f'--psm {psm} --oem 1'
                text = pytesseract.image_to_string(prep_img, lang=lang, config=config)
                text = text.strip()
                if text:
                    # Score: prefer Urdu chars, penalize garbage
                    urdu = sum(1 for c in text if '\u0600' <= c <= '\u06FF')
                    garbage = sum(1 for c in text if c in '[]{}()؟!@#$%^&*;:<>|')
                    words = text.split()
                    unique = len(set(words))
                    total = max(len(words), 1)
                    rep = unique / total
                    score = urdu * rep - garbage * 5
                    if len(text) > 300:
                        score -= (len(text) - 300) * 0.5
                    results.append({
                        'lang': lang,
                        'prep': prep_name,
                        'psm': psm,
                        'score': score,
                        'urdu': urdu,
                        'len': len(text),
                        'text': text[:200]
                    })
            except Exception as e:
                pass  # Skip failed combos

# Sort by score
results.sort(key=lambda x: x['score'], reverse=True)

print(f"\n{'='*60}")
print(f"TOP 20 RESULTS (sorted by score)")
print(f"{'='*60}")

for i, r in enumerate(results[:20]):
    print(f"\n#{i+1} [{r['lang']}|{r['prep']}|psm{r['psm']}] score={r['score']:.1f}, urdu={r['urdu']}, len={r['len']}")
    print(f"  {r['text']}")

# Now test the best langs with more PSM modes
if results:
    best_lang = results[0]['lang']
    best_prep = results[0]['prep']
    print(f"\n\n{'='*60}")
    print(f"TESTING BEST LANG ({best_lang}) + PREP ({best_prep}) WITH ALL PSM MODES")
    print(f"{'='*60}")
    
    for psm in psm_modes:
        try:
            config = f'--psm {psm} --oem 1'
            text = pytesseract.image_to_string(preprocessed[best_prep], lang=best_lang, config=config)
            text = text.strip()
            if text:
                urdu = sum(1 for c in text if '\u0600' <= c <= '\u06FF')
                print(f"\n  PSM {psm}: urdu={urdu}, len={len(text)}")
                print(f"  {text[:200]}")
        except Exception as e:
            print(f"  PSM {psm}: ERROR - {e}")

# Also specifically test with tessdata_best if available
print(f"\n\n{'='*60}")
print(f"TESTING TESSERACT OEM 0 (Legacy) vs OEM 1 (LSTM) vs OEM 3 (both)")
print(f"{'='*60}")

best_img = preprocessed.get('adaptive', preprocessed.get('otsu', gray))
for oem in [0, 1, 3]:
    for lang in ['urd', 'ara', 'urd+ara']:
        try:
            config = f'--psm 6 --oem {oem}'
            text = pytesseract.image_to_string(best_img, lang=lang, config=config)
            text = text.strip()
            if text:
                urdu = sum(1 for c in text if '\u0600' <= c <= '\u06FF')
                print(f"\n  OEM {oem} | {lang}: urdu={urdu}, len={len(text)}")
                print(f"  {text[:200]}")
        except Exception as e:
            print(f"  OEM {oem} | {lang}: ERROR - {str(e)[:80]}")

print("\n\nDONE!")
