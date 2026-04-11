"""Extract unique locations from fir_summary.txt for dictionary expansion."""
import sys
sys.stdout = open('CON', 'w', encoding='utf-8')

entries = {}
with open('fir_summary.txt', 'r', encoding='utf-8') as f:
    lines = f.read().strip().split('\n')

i = 0
while i < len(lines):
    line = lines[i].strip()
    if line.startswith('FIR_') and line.endswith('.png'):
        fname = line
        i += 1
        while i < len(lines) and not lines[i].strip():
            i += 1
        if i < len(lines) and not lines[i].strip().startswith('FIR_'):
            area = lines[i].strip()
            entries[fname] = area
        continue
    i += 1

first_fields = set()
roads = set()
thanas = set()
for fname, area in sorted(entries.items()):
    parts = [p.strip() for p in area.split('\u060c')]  # Urdu comma
    if len(parts) >= 1:
        first_fields.add(parts[0])
    if len(parts) >= 2:
        roads.add(parts[1])
    if len(parts) >= 3:
        thanas.add(parts[2])

print(f"Total entries: {len(entries)}")
print(f"Unique locations: {len(first_fields)}")
print(f"Unique roads: {len(roads)}")
print(f"Unique thanas: {len(thanas)}")
print()
print("=== UNIQUE LOCATIONS (first field) ===")
for loc in sorted(first_fields):
    print(f'    "{loc}",')
print()
print("=== UNIQUE ROADS ===")
for r in sorted(roads):
    print(f'    "{r}",')
print()
print("=== UNIQUE THANAS/AREAS ===")
for t in sorted(thanas):
    print(f'    "{t}",')
