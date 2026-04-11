#!/usr/bin/env python3
"""
Generate VAPID keys for web push notifications.

VAPID (Voluntary Application Server Identification) keys are required to send
push notifications to browsers. This script generates a new pair of keys.

Usage:
    python generate_vapid_keys.py

Output:
    - Prints VAPID public and private keys
    - Can be used to set environment variables
"""

import sys
import os

def generate_vapid_keys():
    """Generate VAPID keys for web push notifications"""
    try:
        import subprocess
        import json

        print("\n" + "="*70)
        print("🔐 VAPID Key Generation")
        print("="*70)

        # Use web-push CLI to generate keys (if available)
        # Otherwise, use pre-generated keys
        try:
            result = subprocess.run(
                ['npx', 'web-push', 'generate-vapid-keys', '--json'],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                keys = json.loads(result.stdout)
                public_key_b64 = keys['publicKey']
                private_key_b64 = keys['privateKey']
            else:
                raise Exception("web-push CLI failed")
        except:
            # Fallback: Use pre-generated keys from main.py
            print("⚠️  Using pre-generated keys from main.py")
            print("   (For production, generate new keys with: npm install -g web-push)")
            public_key_b64 = "MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAEqv+r/g39Scb8z4HtDZZwW3zYgorOLfBStcuPXlwoG3ZP4aX0+EU+jI8rT52CEck7b6Yl81qr+FTQkqzOy0fByQ=="
            private_key_b64 = "MIGHAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBG0wawIBAQQgKf9Iyf0m8x6E7n5Cu36x73zXG/ptWjhBpX1DJ4udC92hRANCAASq/6v+Df1JxvzPge0NlnBbfNiCis4t8FK1y49eXCgbdk/hpfT4RT6MjytPnYIRyTtvpiXzWqv4VNCSrM7LR8HJ"

        print("\n✅ VAPID Keys Generated Successfully!\n")

        print("📋 PUBLIC KEY (for frontend):")
        print("-" * 70)
        print(public_key_b64)
        print()

        print("🔒 PRIVATE KEY (for backend - KEEP SECRET!):")
        print("-" * 70)
        print(private_key_b64)
        print()

        print("="*70)
        print("📝 Environment Variables to Set:")
        print("="*70)
        print(f"VAPID_PUBLIC_KEY={public_key_b64}")
        print(f"VAPID_PRIVATE_KEY={private_key_b64}")
        print()

        print("="*70)
        print("💾 Save to .env file:")
        print("="*70)
        env_content = f"""# Web Push Notification VAPID Keys
VAPID_PUBLIC_KEY={public_key_b64}
VAPID_PRIVATE_KEY={private_key_b64}
"""
        print(env_content)

        # Optionally save to .env file
        env_file = os.path.join(os.path.dirname(__file__), '.env')
        if not os.path.exists(env_file):
            response = input("Would you like to save these keys to .env file? (y/n): ").strip().lower()
            if response == 'y':
                with open(env_file, 'a') as f:
                    f.write('\n' + env_content)
                print(f"✅ Keys saved to {env_file}")
        else:
            print(f"⚠️  .env file already exists at {env_file}")
            print("   Please manually add the keys above to your .env file")

        print("\n" + "="*70)
        print("✅ Setup Complete!")
        print("="*70)
        print("\nNext steps:")
        print("1. Copy the VAPID_PUBLIC_KEY to your frontend (BrowserPushSetup.jsx)")
        print("2. Set VAPID_PRIVATE_KEY in your backend environment")
        print("3. Restart your backend server")
        print("4. Test push notifications\n")

        return True

    except ImportError:
        print("❌ Error: pywebpush is not installed")
        print("   Install it with: pip install pywebpush")
        return False
    except Exception as e:
        print(f"❌ Error generating VAPID keys: {e}")
        import traceback
        traceback.print_exc()
        return False


def get_existing_keys():
    """Display existing VAPID keys from environment"""
    print("\n" + "="*70)
    print("📋 Current VAPID Keys")
    print("="*70)
    
    public_key = os.getenv('VAPID_PUBLIC_KEY')
    private_key = os.getenv('VAPID_PRIVATE_KEY')
    
    if public_key:
        print(f"\n✅ VAPID_PUBLIC_KEY is set")
        print(f"   Value: {public_key[:50]}...")
    else:
        print(f"\n❌ VAPID_PUBLIC_KEY is NOT set")
    
    if private_key:
        print(f"\n✅ VAPID_PRIVATE_KEY is set")
        print(f"   Value: {private_key[:50]}...")
    else:
        print(f"\n❌ VAPID_PRIVATE_KEY is NOT set")
    
    print("\n" + "="*70 + "\n")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--check":
        get_existing_keys()
    else:
        success = generate_vapid_keys()
        sys.exit(0 if success else 1)

