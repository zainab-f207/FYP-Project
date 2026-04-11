# alert_tester.py
import asyncio
from datetime import datetime
from typing import Dict, Any
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException

class AlertTester:
    """Comprehensive alert testing system"""
    
    def __init__(self, notification_system):
        self.notification_system = notification_system
    
    async def test_offline_scheduler_alerts(self, user_data: Dict[str, Any]):
        """Test offline scheduler alerts (background monitoring)"""
        print("🧪 Testing Offline Scheduler Alerts...")
        
        # Simulate saved location monitoring
        test_alert = type('TestAlert', (), {
            'user_id': user_data.get('id', 1),
            'username': user_data.get('username', 'test_user'),
            'email': user_data.get('email', 'test@example.com'),
            'phone': user_data.get('phone_number', '+1234567890'),
            'latitude': 31.5204,
            'longitude': 74.3587,
            'address': "Test Home Location, Lahore",
            'risk_level': "Medium",
            'safety_score': 65,
            'high_risk_crimes': 2,
            'alert_type': "scheduled_monitoring",
            'message': "Scheduled location safety check"
        })()
        
        try:
            # Test email
            email_success = await self.notification_system.send_alert_email(
                test_alert, user_data.get('email', 'test@example.com')
            )
            
            # Test SMS if enabled
            sms_success = False
            if user_data.get('sms_enabled'):
                sms_success = await self.notification_system.send_alert_sms(
                    test_alert, 
                    user_data.get('phone_number', '+1234567890'),
                    user_data.get('sms_carrier', 'unknown')
                )
            
            print(f"✅ Offline Scheduler Test Results:")
            print(f"   📧 Email: {'Success' if email_success else 'Failed'}")
            print(f"   📱 SMS: {'Success' if sms_success else 'Failed'}")
            
            return email_success or sms_success
            
        except Exception as e:
            print(f"❌ Offline scheduler test failed: {e}")
            return False
    
    async def test_live_risk_zone_alerts(self, user_data: Dict[str, Any], test_location: Dict[str, float]):
        """Test live risk zone alerts (real-time detection)"""
        print("📍 Testing Live Risk Zone Alerts...")
        
        # Simulate entering high-risk zone
        test_alert = type('TestAlert', (), {
            'user_id': user_data.get('id', 1),
            'username': user_data.get('username', 'hafsa.fayyaz'),
            'email': user_data.get('email', 'zfayyaz881@gmail.com'),
            'phone': user_data.get('phone_number', '03247949009'),
            'latitude': test_location.get('lat', 31.455023),
            'longitude': test_location.get('lng', 74.298945),
            'address': "Test High Risk Zone, Lahore",
            'risk_level': "High",
            'safety_score': 35,
            'high_risk_crimes': 5,
            'alert_type': "live_high_risk_zone",
            'message': "Immediate high risk zone alert"
        })()
        
        try:
            # Test immediate email alert
            email_success = await self.notification_system.send_alert_email(
                test_alert, user_data.get('email', 'zfayyaz881@example.com')
            )
            
            # Test immediate SMS alert
            sms_success = False
            if user_data.get('sms_enabled'):
                sms_success = await self.notification_system.send_alert_sms(
                    test_alert, 
                    user_data.get('phone_number', '03247949009'),
                    user_data.get('sms_carrier', 'unknown')
                )
            
            print(f"✅ Live Risk Zone Test Results:")
            print(f"   📧 Email: {'Success' if email_success else 'Failed'}")
            print(f"   📱 SMS: {'Success' if sms_success else 'Failed'}")
            print(f"   🚨 Alert Type: Immediate High Risk")
            
            return email_success or sms_success
            
        except Exception as e:
            print(f"❌ Live risk zone test failed: {e}")
            return False
    
    async def test_immediate_risk_alerts(self, user_data: Dict[str, Any]):
        """Test immediate risk alerts for current location"""
        print("⚠️ Testing Immediate Risk Alerts...")
        
        test_alert = type('TestAlert', (), {
            'user_id': user_data.get('id', 1),
            'username': user_data.get('username', 'test_user'),
            'email': user_data.get('email', 'zfayyaz881@example.com'),
            'phone': user_data.get('phone_number', '03247949009'),
            'latitude': 31.455023,
            'longitude': 74.298945,
            'address': "Current Test Location",
            'risk_level': "High",
            'safety_score': 25,
            'high_risk_crimes': 8,
            'alert_type': "immediate_risk",
            'message': "Immediate risk detected at current location"
        })()
        
        try:
            # Test SMS for immediate alerts (most critical)
            sms_success = False
            if user_data.get('sms_enabled'):
                sms_success = await self.notification_system.send_alert_sms(
                    test_alert, 
                    user_data.get('phone_number', '+1234567890'),
                    user_data.get('sms_carrier', 'unknown')
                )
            
            # Also send email
            email_success = await self.notification_system.send_alert_email(
                test_alert, user_data.get('email', 'test@example.com')
            )
            
            print(f"✅ Immediate Risk Test Results:")
            print(f"   📧 Email: {'Success' if email_success else 'Failed'}")
            print(f"   📱 SMS: {'Success' if sms_success else 'Failed'}")
            print(f"   🚨 Priority: High - Immediate Action Required")
            
            return sms_success or email_success
            
        except Exception as e:
            print(f"❌ Immediate risk test failed: {e}")
            return False
    
    async def run_comprehensive_test(self, user_data: Dict[str, Any], test_location: Dict[str, float]):
        """Run all alert tests comprehensively"""
        print("🚀 Starting Comprehensive Alert System Test...")
        print("=" * 50)
        
        test_results = {}
        
        # Test 1: Offline Scheduler Alerts
        test_results['offline_scheduler'] = await self.test_offline_scheduler_alerts(user_data)
        
        # Test 2: Live Risk Zone Alerts
        test_results['live_risk_zone'] = await self.test_live_risk_zone_alerts(user_data, test_location)
        
        # Test 3: Immediate Risk Alerts
        test_results['immediate_risk'] = await self.test_immediate_risk_alerts(user_data)
        
        # Summary
        print("=" * 50)
        print("📊 TEST SUMMARY:")
        for test_name, result in test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"   {test_name.replace('_', ' ').title()}: {status}")
        
        all_passed = all(test_results.values())
        print(f"\nOverall Result: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")
        
        return test_results
    
# Add to your test_alerts.py file


