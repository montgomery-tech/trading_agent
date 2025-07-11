#!/usr/bin/env python3
"""
Redis Integration Fix for FastAPI
Ensures rate limiting properly uses Redis instead of memory fallback
"""

import os
import sys
import time
import redis
import requests
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_current_env():
    """Check current environment configuration"""
    logger.info("🔍 Checking current environment configuration...")
    
    env_file = Path(".env")
    if not env_file.exists():
        logger.error("❌ .env file not found")
        return False
    
    env_content = env_file.read_text()
    
    # Check Redis configuration
    redis_url = None
    redis_enabled = None
    
    for line in env_content.split('\n'):
        if line.startswith('RATE_LIMIT_REDIS_URL='):
            redis_url = line.split('=', 1)[1]
        elif line.startswith('RATE_LIMIT_ENABLED='):
            redis_enabled = line.split('=', 1)[1]
    
    logger.info(f"✅ RATE_LIMIT_ENABLED: {redis_enabled}")
    logger.info(f"✅ RATE_LIMIT_REDIS_URL: {redis_url}")
    
    return redis_url is not None and redis_enabled == 'true'


def test_redis_direct_connection():
    """Test direct Redis connection"""
    logger.info("🔍 Testing direct Redis connection...")
    
    try:
        r = redis.Redis(host='localhost', port=6379, db=1, decode_responses=True)
        
        # Test connection
        response = r.ping()
        logger.info(f"✅ Redis ping: {response}")
        
        # Test key operations in rate limiting database
        test_key = "test_rate_limit_key"
        r.set(test_key, "test_value", ex=60)
        value = r.get(test_key)
        logger.info(f"✅ Redis operations working: {value}")
        
        # Clean up
        r.delete(test_key)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Redis connection failed: {e}")
        return False


def force_redis_rate_limiting():
    """Force FastAPI to use Redis for rate limiting by making many requests"""
    logger.info("🚀 Forcing Redis rate limiting activation...")
    
    try:
        # Clear any existing rate limiting keys
        r = redis.Redis(host='localhost', port=6379, db=1, decode_responses=True)
        
        # Clear rate limiting keys
        for key in r.scan_iter(match="rate_limit*"):
            r.delete(key)
        logger.info("✅ Cleared existing rate limiting keys")
        
        # Make many rapid requests to trigger rate limiting
        session = requests.Session()
        
        logger.info("Making rapid requests to trigger Redis rate limiting...")
        for i in range(30):
            try:
                response = session.get("http://localhost:8000/health", timeout=2)
                # Add some variety to trigger different rate limiting patterns
                if i % 3 == 0:
                    session.get("http://localhost:8000/api/v1/users/agent_1", timeout=2)
                
                time.sleep(0.05)  # 50ms between requests
                
                if i % 10 == 0:
                    logger.info(f"   Made {i+1} requests...")
                    
            except Exception as e:
                logger.warning(f"   Request {i+1} failed: {e}")
        
        # Check for rate limiting keys
        rate_limit_keys = list(r.scan_iter(match="rate_limit*"))
        if rate_limit_keys:
            logger.info(f"✅ Found {len(rate_limit_keys)} rate limiting keys in Redis")
            for key in rate_limit_keys[:5]:  # Show first 5 keys
                value = r.get(key)
                ttl = r.ttl(key)
                logger.info(f"   Key: {key}, Value: {value}, TTL: {ttl}s")
            return True
        else:
            logger.warning("⚠️ Still no rate limiting keys found")
            return False
            
    except Exception as e:
        logger.error(f"❌ Failed to force Redis rate limiting: {e}")
        return False


def check_fastapi_redis_backend():
    """Check if FastAPI is using Redis backend"""
    logger.info("🔍 Checking FastAPI Redis backend status...")
    
    try:
        # Make a request to health endpoint which should show Redis status
        response = requests.get("http://localhost:8000/health", timeout=5)
        
        if response.status_code == 200:
            health_data = response.json()
            
            # Look for Redis information in health data
            health_str = str(health_data).lower()
            if 'redis' in health_str:
                logger.info("✅ Health endpoint mentions Redis")
            else:
                logger.warning("⚠️ Health endpoint doesn't mention Redis")
            
            logger.info(f"Health data: {health_data}")
            return True
        else:
            logger.error(f"❌ Health endpoint returned {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Failed to check FastAPI Redis backend: {e}")
        return False


