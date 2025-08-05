#!/usr/bin/env python3
"""
Debug API Authentication
Diagnoses API key authentication issues by testing the database directly
"""

import os
import sys
import asyncio
from pathlib import Path
import logging

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Add the fastapi_backend directory to Python path
sys.path.insert(0, str(Path(__file__).parent))


async def debug_authentication():
    """Debug the API key authentication process"""
    
    print("🔍 API Key Authentication Debug")
    print("=" * 50)
    
    try:
        # Import dependencies
        from api.database import DatabaseManager
        from api.api_key_service import APIKeyService
        
        # Connect to database
        database_url = os.getenv('DATABASE_URL', 'postgresql://localhost:5432/balance_tracker')
        db = DatabaseManager(database_url)
        db.connect()
        print("✅ Database connected")
        
        # Get API key service
        api_service = APIKeyService()
        print("✅ API Key Service initialized")
        
        # Step 1: Check if there are any API keys in the database
        print("\n📋 Step 1: Check API keys in database")
        print("-" * 40)
        
        api_keys = db.execute_query("""
            SELECT ak.key_id, ak.name, ak.is_active, u.username, u.is_active as user_active
            FROM api_keys ak
            JOIN users u ON ak.user_id = u.id
            ORDER BY ak.created_at DESC
            LIMIT 10
        """)
        
        print(f"Found {len(api_keys)} API keys:")
        for key in api_keys:
            print(f"  - {key['key_id']} | {key['name']} | Active: {key['is_active']} | User: {key['username']} (Active: {key['user_active']})")
        
        if not api_keys:
            print("❌ No API keys found in database!")
            return False
        
        # Step 2: Test with a known API key
        print("\n📋 Step 2: Test authentication with existing key")
        print("-" * 40)
        
        test_key_data = api_keys[0]  # Use the first API key
        test_key_id = test_key_data['key_id']
        
        print(f"Testing with key ID: {test_key_id}")
        
        # We need to generate a test key with the same key_id pattern
        # Since we can't get the original full key, let's create a new test key
        test_key_id_new, test_full_key = api_service.generate_api_key()
        test_hash = api_service.hash_api_key(test_full_key)
        
        # Insert test key
        result = db.execute_query("""
            INSERT INTO api_keys (key_id, key_hash, user_id, name, permissions_scope, is_active)
            SELECT %s, %s, u.id, %s, %s, %s
            FROM users u
            WHERE u.username = %s AND u.is_active = true
            LIMIT 1
            RETURNING id, key_id
        """, (test_key_id_new, test_hash, "Debug Test Key", "inherit", True, test_key_data['username']))
        
        if result:
            inserted_key = result[0]
            print(f"✅ Created test key: {inserted_key['key_id']}")
            
            # Step 3: Test authentication
            print("\n📋 Step 3: Test API key authentication")
            print("-" * 40)
            
            print(f"Testing full key: {test_full_key}")
            
            # Test the authentication method
            authenticated_user = await api_service.authenticate_api_key(test_full_key, db)
            
            if authenticated_user:
                print("✅ Authentication successful!")
                print(f"  - User: {authenticated_user.username}")
                print(f"  - Role: {authenticated_user.role}")
                print(f"  - API Key Name: {authenticated_user.api_key_name}")
                print(f"  - API Key ID: {authenticated_user.api_key_id}")
                
                # Step 4: Test key format validation
                print("\n📋 Step 4: Test key format validation")
                print("-" * 40)
                
                from api.api_key_models import APIKeyValidation
                
                is_valid_format = APIKeyValidation.validate_key_format(test_full_key)
                print(f"Key format valid: {is_valid_format}")
                
                extracted_key_id = api_service.extract_key_id(test_full_key)
                print(f"Extracted key ID: {extracted_key_id}")
                print(f"Matches database: {extracted_key_id == test_key_id_new}")
                
                # Cleanup test key
                db.execute_command("DELETE FROM api_keys WHERE key_id = %s", (test_key_id_new,))
                print("🧹 Cleaned up test key")
                
                return True
            else:
                print("❌ Authentication failed!")
                
                # Debug: Check what's in the database
                debug_query = db.execute_query("""
                    SELECT * FROM api_keys WHERE key_id = %s
                """, (test_key_id_new,))
                
                print("Database record:")
                if debug_query:
                    record = debug_query[0]
                    print(f"  - key_id: {record['key_id']}")
                    print(f"  - is_active: {record['is_active']}")
                    print(f"  - user_id: {record['user_id']}")
                
                # Test hash verification
                if debug_query:
                    stored_hash = debug_query[0]['key_hash']
                    hash_valid = api_service.verify_api_key(test_full_key, stored_hash)
                    print(f"  - Hash verification: {hash_valid}")
                
                # Cleanup test key
                db.execute_command("DELETE FROM api_keys WHERE key_id = %s", (test_key_id_new,))
                return False
        else:
            print("❌ Failed to create test key")
            return False
        
    except Exception as e:
        logger.error(f"Debug failed: {e}")
        print(f"❌ Debug failed: {e}")
        return False
    
    finally:
        if 'db' in locals():
            db.disconnect()


async def test_actual_endpoint():
    """Test making an actual HTTP call to the endpoint"""
    
    print("\n🌐 HTTP Endpoint Test")
    print("=" * 30)
    
    try:
        import aiohttp
        
        # Test the health endpoint first
        async with aiohttp.ClientSession() as session:
            # Test without authentication
            async with session.get("http://localhost:8000/health") as response:
                print(f"Health endpoint (no auth): {response.status}")
            
            # Test a protected endpoint without auth
            async with session.get("http://localhost:8000/api/v1/users/test") as response:
                print(f"Protected endpoint (no auth): {response.status}")
                if response.status != 401:
                    print("⚠️  Protected endpoint should return 401 without auth")
        
    except Exception as e:
        print(f"HTTP test failed: {e}")


async def main():
    success = await debug_authentication()
    await test_actual_endpoint()
    
    if success:
        print("\n✅ Authentication debugging completed successfully")
    else:
        print("\n❌ Authentication debugging found issues")
    
    return success


if __name__ == "__main__":
    asyncio.run(main())
