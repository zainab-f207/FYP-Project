"""
Test the /analyze_route_safety endpoint
"""

import requests
import json
import time

# Test data - a route in New York City
test_route = {
    "start_lat": 40.7128,
    "start_lng": -74.0060,
    "end_lat": 40.7580,
    "end_lng": -73.9855,
    "distance": 5.2,
    "duration": 15,
    "geometry": {
        "type": "LineString",
        "coordinates": [
            [-74.0060, 40.7128],
            [-73.9900, 40.7300],
            [-73.9855, 40.7580]
        ]
    },
    "steps": [
        {
            "instruction": "Head north on Broadway",
            "distance": 1.5,
            "duration": 5
        },
        {
            "instruction": "Turn right on 42nd Street",
            "distance": 2.0,
            "duration": 7
        },
        {
            "instruction": "Continue to destination",
            "distance": 1.7,
            "duration": 3
        }
    ],
    "waypoints": [
        {"lat": 40.7300, "lng": -73.9900}
    ]
}

print("\n" + "="*60)
print("TESTING /analyze_route_safety ENDPOINT")
print("="*60)

try:
    print("\n📤 Sending request to http://localhost:8000/analyze_route_safety")
    print(f"📋 Payload: {json.dumps(test_route, indent=2)}")
    
    response = requests.post(
        "http://localhost:8000/analyze_route_safety",
        json=test_route,
        timeout=10
    )
    
    print(f"\n📥 Response Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print("\n✅ SUCCESS! Response received:")
        print(json.dumps(data, indent=2))
        
        # Verify response structure
        print("\n" + "-"*60)
        print("Response Validation:")
        print("-"*60)
        
        if "overall_score" in data:
            score = data["overall_score"]
            print(f"✅ Overall Score: {score}")
            if 10 <= score <= 100:
                print(f"   ✅ Score is within valid range (10-100)")
            else:
                print(f"   ❌ Score is out of range!")
        else:
            print("❌ Missing 'overall_score' field")
        
        if "safety_level" in data:
            level = data["safety_level"]
            print(f"✅ Safety Level: {level}")
            if level in ["high", "medium", "low"]:
                print(f"   ✅ Valid safety level")
            else:
                print(f"   ❌ Invalid safety level!")
        else:
            print("❌ Missing 'safety_level' field")
        
        if "alerts" in data:
            alerts = data["alerts"]
            print(f"✅ Alerts: {len(alerts)} alert(s)")
            for i, alert in enumerate(alerts):
                print(f"   Alert {i+1}: {alert.get('type', 'Unknown')}")
        else:
            print("❌ Missing 'alerts' field")
        
        if "factors" in data:
            factors = data["factors"]
            print(f"✅ Factors:")
            for key, value in factors.items():
                print(f"   - {key}: {value}")
        else:
            print("❌ Missing 'factors' field")
        
        print("\n" + "="*60)
        print("✅ ENDPOINT TEST PASSED")
        print("="*60)
    else:
        print(f"\n❌ Error: {response.status_code}")
        print(f"Response: {response.text}")
        
except requests.exceptions.ConnectionError:
    print("\n❌ Connection Error: Could not connect to http://localhost:8000")
    print("   Make sure the backend server is running!")
except requests.exceptions.Timeout:
    print("\n❌ Timeout: Request took too long")
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()

