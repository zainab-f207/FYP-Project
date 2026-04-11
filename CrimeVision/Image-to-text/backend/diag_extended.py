"""Diagnose extended failures - dump raw OCR for each strip/strategy."""
import cv2, sys, os, gc, re, numpy as np
outf = open('diag_extended.txt', 'w', encoding='utf-8')
import pytesseract
from batch_test_tess import CRIME_STRIPS

IMAGE_DIR = r"D:\FYP\Project\CrimeVision\OCRModel\app\data\raw"

# All 28 failures
targets = [
    'FIR_113','FIR_118','FIR_129','FIR_136','FIR_137','FIR_147',
    'FIR_153','FIR_155','FIR_12','FIR_13','FIR_14','FIR_16','FIR_18',
    'FIR_126','FIR_130','FIR_142','FIR_151','FIR_156','FIR_157',
    'FIR_165','FIR_169','FIR_170','FIR_173','FIR_174',
    'FIR_183','FIR_188','FIR_192','FIR_198'
]

for fn in targets:
    path = f'{IMAGE_DIR}/{fn}.png'
    if not os.path.exists(path):
        continue
    sz = os.path.getsize(path)
    img = cv2.imread(path, cv2.IMREAD_REDUCED_COLOR_2) if sz > 15_000_000 else cv2.imread(path)
    h, w = img.shape[:2]
    outf.write(f'\n{"="*60}\n=== {fn} ({w}x{h}) ===\n{"="*60}\n')
    
    # Only dump S0 and S1 raw text (most relevant strips)
    for si in [0, 1]:
        t, b, l, r = CRIME_STRIPS[si]
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
        
        # PSM6 only (best strategy for most images)
        config = '--oem 1 --psm 6'
        try:
            text = pytesseract.image_to_string(enh, lang='urd', config=config).strip()
        except: text = "<error>"
        
        raw_short = text.replace('\n', ' | ')[:120]
        outf.write(f'  S{si}-PSM6: {raw_short}\n')
        
        del scaled, enh, gray
        gc.collect()
    
    del img; gc.collect()

outf.close()
print("Done! See diag_extended.txt")
