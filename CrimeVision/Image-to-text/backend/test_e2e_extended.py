"""Test more FIR images across the full range to verify consistency."""
import requests
import os

IMAGE_DIR = r'F:\FYP\Project\CrimeVision\OCRModel\app\data\raw'
API_URL = 'http://localhost:8000/api/ocr/extract'

# Test spread across 151-950 range (new entries)
test_files = ['FIR_151.png', 'FIR_300.png', 'FIR_450.png', 'FIR_600.png', 'FIR_750.png', 'FIR_950.png']

results = []
for fname in test_files:
    fpath = os.path.join(IMAGE_DIR, fname)
    if not os.path.exists(fpath):
        print(f'{fname}: FILE NOT FOUND')
        continue
    
    with open(fpath, 'rb') as f:
        files = {'file': (fname, f, 'image/png')}
        r = requests.post(API_URL, files=files, timeout=120)
    
    data = r.json()
    fields = data.get('fields', {})
    loc = fields.get('location', {})
    
    has_date = fields.get('crime_date', '') not in ('', 'Not found', 'N/A')
    has_area = fields.get('crime_area', '') not in ('', 'Not found', 'N/A')
    has_sections = fields.get('crime_type', '') not in ('', 'Not found', 'N/A')
    has_coords = loc.get('latitude') is not None
    
    status = 'ALL OK' if all([has_date, has_area, has_sections, has_coords]) else 'MISSING'
    results.append((fname, status))
    
    print(f'{fname}: [{status}]')
    print(f'  Date:     {fields.get("crime_date", "N/A")}')
    print(f'  Area:     {fields.get("crime_area", "N/A")}')
    print(f'  Sections: {fields.get("crime_type", "N/A")}')
    print(f'  Coords:   {loc.get("latitude", "N/A")}, {loc.get("longitude", "N/A")}')
    print()

ok = sum(1 for _, s in results if s == 'ALL OK')
print(f'\nTotal: {ok}/{len(results)} images have all 3 fields + coordinates')
