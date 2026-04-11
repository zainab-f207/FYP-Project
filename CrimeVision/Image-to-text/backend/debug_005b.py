"""Call actual extract_crime_area_tesseract for FIR_005 and trace result."""
import cv2, sys, os, gc
outf = open('debug_005b.txt', 'w', encoding='utf-8')

from batch_test_tess import extract_crime_area_tesseract

IMAGE_DIR = r"D:\FYP\Project\CrimeVision\OCRModel\app\data\raw"
path = os.path.join(IMAGE_DIR, 'FIR_005.png')
sz = os.path.getsize(path)
img = cv2.imread(path, cv2.IMREAD_REDUCED_COLOR_2) if sz > 15_000_000 else cv2.imread(path)
h, w = img.shape[:2]
outf.write(f'Image: {w}x{h}\n')

if max(h, w) > 5000:
    s = 3000.0 / max(h, w)
    img = cv2.resize(img, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
    h, w = img.shape[:2]
    outf.write(f'Resized: {w}x{h}\n')

result = extract_crime_area_tesseract(img)
outf.write(f'Result: [{result}]\n')
del img; gc.collect()
outf.close()
print(f"Result: {result}")
print("Done! See debug_005b.txt")
