#!/usr/bin/env python3
"""
Admin Endpoints Testing Script
Tests all admin-related endpoints in CrimeVision backend
"""

import requests
import json
import sys
from typing import Optional, Dict, Any

class AdminAPITester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.token: Optional[str] = None
        self.session = requests.Session()

    def login(self, username: str, password: str) -> bool:
        """Login and get access token"""
        try:
            response = self.session.post(
                f"{self.base_url}/auth/login",
                json={"username": username, "password": password}
            )

            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                self.session.headers.update({"Authorization": f"Bearer {self.token}"})
                print(f"✅ Login successful for user: {username}")
                return True
            else:
                print(f"❌ Login failed: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            print(f"❌ Login error: {e}")
            return False

    def test_endpoint(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Test an endpoint and return response info"""
        try:
            url = f"{self.base_url}{endpoint}"
            response = self.session.request(method, url, **kwargs)

            result = {
                "status_code": response.status_code,
                "success": response.status_code < 400,
                "endpoint": endpoint,
                "method": method
            }

            try:
                result["data"] = response.json()
            except:
                result["data"] = response.text

            return result

        except Exception as e:
            return {
                "status_code": None,
                "success": False,
                "endpoint": endpoint,
                "method": method,
                "error": str(e)
            }

    def run_tests(self):
        """Run all admin endpoint tests"""
        print("🚀 Starting Admin API Tests\n")

        # Test 1: Get admin list
        print("1. Testing GET /admin/list")
        result = self.test_endpoint("GET", "/admin/list")
        if result["success"]:
            print(f"   ✅ Success: {len(result['data'].get('admins', []))} admins found")
        else:
            print(f"   ❌ Failed: {result['status_code']} - {result.get('data', 'Unknown error')}")

        # Test 2: Get admin stats
        print("\n2. Testing GET /admin/stats")
        result = self.test_endpoint("GET", "/admin/stats")
        if result["success"]:
            stats = result["data"]
            print(f"   ✅ Success: {stats.get('total_users', 0)} users, {stats.get('total_crimes', 0)} crimes")
        else:
            print(f"   ❌ Failed: {result['status_code']} - {result.get('data', 'Unknown error')}")

        # Test 3: Get users
        print("\n3. Testing GET /admin/users")
        result = self.test_endpoint("GET", "/admin/users?limit=5")
        if result["success"]:
            users = result["data"].get("users", [])
            print(f"   ✅ Success: {len(users)} users retrieved (showing first 5)")
            if users:
                print(f"   📋 Sample user: {users[0].get('username', 'N/A')}")
        else:
            print(f"   ❌ Failed: {result['status_code']} - {result.get('data', 'Unknown error')}")

        # Test 4: Get notifications
        print("\n4. Testing GET /admin/notifications")
        result = self.test_endpoint("GET", "/admin/notifications")
        if result["success"]:
            notifications = result["data"].get("notifications", [])
            print(f"   ✅ Success: {len(notifications)} notifications")
        else:
            print(f"   ❌ Failed: {result['status_code']} - {result.get('data', 'Unknown error')}")

        # Test 5: Get audit logs
        print("\n5. Testing GET /admin/audit-logs")
        result = self.test_endpoint("GET", "/admin/audit-logs?limit=5")
        if result["success"]:
            logs = result["data"].get("audit_logs", [])
            print(f"   ✅ Success: {len(logs)} audit logs retrieved")
        else:
            print(f"   ❌ Failed: {result['status_code']} - {result.get('data', 'Unknown error')}")

        # Test 6: Register new admin (requires super admin)
        print("\n6. Testing POST /admin/register")
        admin_data = {
            "name": "Test Admin",
            "email": "test.admin@crimevision.com",
            "password": "testpassword123",
            "department": "Testing",
            "permissions": ["read_users", "view_reports"],
            "phone": "+1234567890"
        }
        result = self.test_endpoint("POST", "/admin/register", json=admin_data)
        if result["success"]:
            print(f"   ✅ Success: Admin registered - {result['data'].get('username', 'N/A')}")
        else:
            print(f"   ❌ Failed: {result['status_code']} - {result.get('data', 'Unknown error')}")
            if "Only super admins can register" in str(result.get('data', '')):
                print("   ℹ️  Note: This test requires super admin privileges")

        # Test 7: Bulk user actions (requires super admin)
        print("\n7. Testing POST /admin/user-bulk (suspend action)")
        result = self.test_endpoint("POST", "/admin/user-bulk?action=suspend&user_ids=999")
        if result["success"]:
            print(f"   ✅ Success: Bulk action completed")
        else:
            print(f"   ❌ Failed: {result['status_code']} - {result.get('data', 'Unknown error')}")
            if "super admins" in str(result.get('data', '')):
                print("   ℹ️  Note: This test requires super admin privileges")

        print("\n🏁 Admin API Tests Completed")

def main():
    if len(sys.argv) < 3:
        print("Usage: python test_admin_endpoints.py <username> <password>")
        print("Example: python test_admin_endpoints.py superadmin mypassword")
        sys.exit(1)

    username = sys.argv[1]
    password = sys.argv[2]

    tester = AdminAPITester()

    print(f"🔐 Attempting login with username: {username}")
    if not tester.login(username, password):
        print("❌ Cannot proceed without successful login")
        sys.exit(1)

    tester.run_tests()

if __name__ == "__main__":
    main()
