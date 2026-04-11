"""
Seed missing major housing societies into the areas table.

These are neighbourhoods that appear in FIR data but were absent from the areas
table, causing geocode_area() to fall back to Nominatim with street-level noise
(e.g. "Cantt Road") that can pull coordinates to the wrong part of Lahore.

Run once:
    python seed_missing_societies.py
"""

import os, sys
sys.path.insert(0, os.path.dirname(__file__))

from app.core.database import get_db_connection

# (name, latitude, longitude, zone/district)
# Coordinates verified against Google Maps / OSM for South-LDA / North / East Lahore areas.
SOCIETIES = [
    # South Lahore
    ("LDA City",               31.3630, 74.3310, "South"),
    ("LDA Avenue",             31.3920, 74.2950, "South"),
    ("Paragon City",           31.4000, 74.3560, "South"),
    ("Pak Arab Housing Society", 31.4320, 74.2750, "South"),

    # West / Central
    ("PIA Housing Society",    31.4800, 74.2660, "West"),
    ("PCSIR Housing Scheme",   31.4940, 74.3400, "West"),
    ("Shalimar Housing Society", 31.4100, 74.3300, "Central"),

    # North Lahore
    ("Valencia Housing Society", 31.5340, 74.4380, "North"),
    ("Lake City",              31.6170, 74.4560, "North"),
    ("Raiwind Road",           31.3750, 74.3200, "South"),

    # Cantonment / East
    ("Askari 10",              31.5620, 74.4250, "Cantt"),
    ("Askari 11",              31.4200, 74.2400, "Cantt"),
    ("Askari 8",               31.5060, 74.3840, "Cantt"),

    # Others reported in FIR data
    ("Sukh Chayn Gardens",     31.4320, 74.3500, "Central"),
    ("Township",               31.4700, 74.2850, "West"),
    ("Nishtar Colony",         31.5100, 74.3760, "Central"),
    ("Ferozepur Road",         31.4500, 74.3080, "Central"),
    ("Kahna",                  31.3570, 74.3320, "South"),
    ("Sundar",                 31.3390, 74.4330, "South"),
    ("Manga Mandi",            31.3180, 74.4050, "South"),
]

def main():
    conn = get_db_connection()
    cursor = conn.cursor()

    inserted = 0
    skipped  = 0

    for name, lat, lon, zone in SOCIETIES:
        # Check if already present (case-insensitive)
        cursor.execute(
            "SELECT area_name FROM areas WHERE LOWER(area_name) = LOWER(%s) LIMIT 1", (name,)
        )
        if cursor.fetchone():
            print(f"  SKIP  {name!r}  (already exists)")
            skipped += 1
            continue

        cursor.execute(
            "INSERT INTO areas (area_name, latitude, longitude) VALUES (%s, %s, %s)",
            (name, lat, lon),
        )
        print(f"  INSERT {name!r}  ({lat}, {lon})")
        inserted += 1

    conn.commit()
    cursor.close()
    conn.close()
    print(f"\nDone: {inserted} inserted, {skipped} skipped.")


if __name__ == "__main__":
    main()
