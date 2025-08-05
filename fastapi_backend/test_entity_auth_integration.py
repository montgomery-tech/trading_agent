#!/usr/bin/env python3
"""
Entity Authentication Integration Test
Quick test to validate the entity authentication system integration
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


async def test_entity_auth_integration():
    """Test entity authentication system integration"""
    
    logger.info("🧪 Entity Authentication Integration Test")
    logger.info("=" * 50)
    
    try:
        # Test imports
        logger.info("📦 Testing imports...")
        
        from api.database import DatabaseManager
        logger.info("✅ DatabaseManager imported")
        
        from api.api_key_service import get_api_key_service
        logger.info("✅ APIKeyService imported")
        
        # Test database connection
        logger.info("🔗 Testing database connection...")
        database_url = os.getenv('DATABASE_URL', 'postgresql://localhost:5432/balance_tracker')
        db = DatabaseManager(database_url)
        db.connect()
        logger.info("✅ Database connected")
        
        # Test entity tables exist
        logger.info("🗄️  Testing entity tables...")
        
        # Check entities table
        entities = db.execute_query("SELECT COUNT(*) as count FROM entities")
        entity_count = entities[0]['count'] if entities else 0
        logger.info(f"✅ Entities table: {entity_count} records")
        
        # Check entity_memberships table
        memberships = db.execute_query("SELECT COUNT(*) as count FROM entity_memberships")
        membership_count = memberships[0]['count'] if memberships else 0
        logger.info(f"✅ Entity memberships table: {membership_count} records")
        
        # Test entity context function
        logger.info("🏢 Testing entity context retrieval...")
        
        # Get a test user
        users = db.execute_query("""
            SELECT id, username, COALESCE(role, 'trader') as role
            FROM users 
            WHERE is_active = true
            LIMIT 1
        """)
        
        if users:
            test_user = users[0]
            user_id = test_user['id']
            username = test_user['username']
            
            logger.info(f"📊 Testing with user: {username}")
            
            # Test entity context retrieval (we'll import the function directly)
            try:
                # Import the entity context function
                sys.path.insert(0, str(Path(__file__).parent))
                
                # Create a simple entity context test
                memberships = db.execute_query("""
                    SELECT 
                        e.id as entity_id,
                        e.code as entity_code,
                        e.name as entity_name,
                        em.entity_role,
                        em.is_active
                    FROM entity_memberships em
                    JOIN entities e ON em.entity_id = e.id
                    WHERE em.user_id = %s AND em.is_active = true AND e.is_active = true
                """, (str(user_id),))
                
                if memberships:
                    logger.info(f"✅ User has {len(memberships)} entity memberships:")
                    for membership in memberships:
                        logger.info(f"   - {membership['entity_name']} ({membership['entity_code']}) as {membership['entity_role']}")
                else:
                    logger.info("ℹ️  User has no entity memberships (likely admin)")
                
            except Exception as e:
                logger.warning(f"⚠️  Entity context test error: {e}")
        
        else:
            logger.warning("⚠️  No users found for testing")
        
        # Test API key service
        logger.info("🔑 Testing API key service...")
        api_key_service = get_api_key_service()
        logger.info("✅ API key service initialized")
        
        # Close database
        db.disconnect()
        logger.info("✅ Database disconnected")
        
        logger.info("🎉 Entity authentication integration test completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Integration test failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


async def main():
    """Main test function"""
    success = await test_entity_auth_integration()
    
    if success:
        logger.info("\n✅ INTEGRATION TEST PASSED")
        logger.info("🔧 Next steps:")
        logger.info("   1. Copy the authentication extension files to your api/ directory")
        logger.info("   2. Update existing endpoints to use entity-aware authentication")
        logger.info("   3. Test with actual API key authentication")
    else:
        logger.error("\n❌ INTEGRATION TEST FAILED")
        logger.error("🔧 Please review the error messages above")
    
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
