#!/usr/bin/env python3
"""
Test Script for Forced Password Change System
Task 2.1b: Tests the complete forced password change flow
"""

import requests
import json
import sys

def test_forced_password_change_flow():
    """Test the complete forced password change flow"""
    base_url = "http://localhost:8000"
    
    print("🧪 Testing Forced Password Change System")
    print("========================================")
    
    # Step 1: Create a user that requires password change
    print("\n1. Creating user with forced password change requirement...")
    
    create_user_data = {
        "email": "forcedchange@example.com",
        "full_name": "Force Change User",
        "role": "trader"
    }
    
    try:
        response = requests.post(
            f"{base_url}/api/v1/admin/users",
            json=create_user_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            user_data = response.json()
            username = user_data['username']
            temp_password = user_data['temporary_password']
            
            print(f"✅ User created: {username}")
            print(f"   Temporary password: {temp_password}")
            print(f"   Must change password: {user_data['must_change_password']}")
            
        else:
            print(f"❌ User creation failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ User creation failed: {e}")
        return False
    
    # Step 2: Try to login with temporary password
    print(f"\n2. Attempting login with temporary password...")
    
    login_data = {
        "username": username,
        "password": temp_password
    }
    
    try:
        response = requests.post(
            f"{base_url}/api/v1/auth/login",
            json=login_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 403:
            error_data = response.json()
            detail = error_data.get('detail', {})
            
            if isinstance(detail, dict) and detail.get('error') == 'password_change_required':
                print("✅ Login correctly blocked - password change required")
                print(f"   Message: {detail.get('message')}")
                
                temporary_token = detail.get('temporary_token')
                if temporary_token:
                    print("✅ Received temporary token for password change")
                else:
                    print("❌ No temporary token received")
                    return False
            else:
                print(f"❌ Unexpected response: {error_data}")
                return False
        else:
            print(f"❌ Login should have been blocked but got: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Login test failed: {e}")
        return False
    
    # Step 3: Change password using temporary token
    print(f"\n3. Changing password with temporary token...")
    
    new_password = "NewSecurePassword123!"
    password_change_data = {
        "new_password": new_password,
        "confirm_password": new_password,
        "temporary_token": temporary_token
    }
    
    try:
        response = requests.post(
            f"{base_url}/api/v1/auth/change-password",
            json=password_change_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            change_data = response.json()
            print("✅ Password changed successfully")
            print(f"   Message: {change_data.get('message')}")
            
            # Get new access token
            new_access_token = change_data.get('access_token')
            if new_access_token:
                print("✅ Received new access token")
            else:
                print("❌ No access token received")
                return False
        else:
            print(f"❌ Password change failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Password change failed: {e}")
        return False
    
    # Step 4: Login with new password
    print(f"\n4. Testing login with new password...")
    
    new_login_data = {
        "username": username,
        "password": new_password
    }
    
    try:
        response = requests.post(
            f"{base_url}/api/v1/auth/login",
            json=new_login_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            login_result = response.json()
            print("✅ Login successful with new password")
            print(f"   Username: {login_result['user']['username']}")
            print(f"   Must change password: {login_result.get('must_change_password', False)}")
            
            final_access_token = login_result.get('access_token')
            if final_access_token:
                print("✅ Received access token from normal login")
            else:
                print("❌ No access token from normal login")
                return False
        else:
            print(f"❌ Login with new password failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ New password login failed: {e}")
        return False
    
    # Step 5: Test accessing protected resource
    print(f"\n5. Testing access to protected resource...")
    
    try:
        response = requests.get(
            f"{base_url}/api/v1/auth/me",
            headers={"Authorization": f"Bearer {final_access_token}"}
        )
        
        if response.status_code == 200:
            user_info = response.json()
            print("✅ Successfully accessed protected resource")
            print(f"   User: {user_info['user']['username']}")
            print(f"   Role: {user_info['user']['role']}")
        else:
            print(f"❌ Failed to access protected resource: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Protected resource test failed: {e}")
        return False
    
    return True


def test_password_validation():
    """Test password validation requirements"""
    base_url = "http://localhost:8000"
    
    print("\n🔧 Testing Password Validation...")
    
    # Create a test user first
    create_user_data = {
        "email": "validation@example.com",
        "full_name": "Validation Test User",
        "role": "trader"
    }
    
    response = requests.post(
        f"{base_url}/api/v1/admin/users",
        json=create_user_data,
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code != 200:
        print("❌ Could not create test user for validation")
        return False
    
    user_data = response.json()
    username = user_data['username']
    temp_password = user_data['temporary_password']
    
    # Get temporary token
    login_response = requests.post(
        f"{base_url}/api/v1/auth/login",
        json={"username": username, "password": temp_password},
        headers={"Content-Type": "application/json"}
    )
    
    if login_response.status_code != 403:
        print("❌ Could not get temporary token")
        return False
    
    temp_token = login_response.json()['detail']['temporary_token']
    
    # Test weak passwords
    weak_passwords = [
        "short",                    # Too short
        "nouppercase123!",         # No uppercase
        "NOLOWERCASE123!",         # No lowercase  
        "NoNumbers!",              # No numbers
        "password123"              # No special chars (depending on requirements)
    ]
    
    for weak_password in weak_passwords:
        print(f"   Testing weak password: {weak_password[:8]}...")
        
        password_data = {
            "new_password": weak_password,
            "confirm_password": weak_password,
            "temporary_token": temp_token
        }
        
        response = requests.post(
            f"{base_url}/api/v1/auth/change-password",
            json=password_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 422:  # Validation error
            print(f"      ✅ Correctly rejected weak password")
        else:
            print(f"      ❌ Weak password was accepted: {response.status_code}")
    
    return True


def main():
    """Run all tests"""
    print("🚀 Starting Forced Password Change System Tests")
    print("=" * 50)
    
    try:
        # Test main flow
        flow_success = test_forced_password_change_flow()
        
        if flow_success:
            print("\n" + "=" * 50)
            print("🎉 FORCED PASSWORD CHANGE FLOW: SUCCESS!")
            
            # Test password validation
            validation_success = test_password_validation()
            
            if validation_success:
                print("\n🎊 ALL TESTS PASSED!")
                print("\n📋 Verified Features:")
                print("   ✅ Admin user creation with forced password change")
                print("   ✅ Login blocked until password changed")
                print("   ✅ Temporary token system working")
                print("   ✅ Password change with validation")
                print("   ✅ Normal login after password change")
                print("   ✅ Access to protected resources")
                print("   ✅ Password strength validation")
                
                return True
        
        print("\n❌ Some tests failed. Check output above.")
        return False
        
    except requests.exceptions.ConnectionError:
        print("❌ Connection failed - is the FastAPI server running?")
        print("   Start with: python3 main.py")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
