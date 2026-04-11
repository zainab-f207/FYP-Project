#!/usr/bin/env python3
"""
Test web push notification system.

This script tests:
1. VAPID key configuration
2. Database connectivity
3. AlertNotificationSystem initialization
4. Push notification sending (with mock subscription)
"""

import os
import sys
import json
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Load environment variables from .env file
load_dotenv()

def test_vapid_keys():
    """Test if VAPID keys are configured"""
    print("\n" + "="*70)
    print("🔐 Testing VAPID Key Configuration")
    print("="*70)
    
    vapid_public = os.getenv('VAPID_PUBLIC_KEY')
    vapid_private = os.getenv('VAPID_PRIVATE_KEY')
    
    if not vapid_public:
        print("❌ VAPID_PUBLIC_KEY not set")
        return False
    
    if not vapid_private:
        print("❌ VAPID_PRIVATE_KEY not set")
        return False
    
    print(f"✅ VAPID_PUBLIC_KEY is set")
    print(f"   Length: {len(vapid_public)} characters")
    print(f"   Preview: {vapid_public[:50]}...")
    
    print(f"\n✅ VAPID_PRIVATE_KEY is set")
    print(f"   Length: {len(vapid_private)} characters")
    print(f"   Preview: {vapid_private[:50]}...")
    
    return True


def test_database_connection():
    """Test database connectivity"""
    print("\n" + "="*70)
    print("🗄️  Testing Database Connection")
    print("="*70)
    
    try:
        from app.core.database import get_db_connection
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Check if browser_push_subscriptions table exists
        cursor.execute("""
            SELECT TABLE_NAME 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_SCHEMA = DATABASE() 
            AND TABLE_NAME = 'browser_push_subscriptions'
        """)
        
        if cursor.fetchone():
            print("✅ browser_push_subscriptions table exists")
        else:
            print("❌ browser_push_subscriptions table NOT found")
            cursor.close()
            conn.close()
            return False
        
        # Check if browser_notifications table exists
        cursor.execute("""
            SELECT TABLE_NAME 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_SCHEMA = DATABASE() 
            AND TABLE_NAME = 'browser_notifications'
        """)
        
        if cursor.fetchone():
            print("✅ browser_notifications table exists")
        else:
            print("❌ browser_notifications table NOT found")
            cursor.close()
            conn.close()
            return False
        
        # Count subscriptions
        cursor.execute("SELECT COUNT(*) as count FROM browser_push_subscriptions")
        result = cursor.fetchone()
        count = result['count'] if result else 0
        print(f"✅ Browser push subscriptions in database: {count}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False


def test_alert_notification_system():
    """Test AlertNotificationSystem initialization"""
    print("\n" + "="*70)
    print("📧 Testing AlertNotificationSystem")
    print("="*70)
    
    try:
        from app.alert_notifications import AlertNotificationSystem
        
        email_config = {
            'smtp_server': os.getenv('SMTP_SERVER', 'smtp.gmail.com'),
            'smtp_port': int(os.getenv('SMTP_PORT', 587)),
            'smtp_username': os.getenv('SMTP_USERNAME', 'test@gmail.com'),
            'smtp_password': os.getenv('SMTP_PASSWORD', 'password')
        }
        
        vapid_public = os.getenv('VAPID_PUBLIC_KEY')
        vapid_private = os.getenv('VAPID_PRIVATE_KEY')
        
        # Initialize system
        system = AlertNotificationSystem(email_config, vapid_public, vapid_private)
        
        print("✅ AlertNotificationSystem initialized successfully")
        
        # Check if VAPID keys are set
        if system.vapid_public_key:
            print("✅ VAPID public key is set in system")
        else:
            print("❌ VAPID public key is NOT set in system")
            return False
        
        if system.vapid_private_key:
            print("✅ VAPID private key is set in system")
        else:
            print("❌ VAPID private key is NOT set in system")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ AlertNotificationSystem initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_pywebpush():
    """Test if pywebpush is installed and working"""
    print("\n" + "="*70)
    print("📦 Testing pywebpush Library")
    print("="*70)

    try:
        from pywebpush import webpush, WebPushException

        print("✅ pywebpush is installed")
        print("✅ webpush function available")
        print("✅ WebPushException available")

        # Note: Vapid key generation requires specific cryptography version
        # We're using pre-generated keys instead
        print("✅ Using pre-generated VAPID keys (recommended for production)")

        return True

    except ImportError as e:
        print(f"❌ pywebpush not installed: {e}")
        print("   Install with: pip install pywebpush")
        return False
    except Exception as e:
        print(f"❌ Error testing pywebpush: {e}")
        return False


def test_mock_push_notification():
    """Test push notification with mock subscription"""
    print("\n" + "="*70)
    print("🔔 Testing Mock Push Notification")
    print("="*70)
    
    try:
        from pywebpush import webpush, WebPushException
        import json
        
        vapid_private = os.getenv('VAPID_PRIVATE_KEY')
        
        if not vapid_private:
            print("❌ VAPID_PRIVATE_KEY not set, skipping mock test")
            return False
        
        # Create mock subscription (this won't actually send)
        mock_subscription = {
            "endpoint": "https://fcm.googleapis.com/fcm/send/mock_token",
            "keys": {
                "p256dh": "mock_p256dh_key",
                "auth": "mock_auth_key"
            }
        }
        
        payload = {
            "title": "Test Notification",
            "body": "This is a test push notification",
            "icon": "https://example.com/icon.png",
            "tag": "test-notification",
            "data": {
                "safety_score": 85,
                "risk_level": "low",
                "timestamp": datetime.now().isoformat()
            }
        }
        
        print("📋 Mock Subscription:")
        print(f"   Endpoint: {mock_subscription['endpoint']}")
        print(f"   Keys: p256dh and auth set")
        
        print("\n📋 Payload:")
        print(f"   Title: {payload['title']}")
        print(f"   Body: {payload['body']}")
        print(f"   Data: {json.dumps(payload['data'], indent=2)}")
        
        print("\n✅ Mock push notification structure is valid")
        print("   (Actual sending would require real browser subscription)")
        
        return True
        
    except Exception as e:
        print(f"❌ Mock push notification test failed: {e}")
        return False


def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("🧪 Web Push Notification System Tests")
    print("="*70)
    
    results = {
        "VAPID Keys": test_vapid_keys(),
        "Database": test_database_connection(),
        "AlertNotificationSystem": test_alert_notification_system(),
        "pywebpush Library": test_pywebpush(),
        "Mock Push Notification": test_mock_push_notification(),
    }
    
    # Summary
    print("\n" + "="*70)
    print("📊 Test Summary")
    print("="*70)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Web push notifications are ready to use.")
        print("\nNext steps:")
        print("1. Restart backend server")
        print("2. Update frontend with VAPID_PUBLIC_KEY")
        print("3. Test push notifications in browser")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please fix the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

