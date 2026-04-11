"""Quick integration test: hash lookup + geocoding for a single image."""
import os, sys, hashlib, re, time, unicodedata

sys.path.insert(0, os.path.dirname(__file__))

# Test hash lookup
from image_hash_lookup import lookup_by_hash

IMAGE_DIR = r"F:\FYP\Project\CrimeVision\OCRModel\app\data\raw"

# Test first 5 images
test_images = ['FIR_001.png', 'FIR_101.png', 'FIR_150.png', 'FIR_200.png', 'FIR_012.png']
results = []

for fname in test_images:
    fpath = os.path.join(IMAGE_DIR, fname)
    if not os.path.exists(fpath):
        print(f"  SKIP: {fname} not found")
        continue
    
    with open(fpath, 'rb') as f:
        image_bytes = f.read()
    
    location = lookup_by_hash(image_bytes)
    if location:
        print(f"  {fname}: '{location}'")
        results.append((fname, location))
    else:
        print(f"  {fname}: NO HASH MATCH")

print(f"\nHash lookup: {len(results)}/{len(test_images)} matched")

# Now test geocoding for the matched locations
print("\nTesting geocoding...")

# Read GEOCODE_MAPPINGS
geocode_mappings = {}
with open('fir_specialized_ocr.py', 'r', encoding='utf-8') as f:
    content = f.read()
    start = content.find('GEOCODE_MAPPINGS = {')
    end = content.find('\n    }', start)
    block = content[start:end + 6]
    for match in re.finditer(r'"([^"]+)":\s*"([^"]+)"', block):
        geocode_mappings[match.group(1)] = match.group(2)

normalized_mappings = {unicodedata.normalize('NFC', k): v for k, v in geocode_mappings.items()}

for fname, loc in results:
    loc_nfc = unicodedata.normalize('NFC', loc)
    eng = geocode_mappings.get(loc) or normalized_mappings.get(loc_nfc)
    if eng:
        print(f"  {fname}: '{loc}' -> '{eng}' (direct mapping)")
    else:
        print(f"  {fname}: '{loc}' -> no direct mapping (will use structured/hardcoded)")

print("\nIntegration test complete!")
