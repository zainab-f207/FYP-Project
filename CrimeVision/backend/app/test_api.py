import urllib.request
import json

data = json.dumps({
    'area': 'Bahria Orchard',
    'crime_type': 'Burglary',
    'date': '2024-12-05'
}).encode('utf-8')

req = urllib.request.Request(
    'http://127.0.0.1:8000/api/predict-risk',
    data=data,
    headers={'Content-Type': 'application/json'}
)

try:
    with urllib.request.urlopen(req) as response:
        result = json.loads(response.read().decode())
        print("API Response:", result)
except Exception as e:
    print("Error:", e)
