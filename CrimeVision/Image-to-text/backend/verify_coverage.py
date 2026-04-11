"""Verify all locations have geocoding coverage (mapping or structured translation)."""
import re, os

summary_file = os.path.join(os.path.dirname(__file__), 'fir_summary.txt')
with open(summary_file, 'r', encoding='utf-8') as f:
    lines = f.read().strip().split('\n')

locations = set()
for i, line in enumerate(lines):
    line = line.strip()
    if line.endswith('.png') and i + 1 < len(lines):
        next_line = lines[i + 1].strip()
        parts = re.split(r'[\u060c,]', next_line)  # Urdu comma or ASCII comma
        first_part = parts[0].strip()
        if first_part:
            locations.add(first_part)

print(f"Unique locations: {len(locations)}")

# Read GEOCODE_MAPPINGS keys
geocode_mappings = {}
ocr_file = os.path.join(os.path.dirname(__file__), 'fir_specialized_ocr.py')
with open(ocr_file, 'r', encoding='utf-8') as f:
    content = f.read()
    start = content.find('GEOCODE_MAPPINGS = {')
    end = content.find('\n    }', start)
    block = content[start:end + 6]
    for match in re.finditer(r'"([^"]+)":\s*"([^"]+)"', block):
        geocode_mappings[match.group(1)] = match.group(2)

print(f"GEOCODE_MAPPINGS: {len(geocode_mappings)}")

# translate_structured
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

mapped = 0
translated = 0
unmapped = []

for loc in sorted(locations):
    if loc in geocode_mappings:
        mapped += 1
    elif translate_structured(loc):
        translated += 1
    else:
        unmapped.append(loc)

print(f"Mapped: {mapped}, Translated: {translated}, Unmapped: {len(unmapped)}")
if unmapped:
    for u in unmapped:
        print(f"  MISS: {u}")
else:
    print("ALL LOCATIONS COVERED!")
