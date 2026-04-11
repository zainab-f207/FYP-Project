"""Test geocoding for all 149 locations from fir_summary.txt."""
import sys, os, re, time

# Read fir_summary.txt to get all unique locations
summary_file = os.path.join(os.path.dirname(__file__), 'fir_summary.txt')
with open(summary_file, 'r', encoding='utf-8') as f:
    lines = f.read().strip().split('\n')

locations = set()
for line in lines:
    line = line.strip()
    if not line or line.endswith('.png'):
        continue
    parts = line.split(',')
    first_part = parts[0].strip()
    if first_part:
        locations.add(first_part)

print(f"Unique locations to test: {len(locations)}")

# Test the translate_structured function inline  
def translate_structured(name):
    patterns = [
        (re.compile(r'ڈی\s*ایچ\s*اے\s*فیز\s*(\d+)\s*وای\s*بلاک'), lambda m: f"DHA Phase {m.group(1)} Y Block"),
        (re.compile(r'ڈی\s*ایچ\s*اے\s*فیز\s*(\d+)\s*بلاک\s*(\S+)'), lambda m: f"DHA Phase {m.group(1)} Block {m.group(2)}"),
        (re.compile(r'بحریہ\s*آرچرڈ\s*فیز\s*(\d+)\s*بلاک\s*(\S+)'), lambda m: f"Bahria Orchard Phase {m.group(1)} Block {m.group(2)}"),
        (re.compile(r'بحریہ\s*ٹاؤن\s*سیکٹر\s*(\S+)\s*بلاک\s*(\S+)'), lambda m: f"Bahria Town Sector {m.group(1)} Block {m.group(2)}"),
        (re.compile(r'آسکاری\s*(\d+)\s*بلاک\s*(\S+)'), lambda m: f"Askari {m.group(1)} Block {m.group(2)}"),
        (re.compile(r'واپڈا\s*ٹاؤن\s*فیز\s*(\d+)\s*بلاک\s*(\S+)'), lambda m: f"WAPDA Town Phase {m.group(1)} Block {m.group(2)}"),
        (re.compile(r'لی\s*ڈی\s*اے\s*سٹی\s*سیکٹر\s*(\d+)\s*بلاک\s*(\S+)'), lambda m: f"LDA City Sector {m.group(1)} Block {m.group(2)}"),
        (re.compile(r'پی\s*سی\s*ایس\s*آئی\s*آر\s*فیز\s*(\d+)\s*بلاک\s*(\S+)'), lambda m: f"PCSIR Phase {m.group(1)} Block {m.group(2)}"),
        (re.compile(r'والینشیا\s*ٹاؤن\s*بلاک\s*(\S+)'), lambda m: f"Valencia Town Block {m.group(1)}"),
        (re.compile(r'جوہر\s*ٹاؤن\s*بلاک\s*(\S+)'), lambda m: f"Johar Town Block {m.group(1)}"),
        (re.compile(r'الخضریا\s*ہاؤسنگ\s*بلاک\s*(\S+)'), lambda m: f"Al Khuderia Housing Block {m.group(1)}"),
        (re.compile(r'ایڈن\s*آباد\s*بلاک\s*(\S+)'), lambda m: f"Eden Abad Block {m.group(1)}"),
    ]
    for pat, formatter in patterns:
        match = pat.search(name)
        if match:
            return formatter(match)
    return None

# Read GEOCODE_MAPPINGS from fir_specialized_ocr.py
geocode_mappings = {}
with open(os.path.join(os.path.dirname(__file__), 'fir_specialized_ocr.py'), 'r', encoding='utf-8') as f:
    content = f.read()
    # Find the GEOCODE_MAPPINGS dict
    start = content.find('GEOCODE_MAPPINGS = {')
    if start >= 0:
        end = content.find('\n    }', start)
        block = content[start:end+6]
        # Extract key-value pairs
        for match in re.finditer(r'"([^"]+)":\s*"([^"]+)"', block):
            geocode_mappings[match.group(1)] = match.group(2)

print(f"GEOCODE_MAPPINGS entries: {len(geocode_mappings)}")

# Test translation coverage
translated = 0
mapped = 0
unmapped = []

for loc in sorted(locations):
    # Check if in GEOCODE_MAPPINGS
    if loc in geocode_mappings:
        mapped += 1
        continue
    
    # Check if translate_structured handles it
    eng = translate_structured(loc)
    if eng:
        translated += 1
        continue
    
    unmapped.append(loc)

print(f"\nCoverage Results:")
print(f"  Direct mapping:    {mapped}")
print(f"  Structured trans:  {translated}")
print(f"  UNMAPPED:          {len(unmapped)}")

if unmapped:
    print(f"\nUnmapped locations ({len(unmapped)}):")
    for u in unmapped:
        print(f"  '{u}'")
else:
    print(f"\n✓ ALL {len(locations)} locations have geocoding coverage!")

# Now test a sample of geocoding queries with Nominatim
print("\n" + "="*60)
print("Testing actual Nominatim geocoding (sample of 10)...")
print("="*60)

try:
    from geopy.geocoders import Nominatim
    from geopy.exc import GeocoderTimedOut, GeocoderServiceError
    
    geolocator = Nominatim(user_agent="fir_geocode_test_v1", timeout=10.0)
    
    # Pick a sample: 5 regular + 5 structured
    regular_locs = [l for l in sorted(locations) if not translate_structured(l)][:5]
    struct_locs = [l for l in sorted(locations) if translate_structured(l)][:5]
    sample = regular_locs + struct_locs
    
    success = 0
    fail = 0
    
    for loc in sample:
        eng = geocode_mappings.get(loc)
        if not eng:
            eng = translate_structured(loc)
        
        if eng:
            query = f"{eng}, Lahore, Pakistan"
        else:
            query = f"{loc}, Lahore, Pakistan"
        
        try:
            result = geolocator.geocode(query)
            if hasattr(result, 'latitude') and hasattr(result, 'longitude') and 31.0 <= result.latitude <= 32.0 and 73.5 <= result.longitude <= 75.0:
                print(f"  ✓ {loc[:30]:30s} -> ({result.latitude:.4f}, {result.longitude:.4f})")
                success += 1
            else:
                # Try parent
                parent_eng = eng.rsplit(' Block', 1)[0] if eng and ' Block' in eng else None
                if parent_eng:
                    time.sleep(1.1)
                    result2 = geolocator.geocode(f"{parent_eng}, Lahore, Pakistan")
                    if hasattr(result2, 'latitude') and hasattr(result2, 'longitude') and 31.0 <= result2.latitude <= 32.0 and 73.5 <= result2.longitude <= 75.0:
                        print(f"  ~ {loc[:30]:30s} -> ({result2.latitude:.4f}, {result2.longitude:.4f}) [parent]")
                        success += 1
                        time.sleep(1.1)
                        continue
                print(f"  ✗ {loc[:30]:30s} -> NO RESULT for: {query}")
                fail += 1
        except Exception as e:
            print(f"  ✗ {loc[:30]:30s} -> ERROR: {e}")
            fail += 1
        time.sleep(1.1)
    
    print(f"\nGeocode sample: {success}/{len(sample)} succeeded")
    
except ImportError:
    print("geopy not installed, skipping Nominatim test")
