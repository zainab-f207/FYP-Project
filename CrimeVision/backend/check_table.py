import sys
sys.path.append('.')
from app.core.database import get_db_connection

try:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DESCRIBE users_info')
    result = cursor.fetchall()
    print('Table structure:')
    for row in result:
        print(row)
    cursor.close()
    conn.close()
except Exception as e:
    print(f"Error: {e}")
