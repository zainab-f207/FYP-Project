"""
Test crime area extraction using the production extract_crime_area method directly.
Avoids loading heavy PaddleOCR models by patching __init__.
Output to file to handle Unicode encoding issues.
"""
import sys
import os
import re
import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))

# Patch FIRSpecializedOCR to skip heavy model loading
import fir_specialized_ocr as fir_mod

class LightOCR:
    """Lightweight wrapper that only uses extract_crime_area"""
    def __init__(self):
        pass
    
    # Borrow the methods from the original class
    extract_crime_area = fir_mod.FIRExtractor.extract_crime_area
    _clean_crime_area_text = fir_mod.FIRExtractor._clean_crime_area_text

IMAGE_DIR = r"F:\FYP\Project\CrimeVision\OCRModel\app\data\raw"
SUMMARY_FILE = os.path.join(os.path.dirname(__file__), "fir_summary.txt")
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "production_test_results.txt")


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
    e_words = set(e.split())
    f_words = set(f.split())
    if f_words and e_words:
        overlap = len(e_words & f_words)
        if overlap >= max(1, len(f_words) * 0.5):
            return True
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
    ocr = LightOCR()
    
    correct = 0
    thana_match = 0
    no_result = 0
    other_wrong = 0
    total = 0
    wrong_list = []
    
    test_count = 30
    tested = 0
    
    out_lines = []
    
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
        
        image = cv2.imread(path)
        if image is None:
            out_lines.append(f"{fname}: FAILED TO READ")
            no_result += 1
            continue
        
        result = ocr.extract_crime_area(image)
        
        if not result:
            status = "NO_RESULT"
            no_result += 1
            wrong_list.append((fname, result or "", expected_first))
        elif is_first_part_match(result, expected_first):
            status = "CORRECT"
            correct += 1
        elif is_first_part_match(result, expected_last):
            status = "THANA_MATCH"
            thana_match += 1
            wrong_list.append((fname, result, expected_first))
        else:
            status = "OTHER_WRONG"
            other_wrong += 1
            wrong_list.append((fname, result, expected_first))
        
        out_lines.append(f"{fname}: {status} | got='{result}' | expected='{expected_first}'")
        # Print progress to console (ASCII safe)
        print(f"  [{tested}/{test_count}] {fname}: {status}")
    
    # Summary
    summary = []
    summary.append(f"\n{'='*60}")
    summary.append(f"PRODUCTION CLASS TEST RESULTS (first {test_count})")
    summary.append(f"{'='*60}")
    summary.append(f"Total tested:    {total}")
    summary.append(f"Correct:         {correct}/{total} ({100*correct/total:.1f}%)")
    summary.append(f"Thana match:     {thana_match}/{total}")
    summary.append(f"No result:       {no_result}/{total}")
    summary.append(f"Other wrong:     {other_wrong}/{total}")
    
    if wrong_list:
        summary.append(f"\nFailed images:")
        for fname, got, should_be in wrong_list:
            got_short = (got[:80]) if got and len(got) > 80 else got
            summary.append(f"  {fname}: got='{got_short}' should='{should_be}'")
    
    # Write results to file
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        for line in out_lines:
            f.write(line + '\n')
        for line in summary:
            f.write(line + '\n')
    
    # Print summary to console
    for line in summary:
        print(line)
    
    print(f"\nFull results saved to: {OUTPUT_FILE}")


if __name__ == '__main__':
    import pytesseract
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    main()
