#!/usr/bin/env python3
"""
Test browser notifications setup
"""
import requests
import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv('app/.env')

# Database connection
def get_db():
    return mysql.connector.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        user=os.getenv('DB_USER', 'root'),
        password=os.getenv('DB_PASSWORD', ''),
        database=os.getenv('DB_NAME', 'crime_reporting_system')
    )

def test_browser_notifications():
    print("=" * 60)
    print("BROWSER NOTIFICATIONS DIAGNOSTIC")
    print("=" * 60)

    # Step 1: Check VAPID endpoint
    print("\n1. Testing VAPID endpoint...")
    try:
        resp = requests.get('http://localhost:8000/api/alerts/vapid-public-key', timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            print(f"   OK - VAPID key: {data['publicKey'][:50]}...")
        else:
            print(f"   FAILED - Status: {resp.status_code}")
            return False
    except Exception as e:
        print(f"   ERROR: {e}")
        return False

    # Step 2: Check database subscriptions
    print("\n2. Checking database subscriptions...")
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT user_id, LEFT(endpoint, 60) as endpoint_preview FROM browser_push_subscriptions")
        subs = cursor.fetchall()

        if subs:
            print(f"   Found {len(subs)} subscription(s):")
            for sub in subs:
                print(f"     - User {sub['user_id']}: {sub['endpoint_preview']}...")
        else:
            print("   NO SUBSCRIPTIONS FOUND")
            print("\n   TO FIX:")
            print("   1. Refresh your browser (Ctrl+Shift+R)")
            print("   2. Open DevTools Console (F12)")
            print("   3. Go to Profile Settings")
            print("   4. Enable 'Browser Notifications' toggle")
            print("   5. Click 'Save Changes'")
            print("   6. Check console for subscription confirmation")
            print("   7. Run this script again to verify")

        cursor.close()
        conn.close()
    except Exception as e:
        print(f"   ERROR: {e}")
        return False

    # Step 3: Check user 42 specifically
    print("\n3. Checking user 42 (zainab.fayyaz921)...")
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                u.username,
                u.browser_notifications_enabled,
                CASE WHEN bps.id IS NOT NULL THEN 'YES' ELSE 'NO' END as has_subscription
            FROM users_info u
            LEFT JOIN browser_push_subscriptions bps ON u.id = bps.user_id
            WHERE u.id = 42
        """)
        user = cursor.fetchone()

        if user:
            print(f"   Username: {user['username']}")
            print(f"   Browser notifications enabled: {user['browser_notifications_enabled']}")
            print(f"   Has subscription: {user['has_subscription']}")

            if user['browser_notifications_enabled'] == 1 and user['has_subscription'] == 'NO':
                print("\n   ISSUE DETECTED:")
                print("   - Notifications are ENABLED in profile")
                print("   - But NO browser subscription exists")
                print("   - This means the subscription process failed silently")
                print("\n   SOLUTION:")
                print("   1. Open browser DevTools Console (F12)")
                print("   2. Clear browser data (Settings > Privacy > Clear browsing data)")
                print("   3. Refresh page (Ctrl+Shift+R)")
                print("   4. Go to Profile Settings")
                print("   5. DISABLE browser notifications, save")
                print("   6. ENABLE browser notifications again, save")
                print("   7. When prompted, click ALLOW for notifications")
                print("   8. Check console for: 'Push subscription created'")
        else:
            print("   User 42 not found")

        cursor.close()
        conn.close()
    except Exception as e:
        print(f"   ERROR: {e}")
        return False

    print("\n" + "=" * 60)
    print("Diagnostic complete!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    test_browser_notifications()
