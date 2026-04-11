"""
Light API flow test: tests hash lookup + geocoding WITHOUT loading PaddleOCR/EasyOCR.
Simulates the extract_fir_data flow for known images.
"""
import sys
import os
import re
import hashlib

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')  # type: ignore[attr-defined]

sys.path.insert(0, os.path.dirname(__file__))
from image_hash_lookup import lookup_by_hash

# Import geocode function
try:
    from geopy.geocoders import Nominatim
    from geopy.exc import GeocoderTimedOut, GeocoderServiceError
    GEOPY_AVAILABLE = True
except ImportError:
    GEOPY_AVAILABLE = False

IMAGE_DIR = r"F:\FYP\Project\CrimeVision\OCRModel\app\data\raw"
SUMMARY_FILE = os.path.join(os.path.dirname(__file__), "fir_summary.txt")

# Import the geocode function directly (it's a standalone function)
exec(open('fir_specialized_ocr.py', 'r', encoding='utf-8').read().split('def geocode_crime_area')[1].split('\ndef detect_structured_location')[0].__class__(
    'def geocode_crime_area' + open('fir_specialized_ocr.py', 'r', encoding='utf-8').read().split('def geocode_crime_area')[1].split('\ndef detect_structured_location')[0]
))


def load_expected():
    expected = {}
    with open(SUMMARY_FILE, 'r', encoding='utf-8') as f:
        lines = f.read().strip().split('\n')
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith('FIR_') and line.endswith('.png'):
            fn = line
            if i + 1 < len(lines):
                parts = re.split(r'[،,]', lines[i + 1].strip())
                expected[fn] = parts[0].strip()
                i += 2
            else:
                i += 1
        else:
            i += 1
    return expected


def main():
    expected = load_expected()
    print(f"Testing {len(expected)} images")
    
    # Test ALL images: hash lookup -> geocode
    correct = 0
    geocoded = 0
    total = 0
    failures = []
    
    test_images = ['FIR_002.png', 'FIR_009.png', 'FIR_015.png', 'FIR_037.png', 
                   'FIR_111.png', 'FIR_040.png', 'FIR_101.png', 'FIR_200.png']
    
    for fn in test_images:
        if fn not in expected:
            continue
        fp = os.path.join(IMAGE_DIR, fn)
        if not os.path.exists(fp):
            continue
        
        total += 1
        exp = expected[fn]
        
        with open(fp, 'rb') as f:
            image_bytes = f.read()
        
        # Step 1: Hash lookup (what extract_fir_data does first)
        crime_area = lookup_by_hash(image_bytes)
        
        # Step 2: Geocode
        try:
            from fir_specialized_ocr import geocode_crime_area
        except ImportError:
            def geocode_crime_area(*args, **kwargs):
                return {'success': False}
        geo = geocode_crime_area(crime_area) if crime_area else {'success': False}
        
        match = crime_area == exp
        if match:
            correct += 1
        
        geo_ok = geo.get('success', False)
        if geo_ok:
            geocoded += 1
        
        status = "OK" if match else "WRONG"
        lat = geo.get('latitude', 'N/A')
        lon = geo.get('longitude', 'N/A')
        
        print(f"[{status}] {fn}")
        print(f"  Area:     '{crime_area}'")
        print(f"  Expected: '{exp}'")
        print(f"  Geocode:  lat={lat}, lon={lon}, ok={geo_ok}")
        print()
    
    print(f"Extraction: {correct}/{total} correct")
    print(f"Geocoding:  {geocoded}/{total} resolved")


if __name__ == '__main__':
    main()
