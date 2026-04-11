"""
Test script for date and section extraction
Verifies that date and section extraction still work correctly
after crime area extraction improvements.
"""
import cv2
import sys
import logging
import gc

# Fix Unicode encoding for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from fir_specialized_ocr import FIRExtractor


def test_date_sections(image_path: str):
    """Test date and section extraction on a single image"""

    logger.info("=" * 80)
    logger.info(f"TESTING DATE & SECTION EXTRACTION: {image_path}")
    logger.info("=" * 80)

    # Initialize extractor FIRST (loads EasyOCR when more memory available)
    logger.info("Initializing FIR extractor...")
    extractor = FIRExtractor(debug_mode=True)
    gc.collect()

    # Load image
    img = cv2.imread(image_path)
    if img is None:
        logger.error(f"Failed to load image: {image_path}")
        return

    h, w = img.shape[:2]
    logger.info(f"Image loaded: {w}x{h}px ({img.nbytes / (1024*1024):.1f} MB)")

    # --- Extract Date ---
    logger.info("\n" + "=" * 60)
    logger.info("EXTRACTING DATE...")
    logger.info("=" * 60)
    try:
        date_result = extractor.extract_date(img)
        if date_result:
            logger.info(f"Date found: {date_result}")
        else:
            logger.warning("No date found")
    except Exception as e:
        date_result = None
        logger.error(f"Date extraction failed: {e}", exc_info=True)

    # --- Extract Sections ---
    logger.info("\n" + "=" * 60)
    logger.info("EXTRACTING SECTIONS...")
    logger.info("=" * 60)
    try:
        sections_result = extractor.extract_sections(img)
        if sections_result:
            logger.info(f"Sections found: {len(sections_result)}")
            for i, sec in enumerate(sections_result, 1):
                logger.info(f"  Section {i}: {sec}")
        else:
            logger.warning("No sections found")
    except Exception as e:
        sections_result = None
        logger.error(f"Section extraction failed: {e}", exc_info=True)

    # --- Summary ---
    print("\n" + "=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)

    if date_result:
        print(f"  Date    : {date_result}")
    else:
        print(f"  Date    : NOT FOUND")

    if sections_result:
        print(f"  Sections: {', '.join(sections_result)}")
    else:
        print(f"  Sections: NOT FOUND")

    print("=" * 60)


def test_batch(image_dir: str):
    """Test date and section extraction on all FIR images in a directory"""
    import os
    import glob

    patterns = [os.path.join(image_dir, p) for p in ["FIR_*.png", "FIR_*.jpg", "FIR_*.jpeg"]]
    files = []
    for pat in patterns:
        files.extend(glob.glob(pat))

    if not files:
        print(f"No FIR images found in: {image_dir}")
        return

    files.sort()
    print(f"\nFound {len(files)} FIR image(s)")
    print("=" * 60)

    # Initialize extractor once
    logger.info("Initializing FIR extractor...")
    extractor = FIRExtractor(debug_mode=False)
    gc.collect()

    results = []
    for fpath in files:
        fname = os.path.basename(fpath)
        print(f"\nProcessing: {fname}")

        img = cv2.imread(fpath)
        if img is None:
            print(f"  SKIP: Failed to load image")
            results.append((fname, None, None))
            continue

        try:
            date_result = extractor.extract_date(img)
        except Exception:
            date_result = None

        try:
            sections_result = extractor.extract_sections(img)
        except Exception:
            sections_result = None

        results.append((fname, date_result, sections_result))

        if date_result:
            print(f"  Date    : {date_result}")
        else:
            print(f"  Date    : NOT FOUND")

        if sections_result:
            print(f"  Sections: {', '.join(sections_result)}")
        else:
            print(f"  Sections: NOT FOUND")

        # Free memory
        del img
        gc.collect()

    # Final summary table
    print("\n\n" + "=" * 80)
    print("FINAL SUMMARY")
    print("=" * 80)
    print(f"{'File':<20} {'Date':<15} {'Sections'}")
    print("-" * 80)
    for fname, date, sections in results:
        sec_str = ', '.join(sections) if sections else 'NOT FOUND'
        date_str = date if date else 'NOT FOUND'
        print(f"{fname:<20} {date_str:<15} {sec_str}")
    print("=" * 80)

    total = len(results)
    dates_found = sum(1 for _, d, _ in results if d)
    secs_found = sum(1 for _, _, s in results if s)
    print(f"\nDates found:    {dates_found}/{total}")
    print(f"Sections found: {secs_found}/{total}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  Single image:  py test_date_sections.py <image_path>")
        print("  Batch (dir):   py test_date_sections.py --batch <image_directory>")
        print()
        print("Examples:")
        print('  py test_date_sections.py "D:\\FYP\\...\\FIR_001.png"')
        print('  py test_date_sections.py --batch "D:\\FYP\\...\\raw"')
        sys.exit(1)

    if sys.argv[1] == "--batch" and len(sys.argv) >= 3:
        test_batch(sys.argv[2])
    else:
        test_date_sections(sys.argv[1])
