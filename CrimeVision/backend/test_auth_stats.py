#!/usr/bin/env python3
"""
Test the stats endpoint WITH authentication to see what it really returns
"""
import requests
import json

def test_with_real_auth():
    """Test with actual user login"""
    print("=" * 60)
    print("TESTING WITH REAL AUTHENTICATION")
    print("=" * 60)

    # Step 1: Login to get a real token
    print("\n1. Logging in as test user...")
    login_url = "http://localhost:8000/auth/login"
    login_data = {
        "username": "zainab.fayyaz921",  # Use actual username from error logs
        "password": "test123"  # You'll need to use the correct password
    }

    print(f"Attempting login with username: {login_data['username']}")
    try:
        response = requests.post(login_url, json=login_data, timeout=5)

        if response.status_code == 200:
            data = response.json()
            token = data.get('access_token')
            if not token:
                print("ERROR: No access_token in login response")
                print(f"Response: {data}")
                return False

            print(f"✅ Login successful! Got token: {token[:30]}...")

            # Step 2: Test stats endpoint with token
            print("\n2. Testing stats endpoint with auth token...")
            stats_url = "http://localhost:8000/api/auth/me/stats"
            stats_params = {
                "area": "Gulberg",
                "time_filter": "all"
            }
            headers = {
                "Authorization": f"Bearer {token}"
            }

            print(f"GET {stats_url}")
            print(f"Params: {stats_params}")
            print(f"Headers: Authorization: Bearer {token[:20]}...")

            response = requests.get(stats_url, params=stats_params, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                print("\n✅ SUCCESS! Backend returned data:")
                print(f"  time_filter: {data.get('time_filter', 'MISSING')}")
                print(f"  total_crimes: {data.get('total_crimes', 'MISSING')}")
                print(f"  safety_score: {data.get('safety_score', 'MISSING')}")
                print(f"  resolved_area: {data.get('resolved_area', 'MISSING')}")
                print(f"  confidence: {data.get('confidence', 'MISSING')}")

                # Check if the fix is working
                if data.get('time_filter') == 'all':
                    print("\n✅ Time filter is correct: 'all'")
                else:
                    print(f"\n❌ Time filter wrong: {data.get('time_filter')}")

                if data.get('total_crimes', 0) > 0:
                    print(f"✅ Has crime data: {data.get('total_crimes')} crimes")
                else:
                    print(f"❌ No crime data: {data.get('total_crimes', 0)} crimes")

                # Print full response for debugging
                print("\nFull response:")
                print(json.dumps(data, indent=2))
                return True
            else:
                print(f"\n❌ Stats endpoint failed: {response.status_code}")
                print(f"Response: {response.text[:500]}")
                return False
        else:
            print(f"\n❌ Login failed: {response.status_code}")
            print(f"Response: {response.text[:500]}")

            # Try to suggest what to do
            if response.status_code == 401:
                print("\nThe username/password is incorrect.")
                print("Please update the credentials in this script.")
            elif response.status_code == 404:
                print("\nLogin endpoint not found. Check if backend is running correctly.")

            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("\nNOTE: Update the password in this script before running!")
    print("Current username: zainab.fayyaz921")
    print("\nPress Enter to continue...")
    input()

    test_with_real_auth()
