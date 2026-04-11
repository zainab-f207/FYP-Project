import mysql.connector

def clear_subscriptions():
    try:
        conn = mysql.connector.connect(
            host='localhost',
            database='crimevision_db',
            user='root',
            password='hafsa555'
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