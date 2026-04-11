import os
from app.core.database import get_db_connection

def check_recent_crimes(days=90):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT COUNT(*) as recent FROM crimes WHERE crime_date >= DATE_SUB(NOW(), INTERVAL %s DAY)", (days,))
        result = cursor.fetchone()
        print(f"Crimes in last {days} days: {result['recent']}")
    except Exception as e:
        print('Error:', e)
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    check_recent_crimes(90)
