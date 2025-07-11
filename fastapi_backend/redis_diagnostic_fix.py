#!/usr/bin/env python3
"""
Comprehensive Redis Diagnostic and Fix
Diagnoses and fixes Redis integration issues with FastAPI rate limiting
"""

import os
import sys
import time
import redis
import requests
import asyncio
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def diagnose_redis_backend():
    """Diagnose the Redis backend integration"""
    logger.info("🔍 Diagnosing Redis backend integration...")
    
    try:
        # Import FastAPI components
        sys.path.insert(0, '.')
        from api.security.enhanced_rate_limiting_service import rate_limiting_service
        from api.security.redis_rate_limiting_backend import get_redis_backend
        from api.config import settings
        
        logger.info("✅ Successfully imported FastAPI security components")
        
        # Check settings
        logger.info(f"📋 Settings check:")
        logger.info(f"   RATE_LIMIT_ENABLED: {getattr(settings, 'RATE_LIMIT_ENABLED', 'Not set')}")
        logger.info(f"   RATE_LIMIT_REDIS_URL: {getattr(settings, 'RATE_LIMIT_REDIS_URL', 'Not set')}")
        logger.info(f"   RATE_LIMIT_FALLBACK_TO_MEMORY: {getattr(settings, 'RATE_LIMIT_FALLBACK_TO_MEMORY', 'Not set')}")
        
        # Initialize Redis backend manually
        logger.info("🔄 Manually initializing Redis backend...")
        redis_backend = await get_redis_backend()
        
        if redis_backend:
            logger.info("✅ Redis backend created")
            logger.info(f"   Redis URL: {redis_backend.redis_url}")
            logger.info(f"   Redis available: {redis_backend.redis_available}")
            
            # Test health check
            health = await redis_backend._health_check()
            logger.info(f"   Health check: {health}")
            
        else:
            logger.error("❌ Failed to create Redis backend")
            return False
        
        # Initialize rate limiting service
        logger.info("🔄 Initializing rate limiting service...")
        await rate_limiting_service.initialize_redis()
        
        logger.info(f"   Redis initialized: {rate_limiting_service._redis_initialized}")
        logger.info(f"   Redis backend attached: {rate_limiting_service.redis_backend is not None}")
        
        if rate_limiting_service.redis_backend:
            logger.info(f"   Backend Redis available: {rate_limiting_service.redis_backend.redis_available}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Redis backend diagnosis failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_redis_direct():
    """Test Redis directly with the exact configuration"""
    logger.info("🔍 Testing Redis direct connection...")
    
    try:
        # Test with database 1 (rate limiting database)
        r = redis.Redis(host='localhost', port=6379, db=1, decode_responses=True)
        
        # Test connection
        response = r.ping()
        logger.info(f"✅ Redis ping (db=1): {response}")
        
        # Test incr operation (used by rate limiting)
        test_key = "test_rate_limit_operation"
        
        # Set initial value
        r.set(test_key, 0, ex=60)
        
        # Increment (this is what rate limiting does)
        new_value = r.incr(test_key)
        logger.info(f"✅ Redis incr operation: {new_value}")
        
        # Get TTL
        ttl = r.ttl(test_key)
        logger.info(f"✅ Redis TTL: {ttl}s")
        
        # Clean up
        r.delete(test_key)
        
        # Test pipeline operations
        pipe = r.pipeline()
        pipe.incr('pipeline_test')
        pipe.expire('pipeline_test', 60)
        results = pipe.execute()
        logger.info(f"✅ Redis pipeline: {results}")
        
        # Clean up
        r.delete('pipeline_test')
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Redis direct test failed: {e}")
        return False


async def force_redis_usage():
    """Force the rate limiting system to use Redis"""
    logger.info("🚀 Forcing Redis usage by overwhelming rate limits...")
    
    try:
        # Clear Redis first
        r = redis.Redis(host='localhost', port=6379, db=1, decode_responses=True)
        
        # Clear all rate limiting keys
        for key in r.scan_iter(match="rate_limit*"):
            r.delete(key)
        logger.info("✅ Cleared all existing rate limiting keys")
        
        # Make MANY rapid requests to different endpoints to trigger rate limiting
        base_url = "http://localhost:8000"
        endpoints = [
            "/health",
            "/api/v1/users/agent_1",
            "/",
        ]
        
        logger.info("📈 Making 100 rapid requests to trigger rate limiting...")
        
        for i in range(100):
            try:
                endpoint = endpoints[i % len(endpoints)]
                response = requests.get(f"{base_url}{endpoint}", timeout=1)
                
                # No delay - make requests as fast as possible
                if i % 20 == 0:
                    logger.info(f"   Made {i+1} requests...")
                    
                    # Check for rate limiting keys after every 20 requests
                    keys = list(r.scan_iter(match="rate_limit*"))
                    if keys:
                        logger.info(f"   🎉 Found {len(keys)} rate limiting keys!")
                        for key in keys[:3]:
                            value = r.get(key)
                            ttl = r.ttl(key)
                            logger.info(f"      {key}: {value} (TTL: {ttl}s)")
                        break
                    
            except Exception as e:
                # Ignore individual request failures
                pass
        
        # Final check for rate limiting keys
        final_keys = list(r.scan_iter(match="rate_limit*"))
        
        if final_keys:
            logger.info(f"🎉 SUCCESS: Found {len(final_keys)} rate limiting keys in Redis!")
            return True
        else:
            logger.warning("⚠️ Still no rate limiting keys found after 100 requests")
            return False
            
    except Exception as e:
        logger.error(f"❌ Failed to force Redis usage: {e}")
        return False


def check_fastapi_logs():
    """Check what FastAPI is actually doing with Redis"""
    logger.info("🔍 Checking FastAPI Redis initialization...")
    
    try:
        # Make a request to the health endpoint and check response
        response = requests.get("http://localhost:8000/health", timeout=5)
        
        if response.status_code == 200:
            health_data = response.json()
            logger.info("✅ FastAPI health check response:")
            logger.info(f"   Status: {health_data.get('status')}")
            logger.info(f"   Security: {health_data.get('security', {})}")
            
            # Check if there are any Redis-related endpoints
            try:
                redis_health = requests.get("http://localhost:8000/api/redis/health", timeout=5)
                if redis_health.status_code == 200:
                    logger.info("✅ Redis health endpoint available")
                    logger.info(f"   Redis health: {redis_health.json()}")
                else:
                    logger.warning("⚠️ Redis health endpoint not responding properly")
            except:
                logger.warning("⚠️ Redis health endpoint not available")
                
            return True
        else:
            logger.error(f"❌ FastAPI health check failed: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"❌ FastAPI logs check failed: {e}")
        return False


def create_redis_debug_config():
    """Create a debug configuration to ensure Redis is used"""
    logger.info("⚙️ Creating Redis debug configuration...")
    
    try:
        # Create a super aggressive rate limiting config
        debug_config = """# Redis Debug Configuration - Forces Redis Usage
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REDIS_URL=redis://localhost:6379/1
RATE_LIMIT_FALLBACK_TO_MEMORY=false

# VERY aggressive rate limits to force Redis usage
RATE_LIMIT_AUTH_REQUESTS=2
RATE_LIMIT_TRADING_REQUESTS=3
RATE_LIMIT_INFO_REQUESTS=5
RATE_LIMIT_ADMIN_REQUESTS=1
RATE_LIMIT_REQUESTS_PER_MINUTE=8

# Disable fallback to force Redis usage
RATE_LIMIT_SLIDING_WINDOW=true
RATE_LIMIT_BURST_PROTECTION=false
RATE_LIMIT_ADMIN_BYPASS=false
"""

        # Update .env file
        env_file = Path(".env")
        if env_file.exists():
            content = env_file.read_text()
        else:
            content = ""
        
        # Remove existing rate limiting config
        lines = content.split('\n')
        new_lines = []
        
        skip_keys = [
            'RATE_LIMIT_ENABLED',
            'RATE_LIMIT_REDIS_URL',
            'RATE_LIMIT_FALLBACK_TO_MEMORY',
            'RATE_LIMIT_AUTH_REQUESTS',
            'RATE_LIMIT_TRADING_REQUESTS',
            'RATE_LIMIT_INFO_REQUESTS',
            'RATE_LIMIT_ADMIN_REQUESTS',
            'RATE_LIMIT_REQUESTS_PER_MINUTE',
            'RATE_LIMIT_SLIDING_WINDOW',
            'RATE_LIMIT_BURST_PROTECTION',
            'RATE_LIMIT_ADMIN_BYPASS'
        ]
        
        for line in lines:
            if not any(line.startswith(f"{key}=") for key in skip_keys):
                new_lines.append(line)
        
        # Add debug config
        new_lines.append("")
        new_lines.append("# Redis Debug Configuration")
        new_lines.extend(debug_config.strip().split('\n'))
        
        # Write updated config
        env_file.write_text('\n'.join(new_lines))
        
        logger.info("✅ Redis debug configuration created")
        logger.info("   VERY aggressive rate limits set")
        logger.info("   Fallback to memory DISABLED")
        logger.info("   This should force Redis usage")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to create debug config: {e}")
        return False


async def run_comprehensive_diagnosis():
    """Run all diagnostic tests"""
    logger.info("🔬 Running Comprehensive Redis Diagnosis")
    logger.info("=" * 50)
    
    results = {}
    
    # Test 1: Direct Redis connection
    logger.info("\n1️⃣ Testing direct Redis connection...")
    results['redis_direct'] = test_redis_direct()
    
    # Test 2: FastAPI logs and health
    logger.info("\n2️⃣ Checking FastAPI status...")
    results['fastapi_status'] = check_fastapi_logs()
    
    # Test 3: Redis backend diagnosis
    logger.info("\n3️⃣ Diagnosing Redis backend...")
    results['redis_backend'] = await diagnose_redis_backend()
    
    # Test 4: Force Redis usage
    logger.info("\n4️⃣ Forcing Redis usage...")
    results['force_redis'] = await force_redis_usage()
    
    # Summary
    logger.info("\n" + "=" * 50)
    logger.info("🔬 DIAGNOSIS SUMMARY")
    logger.info("=" * 50)
    
    for test, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"   {test}: {status}")
    
    passed = sum(results.values())
    total = len(results)
    
    logger.info(f"\nOverall: {passed}/{total} tests passed")
    
    if results.get('force_redis', False):
        logger.info("\n🎉 SUCCESS: Redis is working and being used!")
        return True
    else:
        logger.error("\n❌ Redis is not being used by rate limiting")
        logger.info("\n🔧 RECOMMENDED FIXES:")
        logger.info("1. Create debug configuration with aggressive limits")
        logger.info("2. Restart FastAPI application")
        logger.info("3. Test with rapid requests")
        
        return False


def main():
    """Main diagnostic execution"""
    print("🔬 Redis Integration Comprehensive Diagnosis")
    print("=" * 45)
    
    try:
        # Run async diagnosis
        result = asyncio.run(run_comprehensive_diagnosis())
        
        if not result:
            print("\n🔧 Creating debug configuration...")
            if create_redis_debug_config():
                print("\n✅ Debug configuration created!")
                print("\n🚀 NEXT STEPS:")
                print("1. Restart FastAPI: python3 main.py")
                print("2. Test again: python3 redis_validation_test.py")
                print("3. Make rapid requests: for i in {1..20}; do curl http://localhost:8000/health; done")
                print("\nThe aggressive rate limits should now force Redis usage!")
            else:
                print("\n❌ Failed to create debug configuration")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Diagnosis failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
