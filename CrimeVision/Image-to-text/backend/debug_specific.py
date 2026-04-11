"""Debug FIR_033 DHA false positive and FIR_102 شاہدرہ false positive."""
import cv2, sys, os, gc, re, numpy as np
outf = open('debug_specific.txt', 'w', encoding='utf-8')
import pytesseract
from batch_test_tess import (detect_location_fragments, detect_structured_location,
                              clean_crime_area_text, CRIME_STRIPS)
from urdu_location_dictionary import correct_location_text

IMAGE_DIR = r"D:\FYP\Project\CrimeVision\OCRModel\app\data\raw"

for fn in ['FIR_137','FIR_147','FIR_157','FIR_192','FIR_12','FIR_13','FIR_14','FIR_18']:
    path = f'{IMAGE_DIR}/{fn}.png'
    sz = os.path.getsize(path)
    img = cv2.imread(path, cv2.IMREAD_REDUCED_COLOR_2) if sz > 15_000_000 else cv2.imread(path)
    h, w = img.shape[:2]
    outf.write(f'\n{"="*60}\n=== {fn} ({w}x{h}) ===\n{"="*60}\n')
    
    for si, (t, b, l, r) in enumerate(CRIME_STRIPS):
        y1, y2, x1, x2 = int(h*t), int(h*b), int(w*l), int(w*r)
        reg = img[y1:y2, x1:x2]
        rh, rw = reg.shape[:2]
        gray = cv2.cvtColor(reg, cv2.COLOR_BGR2GRAY)
        
        if rw > 1500: sc = 2.0
        elif rw > 800: sc = 3.0
        else: sc = 4.0
        
        scaled = cv2.resize(gray, None, fx=sc, fy=sc, interpolation=cv2.INTER_CUBIC)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
        enh = clahe.apply(scaled)
        
        strategies = [('PSM6', enh), ('PSM7', enh)]
        adaptive = cv2.adaptiveThreshold(enh, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                          cv2.THRESH_BINARY, 31, 10)
        strategies.append(('Adapt', adaptive))
        _, otsu = cv2.threshold(enh, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        strategies.append(('Otsu', otsu))
        
        for sname, simg in strategies:
            config = '--oem 1 --psm 7' if sname == 'PSM7' else '--oem 1 --psm 6'
            try:
                text = pytesseract.image_to_string(simg, lang='urd', config=config).strip()
            except: continue
            if not text: continue
            ur = sum(1 for c in text if '\u0600' <= c <= '\u06FF')
            if ur < 3: continue
            
            frag = detect_location_fragments(text)
            struct = detect_structured_location(text)
            if struct or frag or True:  # Show all for debugging
                raw_short = text.replace('\n', ' | ')[:100]
                outf.write(f'  S{si}-{sname}: frag=[{frag}] struct=[{struct}]\n')
                outf.write(f'       raw: {raw_short}\n')
        
        del scaled, enh, gray
        gc.collect()
    del img; gc.collect()

outf.close()
print("Done! See debug_specific.txt")
