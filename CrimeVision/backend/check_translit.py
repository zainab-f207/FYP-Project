import sys; sys.path.insert(0,'.')
from app.core.database import get_db_connection
conn = get_db_connection()
cursor = conn.cursor(dictionary=True)
cursor.execute("SELECT COUNT(*) as total, SUM(area_translit IS NOT NULL) as has_translit FROM crimes")
r = cursor.fetchone()
print(f"Total rows: {r['total']} | with area_translit: {r['has_translit']}")
cursor.execute("""
    SELECT area_urdu, area_translit, area
    FROM crimes
    WHERE area_translit IS NOT NULL
    GROUP BY area_urdu, area_translit, area
    LIMIT 15
""")
print("\nSample (urdu → translit → zone):")
for r in cursor.fetchall():
    print(f"  {str(r['area_urdu'])[:40]:42} → {str(r['area_translit'])[:40]:42} [{r['area']}]")
conn.close()
