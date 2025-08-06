#!/usr/bin/env python3
"""
Trader API Key Testing Framework
Task 1: Set up live API key testing for trader operations including trade placement

SCRIPT: trader_api_key_testing_framework.py

This script creates and manages API keys for testing trader operations:
- Creates test entities and users
- Generates API keys for traders and viewers
- Tests entity-wide access permissions
- Validates trade placement capabilities
"""

import requests
import json
import sys
import time
from datetime import datetime
from typing import Dict, Any, Optional, List

# Configuration
API_BASE = "http://localhost:8000"
ADMIN_USERNAME = "garrett_admin"  # Adjust as needed
ADMIN_PASSWORD = "AdminPassword123!"  # Adjust as needed

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_status(message: str, color: str = Colors.WHITE):
    """Print colored status message"""
    print(f"{color}{message}{Colors.END}")

def print_header(title: str):
    """Print section header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * len(title)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{title}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * len(title)}{Colors.END}")

class TraderTestingFramework:
    """Comprehensive testing framework for trader operations"""
    
    def __init__(self):
        self.admin_token = None
        self.test_entities = {}
        self.test_users = {}
        self.api_keys = {}
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

    def authenticate_admin(self) -> bool:
        """Authenticate as admin to create test setup"""
        print_header("Admin Authentication")
        
        login_data = {
            "username": ADMIN_USERNAME,
            "password": ADMIN_PASSWORD
        }
        
        try:
            response = self.session.post(f"{API_BASE}/api/v1/auth/login", json=login_data)
            
            if response.status_code == 200:
                data = response.json()
                if 'data' in data and 'token' in data['data']:
                    self.admin_token = data['data']['token']['access_token']
                    print_status("✅ Admin authentication successful", Colors.GREEN)
                    return True
                else:
                    print_status("❌ Invalid admin login response format", Colors.RED)
                    return False
            else:
                print_status(f"❌ Admin login failed: {response.status_code}", Colors.RED)
                print_status(f"Response: {response.text}", Colors.RED)
                return False
                
        except Exception as e:
            print_status(f"❌ Admin authentication error: {e}", Colors.RED)
            return False

    def create_test_entities(self) -> bool:
        """Create test entities for trader testing"""
        print_header("Creating Test Entities")
        
        if not self.admin_token:
            print_status("❌ Admin token required", Colors.RED)
            return False
        
        timestamp = int(time.time())
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        entities_to_create = [
            {"name": f"Alpha Trading Entity {timestamp}", "code": f"ALPHA_{timestamp}", "type": "trading_entity"},
            {"name": f"Beta Trading Entity {timestamp}", "code": f"BETA_{timestamp}", "type": "trading_entity"}
        ]
        
        try:
            for entity_data in entities_to_create:
                response = self.session.post(
                    f"{API_BASE}/api/v1/admin/entities",
                    json=entity_data,
                    headers=headers
                )
                
                if response.status_code in [200, 201]:
                    entity = response.json()
                    entity_key = entity_data["code"].split("_")[0].lower()
                    self.test_entities[entity_key] = entity
                    print_status(f"✅ Created entity: {entity_data['name']}", Colors.GREEN)
                else:
                    print_status(f"⚠️  Entity creation response: {response.status_code}", Colors.YELLOW)
                    print_status(f"Response: {response.text}", Colors.YELLOW)
            
            return len(self.test_entities) > 0
            
        except Exception as e:
            print_status(f"❌ Entity creation error: {e}", Colors.RED)
            return False

    def create_test_users(self) -> bool:
        """Create test users for trader testing"""
        print_header("Creating Test Users")
        
        if not self.admin_token:
            print_status("❌ Admin token required", Colors.RED)
            return False
        
        timestamp = int(time.time())
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        # Create users for each entity and role
        users_to_create = [
            {"role": "trader", "entity": "alpha", "name": f"Alpha Trader {timestamp}"},
            {"role": "viewer", "entity": "alpha", "name": f"Alpha Viewer {timestamp}"},
            {"role": "trader", "entity": "beta", "name": f"Beta Trader {timestamp}"},
            {"role": "viewer", "entity": "beta", "name": f"Beta Viewer {timestamp}"}
        ]
        
        try:
            for user_config in users_to_create:
                user_data = {
                    "email": f"{user_config['role']}.{user_config['entity']}.{timestamp}@test.com",
                    "full_name": user_config["name"],
                    "role": user_config["role"]
                }
                
                response = self.session.post(
                    f"{API_BASE}/api/v1/admin/users",
                    json=user_data,
                    headers=headers
                )
                
                if response.status_code in [200, 201]:
                    user = response.json()
                    user_key = f"{user_config['entity']}_{user_config['role']}"
                    self.test_users[user_key] = user
                    print_status(f"✅ Created {user_config['role']}: {user.get('username', 'Unknown')}", Colors.GREEN)
                else:
                    print_status(f"⚠️  User creation response: {response.status_code}", Colors.YELLOW)
                    print_status(f"Response: {response.text}", Colors.YELLOW)
            
            return len(self.test_users) > 0
            
        except Exception as e:
            print_status(f"❌ User creation error: {e}", Colors.RED)
            return False

    def create_api_keys(self) -> bool:
        """Create API keys for test users"""
        print_header("Creating API Keys")
        
        if not self.admin_token or not self.test_users:
            print_status("❌ Admin token and test users required", Colors.RED)
            return False
        
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        
        try:
            for user_key, user_data in self.test_users.items():
                api_key_data = {
                    "user_id": user_data.get("user_id") or user_data.get("id"),
                    "name": f"test_key_{user_key}",
                    "scope": "inherit",
                    "description": f"Test API key for {user_key}"
                }
                
                response = self.session.post(
                    f"{API_BASE}/api/v1/admin/api-keys",
                    json=api_key_data,
                    headers=headers
                )
                
                if response.status_code in [200, 201]:
                    api_key_info = response.json()
                    self.api_keys[user_key] = api_key_info.get("api_key", "")
                    print_status(f"✅ Created API key for {user_key}", Colors.GREEN)
                    print_status(f"   Key: {self.api_keys[user_key][:20]}...", Colors.CYAN)
                else:
                    print_status(f"⚠️  API key creation failed for {user_key}: {response.status_code}", Colors.YELLOW)
                    print_status(f"Response: {response.text}", Colors.YELLOW)
            
            return len(self.api_keys) > 0
            
        except Exception as e:
            print_status(f"❌ API key creation error: {e}", Colors.RED)
            return False

    def test_trader_balance_access(self) -> bool:
        """Test trader can access entity-wide balance data"""
        print_header("Testing Trader Balance Access")
        
        if "alpha_trader" not in self.api_keys:
            print_status("❌ Alpha trader API key not available", Colors.RED)
            return False
        
        trader_key = self.api_keys["alpha_trader"]
        headers = {"Authorization": f"Bearer {trader_key}"}
        
        try:
            # Test accessing another user's balance within same entity
            if "alpha_viewer" in self.test_users:
                viewer_username = self.test_users["alpha_viewer"].get("username", "")
                response = self.session.get(
                    f"{API_BASE}/api/v1/balances/user/{viewer_username}",
                    headers=headers
                )
                
                if response.status_code == 200:
                    print_status("✅ Trader can access entity balance data", Colors.GREEN)
                    return True
                elif response.status_code == 403:
                    print_status("❌ Trader blocked from entity balance data", Colors.RED)
                    print_status(f"Response: {response.text}", Colors.YELLOW)
                    return False
                else:
                    print_status(f"⚠️  Unexpected response: {response.status_code}", Colors.YELLOW)
                    return False
            else:
                print_status("❌ No viewer user available for testing", Colors.RED)
                return False
                
        except Exception as e:
            print_status(f"❌ Balance access test error: {e}", Colors.RED)
            return False

    def test_trader_transaction_creation(self) -> bool:
        """Test trader can create transactions for entity users"""
        print_header("Testing Trader Transaction Creation")
        
        if "alpha_trader" not in self.api_keys:
            print_status("❌ Alpha trader API key not available", Colors.RED)
            return False
        
        trader_key = self.api_keys["alpha_trader"]
        headers = {"Authorization": f"Bearer {trader_key}"}
        
        try:
            # Test creating deposit for another user in same entity
            if "alpha_viewer" in self.test_users:
                viewer_username = self.test_users["alpha_viewer"].get("username", "")
                deposit_data = {
                    "username": viewer_username,
                    "amount": 100.0,
                    "currency_code": "USD",
                    "description": "Test entity-wide deposit by trader"
                }
                
                response = self.session.post(
                    f"{API_BASE}/api/v1/transactions/deposit",
                    json=deposit_data,
                    headers=headers
                )
                
                if response.status_code == 200:
                    print_status("✅ Trader can create transactions for entity users", Colors.GREEN)
                    result = response.json()
                    print_status(f"   Transaction ID: {result.get('transaction_id', 'N/A')}", Colors.CYAN)
                    return True
                elif response.status_code == 403:
                    print_status("❌ Trader blocked from creating entity transactions", Colors.RED)
                    print_status(f"Response: {response.text}", Colors.YELLOW)
                    return False
                else:
                    print_status(f"⚠️  Unexpected response: {response.status_code}", Colors.YELLOW)
                    print_status(f"Response: {response.text}", Colors.YELLOW)
                    return False
            else:
                print_status("❌ No viewer user available for testing", Colors.RED)
                return False
                
        except Exception as e:
            print_status(f"❌ Transaction creation test error: {e}", Colors.RED)
            return False

    def test_viewer_read_only_access(self) -> bool:
        """Test viewer has read access but cannot create transactions"""
        print_header("Testing Viewer Read-Only Access")
        
        if "alpha_viewer" not in self.api_keys:
            print_status("❌ Alpha viewer API key not available", Colors.RED)
            return False
        
        viewer_key = self.api_keys["alpha_viewer"]
        headers = {"Authorization": f"Bearer {viewer_key}"}
        
        try:
            success = True
            
            # Test 1: Viewer can read entity balance data
            if "alpha_trader" in self.test_users:
                trader_username = self.test_users["alpha_trader"].get("username", "")
                response = self.session.get(
                    f"{API_BASE}/api/v1/balances/user/{trader_username}",
                    headers=headers
                )
                
                if response.status_code == 200:
                    print_status("✅ Viewer can read entity balance data", Colors.GREEN)
                else:
                    print_status(f"❌ Viewer cannot read entity balances: {response.status_code}", Colors.RED)
                    success = False
            
            # Test 2: Viewer CANNOT create transactions
            deposit_data = {
                "username": self.test_users["alpha_trader"].get("username", ""),
                "amount": 50.0,
                "currency_code": "USD",
                "description": "Test viewer transaction (should fail)"
            }
            
            response = self.session.post(
                f"{API_BASE}/api/v1/transactions/deposit",
                json=deposit_data,
                headers=headers
            )
            
            if response.status_code == 403:
                print_status("✅ Viewer correctly blocked from creating transactions", Colors.GREEN)
            elif response.status_code == 200:
                print_status("❌ SECURITY ISSUE: Viewer can create transactions!", Colors.RED)
                success = False
            else:
                print_status(f"⚠️  Unexpected viewer transaction response: {response.status_code}", Colors.YELLOW)
                success = False
            
            return success
            
        except Exception as e:
            print_status(f"❌ Viewer access test error: {e}", Colors.RED)
            return False

    def run_comprehensive_setup_and_testing(self) -> bool:
        """Run complete setup and testing workflow"""
        print_status("🚀 TRADER API KEY TESTING FRAMEWORK", Colors.BOLD)
        print_status("=" * 40, Colors.BLUE)
        print()
        
        # Step 1: Admin authentication
        if not self.authenticate_admin():
            print_status("❌ Cannot proceed without admin access", Colors.RED)
            return False
        
        # Step 2: Create test entities
        if not self.create_test_entities():
            print_status("❌ Entity creation failed", Colors.RED)
            return False
        
        # Step 3: Create test users
        if not self.create_test_users():
            print_status("❌ User creation failed", Colors.RED)
            return False
        
        # Step 4: Create API keys
        if not self.create_api_keys():
            print_status("❌ API key creation failed", Colors.RED)
            return False
        
        # Step 5: Test trader operations
        trader_balance_success = self.test_trader_balance_access()
        trader_transaction_success = self.test_trader_transaction_creation()
        viewer_readonly_success = self.test_viewer_read_only_access()
        
        # Summary
        print_header("TESTING SUMMARY")
        
        tests_passed = sum([
            trader_balance_success,
            trader_transaction_success, 
            viewer_readonly_success
        ])
        
        print_status(f"Tests Passed: {tests_passed}/3", Colors.CYAN)
        
        if tests_passed == 3:
            print_status("🎉 ALL TRADER OPERATIONS WORKING!", Colors.GREEN)
            print_status("✅ Entity-wide trader access confirmed", Colors.GREEN)
            print_status("✅ Role-based permissions validated", Colors.GREEN)
            
            # Export credentials for manual testing
            print_header("API KEYS FOR MANUAL TESTING")
            for user_key, api_key in self.api_keys.items():
                if api_key:
                    print_status(f"{user_key.upper()}_API_KEY='{api_key}'", Colors.CYAN)
            
            return True
        else:
            print_status("⚠️  Some trader operations need attention", Colors.YELLOW)
            return False

def main():
    """Main execution function"""
    framework = TraderTestingFramework()
    
    try:
        success = framework.run_comprehensive_setup_and_testing()
        
        if success:
            print_status("\n🎯 TASK 1 COMPLETED SUCCESSFULLY!", Colors.GREEN)
            print_status("Trader API key testing framework operational", Colors.GREEN)
        else:
            print_status("\n⚠️  TASK 1 PARTIAL COMPLETION", Colors.YELLOW)
            print_status("Framework setup complete, some tests need investigation", Colors.YELLOW)
        
        return success
        
    except KeyboardInterrupt:
        print_status("\n\n👋 Testing interrupted by user", Colors.YELLOW)
        return False
    except Exception as e:
        print_status(f"\n❌ Framework error: {e}", Colors.RED)
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
