"""
Test Nominatim reverse geocoding for Lahore coordinates.
This is completely free and has no API key requirement.
"""
import requests, time, json

REVERSE_URL = "https://nominatim.openstreetmap.org/reverse"
HEADERS = {"User-Agent": "CrimeVision-FIR-Importer/1.0 (Educational Research Project)"}

def reverse_geocode(lat, lon):
    """Call Nominatim reverse geocoding, return address dict."""
    params = {
        "lat": lat,
        "lon": lon,
        "format": "json",
        "zoom": 16,           # neighbourhood level (14=suburb, 16=road, 18=building)
        "addressdetails": 1,
    }
    resp = requests.get(REVERSE_URL, params=params, headers=HEADERS, timeout=10)
    if resp.status_code == 200:
        return resp.json()
    return {}

def best_area_name(addr: dict) -> str:
    """
    Extract the best human-readable English area label from a Nominatim
    reverse-geocode address dict.

    Priority order:
      neighbourhood > suburb > quarter > city_district > city
    """
    a = addr.get("address", {})
    for key in ("neighbourhood", "suburb", "quarter", "city_district", "county", "city"):
        val = a.get(key)
        if val:
            return val
    return addr.get("display_name", "").split(",")[0].strip()

# Test coordinates
test_points = [
    ("Gulberg / Maulana Shaukat Ali Rd area",   31.5245, 74.3492),
    ("DHA Phase 6",                              31.4791, 74.4511),
    ("Bahria Town Lahore",                       31.3909, 74.1824),
    ("Wapda Town",                               31.4369, 74.2819),
    ("Gulshan-e-Ravi",                           31.5720, 74.2906),
    ("Lahore Cantonment",                        31.5649, 74.3920),
    ("Johar Town",                               31.4809, 74.2805),
    ("Thokar Niaz Baig / Gajumatta area",        31.4280, 74.2760),
    ("DHA Phase 3",                              31.4867, 74.3818),
    ("Shadman",                                  31.5466, 74.3316),
]

print(f"{'Label':<38} {'Lat':>8}  {'Lng':>8}  {'suburb/neighbourhood'}")
print("-"*95)
for label, lat, lon in test_points:
    data = reverse_geocode(lat, lon)
    area = best_area_name(data)
    addr = data.get("address", {})
    suburb    = addr.get("suburb", "-")
    neighbour = addr.get("neighbourhood", "-")
    quarter   = addr.get("quarter", "-")
    road      = addr.get("road", "-")
    print(f"{label:<38} {lat:>8.4f}  {lon:>8.4f}  neighbourhood={neighbour!r:25}  suburb={suburb!r:30}  road={road!r}")
    print(f"  → best_area_name: {area!r}")
    print()
    time.sleep(1.1)
