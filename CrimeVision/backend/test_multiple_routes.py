"""
Test the /analyze_route_safety endpoint with multiple routes
"""

import requests
import json

# Test routes with different characteristics
test_routes = [
    {
        "name": "Short Route - Manhattan",
        "data": {
            "start_lat": 40.7128,
            "start_lng": -74.0060,
            "end_lat": 40.7200,
            "end_lng": -74.0000,
            "distance": 1.2,
            "duration": 5,
            "waypoints": []
        }
    },
    {
        "name": "Medium Route - Brooklyn",
        "data": {
            "start_lat": 40.6501,
            "start_lng": -73.9496,
            "end_lat": 40.6700,
            "end_lng": -73.9300,
            "distance": 5.0,
            "duration": 15,
            "waypoints": [
                {"lat": 40.6600, "lng": -73.9400}
            ]
        }
    },
    {
        "name": "Long Route - Queens",
        "data": {
            "start_lat": 40.7282,
            "start_lng": -73.7949,
            "end_lat": 40.7500,
            "end_lng": -73.8000,
            "distance": 10.0,
            "duration": 30,
            "waypoints": [
                {"lat": 40.7350, "lng": -73.8000},
                {"lat": 40.7400, "lng": -73.7950}
            ]
        }
    }
]

print("\n" + "="*70)
print("TESTING /analyze_route_safety WITH MULTIPLE ROUTES")
print("="*70)

all_passed = True

for test_route in test_routes:
    print(f"\n{'='*70}")
    print(f"Testing: {test_route['name']}")
    print(f"{'='*70}")
    
    try:
        response = requests.post(
            "http://localhost:8000/analyze_route_safety",
            json=test_route['data'],
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # Validate response
            score = data.get("overall_score", 0)
            level = data.get("safety_level", "unknown")
            alerts = data.get("alerts", [])
            factors = data.get("factors", {})
            
            print(f"✅ Status: {response.status_code}")
            print(f"✅ Overall Score: {score}")
            print(f"✅ Safety Level: {level}")
            print(f"✅ Alerts: {len(alerts)}")
            print(f"✅ Factors:")
            for key, value in factors.items():
                print(f"   - {key}: {value}")
            
            # Validate score range
            if not (10 <= score <= 100):
                print(f"❌ Score out of range: {score}")
                all_passed = False
            
            # Validate safety level
            if level not in ["high", "medium", "low"]:
                print(f"❌ Invalid safety level: {level}")
                all_passed = False
            
            # Validate factors
            required_factors = ["crime_rate", "lighting", "traffic", "emergency_services_proximity", "road_type"]
            for factor in required_factors:
                if factor not in factors:
                    print(f"❌ Missing factor: {factor}")
                    all_passed = False
            
            print(f"✅ PASSED")
            
        else:
            print(f"❌ Status: {response.status_code}")
            print(f"❌ Response: {response.text}")
            all_passed = False
            
    except requests.exceptions.ConnectionError:
        print(f"❌ Connection Error: Could not connect to http://localhost:8000")
        print(f"   Make sure the backend server is running!")
        all_passed = False
    except Exception as e:
        print(f"❌ Error: {e}")
        all_passed = False

print(f"\n{'='*70}")
if all_passed:
    print("✅ ALL TESTS PASSED!")
else:
    print("❌ SOME TESTS FAILED")
print(f"{'='*70}\n")

