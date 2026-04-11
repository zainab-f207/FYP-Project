import sys
sys.path.append('.')
from app.core.database import get_db_connection
conn=get_db_connection()
c=conn.cursor(dictionary=True)
c.execute('SELECT COUNT(*) as c FROM crimes WHERE area LIKE "%Johar%" AND latitude IS NOT NULL')
print('Johar Crimes with Lat:', c.fetchone())
c.execute('SELECT latitude, longitude FROM crimes WHERE area LIKE "%Johar%" LIMIT 5')
print('Sample Lat/Lng:', c.fetchall())
