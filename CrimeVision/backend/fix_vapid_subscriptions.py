"""
Fix VAPID Credentials Mismatch - Clear Old Browser Subscriptions

This error occurs because the browser has old subscription keys that don't match
the current VAPID keys on the server.

SOLUTION STEPS:
"""

# 1. Clear all browser push subscriptions from the database
import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv()


def clear_old_vapid_subscriptions():
    """Clear old browser push subscriptions that have wrong VAPID keys"""
    print("=" * 60)
    print("CLEARING OLD BROWSER PUSH SUBSCRIPTIONS")
    print("=" * 60)

    try:
        conn = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            database=os.getenv('DB_NAME', 'crimevision_db'),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD', '')
        )
        cursor = conn.cursor()

        # Check existing subscriptions
        cursor.execute("SELECT COUNT(*) as count FROM browser_push_subscriptions")
        result = cursor.fetchone()
        existing_count = result[0] if result else 0

        print(f"Found {existing_count} existing browser subscriptions")

        if existing_count > 0:
            print("Clearing old subscriptions...")
            cursor.execute("DELETE FROM browser_push_subscriptions")
            conn.commit()
            print(f"✅ Cleared {existing_count} old subscriptions")
        else:
            print("No existing subscriptions to clear")

        print("\n✅ VAPID subscription cleanup complete!")
        print("\nNext steps:")
        print("1. Restart backend server")
        print("2. Clear browser cache/data for the site")
        print("3. Reload the dashboard")
        print("4. Allow notifications when prompted")
        print("5. Test notifications - should work without VAPID errors")

        return True

    except Exception as e:
        print(f"❌ Error clearing subscriptions: {e}")
        return False

if __name__ == "__main__":
    clear_old_vapid_subscriptions()