"""
Test script to verify area fuzzy correction is working
Tests the fuzzy correction directly without importing main.py
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

# Import only the fuzzy correction function (not the full main.py)
from urdu_location_dictionary import correct_location_text, _urdu_similarity
import re

def extract_area_simple(area_text: str) -> str:
    """Simplified area extraction for testing (mimics the updated extract_crime_area logic)"""
    if not area_text:
        return ""
    
    text = area_text.strip()
    text = re.sub(r'[ \t]+', ' ', text)
    
    # Remove labels
    label_to_remove = [
        r'جائے\s*وقوعہ',
        r'جائے\s*اور\s*علاقہ.*',
        r'تحصیل\s*و\s*ضلع',
        r'علاقہ\s*تحصیل',
    ]
    
    for label in label_to_remove:
        text = re.sub(label, '', text, flags=re.UNICODE)
    
    # Remove distance patterns
    distance_pattern = r'(?:سے|ے)\s*(?:تقر|نقر|تھر|تمر|تپ|تر|نر|۲ر|تت)'
    distance_match = re.search(distance_pattern, text)
    if distance_match:
        text = text[:distance_match.start()].strip()
    
    extracted_area = None
    
    # Extract text before dash
    dash_patterns = [
        r'^(.*?)[\-]{4,}',
        r'^(.*?)[\-]{3,}',
        r'^(.*?)[ـ]{3,}',
        r'^(.*?)[—]{2,}',
        r'^(.*?)[\.\۔]{4,}',
    ]
    
    for pattern in dash_patterns:
        match = re.search(pattern, text, re.DOTALL | re.UNICODE)
        if match:
            area = match.group(1).strip()
            if area and len(area) >= 3:
                area = re.sub(r'\s+', ' ', area).strip()
                area = re.sub(r'^[\s\-_=.:،۔\d]+', '', area)
                area = re.sub(r'[\s\-_=.:،۔]+$', '', area)
                area = re.sub(r'[\d۰-۹]+\.[\d۰-۹]*\s*$', '', area)
                area = area.strip()
                
                urdu_chars = sum(1 for c in area if '\u0600' <= c <= '\u06FF')
                english_chars = sum(1 for c in area if c.isalpha() and c.isascii())
                
                if (urdu_chars >= 3 or english_chars >= 3) and len(area) >= 3:
                    extracted_area = area
                    break
    
    # Apply fuzzy correction if extracted
    if extracted_area:
        extracted_area = re.sub(r'[\[\]{}()!@#$%^&*;:<>|]', '', extracted_area)
        extracted_area = ' '.join(extracted_area.split()).strip()
        
        # Apply fuzzy correction
        corrected_area = correct_location_text(extracted_area)
        
        if corrected_area and len(corrected_area) >= 2:
            corrected_area = re.sub(r'\s+', ' ', corrected_area).strip()
            return corrected_area
    
    return ""

print("=" * 70)
print("TESTING AREA FUZZY CORRECTION")
print("=" * 70)

# Test cases: Common broken Urdu OCR outputs from area field
test_cases = [
    # Test 1: Broken "ماڈل ٹاؤن" (Model Town)
    {
        "input": "ماأال ان مارک الیک لاک وڑ",
        "expected": "ماڈل ٹاؤن مارکیٹ",
        "description": "Broken Model Town Market"
    },
    # Test 2: Broken "بھاٹی گیٹ" (Bhati Gate)
    {
        "input": "ھ بدا کیٹ بعائی پک شال مار",
        "expected": "بھاٹی گیٹ",
        "description": "Broken Bhati Gate with Shalimar"
    },
    # Test 3: Broken "اقبال ٹاؤن" (Iqbal Town)
    {
        "input": "جاور ار زگ ر وڈ اقال جائان",
        "expected": "حیدر روڈ / اقبال ٹاؤن",
        "description": "Broken Haider Road / Iqbal Town"
    },
    # Test 4: Broken with dash separator
    {
        "input": "ھ پا کیٹ بھاٹی چک----جائے وقوعہ",
        "expected": "بھاٹی گیٹ",
        "description": "Broken with dash and label"
    },
    # Test 5: With distance text
    {
        "input": "الال ہتکن مارکیٹ سے تقریباً 2.5 کلومیٹر----جائے وقوعہ",
        "expected": "ماڈل ٹاؤن مارکیٹ",
        "description": "With distance text"
    },
    # Test 6: Clean text (should pass through correctly)
    {
        "input": "گلبرگ روڈ----جائے وقوعہ",
        "expected": "گلبرگ",
        "description": "Already clean text"
    },
    # Test 7: Broken "شالامار" (Shalimar)
    {
        "input": "شالا مار باغ پک----علاقہ",
        "expected": "شالامار",
        "description": "Broken Shalimar Bagh"
    },
]

print("\n" + "-"*70)
print("TEST RESULTS")
print("-"*70)

passed = 0
failed = 0

for i, test in enumerate(test_cases, 1):
    print(f"\nTest {i}: {test['description']}")
    print(f"  Input:    {test['input']}")
    
    # Test the extraction method
    result = extract_area_simple(test['input'])
    
    print(f"  Output:   {result}")
    print(f"  Expected: {test['expected']}")
    
    # Check if the result is close to expected
    # We use fuzzy matching since OCR correction may produce slight variations
    similarity = _urdu_similarity(result, test['expected'])
    
    # Consider it a pass if similarity > 60% or if result contains key parts of expected
    if similarity > 0.6 or any(word in result for word in test['expected'].split() if len(word) > 2):
        print(f"  Status:   ✅ PASS (similarity: {similarity:.1%})")
        passed += 1
    else:
        print(f"  Status:   ❌ FAIL (similarity: {similarity:.1%})")
        failed += 1

print("\n" + "="*70)
print(f"SUMMARY: {passed} passed, {failed} failed out of {len(test_cases)} tests")
print("="*70)

# Additional test: Direct fuzzy correction
print("\n" + "="*70)
print("DIRECT FUZZY CORRECTION TEST (No Extraction)")
print("="*70)

direct_tests = [
    "ماأال ان مارک",  # Should correct to "ماڈل ٹاؤن مارکیٹ"
    "اقال جائان",      # Should correct to "اقبال ٹاؤن"
    "ھ پا کیٹ",        # Should correct to "بھاٹی گیٹ"
    "شالا مار",        # Should correct to "شالامار"
]

for raw_text in direct_tests:
    corrected = correct_location_text(raw_text)
    print(f"\n  Raw:       {raw_text}")
    print(f"  Corrected: {corrected}")

print("\n" + "="*70)
print("✅ Area fuzzy correction testing complete!")
print("="*70)
