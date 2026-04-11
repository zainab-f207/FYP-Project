#!/usr/bin/env python3
"""
Test if the correct backend is running and working
"""
import requests
import json

def test_running_backend():
    """Test if your main.py backend is actually running and responding"""
    print("=" * 60)
    print("TESTING YOUR MAIN.PY BACKEND")
    print("=" * 60)

    # Test the exact endpoint your frontend calls
    test_url = "http://localhost:8000/api/auth/me/stats"
    test_params = {
        "area": "Gulberg",
        "time_filter": "all"
    }

    print(f"Testing URL: {test_url}")
    print(f"Parameters: {test_params}")

    try:
        response = requests.get(test_url, params=test_params, timeout=5)

        if response.status_code == 200:
            data = response.json()
            print("SUCCESS: Backend is responding!")
            print(f"  time_filter: {data.get('time_filter', 'MISSING')}")
            print(f"  total_crimes: {data.get('total_crimes', 'MISSING')}")
            print(f"  safety_score: {data.get('safety_score', 'MISSING')}")

            # Check if the All Time fix is working
            if data.get('time_filter') == 'all' and data.get('total_crimes', 0) > 0:
                print("SUCCESS: All Time fix is working!")
                print("The issue might be frontend caching or browser cache")
                return True
            else:
                print("PROBLEM: Backend not returning expected data for All Time")
                return False

        elif response.status_code == 401:
            print("AUTHENTICATION REQUIRED")
            print("The backend is running but needs login token")
            print("This explains why your dashboard shows issues")
            return False
        elif response.status_code == 422:
            print("PARAMETER ERROR")
            print("Backend doesn't accept the parameters correctly")
            return False
        else:
            print(f"BACKEND ERROR: Status {response.status_code}")
            print(f"Response: {response.text[:200]}...")
            return False

    except requests.exceptions.ConnectionError:
        print("BACKEND NOT RUNNING")
        print("Your main.py is not accessible on localhost:8000")
        print("Check if it started correctly or crashed")
        return False
    except Exception as e:
        print(f"ERROR: {e}")
        return False

def check_backend_process():
    """Check if backend process is running"""
    print("\n" + "=" * 60)
    print("CHECKING BACKEND PROCESS")
    print("=" * 60)

    import subprocess
    try:
        # Check if any python process is listening on port 8000
        result = subprocess.run(
            ['netstat', '-ano', '|', 'findstr', ':8000'],
            shell=True, capture_output=True, text=True
        )
        if result.stdout:
            print("Process found on port 8000:")
            print(result.stdout)
        else:
            print("No process listening on port 8000")
            print("Your backend is not running!")

    except Exception as e:
        print(f"Could not check process: {e}")

if __name__ == "__main__":
    backend_working = test_running_backend()
    check_backend_process()

    if not backend_working:
        print("\n" + "=" * 60)
        print("SOLUTION STEPS:")
        print("=" * 60)
        print("1. Start your backend:")
        print("   cd d:/FYP/Project/CrimeVision/backend")
        print("   py main.py")
        print("")
        print("2. Look for startup message:")
        print("   'Application startup complete at http://localhost:8000'")
        print("")
        print("3. If it crashes, check the error message")
        print("4. Then test dashboard again")
    else:
        print("\n===== BACKEND IS WORKING =====")
        print("The issue is likely browser cache.")
        print("Clear your browser cache and reload the dashboard.")