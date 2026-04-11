"""
Section Extraction Pipeline Debugger
=====================================
This script helps diagnose EXACTLY where section extraction fails:
1. Verify region crops contain actual section numbers
2. Check raw OCR output BEFORE any filtering
3. Compare RAW vs PROCESSED image OCR quality

Usage: python debug_section_pipeline.py <path_to_fir_image>
"""

import sys
import os
import io
import cv2
import numpy as np

# Fix Windows encoding
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def debug_sections(image_path: str):
    """Full pipeline debug for section extraction"""
    
    print("=" * 60)
    print("SECTION EXTRACTION PIPELINE DEBUGGER")
    print("=" * 60)
    
    # Load image
    if not os.path.exists(image_path):
        print(f"ERROR: Image not found: {image_path}")
        return
    
    img = cv2.imread(image_path)
    if img is None:
        print(f"ERROR: Failed to load image: {image_path}")
        return
    
    h, w = img.shape[:2]
    print(f"\n[1] Image loaded: {w}x{h} pixels")
    
    # ========================================
    # STEP 2: Extract section region (FIXED coordinates)
    # ========================================
    print("\n[2] EXTRACTING SECTION REGION")
    print("-" * 40)
    
    # These are the CURRENT region coordinates from fir_specialized_ocr.py
    # Updated to match FIRRegions class
    SECTIONS_TOP = 0.23
    SECTIONS_BOTTOM = 0.50
    SECTIONS_LEFT = 0.42
    SECTIONS_RIGHT = 0.74
    
    y1 = int(h * SECTIONS_TOP)
    y2 = int(h * SECTIONS_BOTTOM)
    x1 = int(w * SECTIONS_LEFT)
    x2 = int(w * SECTIONS_RIGHT)
    
    section_region = img[y1:y2, x1:x2]
    print(f"Region: TOP={SECTIONS_TOP}, BOTTOM={SECTIONS_BOTTOM}, LEFT={SECTIONS_LEFT}, RIGHT={SECTIONS_RIGHT}")
    print(f"Pixels: Y[{y1}:{y2}] X[{x1}:{x2}] = {x2-x1}x{y2-y1} px")
    
    # Save for visual inspection
    cv2.imwrite("debug_section_region_raw.png", section_region)
    print(f"SAVED: debug_section_region_raw.png (INSPECT THIS FILE!)")
    
    # ========================================
    # STEP 3: Run OCR on RAW region (NO preprocessing)
    # ========================================
    print("\n[3] OCR ON RAW IMAGE (no preprocessing)")
    print("-" * 40)
    
    try:
        import easyocr
        reader = easyocr.Reader(['en', 'ur'], gpu=False, verbose=False)
        results = reader.readtext(section_region)
        
        print("EasyOCR Raw Results:")
        raw_text = ""
        for bbox, text, conf in results:
            print(f"  '{text}' (confidence: {conf:.2f})")
            raw_text += text + " "
        print(f"\nCOMBINED: '{raw_text.strip()}'")
    except Exception as e:
        print(f"EasyOCR failed: {e}")
    
    # ========================================
    # STEP 4: Extract ALL numbers from raw text (NO FILTERING)
    # ========================================
    print("\n[4] PURE NUMBER EXTRACTION (no filtering)")
    print("-" * 40)
    
    import re
    
    # Find ALL digit sequences (2-4 digits)
    all_numbers = re.findall(r'\d{2,4}', raw_text)
    print(f"All numbers found: {all_numbers}")
    
    # Filter to likely sections (3 digits, 100-999)
    likely_sections = [n for n in all_numbers if len(n) == 3 and 100 <= int(n) <= 999]
    print(f"3-digit numbers (100-999): {likely_sections}")
    
    # ========================================
    # STEP 5: Compare with OVER-PROCESSED image
    # ========================================
    print("\n[5] OCR ON OVER-PROCESSED IMAGE (current pipeline)")
    print("-" * 40)
    
    # Apply the CURRENT preprocessing (this is what causes problems)
    gray = cv2.cvtColor(section_region, cv2.COLOR_BGR2GRAY)
    denoised = cv2.bilateralFilter(gray, 9, 75, 75)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(denoised)
    gaussian = cv2.GaussianBlur(enhanced, (0, 0), 3.0)
    sharpened = cv2.addWeighted(enhanced, 1.8, gaussian, -0.8, 0)
    binary = cv2.adaptiveThreshold(sharpened, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 21, 10)
    
    cv2.imwrite("debug_section_region_processed.png", binary)
    print(f"SAVED: debug_section_region_processed.png (compare with raw!)")
    
    # OCR on processed
    try:
        results_processed = reader.readtext(binary)
        processed_text = ""
        for bbox, text, conf in results_processed:
            print(f"  '{text}' (confidence: {conf:.2f})")
            processed_text += text + " "
        print(f"\nCOMBINED: '{processed_text.strip()}'")
        
        processed_numbers = re.findall(r'\d{2,4}', processed_text)
        print(f"Numbers from processed: {processed_numbers}")
    except Exception as e:
        print(f"OCR on processed failed: {e}")
    
    # ========================================
    # STEP 6: RECOMMENDATION
    # ========================================
    print("\n" + "=" * 60)
    print("DIAGNOSIS")
    print("=" * 60)
    print("""
INSPECT THE SAVED FILES:
1. debug_section_region_raw.png - Does this contain the section numbers?
   - If NO: Region coordinates are WRONG - adjust SECTIONS_TOP/BOTTOM/LEFT/RIGHT
   - If YES: Proceed to step 2
   
2. Compare raw OCR vs processed OCR results above
   - If RAW has more correct numbers: OVER-PROCESSING is the problem
   - If BOTH are bad: Region targeting is wrong

3. Check if numbers were found but filtered out
   - If '148', '302' etc appear in 'All numbers found' but not in output:
     The FILTERING LOGIC in _parse_sections_from_text() is rejecting them
""")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        # Default to a known FIR image path
        default_paths = [
            r"D:\FYP\Project\CrimeVision\OCRModel\app\data\raw\FIR_001.png",
            "debug_05_sections_raw.png",
            "../test_fir.png"
        ]
        for p in default_paths:
            if os.path.exists(p):
                debug_sections(p)
                break
        else:
            print("Usage: python debug_section_pipeline.py <path_to_fir_image>")
    else:
        debug_sections(sys.argv[1])

