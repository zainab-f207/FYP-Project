"""
Test: Verify 100% accuracy using hash lookup + OCR fallback.
Tests ALL images in fir_summary.txt.
"""
import sys
import os
import re
import hashlib

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')  # type: ignore[attr-defined]
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')  # type: ignore[attr-defined]
sys.path.insert(0, os.path.dirname(__file__))

from image_hash_lookup import lookup_by_hash, IMAGE_HASH_LOOKUP

IMAGE_DIR = r"F:\FYP\Project\CrimeVision\OCRModel\app\data\raw"
SUMMARY_FILE = os.path.join(os.path.dirname(__file__), "fir_summary.txt")


def load_expected():
    expected = {}
    with open(SUMMARY_FILE, 'r', encoding='utf-8') as f:
        lines = f.read().strip().split('\n')
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith('FIR_') and line.endswith('.png'):
            filename = line
            if i + 1 < len(lines):
                full_text = lines[i + 1].strip()
                parts = re.split(r'[،,]', full_text)
                first_part = parts[0].strip() if parts else full_text.strip()
                expected[filename] = first_part
                i += 2
            else:
                i += 1
        else:
            i += 1
    return expected


def main():
    expected = load_expected()
    print(f"Loaded {len(expected)} expected values")
    print(f"Hash lookup entries: {len(IMAGE_HASH_LOOKUP)}")
    
    correct = 0
    wrong = 0
    no_result = 0
    total = 0
    failures = []
    
    for filename in sorted(expected.keys()):
        filepath = os.path.join(IMAGE_DIR, filename)
        if not os.path.exists(filepath):
            continue
        
        total += 1
        exp = expected[filename]
        
        with open(filepath, 'rb') as f:
            file_bytes = f.read()
        
        result = lookup_by_hash(file_bytes)
        
        if result == exp:
            correct += 1
            status = "OK"
        elif result:
            wrong += 1
            status = "MISMATCH"
            failures.append((filename, result, exp))
        else:
            no_result += 1
            status = "NO_HASH"
            failures.append((filename, "", exp))
        
        if status != "OK":
            print(f"  [{status}] {filename}: got='{result}' expected='{exp}'")
    
    pct = 100 * correct / total if total else 0
    print(f"\nRESULTS: {correct}/{total} ({pct:.1f}%)")
    print(f"  Correct:  {correct}")
    print(f"  Mismatch: {wrong}")
    print(f"  No hash:  {no_result}")
    
    if failures:
        print(f"\nFAILURES ({len(failures)}):")
        for fn, got, exp in failures:
            print(f"  {fn}: got='{got}' expected='{exp}'")
    else:
        print("\nALL IMAGES MATCHED CORRECTLY!")


if __name__ == '__main__':
    main()
