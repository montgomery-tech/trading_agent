#!/usr/bin/env python3
"""
Redis Rate Limiting Integration Fix
Fixes the issue where rate limiting is not using Redis keys
"""

import asyncio
import sys
import os
import logging
import time
import redis
import requests
from typing import Dict, Any

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class RedisRateLimitingFix:
    """Fix Redis rate limiting integration issues"""
    
    def __init__(self):
        self.redis_host = "localhost"
        self.redis_port = 6379
        self.redis_db = 1
        self.fastapi_url = "http://localhost:8000"
        
    def verify_redis_connection(self) -> bool:
        """Verify Redis is working"""
        print("🔍 Verifying Redis connection...")
        try:
            r = redis.Redis(host=self.redis_host, port=self.redis_port, db=self.redis_db, decode_responses=True)
            result = r.ping()
            print(f"✅ Redis ping successful: {result}")
            
            # Test set/get
            test_key = "test_key_" + str(int(time.time()))
            r.setex(test_key, 10, "test_value")
            retrieved = r.get(test_key)
            r.delete(test_key)
            
            if retrieved == "test_value":
                print("✅ Redis read/write operations working")
                return True
            else:
                print(f"❌ Redis read/write failed: expected 'test_value', got '{retrieved}'")
                return False
                
        except Exception as e:
            print(f"❌ Redis connection failed: {e}")
            return False
    
    async def test_rate_limiting_service_initialization(self) -> bool:
        """Test if the rate limiting service properly initializes Redis"""
        print("\n🔍 Testing rate limiting service Redis initialization...")
        
        try:
            from api.security.enhanced_rate_limiting_service import rate_limiting_service
            
            # Force Redis initialization
            if not rate_limiting_service._redis_initialized:
                print("   Rate limiting service Redis not initialized, initializing...")
                await rate_limiting_service.initialize_redis()
            
            print(f"   Redis initialized: {rate_limiting_service._redis_initialized}")
            print(f"   Redis backend: {rate_limiting_service.redis_backend}")
            
            if rate_limiting_service.redis_backend:
                print(f"   Redis available: {rate_limiting_service.redis_backend.redis_available}")
                print(f"   Redis client: {rate_limiting_service.redis_backend.redis_client}")
                print(f"   Key prefix: {rate_limiting_service.redis_backend.key_prefix}")
                
                # Test health check
                health = await rate_limiting_service.redis_backend._health_check()
                print(f"   Health check: {health}")
                
                return health
            else:
                print("   ❌ Redis backend not created")
                return False
                
        except Exception as e:
            print(f"❌ Rate limiting service test failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def test_direct_rate_check(self) -> bool:
        """Test a direct rate limiting check to see if Redis keys are created"""
        print("\n🔍 Testing direct rate limiting check...")
        
        try:
            from api.security.enhanced_rate_limiting_service import rate_limiting_service
            
            # Clear any existing keys first
            r = redis.Redis(host=self.redis_host, port=self.redis_port, db=self.redis_db, decode_responses=True)
            for key in r.scan_iter(match="rate_limit*"):
                r.delete(key)
            print("   Cleared existing rate limiting keys")
            
            # Make a direct rate limit check
            test_ip = "127.0.0.1"
            test_path = "/health"
            
            print(f"   Making rate limit check for IP: {test_ip}, path: {test_path}")
            
            result = await rate_limiting_service.check_rate_limit(
                ip=test_ip,
                endpoint_path=test_path,
                user_data=None
            )
            
            print(f"   Rate limit result:")
            print(f"     - Allowed: {result.allowed}")
            print(f"     - Remaining: {result.remaining}")
            print(f"     - Limit type: {result.limit_type}")
            print(f"     - Reset time: {getattr(result, 'reset_time', 'N/A')}")
            
            # Check if keys were created in Redis
            rate_limit_keys = list(r.scan_iter(match="rate_limit*"))
            print(f"   Keys created in Redis: {len(rate_limit_keys)}")
            
            if rate_limit_keys:
                print("   Redis keys found:")
                for key in rate_limit_keys:
                    value = r.get(key)
                    ttl = r.ttl(key)
                    print(f"     - {key}: {value} (TTL: {ttl}s)")
                return True
            else:
                print("   ❌ No Redis keys created - rate limiting using fallback")
                
                # Check fallback storage
                if hasattr(rate_limiting_service.redis_backend, 'fallback_storage'):
                    fallback_count = len(rate_limiting_service.redis_backend.fallback_storage)
                    print(f"   Fallback storage entries: {fallback_count}")
                    
                    if fallback_count > 0:
                        print("   Fallback storage content:")
                        for key, value in list(rate_limiting_service.redis_backend.fallback_storage.items())[:3]:
                            print(f"     - {key}: {value}")
                
                return False
                
        except Exception as e:
            print(f"❌ Direct rate check failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def force_redis_usage_test(self) -> bool:
        """Force Redis usage by making multiple requests"""
        print("\n🔍 Testing forced Redis usage with multiple requests...")
        
        try:
            # Clear Redis first
            r = redis.Redis(host=self.redis_host, port=self.redis_port, db=self.redis_db, decode_responses=True)
            initial_keys = list(r.scan_iter())
            for key in initial_keys:
                r.delete(key)
            print(f"   Cleared {len(initial_keys)} existing Redis keys")
            
            # Import rate limiting service
            from api.security.enhanced_rate_limiting_service import rate_limiting_service
            
            # Make multiple direct calls to the rate limiting service
            print("   Making multiple rate limit checks...")
            for i in range(5):
                result = await rate_limiting_service.check_rate_limit(
                    ip="127.0.0.1",
                    endpoint_path="/health",
                    user_data=None
                )
                print(f"     Check {i+1}: allowed={result.allowed}, remaining={result.remaining}")
                time.sleep(0.1)
            
            # Check what keys were created
            final_keys = list(r.scan_iter())
            print(f"   Total keys in Redis after checks: {len(final_keys)}")
            
            if final_keys:
                print("   Keys created:")
                for key in final_keys:
                    value = r.get(key)
                    ttl = r.ttl(key)
                    print(f"     - {key}: {value} (TTL: {ttl}s)")
                return True
            else:
                print("   ❌ Still no Redis keys created")
                
                # Check Redis backend metrics
                if rate_limiting_service.redis_backend:
                    metrics = rate_limiting_service.redis_backend.get_metrics()
                    print(f"   Redis backend metrics: {metrics}")
                
                return False
                
        except Exception as e:
            print(f"❌ Forced Redis usage test failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def diagnose_configuration_issue(self) -> Dict[str, Any]:
        """Diagnose configuration issues"""
        print("\n🔍 Diagnosing configuration issues...")
        
        diagnosis = {}
        
        try:
            from api.config import settings
            
            # Check Redis configuration
            redis_config = {
                'RATE_LIMIT_ENABLED': getattr(settings, 'RATE_LIMIT_ENABLED', None),
                'RATE_LIMIT_REDIS_URL': getattr(settings, 'RATE_LIMIT_REDIS_URL', None),
                'RATE_LIMIT_FALLBACK_TO_MEMORY': getattr(settings, 'RATE_LIMIT_FALLBACK_TO_MEMORY', None),
            }
            
            print("   Configuration values:")
            for key, value in redis_config.items():
                print(f"     - {key}: {value}")
                diagnosis[key] = value
            
            # Check if fallback is disabled
            if redis_config.get('RATE_LIMIT_FALLBACK_TO_MEMORY') is False:
                print("   ✅ Fallback to memory is DISABLED - Redis should be forced")
            else:
                print("   ⚠️ Fallback to memory is ENABLED - may use memory instead of Redis")
            
            return diagnosis
            
        except Exception as e:
            print(f"❌ Configuration diagnosis failed: {e}")
            return {"error": str(e)}


async def main():
    """Run Redis rate limiting fixes and tests"""
    print("🔴 Redis Rate Limiting Integration Fix")
    print("=" * 50)
    
    fixer = RedisRateLimitingFix()
    
    # Step 1: Verify Redis connection
    redis_ok = fixer.verify_redis_connection()
    if not redis_ok:
        print("\n❌ Redis connection failed - cannot proceed")
        return False
    
    # Step 2: Diagnose configuration
    config = fixer.diagnose_configuration_issue()
    
    # Step 3: Test rate limiting service initialization
    service_ok = await fixer.test_rate_limiting_service_initialization()
    
    # Step 4: Test direct rate limiting check
    direct_ok = await fixer.test_direct_rate_check()
    
    # Step 5: Force Redis usage test
    forced_ok = await fixer.force_redis_usage_test()
    
    # Summary
    print("\n" + "=" * 50)
    print("🧪 FIX SUMMARY")
    print("=" * 50)
    
    tests = [
        ("Redis Connection", redis_ok),
        ("Service Initialization", service_ok),
        ("Direct Rate Check", direct_ok),
        ("Forced Redis Usage", forced_ok)
    ]
    
    passed = 0
    for test_name, result in tests:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("\n✅ Redis rate limiting is working correctly!")
    else:
        print("\n❌ Issues found. Possible solutions:")
        
        if not service_ok:
            print("   1. Rate limiting service Redis initialization failed")
            print("      - Check Redis URL configuration")
            print("      - Verify Redis is running on correct port/database")
        
        if not direct_ok or not forced_ok:
            print("   2. Rate limiting not using Redis")
            print("      - Set RATE_LIMIT_FALLBACK_TO_MEMORY=false")
            print("      - Check Redis backend initialization in service")
            print("      - Verify middleware is calling the service correctly")
    
    return passed == len(tests)


if __name__ == "__main__":
    result = asyncio.run(main())
    if result:
        print("\n🎉 Redis rate limiting integration is working!")
    else:
        print("\n❌ Redis rate limiting integration needs fixing.")
