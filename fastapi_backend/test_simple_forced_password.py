#!/usr/bin/env python3
"""
Simple Forced Password Change Test
Works with the actual API response format
"""

import requests
import json
import time

def test_complete_flow():
    """Test the complete forced password change flow"""
    
    base_url = "http://localhost:8000"
    
    print("🧪 Testing Complete Forced Password Change Flow")
    print("=" * 50)
    
    # Step 1: Create user
    print("1️⃣  Creating user...")
    
    user_data = {
        "email": f"testuser{int(time.time())}@example.com",
        "full_name": "Test User",
        "role": "trader"
    }
    
    response = requests.post(f"{base_url}/api/v1/admin/users", json=user_data)
    
    if response.status_code not in [200, 201]:
        print(f"❌ User creation failed: {response.status_code}")
        print(f"   Response: {response.text}")
        return False
    
    result = response.json()
    if not result.get("success"):
        print(f"❌ User creation failed: {result}")
        return False
    
    print(f"✅ User created successfully!")
    print(f"   Email: {result['email']}")
    print(f"   Username: {result['username']}")
    print(f"   Temp Password: {result['temporary_password']}")
    
    # Step 2: Try login (should be blocked)
    print("\n2️⃣  Testing login with temporary password...")
    
    login_data = {
        "username": result["email"],
        "password": result["temporary_password"]
    }
    
    response = requests.post(f"{base_url}/api/v1/auth/login", json=login_data)
    
    if response.status_code == 200:
        login_result = response.json()
        if login_result.get("must_change_password"):
            print("✅ Login correctly blocked - password change required!")
            temp_token = login_result.get("temporary_token")
            print(f"   Temporary token received: {temp_token[:20]}...")
        else:
            print("❌ Login should have been blocked!")
            return False
    else:
        print(f"❌ Login failed: {response.status_code}")
        print(f"   Response: {response.text}")
        return False
    
    # Step 3: Change password
    print("\n3️⃣  Changing password...")
    
    change_data = {
        "current_password": "",
        "new_password": "NewSecurePassword123!"
    }
    
    headers = {"Authorization": f"Bearer {temp_token}"}
    response = requests.post(f"{base_url}/api/v1/auth/change-password", 
                           json=change_data, headers=headers)
    
    if response.status_code == 200:
        change_result = response.json()
        print("✅ Password changed successfully!")
        access_token = change_result.get("access_token")
    else:
        print(f"❌ Password change failed: {response.status_code}")
        print(f"   Response: {response.text}")
        return False
    
    # Step 4: Normal login
    print("\n4️⃣  Testing normal login...")
    
    login_data = {
        "username": result["email"],
        "password": "NewSecurePassword123!"
    }
    
    response = requests.post(f"{base_url}/api/v1/auth/login", json=login_data)
    
    if response.status_code == 200:
        final_result = response.json()
        if not final_result.get("must_change_password"):
            print("✅ Normal login successful!")
        else:
            print("❌ Password change requirement not cleared!")
            return False
    else:
        print(f"❌ Normal login failed: {response.status_code}")
        print(f"   Response: {response.text}")
        return False
    
    print("\n🎉 ALL TESTS PASSED!")
    print("✅ Forced password change system is working correctly!")
    
    return True

if __name__ == "__main__":
    success = test_complete_flow()
    exit(0 if success else 1)
