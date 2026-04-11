import sys
sys.path.insert(0, '.')
from app.core.database import get_db_connection
conn = get_db_connection()
cursor = conn.cursor(dictionary=True)
cursor.execute('SELECT area_name, latitude, longitude FROM areas ORDER BY area_name')
rows = cursor.fetchall()
print(f"Areas table has {len(rows)} rows:")
print(f"{'Area Name':<35} {'Lat':>10}  {'Lng':>10}")
print('-'*60)
for r in rows:
    print(f"{r['area_name']:<35} {float(r['latitude']):>10.4f}  {float(r['longitude']):>10.4f}")
conn.close()
