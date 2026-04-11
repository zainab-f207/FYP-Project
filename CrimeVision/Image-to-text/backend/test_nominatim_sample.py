"""Test actual Nominatim geocoding on a sample of locations."""
import re, os, time, unicodedata

with open('fir_summary.txt', 'r', encoding='utf-8') as f:
    lines = f.read().strip().split('\n')

locations = set()
for i, line in enumerate(lines):
    line = line.strip()
    if line.endswith('.png') and i + 1 < len(lines):
        next_line = lines[i + 1].strip()
        parts = re.split(r'[\u060c,]', next_line)
        first_part = parts[0].strip()
        if first_part:
            locations.add(first_part)

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

def translate_structured(name):
    patterns = [
        (re.compile(r'\u0688\u06cc\s*\u0627\u06cc\u0686\s*\u0627\u06d2\s*\u0641\u06cc\u0632\s*(\d+)\s*\u0648\u0627\u06cc\s*\u0628\u0644\u0627\u06a9'), lambda m: f"DHA Phase {m.group(1)} Y Block"),
        (re.compile(r'\u0688\u06cc\s*\u0627\u06cc\u0686\s*\u0627\u06d2\s*\u0641\u06cc\u0632\s*(\d+)\s*\u0628\u0644\u0627\u06a9\s*(\S+)'), lambda m: f"DHA Phase {m.group(1)} Block {m.group(2)}"),
        (re.compile(r'\u0628\u062d\u0631\u06cc\u06c1\s*\u0622\u0631\u0686\u0631\u0688\s*\u0641\u06cc\u0632\s*(\d+)\s*\u0628\u0644\u0627\u06a9\s*(\S+)'), lambda m: f"Bahria Orchard Phase {m.group(1)} Block {m.group(2)}"),
        (re.compile(r'\u0628\u062d\u0631\u06cc\u06c1\s*\u0679\u0627\u0624\u0646\s*\u0633\u06cc\u06a9\u0679\u0631\s*(\S+)\s*\u0628\u0644\u0627\u06a9\s*(\S+)'), lambda m: f"Bahria Town Sector {m.group(1)} Block {m.group(2)}"),
        (re.compile(r'\u0622\u0633\u06a9\u0627\u0631\u06cc\s*(\d+)\s*\u0628\u0644\u0627\u06a9\s*(\S+)'), lambda m: f"Askari {m.group(1)} Block {m.group(2)}"),
        (re.compile(r'\u0648\u0627\u067e\u0688\u0627\s*\u0679\u0627\u0624\u0646\s*\u0641\u06cc\u0632\s*(\d+)\s*\u0628\u0644\u0627\u06a9\s*(\S+)'), lambda m: f"WAPDA Town Phase {m.group(1)} Block {m.group(2)}"),
        (re.compile(r'\u0644\u06cc\s*\u0688\u06cc\s*\u0627\u06d2\s*\u0633\u0679\u06cc\s*\u0633\u06cc\u06a9\u0679\u0631\s*(\d+)\s*\u0628\u0644\u0627\u06a9\s*(\S+)'), lambda m: f"LDA City Sector {m.group(1)} Block {m.group(2)}"),
        (re.compile(r'\u067e\u06cc\s*\u0633\u06cc\s*\u0627\u06cc\u0633\s*\u0622\u0626\u06cc\s*\u0622\u0631\s*\u0641\u06cc\u0632\s*(\d+)\s*\u0628\u0644\u0627\u06a9\s*(\S+)'), lambda m: f"PCSIR Phase {m.group(1)} Block {m.group(2)}"),
        (re.compile(r'\u0648\u0627\u0644\u06cc\u0646\u0634\u06cc\u0627\s*\u0679\u0627\u0624\u0646\s*\u0628\u0644\u0627\u06a9\s*(\S+)'), lambda m: f"Valencia Town Block {m.group(1)}"),
        (re.compile(r'\u062c\u0648\u06c1\u0631\s*\u0679\u0627\u0624\u0646\s*\u0628\u0644\u0627\u06a9\s*(\S+)'), lambda m: f"Johar Town Block {m.group(1)}"),
        (re.compile(r'\u0627\u0644\u062e\u0636\u0631\u06cc\u0627\s*\u06c1\u0627\u0624\u0633\u0646\u06af\s*\u0628\u0644\u0627\u06a9\s*(\S+)'), lambda m: f"Al Khuderia Housing Block {m.group(1)}"),
        (re.compile(r'\u0627\u06cc\u0688\u0646\s*\u0622\u0628\u0627\u062f\s*\u0628\u0644\u0627\u06a9\s*(\S+)'), lambda m: f"Eden Abad Block {m.group(1)}"),
    ]
    for pat, formatter in patterns:
        match = pat.search(name)
        if match:
            return formatter(match)
    return None

def get_english(loc):
    loc_nfc = unicodedata.normalize('NFC', loc)
    eng = geocode_mappings.get(loc) or normalized_mappings.get(loc_nfc)
    if eng:
        return eng
    trans = translate_structured(loc) or translate_structured(loc_nfc) 
    if trans:
        return trans
    # parenthetical fallback
    paren_match = re.match(r'^(.+?)\s*\(', loc)
    if paren_match:
        base = paren_match.group(1).strip()
        return geocode_mappings.get(base) or normalized_mappings.get(unicodedata.normalize('NFC', base))
    return None

# Categorize for sampling
regular = []
structured = []
for loc in sorted(locations):
    eng = get_english(loc)
    if eng and any(x in eng for x in ['DHA', 'Bahria', 'Askari', 'WAPDA', 'LDA', 'PCSIR', 'Valencia', 'Johar Town Block']):
        structured.append((loc, eng))
    else:
        regular.append((loc, eng or loc))

print(f"Regular: {len(regular)}, Structured: {len(structured)}")

# Test Nominatim with diverse sample
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

geolocator = Nominatim(user_agent="fir_geocode_test_v2", timeout=10.0)

# Sample: 5 regular + 10 structured (diverse types)
sample = regular[:5] + structured[::10][:10]
success = 0
parent_success = 0
fail = 0

results = []
for loc, eng in sample:
    queries = [f"{eng}, Lahore, Pakistan"]
    # Add parent fallback for structured
    if ' Block' in eng:
        parent = eng.rsplit(' Block', 1)[0]
        queries.append(f"{parent}, Lahore, Pakistan")
    
    found = False
    for q in queries:
        try:
            result = geolocator.geocode(q)
            if hasattr(result, 'latitude') and hasattr(result, 'longitude') and 31.0 <= result.latitude <= 32.0 and 73.5 <= result.longitude <= 75.0:
                level = "exact" if q == queries[0] else "parent"
                results.append((loc[:25], eng[:35], result.latitude, result.longitude, level))
                if level == "exact":
                    success += 1
                else:
                    parent_success += 1
                found = True
                break
        except Exception as e:
            pass
        time.sleep(1.1)
    
    if not found:
        results.append((loc[:25], eng[:35], None, None, "FAIL"))
        fail += 1
    time.sleep(1.1)

print(f"\nGeocode Results: {success} exact + {parent_success} parent + {fail} fail = {len(sample)} total")
for loc, eng, lat, lon, level in results:
    if lat:
        print(f"  [{level:6s}] {eng:35s} -> ({lat:.4f}, {lon:.4f})")
    else:
        print(f"  [FAIL  ] {eng:35s} -> NO RESULT")
