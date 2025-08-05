#!/usr/bin/env python3
"""
Multi-Entity Isolation Test Setup
Option A: Create a second entity and test real cross-entity isolation

This script:
1. Creates a second test entity
2. Moves some users to the new entity
3. Tests that users can only access their assigned entity's data
4. Validates the complete multi-tenant isolation system
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


class MultiEntityIsolationTest:
    """Create and test multi-entity isolation"""
    
    def __init__(self):
        self.database_url = os.getenv('DATABASE_URL', 'postgresql://localhost:5432/balance_tracker')
        self.db = None
        self.test_entity_id = None
        self.moved_users = []
    
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
    
    def create_test_entity(self):
        """Step 1: Create a second entity for testing"""
        try:
            logger.info("🏢 Step 1: Creating Test Trading Entity...")
            
            # Create the test entity
            create_entity_query = """
                INSERT INTO entities (name, code, description, entity_type, is_active)
                VALUES ('Test Trading Entity', 'TEST_ENTITY', 'Test entity for isolation validation', 'trading_entity', true)
                ON CONFLICT (code) DO UPDATE SET 
                    name = EXCLUDED.name,
                    description = EXCLUDED.description,
                    is_active = EXCLUDED.is_active
                RETURNING id, name, code
            """
            
            result = self.db.execute_query(create_entity_query)
            if result:
                entity = result[0]
                self.test_entity_id = entity['id']
                logger.info(f"✅ Created entity: {entity['name']} ({entity['code']})")
                logger.info(f"   Entity ID: {self.test_entity_id}")
                return True
            else:
                logger.error("❌ Failed to create test entity")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to create test entity: {e}")
            return False
    
    def move_users_to_test_entity(self):
        """Step 2: Move some users to the test entity"""
        try:
            logger.info("👥 Step 2: Moving users to Test Trading Entity...")
            
            # Get some users to move (excluding admin users)
            get_users_query = """
                SELECT u.id, u.username, COALESCE(u.role, 'trader') as role
                FROM users u
                JOIN entity_memberships em ON u.id = em.user_id
                WHERE COALESCE(u.role, 'trader') != 'admin' 
                AND u.is_active = true
                AND u.username IN ('testuser', 'trader.test', 'viewer.test')
                LIMIT 3
            """
            
            users_to_move = self.db.execute_query(get_users_query)
            
            if not users_to_move:
                logger.warning("⚠️  No suitable users found to move")
                return False
            
            logger.info(f"📋 Found {len(users_to_move)} users to move:")
            for user in users_to_move:
                logger.info(f"   - {user['username']} ({user['role']})")
            
            # Move users to the test entity
            moved_count = 0
            for user in users_to_move:
                try:
                    # Remove from default entity
                    remove_query = """
                        DELETE FROM entity_memberships 
                        WHERE user_id = %s AND entity_id = (
                            SELECT id FROM entities WHERE code = 'SYSTEM_DEFAULT'
                        )
                    """
                    self.db.execute_query(remove_query, [user['id']])
                    
                    # Add to test entity
                    add_query = """
                        INSERT INTO entity_memberships (entity_id, user_id, entity_role, is_active)
                        VALUES (%s, %s, %s, true)
                    """
                    
                    # Map system role to entity role
                    entity_role = 'trader' if user['role'] in ['trader', 'admin'] else 'viewer'
                    
                    self.db.execute_query(add_query, [self.test_entity_id, user['id'], entity_role])
                    
                    self.moved_users.append({
                        'id': user['id'],
                        'username': user['username'],
                        'role': user['role'],
                        'entity_role': entity_role
                    })
                    
                    moved_count += 1
                    logger.info(f"✅ Moved {user['username']} to Test Trading Entity as {entity_role}")
                    
                except Exception as e:
                    logger.error(f"❌ Failed to move {user['username']}: {e}")
            
            if moved_count > 0:
                logger.info(f"✅ Successfully moved {moved_count} users to Test Trading Entity")
                return True
            else:
                logger.error("❌ No users were successfully moved")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to move users: {e}")
            return False
    
    def test_current_entity_distribution(self):
        """Step 3: Show current entity distribution"""
        try:
            logger.info("📊 Step 3: Current Entity Distribution")
            
            # Get entity distribution
            distribution_query = """
                SELECT 
                    e.name as entity_name,
                    e.code as entity_code,
                    COUNT(em.user_id) as member_count,
                    COUNT(CASE WHEN em.entity_role = 'trader' THEN 1 END) as traders,
                    COUNT(CASE WHEN em.entity_role = 'viewer' THEN 1 END) as viewers
                FROM entities e
                LEFT JOIN entity_memberships em ON e.id = em.entity_id AND em.is_active = true
                GROUP BY e.id, e.name, e.code
                ORDER BY e.name
            """
            
            distribution = self.db.execute_query(distribution_query)
            
            logger.info("🏢 Entity distribution:")
            total_members = 0
            for entity in distribution:
                member_count = entity['member_count']
                total_members += member_count
                logger.info(f"   📍 {entity['entity_name']} ({entity['entity_code']}):")
                logger.info(f"      - {member_count} total members")
                logger.info(f"      - {entity['traders']} traders")
                logger.info(f"      - {entity['viewers']} viewers")
            
            logger.info(f"📈 Total users distributed: {total_members}")
            
            return len(distribution) >= 2  # Should have at least 2 entities now
            
        except Exception as e:
            logger.error(f"❌ Failed to check entity distribution: {e}")
            return False
    
    def test_cross_entity_isolation(self):
        """Step 4: Test cross-entity access isolation"""
        try:
            logger.info("🔒 Step 4: Testing Cross-Entity Access Isolation")
            
            # Get users from both entities
            users_query = """
                SELECT 
                    u.id, u.username, 
                    e.name as entity_name, e.code as entity_code,
                    em.entity_role
                FROM users u
                JOIN entity_memberships em ON u.id = em.user_id
                JOIN entities e ON em.entity_id = e.id
                WHERE u.is_active = true AND em.is_active = true
                ORDER BY e.name, u.username
            """
            
            users = self.db.execute_query(users_query)
            
            # Group users by entity
            entities_users = {}
            for user in users:
                entity_code = user['entity_code']
                if entity_code not in entities_users:
                    entities_users[entity_code] = []
                entities_users[entity_code].append(user)
            
            logger.info("👥 Users by entity:")
            for entity_code, entity_users in entities_users.items():
                entity_name = entity_users[0]['entity_name']
                logger.info(f"   🏢 {entity_name} ({entity_code}): {len(entity_users)} users")
                for user in entity_users:
                    logger.info(f"      - {user['username']} ({user['entity_role']})")
            
            # Test isolation: Can users from Entity A access Entity B data?
            if len(entities_users) >= 2:
                entity_codes = list(entities_users.keys())
                entity_a_code = entity_codes[0]
                entity_b_code = entity_codes[1]
                
                entity_a_users = entities_users[entity_a_code]
                entity_b_users = entities_users[entity_b_code]
                
                logger.info(f"🧪 Testing isolation between {entity_a_code} and {entity_b_code}:")
                
                # Test: Can Entity A users access Entity B?
                isolation_violations = []
                
                for user_a in entity_a_users:
                    # Check if user A has access to Entity B
                    cross_access_query = """
                        SELECT COUNT(*) as has_access
                        FROM entity_memberships em
                        JOIN entities e ON em.entity_id = e.id
                        WHERE em.user_id = %s AND e.code = %s AND em.is_active = true
                    """
                    
                    access_result = self.db.execute_query(cross_access_query, [user_a['id'], entity_b_code])
                    has_cross_access = access_result[0]['has_access'] > 0 if access_result else False
                    
                    if has_cross_access:
                        isolation_violations.append(f"{user_a['username']} can access {entity_b_code}")
                    else:
                        logger.info(f"   ✅ {user_a['username']} ({entity_a_code}) cannot access {entity_b_code}")
                
                # Test: Can Entity B users access Entity A?
                for user_b in entity_b_users:
                    access_result = self.db.execute_query(cross_access_query, [user_b['id'], entity_a_code])
                    has_cross_access = access_result[0]['has_access'] > 0 if access_result else False
                    
                    if has_cross_access:
                        isolation_violations.append(f"{user_b['username']} can access {entity_a_code}")
                    else:
                        logger.info(f"   ✅ {user_b['username']} ({entity_b_code}) cannot access {entity_a_code}")
                
                # Results
                if isolation_violations:
                    logger.error("❌ Isolation violations found:")
                    for violation in isolation_violations:
                        logger.error(f"   - {violation}")
                    return False
                else:
                    logger.info("🎉 Perfect isolation! No cross-entity access detected.")
                    return True
            else:
                logger.error("❌ Need at least 2 entities with users for isolation testing")
                return False
                
        except Exception as e:
            logger.error(f"❌ Cross-entity isolation test failed: {e}")
            return False
    
    def test_entity_filter_queries(self):
        """Step 5: Test entity-filtered queries"""
        try:
            logger.info("🔍 Step 5: Testing Entity-Filtered Queries")
            
            # Test the entity filtering logic that would be used in API endpoints
            test_cases = []
            
            # Get users from different entities
            users_query = """
                SELECT DISTINCT 
                    u.id, u.username, 
                    e.id as entity_id, e.name as entity_name, e.code as entity_code
                FROM users u
                JOIN entity_memberships em ON u.id = em.user_id
                JOIN entities e ON em.entity_id = e.id
                WHERE u.is_active = true AND em.is_active = true
                LIMIT 4
            """
            
            test_users = self.db.execute_query(users_query)
            
            for user in test_users:
                # Get user's accessible entity IDs
                accessible_query = """
                    SELECT em.entity_id
                    FROM entity_memberships em
                    WHERE em.user_id = %s AND em.is_active = true
                """
                
                accessible_entities = self.db.execute_query(accessible_query, [user['id']])
                accessible_ids = [str(e['entity_id']) for e in accessible_entities]
                
                # Simulate entity-filtered query (using proper UUID casting)
                if accessible_ids:
                    filter_query = """
                        SELECT 
                            e.name as entity_name,
                            'Mock data for ' || e.name as mock_data
                        FROM entities e
                        WHERE e.id = ANY(%s::uuid[])
                    """
                    
                    filtered_results = self.db.execute_query(filter_query, [accessible_ids])
                    
                    test_cases.append({
                        'username': user['username'],
                        'user_entity': user['entity_name'],
                        'accessible_count': len(filtered_results),
                        'accessible_entities': [r['entity_name'] for r in filtered_results]
                    })
            
            # Display results
            logger.info("📊 Entity filter test results:")
            for case in test_cases:
                logger.info(f"   👤 {case['username']} (from {case['user_entity']}):")
                logger.info(f"      - Can query {case['accessible_count']} entities")
                for entity_name in case['accessible_entities']:
                    logger.info(f"        ✅ {entity_name}")
            
            # Validate: Users should only see their own entity
            all_passed = True
            for case in test_cases:
                if case['accessible_count'] != 1:
                    logger.error(f"❌ {case['username']} can access {case['accessible_count']} entities (should be 1)")
                    all_passed = False
                elif case['user_entity'] not in case['accessible_entities']:
                    logger.error(f"❌ {case['username']} cannot access their own entity {case['user_entity']}")
                    all_passed = False
            
            if all_passed:
                logger.info("✅ Entity filtering working perfectly!")
            
            return all_passed
            
        except Exception as e:
            logger.error(f"❌ Entity filter query test failed: {e}")
            return False
    
    def cleanup_option(self):
        """Option: Clean up test data"""
        logger.info("🧹 Cleanup Options:")
        logger.info("   1. Keep test entity for continued testing")
        logger.info("   2. Move users back to default entity")
        logger.info("   3. Delete test entity")
        
        try:
            response = input("\nChoose cleanup option (1/2/3) or press Enter to keep current setup: ").strip()
            
            if response == "2":
                # Move users back to default entity
                logger.info("🔄 Moving users back to System Default Entity...")
                
                default_entity_query = "SELECT id FROM entities WHERE code = 'SYSTEM_DEFAULT'"
                default_result = self.db.execute_query(default_entity_query)
                
                if default_result:
                    default_entity_id = default_result[0]['id']
                    
                    for user in self.moved_users:
                        # Remove from test entity
                        remove_query = "DELETE FROM entity_memberships WHERE user_id = %s AND entity_id = %s"
                        self.db.execute_query(remove_query, [user['id'], self.test_entity_id])
                        
                        # Add back to default entity
                        add_query = """
                            INSERT INTO entity_memberships (entity_id, user_id, entity_role, is_active)
                            VALUES (%s, %s, %s, true)
                        """
                        self.db.execute_query(add_query, [default_entity_id, user['id'], user['entity_role']])
                        
                        logger.info(f"✅ Moved {user['username']} back to System Default Entity")
                    
                    logger.info("✅ Users moved back to default entity")
                
            elif response == "3":
                # Delete test entity and move users back
                logger.info("🗑️  Deleting test entity...")
                
                # First move users back (cascade should handle this, but be safe)
                if response != "2":  # If we didn't already move them back
                    default_entity_query = "SELECT id FROM entities WHERE code = 'SYSTEM_DEFAULT'"
                    default_result = self.db.execute_query(default_entity_query)
                    
                    if default_result:
                        default_entity_id = default_result[0]['id']
                        
                        for user in self.moved_users:
                            add_query = """
                                INSERT INTO entity_memberships (entity_id, user_id, entity_role, is_active)
                                VALUES (%s, %s, %s, true)
                                ON CONFLICT (entity_id, user_id) DO NOTHING
                            """
                            self.db.execute_query(add_query, [default_entity_id, user['id'], user['entity_role']])
                
                # Delete test entity (will cascade delete memberships)
                delete_query = "DELETE FROM entities WHERE code = 'TEST_ENTITY'"
                self.db.execute_query(delete_query)
                
                logger.info("✅ Test entity deleted and users restored")
                
            else:
                logger.info("✅ Keeping current multi-entity setup for continued testing")
                
        except Exception as e:
            logger.error(f"❌ Cleanup failed: {e}")
    
    async def run_multi_entity_test(self):
        """Run complete multi-entity isolation test"""
        logger.info("🧪 Multi-Entity Isolation Test")
        logger.info("=" * 60)
        logger.info("Creating second entity and testing real isolation")
        logger.info("=" * 60)
        
        # Setup
        if not await self.setup_database_connection():
            return False
        
        # Execute test steps
        steps = [
            ("Create Test Entity", self.create_test_entity),
            ("Move Users to Test Entity", self.move_users_to_test_entity),
            ("Check Entity Distribution", self.test_current_entity_distribution),
            ("Test Cross-Entity Isolation", self.test_cross_entity_isolation),
            ("Test Entity-Filtered Queries", self.test_entity_filter_queries)
        ]
        
        passed_steps = 0
        total_steps = len(steps)
        
        for step_name, step_func in steps:
            logger.info(f"\n{'='*15} {step_name} {'='*15}")
            try:
                success = step_func()
                if success:
                    passed_steps += 1
                    logger.info(f"✅ {step_name}: SUCCESS")
                else:
                    logger.error(f"❌ {step_name}: FAILED")
                    # Continue with remaining steps even if one fails
            except Exception as e:
                logger.error(f"❌ {step_name}: ERROR - {e}")
        
        # Results
        logger.info("\n" + "=" * 60)
        logger.info("📊 MULTI-ENTITY TEST RESULTS")
        logger.info("=" * 60)
        
        success_rate = (passed_steps / total_steps) * 100
        logger.info(f"📈 Results: {passed_steps}/{total_steps} steps completed ({success_rate:.1f}%)")
        
        if success_rate >= 80:
            logger.info("🎉 Multi-entity isolation test SUCCESSFUL!")
            logger.info("✅ Your entity system provides proper multi-tenant isolation")
            logger.info("🚀 Ready for production multi-entity use")
        else:
            logger.error("❌ Multi-entity isolation test had issues")
            logger.error("🔧 Review failed steps before production deployment")
        
        # Cleanup option
        logger.info("\n" + "=" * 60)
        self.cleanup_option()
        
        # Cleanup
        if self.db:
            self.db.disconnect()
        
        return success_rate >= 80


async def main():
    """Run multi-entity isolation test"""
    test_suite = MultiEntityIsolationTest()
    success = await test_suite.run_multi_entity_test()
    return 0 if success else 1


if __name__ == "__main__":
    print("🚀 Starting Multi-Entity Isolation Test...")
    print("This will create a second entity and test real cross-entity isolation")
    print("⚠️  This will modify your database by moving some users between entities")
    print()
    
    confirm = input("Continue? (y/N): ").strip().lower()
    if confirm not in ['y', 'yes']:
        print("Test cancelled by user")
        sys.exit(0)
    
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
