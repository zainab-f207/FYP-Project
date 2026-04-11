
import cv2
import sys
import os
import io

if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.append('f:/Image-to-text/backend')
from fir_specialized_ocr import MultiEngineOCR

def find_keywords():
    image_path = r"D:\FYP\Project\CrimeVision\OCRModel\app\data\raw\FIR_001.png"
    img = cv2.imread(image_path)
    if img is None: return
    
    ocr = MultiEngineOCR()
    reader = ocr.easyocr_reader
    
    # Check top 30% of the image
    h, w = img.shape[:2]
    crop = img[0:int(h*0.3), 0:w]
    results = reader.readtext(crop)
    
    for res in results:
        text = res[1]
        print(f"Text: {repr(text)} | Box: {res[0]}")
        if 'تھان' in text:
            print(f"  !!! FOUND THANA LABEL !!!")

if __name__ == "__main__":
    find_keywords()
