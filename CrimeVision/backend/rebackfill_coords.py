"""
rebackfill_coords.py
────────────────────
Re-geocodes existing crimes in the DB using the improved Nominatim logic
(comma-formatted queries + specificity scoring + Lahore viewbox).

Only unique area_urdu values are geocoded (cached), so API calls ≈ number of
distinct street addresses — typically a few hundred, completed in ~10 minutes.

Usage:
    python rebackfill_coords.py [--dry-run] [--limit N]

Options:
    --dry-run   Show what would change without updating the DB.
    --limit N   Only process N unique areas (for testing).
"""

import sys
import os
import argparse
import time

# Allow imports from the app package
sys.path.insert(0, os.path.dirname(__file__))

# Import app DB connection (reads config/.env automatically)
from app.core.database import get_db_connection

# Import improved geocoding from the updated import_fir_data module
from import_fir_data import geocode_area, _load_areas_dict


def dict_cursor(conn):
    """Return a cursor that yields rows as dicts."""
    return conn.cursor(dictionary=True)


def main():
    parser = argparse.ArgumentParser(description="Re-geocode crimes with improved Nominatim logic")
    parser.add_argument("--dry-run", action="store_true", help="Print changes without updating DB")
    parser.add_argument("--limit", type=int, default=0, help="Max unique areas to process (0 = all)")
    args = parser.parse_args()

    conn = get_db_connection()
    try:
        with dict_cursor(conn) as cur:
            # Pre-load areas table into the geocoding text-match fallback dict
            _load_areas_dict(cur)

            # Fetch all distinct area_urdu values that have associated crime rows
            cur.execute("""
                SELECT area_urdu, COUNT(*) AS cnt
                FROM crimes
                WHERE area_urdu IS NOT NULL AND area_urdu != ''
                GROUP BY area_urdu
                ORDER BY cnt DESC
            """)
            rows = cur.fetchall()

        unique_areas = [(r["area_urdu"], r["cnt"]) for r in rows]
        if args.limit:
            unique_areas = unique_areas[:args.limit]

        print(f"\n{'DRY-RUN — ' if args.dry_run else ''}Processing {len(unique_areas)} unique area_urdu values …\n")

        updated_areas = 0
        updated_rows  = 0

        with dict_cursor(conn) as cur:
            for idx, (area_urdu, crime_count) in enumerate(unique_areas, 1):
                new_lat, new_lon = geocode_area(area_urdu)

                # Fetch current coordinates for this area (use first matching row)
                cur.execute(
                    "SELECT latitude, longitude FROM crimes WHERE area_urdu = %s LIMIT 1",
                    (area_urdu,)
                )
                existing = cur.fetchone()
                if not existing:
                    continue

                old_lat = float(existing["latitude"] or 0)
                old_lon = float(existing["longitude"] or 0)

                # Skip if coordinates haven't changed meaningfully (within 5 m)
                diff = ((new_lat - old_lat) ** 2 + (new_lon - old_lon) ** 2) ** 0.5
                if diff < 0.00005:  # ~5 m threshold
                    print(f"  [{idx}/{len(unique_areas)}] SKIP  {area_urdu[:55]!r:<58} "
                          f"(unchanged {old_lat:.5f},{old_lon:.5f})")
                    continue

                print(f"  [{idx}/{len(unique_areas)}] UPDATE {area_urdu[:55]!r:<58} "
                      f"{crime_count:>4} rows  "
                      f"({old_lat:.5f},{old_lon:.5f}) → ({new_lat:.5f},{new_lon:.5f})")

                if not args.dry_run:
                    cur.execute(
                        "UPDATE crimes SET latitude = %s, longitude = %s WHERE area_urdu = %s",
                        (new_lat, new_lon, area_urdu)
                    )
                    conn.commit()

                updated_areas += 1
                updated_rows  += crime_count

        print(f"\n{'[DRY-RUN] Would update' if args.dry_run else 'Updated'} "
              f"{updated_areas} unique areas → {updated_rows} crime rows.\n")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
