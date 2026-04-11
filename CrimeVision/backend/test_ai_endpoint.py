"""
Quick test to verify the AI route safety endpoint is working
"""
import requests
import json

# Test data
test_data = {
    "route_points": [
        {
            "latitude": 31.5204,
            "longitude": 74.3587,
            "area": "Model Town",
            "crime_type": "Burglary"
        },
        {
            "latitude": 31.5304,
            "longitude": 74.3687,
            "area": "Gulberg",
            "crime_type": "Theft"
        }
    ],
    "date": "2024-12-20"
}

# Test the endpoint
url = "http://localhost:8000/api/crimes/analyze-route-safety-ai"
print(f"Testing endpoint: {url}")
print(f"Request data: {json.dumps(test_data, indent=2)}")

try:
    response = requests.post(url, json=test_data, timeout=10)
    print(f"\n✅ Status Code: {response.status_code}")
    
    if response.ok:
        result = response.json()
        print(f"✅ Response: {json.dumps(result, indent=2)}")
    else:
        print(f"❌ Error: {response.text}")
        
except requests.exceptions.ConnectionError:
    print("❌ Connection Error: Backend server is not running!")
    print("   Please start the backend with: uvicorn main:app --host 0.0.0.0 --port 8000 --reload")
except Exception as e:
    print(f"❌ Error: {e}")
