#!/usr/bin/env python3
"""
Test script to verify VAPID keys are correctly configured for browser push notifications.
Run this from the backend directory: python test_vapid_config.py
"""

import os
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / 'CrimeVision' / 'backend'
sys.path.insert(0, str(backend_path))

# Import config to load .env
from app.core.config import get_logger

logger = get_logger('vapid_test')

def validate_vapid_keys():
    """Validate VAPID keys are configured correctly."""

    print("=" * 70)
    print("VAPID Configuration Validator")
    print("=" * 70)

    # Get keys from environment
    public_key = os.getenv('VAPID_PUBLIC_KEY')
    private_key = os.getenv('VAPID_PRIVATE_KEY')

    issues = []

    # Check public key
    print("\n📋 Checking Public Key...")
    if not public_key:
        issues.append("❌ VAPID_PUBLIC_KEY not set in .env")
        print(issues[-1])
    else:
        print(f"✅ VAPID_PUBLIC_KEY found (length: {len(public_key)})")

        # Validate format (should be base64url)
        if not public_key.replace('-', '').replace('_', '').replace('=', '').isalnum():
            issues.append("❌ VAPID_PUBLIC_KEY has invalid characters (not base64url)")
            print(issues[-1])
        else:
            print(f"✅ Public key format valid (base64url)")
            print(f"   Key: {public_key[:40]}...")

    # Check private key
    print("\n📋 Checking Private Key...")
    if not private_key:
        issues.append("❌ VAPID_PRIVATE_KEY not set in .env")
        print(issues[-1])
    else:
        print(f"✅ VAPID_PRIVATE_KEY found (length: {len(private_key)})")

        # Check if it's PEM-encoded (should start with specific markers)
        if "BEGIN PRIVATE KEY" in private_key or private_key.startswith("LS0t"):
            print("✅ Private key appears to be properly encoded (PEM or base64)")
        else:
            print("⚠️  Private key format not recognized - may need adjustment")

    # Test key conversion (frontend's urlBase64ToUint8Array)
    print("\n📋 Testing Key Conversion...")
    if public_key:
        try:
            # Simulate the frontend's urlBase64ToUint8Array
            padding = '='.repeat((4 - len(public_key) % 4) % 4) if isinstance('='.repeat(0), str) else '=' * ((4 - len(public_key) % 4) % 4)
            import base64
            # Proper base64url decoding
            decoded = base64.urlsafe_b64decode(public_key + padding)
            print(f"✅ Public key decodes successfully ({len(decoded)} bytes)")
        except Exception as e:
            issues.append(f"❌ Failed to decode public key: {e}")
            print(issues[-1])

    # Summary
    print("\n" + "=" * 70)
    if not issues:
        print("✅ All VAPID checks passed! Configuration is valid.")
        print("\nBrowser push notifications should work correctly.")
        return 0
    else:
        print(f"❌ Found {len(issues)} issue(s):")
        for issue in issues:
            print(f"  {issue}")
        print("\nFix the issues above and test again.")
        return 1

if __name__ == '__main__':
    sys.exit(validate_vapid_keys())
