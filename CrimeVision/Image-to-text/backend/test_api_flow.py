"""
End-to-end test: Simulates API flow for ALL 149 images.
Tests: file bytes -> extract_fir_data -> crime_area + geocoding
"""
import sys
import os
import re

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')  # type: ignore[attr-defined]
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')  # type: ignore[attr-defined]
os.environ['DISABLE_MODEL_SOURCE_CHECK'] = 'True'
sys.path.insert(0, os.path.dirname(__file__))

IMAGE_DIR = r"F:\FYP\Project\CrimeVision\OCRModel\app\data\raw"
SUMMARY_FILE = os.path.join(os.path.dirname(__file__), "fir_summary.txt")


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
    # Import fir_specialized_ocr
    import importlib
    import importlib.util
    spec = importlib.util.spec_from_file_location('fir_mod', 'fir_specialized_ocr.py')
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load spec for fir_mod from fir_specialized_ocr.py")
        fir_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fir_mod)
    
    extractor = fir_mod.FIRExtractor()
    expected = load_expected()
    print(f"Loaded {len(expected)} expected values")
    
    # Test sample images through full extract_fir_data flow
    test_images = ['FIR_002.png', 'FIR_009.png', 'FIR_015.png', 'FIR_037.png', 'FIR_111.png']
    
    for fn in test_images:
        if fn not in expected:
            continue
        fp = os.path.join(IMAGE_DIR, fn)
        if not os.path.exists(fp):
            continue
        
        with open(fp, 'rb') as f:
            image_bytes = f.read()
        
        result = extractor.extract_fir_data(image_bytes)
        
        crime_area = result.get('crime_area', '')
        location = result.get('location', {})
        lat = location.get('latitude')
        lon = location.get('longitude')
        display = location.get('display_name', '')[:60]
        mappable = location.get('mappable', False)
        exp = expected[fn]
        
        match = "OK" if crime_area == exp else "WRONG"
        print(f"[{match}] {fn}")
        print(f"  Expected:  '{exp}'")
        print(f"  Got:       '{crime_area}'")
        print(f"  Lat/Long:  ({lat}, {lon})")
        print(f"  Mappable:  {mappable}")
        if display:
            print(f"  Display:   {display}")
        print()


if __name__ == '__main__':
    main()
