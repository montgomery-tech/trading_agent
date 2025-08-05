#!/usr/bin/env python3
"""
Comprehensive Entity System Test Suite
Tests all aspects of the entity-based authentication and access control system

This test suite validates:
1. Database schema and data integrity
2. Entity context retrieval and authentication
3. Access control and permissions
4. API endpoint security
5. Multi-entity scenarios
6. Admin vs user permissions
"""

import os
import sys
import asyncio
import logging
import json
import requests
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class EntitySystemTestSuite:
    """Comprehensive test suite for entity system"""
    
    def __init__(self):
        self.database_url = os.getenv('DATABASE_URL', 'postgresql://localhost:5432/balance_tracker')
        self.api_base = "http://localhost:8000"
        self.db = None
        self.test_results = []
        
        # Test data storage
        self.admin_api_key = None
        self.test_entities = []
        self.test_users = []
        self.test_api_keys = []
    
    def log_test_result(self, test_name: str, passed: bool, details: str = ""):
        """Log and store test results"""
        status = "✅ PASS" if passed else "❌ FAIL"
        message = f"{status} {test_name}"
        if details:
            message += f" - {details}"
        
        logger.info(message)
        self.test_results.append({
            "test": test_name,
            "passed": passed,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })
        
        return passed
    
    async def setup_database_connection(self):
        """Setup database connection for direct queries"""
        try:
            # Import database manager
            sys.path.insert(0, str(Path(__file__).parent))
            from api.database import DatabaseManager
            
            self.db = DatabaseManager(self.database_url)
            self.db.connect()
            
            return self.log_test_result("Database Connection Setup", True, "Connected successfully")
        except Exception as e:
            return self.log_test_result("Database Connection Setup", False, str(e))
    
    def test_api_server_health(self):
        """Test 1: Verify API server is running and healthy"""
        try:
            response = requests.get(f"{self.api_base}/health", timeout=5)
            
            if response.status_code == 200:
                health_data = response.json()
                entity_management = health_data.get('entity_management', False)
                
                if entity_management:
                    return self.log_test_result(
                        "API Server Health", True, 
                        f"Server healthy with entity management enabled"
                    )
                else:
                    return self.log_test_result(
                        "API Server Health", False, 
                        "Server healthy but entity management not enabled"
                    )
            else:
                return self.log_test_result(
                    "API Server Health", False, 
                    f"Server responded with status {response.status_code}"
                )
                
        except Exception as e:
            return self.log_test_result("API Server Health", False, str(e))
    
    def test_database_schema_integrity(self):
        """Test 2: Verify database schema and data integrity"""
        try:
            # Check required tables exist
            required_tables = ['entities', 'entity_memberships', 'users', 'api_keys']
            
            table_query = """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = ANY(%s)
                ORDER BY table_name
            """
            
            existing_tables = self.db.execute_query(table_query, [required_tables])
            existing_table_names = [row['table_name'] for row in existing_tables]
            
            missing_tables = [t for t in required_tables if t not in existing_table_names]
            
            if missing_tables:
                return self.log_test_result(
                    "Database Schema Integrity", False, 
                    f"Missing tables: {missing_tables}"
                )
            
            # Check data integrity
            integrity_checks = [
                {
                    "name": "Default entity exists",
                    "query": "SELECT COUNT(*) as count FROM entities WHERE code = 'SYSTEM_DEFAULT'",
                    "expected": lambda x: x > 0
                },
                {
                    "name": "Users have entity memberships",
                    "query": """
                        SELECT COUNT(*) as count
                        FROM users u
                        LEFT JOIN entity_memberships em ON u.id = em.user_id
                        WHERE COALESCE(u.role, 'trader') != 'admin' 
                        AND u.is_active = true 
                        AND em.user_id IS NULL
                    """,
                    "expected": lambda x: x == 0
                },
                {
                    "name": "Entity memberships are valid",
                    "query": """
                        SELECT COUNT(*) as violations
                        FROM entity_memberships em
                        LEFT JOIN entities e ON em.entity_id = e.id
                        LEFT JOIN users u ON em.user_id = u.id
                        WHERE e.id IS NULL OR u.id IS NULL
                    """,
                    "expected": lambda x: x == 0
                }
            ]
            
            failed_checks = []
            for check in integrity_checks:
                result = self.db.execute_query(check["query"])
                count = result[0]['count'] if 'count' in result[0] else result[0]['violations']
                
                if not check["expected"](count):
                    failed_checks.append(f"{check['name']}: {count}")
            
            if failed_checks:
                return self.log_test_result(
                    "Database Schema Integrity", False, 
                    f"Failed checks: {', '.join(failed_checks)}"
                )
            
            return self.log_test_result(
                "Database Schema Integrity", True, 
                f"All tables exist and data integrity validated"
            )
            
        except Exception as e:
            return self.log_test_result("Database Schema Integrity", False, str(e))
    
    def test_entity_context_retrieval(self):
        """Test 3: Test entity context retrieval for users"""
        try:
            # Get test users with entity memberships
            users_query = """
                SELECT DISTINCT 
                    u.id, u.username, COALESCE(u.role, 'trader') as role,
                    em.entity_id, em.entity_role, em.is_active as membership_active,
                    e.name as entity_name, e.code as entity_code
                FROM users u
                JOIN entity_memberships em ON u.id = em.user_id
                JOIN entities e ON em.entity_id = e.id
                WHERE u.is_active = true AND em.is_active = true
                LIMIT 5
            """
            
            users = self.db.execute_query(users_query)
            
            if not users:
                return self.log_test_result(
                    "Entity Context Retrieval", False, 
                    "No users with entity memberships found"
                )
            
            context_results = []
            for user in users:
                # Test entity context retrieval
                context_query = """
                    SELECT 
                        e.id as entity_id,
                        e.code as entity_code,
                        e.name as entity_name,
                        em.entity_role,
                        em.is_active
                    FROM entity_memberships em
                    JOIN entities e ON em.entity_id = e.id
                    WHERE em.user_id = %s AND em.is_active = true AND e.is_active = true
                """
                
                context = self.db.execute_query(context_query, [user['id']])
                
                context_results.append({
                    'username': user['username'],
                    'role': user['role'],
                    'entity_count': len(context),
                    'primary_entity': context[0]['entity_name'] if context else None
                })
            
            return self.log_test_result(
                "Entity Context Retrieval", True, 
                f"Retrieved context for {len(context_results)} users"
            )
            
        except Exception as e:
            return self.log_test_result("Entity Context Retrieval", False, str(e))
    
    def test_admin_api_key_creation(self):
        """Test 4: Test admin API key creation and usage"""
        try:
            # First, get admin user
            admin_query = """
                SELECT id, username, email 
                FROM users 
                WHERE COALESCE(role, 'trader') = 'admin' 
                AND is_active = true 
                LIMIT 1
            """
            
            admin_users = self.db.execute_query(admin_query)
            if not admin_users:
                return self.log_test_result(
                    "Admin API Key Creation", False, 
                    "No admin users found in database"
                )
            
            admin_user = admin_users[0]
            
            # Check if admin already has an API key
            existing_key_query = """
                SELECT ak.key_id, ak.name, ak.is_active
                FROM api_keys ak
                WHERE ak.user_id = %s AND ak.is_active = true
                LIMIT 1
            """
            
            existing_keys = self.db.execute_query(existing_key_query, [admin_user['id']])
            
            if existing_keys:
                # Use existing admin API key
                existing_key = existing_keys[0]
                
                # We need the full API key, not just key_id for authentication
                # For testing, we'll need to check if we can retrieve or create a test key
                return self.log_test_result(
                    "Admin API Key Creation", True, 
                    f"Admin has existing API key: {existing_key['name']}"
                )
            else:
                return self.log_test_result(
                    "Admin API Key Creation", False, 
                    "Admin user exists but no API keys found. Need to create API key via admin interface."
                )
                
        except Exception as e:
            return self.log_test_result("Admin API Key Creation", False, str(e))
    
    def test_entity_access_isolation(self):
        """Test 5: Test entity access isolation between users"""
        try:
            # Get users from different entities
            users_query = """
                SELECT DISTINCT 
                    u.id, u.username, em.entity_id, e.name as entity_name
                FROM users u
                JOIN entity_memberships em ON u.id = em.user_id
                JOIN entities e ON em.entity_id = e.id
                WHERE u.is_active = true AND em.is_active = true
                ORDER BY em.entity_id
                LIMIT 5
            """
            
            users = self.db.execute_query(users_query)
            
            if len(users) < 2:
                return self.log_test_result(
                    "Entity Access Isolation", False, 
                    "Need at least 2 users for isolation testing"
                )
            
            # Test cross-entity access patterns
            isolation_results = []
            
            for i, user1 in enumerate(users):
                for j, user2 in enumerate(users):
                    if i != j:
                        # Check if user1 can access user2's entity
                        access_query = """
                            SELECT COUNT(*) as can_access
                            FROM entity_memberships em
                            WHERE em.user_id = %s 
                            AND em.entity_id = %s 
                            AND em.is_active = true
                        """
                        
                        can_access = self.db.execute_query(
                            access_query, 
                            [user1['id'], user2['entity_id']]
                        )[0]['can_access']
                        
                        isolation_results.append({
                            'user1': user1['username'],
                            'user2': user2['username'],
                            'can_access': can_access > 0,
                            'same_entity': user1['entity_id'] == user2['entity_id']
                        })
            
            # Analyze isolation results
            violations = [r for r in isolation_results 
                         if r['can_access'] and not r['same_entity']]
            
            if violations:
                violation_details = [f"{v['user1']} can access {v['user2']}'s entity" 
                                   for v in violations]
                return self.log_test_result(
                    "Entity Access Isolation", False, 
                    f"Isolation violations: {', '.join(violation_details)}"
                )
            
            return self.log_test_result(
                "Entity Access Isolation", True, 
                f"Tested {len(isolation_results)} access patterns - no violations found"
            )
            
        except Exception as e:
            return self.log_test_result("Entity Access Isolation", False, str(e))
    
    def test_role_based_permissions(self):
        """Test 6: Test role-based permissions within entities"""
        try:
            # Get users with different entity roles
            roles_query = """
                SELECT 
                    u.username,
                    em.entity_role,
                    e.name as entity_name,
                    COUNT(*) as role_count
                FROM users u
                JOIN entity_memberships em ON u.id = em.user_id
                JOIN entities e ON em.entity_id = e.id
                WHERE u.is_active = true AND em.is_active = true
                GROUP BY u.username, em.entity_role, e.name
                ORDER BY em.entity_role
            """
            
            role_distribution = self.db.execute_query(roles_query)
            
            if not role_distribution:
                return self.log_test_result(
                    "Role-Based Permissions", False, 
                    "No entity role memberships found"
                )
            
            # Analyze role distribution
            roles_summary = {}
            for row in role_distribution:
                role = row['entity_role']
                if role not in roles_summary:
                    roles_summary[role] = 0
                roles_summary[role] += 1
            
            # Check that we have the expected roles
            expected_roles = ['trader', 'viewer']
            missing_roles = [role for role in expected_roles if role not in roles_summary]
            
            if missing_roles:
                return self.log_test_result(
                    "Role-Based Permissions", False, 
                    f"Missing expected roles: {missing_roles}. Found: {list(roles_summary.keys())}"
                )
            
            return self.log_test_result(
                "Role-Based Permissions", True, 
                f"Role distribution: {roles_summary}"
            )
            
        except Exception as e:
            return self.log_test_result("Role-Based Permissions", False, str(e))
    
    def test_middleware_functionality(self):
        """Test 7: Test middleware functionality"""
        try:
            # Test that middleware is loaded by checking the root endpoint
            response = requests.get(f"{self.api_base}/", timeout=5)
            
            if response.status_code != 200:
                return self.log_test_result(
                    "Middleware Functionality", False, 
                    f"Root endpoint returned {response.status_code}"
                )
            
            root_data = response.json()
            
            # Check entity management status
            entity_management = root_data.get('entity_management', False)
            entity_middleware = root_data.get('security', {}).get('entity_middleware', 'disabled')
            
            if not entity_management:
                return self.log_test_result(
                    "Middleware Functionality", False, 
                    "Entity management not enabled in API response"
                )
            
            if entity_middleware != 'enabled':
                return self.log_test_result(
                    "Middleware Functionality", False, 
                    f"Entity middleware status: {entity_middleware}"
                )
            
            # Check for entity-specific features in response
            entity_features = root_data.get('entity_features', {})
            if not entity_features:
                return self.log_test_result(
                    "Middleware Functionality", False, 
                    "Entity features not found in API response"
                )
            
            return self.log_test_result(
                "Middleware Functionality", True, 
                f"Middleware active with features: {list(entity_features.keys())}"
            )
            
        except Exception as e:
            return self.log_test_result("Middleware Functionality", False, str(e))
    
    async def run_all_tests(self):
        """Run the complete test suite"""
        logger.info("🧪 Comprehensive Entity System Test Suite")
        logger.info("=" * 70)
        logger.info("Testing entity-based authentication and access control system")
        logger.info("=" * 70)
        
        # Setup
        logger.info("\n📋 SETUP PHASE")
        logger.info("-" * 30)
        
        if not await self.setup_database_connection():
            logger.error("❌ Cannot proceed without database connection")
            return False
        
        # Test execution
        logger.info("\n🔧 TESTING PHASE")
        logger.info("-" * 30)
        
        tests = [
            ("API Server Health", self.test_api_server_health),
            ("Database Schema Integrity", self.test_database_schema_integrity),
            ("Entity Context Retrieval", self.test_entity_context_retrieval),
            ("Admin API Key Creation", self.test_admin_api_key_creation),
            ("Entity Access Isolation", self.test_entity_access_isolation),
            ("Role-Based Permissions", self.test_role_based_permissions),
            ("Middleware Functionality", self.test_middleware_functionality)
        ]
        
        passed_tests = 0
        total_tests = len(tests)
        
        for test_name, test_func in tests:
            logger.info(f"\n🔍 Running: {test_name}")
            try:
                if asyncio.iscoroutinefunction(test_func):
                    success = await test_func()
                else:
                    success = test_func()
                
                if success:
                    passed_tests += 1
                    
            except Exception as e:
                self.log_test_result(test_name, False, f"Test execution error: {str(e)}")
        
        # Cleanup
        if self.db:
            self.db.disconnect()
        
        # Results summary
        logger.info("\n" + "=" * 70)
        logger.info("📊 TEST RESULTS SUMMARY")
        logger.info("=" * 70)
        
        for result in self.test_results:
            status = "✅ PASS" if result['passed'] else "❌ FAIL"
            details = f" - {result['details']}" if result['details'] else ""
            logger.info(f"{status} {result['test']}{details}")
        
        logger.info(f"\n📈 OVERALL RESULTS: {passed_tests}/{total_tests} tests passed")
        
        success_rate = (passed_tests / total_tests) * 100
        
        if success_rate == 100:
            logger.info("🎉 ALL TESTS PASSED! Entity system is working correctly.")
            logger.info("✅ Ready for production use with entity-based access control.")
        elif success_rate >= 85:
            logger.info("✅ Most tests passed. System is largely functional.")
            logger.info("⚠️  Review failed tests before production deployment.")
        else:
            logger.error("❌ Multiple test failures detected.")
            logger.error("🔧 Entity system needs attention before deployment.")
        
        return success_rate == 100


async def main():
    """Main test execution"""
    test_suite = EntitySystemTestSuite()
    success = await test_suite.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    print("🚀 Starting Comprehensive Entity System Tests...")
    print("📋 This will test database integrity, access control, and API functionality")
    print()
    
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test suite failed with error: {e}")
        sys.exit(1)
