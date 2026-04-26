import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "crimevision_db"),
    "port": int(os.getenv("DB_PORT", "3306")),
}

def run_community_migrations():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # Read the SQL file
        with open(os.path.join(os.path.dirname(__file__), 'db_migrations_community.sql'), 'r') as file:
            sql_script = file.read()

        # Split into individual statements
        statements = [stmt.strip() for stmt in sql_script.split(';') if stmt.strip()]

        for statement in statements:
            if statement:
                try:
                    cursor.execute(statement)
                    print(f"Executed: {statement[:50]}...")
                except Error as e:
                    print(f"Error executing statement: {e}")
                    # Continue with next statement

        conn.commit()
        print("Community migrations completed successfully")

    except Error as e:
        print(f"Database error: {e}")
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals() and conn.is_connected():
            conn.close()

if __name__ == "__main__":
    run_community_migrations()
