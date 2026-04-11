"""Quick test of just the fuzzy dictionary - no images needed"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from urdu_location_dictionary import test_correction, correct_location_text, multi_vote_correct

print("=" * 60)
print("FUZZY DICTIONARY CORRECTION TEST")
print("=" * 60)

# Actual OCR outputs from previous debug runs
tests = [
    # FIR_006 OCR outputs - should match "بھاٹی گیٹ"
    ("ھ بدا کیٹ بعائی پک شال مار", "بھاٹی گیٹ / شالامار"),
    ("ھ پا کیٹ بھاٹی چک", "بھاٹی گیٹ"),
    ("ای گیٹ بھاٹی پک شال مار", "بھاٹی گیٹ / شالامار"),
    ("ہا یلیٹ بھانی چک", "بھاٹی گیٹ"),
    # FIR_014 OCR outputs - should match "ماڈل ٹاؤن مارکیٹ"
    ("ماأال ڈان ما رگ ایل ےلاک", "ماڈل ٹاؤن مارکیٹ"),
    ("الال ان مارک الیک لاک وڑ", "ماڈل ٹاؤن مارکیٹ"),
    ("الال ہتکن مارکیٹ الیک لاکگک وڈ", "ماڈل ٹاؤن مارکیٹ"),
    # FIR_010 - market related
    ("رن مارکیٹ ارام الم رز", "مارکیٹ / اسلام روڈ"),
    ("اہر نی مارکیٹ ای ایم دا لم روڈ", "مارکیٹ / اسلام روڈ"),
    # FIR_001 - should have حیدر and اقبال ٹاؤن
    ("جاور ار زگ ر وڈ اقال جائان", "حیدر روڈ / اقبال ٹاؤن"),
    ("دحیدر ہس رگرروڈ دقپال ماؤن", "حیدر روڈ / اقبال ٹاؤن"),
    # FIR_015 - ماڈل ٹاؤن + بلاک
    ("ٹیل دائؤن آر فی الاک رات", "ماڈل ٹاؤن / بلاک"),
    ("نیل دن آر یلاک دا", "ماڈل ٹاؤن / بلاک"),
]

for raw, expected in tests:
    result = test_correction(raw)
    print(f"\n  RAW OCR:   {raw}")
    print(f"  EXPECTED:  {expected}")
    print(f"  CORRECTED: {result['corrected']}")
    print(f"  MATCH:     {result['best_match']} ({result['similarity']:.0%})")

# Test multi-vote with simulated results
print("\n" + "=" * 60)
print("MULTI-VOTE TEST (FIR_006)")
print("=" * 60)
simulated_006 = [
    {'text': 'ھ بدا کیٹ بعائی پک شال مار', 'score': 15, 'method': 'raw_otsu'},
    {'text': 'ھ پا کیٹ بھاٹی چک', 'score': 12, 'method': 'denoise_otsu'},
    {'text': 'ای گیٹ بھاٹی پک شال مار', 'score': 14, 'method': 'morph_otsu'},
    {'text': 'ہلا یلیٹ بھانی چک', 'score': 10, 'method': '0.5x_otsu'},
]
voted = multi_vote_correct(simulated_006)
print(f"  VOTED RESULT: {voted}")

print("\n" + "=" * 60)
print("MULTI-VOTE TEST (FIR_014)")
print("=" * 60)
simulated_014 = [
    {'text': 'ماأال ڈان ما رگ ایل ےلاک', 'score': 12, 'method': 'raw_gray'},
    {'text': 'الال ان مارک الیک لاک وڑ', 'score': 11, 'method': 'raw_otsu'},
    {'text': 'الال ہتکن مارکیٹ الیک لاکگک وڈ', 'score': 14, 'method': 'denoise_otsu'},
    {'text': 'مال گڈاکن مارک ال لاک دز', 'score': 10, 'method': 'morph_otsu'},
]
voted = multi_vote_correct(simulated_014)
print(f"  VOTED RESULT: {voted}")

print("\nDone!")
