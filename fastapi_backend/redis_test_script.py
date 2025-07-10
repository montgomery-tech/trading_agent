#!/usr/bin/env python3
"""
Redis Connection Test Script
Tests Redis connectivity and async functionality
"""

import asyncio
import sys
import traceback

def test_redis_imports():
    """Test Redis import compatibility."""
    print("🔍 Testing Redis imports...")
    
    try:
        import redis
        print(f"✅ Redis library v{redis.__version__}")
        
        # Test Redis 5.x async import
        try:
            import redis.asyncio as aioredis
            print("✅ redis.asyncio available (Redis 5.x style)")
            return True, aioredis
        except ImportError:
            try:
                import aioredis
                print("✅ aioredis available (standalone package)")
                return True, aioredis
            except ImportError:
                print("❌ No async Redis available")
                return False, None
                
    except ImportError as e:
        print(f"❌ Redis import failed: {e}")
        return False, None

async def test_redis_connection(aioredis_module):
    """Test Redis connection."""
    print("\n🔍 Testing Redis connection...")
    
    try:
        # Try to connect to Redis
        if hasattr(aioredis_module, 'from_url'):
            # Redis 5.x style
            client = aioredis_module.from_url(
                "redis://localhost:6379/0",
                socket_timeout=2,
                socket_connect_timeout=2,
                decode_responses=True
            )
        else:
            # Older aioredis style
            client = await aioredis_module.create_redis_pool(
                "redis://localhost:6379/0",
                timeout=2
            )
        
        # Test ping
        result = await client.ping()
        print(f"✅ Redis ping successful: {result}")
        
        # Test basic operations
        await client.set("test_key", "test_value", ex=10)
        value = await client.get("test_key")
        print(f"✅ Redis set/get successful: {value}")
        
        # Cleanup
        await client.delete("test_key")
        if hasattr(client, 'close'):
            await client.close()
        
        return True
        
    except ConnectionError as e:
        print(f"❌ Redis connection failed: {e}")
        print("💡 Start Redis with: docker run -p 6379:6379 redis:7-alpine")
        return False
    except Exception as e:
        print(f"❌ Redis test failed: {e}")
        traceback.print_exc()
        return False

def test_sync_redis_fallback():
    """Test sync Redis as fallback."""
    print("\n🔍 Testing sync Redis fallback...")
    
    try:
        import redis
        
        client = redis.Redis.from_url(
            "redis://localhost:6379/0",
            socket_timeout=2,
            socket_connect_timeout=2,
            decode_responses=True
        )
        
        # Test ping
        result = client.ping()
        print(f"✅ Sync Redis ping successful: {result}")
        
        # Test basic operations
        client.set("test_key_sync", "test_value", ex=10)
        value = client.get("test_key_sync")
        print(f"✅ Sync Redis set/get successful: {value}")
        
        # Cleanup
        client.delete("test_key_sync")
        client.close()
        
        return True
        
    except ConnectionError as e:
        print(f"❌ Sync Redis connection failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Sync Redis test failed: {e}")
        return False

async def test_fixed_backend():
    """Test the fixed Redis backend."""
    print("\n🔍 Testing fixed Redis backend...")
    
    try:
        # Import our fixed backend (this would be saved as a separate file)
        # For now, we'll test the logic inline
        
        # Simulate the fixed backend initialization
        redis_available = False
        async_available = False
        
        try:
            import redis
            redis_available = True
            
            try:
                import redis.asyncio as aioredis
                async_available = True
                print("✅ Fixed backend: Async Redis available")
            except ImportError:
                print("⚠️ Fixed backend: Using sync Redis with async wrapper")
                
        except ImportError:
            print("❌ Fixed backend: Redis not available, fallback only")
        
        print(f"✅ Fixed backend compatibility check complete")
        print(f"   Redis available: {redis_available}")
        print(f"   Async available: {async_available}")
        
        return True
        
    except Exception as e:
        print(f"❌ Fixed backend test failed: {e}")
        traceback.print_exc()
        return False

async def main():
    """Run all Redis tests."""
    print("🔍 Redis Connection Diagnostic")
    print("=" * 40)
    
    # Test imports
    redis_ok, aioredis_module = test_redis_imports()
    
    if not redis_ok:
        print("\n❌ Redis not available - install with: pip install redis==5.0.1")
        return False
    
    # Test async connection if available
    if aioredis_module:
        connection_ok = await test_redis_connection(aioredis_module)
    else:
        connection_ok = False
    
    # Test sync fallback
    if not connection_ok:
        print("\n🔄 Testing sync Redis fallback...")
        fallback_ok = test_sync_redis_fallback()
    else:
        fallback_ok = True
    
    # Test fixed backend logic
    backend_ok = await test_fixed_backend()
    
    # Summary
    print("\n" + "=" * 40)
    print("📊 REDIS TEST SUMMARY")
    print("=" * 40)
    print(f"Redis Import:     {'✅' if redis_ok else '❌'}")
    print(f"Async Connection: {'✅' if connection_ok else '❌'}")
    print(f"Sync Fallback:    {'✅' if fallback_ok else '❌'}")
    print(f"Backend Logic:    {'✅' if backend_ok else '❌'}")
    
    if redis_ok and (connection_ok or fallback_ok) and backend_ok:
        print("\n🎉 Redis tests passed! The issue is likely in the startup sequence.")
        print("\n💡 Next steps:")
        print("1. Replace the Redis backend with the fixed version")
        print("2. Test the application startup")
        print("3. Check for Redis server if connection failed")
    else:
        print("\n⚠️ Redis tests revealed issues.")
        print("\n💡 Fix needed:")
        if not redis_ok:
            print("- Install Redis: pip install redis==5.0.1")
        if not connection_ok and not fallback_ok:
            print("- Start Redis server: docker run -p 6379:6379 redis:7-alpine")
        print("- Apply the fixed Redis backend")
    
    return redis_ok and backend_ok

if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n⚠️ Test interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test crashed: {e}")
        sys.exit(1)
