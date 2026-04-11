import mysql.connector
import os
import sys

# Add current directory to path to import app modules
sys.path.append(os.getcwd())

# Hardcoded defaults based on app/core/config.py
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "hafsa555",
    "database": "crimevision_db",
    "port": 3306
}

def run_migration():
    print("Starting migration...")
    try:
        # Try to connect
        print(f"Connecting to {DB_CONFIG['host']} as {DB_CONFIG['user']}...")
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        print(f"Connected to database: {DB_CONFIG['database']}")
        
        with open('db_migrations_admin_reports.sql', 'r') as f:
            sql_script = f.read()
            
        # Split by semicolon to execute multiple statements
        statements = sql_script.split(';')
        
        for statement in statements:
            if statement.strip():
                try:
                    cursor.execute(statement)
                    print(f"Executed: {statement.strip()[:50]}...")
                except Exception as e:
                    print(f"Error executing statement: {e}")
                    
        conn.commit()
        print("Migration completed successfully!")
        
    except Exception as e:
        print(f"Migration failed: {e}")

if __name__ == "__main__":
    run_migration()
