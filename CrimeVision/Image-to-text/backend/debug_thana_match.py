"""Debug script to test thana matching."""
import sys
sys.path.insert(0, '.')
from fir_specialized_ocr import FIRExtractor
import cv2

# Create the extractor
extractor = FIRExtractor()

# Simulate what OCR returns from FIR_004.png header
# Based on analyze_header.py output, OCR reads: "قان : کشمراول"
test_ocr_texts = [
    "ٹ : لاہور",
    "قان : کشمراول",
    "9356/25",
    "Lahore"
]

print("=" * 60)
print("Testing _match_known_thana with FIR_004 OCR texts")
print("=" * 60)

# Define known thanas
KNOWN_THANAS = [
    "Gulshan Ravi", "گلشن راوی",
    "Iqbal Town", "اقبال ٹاؤن",
    "Model Town", "ماڈل ٹاؤن",
    "Ghalib Market", "غالب مارکیٹ",
]

print(f"\nOCR texts: {test_ocr_texts}")
print(f"\nKnown thanas: {KNOWN_THANAS}")

# Combined text
combined = ' '.join(test_ocr_texts)
print(f"\nCombined text: {combined}")

# Check if کشمراول is in the text
search_term = "کشمراول"
print(f"\nSearching for: '{search_term}'")
print(f"Is in combined: {search_term in combined}")
print(f"Is in combined.lower(): {search_term.lower() in combined.lower()}")

# Test the actual matcher
result = extractor._match_known_thana(test_ocr_texts, KNOWN_THANAS)
print(f"\n_match_known_thana result: {result}")

# Also test with the raw image
if len(sys.argv) > 1:
    img_path = sys.argv[1]
    print(f"\n\nTesting with actual image: {img_path}")
    img = cv2.imread(img_path)
    if img is not None:
        result = extractor.extract_crime_area(img)
        print(f"\nextract_crime_area result: {result}")
