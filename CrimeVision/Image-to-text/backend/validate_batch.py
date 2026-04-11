"""
Batch Validation Script
Tests region accuracy on multiple FIR images before full processing
"""

import cv2
import numpy as np
from pathlib import Path
import sys
import json
from typing import List, Dict
import logging

sys.path.append(str(Path(__file__).parent))
from fir_specialized_ocr import FIRExtractor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def validate_regions_on_samples(folder: str, sample_count: int = 20):
    """
    Test extraction on sample images to validate region accuracy
    """
    folder_path = Path(folder)
    
    # Get sample images
    image_files = list(folder_path.glob("*.png")) + list(folder_path.glob("*.jpg"))
    
    if len(image_files) < sample_count:
        sample_count = len(image_files)
        logger.warning(f"Only {len(image_files)} images found, testing all")
    
    # Random sample
    import random
    random.seed(42)
    samples = random.sample(image_files, sample_count)
    
    logger.info(f"Testing extraction on {sample_count} sample images...")
    
    # Initialize extractor
    extractor = FIRExtractor(debug_mode=False)
    
    results = []
    success_count = 0
    
    for idx, img_path in enumerate(samples, 1):
        logger.info(f"\n[{idx}/{sample_count}] Processing: {img_path.name}")
        
        try:
            with open(img_path, 'rb') as f:
                image_bytes = f.read()
            
            result = extractor.extract_fir_data(image_bytes)
            
            # Check success
            fields_found = sum([
                bool(result.get('crime_date')),
                bool(result.get('crime_area')),
                bool(result.get('sections'))
            ])
            
            if result['status'] == 'success' and fields_found >= 2:
                success_count += 1
                status = "✓ SUCCESS"
            else:
                status = "✗ PARTIAL/FAILED"
            
            results.append({
                'file': img_path.name,
                'status': status,
                'date_found': bool(result.get('crime_date')),
                'thana_found': bool(result.get('crime_area')),
                'sections_found': bool(result.get('sections')),
                'confidence': result.get('confidence', 0),
                'date': result.get('crime_date', ''),
                'thana': result.get('crime_area', ''),
                'sections': result.get('sections', [])
            })
            
            logger.info(f"{status} | Confidence: {result.get('confidence', 0)}%")
            logger.info(f"  Date: {result.get('crime_date', 'NOT FOUND')}")
            logger.info(f"  Thana: {result.get('crime_area', 'NOT FOUND')}")
            logger.info(f"  Sections: {result.get('sections', 'NOT FOUND')}")
            
        except Exception as e:
            logger.error(f"Error processing {img_path.name}: {e}")
            results.append({
                'file': img_path.name,
                'status': '✗ ERROR',
                'error': str(e)
            })
    
    # Print summary
    logger.info("\n" + "=" * 80)
    logger.info("VALIDATION SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Total samples: {sample_count}")
    logger.info(f"Successful: {success_count} ({success_count/sample_count*100:.1f}%)")
    
    # Field-level success rates
    date_success = sum(1 for r in results if r.get('date_found', False))
    thana_success = sum(1 for r in results if r.get('thana_found', False))
    sections_success = sum(1 for r in results if r.get('sections_found', False))
    
    logger.info(f"\nField Success Rates:")
    logger.info(f"  Date: {date_success}/{sample_count} ({date_success/sample_count*100:.1f}%)")
    logger.info(f"  Thana: {thana_success}/{sample_count} ({thana_success/sample_count*100:.1f}%)")
    logger.info(f"  Sections: {sections_success}/{sample_count} ({sections_success/sample_count*100:.1f}%)")
    
    # Save results
    output_file = folder_path / "validation_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    logger.info(f"\nResults saved to: {output_file}")
    logger.info("=" * 80)
    
    # Recommendations
    if success_count / sample_count < 0.7:
        logger.warning("\n⚠️ Success rate < 70% - Region adjustments needed!")
        logger.warning("Recommendations:")
        logger.warning("  1. Run visualize_regions.py on failed images")
        logger.warning("  2. Use adjust_regions.py to fine-tune coordinates")
        logger.warning("  3. Check if FIR forms have different layouts")
    elif success_count / sample_count < 0.85:
        logger.warning("\n⚠️ Success rate < 85% - Consider improvements:")
        logger.warning("  1. Add adaptive region detection")
        logger.warning("  2. Test on more diverse samples")
    else:
        logger.info("\n✓ Success rate > 85% - Ready for full batch processing!")
    
    return results


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Validate extraction on sample images')
    parser.add_argument('folder', help='Folder containing FIR images')
    parser.add_argument('--count', '-n', type=int, default=20, help='Number of samples to test')
    
    args = parser.parse_args()
    
    if not Path(args.folder).exists():
        print(f"Error: Folder not found: {args.folder}")
        sys.exit(1)
    
    validate_regions_on_samples(args.folder, args.count)


if __name__ == '__main__':
    main()
