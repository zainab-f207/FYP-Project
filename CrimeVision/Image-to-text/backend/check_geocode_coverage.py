"""Check which locations from fir_summary.txt are missing from GEOCODE_MAPPINGS"""
import sys, os, re
import io
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')  # type: ignore[attr-defined]
else:
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    except Exception:
        pass
sys.path.insert(0, '.')

SUMMARY = 'fir_summary.txt'

# Extract GEOCODE_MAPPINGS from fir_specialized_ocr.py
with open('fir_specialized_ocr.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the GEOCODE_MAPPINGS dict
start = content.find('GEOCODE_MAPPINGS = {')
end = content.find('}', start + content[start:].find('"راوی روڈ"')) + 1
mapping_text = content[start:end]

# Extract keys
import ast
# Simpler: just find all quoted strings that are keys
keys = re.findall(r'"([^"]+)":\s*"', mapping_text)
geocode_keys = set(keys)

# Load unique first parts from fir_summary.txt
locations = set()
with open(SUMMARY, 'r', encoding='utf-8') as f:
    lines = f.read().strip().split('\n')

i = 0
while i < len(lines):
    line = lines[i].strip()
    if line.startswith('FIR_') and line.endswith('.png'):
        if i + 1 < len(lines):
            parts = re.split(r'[،,]', lines[i + 1].strip())
            first = parts[0].strip()
            # Remove parenthetical content
            first_clean = re.sub(r'\s*\([^)]+\)', '', first).strip()
            locations.add(first_clean)
            i += 2
        else:
            i += 1
    else:
        i += 1

print(f"Unique locations in fir_summary.txt: {len(locations)}")
print(f"Keys in GEOCODE_MAPPINGS: {len(geocode_keys)}")

# Find missing
missing = locations - geocode_keys
# Also check if structured locations (DHA, Bahria, etc.) need mappings
structured = set()
regular_missing = set()
for loc in missing:
    if any(k in loc for k in ['ڈی ایچ اے', 'بحریہ', 'آسکاری', 'لی ڈی اے', 'واپڈا', 
                                'پی سی ایس', 'پی آئی اے', 'والینشیا', 'جوہر ٹاؤن بلاک',
                                'بحریہ آرچرڈ', 'الخضریا', 'ایڈن آباد']):
        structured.add(loc)
    else:
        regular_missing.add(loc)

print(f"\nMissing regular locations ({len(regular_missing)}):")
for loc in sorted(regular_missing):
    print(f"  '{loc}'")

print(f"\nMissing structured locations ({len(structured)}):")
for loc in sorted(structured):
    print(f"  '{loc}'")

# Show what IS in mappings but also a location  
present = locations & geocode_keys
print(f"\nAlready in GEOCODE_MAPPINGS ({len(present)}):")
for loc in sorted(present):
    print(f"  '{loc}'")
