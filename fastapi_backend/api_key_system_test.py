#!/usr/bin/env python3
"""
API Key System End-to-End Test
Verifies the complete API key authentication system is working
"""

import requests
import json
import time
from typing import Optional, Dict, Any


class APIKeySystemTester:
    """Test the complete API key authentication system"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.admin_api_key: Optional[str] = None
        self.test_api_key: Optional[str] = None
        self.test_user_id: Optional[str] = None
    
    def test_health_check(self) -> bool:
        """Test that the API is running"""
        print("🏥 Testing health check...")
        
        try:
            response = requests.get(f"{self.base_url}/health")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ API is healthy - Version: {data.get('version')}")
                print(f"   Authentication: {data.get('authentication')}")
                return True
            else:
                print(f"❌ Health check failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Health check error: {e}")
            return False
    
    def test_root_endpoint(self) -> bool:
        """Test root endpoint shows API key authentication"""
        print("🏠 Testing root endpoint...")
        
        try:
            response = requests.get(f"{self.base_url}/")
            
            if response.status_code == 200:
                data = response.json()
                auth_method = data.get('authentication', '')
                
                if 'API Key' in auth_method:
                    print("✅ Root endpoint shows API key authentication")
                    print(f"   Auth method: {auth_method}")
                    return True
                else:
                    print(f"❌ Authentication method: {auth_method}")
                    return False
            else:
                print(f"❌ Root endpoint failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Root endpoint error: {e}")
            return False
    
    def test_unauthenticated_access(self) -> bool:
        """Test that protected endpoints require authentication"""
        print("🔒 Testing unauthenticated access...")
        
        protected_endpoints = [
            "/api/v1/users",
            "/api/v1/balances", 
            "/api/v1/transactions",
            "/api/v1/admin/api-keys"
        ]
        
        all_protected = True
        
        for endpoint in protected_endpoints:
            try:
                response = requests.get(f"{self.base_url}{endpoint}")
                
                if response.status_code == 401:
                    print(f"✅ {endpoint} properly protected")
                else:
                    print(f"❌ {endpoint} not protected (status: {response.status_code})")
                    all_protected = False
                    
            except Exception as e:
                print(f"❌ Error testing {endpoint}: {e}")
                all_protected = False
        
        return all_protected
    
    def test_invalid_api_key(self) -> bool:
        """Test that invalid API keys are rejected"""
        print("🔑 Testing invalid API key...")
        
        invalid_keys = [
            "invalid_key",
            "btapi_invalid",
            "btapi_1234567890123456_invalid",
            ""
        ]
        
        for invalid_key in invalid_keys:
            try:
                headers = {"Authorization": f"Bearer {invalid_key}"}
                response = requests.get(f"{self.base_url}/api/v1/balances", headers=headers)
                
                if response.status_code == 401:
                    print(f"✅ Invalid key rejected: {invalid_key[:20]}...")
                else:
                    print(f"❌ Invalid key accepted: {invalid_key[:20]}... (status: {response.status_code})")
                    return False
                    
            except Exception as e:
                print(f"❌ Error testing invalid key: {e}")
                return False
        
        return True
    
    def create_admin_api_key(self, admin_username: str, admin_password: str) -> bool:
        """Create an API key for admin testing (requires existing admin account)"""
        print("👑 Creating admin API key...")
        
        # This is a placeholder - in real implementation, you'd need to:
        # 1. Login with admin credentials to get JWT
        # 2. Use JWT to create an API key via admin endpoints
        # 3. Store the API key for further testing
        
        # For now, assume admin manually provides an API key
        print("⚠️  Manual step required:")
        print("   1. Create admin API key via admin interface")
        print("   2. Set ADMIN_API_KEY environment variable")
        print("   3. Run tests with: ADMIN_API_KEY=<key> python test_api_keys.py")
        
        import os
        admin_key = os.getenv('ADMIN_API_KEY')
        
        if admin_key:
            self.admin_api_key = admin_key
            print(f"✅ Using admin API key: {admin_key[:25]}...")
            return True
        else:
            print("❌ No admin API key provided")
            return False
    
    def test_admin_endpoints(self) -> bool:
        """Test admin API key management endpoints"""
        if not self.admin_api_key:
            print("⚠️  Skipping admin endpoint tests (no admin API key)")
            return True
        
        print("🛠️ Testing admin endpoints...")
        
        headers = {"Authorization": f"Bearer {self.admin_api_key}"}
        
        # Test list API keys
        try:
            response = requests.get(f"{self.base_url}/api/v1/admin/api-keys", headers=headers)
            
            if response.status_code == 200:
                print("✅ Admin can list API keys")
                data = response.json()
                print(f"   Found {data.get('total_count', 0)} API keys")
            else:
                print(f"❌ Admin list keys failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Admin endpoint error: {e}")
            return False
        
        return True
    
    def test_api_key_creation(self) -> bool:
        """Test creating a new API key via admin endpoint"""
        if not self.admin_api_key:
            print("⚠️  Skipping API key creation test (no admin API key)")
            return True
        
        print("🔧 Testing API key creation...")
        
        headers = {
            "Authorization": f"Bearer {self.admin_api_key}",
            "Content-Type": "application/json"
        }
        
        # First, we need a user ID - try to find one
        try:
            response = requests.get(f"{self.base_url}/api/v1/admin/users", headers=headers)
            
            if response.status_code == 200:
                users = response.json().get('data', [])
                if users:
                    test_user = users[0]
                    self.test_user_id = test_user['id']
                    print(f"✅ Found test user: {test_user['username']}")
                else:
                    print("❌ No users found for testing")
                    return False
            else:
                print(f"❌ Could not get users: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Error getting users: {e}")
            return False
        
        # Create API key for test user
        try:
            create_data = {
                "user_id": self.test_user_id,
                "name": "Test API Key",
                "description": "Automated test key",
                "permissions_scope": "inherit"
            }
            
            response = requests.post(
                f"{self.base_url}/api/v1/admin/api-keys",
                headers=headers,
                json=create_data
            )
            
            if response.status_code == 200:
                data = response.json()
                self.test_api_key = data.get('api_key')
                print("✅ Successfully created test API key")
                print(f"   Key ID: {data.get('key_info', {}).get('key_id')}")
                return True
            else:
                print(f"❌ API key creation failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ API key creation error: {e}")
            return False
    
    def test_api_key_authentication(self) -> bool:
        """Test using the created API key for authentication"""
        if not self.test_api_key:
            print("⚠️  Skipping API key authentication test (no test key)")
            return True
        
        print("🔐 Testing API key authentication...")
        
        headers = {"Authorization": f"Bearer {self.test_api_key}"}
        
        # Test various endpoints
        test_endpoints = [
            "/api/v1/balances",
            "/api/v1/transactions", 
            "/api/v1/currencies"
        ]
        
        for endpoint in test_endpoints:
            try:
                response = requests.get(f"{self.base_url}{endpoint}", headers=headers)
                
                if response.status_code in [200, 404]:  # 404 is OK if no data
                    print(f"✅ {endpoint} accessible with API key")
                else:
                    print(f"❌ {endpoint} failed: {response.status_code}")
                    print(f"   Response: {response.text}")
                    return False
                    
            except Exception as e:
                print(f"❌ Error testing {endpoint}: {e}")
                return False
        
        return True
    
    def test_api_key_permissions(self) -> bool:
        """Test API key permission scopes"""
        if not self.test_api_key:
            print("⚠️  Skipping permission tests (no test key)")
            return True
        
        print("🎯 Testing API key permissions...")
        
        headers = {"Authorization": f"Bearer {self.test_api_key}"}
        
        # Test that non-admin key cannot access admin endpoints
        try:
            response = requests.get(f"{self.base_url}/api/v1/admin/api-keys", headers=headers)
            
            if response.status_code == 403:
                print("✅ Non-admin API key properly denied admin access")
                return True
            else:
                print(f"❌ Non-admin key got admin access: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Permission test error: {e}")
            return False
    
    def cleanup_test_resources(self) -> bool:
        """Clean up test API keys"""
        if not self.admin_api_key or not self.test_api_key:
            return True
        
        print("🧹 Cleaning up test resources...")
        
        # Extract key ID from test API key
        try:
            parts = self.test_api_key.split('_')
            if len(parts) >= 2:
                key_id = f"{parts[0]}_{parts[1]}"
                
                headers = {"Authorization": f"Bearer {self.admin_api_key}"}
                
                response = requests.delete(
                    f"{self.base_url}/api/v1/admin/api-keys/{key_id}",
                    headers=headers
                )
                
                if response.status_code == 200:
                    print("✅ Test API key cleaned up")
                else:
                    print(f"⚠️  Could not clean up test key: {response.status_code}")
                
        except Exception as e:
            print(f"⚠️  Cleanup error: {e}")
        
        return True
    
    def run_all_tests(self) -> bool:
        """Run all tests in sequence"""
        print("🧪 API Key System End-to-End Tests")
        print("=" * 40)
        
        tests = [
            ("Health Check", self.test_health_check),
            ("Root Endpoint", self.test_root_endpoint),
            ("Unauthenticated Access", self.test_unauthenticated_access),
            ("Invalid API Keys", self.test_invalid_api_key),
            ("Admin API Key Setup", lambda: self.create_admin_api_key("admin", "password")),
            ("Admin Endpoints", self.test_admin_endpoints),
            ("API Key Creation", self.test_api_key_creation),
            ("API Key Authentication", self.test_api_key_authentication),
            ("API Key Permissions", self.test_api_key_permissions),
            ("Cleanup", self.cleanup_test_resources)
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            print(f"\\n🔬 {test_name}...")
            try:
                if test_func():
                    passed += 1
                    print(f"✅ {test_name} PASSED")
                else:
                    print(f"❌ {test_name} FAILED")
            except Exception as e:
                print(f"❌ {test_name} ERROR: {e}")
        
        print(f"\\n📊 Test Results: {passed}/{total} passed")
        
        if passed == total:
            print("🎉 All tests passed! API key system is working correctly.")
            return True
        else:
            print("⚠️  Some tests failed. Please check the system configuration.")
            return False


def main():
    """Run the API key system tests"""
    import sys
    
    # Allow custom base URL
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    
    tester = APIKeySystemTester(base_url)
    success = tester.run_all_tests()
    
    if success:
        print("\\n✅ API Key Authentication Migration Verification Complete!")
        sys.exit(0)
    else:
        print("\\n❌ Some tests failed. Check system configuration.")
        sys.exit(1)


if __name__ == "__main__":
    main()
