"""
Test two approaches:
1. Nominatim reverse with accept-language=en (force English from OSM)
2. indic-transliteration library (local, converts Urdu script → Roman)
"""
import requests, time, subprocess, sys

# ---------- Test 1: Nominatim with accept-language: en ----------
REVERSE_URL = "https://nominatim.openstreetmap.org/reverse"
HEADERS_EN = {
    "User-Agent": "CrimeVision-FIR-Importer/1.0 (Educational Research Project)",
    "accept-language": "en",
}

def reverse_en(lat, lon, zoom=14):
    params = {"lat": lat, "lon": lon, "format": "json", "zoom": zoom, "addressdetails": 1}
    r = requests.get(REVERSE_URL, params=params, headers=HEADERS_EN, timeout=10)
    return r.json() if r.ok else {}

test_points = [
    ("Maulana Shaukat Ali Rd (Gulberg zone)", 31.5245, 74.3492),
    ("Thokar/Gajumatta area",                31.4280, 74.2760),
    ("DHA Phase 6",                          31.4791, 74.4511),
    ("Bahria Town",                          31.3909, 74.1824),
    ("Gulshan-e-Ravi",                       31.5720, 74.2906),
    ("Lahore Cantt",                         31.5649, 74.3920),
]

print("=" * 80)
print("APPROACH 1: Nominatim Reverse with accept-language: en")
print("=" * 80)
for label, lat, lon in test_points:
    d = reverse_en(lat, lon)
    a = d.get("address", {})
    suburb    = a.get("suburb", "")
    neighbour = a.get("neighbourhood", "")
    district  = a.get("city_district", "")
    road      = a.get("road", "")
    display   = d.get("display_name", "")[:70]
    best = next((v for v in [neighbour, suburb, district] if v), display.split(",")[0])
    print(f"\n  {label}")
    print(f"    neighbourhood: {neighbour!r}")
    print(f"    suburb:        {suburb!r}")
    print(f"    city_district: {district!r}")
    print(f"    road:          {road!r}")
    print(f"    display:       {display!r}")
    print(f"    → BEST:        {best!r}")
    time.sleep(1.1)

# ---------- Test 2: indic-transliteration ----------
print()
print("=" * 80)
print("APPROACH 2: indic-transliteration library (local, free forever)")
print("=" * 80)
try:
    from indic_transliteration import sanscript
    from indic_transliteration.sanscript import transliterate

    urdu_samples = [
        "مولانا شوکت علی روڈ",
        "گجومتہ موڑ سب بلاک B",
        "ٹھوکر نیاز بیگ انٹرچینج",
        "ڈی ایچ اے فیز 6 بلاک J",
        "بحریہ ٹاؤن سیکٹر G",
        "گلشنِ راوی بلاک K",
        "جوہر ٹاؤن بلاک C",
    ]
    for urdu in urdu_samples:
        roman = transliterate(urdu, sanscript.SHAHMUKHI, sanscript.IAST)
        print(f"  {urdu:<35} → {roman!r}")
except ImportError:
    print("  indic-transliteration NOT installed. Installing...")
    subprocess.run([sys.executable, "-m", "pip", "install", "indic-transliteration"], check=True)
    print("  Installed. Re-run the script.")
