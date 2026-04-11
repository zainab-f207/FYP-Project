"""Word-level confidence analysis + multi-config consensus for crime area OCR"""
import cv2
import numpy as np
import pytesseract
import os

print("=" * 60)
print("WORD-LEVEL CONFIDENCE + CONSENSUS APPROACH")
print("=" * 60)

TESSDATA = r"E:\programming softwares\Tesseract-OCR\tessdata"
img = cv2.imread("crime_area_best.png")
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
h, w = gray.shape
print(f"Image: {w}x{h}")

# Best preprocessing variants
preprocessed = {}
preprocessed['raw'] = gray

_, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
preprocessed['otsu'] = otsu

denoised = cv2.fastNlMeansDenoising(gray, None, h=10, templateWindowSize=7, searchWindowSize=21)
_, dn_otsu = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
preprocessed['dn_otsu'] = dn_otsu

kernel_sharp = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
sharpened = cv2.filter2D(denoised, -1, kernel_sharp)
preprocessed['sharp'] = sharpened

clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
enhanced = clahe.apply(gray)
preprocessed['clahe'] = enhanced

# 2x upscale + denoise + otsu (one of the best)
scaled2x = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
dn2x = cv2.fastNlMeansDenoising(scaled2x, None, h=10)
_, otsu2x = cv2.threshold(dn2x, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
preprocessed['2x_dn_otsu'] = otsu2x

print("\n" + "=" * 60)
print("PART 1: WORD-LEVEL CONFIDENCE ANALYSIS")
print("=" * 60)

# Get word-level data for best configs
best_configs = [
    ('urd', 'otsu', '--psm 6 --oem 1'),
    ('urd', '2x_dn_otsu', '--psm 6 --oem 1'),
    ('urd', 'sharp', '--psm 6 --oem 1'),
    ('urd_best', 'otsu', f'--tessdata-dir "{TESSDATA}" --psm 6 --oem 1'),
    ('urd_best', 'sharp', f'--tessdata-dir "{TESSDATA}" --psm 6 --oem 1'),
    ('urd', 'raw', '--psm 6 --oem 1'),
    ('urd', 'clahe', '--psm 6 --oem 1'),
    ('urd', 'dn_otsu', '--psm 6 --oem 1'),
]

for lang, prep_name, config in best_configs:
    prep_img = preprocessed[prep_name]
    try:
        data = pytesseract.image_to_data(prep_img, lang=lang, config=config, output_type=pytesseract.Output.DICT)
        words = []
        for i in range(len(data['text'])):
            text = data['text'][i].strip()
            conf = int(data['conf'][i])
            if text and conf > 0:
                urdu_chars = sum(1 for c in text if '\u0600' <= c <= '\u06FF')
                if urdu_chars > 0 or text.replace('.', '').replace(',', '').isdigit():
                    words.append((text, conf))
        
        if words:
            # Filter by confidence
            high_conf = [(t, c) for t, c in words if c >= 50]
            med_conf = [(t, c) for t, c in words if c >= 30]
            
            print(f"\n[{lang}|{prep_name}]")
            print(f"  ALL words ({len(words)}): {' '.join(f'{t}({c})' for t, c in words[:30])}")
            print(f"  HIGH conf(>=50) ({len(high_conf)}): {' '.join(f'{t}' for t, _ in high_conf)}")
            print(f"  MED conf(>=30) ({len(med_conf)}): {' '.join(f'{t}' for t, _ in med_conf)}")
    except Exception as e:
        print(f"  [{lang}|{prep_name}]: ERROR - {str(e)[:80]}")

# Part 2: Consensus from multiple OCR runs
print("\n\n" + "=" * 60)
print("PART 2: MULTI-CONFIG CONSENSUS")
print("=" * 60)

all_texts = []
configs_to_run = [
    ('urd', 'otsu', '--psm 6 --oem 1'),
    ('urd', '2x_dn_otsu', '--psm 6 --oem 1'),
    ('urd', 'sharp', '--psm 6 --oem 1'),
    ('urd_best', 'otsu', f'--tessdata-dir "{TESSDATA}" --psm 6 --oem 1'),
    ('urd_best', 'sharp', f'--tessdata-dir "{TESSDATA}" --psm 6 --oem 1'),
    ('urd', 'raw', '--psm 6 --oem 1'),
    ('urd', 'dn_otsu', '--psm 6 --oem 1'),
    ('urd', 'otsu', '--psm 4 --oem 1'),
    ('urd', 'otsu', '--psm 7 --oem 1'),
    ('urd', 'otsu', '--psm 12 --oem 1'),
    ('fas_best', 'raw', f'--tessdata-dir "{TESSDATA}" --psm 6 --oem 1'),
    ('fas_best', 'otsu', f'--tessdata-dir "{TESSDATA}" --psm 6 --oem 1'),
    ('ara_best', 'clahe', f'--tessdata-dir "{TESSDATA}" --psm 6 --oem 1'),
]

for lang, prep_name, config in configs_to_run:
    prep_img = preprocessed[prep_name]
    try:
        text = pytesseract.image_to_string(prep_img, lang=lang, config=config).strip()
        if text:
            # Clean: remove garbage chars and repeated patterns
            import re
            text = re.sub(r'[{}()\[\]@#$%^&*;:<>|\\/_=+!؟٭٪]', '', text)
            text = re.sub(r'[چ]{3,}|[و]{4,}|[ل]{4,}|[ج]{4,}', '', text)  # repeated chars
            text = re.sub(r'[\.۔]{4,}', '...', text)
            text = re.sub(r'[-ـ]{3,}', '', text)
            text = ' '.join(text.split()).strip()
            if len(text) > 5:
                all_texts.append({'lang': lang, 'prep': prep_name, 'text': text})
    except:
        pass

# Find common substrings across results
print(f"\nCollected {len(all_texts)} OCR results")
print("\nALL cleaned texts:")
for i, t in enumerate(all_texts):
    print(f"  {i+1}. [{t['lang']}|{t['prep']}]: {t['text'][:150]}")

# Find most common words
from collections import Counter
word_counts = Counter()
for t in all_texts:
    words = t['text'].split()
    for word in words:
        if len(word) >= 2:
            urdu = sum(1 for c in word if '\u0600' <= c <= '\u06FF')
            if urdu >= 2:
                word_counts[word] += 1

print(f"\nMost common Urdu words across all OCR runs:")
for word, count in word_counts.most_common(30):
    print(f"  '{word}': {count} times")

# Part 3: Try with explicit DPI setting
print("\n\n" + "=" * 60)
print("PART 3: DPI OVERRIDE TESTS (150, 200, 300, 400)")
print("=" * 60)

for dpi in [150, 200, 300, 400]:
    config = f'--psm 6 --oem 1 --dpi {dpi}'
    text = pytesseract.image_to_string(otsu, lang='urd', config=config).strip()
    if text:
        text_clean = ' '.join(text.split())[:150]
        urdu = sum(1 for c in text_clean if '\u0600' <= c <= '\u06FF')
        print(f"\n  DPI {dpi}: urdu={urdu}, len={len(text_clean)}")
        print(f"  {text_clean}")

print("\n\nDONE!")
