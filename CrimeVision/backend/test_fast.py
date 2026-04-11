import sys
from app.core.database import get_db_connection
conn=get_db_connection()
c=conn.cursor(dictionary=True)
l=31.4697
lo=74.2818
c.execute('SELECT COUNT(*) as cnt FROM crimes WHERE ST_Distance_Sphere(point(longitude, latitude), point(%s, %s)) <= 2000 AND crime_date >= DATE_SUB(NOW(), INTERVAL 365 DAY)', (lo, l))
print('2km Crimes:', c.fetchone())
