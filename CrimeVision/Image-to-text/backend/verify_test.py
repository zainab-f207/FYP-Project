"""Quick verify - test specific images and write results to file."""
import cv2, sys, os, gc, re, numpy as np, time

outf = open('verify_results.txt', 'w', encoding='utf-8')

import pytesseract
from batch_test_tess import (extract_crime_area_tesseract, parse_summary, 
                              is_match, extract_first_location, CRIME_STRIPS)
from urdu_location_dictionary import _urdu_similarity, _normalize_text

IMAGE_DIR = r"D:\FYP\Project\CrimeVision\OCRModel\app\data\raw"
SUMMARY_FILE = os.path.join(os.path.dirname(__file__), "fir_summary.txt")

entries = parse_summary(SUMMARY_FILE)
sorted_entries = sorted(entries.items(), key=lambda x: x[0])

passed = 0
failed = 0
fail_list = []

for fname, expected in sorted_entries:
    img_path = os.path.join(IMAGE_DIR, fname)
    if not os.path.exists(img_path):
        continue
    
    file_size = os.path.getsize(img_path)
    img = cv2.imread(img_path, cv2.IMREAD_REDUCED_COLOR_2) if file_size > 15_000_000 else cv2.imread(img_path)
    if img is None:
        continue
    
    ih, iw = img.shape[:2]
    if max(ih, iw) > 5000:
        s = 3000.0 / max(ih, iw)
        img = cv2.resize(img, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
    
    extracted = extract_crime_area_tesseract(img)
    del img
    gc.collect()
    
    expected_first = extract_first_location(expected)
    match = is_match(extracted, expected)
    
    if match:
        passed += 1
        mark = "OK"
    else:
        failed += 1
        mark = "XX"
        fail_list.append((fname, expected_first, extracted))
    
    line = f"[{mark}] {fname:<16} expected: {expected_first} | got: {extracted or '(empty)'}"
    outf.write(line + '\n')
    print(f"  {mark} {fname}")

outf.write(f'\nRESULTS: {passed}/{passed+failed} passed ({100*passed/max(passed+failed,1):.1f}%)\n')
outf.write(f'\nFAILED:\n')
for fn, exp, ext in fail_list:
    outf.write(f'  {fn}: expected [{exp}] got [{ext}]\n')

outf.close()
print(f"\nDone: {passed}/{passed+failed}")
