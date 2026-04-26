"""Quick diagnostic — show what's actually in TiDB right now."""
import os
import sys

import mysql.connector
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.core.config import get_db_config

config = get_db_config()
print(f"Connecting to {config['host']}:{config['port']} as {config['user']}\n")

conn = mysql.connector.connect(**config)
cursor = conn.cursor()

cursor.execute("SHOW TABLES")
tables = [row[0] for row in cursor.fetchall()]
print(f"Total tables in {config['database']}: {len(tables)}")
print(f"Tables: {', '.join(tables)}\n")

if "users_info" in tables:
    print("=== users_info columns ===")
    cursor.execute("DESCRIBE users_info")
    cols = cursor.fetchall()
    print(f"Total columns: {len(cols)}\n")
    for col in cols:
        print(f"  {col[0]:<35} {col[1]}")

    print("\n=== Required columns check ===")
    required = ["is_active", "is_logged_in", "last_login", "last_activity_at",
                "incident_alerts_enabled", "browser_notifications_enabled",
                "home_latitude", "home_longitude", "alert_radius"]
    actual = {col[0] for col in cols}
    for r in required:
        present = "OK " if r in actual else "MISSING"
        print(f"  [{present}] {r}")
else:
    print("WARNING: users_info table does not exist!")

if "crimes" in tables:
    print("\n=== crimes table exists ===")
else:
    print("\nWARNING: crimes table does not exist!")

cursor.close()
conn.close()
