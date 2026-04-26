from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
import asyncio

# Request models
class TestAlertRequest(BaseModel):
    user_id: int
    alert_type: str  # "offline_scheduled" or "live_risk_zone"
    test_location: Optional[Dict[str, Any]] = None
    email: Optional[str] = None
    phone_number: Optional[str] = None

class AlertTestResponse(BaseModel):
    success: bool
    test_type: str
    results: Dict[str, bool]
    message: str
    user_data: Optional[Dict[str, Any]] = None

# Create router
test_router = APIRouter(prefix="/api/test", tags=["Alert Testing"])

@test_router.post("/trigger-alert", response_model=AlertTestResponse)
async def trigger_test_alert(request: TestAlertRequest):
    """
    Test both offline scheduler and live risk zone alerts via Swagger
    """
    try:
        from app.alert_notifications import AlertNotificationSystem
        from app.alert_tester import AlertTester
        
        # Use your actual email config from environment variables
        import os
        email_config = {
            'smtp_server': os.getenv('SMTP_SERVER', 'smtp.gmail.com'),
            'smtp_port': int(os.getenv('SMTP_PORT', 587)),
            'smtp_username': os.getenv('SMTP_USERNAME', 'your-email@gmail.com'),
            'smtp_password': os.getenv('SMTP_PASSWORD', 'your-app-password')
        }
        
        notification_system = AlertNotificationSystem(email_config)
        tester = AlertTester(notification_system)
        
        # Mock user data - you can modify this with real user data
        test_user = {
            'id': request.user_id,
            'username': 'test_user',
            'first_name': 'Test',
            'last_name': 'User',
            'email': request.email or 'test@example.com',
            'phone_number': request.phone_number or '+1234567890',
            'sms_enabled': bool(request.phone_number),
            'sms_carrier': 'att',
            'home_area': 'Test Area',
            'work_area': 'Test Work Area',
            'alert_radius': 5.0
        }
        
        if request.alert_type == "offline_scheduled":
            success = await tester.test_offline_scheduler_alerts(test_user)
            return AlertTestResponse(
                success=success,
                test_type="offline_scheduled",
                results={"email_sent": success, "sms_sent": success},
                message="Offline scheduler alert test completed",
                user_data=test_user
            )
            
        elif request.alert_type == "live_risk_zone":
            # Use provided location or default to high-risk area
            test_location = request.test_location or {
                'lat': 31.455023,  # Your high-risk coordinates
                'lng': 74.298945
            }
            success = await tester.test_live_risk_zone_alerts(test_user, test_location)
            return AlertTestResponse(
                success=success,
                test_type="live_risk_zone",
                results={"email_sent": success, "sms_sent": success},
                message=f"Live risk zone alert test completed for coordinates {test_location}",
                user_data=test_user
            )
        else:
            raise HTTPException(status_code=400, detail="Invalid alert type. Use 'offline_scheduled' or 'live_risk_zone'")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Test failed: {str(e)}")

@test_router.post("/test-high-risk-area")
async def test_high_risk_area_alerts():
    """
    Specifically test with your high-risk coordinates
    """
    try:
        from app.alert_notifications import AlertNotificationSystem
        from app.alert_tester import AlertTester
        
        import os
        email_config = {
            'smtp_server': os.getenv('SMTP_SERVER', 'smtp.gmail.com'),
            'smtp_port': int(os.getenv('SMTP_PORT', 587)),
            'smtp_username': os.getenv('SMTP_USERNAME', 'safevision.noreply@gmail.com'),
            'smtp_password': os.getenv('SMTP_PASSWORD', '')
        }
        
        notification_system = AlertNotificationSystem(email_config)
        tester = AlertTester(notification_system)
        
        # Test user - replace with actual user data
        test_user = {
            'id': 1,
            'username': 'high_risk_tester',
            'first_name': 'High',
            'last_name': 'Risk Tester',
            'email': 'zfayyaz881@gmail.com',  # CHANGE THIS
            'phone_number': '03247949009',  # CHANGE THIS if testing SMS
            'sms_enabled': True,
            'sms_carrier': 'att',
            'home_area': 'High Risk Test Area',
            'work_area': 'Test Work Area',
            'alert_radius': 5.0
        }
        
        # Your specific high-risk coordinates
        high_risk_location = {
            'lat': 31.455023,
            'lng': 74.298945,
            'address': 'High Risk Area, Lahore'
        }
        
        print(f"🚨 Testing high risk area: {high_risk_location}")
        
        # Test both alert types
        results = {}
        
        # Test live risk zone alert
        results['live_risk_zone'] = await tester.test_live_risk_zone_alerts(
            test_user, high_risk_location
        )
        
        # Test immediate risk alert
        results['immediate_risk'] = await tester.test_immediate_risk_alerts(test_user)
        
        return {
            "success": all(results.values()),
            "test_type": "high_risk_area_comprehensive",
            "coordinates_used": high_risk_location,
            "detailed_results": results,
            "message": f"High risk area test completed for coordinates {high_risk_location}",
            "user_notified": test_user['email']
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"High risk area test failed: {str(e)}")

@test_router.post("/test-multiple-locations")
async def test_multiple_high_risk_locations():
    """
    Test multiple high-risk locations including yours
    """
    high_risk_locations = [
        {
            'lat': 31.455023,
            'lng': 74.298945,
            'address': 'Primary High Risk Area, Lahore',
            'risk_level': 'Very High'
        },
        {
            'lat': 31.5204,
            'lng': 74.3587,
            'address': 'Secondary Risk Zone, Lahore', 
            'risk_level': 'High'
        },
        {
            'lat': 31.5497,
            'lng': 74.3436,
            'address': 'Tertiary Risk Area, Lahore',
            'risk_level': 'Medium-High'
        }
    ]
    
    try:
        from app.alert_notifications import AlertNotificationSystem
        from app.alert_tester import AlertTester
        
        import os
        email_config = {
            'smtp_server': os.getenv('SMTP_SERVER', 'smtp.gmail.com'),
            'smtp_port': int(os.getenv('SMTP_PORT', 587)),
            'smtp_username': os.getenv('SMTP_USERNAME', 'your-email@gmail.com'),
            'smtp_password': os.getenv('SMTP_PASSWORD', 'your-app-password')
        }
        
        notification_system = AlertNotificationSystem(email_config)
        tester = AlertTester(notification_system)
        
        test_user = {
            'id': 1,
            'username': 'multi_location_tester',
            'first_name': 'Multi',
            'last_name': 'Location Tester',
            'email': 'zfayyaz881@gmail.com',  # CHANGE THIS
            'phone_number': '03247949009',  # CHANGE THIS
            'sms_enabled': True,
            'sms_carrier': 'att'
        }
        
        results = {}
        
        for i, location in enumerate(high_risk_locations):
            print(f"📍 Testing location {i+1}: {location['address']}")
            
            success = await tester.test_live_risk_zone_alerts(test_user, location)
            results[location['address']] = {
                'success': success,
                'coordinates': f"{location['lat']}, {location['lng']}",
                'risk_level': location['risk_level']
            }
            
            # Small delay between tests
            await asyncio.sleep(1)
        
        return {
            "success": all(result['success'] for result in results.values()),
            "test_type": "multiple_high_risk_locations",
            "locations_tested": len(high_risk_locations),
            "detailed_results": results,
            "message": f"Tested {len(high_risk_locations)} high-risk locations"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Multiple locations test failed: {str(e)}")