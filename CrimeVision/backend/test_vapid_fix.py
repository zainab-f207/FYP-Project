#!/usr/bin/env python3
"""
Test VAPID Key Processing for Browser Notifications
"""
import base64
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

def test_vapid_key_processing():
    """Test the VAPID key processing logic"""
    print("=" * 60)
    print("TESTING VAPID KEY PROCESSING")
    print("=" * 60)

    # The current VAPID private key from .env
    vapid_private_key = "LS0tLS1CRUdJTiBQUklWQVRFIEtFWS0tLS0tCk1JR0hBZ0VBTUJNR0J5cUdTTTQ5QWdFR0NDcUdTTTQ5QXdFSEJHMHdhd0lCQVFRZ3dzTlZ4Q1lQZjNHWEdiYnQKTmUxREltUkVmMUwxbEMrOFA5Wk9lcmhRNE5paFJBTkNBQVF6UlJJRXZCQnRnOGt2ZlA2Qmw1Q2VickRGYXovVApBRUNTb3N2dUhzTG5ZN0ttSUNlR1lxR1ZIcEZDaTRXVlZGd1QyN1VDWlQ4SUJVMVhtanRNdG5rZAotLS0tLUVORCBQUklWQVRFIEtFWS0tLS0tCg"

    try:
        print("1. DECODING BASE64 TO PEM")
        decoded_key_bytes = base64.urlsafe_b64decode(vapid_private_key + '===')  # Add padding
        pem_key = decoded_key_bytes.decode('utf-8')
        print(f"PEM Key (first 50 chars): {pem_key[:50]}...")
        print(f"PEM Key (last 50 chars): ...{pem_key[-50:]}")

        print("\n2. LOADING PRIVATE KEY OBJECT")
        private_key_obj = serialization.load_pem_private_key(
            pem_key.encode('utf-8'),
            password=None
        )
        print(f"Private key object: {type(private_key_obj)}")

        print("\n3. EXTRACTING RAW PRIVATE KEY BYTES")
        private_number = private_key_obj.private_numbers().private_value
        private_bytes = private_number.to_bytes(32, 'big')
        print(f"Private key bytes length: {len(private_bytes)}")
        print(f"Private key bytes (hex): {private_bytes.hex()[:32]}...")

        print("\n4. CONVERTING TO BASE64URL FOR PYWEBPUSH")
        pywebpush_key = base64.urlsafe_b64encode(private_bytes).decode('ascii').rstrip('=')
        print(f"PyWebPush key: {pywebpush_key}")
        print(f"PyWebPush key length: {len(pywebpush_key)}")

        print("\n" + "=" * 60)
        print("SUCCESS: VAPID key processing completed successfully!")
        print("The converted key should work with pywebpush.")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        print("\n" + "=" * 60)
        print("FAILURE: VAPID key processing failed")
        print("=" * 60)
        return False

if __name__ == "__main__":
    success = test_vapid_key_processing()
    if success:
        print("\nThe VAPID key fix should resolve browser notification issues.")
        print("Restart the backend server to apply the changes.")
    else:
        print("\nVAPID key processing needs further investigation.")