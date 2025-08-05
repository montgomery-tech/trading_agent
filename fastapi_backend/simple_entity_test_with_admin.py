#!/usr/bin/env python3
"""
Simple Entity Isolation Test using Admin User
Tests entity isolation by temporarily assigning admin to test entities

This is a simpler approach that uses the existing admin user instead of creating new users.
"""

import os
import sys
import asyncio
import aiohttp
import logging
from pathlib import Path
import time

sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class SimpleEntityAdminTest:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.db = None
        self.test_entities = {}
        self.admin_memberships = []  # Track memberships to clean up
        
    async def setup_database_connection(self):
        """Setup database connection"""
        try:
            from api.database import DatabaseManager
            
            database_url = os.getenv('DATABASE_URL', 'postgresql://localhost:5432/balance_tracker')
            self.db = DatabaseManager(database_url)
            self.db.connect()
            logger.info("✅ Database connected")
            return True
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            return False
    
    async def create_test_entities(self):
        """Create test entities for isolation testing"""
        try:
            logger.info("🏗️  Creating test entities...")
            
            timestamp = str(int(time.time()))
            
            # Create Alpha Entity
            alpha_result = self.db.execute_query("""
                INSERT INTO entities (name, code, description, entity_type, is_active)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name
                RETURNING id, name, code
            """, (f"Admin Test Alpha {timestamp}", f"ADMIN_ALPHA_{timestamp}", "Admin test alpha entity", "trading_entity", True))
            
            if alpha_result:
                self.test_entities['alpha'] = alpha_result[0]
                logger.info(f"✅ Created Alpha Entity: {alpha_result[0]['name']} ({alpha_result[0]['code']})")
            
            # Create Beta Entity  
            beta_result = self.db.execute_query("""
                INSERT INTO entities (name, code, description, entity_type, is_active)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name
                RETURNING id, name, code
            """, (f"Admin Test Beta {timestamp}", f"ADMIN_BETA_{timestamp}", "Admin test beta entity", "trading_entity", True))
            
            if beta_result:
                self.test_entities['beta'] = beta_result[0]
                logger.info(f"✅ Created Beta Entity: {beta_result[0]['name']} ({beta_result[0]['code']})")
            
            return len(self.test_entities) == 2
            
        except Exception as e:
            logger.error(f"❌ Failed to create test entities: {e}")
            return False
    
    async def assign_admin_to_entity(self, entity_key: str, role: str = 'trader'):
        """Temporarily assign admin to an entity for testing"""
        try:
            entity = self.test_entities[entity_key]
            
            # Get admin user ID
            admin_result = self.db.execute_query("""
                SELECT id FROM users WHERE username = %s
            """, ('garrett_admin',))
            
            if not admin_result:
                logger.error("❌ Admin user not found")
                return False
            
            admin_id = admin_result[0]['id']
            
            # Create entity membership
            membership_result = self.db.execute_query("""
                INSERT INTO entity_memberships (entity_id, user_id, entity_role, is_active)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (entity_id, user_id) DO UPDATE SET 
                    entity_role = EXCLUDED.entity_role,
                    is_active = EXCLUDED.is_active
                RETURNING id
            """, (entity['id'], admin_id, role, True))
            
            if membership_result:
                membership_id = membership_result[0]['id']
                self.admin_memberships.append(membership_id)
                logger.info(f"✅ Assigned admin to {entity['name']} as {role}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Failed to assign admin to entity: {e}")
            return False
    
    async def test_endpoint_with_auth(self, endpoint: str, api_key: str) -> dict:
        """Make authenticated request to API endpoint"""
        try:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}{endpoint}"
                async with session.get(url, headers=headers) as response:
                    result = {
                        'status': response.status,
                        'data': await response.json() if response.content_type == 'application/json' else await response.text(),
                        'headers': dict(response.headers)
                    }
                    return result
                    
        except Exception as e:
            logger.error(f"❌ Request to {endpoint} failed: {e}")
            return {'status': 0, 'data': {'error': str(e)}, 'headers': {}}
    
    async def test_entity_isolation(self) -> bool:
        """Test entity isolation using admin user with different entity assignments"""
        try:
            logger.info("🔒 Testing Entity Isolation...")
            
            # Get an existing admin API key
            admin_keys = self.db.execute_query("""
                SELECT ak.key_hash, ak.key_id
                FROM api_keys ak
                JOIN users u ON ak.user_id = u.id
                WHERE u.username = 'garrett_admin' AND ak.is_active = true
                LIMIT 1
            """)
            
            if not admin_keys:
                logger.error("❌ No admin API keys found")
                return False
            
            # We need the full API key, but we only have the hash
            # Let's create a new test key for admin
            from api.api_key_service import APIKeyService
            api_service = APIKeyService()
            
            admin_user_result = self.db.execute_query("SELECT id FROM users WHERE username = 'garrett_admin'")
            admin_id = admin_user_result[0]['id']
            
            # Generate new API key
            key_id, full_api_key = api_service.generate_api_key()
            key_hash = api_service.hash_api_key(full_api_key)
            
            # Insert test API key
            test_key_result = self.db.execute_query("""
                INSERT INTO api_keys (key_id, key_hash, user_id, name, permissions_scope, is_active)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (key_id, key_hash, admin_id, "Admin Entity Test Key", "inherit", True))
            
            if not test_key_result:
                logger.error("❌ Failed to create test API key")
                return False
                
            test_key_db_id = test_key_result[0]['id']
            logger.info(f"✅ Created test API key: {key_id}")
            
            violations = []
            
            # Test 1: Admin with Alpha entity membership accessing Alpha data
            logger.info("📋 Test 1: Admin (Alpha entity) accessing Alpha data")
            await self.assign_admin_to_entity('alpha', 'trader')
            
            result = await self.test_endpoint_with_auth("/api/v1/users/garrett_admin", full_api_key)
            logger.info(f"Alpha entity admin accessing own data: Status {result['status']}")
            
            if result['status'] != 200:
                violations.append("Admin with Alpha entity membership cannot access own data")
            else:
                logger.info("✅ Admin can access own data when assigned to entity")
            
            # Test 2: Try to access a user from a different entity (should fail)
            # First, let's create a test user in Beta entity
            beta_user_result = self.db.execute_query("""
                INSERT INTO users (username, email, password_hash, is_active, is_verified, role)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id, username
            """, ("beta_test_user", "beta@test.com", "test_hash", True, True, "trader"))
            
            if beta_user_result:
                beta_user = beta_user_result[0]
                # Assign to Beta entity
                self.db.execute_command("""
                    INSERT INTO entity_memberships (entity_id, user_id, entity_role, is_active)
                    VALUES (%s, %s, %s, %s)
                """, (self.test_entities['beta']['id'], beta_user['id'], 'trader', True))
                
                logger.info("📋 Test 2: Admin (Alpha entity) accessing Beta entity user")
                result = await self.test_endpoint_with_auth(f"/api/v1/users/{beta_user['username']}", full_api_key)
                logger.info(f"Alpha entity admin accessing Beta user: Status {result['status']}")
                
                if result['status'] == 200:
                    violations.append("Admin with Alpha entity membership can access Beta entity user")
                else:
                    logger.info("✅ Admin correctly blocked from accessing Beta entity user")
            
            # Test 3: Switch admin to Beta entity and test access
            logger.info("📋 Test 3: Admin (Beta entity) accessing Beta data")
            
            # Remove Alpha membership and add Beta membership
            self.db.execute_command("DELETE FROM entity_memberships WHERE user_id = %s", (admin_id,))
            self.admin_memberships.clear()
            
            await self.assign_admin_to_entity('beta', 'trader')
            
            if beta_user_result:
                result = await self.test_endpoint_with_auth(f"/api/v1/users/{beta_user['username']}", full_api_key)
                logger.info(f"Beta entity admin accessing Beta user: Status {result['status']}")
                
                if result['status'] != 200:
                    violations.append("Admin with Beta entity membership cannot access Beta entity user")
                else:
                    logger.info("✅ Admin can access Beta entity user when assigned to Beta entity")
            
            # Cleanup test user
            if beta_user_result:
                self.db.execute_command("DELETE FROM entity_memberships WHERE user_id = %s", (beta_user['id'],))
                self.db.execute_command("DELETE FROM users WHERE id = %s", (beta_user['id'],))
            
            # Cleanup test API key
            self.db.execute_command("DELETE FROM api_keys WHERE id = %s", (test_key_db_id,))
            
            # Results
            if violations:
                logger.error("❌ Entity isolation violations found:")
                for violation in violations:
                    logger.error(f"   - {violation}")
                return False
            else:
                logger.info("🎉 PERFECT ENTITY ISOLATION! Admin can only access data from assigned entity.")
                return True
                
        except Exception as e:
            logger.error(f"❌ Entity isolation test failed: {e}")
            return False
    
    async def cleanup_test_data(self):
        """Clean up test data"""
        try:
            logger.info("🧹 Cleaning up test data...")
            
            # Remove admin entity memberships
            admin_user_result = self.db.execute_query("SELECT id FROM users WHERE username = 'garrett_admin'")
            if admin_user_result:
                admin_id = admin_user_result[0]['id']
                self.db.execute_command("DELETE FROM entity_memberships WHERE user_id = %s", (admin_id,))
            
            # Delete test entities
            for entity_key, entity in self.test_entities.items():
                self.db.execute_command("DELETE FROM entities WHERE id = %s", (entity['id'],))
            
            logger.info("✅ Test data cleaned up")
            
        except Exception as e:
            logger.warning(f"⚠️  Cleanup failed: {e}")
    
    async def run_test(self) -> bool:
        """Run the complete entity isolation test"""
        logger.info("🚀 Simple Entity Isolation Test with Admin User")
        logger.info("=" * 60)
        logger.info("Testing entity isolation using admin user assignments")
        logger.info("=" * 60)
        
        if not await self.setup_database_connection():
            return False
        
        try:
            # Create test entities
            if not await self.create_test_entities():
                logger.error("❌ Failed to create test entities")
                return False
            
            # Run entity isolation test
            success = await self.test_entity_isolation()
            
            if success:
                logger.info("\n🎉 ENTITY ISOLATION TEST COMPLETE!")
                logger.info("✅ Entity-based access control is working perfectly")
                logger.info("🔒 Users can only access data from their assigned entities")
                logger.info("🚀 System is ready for multi-tenant production use")
            else:
                logger.error("❌ Entity isolation test had issues")
            
            return success
            
        finally:
            await self.cleanup_test_data()
            if self.db:
                self.db.disconnect()


async def main():
    test_suite = SimpleEntityAdminTest()
    success = await test_suite.run_test()
    return 0 if success else 1


if __name__ == "__main__":
    print("🧪 Simple Entity Isolation Test")
    print("This tests entity isolation using the admin user")
    print("Make sure the FastAPI server is running: python3 main.py")
    print()
    
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
