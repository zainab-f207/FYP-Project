#!/usr/bin/env python3
"""
Test VAPID Configuration from Environment Variables
"""
import os

def test_vapid_env():
    """Test if VAPID environment variables are properly set"""
    print("=" * 60)
    print("TESTING VAPID ENVIRONMENT VARIABLES")
    print("=" * 60)

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
        print("SUCCESS: VAPID configuration is ready for browser notifications!")
        return True
    else:
        print("ERROR: VAPID configuration incomplete")
        if not valid_public:
            print("- Public key missing or too short")
        if not valid_private:
            print("- Private key missing or too short")
        return False

if __name__ == "__main__":
    success = test_vapid_env()
    if success:
        print("\nNext steps:")
        print("1. Restart your backend server")
        print("2. Test browser notifications in the frontend")
    else:
        print("\nTo fix:")
        print("1. Check .env file contents")
        print("2. Restart backend server")
        print("3. Test again")