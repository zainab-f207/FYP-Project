import sys
from app.core.database import get_db_connection
conn = get_db_connection()
cursor = conn.cursor(dictionary=True)
cursor.execute('''SELECT COUNT(*) as total_crimes, SUM(CASE WHEN risk_level = 'High' THEN 1 ELSE 0 END) as high_risk_count FROM crimes WHERE ST_Distance_Sphere(point(longitude, latitude), point(74.2818, 31.4697)) <= 2000 AND crime_date >= '2025-03-17' ''' )
print('Radius last year:', cursor.fetchone())
cursor.execute('''SELECT COUNT(*) FROM crimes WHERE area LIKE '%Johar%' AND crime_date >= '2025-03-17' ''')
print('Area last year:', cursor.fetchone())
