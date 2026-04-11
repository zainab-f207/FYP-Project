"""Re-backfill area_translit for all rows using updated keyword map."""
import sys; sys.path.insert(0,'.')

# Force reload of import_fir_data to pick up updated _URDU_KW
import importlib
import import_fir_data
importlib.reload(import_fir_data)
from import_fir_data import azure_transliterate_batch

from app.core.database import get_db_connection
conn = get_db_connection()
cursor = conn.cursor(dictionary=True)

cursor.execute("SELECT id, area_urdu FROM crimes WHERE area_urdu IS NOT NULL AND area_urdu != ''")
rows = cursor.fetchall()
print(f"Backfilling {len(rows)} rows...")

texts = [r['area_urdu'] for r in rows]
translit_map = azure_transliterate_batch(texts)

update_cur = conn.cursor()
for row in rows:
    val = translit_map.get(row['area_urdu'], '')
    if val:
        update_cur.execute("UPDATE crimes SET area_translit=%s WHERE id=%s", (val, row['id']))
conn.commit()
print(f"Done. Updated {len(rows)} rows.")

# Sample check
cursor.execute("""
    SELECT area_urdu, area_translit FROM crimes
    WHERE area_urdu LIKE '%شاہ عالمی%' OR area_urdu LIKE '%مولانا%'
    LIMIT 6
""")
for r in cursor.fetchall():
    print(f"  {str(r['area_urdu'])[:40]:42} → {r['area_translit']}")

update_cur.close(); cursor.close(); conn.close()
