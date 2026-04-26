#!/usr/bin/env python3
"""
Comprehensive Diagnostic - Find Root Cause of Both Issues
"""
import os
import requests
import json
import time
from dotenv import load_dotenv

load_dotenv()

def test_backend_with_auth():
    """Test the backend with proper authentication like the frontend does"""
    print("=" * 60)
    print("TESTING BACKEND WITH AUTHENTICATION")
    print("=" * 60)

    # Test 1: Check if backend is responding at all
    try:
        response = requests.get("http://localhost:8000/", timeout=5)
        print(f"Backend root: Status {response.status_code}")
    except Exception as e:
        print(f"Backend not accessible: {e}")
        return False

    # Test 2: Try the stats endpoint without auth (should get 401)
    try:
        response = requests.get("http://localhost:8000/api/auth/me/stats?area=Gulberg&time_filter=all", timeout=5)
        print(f"Stats without auth: Status {response.status_code}")

        if response.status_code == 401:
            print("✓ Backend requires authentication (correct)")
        elif response.status_code == 200:
            data = response.json()
            print("✗ Backend allows access without auth")
            print(f"Response: {data}")
        else:
            print(f"✗ Unexpected status: {response.text[:200]}")

    except Exception as e:
        print(f"Stats endpoint error: {e}")

    # Test 3: Check VAPID endpoint
    try:
        response = requests.get("http://localhost:8000/vapid-public-key", timeout=5)
        if response.status_code == 200:
            data = response.json()
            public_key = data.get('publicKey', '')
            print(f"VAPID endpoint: Working")
            print(f"Public key: {public_key[:30]}...")

            # Check if it's the expected original key
            expected = "MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAE"
            if public_key.startswith(expected):
                print("✓ Using original VAPID keys")
            else:
                print("✗ Using wrong VAPID keys - browser subscriptions won't match")
        else:
            print(f"VAPID endpoint failed: {response.status_code}")
    except Exception as e:
        print(f"VAPID endpoint error: {e}")

    return True

def check_database_directly():
    """Check database directly to see if Gulberg crimes exist"""
    print("\n" + "=" * 60)
    print("CHECKING DATABASE DIRECTLY")
    print("=" * 60)

    try:
        import mysql.connector

        conn = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            database=os.getenv('DB_NAME', 'crimevision_db'),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD', '')
        )
        cursor = conn.cursor(dictionary=True)

        # Test different Gulberg patterns
        patterns = ['%gulberg%', '%Gulberg%', 'Gulberg, Lahore']

        for pattern in patterns:
            cursor.execute("SELECT COUNT(*) as count FROM crimes WHERE area LIKE %s", (pattern,))
            result = cursor.fetchone()
            count = result['count'] if result else 0
            print(f"Pattern '{pattern}': {count} crimes found")

        # Test the exact query that should run for "All Time"
        print(f"\nTesting 'All Time' query (no date filter):")
        cursor.execute("""
            SELECT
                COUNT(*) as total_crimes,
                SUM(CASE WHEN risk_level = 'High' THEN 1 ELSE 0 END) as high_risk_count,
                SUM(CASE WHEN risk_level = 'Medium' THEN 1 ELSE 0 END) as medium_risk_count
            FROM crimes
            WHERE area LIKE %s
        """, ('%gulberg%',))

        result = cursor.fetchone()
        print(f"All Time result: {result}")

        if result and result['total_crimes'] > 0:
            print("✓ Database has Gulberg crimes - backend issue")
        else:
            print("✗ No crimes found in database - data issue")

        cursor.close()
        conn.close()

        return result and result['total_crimes'] > 0

    except Exception as e:
        print(f"Database check failed: {e}")
        return False

def check_browser_subscription_flow():
    """Check the browser subscription endpoint"""
    print("\n" + "=" * 60)
    print("CHECKING BROWSER SUBSCRIPTION FLOW")
    print("=" * 60)

    try:
        # Test subscription endpoint
        response = requests.get("http://localhost:8000/api/browser-notifications", timeout=5)
        print(f"Subscription endpoint: Status {response.status_code}")

        if response.status_code == 401:
            print("✓ Subscription requires authentication")
        elif response.status_code == 200:
            print("✗ Subscription works without auth - config issue")

        # Check if there are any subscriptions in database
        import mysql.connector

        conn = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            database=os.getenv('DB_NAME', 'crimevision_db'),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD', '')
        )
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT COUNT(*) as count FROM browser_push_subscriptions")
        result = cursor.fetchone()
        sub_count = result['count'] if result else 0
        print(f"Database subscriptions: {sub_count}")

        if sub_count == 0:
            print("✓ Old subscriptions cleared successfully")
        else:
            print("✗ Subscriptions still exist")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"Browser subscription check failed: {e}")

def solution_summary():
    """Provide solution steps based on findings"""
    print("\n" + "=" * 60)
    print("SOLUTION ANALYSIS")
    print("=" * 60)

    backend_ok = test_backend_with_auth()
    db_has_data = check_database_directly()
    check_browser_subscription_flow()

    print(f"\nDIAGNOSIS:")
    print(f"Backend accessible: {backend_ok}")
    print(f"Database has Gulberg data: {db_has_data}")

    if backend_ok and db_has_data:
        print("\n🔍 LIKELY CAUSE: Authentication issue")
        print("The frontend can't authenticate properly to get real data")
        print("\nSOLUTIONS:")
        print("1. Check if you're logged into the dashboard")
        print("2. Try logging out and back in")
        print("3. Check browser developer tools for auth errors")
        print("4. Clear ALL browser data (not just cache)")
    elif backend_ok and not db_has_data:
        print("\n🔍 LIKELY CAUSE: Database issue")
        print("No crime data found for Gulberg")
    elif not backend_ok:
        print("\n🔍 LIKELY CAUSE: Backend startup issue")
        print("Backend not responding properly")

    print(f"\nFor browser notifications:")
    print("The 'No subscription found' error means the subscription process")
    print("isn't working. This could be authentication or VAPID key issues.")

if __name__ == "__main__":
    solution_summary()