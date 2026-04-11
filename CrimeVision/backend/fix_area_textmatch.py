"""
Text-match post-correction: fix crimes whose area_translit clearly names a
specific area but the geocoding placed them in the wrong location.

This targets cases where nearest_area_name() gives a wrong result because
Nominatim geocoding of the Urdu address returned incorrect coordinates.

Known affected cases discovered in analysis:
  - area_translit LIKE '%Lake City%'  → should be 'Lake City'
"""
import sys
sys.path.insert(0, ".")
from app.core.database import get_db_connection

conn = get_db_connection()
cur  = conn.cursor(dictionary=True)

# Text-based area name fixes: (area_translit_pattern, correct_area_name)
TEXT_FIXES = [
    ("%Lake City%",             "Lake City"),
    ("%Bahria Orchard%",        "Bahria Orchard"),
    ("%Green Town%",            "Green Town"),
    ("%Pak Arab%",              "Pak Arab Housing Society"),
    ("%Sukh Chayn%",            "Sukh Chayn Gardens"),
    ("%Raiwind%",               "Raiwind Road"),
    ("%Sundar%",                "Sundar"),
    ("%Shalimar Housing%",      "Shalimar Housing Society"),
    ("%Nishtar Colony%",        "Nishtar Colony"),
    ("%Nishtar Town%",          "Nishtar Town, Lahore"),
    ("%Shalimar Town%",         "Shalimar Town, Lahore"),
    ("%Pcsir%",                 "PCSIR Housing Scheme"),
    ("%Valencia%",              "Valencia Housing Society"),
    ("%Wapda Town%",            "Wapda Town"),
    ("%Pia Housing%",           "PIA Housing Society"),
    ("%Johar Town%",            "Johar Town"),
    ("%Gulbarg%",               "Gulberg"),
]

total_fixed = 0
for (pattern, correct_area) in TEXT_FIXES:
    # Count how many need fixing
    cur.execute(
        "SELECT COUNT(*) AS cnt FROM crimes WHERE area_translit LIKE %s AND area != %s",
        (pattern, correct_area),
    )
    cnt = cur.fetchone()["cnt"]
    if cnt == 0:
        print(f"  [OK]  '{pattern}' → already all in '{correct_area}'")
        continue

    # Preview which old areas these come from
    cur.execute(
        "SELECT area, COUNT(*) AS n FROM crimes WHERE area_translit LIKE %s AND area != %s GROUP BY area ORDER BY n DESC",
        (pattern, correct_area),
    )
    froms = cur.fetchall()
    print(f"  FIXING {cnt:4d} rows  '{pattern}' → '{correct_area}'")
    for f in froms:
        print(f"         from area='{f['area']}' ({f['n']} rows)")

    # Apply
    upd = conn.cursor()
    upd.execute(
        "UPDATE crimes SET area = %s WHERE area_translit LIKE %s AND area != %s",
        (correct_area, pattern, correct_area),
    )
    conn.commit()
    total_fixed += cnt
    upd.close()

print(f"\n✓ Text-match corrections applied: {total_fixed} rows total")
conn.close()
print("Done.")
