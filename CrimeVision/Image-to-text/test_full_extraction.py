"""
Test script to verify the complete extraction logic with real OCR output
"""

import sys
sys.path.append('backend')

from main import TextParser
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Simulated OCR output based on your actual frontend result
test_text = """LHR+ب 38392025
LHR+ب 3839-2025
iتc Fcamact
Ciنc Fcamact
- اببارل
ٹلہب
لالہر
الکتب 1007-092025
418225:/
الکمت 1007-09/2025
418225:,
08:53PM/ 12-012-2025.
تنے رەل
08;53PM 12-02-2025
09:18PM1 12-02-2025
08;532M1 12~022025
09:18P}112-02-2025
:م رعتاسااءوستیں
2
&1ن/:4892432-336
3
--148
7-148
-=149
7-302
LHRI5682: پلد
"""

print("\n" + "="*70)
print("Testing Complete FIR Extraction Logic")
print("="*70)

print("\nRaw OCR Text:")
print("-"*70)
print(test_text)
print("-"*70)

# Test the extraction
parser = TextParser()
result = parser.extract_info(test_text)

print("\n" + "="*70)
print("EXTRACTION RESULTS:")
print("="*70)

print(f"\n📅 Crime Date: {result['crime_date']}")
print(f"   Confidence: {result['field_confidence']['crime_date']*100:.1f}%")

print(f"\n📋 Crime Type: {result['crime_type']}")
print(f"   Confidence: {result['field_confidence']['crime_type']*100:.1f}%")

print(f"\n📍 Crime Area: {result['crime_area']}")
print(f"   Confidence: {result['field_confidence']['crime_area']*100:.1f}%")

print("\n" + "="*70)
print("Expected Results:")
print("="*70)
print("Date: 12-02-2025")
print("Sections: 148, 149, 302 PPC")
print("Area: پلد (or similar thana name)")

print("\n" + "="*70)
print("Test Complete!")
print("="*70 + "\n")

