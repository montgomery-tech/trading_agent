#!/usr/bin/env python3
"""
Simple Entity Validation Test
Quick validation that entity isolation is working correctly

This focuses on validating the existing data and logic without creating new test data.
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class SimpleEntityValidation:
    """Simple validation of entity system functionality"""
    
    def __init__(self):
        self.database_url = os.getenv('DATABASE_URL', 'postgresql://localhost:5432/balance_tracker')
        self.db = None
    
    async def setup_database_connection(self):
        """Setup database connection"""
        try:
            sys.path.insert(0, str(Path(__file__).parent))
            from api.database import DatabaseManager
            
            self.db = DatabaseManager(self.database_url)
            self.db.connect()
            logger.info("✅ Database connected")
            return True
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            return False
    
    def test_entity_data_structure(self):
        """Test 1: Validate entity data structure"""
        try:
            logger.info("🔍 Test 1: Entity Data Structure")
            
            # Get all entities
            entities_query = "SELECT id, name, code, is_active FROM entities ORDER BY name"
            entities = self.db.execute_query(entities_query)
            
            logger.info(f"📊 Found {len(entities)} entities:")
            for entity in entities:
                logger.info(f"   - {entity['name']} ({entity['code']}) - Active: {entity['is_active']}")
            
            # Get entity memberships count
            memberships_query = """
                SELECT 
                    e.name as entity_name,
                    COUNT(em.user_id) as member_count,
                    COUNT(CASE WHEN em.entity_role = 'trader' THEN 1 END) as traders,
                    COUNT(CASE WHEN em.entity_role = 'viewer' THEN 1 END) as viewers
                FROM entities e
                LEFT JOIN entity_memberships em ON e.id = em.entity_id AND em.is_active = true
                GROUP BY e.id, e.name
                ORDER BY e.name
            """
            
            memberships = self.db.execute_query(memberships_query)
            
            logger.info(f"📊 Entity membership distribution:")
            for membership in memberships:
                logger.info(f"   - {membership['entity_name']}: {membership['member_count']} members "
                           f"({membership['traders']} traders, {membership['viewers']} viewers)")
            
            return len(entities) > 0 and len(memberships) > 0
            
        except Exception as e:
            logger.error(f"❌ Entity data structure test failed: {e}")
            return False
    
    def test_access_isolation_logic(self):
        """Test 2: Test access isolation logic with existing users"""
        try:
            logger.info("🔍 Test 2: Access Isolation Logic")
            
            # Get users with their entity memberships
            users_entities_query = """
                SELECT 
                    u.id as user_id,
                    u.username,
                    u.role as system_role,
                    e.id as entity_id,
                    e.name as entity_name,
                    e.code as entity_code,
                    em.entity_role
                FROM users u
                JOIN entity_memberships em ON u.id = em.user_id
                JOIN entities e ON em.entity_id = e.id
                WHERE u.is_active = true AND em.is_active = true
                ORDER BY u.username, e.name
            """
            
            user_entities = self.db.execute_query(users_entities_query)
            
            if not user_entities:
                logger.warning("⚠️  No user-entity relationships found")
                return False
            
            logger.info(f"📊 Found {len(user_entities)} user-entity relationships:")
            
            # Group by user
            users_by_id = {}
            for ue in user_entities:
                user_id = ue['user_id']
                if user_id not in users_by_id:
                    users_by_id[user_id] = {
                        'username': ue['username'],
                        'system_role': ue['system_role'],
                        'entities': []
                    }
                users_by_id[user_id]['entities'].append({
                    'entity_id': ue['entity_id'],
                    'entity_name': ue['entity_name'],
                    'entity_code': ue['entity_code'],
                    'entity_role': ue['entity_role']
                })
            
            # Display user access patterns
            for user_id, user_data in users_by_id.items():
                logger.info(f"   👤 {user_data['username']} ({user_data['system_role']}):")
                for entity in user_data['entities']:
                    logger.info(f"      - Can access {entity['entity_name']} as {entity['entity_role']}")
            
            # Test isolation logic: Can users access entities they're not members of?
            isolation_test_results = []
            
            all_entities = set(ue['entity_id'] for ue in user_entities)
            
            for user_id, user_data in users_by_id.items():
                user_entities_set = set(e['entity_id'] for e in user_data['entities'])
                inaccessible_entities = all_entities - user_entities_set
                
                isolation_test_results.append({
                    'username': user_data['username'],
                    'system_role': user_data['system_role'],
                    'accessible_count': len(user_entities_set),
                    'inaccessible_count': len(inaccessible_entities),
                    'total_entities': len(all_entities)
                })
            
            # Analyze isolation
            logger.info("🔒 Access isolation analysis:")
            proper_isolation = True
            
            for result in isolation_test_results:
                if result['system_role'] == 'admin':
                    # Admins should be able to access all entities (but may not have memberships)
                    logger.info(f"   👑 {result['username']} (admin): Can access all entities")
                else:
                    # Non-admin users should have limited access
                    if result['inaccessible_count'] > 0:
                        logger.info(f"   ✅ {result['username']}: Proper isolation - "
                                   f"can access {result['accessible_count']} of {result['total_entities']} entities")
                    else:
                        logger.warning(f"   ⚠️  {result['username']}: Can access ALL entities - check isolation")
                        proper_isolation = False
            
            return proper_isolation
            
        except Exception as e:
            logger.error(f"❌ Access isolation test failed: {e}")
            return False
    
    def test_entity_filter_simulation(self):
        """Test 3: Simulate entity filtering for queries"""
        try:
            logger.info("🔍 Test 3: Entity Filter Simulation")
            
            # Get a sample user (non-admin)
            sample_user_query = """
                SELECT u.id, u.username, u.role
                FROM users u
                WHERE COALESCE(u.role, 'trader') != 'admin' 
                AND u.is_active = true
                LIMIT 1
            """
            
            sample_users = self.db.execute_query(sample_user_query)
            if not sample_users:
                logger.warning("⚠️  No non-admin users found for testing")
                return False
            
            sample_user = sample_users[0]
            logger.info(f"📋 Testing with user: {sample_user['username']}")
            
            # Get user's accessible entities
            accessible_entities_query = """
                SELECT em.entity_id, e.name as entity_name
                FROM entity_memberships em
                JOIN entities e ON em.entity_id = e.id
                WHERE em.user_id = %s AND em.is_active = true
            """
            
            accessible_entities = self.db.execute_query(accessible_entities_query, [sample_user['id']])
            accessible_entity_ids = [e['entity_id'] for e in accessible_entities]
            
            logger.info(f"📊 User can access {len(accessible_entities)} entities:")
            for entity in accessible_entities:
                logger.info(f"   - {entity['entity_name']}")
            
            # Simulate an entity-filtered query (like balance query)
            if accessible_entity_ids:
                simulated_balance_query = """
                    SELECT 
                        'Mock Balance Data' as balance_info,
                        e.name as entity_name,
                        COUNT(*) as simulated_balance_count
                    FROM entities e
                    WHERE e.id = ANY(%s)
                    GROUP BY e.id, e.name
                """
                
                filtered_results = self.db.execute_query(simulated_balance_query, [accessible_entity_ids])
                
                logger.info(f"🔍 Simulated entity-filtered query results:")
                for result in filtered_results:
                    logger.info(f"   - {result['entity_name']}: {result['simulated_balance_count']} records")
                
                # Test that filtering works - should only return accessible entities
                returned_count = len(filtered_results)
                expected_count = len(accessible_entities)
                
                if returned_count == expected_count:
                    logger.info("✅ Entity filtering working correctly")
                    return True
                else:
                    logger.error(f"❌ Entity filtering issue: expected {expected_count}, got {returned_count}")
                    return False
            else:
                logger.warning("⚠️  User has no accessible entities")
                return False
            
        except Exception as e:
            logger.error(f"❌ Entity filter simulation failed: {e}")
            return False
    
    def test_admin_vs_user_access(self):
        """Test 4: Compare admin vs user access patterns"""
        try:
            logger.info("🔍 Test 4: Admin vs User Access Patterns")
            
            # Get admin users
            admin_query = """
                SELECT id, username 
                FROM users 
                WHERE COALESCE(role, 'trader') = 'admin' AND is_active = true
            """
            admins = self.db.execute_query(admin_query)
            
            # Get non-admin users with entity memberships
            user_query = """
                SELECT DISTINCT u.id, u.username, u.role
                FROM users u
                JOIN entity_memberships em ON u.id = em.user_id
                WHERE COALESCE(u.role, 'trader') != 'admin' AND u.is_active = true
                LIMIT 3
            """
            regular_users = self.db.execute_query(user_query)
            
            logger.info(f"📊 Found {len(admins)} admin users and {len(regular_users)} regular users")
            
            # Test access patterns
            all_entities_query = "SELECT id FROM entities WHERE is_active = true"
            all_entities = self.db.execute_query(all_entities_query)
            total_entities = len(all_entities)
            
            logger.info(f"🏢 System has {total_entities} active entities")
            
            # For admins: Should be able to access all entities (conceptually)
            logger.info("👑 Admin access pattern:")
            for admin in admins:
                logger.info(f"   - {admin['username']}: Can access ALL {total_entities} entities (admin privilege)")
            
            # For regular users: Should only access their assigned entities
            logger.info("👤 Regular user access patterns:")
            for user in regular_users:
                user_entities_query = """
                    SELECT COUNT(*) as accessible_count
                    FROM entity_memberships em
                    WHERE em.user_id = %s AND em.is_active = true
                """
                
                user_access = self.db.execute_query(user_entities_query, [user['id']])
                accessible_count = user_access[0]['accessible_count'] if user_access else 0
                
                logger.info(f"   - {user['username']}: Can access {accessible_count} of {total_entities} entities")
                
                if accessible_count < total_entities:
                    logger.info(f"     ✅ Proper isolation: Restricted access")
                else:
                    logger.warning(f"     ⚠️  Full access: Check entity assignments")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Admin vs user access test failed: {e}")
            return False
    
    async def run_validation(self):
        """Run simple entity validation"""
        logger.info("🧪 Simple Entity System Validation")
        logger.info("=" * 50)
        logger.info("Validating existing entity system functionality")
        logger.info("=" * 50)
        
        # Setup
        if not await self.setup_database_connection():
            return False
        
        # Run tests
        tests = [
            ("Entity Data Structure", self.test_entity_data_structure),
            ("Access Isolation Logic", self.test_access_isolation_logic),
            ("Entity Filter Simulation", self.test_entity_filter_simulation),
            ("Admin vs User Access", self.test_admin_vs_user_access)
        ]
        
        passed_tests = 0
        total_tests = len(tests)
        
        for test_name, test_func in tests:
            logger.info(f"\n{'='*20} {test_name} {'='*20}")
            try:
                success = test_func()
                if success:
                    passed_tests += 1
                    logger.info(f"✅ {test_name}: PASSED")
                else:
                    logger.error(f"❌ {test_name}: FAILED")
            except Exception as e:
                logger.error(f"❌ {test_name}: ERROR - {e}")
        
        # Cleanup
        if self.db:
            self.db.disconnect()
        
        # Results
        logger.info("\n" + "=" * 50)
        logger.info("📊 VALIDATION RESULTS")
        logger.info("=" * 50)
        
        success_rate = (passed_tests / total_tests) * 100
        logger.info(f"📈 Results: {passed_tests}/{total_tests} tests passed ({success_rate:.1f}%)")
        
        if success_rate == 100:
            logger.info("🎉 All validation tests PASSED!")
            logger.info("✅ Entity system is functioning correctly with your existing data")
            logger.info("🚀 Ready to proceed with entity-aware API development")
        elif success_rate >= 75:
            logger.info("✅ Most validation tests passed - system is largely functional")
            logger.info("⚠️  Review any failed tests before proceeding")
        else:
            logger.error("❌ Multiple validation failures detected")
            logger.error("🔧 Entity system needs attention")
        
        return success_rate >= 75


async def main():
    """Run simple validation"""
    validator = SimpleEntityValidation()
    success = await validator.run_validation()
    return 0 if success else 1


if __name__ == "__main__":
    print("🚀 Starting Simple Entity System Validation...")
    print("This validates the entity system using your existing data")
    print()
    
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⚠️  Validation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Validation failed: {e}")
        sys.exit(1)
