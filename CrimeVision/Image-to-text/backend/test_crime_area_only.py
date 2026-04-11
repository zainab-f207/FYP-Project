"""
Quick test script for crime area extraction only
Tests memory fallback and known location pre-check fixes
"""
import cv2
import sys
import logging

# Fix Unicode encoding for Windows console
import sys
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from fir_specialized_ocr import FIRExtractor

def test_crime_area(image_path: str):
    """Test only crime area extraction"""
    
    logger.info("=" * 80)
    logger.info(f"TESTING CRIME AREA EXTRACTION: {image_path}")
    logger.info("=" * 80)
    
    # Initialize extractor FIRST (loads EasyOCR when more memory available)
    import gc
    logger.info("Initializing FIR extractor...")
    extractor = FIRExtractor(debug_mode=True)
    gc.collect()
    
    # THEN load image
    img = cv2.imread(image_path)
    if img is None:
        logger.error(f"Failed to load image: {image_path}")
        return
    
    h, w = img.shape[:2]
    logger.info(f"Image loaded: {w}x{h}px ({img.nbytes / (1024*1024):.1f} MB)")
    
    # Note: images are processed at full resolution for best OCR quality
    # extract_crime_area handles memory internally (frees 4x upscale before EasyOCR)
    
    # Extract crime area only
    logger.info("\nExtracting crime area...")
    try:
        crime_area = extractor.extract_crime_area(img)
        
        logger.info("\n" + "=" * 80)
        logger.info("RESULT")
        logger.info("=" * 80)
        if crime_area:
            logger.info(f"✓ Crime Area: {crime_area}")
            logger.info(f"  Length: {len(crime_area)} chars")
            
            # Count Urdu characters
            urdu_chars = sum(1 for c in crime_area if '\u0600' <= c <= '\u06FF')
            logger.info(f"  Urdu chars: {urdu_chars}")
            
            print(f"\nSUCCESS!")
            print(f"Crime Area: {crime_area}")
        else:
            logger.warning("No crime area extracted - OCR quality too poor")
            print(f"\nWARNING: No crime area extracted (OCR quality too poor)")
            
    except Exception as e:
        logger.error(f"Extraction failed: {e}", exc_info=True)
        print(f"\nFAILED: {e}")
    
    logger.info("=" * 80)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: py test_crime_area_only.py <image_path>")
        print("\nExample:")
        print('  py test_crime_area_only.py "D:\\FYP\\Project\\CrimeVision\\OCRModel\\app\\data\\raw\\FIR_001.png"')
        sys.exit(1)
    
    image_path = sys.argv[1]
    test_crime_area(image_path)
