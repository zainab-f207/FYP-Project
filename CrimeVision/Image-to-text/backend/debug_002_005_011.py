"""Quick debug for FIR_002, FIR_005, FIR_011"""
import sys, os, cv2
sys.path.insert(0, os.path.dirname(__file__))
from fir_specialized_ocr import CRIME_STRIPS, detect_location_fragments
import pytesseract

IMAGE_DIR = r"F:\FYP\Project\CrimeVision\OCRModel\app\data\raw"

for fn, expected in [("FIR_002.png", "انارکلی"), ("FIR_005.png", "دہلی گیٹ"), ("FIR_011.png", "مین بلیوارڈ")]:
    img = cv2.imread(os.path.join(IMAGE_DIR, fn))
    h, w = img.shape[:2]
    if max(h,w) > 5000:
        s = 3000/max(h,w); img = cv2.resize(img,(int(w*s),int(h*s)),interpolation=cv2.INTER_AREA)
    h, w = img.shape[:2]
    print(f"\n{'='*70}\n{fn} (expected: {expected})\n{'='*70}")
    for si, (y1f,y2f,x1f,x2f) in enumerate(CRIME_STRIPS[:2]):
        y1,y2=int(h*y1f),int(h*y2f); x1,x2=int(w*x1f),int(w*x2f)
        if y2<=y1 or x2<=x1: continue
        crop=img[y1:y2,x1:x2]; rh,rw=crop.shape[:2]
        sf=2.0 if rw>1500 else(3.0 if rw>800 else 4.0)
        resized=cv2.resize(crop,None,fx=sf,fy=sf,interpolation=cv2.INTER_CUBIC)
        gray=cv2.cvtColor(resized,cv2.COLOR_BGR2GRAY)
        clahe=cv2.createCLAHE(clipLimit=2.0,tileGridSize=(8,8))
        cl=clahe.apply(gray)
        for proc,config,label in [(cl,'--psm 6 --oem 3 -l urd',f'S{si}-PSM6'),(cl,'--psm 7 --oem 3 -l urd',f'S{si}-PSM7')]:
            raw=pytesseract.image_to_string(proc,config=config).strip()
            if raw and len(raw)>5:
                frags=detect_location_fragments(raw,return_all=True)
                print(f"  {label}: {raw[:150].replace(chr(10),' ')}")
                if frags: print(f"    Frags: {frags}")
