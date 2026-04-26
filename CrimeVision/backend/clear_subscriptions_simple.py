import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv()


def clear_subscriptions():
    try:
        conn = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            database=os.getenv('DB_NAME', 'crimevision_db'),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD', '')
        )
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM browser_push_subscriptions")
        count = cursor.fetchone()[0]
        print(f"Found {count} subscriptions")

        cursor.execute("DELETE FROM browser_push_subscriptions")
        conn.commit()
        print("SUCCESS: Cleared all old subscriptions")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    clear_subscriptions()