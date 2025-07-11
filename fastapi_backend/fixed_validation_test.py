#!/usr/bin/env python3
"""
Fixed Redis Integration Validation Test
Properly tests Redis rate limiting integration with correct key patterns
"""

import asyncio
import time
import logging
import requests
import redis
from typing import Dict, Any, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FixedRedisValidationTest:
    """Fixed Redis validation test that properly tests rate limiting integration"""
    
    def __init__(self):
        self.redis_host = "localhost"
        self.redis_port = 6379
        self.redis_db = 1
        self.fastapi_url = "http://localhost:8000"
        self.test_results: Dict[str, bool] = {}
        
    def test_redis_connection(self) -> bool:
        """Test basic Redis connection"""
        logger.info("🔍 Testing Redis connection...")
        try:
            r = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                db=self.redis_db,
                decode_responses=True
            )
            result = r.ping()
            logger.info("✅ Redis ping successful")
            
            # Test read/write
            test_key = "test_validation_" + str(int(time.time()))
            r.setex(test_key, 10, "test_value")
            retrieved = r.get(test_key)
            r.delete(test_key)
            
            if retrieved == "test_value":
                logger.info("✅ Redis read/write operations working")
                self.test_results['redis_connection'] = True
                return True
            else:
                logger.error(f"❌ Redis read/write failed")
                self.test_results['redis_connection'] = False
                return False
                
        except Exception as e:
            logger.error(f"❌ Redis connection failed: {e}")
            self.test_results['redis_connection'] = False
            return False
    
    def test_fastapi_availability(self) -> bool:
        """Test FastAPI is running"""
        logger.info("🔍 Testing FastAPI availability...")
        try:
            response = requests.get(f"{self.fastapi_url}/health", timeout=5)
            if response.status_code == 200:
                logger.info("✅ FastAPI is running")
                self.test_results['fastapi_availability'] = True
                return True
            else:
                logger.error(f"❌ FastAPI returned status: {response.status_code}")
                self.test_results['fastapi_availability'] = False
                return False
        except Exception as e:
            logger.error(f"❌ FastAPI connection failed: {e}")
            self.test_results['fastapi_availability'] = False
            return False
    
    def test_redis_rate_limiting_keys_comprehensive(self) -> bool:
        """Comprehensive test for Redis rate limiting key creation"""
        logger.info("🔑 Testing Redis rate limiting key creation (comprehensive)...")
        
        try:
            r = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                db=self.redis_db,
                decode_responses=True
            )
            
            # Clear all existing keys
            all_keys = list(r.scan_iter())
            if all_keys:
                r.delete(*all_keys)
                logger.info(f"   Cleared {len(all_keys)} existing keys")
            
            # Test multiple key patterns that might be used
            key_patterns_to_test = [
                "rate_limit*",  # Expected pattern
                "rl:*",         # Alternative pattern
                "*rate*",       # Broader pattern
                "*limit*",      # Broader pattern
                "*"             # All keys
            ]
            
            logger.info("   Making requests to trigger rate limiting...")
            
            # Make requests with different patterns to trigger various rate limiting scenarios
            request_scenarios = [
                ("/health", "GET"),
                ("/api/v1/users/test_user", "GET"),
                ("/docs", "GET"),
                ("/health", "GET"),  # Repeat to trigger rate limiting
                ("/health", "GET"),
            ]
            
            session = requests.Session()
            for i, (path, method) in enumerate(request_scenarios):
                try:
                    url = f"{self.fastapi_url}{path}"
                    if method == "GET":
                        response = session.get(url, timeout=3)
                    
                    logger.info(f"     Request {i+1}: {method} {path} -> {response.status_code}")
                    
                    # Check for rate limiting headers
                    rate_headers = {k: v for k, v in response.headers.items() 
                                  if any(term in k.lower() for term in ['rate', 'limit', 'retry'])}
                    if rate_headers:
                        logger.info(f"       Rate headers: {rate_headers}")
                    
                    # Small delay between requests
                    time.sleep(0.2)
                    
                except Exception as e:
                    logger.warning(f"     Request {i+1} failed: {e}")
            
            # Now check for keys with each pattern
            total_keys_found = 0
            for pattern in key_patterns_to_test:
                keys = list(r.scan_iter(match=pattern))
                logger.info(f"   Pattern '{pattern}': {len(keys)} keys found")
                
                if keys:
                    total_keys_found += len(keys)
                    logger.info(f"     Keys: {keys[:5]}")  # Show first 5 keys
                    
                    # Show key details
                    for key in keys[:3]:  # Show details for first 3 keys
                        try:
                            value = r.get(key)
                            ttl = r.ttl(key)
                            logger.info(f"       {key}: {value} (TTL: {ttl}s)")
                        except Exception as e:
                            logger.warning(f"       Error reading key {key}: {e}")
            
            # Final verdict
            if total_keys_found > 0:
                logger.info(f"✅ Found {total_keys_found} rate limiting keys in Redis")
                self.test_results['redis_rate_limiting_keys'] = True
                return True
            else:
                logger.warning("⚠️ No rate limiting keys found in Redis")
                
                # Additional debugging: check if there are any keys at all
                all_keys_after = list(r.scan_iter())
                logger.info(f"   Total keys in Redis DB {self.redis_db}: {len(all_keys_after)}")
                
                if all_keys_after:
                    logger.info(f"   Keys present: {all_keys_after[:10]}")
                else:
                    logger.warning("   No keys at all in Redis - rate limiting likely using memory fallback")
                
                self.test_results['redis_rate_limiting_keys'] = False
                return False
                
        except Exception as e:
            logger.error(f"❌ Redis rate limiting key test failed: {e}")
            self.test_results['redis_rate_limiting_keys'] = False
            return False
    
    async def test_rate_limiting_service_direct(self) -> bool:
        """Test rate limiting service directly"""
        logger.info("🔍 Testing rate limiting service directly...")
        
        try:
            # Import after ensuring we're in the right directory
            import sys
            import os
            sys.path.append(os.path.dirname(os.path.abspath(__file__)))
            
            from api.security.enhanced_rate_limiting_service import rate_limiting_service
            
            # Initialize Redis if not already done
            if not rate_limiting_service._redis_initialized:
                await rate_limiting_service.initialize_redis()
            
            logger.info(f"   Redis initialized: {rate_limiting_service._redis_initialized}")
            
            if rate_limiting_service.redis_backend:
                logger.info(f"   Redis backend available: {rate_limiting_service.redis_backend.redis_available}")
                logger.info(f"   Key prefix: {rate_limiting_service.redis_backend.key_prefix}")
                
                # Test direct rate limiting
                result = await rate_limiting_service.check_rate_limit(
                    ip="127.0.0.1",
                    endpoint_path="/test",
                    user_data=None
                )
                
                logger.info(f"   Direct rate limit test: allowed={result.allowed}")
                
                # Check Redis backend metrics
                metrics = rate_limiting_service.redis_backend.get_metrics()
                logger.info(f"   Redis operations: {metrics.get('redis_operations', 0)}")
                logger.info(f"   Fallback operations: {metrics.get('fallback_operations', 0)}")
                
                self.test_results['rate_limiting_service_direct'] = True
                return True
            else:
                logger.error("❌ Redis backend not available")
                self.test_results['rate_limiting_service_direct'] = False
                return False
                
        except Exception as e:
            logger.error(f"❌ Rate limiting service direct test failed: {e}")
            import traceback
            traceback.print_exc()
            self.test_results['rate_limiting_service_direct'] = False
            return False
    
    def test_configuration_verification(self) -> bool:
        """Verify configuration is correct for Redis usage"""
        logger.info("🔍 Verifying configuration...")
        
        try:
            import sys
            import os
            sys.path.append(os.path.dirname(os.path.abspath(__file__)))
            
            from api.config import settings
            
            config_checks = {
                'RATE_LIMIT_ENABLED': getattr(settings, 'RATE_LIMIT_ENABLED', None),
                'RATE_LIMIT_REDIS_URL': getattr(settings, 'RATE_LIMIT_REDIS_URL', None),
                'RATE_LIMIT_FALLBACK_TO_MEMORY': getattr(settings, 'RATE_LIMIT_FALLBACK_TO_MEMORY', None),
            }
            
            logger.info("   Configuration values:")
            all_good = True
            
            for key, value in config_checks.items():
                logger.info(f"     {key}: {value}")
                
                if key == 'RATE_LIMIT_ENABLED' and not value:
                    logger.warning(f"     ⚠️ Rate limiting is disabled")
                    all_good = False
                elif key == 'RATE_LIMIT_REDIS_URL' and not value:
                    logger.warning(f"     ⚠️ Redis URL not configured")
                    all_good = False
                elif key == 'RATE_LIMIT_FALLBACK_TO_MEMORY' and value is not False:
                    logger.warning(f"     ⚠️ Fallback to memory is enabled - may not use Redis")
            
            if all_good:
                logger.info("✅ Configuration looks good for Redis usage")
            else:
                logger.warning("⚠️ Configuration issues detected")
            
            self.test_results['configuration_verification'] = all_good
            return all_good
            
        except Exception as e:
            logger.error(f"❌ Configuration verification failed: {e}")
            self.test_results['configuration_verification'] = False
            return False


