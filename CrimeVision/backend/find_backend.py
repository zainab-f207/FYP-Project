#!/usr/bin/env python3
"""
Find Running Backend Process
"""
import requests
import subprocess

def scan_for_backends():
    """Scan for running backend processes and ports"""
    print("=" * 60)
    print("SCANNING FOR RUNNING BACKENDS")
    print("=" * 60)

    # Check for Python processes that might be running the backend
    try:
        # Get running Python processes
        result = subprocess.run(['powershell', '-Command',
                               'Get-Process python* | Select-Object Name,Id,Path | Format-Table -AutoSize'],
                               capture_output=True, text=True, shell=True)
        print("Python processes:")
        print(result.stdout)
    except:
        print("Could not check Python processes")

    # Test expanded port range
    print("\nScanning ports for backend services...")
    test_ports = [8000, 8080, 3000, 5000, 8001, 8888, 9000, 4000, 7000, 5173, 5174]

    for port in test_ports:
        try:
            # Test basic connection
            response = requests.get(f"http://localhost:{port}", timeout=1)
            print(f"Port {port}: Active (Status {response.status_code})")

            # Test for API endpoints
            try:
                api_response = requests.get(f"http://localhost:{port}/api/auth/me/stats?area=Gulberg&time_filter=all", timeout=1)
                if api_response.status_code == 200:
                    data = api_response.json()
                    print(f"  -> FOUND BACKEND! Stats endpoint working")
                    print(f"     Time filter: {data.get('time_filter')}")
                    print(f"     Total crimes: {data.get('total_crimes')}")
                    print(f"     This is the backend causing your issues!")
                    return port
            except:
                pass

        except requests.exceptions.RequestException:
            pass  # Port not accessible
        except Exception as e:
            pass

    print("No backend found on scanned ports")
    return None

def solution_steps():
    """Provide solution steps"""
    print("\n" + "=" * 60)
    print("SOLUTION STEPS")
    print("=" * 60)
    print()
    print("Since you're seeing errors but no backend is detectable:")
    print()
    print("1. STOP ALL BACKEND PROCESSES:")
    print("   - Press Ctrl+C in any terminal running Python/FastAPI")
    print("   - Close VS Code terminals")
    print("   - Check Task Manager for python.exe processes")
    print()
    print("2. START THE CORRECT BACKEND:")
    print("   - Open NEW terminal")
    print("   - cd d:/FYP/Project/CrimeVision/backend")
    print("   - py main.py")
    print("   - Wait for 'Application startup complete' message")
    print("   - Note the port number (should be :8000)")
    print()
    print("3. VERIFY FIXES:")
    print("   - Run: py detect_backend.py")
    print("   - Should show backend responding with 222 crimes for Gulberg")
    print()
    print("4. TEST IN BROWSER:")
    print("   - Clear browser cache (Ctrl+Shift+R)")
    print("   - Test Gulberg All Time -> should show ~222 incidents")
    print("   - Test browser notifications -> should work without VAPID errors")

if __name__ == "__main__":
    found_port = scan_for_backends()
    if not found_port:
        solution_steps()