#!/usr/bin/env python3
"""
Kill stuck backend process and restart instructions
"""
import subprocess

def kill_stuck_backend():
    """Kill the stuck backend process"""
    print("=" * 60)
    print("KILLING STUCK BACKEND PROCESS")
    print("=" * 60)

    try:
        # Kill the process on port 8000 (PID 4164)
        print("Killing stuck backend process (PID 4164)...")
        result = subprocess.run(['taskkill', '/PID', '4164', '/F'],
                              capture_output=True, text=True)

        if result.returncode == 0:
            print("SUCCESS: Stuck backend process killed")
        else:
            print(f"Note: {result.stderr}")

        # Verify it's gone
        result = subprocess.run(['netstat', '-ano'],
                              capture_output=True, text=True)
        if ':8000' in result.stdout:
            print("WARNING: Port 8000 still in use")
        else:
            print("SUCCESS: Port 8000 is now free")

        print("\n" + "=" * 60)
        print("NOW START YOUR BACKEND CLEANLY:")
        print("=" * 60)
        print("1. Open new terminal/command prompt")
        print("2. cd d:/FYP/Project/CrimeVision/backend")
        print("3. py main.py")
        print("4. Wait for: 'Application startup complete at http://localhost:8000'")
        print("5. Test dashboard - should work now!")

    except Exception as e:
        print(f"Error: {e}")
        print("\nManual solution:")
        print("1. Open Task Manager (Ctrl+Shift+Esc)")
        print("2. Find python.exe process (PID 4164)")
        print("3. End task")
        print("4. Restart backend: py main.py")

if __name__ == "__main__":
    kill_stuck_backend()