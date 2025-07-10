#!/usr/bin/env python3
"""
Rate Limiting Diagnostic Script
Helps diagnose issues with the rate limiting system
"""

import sys
import traceback
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_imports():
    """Test all required imports."""
    print("🔍 Testing imports...")
    
    try:
        from api.security.enhanced_rate_limiting_service import rate_limiting_service, RateLimitType
        print("✅ Enhanced rate limiting service imported")
    except Exception as e:
        print(f"❌ Enhanced rate limiting service import failed: {e}")
        traceback.print_exc()
        return False
    
    try:
        from api.security.enhanced_rate_limiting_middleware import EnhancedRateLimitingMiddleware, RateLimitingConfigMiddleware
        print("✅ Enhanced rate limiting middleware imported")
    except Exception as e:
        print(f"❌ Enhanced rate limiting middleware import failed: {e}")
        traceback.print_exc()
        return False
    
    try:
        from api.security.redis_rate_limiting_backend import RedisRateLimitingBackend
        print("✅ Redis backend imported")
    except Exception as e:
        print(f"❌ Redis backend import failed: {e}")
        traceback.print_exc()
        return False
    
    return True

def test_redis_dependencies():
    """Test Redis-related dependencies."""
    print("\n🔍 Testing Redis dependencies...")
    
    try:
        import redis
        print(f"✅ Redis library imported (version: {redis.__version__})")
    except Exception as e:
        print(f"❌ Redis library import failed: {e}")
        return False
    
    try:
        import redis.asyncio as aioredis
        print("✅ Async Redis imported")
    except Exception as e:
        print(f"❌ Async Redis import failed: {e}")
        return False
    
    return True

def test_rate_limiting_service():
    """Test the rate limiting service basic functionality."""
    print("\n🔍 Testing rate limiting service...")
    
    try:
        from api.security.enhanced_rate_limiting_service import rate_limiting_service
        
        # Test getting metrics
        metrics = rate_limiting_service.get_metrics()
        print(f"✅ Service metrics: {metrics}")
        
        # Test getting config
        config = rate_limiting_service.get_config("default")
        print(f"✅ Default config: requests={config.requests}, window={config.window}")
        
        return True
        
    except Exception as e:
        print(f"❌ Rate limiting service test failed: {e}")
        traceback.print_exc()
        return False

def test_basic_rate_limit_check():
    """Test basic rate limit check."""
    print("\n🔍 Testing basic rate limit check...")
    
    try:
        import asyncio
        from api.security.enhanced_rate_limiting_service import rate_limiting_service
        
        async def test_check():
            result = await rate_limiting_service.check_rate_limit(
                ip="127.0.0.1",
                user_id=None,
                user_data=None,
                endpoint_path="/test",
                request_method="GET"
            )
            print(f"✅ Rate limit check result: allowed={result.allowed}, remaining={result.remaining}")
            return result
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(test_check())
        loop.close()
        
        return result.allowed
        
    except Exception as e:
        print(f"❌ Rate limit check failed: {e}")
        traceback.print_exc()
        return False

def test_redis_backend_init():
    """Test Redis backend initialization."""
    print("\n🔍 Testing Redis backend initialization...")
    
    try:
        import asyncio
        from api.security.redis_rate_limiting_backend import RedisRateLimitingBackend
        
        async def test_init():
            backend = RedisRateLimitingBackend()
            success = await backend.initialize()
            print(f"✅ Redis backend initialized: {success}")
            
            if backend.redis_available:
                print("✅ Redis is available")
            else:
                print("⚠️ Redis not available, using fallback")
            
            await backend.cleanup()
            return success
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(test_init())
        loop.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Redis backend test failed: {e}")
        traceback.print_exc()
        return False

def test_configuration():
    """Test configuration loading."""
    print("\n🔍 Testing configuration...")
    
    try:
        from api.config import settings
        
        print(f"✅ Rate limiting enabled: {getattr(settings, 'RATE_LIMIT_ENABLED', 'NOT SET')}")
        print(f"✅ Redis URL: {getattr(settings, 'RATE_LIMIT_REDIS_URL', 'NOT SET')}")
        print(f"✅ Fallback enabled: {getattr(settings, 'RATE_LIMIT_FALLBACK_TO_MEMORY', 'NOT SET')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all diagnostic tests."""
    print("🔐 RATE LIMITING DIAGNOSTIC SCRIPT")
    print("=" * 50)
    
    tests = [
        ("Import Tests", test_imports),
        ("Redis Dependencies", test_redis_dependencies),
        ("Configuration", test_configuration),
        ("Rate Limiting Service", test_rate_limiting_service),
        ("Redis Backend", test_redis_backend_init),
        ("Basic Rate Limit Check", test_basic_rate_limit_check),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n🧪 Running: {test_name}")
        try:
            result = test_func()
            results[test_name] = result
        except Exception as e:
            print(f"❌ Test {test_name} crashed: {e}")
            results[test_name] = False
    
    print("\n" + "=" * 50)
    print("📊 DIAGNOSTIC RESULTS")
    print("=" * 50)
    
    total_tests = len(results)
    passed_tests = sum(1 for result in results.values() if result)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} - {test_name}")
    
    print(f"\n🎯 Overall: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 All diagnostics passed! Rate limiting should work.")
    else:
        print("⚠️ Some diagnostics failed. Check the errors above.")
    
    return passed_tests == total_tests

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
