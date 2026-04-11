"""End-to-end test: send FIR images to the running API and verify all 3 fields."""
import requests
import os
import json

IMAGE_DIR = r'F:\FYP\Project\CrimeVision\OCRModel\app\data\raw'
API_URL = 'http://localhost:8000/api/ocr/extract'

test_files = ['FIR_001.png', 'FIR_050.png', 'FIR_200.png', 'FIR_500.png', 'FIR_900.png']

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
    
    print(f'{fname}:')
    print(f'  Date:     {fields.get("crime_date", "N/A")}')
    print(f'  Area:     {fields.get("crime_area", "N/A")}')
    print(f'  Sections: {fields.get("crime_type", "N/A")}')
    print(f'  Coords:   {loc.get("latitude", "N/A")}, {loc.get("longitude", "N/A")}')
    print(f'  Status:   {data.get("status", "N/A")}')
    print()
