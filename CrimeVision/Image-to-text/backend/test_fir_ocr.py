"""
Quick test script for FIR OCR
Tests the specialized FIR extraction on sample images
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent / 'backend'))

from fir_specialized_ocr import FIRExtractor
import logging
import io
import sys

# Fix Windows encoding
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_fir_extraction(image_path: str, debug: bool = False):
    """Test FIR extraction on a single image"""
    
    logger.info("=" * 80)
    logger.info("TESTING FIR OCR SYSTEM")
    logger.info("=" * 80)
    
    # Initialize extractor
    logger.info("Initializing FIR extractor...")
    extractor = FIRExtractor(debug_mode=debug)
    
    if debug:
        logger.info("🔍 Debug mode ENABLED - will save preprocessed images")
    
    # Load image
    logger.info(f"Loading image: {image_path}")
    try:
        with open(image_path, 'rb') as f:
            image_bytes = f.read()
        logger.info(f"Image loaded: {len(image_bytes)} bytes")
    except Exception as e:
        logger.error(f"Failed to load image: {e}")
        return
    
    # Extract FIR data
    logger.info("Extracting FIR data...")
    result = extractor.extract_fir_data(image_bytes)
    
    # Display results
    logger.info("\n" + "=" * 80)
    logger.info("EXTRACTION RESULTS")
    logger.info("=" * 80)
    
    if result['status'] == 'success':
        logger.info(f"Status: SUCCESS")
        logger.info(f"Crime Date: {result['crime_date']}")
        # logger.info(f"Crime Area (Thana): {result['crime_area']}")
        logger.info(f"Sections: {', '.join(result['sections']) if result['sections'] else 'None'}")
        logger.info(f"Confidence: {result['confidence']}%")
        logger.info(f"\nFields Found:")
        logger.info(f"  - Crime Date: {'YES' if result['fields_found']['crime_date'] else 'NO'}")
        # logger.info(f"  - Crime Area: {'YES' if result['fields_found']['crime_area'] else 'NO'}")
        logger.info(f"  - Sections: {'YES' if result['fields_found']['sections'] else 'NO'}")
        
        # Check if meets target confidence
        if result['confidence'] >= 85:
            logger.info(f"\n🎯 TARGET ACHIEVED: Confidence {result['confidence']}% >= 85%")
        else:
            logger.warning(f"\n⚠️ Below target: Confidence {result['confidence']}% < 85%")
    else:
        logger.error(f"✗ Status: FAILED")
        logger.error(f"✗ Error: {result.get('error', 'Unknown error')}")
    
    logger.info("=" * 80)
    
    return result


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test FIR OCR extraction')
    parser.add_argument('image', help='Path to FIR image file')
    parser.add_argument('--debug', '-d', action='store_true', help='Enable debug mode (saves preprocessed images)')
    
    args = parser.parse_args()
    
    # Check if file exists
    if not Path(args.image).exists():
        print(f"Error: Image file not found: {args.image}")
        sys.exit(1)
    
    # Test extraction
    result = test_fir_extraction(args.image, debug=args.debug)
    
    # Exit code based on success
    if result and result['status'] == 'success' and result['confidence'] >= 85:
        print("\nTest PASSED")
        sys.exit(0)
    else:
        print("\nTest FAILED or below target confidence")
        sys.exit(1)


if __name__ == '__main__':
    main()
