"""
Re-assign the `area` column in the `crimes` table by re-running
the nearest-area lookup against the *current* (fully-populated) `areas` table.

Why this is needed:
  At original import time some areas (e.g. "LDA City") were not yet in the
  `areas` table, so nearest_area_name() fell back to the wrong nearest entry.
  Now that the `areas` table is complete we can correct those assignments.

How it works:
  1. Load every distinct (latitude, longitude) pair from crimes.
  2. For each unique coord pair, find the nearest area in the `areas` table
     using the same Haversine formula used during import.
  3. Batch-update all crimes rows that have that coord pair.

Run with:
  venv\Scripts\python.exe reassign_areas.py
  (add --dry-run to preview changes without writing to DB)
"""
import sys, argparse
sys.path.insert(0, ".")
from app.core.database import get_db_connection

# ── CLI ──────────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument("--dry-run", action="store_true",
                    help="Print changes without writing to DB")
args = parser.parse_args()
DRY_RUN = args.dry_run

# ── Connect ──────────────────────────────────────────────────────────────────
conn = get_db_connection()
cur  = conn.cursor(dictionary=True)

print(f"Mode: {'DRY RUN (no DB changes)' if DRY_RUN else 'LIVE UPDATE'}\n")

# ── Step 1: Load all distinct (lat, lon) pairs from crimes ───────────────────
cur.execute("""
    SELECT DISTINCT latitude, longitude
    FROM crimes
    WHERE latitude IS NOT NULL AND longitude IS NOT NULL
""")
coord_pairs = cur.fetchall()
print(f"Distinct (lat, lon) pairs in crimes table: {len(coord_pairs)}")

# ── Step 2: For each coord, find the nearest area in the areas table ─────────
HAVERSINE_SQL = """
    SELECT area_name,
           (6371 * acos(LEAST(1.0,
               cos(radians(%s)) * cos(radians(latitude))
               * cos(radians(longitude) - radians(%s))
               + sin(radians(%s)) * sin(radians(latitude))
           ))) AS dist_km
    FROM areas
    ORDER BY dist_km ASC
    LIMIT 1
"""

# Build a mapping: (lat, lon) → correct_area_name
coord_to_area: dict = {}
for row in coord_pairs:
    lat, lon = float(row["latitude"]), float(row["longitude"])
    cur.execute(HAVERSINE_SQL, (lat, lon, lat))
    best = cur.fetchone()
    coord_to_area[(lat, lon)] = best["area_name"] if best else "Lahore"

# ── Step 3: Find which crimes have the wrong area ────────────────────────────
cur.execute("""
    SELECT id, latitude, longitude, area, area_translit
    FROM crimes
    WHERE latitude IS NOT NULL AND longitude IS NOT NULL
""")
all_crimes = cur.fetchall()

changes: list[dict] = []
for c in all_crimes:
    lat = float(c["latitude"])
    lon = float(c["longitude"])
    correct = coord_to_area.get((lat, lon), c["area"])
    if correct != c["area"]:
        changes.append({
            "id":       c["id"],
            "old_area": c["area"],
            "new_area": correct,
            "translit": c["area_translit"] or "",
        })

print(f"Rows needing re-assignment: {len(changes)}")

# ── Step 4: Group changes by (old → new) for a summary ──────────────────────
from collections import defaultdict
summary: dict = defaultdict(int)
for ch in changes:
    summary[(ch["old_area"], ch["new_area"])] += ch["id"] and 1

print("\n=== Change summary (old_area → new_area : count) ===")
for (old, new), cnt in sorted(summary.items(), key=lambda x: -x[1]):
    print(f"  {old:<35} → {new:<35}  ({cnt} rows)")

# ── Step 5: Apply updates ────────────────────────────────────────────────────
if not DRY_RUN and changes:
    print("\nApplying updates...")
    batch = [(ch["new_area"], ch["id"]) for ch in changes]
    upd_cur = conn.cursor()
    upd_cur.executemany("UPDATE crimes SET area = %s WHERE id = %s", batch)
    conn.commit()
    print(f"✓ Updated {upd_cur.rowcount} rows.")
    upd_cur.close()

    # Verify a sample
    print("\n=== Verification: area_translit='Lda City%' after update ===")
    cur.execute("""
        SELECT area, COUNT(*) as cnt FROM crimes
        WHERE area_translit LIKE 'Lda City%'
        GROUP BY area ORDER BY cnt DESC
    """)
    for r in cur.fetchall():
        print(f"  area='{r['area']}'  count={r['cnt']}")
elif DRY_RUN:
    print("\n(Dry run — no changes written.)")
else:
    print("\nNo changes needed.")

conn.close()
print("\nDone.")
