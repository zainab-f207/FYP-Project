"""
Test crime area extraction using the ACTUAL production class.
This ensures we test the real pipeline, not a standalone reimplementation.
"""
import sys
import os
import re
import cv2
import io

# Force UTF-8 output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.dirname(__file__))

from fir_specialized_ocr import FIRExtractor

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
                last_part = parts[-1].strip() if len(parts) > 1 else ""
                expected[filename] = {
                    'first_part': first_part,
                    'full': full_text,
                    'last_part': last_part
                }
                i += 2
            else:
                i += 1
        else:
            i += 1
    return expected


def is_first_part_match(extracted, expected_first):
    if not extracted or not expected_first:
        return False
    e = extracted.strip()
    f = expected_first.strip()
    if f in e or e in f:
        return True
    # Fuzzy: check key words overlap
    e_words = set(e.split())
    f_words = set(f.split())
    if f_words and e_words:
        overlap = len(e_words & f_words)
        if overlap >= max(1, len(f_words) * 0.5):
            return True
    # Specific fuzzy mappings
    fuzzy_pairs = [
        ('غڑی', 'غری'), ('شاہو', 'شاھو'), ('گدائی', 'گدافی'),
        ('لوہاری', 'لزاری'), ('لبارٹ', 'لبرٹ'),
    ]
    for a, b in fuzzy_pairs:
        if (a in e and b in f) or (b in e and a in f):
            return True
    return False


def main():
    expected_data = load_expected()
    
    # Initialize the production OCR class
    ocr = FIRExtractor()
    
    correct = 0
    thana_match = 0
    no_result = 0
    other_wrong = 0
    total = 0
    
    wrong_list = []
    
    # Test first 30 images (or all available)
    test_count = 30
    tested = 0
    
    for fname in sorted(expected_data.keys()):
        if tested >= test_count:
            break
        
        path = os.path.join(IMAGE_DIR, fname)
        if not os.path.exists(path):
            continue
        
        total += 1
        tested += 1
        exp = expected_data[fname]
        expected_first = exp['first_part']
        expected_last = exp['last_part']
        
        # Use the ACTUAL production method
        image = cv2.imread(path)
        if image is None:
            print(f"\n{'='*60}")
            print(f"📂 {fname}")
            print(f"   ❌ Could not read image")
            no_result += 1
            continue
        
        result = ocr.extract_crime_area(image)
        
        print(f"\n{'='*60}")
        print(f"📂 {fname}")
        print(f"   Expected first: {expected_first}")
        print(f"   Expected last:  {expected_last}")
        print(f"   Extracted: {result}")
        
        if not result:
            print(f"   ❌ NO RESULT")
            no_result += 1
            wrong_list.append((fname, result, expected_first))
        elif is_first_part_match(result, expected_first):
            print(f"   ✅ CORRECT (first part)")
            correct += 1
        elif is_first_part_match(result, expected_last):
            print(f"   ❌ WRONG (got thana name!)")
            thana_match += 1
            wrong_list.append((fname, result, expected_first))
        else:
            print(f"   ❌ OTHER")
            other_wrong += 1
            wrong_list.append((fname, result, expected_first))
    
    print(f"\n{'='*60}")
    print(f"PRODUCTION CLASS TEST RESULTS (first {test_count} images)")
    print(f"{'='*60}")
    print(f"  Total tested:         {total}")
    print(f"  ✅ Correct (first part): {correct}/{total} ({100*correct/total:.1f}%)")
    print(f"  ❌ Wrong (got thana):    {thana_match}/{total}")
    print(f"  ❌ No result:            {no_result}/{total}")
    print(f"  ❌ Other wrong:          {other_wrong}/{total}")
    
    if wrong_list:
        print(f"\n⚠️ Failed images:")
        for fname, got, should_be in wrong_list:
            got_short = (got[:60] + '...') if got and len(got) > 60 else got
            print(f"  {fname}: got '{got_short}' should be '{should_be}'")


if __name__ == '__main__':
    main()
