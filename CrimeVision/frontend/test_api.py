import sys
import asyncio
from fastapi.testclient import TestClient

sys.path.append('D:/FYP/Project/CrimeVision/backend')

try:
    from main import app
    from app.dependencies import get_username_from_token
    
    app.dependency_overrides[get_username_from_token] = lambda: 'testuser'
    
    client = TestClient(app)
    response = client.get('/api/auth/me/stats?latitude=31.4697&longitude=74.2728&area=Johar%20Town')
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
except Exception as e:
    print(f"Error: {e}")