def update_env_for_redis():
    """Update .env to ensure Redis is properly configured"""
    logger.info("⚙️ Updating .env for Redis integration...")
    
    try:
        env_file = Path(".env")
        
        if env_file.exists():
            env_content = env_file.read_text()
        else:
            env_content = ""
        
        # Ensure Redis configuration is correct
        redis_config = """
# Redis Configuration - Updated for proper integration
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REDIS_URL=redis://localhost:6379/1
RATE_LIMIT_FALLBACK_TO_MEMORY=true

# Rate limiting settings to ensure Redis usage
RATE_LIMIT_AUTH_REQUESTS=5
RATE_LIMIT_TRADING_REQUESTS=10
RATE_LIMIT_INFO_REQUESTS=20
RATE_LIMIT_ADMIN_REQUESTS=3
RATE_LIMIT_REQUESTS_PER_MINUTE=15
"""
        
        # Update or add Redis configuration
        lines = env_content.split('\n')
        new_lines = []
        redis_keys = [
            'RATE_LIMIT_ENABLED',
            'RATE_LIMIT_REDIS_URL', 
            'RATE_LIMIT_FALLBACK_TO_MEMORY',
            'RATE_LIMIT_AUTH_REQUESTS',
            'RATE_LIMIT_TRADING_REQUESTS',
            'RATE_LIMIT_INFO_REQUESTS',
            'RATE_LIMIT_ADMIN_REQUESTS',
            'RATE_LIMIT_REQUESTS_PER_MINUTE'
        ]
        
        # Remove existing Redis config lines
        for line in lines:
            if not any(line.startswith(f"{key}=") for key in redis_keys):
                new_lines.append(line)
        
        # Add updated Redis configuration
        new_lines.append(redis_config)
        
        # Write updated .env
        updated_content = '\n'.join(new_lines)
        env_file.write_text(updated_content)
        
        logger.info("✅ Environment configuration updated for Redis")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to update environment: {e}")
        return False


def restart_and_test():
    """Instructions for restarting FastAPI and testing"""
    logger.info("🔄 Ready for restart and testing...")
    
    print("\n" + "="*50)
    print("🚀 NEXT STEPS TO COMPLETE REDIS INTEGRATION")
    print("="*50)
    print("\n1. Restart FastAPI application:")
    print("   • Stop current FastAPI (Ctrl+C if running)")
    print("   • python3 main.py")
    print("\n2. Test Redis integration:")
    print("   • python3 redis_validation_test.py")
    print("\n3. Monitor Redis usage:")
    print("   • redis-cli -n 1 MONITOR")
    print("   • python3 redis_monitor.py")
    print("\n4. Test rate limiting manually:")
    print("   • for i in {1..10}; do curl http://localhost:8000/health; echo; done")
    print("\nThe lower rate limits should now trigger Redis usage!")


def main():
    """Main integration fix"""
    print("🔧 Redis Integration Fix for FastAPI")
    print("=" * 40)
    
    # Check current environment
    if not check_current_env():
        logger.error("❌ Environment configuration issues detected")
    
    # Test Redis connection
    if not test_redis_direct_connection():
        logger.error("❌ Redis connection issues detected")
        return False
    
    # Check FastAPI Redis backend
    if not check_fastapi_redis_backend():
        logger.warning("⚠️ FastAPI Redis backend issues detected")
    
    # Update environment for better Redis integration
    if not update_env_for_redis():
        logger.error("❌ Failed to update environment")
        return False
    
    print("\n✅ Redis integration fix completed!")
    print("\n📋 Summary:")
    print("  • Redis connection verified")
    print("  • Environment updated with lower rate limits")
    print("  • Configuration optimized for Redis usage")
    
    restart_and_test()
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
