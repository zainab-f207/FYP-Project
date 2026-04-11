"""
Batch FIR Processing Script
Process 3000+ FIR images and extract structured data
Outputs: CSV file with all extracted data
"""

import os
import sys
import csv
import json
import logging
from pathlib import Path
from typing import List, Dict
from datetime import datetime
import time

# Add backend to path
sys.path.append(str(Path(__file__).parent / 'backend'))

from fir_specialized_ocr import FIRExtractor  # type: ignore

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'batch_processing_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class BatchFIRProcessor:
    """Process multiple FIR images in batch"""
    
    def __init__(self, input_folder: str, output_csv: str):
        self.input_folder = Path(input_folder)
        self.output_csv = Path(output_csv)
        self.extractor = FIRExtractor()
        self.results: List[Dict] = []
        
        # Statistics
        self.total_processed = 0
        self.successful = 0
        self.failed = 0
        self.start_time: float | None = None
        
    def find_images(self) -> List[Path]:
        """Find all image files in input folder"""
        image_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff'}
        images = []
        
        for ext in image_extensions:
            images.extend(self.input_folder.glob(f'*{ext}'))
            images.extend(self.input_folder.glob(f'*{ext.upper()}'))
        
        logger.info(f"Found {len(images)} images in {self.input_folder}")
        return sorted(images)
    
    def process_image(self, image_path: Path) -> Dict:
        """Process a single FIR image"""
        try:
            logger.info(f"Processing: {image_path.name}")
            
            # Read image
            with open(image_path, 'rb') as f:
                image_bytes = f.read()
            
            # Extract FIR data
            result = self.extractor.extract_fir_data(image_bytes)
            
            # Add filename to result
            result['filename'] = image_path.name
            result['filepath'] = str(image_path)
            
            if result['status'] == 'success':
                self.successful += 1
                logger.info(f"✓ Success: {image_path.name} (Confidence: {result['confidence']}%)")
                logger.info(f"  Date: {result['crime_date']}, Thana: {result['crime_area']}, Sections: {result['sections']}")
            else:
                self.failed += 1
                logger.error(f"✗ Failed: {image_path.name} - {result.get('error', 'Unknown error')}")
            
            return result
            
        except Exception as e:
            self.failed += 1
            logger.error(f"✗ Error processing {image_path.name}: {e}")
            return {
                'filename': image_path.name,
                'filepath': str(image_path),
                'status': 'failed',
                'error': str(e),
                'crime_date': '',
                'crime_area': '',
                'sections': [],
                'confidence': 0
            }
    
    def process_all(self):
        """Process all images in batch"""
        self.start_time = time.time()
        
        logger.info("=" * 80)
        logger.info("STARTING BATCH FIR PROCESSING")
        logger.info("=" * 80)
        
        # Find all images
        images = self.find_images()
        
        if not images:
            logger.error("No images found!")
            return
        
        total_images = len(images)
        logger.info(f"Total images to process: {total_images}")
        
        # Process each image
        for idx, image_path in enumerate(images, 1):
            logger.info(f"\n[{idx}/{total_images}] " + "=" * 60)
            
            result = self.process_image(image_path)
            self.results.append(result)
            self.total_processed += 1
            
            # Show progress
            elapsed = time.time() - self.start_time
            avg_time = elapsed / self.total_processed
            remaining = (total_images - self.total_processed) * avg_time
            
            logger.info(f"Progress: {self.total_processed}/{total_images} ({self.total_processed/total_images*100:.1f}%)")
            logger.info(f"Success: {self.successful} | Failed: {self.failed}")
            logger.info(f"Elapsed: {elapsed/60:.1f}min | Est. remaining: {remaining/60:.1f}min")
            
            # Save intermediate results every 100 images
            if self.total_processed % 100 == 0:
                self.save_results(suffix='_intermediate')
                logger.info("Intermediate results saved")
        
        # Final save
        self.save_results()
        self.print_summary()
    
    def save_results(self, suffix=''):
        """Save results to CSV"""
        if not self.results:
            logger.warning("No results to save")
            return
        
        output_file = self.output_csv.parent / f"{self.output_csv.stem}{suffix}{self.output_csv.suffix}"
        
        with open(output_file, 'w', newline='', encoding='utf-8-sig') as f:
            fieldnames = ['filename', 'filepath', 'status', 'crime_date', 'crime_area', 
                         'sections', 'confidence', 'error']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            
            writer.writeheader()
            for result in self.results:
                # Convert sections list to string
                row = result.copy()
                row['sections'] = ', '.join(result.get('sections', []))
                writer.writerow(row)
        
        logger.info(f"Results saved to: {output_file}")
        
        # Also save as JSON for easier processing
        json_file = output_file.with_suffix('.json')
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        logger.info(f"JSON results saved to: {json_file}")
    
    def print_summary(self):
        """Print processing summary"""
        if self.start_time is None:
            logger.error("No start time recorded")
            return
        
        elapsed = time.time() - self.start_time
        
        logger.info("\n" + "=" * 80)
        logger.info("BATCH PROCESSING COMPLETE")
        logger.info("=" * 80)
        logger.info(f"Total images processed: {self.total_processed}")
        logger.info(f"Successful: {self.successful} ({self.successful/self.total_processed*100:.1f}%)")
        logger.info(f"Failed: {self.failed} ({self.failed/self.total_processed*100:.1f}%)")
        logger.info(f"Total time: {elapsed/60:.1f} minutes")
        logger.info(f"Average time per image: {elapsed/self.total_processed:.1f} seconds")
        
        # Calculate field extraction rates
        date_found = sum(1 for r in self.results if r.get('crime_date'))
        thana_found = sum(1 for r in self.results if r.get('crime_area'))
        sections_found = sum(1 for r in self.results if r.get('sections'))
        
        logger.info(f"\nField Extraction Rates:")
        logger.info(f"  Crime Date: {date_found}/{self.successful} ({date_found/self.successful*100:.1f}%)")
        logger.info(f"  Crime Area (Thana): {thana_found}/{self.successful} ({thana_found/self.successful*100:.1f}%)")
        logger.info(f"  Sections: {sections_found}/{self.successful} ({sections_found/self.successful*100:.1f}%)")
        
        # Average confidence
        confidences = [r.get('confidence', 0) for r in self.results if r.get('status') == 'success']
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        logger.info(f"\nAverage confidence: {avg_confidence:.1f}%")
        
        # High confidence extractions (>= 85%)
        high_conf = sum(1 for c in confidences if c >= 85)
        logger.info(f"High confidence extractions (>=85%): {high_conf}/{len(confidences)} ({high_conf/len(confidences)*100:.1f}%)")
        
        logger.info("=" * 80)


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Batch process FIR images')
    parser.add_argument('input_folder', help='Folder containing FIR images')
    parser.add_argument('--output', '-o', default='fir_results.csv', help='Output CSV file')
    
    args = parser.parse_args()
    
    # Validate input folder
    input_folder = Path(args.input_folder)
    if not input_folder.exists():
        print(f"Error: Input folder not found: {input_folder}")
        sys.exit(1)
    
    if not input_folder.is_dir():
        print(f"Error: Input path is not a folder: {input_folder}")
        sys.exit(1)
    
    # Create output folder if needed
    output_csv = Path(args.output)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    
    # Process
    processor = BatchFIRProcessor(str(input_folder), str(output_csv))
    processor.process_all()


if __name__ == '__main__':
    main()
