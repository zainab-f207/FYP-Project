"""Detailed scoring diagnostic - shows ALL candidates and scores for failing images."""
import cv2, sys, os, gc, re, numpy as np
import io

outf = open('diag_scores.txt', 'w', encoding='utf-8')

def log(msg):
    outf.write(msg + '\n')
    outf.flush()

import pytesseract
from batch_test_tess import (detect_location_fragments, detect_structured_location,
                              clean_crime_area_text, CRIME_STRIPS)
from urdu_location_dictionary import correct_location_text, _urdu_similarity, _normalize_text, KNOWN_LOCATIONS

IMAGE_DIR = r"D:\FYP\Project\CrimeVision\OCRModel\app\data\raw"

# Only check specific images where correct fragment exists but wrong result
debug_images = ['FIR_005', 'FIR_029', 'FIR_033']

for fn in debug_images:
    path = f'{IMAGE_DIR}/{fn}.png'
    sz = os.path.getsize(path)
    img = cv2.imread(path, cv2.IMREAD_REDUCED_COLOR_2) if sz > 15_000_000 else cv2.imread(path)
    h, w = img.shape[:2]
    log(f'\n{"="*60}')
    log(f'=== {fn} ({w}x{h}) ===')
    log(f'{"="*60}')
    
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
        
        strategies = [
            ('PSM6', enh, '--oem 1 --psm 6'),
            ('PSM7', enh, '--oem 1 --psm 7'),
        ]
        # Add adaptive
        adaptive = cv2.adaptiveThreshold(enh, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                          cv2.THRESH_BINARY, 31, 10)
        strategies.append(('Adapt', adaptive, '--oem 1 --psm 6'))
        
        # Add otsu
        _, otsu = cv2.threshold(enh, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        strategies.append(('Otsu', otsu, '--oem 1 --psm 6'))
        
        for sname, simg, config in strategies:
            try:
                text = pytesseract.image_to_string(simg, lang='urd', config=config).strip()
            except:
                continue
            if not text:
                continue
            ur = sum(1 for c in text if '\u0600' <= c <= '\u06FF')
            if ur < 3:
                continue
            
            engine = f'S{si}-{sname}'
            
            struct = detect_structured_location(text)
            if struct:
                s = 0.90 + (0.05 if si == 0 else 0)
                all_candidates.append((struct, s, engine + '-Struct'))
                log(f'  [{engine}] STRUCT: [{struct}] score={s:.3f}')
            
            frag = detect_location_fragments(text)
            if frag:
                s = 0.85 + (0.05 if si == 0 else 0)
                all_candidates.append((frag, s, engine + '-Frag'))
                log(f'  [{engine}] FRAG: [{frag}] score={s:.3f}')
            
            cleaned = clean_crime_area_text(text)
            if not cleaned or len(cleaned) < 2:
                continue
            
            if not frag:
                frag2 = detect_location_fragments(cleaned)
                if frag2:
                    s = 0.83 + (0.05 if si == 0 else 0)
                    all_candidates.append((frag2, s, engine + '-FragC'))
                    log(f'  [{engine}] FRAGC: [{frag2}] score={s:.3f}')
            
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
                log(f'  [{engine}] FUZZY: [{corrected}] score={adj:.3f} (ms={ms:.3f} oc={oc:.3f})')
        
        del scaled, enh, gray
        gc.collect()
    
    all_candidates.sort(key=lambda x: x[1], reverse=True)
    log(f'\n  TOP CANDIDATES:')
    for c, s, e in all_candidates[:15]:
        log(f'    score={s:.3f} [{e}] [{c}]')
    
    del img
    gc.collect()

outf.close()
print("Done! See diag_scores.txt")
