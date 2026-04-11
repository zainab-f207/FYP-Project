"""
Batch test crime area extraction against fir_summary.txt ground truth.
Tests all images and reports accuracy.
"""
import cv2
import sys
import os
import gc
import logging
import re
import time

os.environ['DISABLE_MODEL_SOURCE_CHECK'] = 'True'

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Reduce logging noise 
logging.basicConfig(level=logging.WARNING, format='%(levelname)s - %(message)s')

# Disable PaddleOCR to save memory - only Tesseract + EasyOCR needed for crime area
import fir_specialized_ocr
fir_specialized_ocr.PADDLEOCR_AVAILABLE = False

from fir_specialized_ocr import FIRExtractor
from urdu_location_dictionary import _urdu_similarity, _normalize_text

IMAGE_DIR = r"D:\FYP\Project\CrimeVision\OCRModel\app\data\raw"
SUMMARY_FILE = os.path.join(os.path.dirname(__file__), "fir_summary.txt")


def parse_summary(path):
    """Parse fir_summary.txt into {filename: expected_area} dict."""
    entries = {}
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.read().strip().split('\n')
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith('FIR_') and line.endswith('.png'):
            fname = line
            # Next non-empty line is the expected area
            i += 1
            while i < len(lines) and not lines[i].strip():
                i += 1
            if i < len(lines) and not lines[i].strip().startswith('FIR_'):
                area = lines[i].strip()
                entries[fname] = area
            continue
        i += 1
    return entries


def extract_first_location(full_area: str) -> str:
    """Get the primary location (first comma-separated field)."""
    parts = full_area.split('،')
    if not parts:
        parts = full_area.split(',')
    return parts[0].strip()


def is_match(extracted: str, expected_full: str, threshold=0.45) -> bool:
    """Check if extracted area matches expected (using first field similarity)."""
    if not extracted:
        return False
    
    expected_first = extract_first_location(expected_full)
    
    # Normalize both
    ext_norm = _normalize_text(extracted)
    exp_norm = _normalize_text(expected_first)
    exp_full_norm = _normalize_text(expected_full)
    
    # Check similarity against first field
    sim1 = _urdu_similarity(ext_norm, exp_norm)
    if sim1 >= threshold:
        return True
    
    # Check similarity against full area
    sim2 = _urdu_similarity(ext_norm, exp_full_norm)
    if sim2 >= threshold:
        return True
    
    # Check if first field is contained in extracted
    if exp_norm and exp_norm in ext_norm:
        return True
    
    # Check if extracted is contained in expected
    if ext_norm and ext_norm in exp_full_norm:
        return True
    
    return False


def main():
    # Parse summary
    entries = parse_summary(SUMMARY_FILE)
    print(f"Loaded {len(entries)} entries from fir_summary.txt")
    
    # Optionally limit to specific range
    start_idx = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    end_idx = int(sys.argv[2]) if len(sys.argv) > 2 else len(entries)
    
    # Sort entries
    sorted_entries = sorted(entries.items(), key=lambda x: x[0])
    sorted_entries = sorted_entries[start_idx:end_idx]
    
    print(f"Testing {len(sorted_entries)} images (index {start_idx} to {end_idx})")
    print("=" * 100)
    
    # Init extractor once
    print("Initializing FIR extractor...")
    extractor = FIRExtractor(debug_mode=False)
    # Free the English-only EasyOCR reader (not needed for crime area)
    if hasattr(extractor, 'ocr') and hasattr(extractor.ocr, 'easyocr_reader_en'):
        extractor.ocr.easyocr_reader_en = None
    gc.collect()
    print("Ready.\n")
    
    results = []
    passed = 0
    failed = 0
    errors = 0
    
    for fname, expected in sorted_entries:
        img_path = os.path.join(IMAGE_DIR, fname)
        if not os.path.exists(img_path):
            print(f"  SKIP {fname} - file not found")
            continue
        
        t0 = time.time()
        try:
            # Check file size to decide loading strategy
            file_size = os.path.getsize(img_path)
            
            if file_size > 40_000_000:  # > 40MB: load at 1/4 resolution
                img = cv2.imread(img_path, cv2.IMREAD_REDUCED_COLOR_4)
            elif file_size > 15_000_000:  # > 15MB: load at 1/2 resolution
                img = cv2.imread(img_path, cv2.IMREAD_REDUCED_COLOR_2)
            else:
                img = cv2.imread(img_path)
            
            if img is None:
                print(f"  SKIP {fname} - failed to load")
                continue
            
            # Final safety cap at 3000px
            ih, iw = img.shape[:2]
            if max(ih, iw) > 3000:
                scale_down = 3000.0 / max(ih, iw)
                img = cv2.resize(img, None, fx=scale_down, fy=scale_down, interpolation=cv2.INTER_AREA)
            
            extracted = extractor.extract_crime_area(img)
            del img
            gc.collect()
            elapsed = time.time() - t0
            
            expected_first = extract_first_location(expected)
            match = is_match(extracted, expected)
            
            if match:
                status = "PASS"
                passed += 1
            else:
                status = "FAIL"
                failed += 1
            
            # Compute similarity for reporting
            if extracted:
                sim = _urdu_similarity(_normalize_text(extracted), _normalize_text(expected_first))
            else:
                sim = 0.0
            
            results.append((fname, status, expected_first, extracted or "(empty)", sim, elapsed))
            
            mark = "OK" if match else "XX"
            print(f"  [{mark}] {fname:<16} sim={sim:.2f} t={elapsed:.1f}s | expected: {expected_first} | got: {extracted or '(empty)'}")
            
        except Exception as e:
            elapsed = time.time() - t0
            errors += 1
            results.append((fname, "ERR", extract_first_location(expected), str(e)[:50], 0.0, elapsed))
            print(f"  [ER] {fname:<16} ERROR: {str(e)[:80]}")
        finally:
            # Always ensure image is freed
            try:
                del img
            except:
                pass
            gc.collect()
            # Also clear torch memory cache if available
            try:
                import torch
                if hasattr(torch, 'cuda') and torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except:
                pass
    
    # Summary
    total = passed + failed + errors
    print("\n" + "=" * 100)
    print(f"RESULTS: {passed}/{total} passed ({100*passed/max(total,1):.1f}%), {failed} failed, {errors} errors")
    print("=" * 100)
    
    if failed > 0:
        print("\nFAILED images:")
        for fname, status, expected, extracted, sim, elapsed in results:
            if status == "FAIL":
                print(f"  {fname:<16} expected: {expected}")
                print(f"  {'':16} got:      {extracted} (sim={sim:.2f})")
    
    if errors > 0:
        print("\nERROR images:")
        for fname, status, expected, extracted, sim, elapsed in results:
            if status == "ERR":
                print(f"  {fname}: {extracted}")


if __name__ == "__main__":
    main()
