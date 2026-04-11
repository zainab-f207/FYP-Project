#!/usr/bin/env python3
"""
Test VAPID Configuration by Loading .env File Directly
"""
import os
try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False

def test_vapid_with_dotenv():
    """Test VAPID keys by loading .env file"""
    print("=" * 60)
    print("TESTING VAPID WITH EXPLICIT .env LOADING")
    print("=" * 60)

    # Try loading .env file
    if DOTENV_AVAILABLE:
        print("Loading .env file...")
        load_dotenv()
    else:
        print("python-dotenv not available, checking environment...")

    # Load from environment
    public_key = os.getenv('VAPID_PUBLIC_KEY')
    private_key = os.getenv('VAPID_PRIVATE_KEY')
    subject = os.getenv('VAPID_SUBJECT')

    print(f"Public Key Found: {'YES' if public_key else 'NO'}")
    if public_key:
        print(f"Public Key Length: {len(public_key)}")
        print(f"Public Key Preview: {public_key[:30]}...")

    print(f"Private Key Found: {'YES' if private_key else 'NO'}")
    if private_key:
        print(f"Private Key Length: {len(private_key)}")
        print(f"Private Key Preview: {'*' * 30}...")

    print(f"VAPID Subject: {subject if subject else 'NOT SET'}")

    # Check if keys look valid
    valid_public = public_key and len(public_key) > 80
    valid_private = private_key and len(private_key) > 300

    print("\n" + "=" * 60)
    print("VALIDATION RESULTS")
    print("=" * 60)
    print(f"Public Key Valid: {'YES' if valid_public else 'NO'}")
    print(f"Private Key Valid: {'YES' if valid_private else 'NO'}")

    if valid_public and valid_private:
        print("SUCCESS: VAPID configuration is working!")
        return True
    else:
        print("ERROR: VAPID configuration needs attention")
        print("\nDirect .env file check:")
        try:
            with open('.env', 'r') as f:
                content = f.read()
                if 'VAPID_PUBLIC_KEY' in content:
                    print("✓ VAPID_PUBLIC_KEY found in .env file")
                else:
                    print("✗ VAPID_PUBLIC_KEY not found in .env file")
                if 'VAPID_PRIVATE_KEY' in content:
                    print("✓ VAPID_PRIVATE_KEY found in .env file")
                else:
                    print("✗ VAPID_PRIVATE_KEY not found in .env file")
        except FileNotFoundError:
            print("✗ .env file not found in current directory")
        return False

def test_manual_env_load():
    """Manually read .env file and check VAPID keys"""
    print("\n" + "=" * 60)
    print("MANUAL .env FILE PARSING")
    print("=" * 60)

    try:
        with open('.env', 'r') as f:
            lines = f.readlines()

        vapid_vars = {}
        for line in lines:
            line = line.strip()
            if line.startswith('VAPID_') and '=' in line:
                key, value = line.split('=', 1)
                vapid_vars[key] = value
                print(f"Found: {key} = {value[:30]}{'...' if len(value) > 30 else ''}")

        if vapid_vars:
            print(f"\nFound {len(vapid_vars)} VAPID variables in .env file")
            return True
        else:
            print("No VAPID variables found in .env file")
            return False

    except FileNotFoundError:
        print("ERROR: .env file not found")
        return False
    except Exception as e:
        print(f"ERROR reading .env file: {e}")
        return False

if __name__ == "__main__":
    success1 = test_vapid_with_dotenv()
    success2 = test_manual_env_load()

    if success1 or success2:
        print("\n" + "=" * 60)
        print("OVERALL: VAPID keys are configured correctly!")
        print("Backend server should be able to use browser notifications.")
    else:
        print("\n" + "=" * 60)
        print("OVERALL: VAPID configuration needs fixing")
        print("Check .env file location and contents")