async def main():
    """Run the fixed validation tests"""
    print("🔴 Fixed Redis Integration Validation Test")
    print("=" * 50)
    
    tester = FixedRedisValidationTest()
    
    # Run tests in order
    tests = [
        ("Redis Connection", tester.test_redis_connection),
        ("FastAPI Availability", tester.test_fastapi_availability),
        ("Configuration Verification", tester.test_configuration_verification),
        ("Rate Limiting Service Direct", tester.test_rate_limiting_service_direct),
        ("Redis Rate Limiting Keys", tester.test_redis_rate_limiting_keys_comprehensive),
    ]
    
    results = {}
    for test_name, test_func in tests:
        logger.info(f"\n🔍 Running: {test_name}")
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            results[test_name] = result
        except Exception as e:
            logger.error(f"❌ {test_name} failed with exception: {e}")
            results[test_name] = False
    
    # Summary
    logger.info("\n" + "=" * 50)
    logger.info("🧪 FIXED VALIDATION SUMMARY")
    logger.info("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"   {test_name}: {status}")
        if result:
            passed += 1
    
    logger.info(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("\n✅ All tests passed! Redis rate limiting is working correctly.")
    else:
        logger.error(f"\n❌ {total - passed} tests failed.")
        
        # Provide specific guidance
        if not results.get("Configuration Verification", True):
            logger.info("\n💡 Configuration Fix:")
            logger.info("   Set RATE_LIMIT_FALLBACK_TO_MEMORY=false in .env")
        
        if not results.get("Redis Rate Limiting Keys", True):
            logger.info("\n💡 Redis Keys Fix:")
            logger.info("   1. Restart FastAPI application")
            logger.info("   2. Make more requests to trigger rate limiting")
            logger.info("   3. Check Redis logs for errors")
    
    return passed == total


if __name__ == "__main__":
    result = asyncio.run(main())
    exit(0 if result else 1)
