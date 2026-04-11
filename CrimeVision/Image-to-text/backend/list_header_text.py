
import cv2
import sys
import os
import io

if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.append('f:/Image-to-text/backend')
from fir_specialized_ocr import MultiEngineOCR

def list_all_header_text():
    image_path = r"D:\FYP\Project\CrimeVision\OCRModel\app\data\raw\FIR_001.png"
    img = cv2.imread(image_path)
    h, w = img.shape[:2]
    ocr = MultiEngineOCR()
    reader = ocr.easyocr_reader
    
    crop = img[0:int(h*0.30), 0:w]
    results = reader.readtext(crop)
    for res in results:
        print(f"Text: '{res[1]}' | Box: {res[0]}")

if __name__ == "__main__":
    list_all_header_text()
