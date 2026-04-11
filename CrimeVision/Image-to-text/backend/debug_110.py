"""Quick debug FIR_110 DHA detection."""
import cv2, sys, os, gc, re, numpy as np
outf = open('debug_110.txt', 'w', encoding='utf-8')
import pytesseract
from batch_test_tess import detect_structured_location, CRIME_STRIPS
IMAGE_DIR = r"D:\FYP\Project\CrimeVision\OCRModel\app\data\raw"
path = f'{IMAGE_DIR}/FIR_110.png'
img = cv2.imread(path)
h, w = img.shape[:2]
for si, (t,b,l,r) in enumerate(CRIME_STRIPS):
    y1,y2,x1,x2 = int(h*t),int(h*b),int(w*l),int(w*r)
    reg = img[y1:y2,x1:x2]
    gray = cv2.cvtColor(reg, cv2.COLOR_BGR2GRAY)
    rw = gray.shape[1]
    sc = 4.0 if rw < 800 else (3.0 if rw <= 1500 else 2.0)
    scaled = cv2.resize(gray, None, fx=sc, fy=sc, interpolation=cv2.INTER_CUBIC)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
    enh = clahe.apply(scaled)
    for sname, config in [('PSM6','--oem 1 --psm 6'),('PSM7','--oem 1 --psm 7')]:
        simg = enh
        if sname == 'Otsu':
            _, simg = cv2.threshold(enh, 0, 255, cv2.THRESH_BINARY+cv2.THRESH_OTSU)
        try:
            text = pytesseract.image_to_string(simg, lang='urd', config=config).strip()
        except: continue
        if not text: continue
        ur = sum(1 for c in text if '\u0600'<=c<='\u06FF')
        if ur < 3: continue
        struct = detect_structured_location(text)
        raw_short = text.replace('\n',' | ')[:120]
        outf.write(f'S{si}-{sname}: struct=[{struct}]\n  raw: {raw_short}\n')
        # Check DHA markers manually
        dha_markers = ['ایچ اے','اچ اے','ای اے','کی اے','کے اے']
        for m in dha_markers:
            p = text.find(m)
            if p >= 0:
                prefix = text[max(0,p-5):p]
                outf.write(f'  DHA marker [{m}] at pos {p}, prefix=[{prefix}]\n')
                has_d = bool(re.search(r'[ڈڑ][\s]?ی', prefix))
                outf.write(f'  has_d_context={has_d}\n')
    del scaled, enh, gray; gc.collect()
del img; gc.collect()
outf.close()
print("Done! See debug_110.txt")
