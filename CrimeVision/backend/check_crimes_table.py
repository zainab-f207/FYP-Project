import sys
sys.path.append('.')
from app.core.database import get_db_connection

try:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DESCRIBE crimes')
    result = cursor.fetchall()
    print('Crimes table structure:')
    for row in result:
        print(row)

    # Also check if there's any data
    cursor.execute('SELECT COUNT(*) FROM crimes')
    count = cursor.fetchone()
    print(f'Total records in crimes table: {count[0]}')

    cursor.close()
    conn.close()
except Exception as e:
    print(f"Error: {e}")
