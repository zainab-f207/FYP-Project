
import sys
import os

# Add the backend directory to sys.path
backend_path = os.path.abspath(os.path.join(os.getcwd(), 'backend'))
sys.path.append(backend_path)

# Change cwd to backend
os.chdir(backend_path)

from app.utils.geo import get_coordinates

def test_askari():
    area = "Askari 4"
    print(f"Testing geocoding for: '{area}' (with new Lahore-strict logic)")
    coords = get_coordinates(area)
    print(f"Resolved Coords: {coords}")
    
    if coords:
        lat, lon = coords
        if 31.0 < lat < 32.0:
            print("✅ SUCCESS: Correctly resolved to LAHORE.")
        else:
            print("❌ FAILURE: Still resolving to another city.")
    else:
        print("❌ FAILURE: Geocoding failed.")

if __name__ == "__main__":
    test_askari()
