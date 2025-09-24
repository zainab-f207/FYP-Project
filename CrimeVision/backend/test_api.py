import sys
sys.path.append('.')
from app.main_enhanced_final_fixed import app
import json

# Test the crimes endpoint
with app.test_client() as client:
    response = client.get('/api/crimes?limit=10')
    print('Status Code:', response.status_code)
    if response.status_code == 200:
        data = response.get_json()
        print('Response data type:', type(data))
        print('Number of crimes:', len(data) if isinstance(data, list) else 'Not a list')
        print('First few crimes:')
        for i, crime in enumerate(data[:3]):
            print(f'Crime {i+1}:', json.dumps(crime, indent=2, default=str))
            print('Available keys:', list(crime.keys()) if isinstance(crime, dict) else 'Not a dict')
    else:
        print('Error response:', response.get_json())
