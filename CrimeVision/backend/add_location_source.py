import sys
import os
sys.path.append(os.path.dirname(__file__))

from app.core.database import get_db_connection

def add_location_source_columns():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Add the missing location_source column to user_location_history table
    try:
        cursor.execute('ALTER TABLE user_location_history ADD COLUMN location_source VARCHAR(20) DEFAULT "gps"')
        print('✅ Added location_source column to user_location_history table')
        conn.commit()
    except Exception as e:
        print(f'⚠️ Error adding location_source column to user_location_history: {e}')
        conn.rollback()

    # Add the missing location_source column to users_info table
    try:
        cursor.execute('ALTER TABLE users_info ADD COLUMN location_source VARCHAR(20) DEFAULT "gps"')
        print('✅ Added location_source column to users_info table')
        conn.commit()
    except Exception as e:
        print(f'⚠️ Error adding location_source column to users_info: {e}')
        conn.rollback()

    cursor.close()
    conn.close()
    print('Database schema update completed')

if __name__ == "__main__":
    add_location_source_columns()
