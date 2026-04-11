
import cv2
import sys
import os
import io
import re

if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.append('f:/Image-to-text/backend')
from fir_specialized_ocr import MultiEngineOCR

def locate_key_labels():
    image_path = r"D:\FYP\Project\CrimeVision\OCRModel\app\data\raw\FIR_001.png"
    img = cv2.imread(image_path)
    h, w = img.shape[:2]
    ocr = MultiEngineOCR()
    
    # OCR the top 20% of the image to find labels
    top_region = img[0:int(h*0.25), 0:w]
    text, _ = ocr.extract_text_easyocr(top_region)
    print(f"Top Text: {repr(text)}")
    
    # Also check with Tesseract for keywords
    text_tess, _ = ocr.extract_text_tesseract(top_region)
    print(f"Top Tesseract: {repr(text_tess)}")

if __name__ == "__main__":
    locate_key_labels()
