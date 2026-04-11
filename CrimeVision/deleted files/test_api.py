import sys
sys.path.append('.')
from app.main_enhanced_final_fixed import app
from fastapi.testclient import TestClient
import json

# Create a TestClient instance for the FastAPI app
client = TestClient(app)

# Test the crimes endpoint
response = client.get('/api/crimes?limit=10')
print('Status Code:', response.status_code)
if response.status_code == 200:
    data = response.json()
    print('Response data type:', type(data))
    print('Number of crimes:', len(data) if isinstance(data, list) else 'Not a list')
    print('First few crimes:')
    for i, crime in enumerate(data[:3]):
        print(f'Crime {i+1}:', json.dumps(crime, indent=2, default=str))
        print('Available keys:', list(crime.keys()) if isinstance(crime, dict) else 'Not a dict')
else:
    print('Error response:', response.json())
