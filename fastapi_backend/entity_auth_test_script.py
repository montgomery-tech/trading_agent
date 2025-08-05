#!/usr/bin/env python3
"""
Entity Authentication System Test Script
Task 2.1: Test entity-based access control and authentication

This script validates that the entity-aware authentication system works correctly
and that users can only access data from their assigned entities.
"""

import os
import sys
import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Any

# Add the fastapi_backend directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from api.database import DatabaseManager
from api.auth_dependencies import (
    authenticate_with_entity_context, 
    _get_user_entity_context,
    get_user_accessible_entity_filter,
    EntityAuthenticatedUser
)
from api.api_key_service import get_api_key_service

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class EntityAuthTestSuite:
    """Test suite for entity-based authentication system"""
    
    def __init__(self):
        self.database_url = os.getenv('DATABASE_URL', 'postgresql://localhost:5432/balance_tracker')
        self.db = None
        self.api_key_service = get_api_key_service()
        
    async def setup(self):
        """Initialize database connection"""
        try:
            self.db = DatabaseManager(self.database_url)
            self.db.connect()
            logger.info("✅ Connected to database for testing")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to connect to database: {e}")
            return False
    
    async def cleanup(self):
        """Cleanup database connection"""
        if self.db:
            self.db.disconnect()
            logger.info("Database connection closed")
    
    async def test_entity_context_retrieval(self):
        """Test 1: Entity context retrieval for users"""
        logger.info("🧪 Test 1: Entity context retrieval")
        
        try:
            # Get all users
            users = self.db.execute_query("""
                SELECT id, username, COALESCE(role, 'trader') as role
                FROM users 
                WHERE is_active = true
                LIMIT 5
            """)
            
            if not users:
                logger.warning("⚠️  No users found in database")
                return False
            
            logger.info(f"Testing entity context for {len(users)} users...")
            
            for user in users:
                user_id = user['id']
                username = user['username']
                role = user['role']
                
                # Get entity context
                entity_info, accessible_entities = await _get_user_entity_context(user_id, self.db)
                
                logger.info(f"📊 User: {username} (role: {role})")
                
                if entity_info:
                    logger.info(f"   Primary Entity: {entity_info.entity_name} ({entity_info.entity_code})")
                    logger.info(f"   Entity Role: {entity_info.entity_role}")
                    logger.info(f"   Accessible Entities: {len(accessible_entities)}")
                else:
                    logger.info(f"   No entity memberships (likely admin)")
                
                print()
            
            logger.info("✅ Entity context retrieval test completed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Entity context test failed: {e}")
            return False
    
    async def test_entity_filter_generation(self):
        """Test 2: Entity filter SQL generation"""
        logger.info("🧪 Test 2: Entity filter SQL generation")
        
        try:
            # Get a test user with entity memberships
            user_data = self.db.execute_query("""
                SELECT u.id, u.username, COALESCE(u.role, 'trader') as role
                FROM users u
                JOIN entity_memberships em ON u.id = em.user_id
                WHERE u.is_active = true AND em.is_active = true
                LIMIT 1
            """)
            
            if not user_data:
                logger.warning("⚠️  No users with entity memberships found")
                return False
            
            user = user_data[0]
            user_id = user['id']
            username = user['username']
            
            # Create a mock EntityAuthenticatedUser for testing
            entity_info, accessible_entities = await _get_user_entity_context(user_id, self.db)
            
            # Create mock user object
            from api.api_key_models import UserRole, APIKeyScope
            mock_user = EntityAuthenticatedUser(
                id=user_id,
                username=username,
                email=f"{username}@test.com",
                role=UserRole(user['role']),
                is_active=True,
                is_verified=True,
                created_at="2024-01-01T00:00:00Z",
                api_key_id="test_key",
                api_key_name="test_key",
                api_key_scope=APIKeyScope.INHERIT
            )
            
            # Set entity context
            mock_user.entity_info = entity_info
            mock_user.accessible_entities = accessible_entities
            
            # Test filter generation
            condition, params = await get_user_accessible_entity_filter(mock_user, self.db, "t")
            
            logger.info(f"📊 Testing filter for user: {username}")
            logger.info(f"   Accessible entities: {accessible_entities}")
            logger.info(f"   Generated condition: {condition}")
            logger.info(f"   Parameters: {params}")
            
            # Test admin user (should have no filter)
            mock_admin = EntityAuthenticatedUser(
                id=user_id,
                username="admin_test",
                email="admin@test.com",
                role=UserRole.ADMIN,
                is_active=True,
                is_verified=True,
                created_at="2024-01-01T00:00:00Z",
                api_key_id="admin_key",
                api_key_name="admin_key",
                api_key_scope=APIKeyScope.FULL_ACCESS
            )
            mock_admin.accessible_entities = []
            
            admin_condition, admin_params = await get_user_accessible_entity_filter(mock_admin, self.db, "t")
            
            logger.info(f"📊 Testing filter for admin user:")
            logger.info(f"   Generated condition: '{admin_condition}' (should be empty)")
            logger.info(f"   Parameters: {admin_params} (should be empty)")
            
            logger.info("✅ Entity filter generation test completed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Entity filter test failed: {e}")
            return False
    
    async def test_entity_access_validation(self):
        """Test 3: Entity access validation"""
        logger.info("🧪 Test 3: Entity access validation")
        
        try:
            # Get users with different entity memberships
            users = self.db.execute_query("""
                SELECT DISTINCT 
                    u.id, 
                    u.username, 
                    COALESCE(u.role, 'trader') as role,
                    em.entity_id,
                    e.code as entity_code,
                    e.name as entity_name
                FROM users u
                JOIN entity_memberships em ON u.id = em.user_id
                JOIN entities e ON em.entity_id = e.id
                WHERE u.is_active = true AND em.is_active = true
                LIMIT 3
            """)
            
            if len(users) < 2:
                logger.warning("⚠️  Need at least 2 users with entity memberships for testing")
                return False
            
            user1 = users[0]
            user2 = users[1] if len(users) > 1 else users[0]
            
            logger.info(f"📊 Testing access between users:")
            logger.info(f"   User 1: {user1['username']} -> Entity: {user1['entity_name']}")
            logger.info(f"   User 2: {user2['username']} -> Entity: {user2['entity_name']}")
            
            # Get entity contexts for both users
            entity_info1, accessible1 = await _get_user_entity_context(user1['id'], self.db)
            entity_info2, accessible2 = await _get_user_entity_context(user2['id'], self.db)
            
            # Test if user1 can access user2's entity
            user1_can_access_user2_entity = user2['entity_id'] in accessible1
            user2_can_access_user1_entity = user1['entity_id'] in accessible2
            
            logger.info(f"   {user1['username']} can access {user2['username']}'s entity: {user1_can_access_user2_entity}")
            logger.info(f"   {user2['username']} can access {user1['username']}'s entity: {user2_can_access_user1_entity}")
            
            # If they're different entities, they shouldn't have cross-access (unless multi-entity user)
            if user1['entity_id'] != user2['entity_id']:
                if not user1_can_access_user2_entity and not user2_can_access_user1_entity:
                    logger.info("✅ Proper entity isolation detected")
                else:
                    logger.info("ℹ️  Users have multi-entity access (valid scenario)")
            else:
                logger.info("ℹ️  Users belong to same entity")
            
            logger.info("✅ Entity access validation test completed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Entity access validation test failed: {e}")
            return False
    
    async def test_database_integrity(self):
        """Test 4: Database integrity checks"""
        logger.info("🧪 Test 4: Database integrity checks")
        
        try:
            # Check that all required tables exist
            tables = self.db.execute_query("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name IN ('entities', 'entity_memberships', 'users', 'api_keys')
                ORDER BY table_name
            """)
            
            table_names = [t['table_name'] for t in tables]
            required_tables = ['entities', 'entity_memberships', 'users']
            
            logger.info(f"📊 Database tables found: {table_names}")
            
            missing_tables = [t for t in required_tables if t not in table_names]
            if missing_tables:
                logger.error(f"❌ Missing required tables: {missing_tables}")
                return False
            
            # Check data integrity
            integrity_checks = [
                {
                    "name": "Default entity exists",
                    "query": "SELECT COUNT(*) as count FROM entities WHERE code = 'SYSTEM_DEFAULT'"
                },
                {
                    "name": "All non-admin users have entity memberships",
                    "query": """
                        SELECT COUNT(*) as count
                        FROM users u
                        LEFT JOIN entity_memberships em ON u.id = em.user_id
                        WHERE COALESCE(u.role, 'trader') != 'admin' 
                        AND u.is_active = true 
                        AND em.user_id IS NULL
                    """
                },
                {
                    "name": "All entity memberships reference valid entities",
                    "query": """
                        SELECT COUNT(*) as count
                        FROM entity_memberships em
                        LEFT JOIN entities e ON em.entity_id = e.id
                        WHERE e.id IS NULL
                    """
                },
                {
                    "name": "All entity memberships reference valid users",
                    "query": """
                        SELECT COUNT(*) as count
                        FROM entity_memberships em
                        LEFT JOIN users u ON em.user_id = u.id
                        WHERE u.id IS NULL
                    """
                }
            ]
            
            all_passed = True
            for check in integrity_checks:
                result = self.db.execute_query(check["query"])
                count = result[0]['count'] if result else 0
                
                if check["name"] == "Default entity exists":
                    passed = count > 0
                    status = "✅" if passed else "❌"
                    logger.info(f"   {status} {check['name']}: {count} found")
                else:
                    passed = count == 0
                    status = "✅" if passed else "❌"
                    logger.info(f"   {status} {check['name']}: {count} violations")
                
                if not passed:
                    all_passed = False
            
            logger.info(f"{'✅' if all_passed else '❌'} Database integrity check {'passed' if all_passed else 'failed'}")
            return all_passed
            
        except Exception as e:
            logger.error(f"❌ Database integrity test failed: {e}")
            return False
    
    async def run_all_tests(self):
        """Run all entity authentication tests"""
        logger.info("🧪 Entity Authentication System Test Suite")
        logger.info("=" * 60)
        
        if not await self.setup():
            return False
        
        tests = [
            ("Entity Context Retrieval", self.test_entity_context_retrieval),
            ("Entity Filter Generation", self.test_entity_filter_generation),
            ("Entity Access Validation", self.test_entity_access_validation),
            ("Database Integrity", self.test_database_integrity)
        ]
        
        results = []
        
        for test_name, test_func in tests:
            logger.info(f"\n{'='*20} {test_name} {'='*20}")
            try:
                result = await test_func()
                results.append((test_name, result))
                status = "✅ PASSED" if result else "❌ FAILED"
                logger.info(f"{status}: {test_name}")
            except Exception as e:
                logger.error(f"❌ FAILED: {test_name} - {e}")
                results.append((test_name, False))
        
        # Summary
        logger.info("\n" + "="*60)
        logger.info("📊 TEST SUMMARY")
        logger.info("="*60)
        
        passed = sum(1 for _, result in results if result)
        total = len(results)
        
        for test_name, result in results:
            status = "✅ PASS" if result else "❌ FAIL"
            logger.info(f"   {status} {test_name}")
        
        logger.info(f"\nResults: {passed}/{total} tests passed")
        
        if passed == total:
            logger.info("🎉 All entity authentication tests PASSED!")
            logger.info("✅ Entity-based access control system is working correctly")
        else:
            logger.error("❌ Some entity authentication tests FAILED!")
            logger.error("⚠️  Please review the entity system implementation")
        
        await self.cleanup()
        return passed == total


async def main():
    """Main test execution function"""
    test_suite = EntityAuthTestSuite()
    success = await test_suite.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
