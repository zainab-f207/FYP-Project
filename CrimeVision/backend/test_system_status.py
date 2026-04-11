#!/usr/bin/env python3
"""
Comprehensive System Status Check
"""
import requests
import json
import os

def test_backend_status():
    """Test if backend is working with both fixes"""
    print("=" * 60)
    print("COMPREHENSIVE SYSTEM STATUS CHECK")
    print("=" * 60)

    try:
        # Test 1: Check if backend is running
        print("\n1. TESTING BACKEND CONNECTION")
        try:
            response = requests.get("http://localhost:8000/docs", timeout=5)
            if response.status_code == 200:
                print("✅ Backend server is running")
            else:
                print(f"⚠️  Backend responded with status {response.status_code}")
        except Exception as e:
            print(f"❌ Backend server is not accessible: {e}")
            return

        # Test 2: Check VAPID keys endpoint
        print("\n2. TESTING VAPID KEYS ENDPOINT")
        try:
            response = requests.get("http://localhost:8000/vapid-public-key", timeout=5)
            if response.status_code == 200:
                data = response.json()
                public_key = data.get('publicKey', '')
                print(f"✅ VAPID endpoint working")
                print(f"Public key (first 30 chars): {public_key[:30]}...")

                # Check if it matches expected original key
                expected_start = "MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAE"
                if public_key.startswith(expected_start):
                    print("✅ Using original VAPID keys (should fix browser notifications)")
                else:
                    print("⚠️  Using different VAPID keys")
            else:
                print(f"❌ VAPID endpoint failed: {response.status_code}")
        except Exception as e:
            print(f"❌ VAPID endpoint error: {e}")

        # Test 3: Check getUserStats with All Time filter
        print("\n3. TESTING ALL TIME DASHBOARD ENDPOINT")
        try:
            # Simulate the API call that the dashboard makes
            params = {
                'area': 'Gulberg',
                'time_filter': 'all'
            }
            response = requests.get("http://localhost:8000/user-stats",
                                  params=params,
                                  timeout=10)

            if response.status_code == 200:
                data = response.json()
                print("✅ getUserStats endpoint working")
                print(f"Time filter returned: '{data.get('time_filter', 'MISSING')}'")
                print(f"Total crimes: {data.get('total_crimes', 'MISSING')}")
                print(f"Safety score: {data.get('safety_score', 'MISSING')}")
                print(f"Resolved area: {data.get('resolved_area', 'MISSING')}")

                # Check if All Time data is correct
                time_filter = data.get('time_filter')
                total_crimes = data.get('total_crimes', 0)

                if time_filter == 'all':
                    print("✅ Time filter correctly returned as 'all'")
                else:
                    print(f"❌ Time filter should be 'all' but got '{time_filter}'")

                if total_crimes > 0:
                    print(f"✅ Found {total_crimes} crimes (should fix dashboard)")
                else:
                    print("❌ No crimes found - backend SQL fixes not active")

            else:
                print(f"❌ getUserStats failed: {response.status_code}")
                print(f"Response: {response.text[:200]}...")

        except Exception as e:
            print(f"❌ getUserStats error: {e}")

        print("\n" + "=" * 60)
        print("DIAGNOSIS:")
        print("=" * 60)
        print("If getUserStats shows 0 crimes for 'all' time filter:")
        print("  → Backend server needs RESTART to load SQL fixes")
        print()
        print("If VAPID key doesn't match expected format:")
        print("  → Backend server needs RESTART to load original keys")
        print()
        print("After restart, both issues should be resolved!")

    except Exception as e:
        print(f"System check failed: {e}")

if __name__ == "__main__":
    test_backend_status()