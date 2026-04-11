"""Debug FIR_005 specifically - trace what extract_crime_area_tesseract returns."""
import cv2, sys, os, gc, re, numpy as np

outf = open('debug_005.txt', 'w', encoding='utf-8')

import pytesseract
from batch_test_tess import (detect_location_fragments, detect_structured_location,
                              clean_crime_area_text, CRIME_STRIPS)
from urdu_location_dictionary import correct_location_text, _urdu_similarity, _normalize_text, KNOWN_LOCATIONS

IMAGE_DIR = r"D:\FYP\Project\CrimeVision\OCRModel\app\data\raw"

path = os.path.join(IMAGE_DIR, 'FIR_005.png')
sz = os.path.getsize(path)
img = cv2.imread(path, cv2.IMREAD_REDUCED_COLOR_2) if sz > 15_000_000 else cv2.imread(path)
h, w = img.shape[:2]
outf.write(f'Image: {w}x{h}\n\n')

all_candidates = []

for si, (t, b, l, r) in enumerate(CRIME_STRIPS):
    y1, y2, x1, x2 = int(h*t), int(h*b), int(w*l), int(w*r)
    reg = img[y1:y2, x1:x2]
    gray = cv2.cvtColor(reg, cv2.COLOR_BGR2GRAY)
    rw = gray.shape[1]
    sc = 3.0 if rw < 800 else 2.0
    scaled = cv2.resize(gray, None, fx=sc, fy=sc, interpolation=cv2.INTER_CUBIC)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
    enh = clahe.apply(scaled)
    
    strip_texts = []
    
    # PSM6
    try:
        text = pytesseract.image_to_string(enh, lang='urd', config='--oem 1 --psm 6').strip()
        ur = sum(1 for c in text if '\u0600' <= c <= '\u06FF') if text else 0
        if ur >= 3:
            strip_texts.append((text, f'S{si}-PSM6'))
    except: pass
    
    # PSM7
    try:
        text = pytesseract.image_to_string(enh, lang='urd', config='--oem 1 --psm 7').strip()
        ur = sum(1 for c in text if '\u0600' <= c <= '\u06FF') if text else 0
        if ur >= 3:
            strip_texts.append((text, f'S{si}-PSM7'))
    except: pass
    
    # Adaptive
    try:
        adaptive = cv2.adaptiveThreshold(enh, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                          cv2.THRESH_BINARY, 31, 10)
        text = pytesseract.image_to_string(adaptive, lang='urd', config='--oem 1 --psm 6').strip()
        ur = sum(1 for c in text if '\u0600' <= c <= '\u06FF') if text else 0
        if ur >= 3:
            strip_texts.append((text, f'S{si}-Adapt'))
        del adaptive
    except: pass
    
    # Otsu
    try:
        _, otsu = cv2.threshold(enh, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        text = pytesseract.image_to_string(otsu, lang='urd', config='--oem 1 --psm 6').strip()
        ur = sum(1 for c in text if '\u0600' <= c <= '\u06FF') if text else 0
        if ur >= 3:
            strip_texts.append((text, f'S{si}-Otsu'))
        del otsu
    except: pass
    
    del scaled, enh
    
    for raw_text, engine in strip_texts:
        struct = detect_structured_location(raw_text)
        if struct:
            s = 0.90 + (0.05 if si == 0 else 0)
            all_candidates.append((struct, s, engine + '-Struct'))
            outf.write(f'STRUCT [{engine}]: [{struct}] score={s:.3f}\n')
        
        frag = detect_location_fragments(raw_text)
        if frag:
            s = 0.85 + (0.05 if si == 0 else 0)
            all_candidates.append((frag, s, engine + '-Frag'))
            outf.write(f'FRAG [{engine}]: [{frag}] score={s:.3f}\n')
            # Also show what the pre-filtered text looks like
            lines = raw_text.strip().split('\n')
            for li, line in enumerate(lines):
                outf.write(f'  raw_line_{li}: {line[:80]}\n')
        
        cleaned = clean_crime_area_text(raw_text)
        if not cleaned or len(cleaned) < 2:
            continue
        
        if not frag:
            frag2 = detect_location_fragments(cleaned)
            if frag2:
                s = 0.83 + (0.05 if si == 0 else 0)
                all_candidates.append((frag2, s, engine + '-FragC'))
                outf.write(f'FRAGC [{engine}]: [{frag2}] score={s:.3f}\n')
        
        corrected = correct_location_text(cleaned)
        if corrected and len(corrected) >= 2:
            norm = _normalize_text(corrected)
            ms = max((_urdu_similarity(norm, _normalize_text(loc)) for loc in KNOWN_LOCATIONS), default=0)
            oc = _urdu_similarity(_normalize_text(cleaned), _normalize_text(corrected))
            adj = max(ms * 0.7 + oc * 0.3, ms * oc)
            if si == 0:
                adj += 0.05
            if len(corrected.split()) == 1 and len(corrected) <= 5:
                adj *= 0.6
            all_candidates.append((corrected, adj, engine))
            outf.write(f'FUZZY [{engine}]: [{corrected}] score={adj:.3f} (clean=[{cleaned[:40]}])\n')
    
    del gray
    gc.collect()

all_candidates.sort(key=lambda x: x[1], reverse=True)
outf.write(f'\nTOP 15 CANDIDATES:\n')
for c, s, e in all_candidates[:15]:
    outf.write(f'  score={s:.3f} [{e}] [{c}]\n')

best = all_candidates[0] if all_candidates else ('', 0, '')
outf.write(f'\nFINAL RESULT: [{best[0]}] score={best[1]:.3f}\n')

del img
gc.collect()
outf.close()
print("Done! See debug_005.txt")
