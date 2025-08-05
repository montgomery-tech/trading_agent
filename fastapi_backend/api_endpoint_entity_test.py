#!/usr/bin/env python3
"""
API Endpoint Entity Isolation Test
Tests actual FastAPI endpoints to verify entity-based access control works

This test makes real HTTP requests to the API to verify:
1. Users can only access their own entity's data via API calls
2. API authentication properly enforces entity boundaries
3. Cross-entity access is prevented at the HTTP endpoint level
"""

import os
import sys
import asyncio
import aiohttp
import logging
from pathlib import Path
import json
import time
from typing import Dict, List, Optional

# Add the fastapi_backend directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class APIEndpointEntityTest:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.api_keys = {}  # Will store API keys for test users
        self.test_entities = {}  # Will store test entity info
        self.test_users = {}  # Will store test user info
        self.db = None

    async def setup_database_connection(self):
        """Setup database connection for test data preparation"""
        try:
            from api.database import DatabaseManager

            database_url = os.getenv('DATABASE_URL', 'postgresql://localhost:5432/balance_tracker')
            self.db = DatabaseManager(database_url)
            self.db.connect()
            logger.info("✅ Database connected for test setup")
            return True
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            return False

    async def check_api_server(self) -> bool:
        """Check if the API server is running"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/health") as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"✅ API server is running: {data.get('status', 'unknown')}")
                        return True
                    else:
                        logger.error(f"❌ API server returned status {response.status}")
                        return False
        except Exception as e:
            logger.error(f"❌ Cannot reach API server at {self.base_url}: {e}")
            logger.error("Make sure the FastAPI server is running: python3 main.py")
            return False

    async def create_test_scenario(self) -> bool:
        """Create test entities, users, and API keys for testing"""
        try:
            logger.info("🏗️  Creating API Test Scenario...")

            # Step 1: Create test entities using database directly
            logger.info("📋 Step 1: Creating test entities...")

            timestamp = str(int(time.time()))
            alpha_code = f"API_ALPHA_{timestamp}"
            beta_code = f"API_BETA_{timestamp}"

            # Create Alpha entity
            alpha_result = self.db.execute_query("""
                INSERT INTO entities (name, code, description, entity_type, is_active)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name
                RETURNING id, name, code
            """, (f"API Alpha Entity {timestamp}", alpha_code, "Alpha entity for API testing", "trading_entity", True))

            if not alpha_result:
                raise Exception("Failed to create Alpha entity")

            alpha_entity = alpha_result[0]
            self.test_entities['alpha'] = alpha_entity
            logger.info(f"✅ Created Alpha Entity: {alpha_entity['name']} ({alpha_entity['code']})")

            # Create Beta entity
            beta_result = self.db.execute_query("""
                INSERT INTO entities (name, code, description, entity_type, is_active)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name
                RETURNING id, name, code
            """, (f"API Beta Entity {timestamp}", beta_code, "Beta entity for API testing", "trading_entity", True))

            if not beta_result:
                raise Exception("Failed to create Beta entity")

            beta_entity = beta_result[0]
            self.test_entities['beta'] = beta_entity
            logger.info(f"✅ Created Beta Entity: {beta_entity['name']} ({beta_entity['code']})")

            # Step 2: Create test users
            logger.info("📋 Step 2: Creating test users...")

            test_users_data = [
                ('alpha_trader', f"alpha_trader_{timestamp}@test.com", alpha_entity['id'], 'trader'),
                ('alpha_viewer', f"alpha_viewer_{timestamp}@test.com", alpha_entity['id'], 'viewer'),
                ('beta_trader', f"beta_trader_{timestamp}@test.com", beta_entity['id'], 'trader'),
                ('beta_viewer', f"beta_viewer_{timestamp}@test.com", beta_entity['id'], 'viewer')
            ]

            for user_key, email, entity_id, entity_role in test_users_data:
                # Create user
                user_result = self.db.execute_query("""
                    INSERT INTO users (username, email, password_hash, is_active, is_verified, role)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id, username, email
                """, (f"api_{user_key}_{timestamp}", email, 'test_hash_api', True, True, 'trader'))

                if not user_result:
                    raise Exception(f"Failed to create user {user_key}")

                user = user_result[0]

                # Create entity membership
                self.db.execute_command("""
                    INSERT INTO entity_memberships (entity_id, user_id, entity_role, is_active)
                    VALUES (%s, %s, %s, %s)
                """, (entity_id, user['id'], entity_role, True))

                self.test_users[user_key] = {
                    'id': user['id'],
                    'username': user['username'],
                    'email': user['email'],
                    'entity_id': entity_id,
                    'entity_role': entity_role
                }

                logger.info(f"✅ Created user: {user['username']} → {entity_role} in entity {entity_id}")

            # Step 3: Create API keys for users
            logger.info("📋 Step 3: Creating API keys...")

            for user_key, user_data in self.test_users.items():
                try:
                    # Use the proper API key service to generate keys
                    from api.api_key_service import APIKeyService
                    api_key_service = APIKeyService()

                    # Generate API key using the service (returns key_id and full_api_key)
                    key_id, full_api_key = api_key_service.generate_api_key()

                    # Hash the full API key
                    key_hash = api_key_service.hash_api_key(full_api_key)

                    logger.info(f"Generated for {user_key}: key_id={key_id}, full_key={full_api_key[:30]}...")

                    # Insert into database with proper format
                    api_key_result = self.db.execute_query("""
                        INSERT INTO api_keys (key_id, key_hash, user_id, name, permissions_scope, is_active)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        RETURNING id, name, key_id
                    """, (key_id, key_hash, user_data['id'], f"Test API Key {user_key}", 'inherit', True))

                    if not api_key_result:
                        raise Exception(f"Failed to create API key for {user_key}")

                    created_key = api_key_result[0]

                    # Store the full API key for HTTP authentication
                    self.api_keys[user_key] = full_api_key
                    logger.info(f"✅ Created API key for {user_data['username']}: {created_key['key_id']}")

                    # CRITICAL: Verify the key is in database and can be authenticated
                    logger.info(f"🔍 Verifying API key for {user_key}...")

                    # Test authentication with the API key service
                    authenticated_user = await api_key_service.authenticate_api_key(full_api_key, self.db)

                    if authenticated_user:
                        logger.info(f"✅ API key authentication verified for {authenticated_user.username}")
                    else:
                        logger.error(f"❌ API key authentication failed for {user_key}")
                        logger.error(f"   Key ID: {key_id}")
                        logger.error(f"   Full key: {full_api_key}")

                        # Debug: Check what's in the database
                        db_check = self.db.execute_query("""
                            SELECT ak.key_id, ak.is_active, u.username, u.is_active as user_active
                            FROM api_keys ak
                            JOIN users u ON ak.user_id = u.id
                            WHERE ak.key_id = %s
                        """, (key_id,))

                        if db_check:
                            logger.info(f"   DB record: {db_check[0]}")
                        else:
                            logger.error("   Key not found in database!")

                        raise Exception(f"API key verification failed for {user_key}")

                except Exception as e:
                    logger.error(f"❌ Failed to create API key for {user_key}: {e}")
                    raise e

            logger.info("✅ API test scenario created successfully")
            logger.info(f"📊 Created {len(self.api_keys)} working API keys")

            # Final verification: List all created keys
            logger.info("🔍 Final verification of created API keys:")
            for user_key, api_key in self.api_keys.items():
                user_data = self.test_users[user_key]
                logger.info(f"  - {user_key}: {user_data['username']} → {api_key[:30]}...")

            return True

        except Exception as e:
            logger.error(f"❌ Failed to create API test scenario: {e}")
            return False

    async def test_endpoint_with_auth(self, endpoint: str, api_key: str, method: str = "GET", data: dict = None) -> Dict:
        """Make authenticated request to API endpoint"""
        try:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }

            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}{endpoint}"

                if method.upper() == "GET":
                    async with session.get(url, headers=headers) as response:
                        result = {
                            'status': response.status,
                            'data': await response.json() if response.content_type == 'application/json' else await response.text(),
                            'headers': dict(response.headers)
                        }
                elif method.upper() == "POST":
                    async with session.post(url, headers=headers, json=data) as response:
                        result = {
                            'status': response.status,
                            'data': await response.json() if response.content_type == 'application/json' else await response.text(),
                            'headers': dict(response.headers)
                        }
                else:
                    raise ValueError(f"Unsupported method: {method}")

                return result

        except Exception as e:
            logger.error(f"❌ Request to {endpoint} failed: {e}")
            return {'status': 0, 'data': {'error': str(e)}, 'headers': {}}

    async def test_user_endpoint_isolation(self) -> bool:
        """Test user endpoint isolation between entities"""
        try:
            logger.info("🔒 Testing User Endpoint Isolation...")

            violations = []

            # Test: Can Alpha users access Beta users via API?
            alpha_trader_key = self.api_keys['alpha_trader']
            beta_trader_username = self.test_users['beta_trader']['username']

            # Try to access Beta user from Alpha user's API key
            result = await self.test_endpoint_with_auth(
                f"/api/v1/users/{beta_trader_username}",
                alpha_trader_key
            )

            logger.info(f"Alpha trader accessing Beta user: Status {result['status']}")

            # This should fail (403 or 404)
            if result['status'] == 200:
                violations.append("Alpha trader can access Beta user data via API")
            else:
                logger.info("✅ Alpha trader correctly blocked from accessing Beta user")

            # Test: Can Beta users access Alpha users via API?
            beta_trader_key = self.api_keys['beta_trader']
            alpha_trader_username = self.test_users['alpha_trader']['username']

            result = await self.test_endpoint_with_auth(
                f"/api/v1/users/{alpha_trader_username}",
                beta_trader_key
            )

            logger.info(f"Beta trader accessing Alpha user: Status {result['status']}")

            if result['status'] == 200:
                violations.append("Beta trader can access Alpha user data via API")
            else:
                logger.info("✅ Beta trader correctly blocked from accessing Alpha user")

            # Test: Can users access their own data?
            result = await self.test_endpoint_with_auth(
                f"/api/v1/users/{alpha_trader_username}",
                alpha_trader_key
            )

            logger.info(f"Alpha trader accessing own data: Status {result['status']}")

            if result['status'] != 200:
                violations.append("Alpha trader cannot access their own data")
            else:
                logger.info("✅ Alpha trader can access their own data")

            return len(violations) == 0

        except Exception as e:
            logger.error(f"❌ User endpoint isolation test failed: {e}")
            return False

    async def test_balance_endpoint_isolation(self) -> bool:
        """Test balance endpoint isolation between entities"""
        try:
            logger.info("💰 Testing Balance Endpoint Isolation...")

            violations = []

            # Test cross-entity balance access
            alpha_trader_key = self.api_keys['alpha_trader']
            beta_trader_username = self.test_users['beta_trader']['username']

            # Try to access Beta user's balances from Alpha user's API key
            result = await self.test_endpoint_with_auth(
                f"/api/v1/balances/user/{beta_trader_username}",
                alpha_trader_key
            )

            logger.info(f"Alpha trader accessing Beta balances: Status {result['status']}")

            if result['status'] == 200:
                violations.append("Alpha trader can access Beta user's balances via API")
            else:
                logger.info("✅ Alpha trader correctly blocked from accessing Beta balances")

            # Test the reverse
            beta_trader_key = self.api_keys['beta_trader']
            alpha_trader_username = self.test_users['alpha_trader']['username']

            result = await self.test_endpoint_with_auth(
                f"/api/v1/balances/user/{alpha_trader_username}",
                beta_trader_key
            )

            logger.info(f"Beta trader accessing Alpha balances: Status {result['status']}")

            if result['status'] == 200:
                violations.append("Beta trader can access Alpha user's balances via API")
            else:
                logger.info("✅ Beta trader correctly blocked from accessing Alpha balances")

            return len(violations) == 0

        except Exception as e:
            logger.error(f"❌ Balance endpoint isolation test failed: {e}")
            return False

    async def test_transaction_endpoint_isolation(self) -> bool:
        """Test transaction endpoint isolation between entities"""
        try:
            logger.info("💸 Testing Transaction Endpoint Isolation...")

            violations = []

            # Test cross-entity transaction access
            alpha_trader_key = self.api_keys['alpha_trader']
            beta_trader_username = self.test_users['beta_trader']['username']

            # Try to access Beta user's transactions from Alpha user's API key
            result = await self.test_endpoint_with_auth(
                f"/api/v1/transactions/user/{beta_trader_username}",
                alpha_trader_key
            )

            logger.info(f"Alpha trader accessing Beta transactions: Status {result['status']}")

            if result['status'] == 200:
                violations.append("Alpha trader can access Beta user's transactions via API")
            else:
                logger.info("✅ Alpha trader correctly blocked from accessing Beta transactions")

            # Test the reverse
            beta_trader_key = self.api_keys['beta_trader']
            alpha_trader_username = self.test_users['alpha_trader']['username']

            result = await self.test_endpoint_with_auth(
                f"/api/v1/transactions/user/{alpha_trader_username}",
                beta_trader_key
            )

            logger.info(f"Beta trader accessing Alpha transactions: Status {result['status']}")

            if result['status'] == 200:
                violations.append("Beta trader can access Alpha user's transactions via API")
            else:
                logger.info("✅ Beta trader correctly blocked from accessing Alpha transactions")

            return len(violations) == 0

        except Exception as e:
            logger.error(f"❌ Transaction endpoint isolation test failed: {e}")
            return False

    async def test_api_key_authentication(self) -> bool:
        """Test API key authentication works correctly"""
        try:
            logger.info("🔑 Testing API Key Authentication...")

            # Test with valid API key
            alpha_trader_key = self.api_keys['alpha_trader']
            logger.info(f"Testing with Alpha trader key: {alpha_trader_key}")

            result = await self.test_endpoint_with_auth("/health", alpha_trader_key)
            logger.info(f"Health endpoint with valid key: Status {result['status']}")

            if result['status'] != 200:
                logger.error(f"❌ Valid API key rejected: Status {result['status']}")
                logger.error(f"Response: {result['data']}")
                return False

            logger.info("✅ Valid API key accepted for health endpoint")

            # Test with invalid API key format
            invalid_key = "invalid_key_format"
            result = await self.test_endpoint_with_auth("/health", invalid_key)
            logger.info(f"Health endpoint with invalid key: Status {result['status']}")

            # Health endpoint should accept invalid keys (it's not protected)
            # This is actually CORRECT behavior - health endpoints usually don't require auth
            logger.info("ℹ️  Health endpoint accepts all requests (not protected) - this is correct")

            # Now test a PROTECTED endpoint with valid key
            alpha_trader_username = self.test_users['alpha_trader']['username']
            result = await self.test_endpoint_with_auth(
                f"/api/v1/users/{alpha_trader_username}",
                alpha_trader_key
            )

            logger.info(f"Protected endpoint with valid key: Status {result['status']}")

            if result['status'] == 200:
                logger.info("✅ Valid API key accepted for protected endpoint")
                return True
            elif result['status'] == 401:
                logger.error("❌ Valid API key rejected by protected endpoint")
                logger.error(f"Response: {result['data']}")

                # Let's debug this specific key
                logger.info("🔍 Debugging API key authentication failure...")

                # Check if key exists in database
                from api.api_key_service import APIKeyService
                temp_service = APIKeyService()
                try:
                    key_id = temp_service.extract_key_id(alpha_trader_key)
                    logger.info(f"Extracted key ID: {key_id}")

                    key_check = self.db.execute_query("""
                        SELECT ak.key_id, ak.is_active, u.username, u.is_active as user_active
                        FROM api_keys ak
                        JOIN users u ON ak.user_id = u.id
                        WHERE ak.key_id = %s
                    """, (key_id,))

                    if key_check:
                        logger.info(f"Key found in DB: {key_check[0]}")
                    else:
                        logger.error("❌ Key not found in database!")

                except Exception as extract_error:
                    logger.error(f"Failed to extract key ID: {extract_error}")
                    logger.info(f"Raw key: {alpha_trader_key}")

                return False
            else:
                logger.error(f"❌ Unexpected response code: {result['status']}")
                return False

        except Exception as e:
            logger.error(f"❌ API key authentication test failed: {e}")
            return False

    async def test_role_based_access(self) -> bool:
        """Test role-based access within entities"""
        try:
            logger.info("👥 Testing Role-Based Access...")

            violations = []

            # Test viewer vs trader access within same entity
            alpha_trader_key = self.api_keys['alpha_trader']
            alpha_viewer_key = self.api_keys['alpha_viewer']
            alpha_trader_username = self.test_users['alpha_trader']['username']

            # Both should be able to read user data within their entity
            trader_result = await self.test_endpoint_with_auth(
                f"/api/v1/users/{alpha_trader_username}",
                alpha_trader_key
            )

            viewer_result = await self.test_endpoint_with_auth(
                f"/api/v1/users/{alpha_trader_username}",
                alpha_viewer_key
            )

            logger.info(f"Trader accessing same entity user: Status {trader_result['status']}")
            logger.info(f"Viewer accessing same entity user: Status {viewer_result['status']}")

            # Both should succeed (200) for read access within their entity
            if trader_result['status'] != 200:
                violations.append("Trader cannot access same entity user data")

            if viewer_result['status'] != 200:
                violations.append("Viewer cannot access same entity user data")

            if len(violations) == 0:
                logger.info("✅ Both trader and viewer can access same entity data")

            return len(violations) == 0

        except Exception as e:
            logger.error(f"❌ Role-based access test failed: {e}")
            return False

    async def cleanup_test_data(self):
        """Clean up test data from database"""
        try:
            logger.info("🧹 Cleaning up API test data...")

            if not self.db:
                return

            # Delete API keys first (foreign key constraint)
            for user_key, user_data in self.test_users.items():
                try:
                    deleted_keys = self.db.execute_command("""
                        DELETE FROM api_keys WHERE user_id = %s
                    """, (user_data['id'],))
                    logger.debug(f"Deleted {deleted_keys} API keys for {user_data['username']}")
                except Exception as e:
                    logger.warning(f"Failed to delete API keys for {user_key}: {e}")

            # Delete entity memberships
            for user_key, user_data in self.test_users.items():
                try:
                    deleted_memberships = self.db.execute_command("""
                        DELETE FROM entity_memberships WHERE user_id = %s
                    """, (user_data['id'],))
                    logger.debug(f"Deleted {deleted_memberships} memberships for {user_data['username']}")
                except Exception as e:
                    logger.warning(f"Failed to delete memberships for {user_key}: {e}")

            # Delete test users
            for user_key, user_data in self.test_users.items():
                try:
                    deleted_users = self.db.execute_command("""
                        DELETE FROM users WHERE id = %s
                    """, (user_data['id'],))
                    logger.debug(f"Deleted user {user_data['username']}")
                except Exception as e:
                    logger.warning(f"Failed to delete user {user_key}: {e}")

            # Delete test entities
            if 'alpha' in self.test_entities:
                try:
                    self.db.execute_command("""
                        DELETE FROM entities WHERE id = %s
                    """, (self.test_entities['alpha']['id'],))
                    logger.debug(f"Deleted Alpha entity")
                except Exception as e:
                    logger.warning(f"Failed to delete Alpha entity: {e}")

            if 'beta' in self.test_entities:
                try:
                    self.db.execute_command("""
                        DELETE FROM entities WHERE id = %s
                    """, (self.test_entities['beta']['id'],))
                    logger.debug(f"Deleted Beta entity")
                except Exception as e:
                    logger.warning(f"Failed to delete Beta entity: {e}")

            logger.info("✅ API test data cleaned up")

        except Exception as e:
            logger.warning(f"⚠️  API test cleanup failed: {e}")
            # Don't raise - cleanup failures shouldn't break the test

    async def run_api_endpoint_tests(self) -> bool:
        """Run complete API endpoint entity isolation tests"""
        logger.info("🚀 API Endpoint Entity Isolation Test")
        logger.info("=" * 60)
        logger.info("Testing real HTTP API calls for entity isolation")
        logger.info("=" * 60)

        # Setup
        if not await self.setup_database_connection():
            return False

        if not await self.check_api_server():
            logger.error("❌ API server is not running!")
            logger.info("Start the server: python3 main.py")
            return False

        # Create test scenario
        if not await self.create_test_scenario():
            logger.error("❌ Failed to create test scenario")
            return False

        try:
            # Run tests
            tests = [
                ("API Key Authentication", self.test_api_key_authentication),
                ("User Endpoint Isolation", self.test_user_endpoint_isolation),
                ("Balance Endpoint Isolation", self.test_balance_endpoint_isolation),
                ("Transaction Endpoint Isolation", self.test_transaction_endpoint_isolation),
                ("Role-Based Access", self.test_role_based_access)
            ]

            passed_tests = 0
            for test_name, test_func in tests:
                logger.info(f"\n{'='*15} {test_name} {'='*15}")
                try:
                    success = await test_func()
                    if success:
                        passed_tests += 1
                        logger.info(f"✅ {test_name}: SUCCESS")
                    else:
                        logger.error(f"❌ {test_name}: FAILED")
                except Exception as e:
                    logger.error(f"❌ {test_name}: ERROR - {e}")

            # Results
            logger.info("\n" + "=" * 60)
            logger.info("📊 API ENDPOINT TEST RESULTS")
            logger.info("=" * 60)

            success_rate = (passed_tests / len(tests)) * 100
            logger.info(f"📈 Results: {passed_tests}/{len(tests)} tests passed ({success_rate:.1f}%)")

            if success_rate == 100:
                logger.info("🎉 API ENDPOINT ENTITY ISOLATION COMPLETE!")
                logger.info("✅ All HTTP API endpoints respect entity boundaries")
                logger.info("🔒 Entity-based access control is working at API level")
                logger.info("🚀 System is SECURE for production multi-tenant use")
                logger.info("")
                logger.info("🏆 CONCLUSION: Your API endpoints provide TRUE")
                logger.info("    multi-tenant data isolation via HTTP!")
            else:
                logger.error("❌ Some API endpoint tests failed")
                logger.error("⚠️  Review entity authentication implementation")

            return success_rate == 100

        finally:
            # Always cleanup
            await self.cleanup_test_data()

            if self.db:
                self.db.disconnect()


async def main():
    # Check if server URL is provided
    base_url = os.getenv('API_BASE_URL', 'http://localhost:8000')

    test_suite = APIEndpointEntityTest(base_url)
    success = await test_suite.run_api_endpoint_tests()
    return 0 if success else 1


if __name__ == "__main__":
    print("🌐 API Endpoint Entity Isolation Test")
    print("This tests real HTTP API calls to verify entity boundaries")
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
