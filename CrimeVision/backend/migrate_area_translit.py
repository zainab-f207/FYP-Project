"""
Add area_translit column to crimes table and backfill all existing rows.
Uses Azure Translator if AZURE_TRANSLATOR_KEY is set, otherwise uses
the keyword-substitution fallback.

Usage:
    python migrate_area_translit.py

With Azure key (for proper Roman transliteration):
    set AZURE_TRANSLATOR_KEY=your_key_here
    python migrate_area_translit.py
"""
import sys
import os
sys.path.insert(0, '.')

from app.core.database import get_db_connection

def run():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # 1. Add column if missing
    cursor.execute("SHOW COLUMNS FROM crimes LIKE 'area_translit'")
    if not cursor.fetchone():
        print("Adding area_translit column...")
        cursor.execute(
            "ALTER TABLE crimes ADD COLUMN area_translit VARCHAR(500) DEFAULT NULL AFTER area_urdu"
        )
        conn.commit()
        print("  ✓ area_translit column added")
    else:
        print("area_translit column already exists")

    # 2. Fetch all rows that have area_urdu but area_translit is NULL
    cursor.execute("""
        SELECT id, area_urdu
        FROM crimes
        WHERE area_urdu IS NOT NULL
          AND area_urdu != ''
          AND (area_translit IS NULL OR area_translit = '')
    """)
    rows = cursor.fetchall()
    print(f"Rows needing transliteration: {len(rows)}")

    if not rows:
        print("Nothing to do.")
        conn.close()
        return

    # 3. Import transliteration (batch Azure or keyword fallback)
    from import_fir_data import azure_transliterate_batch

    urdu_texts = [r['area_urdu'] for r in rows]
    print(f"Transliterating {len(set(urdu_texts))} unique Urdu strings...")
    translit_map = azure_transliterate_batch(urdu_texts)

    # 4. Batch UPDATE
    update_cursor = conn.cursor()
    updated = 0
    for row in rows:
        translit = translit_map.get(row['area_urdu'], '')
        if translit:
            update_cursor.execute(
                "UPDATE crimes SET area_translit = %s WHERE id = %s",
                (translit, row['id'])
            )
            updated += 1

    conn.commit()
    print(f"✓ Updated {updated} rows with area_translit")

    # 5. Verify
    cursor.execute("SELECT COUNT(*) as n FROM crimes WHERE area_translit IS NOT NULL")
    r = cursor.fetchone()
    print(f"Total rows with area_translit: {r['n']}")

    # Show sample
    cursor.execute("""
        SELECT area_urdu, area_translit
        FROM crimes
        WHERE area_translit IS NOT NULL
        LIMIT 10
    """)
    print("\nSample transliterations:")
    for r in cursor.fetchall():
        print(f"  {str(r['area_urdu'])[:40]:42} → {r['area_translit']}")

    update_cursor.close()
    cursor.close()
    conn.close()

if __name__ == '__main__':
    run()
