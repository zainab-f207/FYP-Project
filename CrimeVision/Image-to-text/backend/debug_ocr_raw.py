
import cv2
import numpy as np
import logging
import sys
import os

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# Add current directory to path
sys.path.append(os.getcwd())
sys.path.append('backend')

from fir_specialized_ocr import FIRImagePreprocessor, MultiEngineOCR, FIRExtractor

def debug_extraction():
    # Open debug file
    with open("debug_results.txt", "w", encoding="utf-8") as f:
        f.write("=== START DEBUG ===\n")
        
        ocr = MultiEngineOCR()
        preprocessor = FIRImagePreprocessor()
        extractor = FIRExtractor(debug_mode=True)

        # 1. Debug Thana
        header_path = "debug_01_header_raw.png"
        if not os.path.exists(header_path):
            header_path = "backend/debug_01_header_raw.png"
            
        if os.path.exists(header_path):
            f.write(f"\n=== Debugging Thana ({header_path}) ===\n")
            header_img = cv2.imread(header_path)
            if header_img is not None:
                text_easy, conf_easy = ocr.extract_text_easyocr(header_img)
                f.write(f"EasyOCR Raw: {repr(text_easy)} (conf: {conf_easy})\n")
                
                text_tess, conf_tess = ocr.extract_text_tesseract(header_img)
                f.write(f"Tesseract Raw: {repr(text_tess)} (conf: {conf_tess})\n")
                
                thana = extractor._parse_thana_from_text(text_easy)
                f.write(f"Parsed Thana: {thana}\n")
        
        # 2. Debug Sections
        sections_path = "debug_05_sections_raw.png"
        if not os.path.exists(sections_path):
            sections_path = "backend/debug_05_sections_raw.png"
            
        if os.path.exists(sections_path):
            f.write(f"\n=== Debugging Sections ({sections_path}) ===\n")
            sections_img = cv2.imread(sections_path)
            if sections_img is not None:
                # Current process: Remove lines -> Upscale -> OCR
                no_lines = preprocessor.remove_table_lines_advanced(sections_img)
                upscaled = preprocessor.aggressive_upscale(no_lines)
                
                f.write("--- EasyOCR on cleaned/upscaled ---\n")
                text_easy, conf_easy = ocr.extract_text_easyocr(upscaled)
                f.write(f"Text: {repr(text_easy)} (conf: {conf_easy})\n")
                
                f.write("--- Tesseract on cleaned/upscaled ---\n")
                text_tess, conf_tess = ocr.extract_text_tesseract(upscaled)
                f.write(f"Text: {repr(text_tess)} (conf: {conf_tess})\n")
                
                sections_easy = extractor._parse_sections_from_text(text_easy)
                sections_tess = extractor._parse_sections_from_text(text_tess)
                f.write(f"Parsed (Easy): {sections_easy}\n")
                f.write(f"Parsed (Tess): {sections_tess}\n")
        
        f.write("\n=== END DEBUG ===\n")

if __name__ == "__main__":
    debug_extraction()
