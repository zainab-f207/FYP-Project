
import cv2
import sys
import os
import io

if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.append('f:/Image-to-text/backend')
from fir_specialized_ocr import FIRRegions, MultiEngineOCR, FIRImagePreprocessor

def debug_easyocr():
    image_path = r"D:\FYP\Project\CrimeVision\OCRModel\app\data\raw\FIR_001.png"
    img = cv2.imread(image_path)
    if img is None:
        print("Failed to load image")
        return
        
    regions = FIRRegions()
    preprocessor = FIRImagePreprocessor()
    
    # Use the current regions
    crop = preprocessor.extract_region_percent(img, 
        regions.SECTIONS_TOP, regions.SECTIONS_BOTTOM, 
        regions.SECTIONS_LEFT, regions.SECTIONS_RIGHT)
        
    # Upscale
    upscaled = preprocessor.aggressive_upscale(crop)
    
    ocr = MultiEngineOCR()
    reader = ocr.easyocr_reader
    results = reader.readtext(upscaled)
    
    print(f"EasyOCR found {len(results)} results:")
    for res in results:
        print(f"  Box: {res[0]}, Text: '{res[1]}', Conf: {res[2]:.2f}")

if __name__ == "__main__":
    debug_easyocr()
