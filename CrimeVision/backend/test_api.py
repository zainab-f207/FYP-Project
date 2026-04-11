import sys
from app.core.database import get_db_connection
conn = get_db_connection()
cursor = conn.cursor(dictionary=True)
cursor.execute('DESCRIBE crimes')
print(cursor.fetchall())
