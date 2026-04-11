"""Diagnose failing images - dump raw OCR, fragment/struct detection, cleaned/corrected text."""
import cv2, sys, os, gc, re, numpy as np
import io

# Write output to file to avoid encoding issues
outf = open('diag_output.txt', 'w', encoding='utf-8')

def log(msg):
    outf.write(msg + '\n')
    outf.flush()

import pytesseract
from batch_test_tess import detect_location_fragments, detect_structured_location, clean_crime_area_text, CRIME_STRIPS
from urdu_location_dictionary import correct_location_text, _urdu_similarity, _normalize_text, KNOWN_LOCATIONS

IMAGE_DIR = r"D:\FYP\Project\CrimeVision\OCRModel\app\data\raw"

fails = ['FIR_033','FIR_103','FIR_035','FIR_102','FIR_015']

for fn in fails:
    path = f'{IMAGE_DIR}/{fn}.png'
    sz = os.path.getsize(path)
    img = cv2.imread(path, cv2.IMREAD_REDUCED_COLOR_2) if sz > 15_000_000 else cv2.imread(path)
    h, w = img.shape[:2]
    print(f'\n=== {fn} ({w}x{h}) ===')
    log(f'\n=== {fn} ({w}x{h}) ===')
    
    for si, (t, b, l, r) in enumerate(CRIME_STRIPS):
        y1, y2, x1, x2 = int(h*t), int(h*b), int(w*l), int(w*r)
        reg = img[y1:y2, x1:x2]
        gray = cv2.cvtColor(reg, cv2.COLOR_BGR2GRAY)
        sc = 3.0 if gray.shape[1] < 800 else 2.0
        scaled = cv2.resize(gray, None, fx=sc, fy=sc, interpolation=cv2.INTER_CUBIC)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
        enh = clahe.apply(scaled)
        text = pytesseract.image_to_string(enh, lang='urd', config='--oem 1 --psm 6').strip()
        
        if text:
            ur = sum(1 for c in text if '\u0600' <= c <= '\u06FF')
            if ur >= 3:
                frag = detect_location_fragments(text)
                struct = detect_structured_location(text)
                cleaned = clean_crime_area_text(text)
                corrected = correct_location_text(cleaned) if cleaned else ''
                
                raw_short = text.replace('\n', ' | ')[:100]
                log(f'  S{si}: frag=[{frag}] struct=[{struct}]')
                log(f'       clean=[{cleaned[:50]}] corr=[{corrected[:50]}]')
                log(f'       raw: {raw_short}')
        
        del scaled, enh, gray
    del img
    gc.collect()

outf.close()
print("Done! See diag_output.txt")
