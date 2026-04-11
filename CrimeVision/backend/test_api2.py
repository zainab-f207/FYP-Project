import sys
from app.core.database import get_db_connection
from app.utils.risk import calculate_safety_score
conn=get_db_connection()
c=conn.cursor(dictionary=True)
l=31.4697
lo=74.2818
c.execute('''SELECT SUM(CASE WHEN HOUR(crime_time) BETWEEN 6 AND 18 THEN 1 ELSE 0 END) as day_crimes, SUM(CASE WHEN HOUR(crime_time) NOT BETWEEN 6 AND 18 THEN 1 ELSE 0 END) as night_crimes FROM crimes WHERE ST_Distance_Sphere(point(longitude, latitude), point(%s, %s)) <= 5000 AND crime_date >= DATE_SUB(NOW(), INTERVAL 365 DAY)''', (lo, l))
print('Time stats:', c.fetchone())
