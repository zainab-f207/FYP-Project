
import sys
import os
import io

# utf-8 for windows
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.append('f:/Image-to-text/backend')
from fir_specialized_ocr import FIRExtractor

def final_test():
    image_path = r"D:\FYP\Project\CrimeVision\OCRModel\app\data\raw\FIR_001.png"
    extractor = FIRExtractor(debug_mode=False)
    
    with open(image_path, 'rb') as f:
        img_bytes = f.read()
        
    result = extractor.extract_fir_data(img_bytes)
    
    print("--- FINAL RESULT ---")
    print(f"Date: {result['crime_date']}")
    print(f"Thana: {result['crime_area']}")
    print(f"Sections: {result['sections']}")
    print("--------------------")

if __name__ == "__main__":
    final_test()
