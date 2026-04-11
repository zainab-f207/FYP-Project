#!/usr/bin/env python3
"""
Simple VAPID Key Generator - No Emojis for Windows Compatibility
"""
import json
import secrets
import base64
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.backends import default_backend

def generate_vapid_keys():
    """Generate VAPID keys for web push notifications"""
    try:
        print("=" * 50)
        print("VAPID KEY GENERATION")
        print("=" * 50)

        # Generate private key
        print("Generating private key...")
        private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())

        # Get private key in PEM format
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )

        # Get public key
        public_key = private_key.public_key()

        # Get public key in uncompressed point format
        public_numbers = public_key.public_numbers()

        # Convert to uncompressed point format (0x04 + x + y coordinates)
        x = public_numbers.x.to_bytes(32, 'big')
        y = public_numbers.y.to_bytes(32, 'big')
        uncompressed_point = b'\x04' + x + y

        # Base64 URL-safe encode
        public_key_b64 = base64.urlsafe_b64encode(uncompressed_point).decode('ascii').rstrip('=')

        # Convert private key to base64 for storage
        private_key_b64 = base64.urlsafe_b64encode(private_pem).decode('ascii').rstrip('=')

        # Create environment variables content
        env_content = f"""
# VAPID Keys for Browser Notifications
VAPID_PUBLIC_KEY={public_key_b64}
VAPID_PRIVATE_KEY={private_key_b64}
VAPID_SUBJECT=mailto:safevision.alerts@gmail.com
"""

        print("Keys generated successfully!")
        print(f"Public Key Length: {len(public_key_b64)}")
        print(f"Private Key Length: {len(private_key_b64)}")

        # Save to vapid.json for backup
        vapid_data = {
            "public_key": public_key_b64,
            "private_key": private_key_b64,
            "subject": "mailto:safevision.alerts@gmail.com"
        }

        with open('vapid.json', 'w') as f:
            json.dump(vapid_data, f, indent=2)

        print("\nSaved to vapid.json")

        # Show environment variables
        print("\n" + "=" * 50)
        print("ADD THESE TO YOUR .env FILE:")
        print("=" * 50)
        print(env_content)
        print("=" * 50)

        return True

    except ImportError as e:
        print(f"ERROR: Missing required library: {e}")
        print("Install required packages:")
        print("pip install cryptography")
        return False
    except Exception as e:
        print(f"ERROR: {e}")
        return False

if __name__ == "__main__":
    success = generate_vapid_keys()
    if success:
        print("SUCCESS: VAPID keys generated!")
        print("1. Copy the environment variables to your .env file")
        print("2. Restart your backend server")
        print("3. Test browser notifications")
    else:
        print("FAILED: Could not generate VAPID keys")
        print("Check error messages above")