import sys
sys.path.append('.')
from app.core.database import get_db_connection
conn=get_db_connection()
c=conn.cursor(dictionary=True)
c.execute('SELECT MIN(crime_date), MAX(crime_date) FROM crimes')
print('Dates:', c.fetchone())
