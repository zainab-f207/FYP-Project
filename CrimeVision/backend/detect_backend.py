#!/usr/bin/env python3
"""
Backend Detection and Fix Script
"""
import requests
import time

def test_actual_backend():
    """Test which backend is actually running and apply fixes"""
    print("=" * 60)
    print("BACKEND SERVER DETECTION")
    print("=" * 60)

    # Test different possible URLs the frontend might be calling
    test_urls = [
        ("Main Backend", "http://localhost:8000/api/auth/me/stats?area=Gulberg&time_filter=all"),
        ("Enhanced Backend", "http://localhost:8080/api/auth/me/stats?area=Gulberg&time_filter=all"),
        ("Alternative Port", "http://127.0.0.1:8000/api/auth/me/stats?area=Gulberg&time_filter=all"),
    ]

    backend_found = False

    for name, url in test_urls:
        try:
            print(f"\nTesting {name}: {url}")
            response = requests.get(url, timeout=5)

            if response.status_code == 200:
                data = response.json()
                print(f"SUCCESS: {name} is responding!")
                print(f"  Time filter: {data.get('time_filter', 'MISSING')}")
                print(f"  Total crimes: {data.get('total_crimes', 'MISSING')}")
                print(f"  Safety score: {data.get('safety_score', 'MISSING')}")

                # Check if this backend has the fix
                if data.get('time_filter') == 'all' and data.get('total_crimes', 0) > 0:
                    print(f"  STATUS: FIXED - This backend is working correctly!")
                else:
                    print(f"  STATUS: NEEDS FIX - This backend needs the SQL fixes")
                backend_found = True
                break
            else:
                print(f"  Status: {response.status_code}")

        except requests.exceptions.ConnectionError:
            print(f"  Status: Not accessible")
        except Exception as e:
            print(f"  Error: {e}")

    if not backend_found:
        print("\nNO BACKEND FOUND!")
        print("Possible causes:")
        print("1. Backend server is not running")
        print("2. Backend is running on a different port")
        print("3. Backend startup failed")

        print("\nSOLUTION:")
        print("1. Stop all backend processes")
        print("2. Navigate to: cd d:/FYP/Project/CrimeVision/backend")
        print("3. Run: py main.py")
        print("4. Look for 'Application startup complete' message")
        print("5. Test again")

def check_vapid_keys():
    """Check VAPID keys on actual running backend"""
    print("\n" + "=" * 60)
    print("VAPID KEYS CHECK")
    print("=" * 60)

    vapid_urls = [
        "http://localhost:8000/vapid-public-key",
        "http://localhost:8080/vapid-public-key"
    ]

    for url in vapid_urls:
        try:
            response = requests.get(url, timeout=3)
            if response.status_code == 200:
                data = response.json()
                public_key = data.get('publicKey', '')

                # Check if it matches the expected original key
                expected = "MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAE"
                if public_key.startswith(expected):
                    print(f"SUCCESS: {url}")
                    print("  VAPID keys are correct (original keys)")
                    print("  Browser notifications should work")
                else:
                    print(f"WRONG KEYS: {url}")
                    print("  VAPID keys don't match browser subscriptions")
                return
        except:
            continue

    print("ERROR: No VAPID endpoint found")
    print("Backend server might not be running")

if __name__ == "__main__":
    test_actual_backend()
    check_vapid_keys()

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print("1. Run this script to identify which backend is active")
    print("2. Stop any wrong backends")
    print("3. Start the correct backend: cd backend && py main.py")
    print("4. Verify fixes are working")
    print("5. Clear browser cache and test dashboard")