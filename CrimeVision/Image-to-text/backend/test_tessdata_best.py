"""Test tessdata_best quality vs standard tessdata on crime area"""
import cv2
import numpy as np
import pytesseract
import os

print("=" * 60)
print("TESSDATA_BEST vs STANDARD COMPARISON")
print("=" * 60)

img = cv2.imread("crime_area_best.png")
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
h, w = gray.shape
print(f"Image: {w}x{h}")

TESSDATA = r"E:\programming softwares\Tesseract-OCR\tessdata"

# Preprocessing variants
preprocessed = {}
preprocessed['raw'] = gray

_, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
preprocessed['otsu'] = otsu

adaptive = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 51, 15)
preprocessed['adaptive'] = adaptive

denoised = cv2.fastNlMeansDenoising(gray, None, h=10, templateWindowSize=7, searchWindowSize=21)
preprocessed['denoised'] = denoised

_, dn_otsu = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
preprocessed['denoised_otsu'] = dn_otsu

# CLAHE
clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
enhanced = clahe.apply(gray)
preprocessed['clahe'] = enhanced

# Sharpen
kernel_sharp = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
sharpened = cv2.filter2D(denoised, -1, kernel_sharp)
preprocessed['sharp'] = sharpened

# 2x upscale + denoise + otsu
scaled2x = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
dn2x = cv2.fastNlMeansDenoising(scaled2x, None, h=10)
_, otsu2x = cv2.threshold(dn2x, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
preprocessed['2x_dn_otsu'] = otsu2x

# Language configs to test
lang_configs = [
    ('urd_best', f'--tessdata-dir "{TESSDATA}" --psm 6 --oem 1'),
    ('ara_best', f'--tessdata-dir "{TESSDATA}" --psm 6 --oem 1'),
    ('urd', f'--psm 6 --oem 1'),  # standard for comparison
    ('ara', f'--psm 6 --oem 1'),  # standard for comparison
    ('fas_best', f'--tessdata-dir "{TESSDATA}" --psm 6 --oem 1'),
]

results = []

for lang, config in lang_configs:
    for prep_name, prep_img in preprocessed.items():
        try:
            text = pytesseract.image_to_string(prep_img, lang=lang, config=config)
            text = text.strip()
            if text:
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
                    'score': score,
                    'urdu': urdu,
                    'len': len(text),
                    'text': text[:200]
                })
        except Exception as e:
            print(f"  ERROR [{lang}|{prep_name}]: {str(e)[:60]}")

results.sort(key=lambda x: x['score'], reverse=True)

print(f"\n{'='*60}")
print(f"TOP 25 RESULTS")
print(f"{'='*60}")

for i, r in enumerate(results[:25]):
    is_best = '_best' in r['lang']
    marker = "*** BEST ***" if is_best else "  standard  "
    print(f"\n#{i+1} [{r['lang']}|{r['prep']}] {marker} score={r['score']:.1f}, urdu={r['urdu']}, len={r['len']}")
    print(f"  {r['text']}")

# Show best result for each lang type
print(f"\n\n{'='*60}")
print(f"BEST PER LANGUAGE")
print(f"{'='*60}")
seen_langs = set()
for r in results:
    if r['lang'] not in seen_langs:
        seen_langs.add(r['lang'])
        is_best = '_best' in r['lang']
        marker = "BEST_QUALITY" if is_best else "STANDARD"
        print(f"\n[{r['lang']}] ({marker}) score={r['score']:.1f}, prep={r['prep']}")
        print(f"  {r['text']}")

# Now test PSM modes with top-scoring lang+prep
if results:
    top = results[0]
    print(f"\n\n{'='*60}")
    print(f"BEST COMBO ({top['lang']}|{top['prep']}) - ALL PSM MODES")
    print(f"{'='*60}")
    for psm in [3, 4, 6, 7, 11, 12, 13]:
        try:
            if '_best' in top['lang']:
                config = f'--tessdata-dir "{TESSDATA}" --psm {psm} --oem 1'
            else:
                config = f'--psm {psm} --oem 1'
            text = pytesseract.image_to_string(preprocessed[top['prep']], lang=top['lang'], config=config)
            text = text.strip()
            if text:
                urdu = sum(1 for c in text if '\u0600' <= c <= '\u06FF')
                print(f"\n  PSM {psm}: urdu={urdu}, len={len(text)}")
                print(f"  {text[:200]}")
        except Exception as e:
            print(f"  PSM {psm}: ERROR")

print("\n\nDONE!")
