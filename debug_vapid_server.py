#!/usr/bin/env python3
"""Quick test to verify what VAPID key the server is actually serving."""

import requests
import os
import sys
from pathlib import Path

# Add backend to path for config loading
backend_path = Path(__file__).parent / 'CrimeVision' / 'backend'
sys.path.insert(0, str(backend_path))

try:
    from app.core.config import get_logger
    logger = get_logger('vapid_check')

    print("🔍 Testing VAPID Key Server Response...")
    print("=" * 50)

    # Test the endpoint directly
    response = requests.get('http://localhost:8000/api/alerts/vapid-public-key', timeout=5)

    if response.status_code == 200:
        data = response.json()
        public_key = data.get('publicKey', '')

        print(f"✅ Server Status: {response.status_code}")
        print(f"📋 Server Returns: {public_key}")
        print(f"📏 Key Length: {len(public_key)}")

        # Check if it's the old or new key
        if public_key.startswith('MFkwEwYH'):
            print("❌ PROBLEM: Server is still returning OLD hardcoded key!")
        elif public_key.startswith('BDNFEgS8'):
            print("✅ CORRECT: Server is returning NEW key from .env file!")
        else:
            print(f"⚠️  UNKNOWN: Key format not recognized: {public_key[:20]}...")

        # Check key format
        import re
        if re.match(r'^[A-Za-z0-9_-]+$', public_key):
            print("✅ Format: Valid base64url (no + or / characters)")
        else:
            print("❌ Format: Invalid base64url (contains + or / characters)")
            if '+' in public_key:
                print("   - Contains '+' character (should be '-')")
            if '/' in public_key:
                print("   - Contains '/' character (should be '_')")

        print(f"\n📋 Full Key: {public_key}")

    else:
        print(f"❌ Server Error: {response.status_code}")
        print(f"Response: {response.text}")

    # Also check .env file directly
    print("\n" + "=" * 50)
    print("🔍 Checking .env file directly...")

    env_public_key = os.getenv('VAPID_PUBLIC_KEY')
    if env_public_key:
        print(f"✅ .env VAPID_PUBLIC_KEY: {env_public_key}")
    else:
        print("❌ .env VAPID_PUBLIC_KEY: NOT SET")

except Exception as e:
    print(f"❌ Error: {e}")