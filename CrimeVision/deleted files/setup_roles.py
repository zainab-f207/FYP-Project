import mysql.connector
from mysql.connector import Error
import sys
import os
from dotenv import load_dotenv

load_dotenv()

sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))
from auth_updated import get_password_hash

# Database config
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "crimevision_db"),
    "port": int(os.getenv("DB_PORT", "3306")),
}

def setup_roles():
    """Add role column to users_info table and create SuperAdmin"""
    conn = None
    cursor = None
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # Check if role column exists, if not add it
        cursor.execute("SHOW COLUMNS FROM users_info LIKE 'role'")
        if not cursor.fetchone():
            cursor.execute("""
                ALTER TABLE users_info
                ADD COLUMN role ENUM('user', 'admin', 'superadmin') NOT NULL DEFAULT 'user' AFTER email
            """)
            print("Role column added to users_info table")
        else:
            print("Role column already exists")

        # Check if SuperAdmin exists
        cursor.execute("SELECT id FROM users_info WHERE username = 'superadmin'")
        if not cursor.fetchone():
            # Create SuperAdmin with fixed credentials
            password_hash = get_password_hash("SuperAdmin123!")
            cursor.execute("""
                INSERT INTO users_info (username, first_name, last_name, email, password_hash, role)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, ("superadmin", "Super", "Admin", "superadmin@safevision.com", password_hash, "superadmin"))
            print("SuperAdmin created with username: superadmin, password: SuperAdmin123!")
        else:
            print("SuperAdmin already exists")

        conn.commit()

    except Error as e:
        print(f"Database error: {e}")
        if conn:
            conn.rollback()
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

if __name__ == "__main__":
    setup_roles()
