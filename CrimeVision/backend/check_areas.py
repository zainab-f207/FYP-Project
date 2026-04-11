import sys
sys.path.insert(0, '.')
from app.core.database import get_db_connection
conn = get_db_connection()
cursor = conn.cursor(dictionary=True)
cursor.execute('''
    SELECT area,
           COUNT(*) as crime_count,
           SUM(CASE WHEN latitude IS NULL OR longitude IS NULL THEN 1 ELSE 0 END) as null_coords,
           MAX(latitude) as lat, MAX(longitude) as lng
    FROM crimes
    GROUP BY area
    ORDER BY crime_count DESC
''')
rows = cursor.fetchall()
print(f"{'Area':<35} {'Count':>6}  {'NullCoords':>10}  {'Lat':>10}  {'Lng':>10}")
print('-'*80)
total = 0
total_null = 0
for r in rows:
    total += r['crime_count']
    total_null += r['null_coords']
    lat = f"{r['lat']:.4f}" if r['lat'] else 'NULL'
    lng = f"{r['lng']:.4f}" if r['lng'] else 'NULL'
    print(f"{str(r['area']):<35} {r['crime_count']:>6}  {r['null_coords']:>10}  {lat:>10}  {lng:>10}")
print(f"\nTotal crimes: {total}  |  Total NULL coords: {total_null}")
conn.close()
