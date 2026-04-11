"""Quick E2E test: extract 2 images -> geocode"""
import sys, os, cv2, importlib, importlib.util
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
os.environ['EASYOCR_DISABLE'] = '1'

spec = importlib.util.spec_from_file_location('fir_mod', 'fir_specialized_ocr.py')
fir_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fir_mod)

IMAGE_DIR = r'F:\FYP\Project\CrimeVision\OCRModel\app\data\raw'

class L:
    pass

e = L()
# Bind all required methods from FIRExtractor
e.extract_crime_area = fir_mod.FIRExtractor.extract_crime_area.__get__(e)
e._clean_crime_area_text = fir_mod.FIRExtractor._clean_crime_area_text.__get__(e)

for name in ['FIR_002.png', 'FIR_015.png']:
    p = os.path.join(IMAGE_DIR, name)
    if not os.path.exists(p):
        print(f'SKIP {name}')
        continue
    img = cv2.imread(p)
    print(f'Processing {name}...')
    area = e.extract_crime_area(img)
    print(f'  area={area}')
    if area:
        geo = fir_mod.geocode_crime_area(area)
        lat = geo.get('latitude')
        lon = geo.get('longitude')
        ok = geo.get('success')
        disp = geo.get('display_name', '')[:80]
        print(f'  lat={lat}, lon={lon}, ok={ok}')
        print(f'  display={disp}')
    else:
        print('  NO AREA EXTRACTED')

print('Done!')
