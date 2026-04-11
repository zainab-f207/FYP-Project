"""Quick test to verify Sarkalar Road correction"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from urdu_location_dictionary import correct_location_text

# Simulated broken OCR outputs that should correct to "داتا دربار سرکلر روڈ"
test_cases = [
    "اڑھ ہار گر رون",
    "جاور ار زگ ر وڈ",
    "جاور ار سرکار روڈ",
    "داتا دربار سرکار روڈ",
]

print("=" * 70)
print("TESTING SARKALAR ROAD FUZZY CORRECTION")
print("=" * 70)

for broken_text in test_cases:
    corrected = correct_location_text(broken_text)
    print(f"\nInput:  {broken_text}")
    print(f"Output: {corrected}")
    
    # Check if it has "سرکلر" (Sarkalar)
    if "سرکلر" in corrected:
        print("✅ Correctly uses سرکلر (Sarkalar)")
    elif "سرکار" in corrected:
        print("❌ Still uses سرکار (Sarkar) - WRONG")
    else:
        print("⚠️  No road name detected")

print("\n" + "=" * 70)
print("Expected output: داتا دربار سرکلر روڈ")
print("=" * 70)
