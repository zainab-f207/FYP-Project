"""End-to-end test: extract_crime_area -> geocode -> lat/long"""
import sys
import os
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')  # type: ignore[attr-defined]
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')  # type: ignore[attr-defined]

# Minimal imports to avoid loading heavy OCR engines
os.environ['EASYOCR_DISABLE'] = '1'

import cv2
import importlib
import importlib.util

# Load the module
spec = importlib.util.spec_from_file_location("fir_mod", "fir_specialized_ocr.py")
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load spec for fir_mod from fir_specialized_ocr.py")
    fir_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fir_mod)

# Test geocoding directly with known locations
print("=" * 60)
print("TEST 1: Direct geocoding of known Urdu locations")
print("=" * 60)

test_locations = [
    "انارکلی بازار",
    "لبرٹی مارکیٹ", 
    "سبزہ زار",
    "قذافی اسٹیڈیم",
    "لوہاری گیٹ",
    "شالامار باغ",
    "گلبرگ",
    "جوہر ٹاؤن",
]

for loc in test_locations:
    result = fir_mod.geocode_crime_area(loc)
    status = "OK" if result['success'] else "FAIL"
    lat = result.get('latitude', 'N/A')
    lon = result.get('longitude', 'N/A')
    display = result.get('display_name', '')[:60]
    print(f"  [{status}] {loc} -> ({lat}, {lon})")
    if display:
        print(f"         {display}")

# Test extraction on a few images
print("\n" + "=" * 60)
print("TEST 2: Extract crime area + geocode from FIR images")
print("=" * 60)

image_dir = r"F:\FYP\Project\CrimeVision\OCRModel\app\data\raw"
test_images = ["FIR_002.png", "FIR_001.png", "FIR_003.png", "FIR_015.png"]

# Create a lightweight extractor
class LightExtractor:

    def extract_crime_area(self, *args, **kwargs):
        # Dummy implementation, replace with actual logic as needed
        return None

extractor = LightExtractor()
extractor.extract_crime_area = fir_mod.FIRExtractor.extract_crime_area.__get__(extractor)

for img_name in test_images:
    img_path = os.path.join(image_dir, img_name)
    if not os.path.exists(img_path):
        print(f"  [SKIP] {img_name} not found")
        continue
    
    image = cv2.imread(img_path)
    if image is None:
        print(f"  [SKIP] {img_name} couldn't be read")
        continue
    
    crime_area = extractor.extract_crime_area(image)
    
    if crime_area:
        geo = fir_mod.geocode_crime_area(crime_area)
        status = "OK" if geo['success'] else "NO_GEO"
        lat = geo.get('latitude', 'N/A')
        lon = geo.get('longitude', 'N/A')
        print(f"  [{status}] {img_name}: area='{crime_area}' -> ({lat}, {lon})")
    else:
        print(f"  [EMPTY] {img_name}: No crime area extracted")

print("\nDone!")
