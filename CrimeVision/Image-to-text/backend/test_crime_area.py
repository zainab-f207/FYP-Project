"""Test crime area extraction from FIR images"""
import cv2
import logging
import sys

logging.basicConfig(level=logging.INFO)

from fir_specialized_ocr import FIRDataExtractor

# Get image path from args or default
image_path = sys.argv[1] if len(sys.argv) > 1 else 'test_images/FIR_001.jpg'

# Load test image
img = cv2.imread(image_path)
if img is None:
    print(f"ERROR: Could not load {image_path}")
    sys.exit(1)

print(f"Image: {image_path}")
print(f"Size: {img.shape[1]}x{img.shape[0]}")

# Create extractor with debug mode
extractor = FIRDataExtractor(debug_mode=True)

# Extract all fields  
print("\nExtracting fields...")
data = extractor.extract_all_fields(img)

print("\n" + "="*60)
print("RESULT:")
print(f"Crime Area: {data.get('crime_area', 'NOT FOUND')}")
print(f"Thana: {data.get('thana', 'NOT FOUND')}")
print(f"Crime Date: {data.get('crime_date', 'NOT FOUND')}")
print("="*60)

# Keep original function for compatibility
def test_extraction(image_path: str):
    img = cv2.imread(image_path)
    extractor = FIRDataExtractor()
    return extractor.extract_all_fields(img)
    if loc['mappable']:
        source = loc.get('source', 'unknown')
        name_source = loc.get('name_source', 'ocr')
        
        if source == 'nominatim_api':
            print(f"✅ REAL COORDINATES FROM OPENSTREETMAP API")
            if name_source == 'ps_code_mapping':
                print(f"   (Area name from PS code {result['police_station_code']} mapping)")
        else:
            print(f"⚠️  Source: {source}")
        
        print(f"   Thana Name: {loc['thana_name']}")
        print(f"   Latitude:   {loc['latitude']}  ← REAL from API")
        print(f"   Longitude:  {loc['longitude']}  ← REAL from API")
        
        if loc.get('display_name'):
            print(f"\n   📍 Full Address (from OpenStreetMap):")
            print(f"   {loc['display_name']}")
        
        print(f"\n   🔗 OpenStreetMap URL:")
        print(f"   https://www.openstreetmap.org/?mlat={loc['latitude']}&mlon={loc['longitude']}&zoom=15")
    else:
        print(f"❌ COULD NOT GET REAL COORDINATES")
        print(f"   OCR extracted: '{result.get('thana_ocr', 'N/A')}'")
        print(f"   PS Code: '{result['police_station_code']}'")
        print(f"   No fallback used - coordinates must come from API")
    
    print("\n" + "=" * 60)
    
    return result


def test_geocoding_direct(area_name: str):
    """Test the geocoding function directly with an area name"""
    print("\n" + "=" * 60)
    print(f"🌐 DIRECT GEOCODING TEST: '{area_name}'")
    print("=" * 60)
    
    result = RealTimeGeocoder.geocode(area_name, city="Lahore", country="Pakistan")
    
    if result['success']:
        print(f"✅ SUCCESS!")
        print(f"   Area: {result['area_name']}")
        print(f"   Latitude:  {result['latitude']}")
        print(f"   Longitude: {result['longitude']}")
        print(f"   Source: {result['source']}")
        print(f"\n   Full Address:")
        print(f"   {result['display_name']}")
        print(f"\n   🔗 https://www.openstreetmap.org/?mlat={result['latitude']}&mlon={result['longitude']}&zoom=15")
    else:
        print(f"❌ FAILED to geocode '{area_name}'")
    
    return result


def show_all_stations():
    """Display all police stations in the fallback database"""
    print("\n" + "=" * 60)
    print("📍 FALLBACK DATABASE (used only if API fails)")
    print("=" * 60)
    
    for code, (name, lat, lon) in sorted(LAHORE_POLICE_STATIONS.items()):
        print(f"  {code}: {name:20s} ({lat:.4f}, {lon:.4f})")


if __name__ == "__main__":
    # Test with your FIR image
    if len(sys.argv) > 1:
        # Check if it's a direct geocoding test (--geocode at START)
        if sys.argv[1] == "--geocode" and len(sys.argv) > 2:
            area_name = " ".join(sys.argv[2:])
            test_geocoding_direct(area_name)
        else:
            # Extract image path (ignore --geocode flag if present anywhere)
            image_path = None
            for arg in sys.argv[1:]:
                if arg != "--geocode" and not arg.startswith("--"):
                    image_path = arg
                    break
            
            if image_path:
                result = test_extraction(image_path)
            else:
                print("❌ No image path provided")
                print("Usage: python test_crime_area.py <path_to_fir_image>")
                sys.exit(1)
    else:
        # Default - look for test images
        test_paths = [
            "test_fir.png",
            "test_fir.jpg",
            "sample_fir.png",
            "backend/test_fir.png",
        ]
        image_path = None
        for p in test_paths:
            if os.path.exists(p):
                image_path = p
                break
        
        if not image_path:
            print("Usage:")
            print("  python test_crime_area.py <path_to_fir_image>")
            print("  python test_crime_area.py --geocode <area_name>")
            print("\nExamples:")
            print("  python test_crime_area.py my_fir.png")
            print("  python test_crime_area.py --geocode Gulberg")
            print("  python test_crime_area.py --geocode Model Town")
            print("\n" + "-" * 40)
            print("Testing direct geocoding with 'Model Town'...")
            test_geocoding_direct("Model Town")
            print("\n" + "-" * 40)
            print("Testing direct geocoding with 'Gulberg'...")
            test_geocoding_direct("Gulberg")
            sys.exit(0)
        
        result = test_extraction(image_path)
