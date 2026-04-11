"""Quick test: Multi-config voting + Fuzzy dictionary correction on crime area OCR"""
import cv2
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from fir_specialized_ocr import FIRExtractor
from urdu_location_dictionary import test_correction, correct_location_text

# ============================================================
# TEST 1: Direct fuzzy correction on previous OCR outputs
# ============================================================
print("=" * 70)
print("TEST 1: FUZZY CORRECTION ON KNOWN OCR OUTPUTS")
print("=" * 70)

# These are actual OCR outputs from previous runs
test_texts = [
    # FIR_001: should be something like "حیدر پارک روڈ / اقبال ٹاؤن"
    "جاور ار ؛م زگ ر وڈ اقال جائان",
    "د ہیور پر ؛س زگ ر وڈ تال کاو",
    "وہر طر وص رکگرروڈ وقپال ماؤن",
    "دحیدر ہس رگرروڈ دقپال ماؤن",
    # FIR_006: should be "بھاٹی گیٹ / شالامار"
    "ھ۸ ہمان کیٹ بھائی ہر ک",
    "ھ بدا کیٹ بعائی پک شال مار",
    "ھ پا کیٹ بھاٹی چک شال مار",
    "ہلا یلیٹ بھانی چک",
    "ای گیٹ بھاٹی پک شال مار",
    # FIR_010: should be "نیو مارکیٹ ایم دالم روڈ"
    "رن مارکیٹ ارام الم رز ہبا کی",
    "اہر نی مارکیٹ ای ایم دا لم روڈ",
    "ابر یمارکیٹ ام پالم ررز",
    # FIR_014: should be "ماڈل ٹاؤن مارکیٹ / لنک روڈ"
    "ماأال ڈان ما رگ ایل ےلاک",
    "الال ان مارک الیک لاک وڑ",
    "مال گڈاکن مارک ال لاک دز",
    "الال ہتکن مارکیٹ الیک لاکگک وڈ",
    # FIR_015: should be "ماڈل ٹاؤن / بلاک"
    "ٹیل دائؤن آر فی الاک رات رکش",
    "نیل دن آر یلاک دا",
    "یلد انآ رن ملاک دا",
]

for text in test_texts:
    result = test_correction(text)
    print(f"\n  INPUT:     {text}")
    print(f"  CORRECTED: {result['corrected']}")
    print(f"  MATCH:     {result['best_match']} ({result['similarity']:.0%})")

# ============================================================
# TEST 2: Full pipeline on actual images
# ============================================================
print("\n" + "=" * 70)
print("TEST 2: FULL PIPELINE ON FIR IMAGES")
print("=" * 70)

image_dir = r"F:\FYP2\Project\CrimeVision\OCRModel\app\data\raw"
fir_files = ["FIR_001.png", "FIR_006.png", "FIR_010.png", "FIR_014.png", "FIR_015.png"]

extractor = FIRExtractor(use_gpu=False)

for fname in fir_files:
    fpath = os.path.join(image_dir, fname)
    if not os.path.exists(fpath):
        print(f"\n--- {fname}: FILE NOT FOUND ---")
        continue
    
    img = cv2.imread(fpath)
    if img is None:
        print(f"\n--- {fname}: COULD NOT READ ---")
        continue
    
    h, w = img.shape[:2]
    result = extractor.extract_crime_area(img)
    print(f"\n--- {fname} ({w}x{h}) ---")
    print(f"  RESULT: \"{result}\"")

print("\nDone!")
