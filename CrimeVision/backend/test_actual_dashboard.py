#!/usr/bin/env python3
"""
Test Actual Dashboard API Call
"""
import requests
import json

def test_dashboard_api():
    """Test the exact API call the dashboard makes"""
    print("=" * 60)
    print("TESTING ACTUAL DASHBOARD API")
    print("=" * 60)

    # The exact API call your dashboard makes based on the frontend code
    test_cases = [
        {
            "name": "Dashboard API (main)",
            "url": "http://localhost:8000/api/auth/me/stats",
            "params": {"area": "Gulberg", "time_filter": "all"}
        },
        {
            "name": "Dashboard API (alt port)",
            "url": "http://localhost:8080/api/auth/me/stats",
            "params": {"area": "Gulberg", "time_filter": "all"}
        },
        {
            "name": "Dashboard API (127.0.0.1)",
            "url": "http://127.0.0.1:8000/api/auth/me/stats",
            "params": {"area": "Gulberg", "time_filter": "all"}
        }
    ]

    backend_found = False

    for test in test_cases:
        try:
            print(f"\nTesting: {test['name']}")
            print(f"URL: {test['url']}")
            print(f"Params: {test['params']}")

            response = requests.get(test['url'], params=test['params'], timeout=5)

            if response.status_code == 200:
                data = response.json()
                print("SUCCESS: Backend responding!")
                print(f"Response data:")
                print(f"  time_filter: {data.get('time_filter', 'MISSING')}")
                print(f"  total_crimes: {data.get('total_crimes', 'MISSING')}")
                print(f"  safety_score: {data.get('safety_score', 'MISSING')}")
                print(f"  resolved_area: {data.get('resolved_area', 'MISSING')}")

                backend_found = True

                # Check if fixes are applied
                if data.get('time_filter') == 'all':
                    print("  ✓ Time filter fix: WORKING")
                else:
                    print("  ✗ Time filter fix: MISSING")

                if data.get('total_crimes', 0) > 0:
                    print(f"  ✓ Crime data: WORKING ({data.get('total_crimes')} crimes)")
                else:
                    print("  ✗ Crime data: NOT WORKING (0 crimes)")

                return test['url']

            elif response.status_code == 401:
                print(f"Authentication required - backend is running but needs login")
                return test['url']
            else:
                print(f"Status: {response.status_code}")

        except requests.exceptions.ConnectionError:
            print("Not accessible")
        except Exception as e:
            print(f"Error: {e}")

    if not backend_found:
        print("\nNO BACKEND DETECTED!")
        print("But you're seeing errors, so it must be running somewhere...")
        print("Check these possibilities:")
        print("1. Backend running in VS Code terminal")
        print("2. Backend running in different command prompt")
        print("3. Backend running as service/background process")
        print("4. Backend running on non-standard port")

        # Let's check a wider port range
        print("\nScanning wider port range...")
        for port in range(8000, 8010):
            try:
                test_url = f"http://localhost:{port}/api/auth/me/stats"
                response = requests.get(test_url, params={"area": "Gulberg"}, timeout=1)
                if response.status_code in [200, 401]:
                    print(f"FOUND: Backend on port {port}")
                    return f"http://localhost:{port}"
            except:
                pass

    return None

if __name__ == "__main__":
    backend_url = test_dashboard_api()
    if backend_url:
        print(f"\nFound backend at: {backend_url}")
        print("This is the backend that needs to be fixed!")
    else:
        print("\nCould not locate the running backend.")