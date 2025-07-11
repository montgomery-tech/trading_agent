#!/usr/bin/env python3
"""
Environment Redis Configuration Fix
Ensures .env is properly configured for Redis usage
"""

import os
import shutil
from datetime import datetime

def backup_env_file():
    """Backup current .env file"""
    if os.path.exists('.env'):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f'.env.backup.{timestamp}'
        shutil.copy('.env', backup_name)
        print(f"✅ Backed up .env to {backup_name}")
        return backup_name
    return None

def create_redis_optimized_env():
    """Create Redis-optimized .env configuration"""
    
    redis_env_content = """# =============================================================================
# Redis-Optimized Environment Configuration (Fixed)
# Updated: {timestamp}
# Task 1.2: Redis Production Setup - Redis Integration Fix
# =============================================================================

# Environment
ENVIRONMENT=development
DEBUG=true

# Security - Development Keys (CHANGE FOR PRODUCTION)
SECRET_KEY=f19fb15492b88dbb703a5affeb215d308debaa49f91e47ce040e5ef8ad9be162
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=30
JWT_REFRESH_EXPIRE_DAYS=7

# Password Requirements
PASSWORD_MIN_LENGTH=8
PASSWORD_REQUIRE_UPPERCASE=true
PASSWORD_REQUIRE_LOWERCASE=true
PASSWORD_REQUIRE_NUMBERS=true
PASSWORD_REQUIRE_SPECIAL=false

# Database Configuration - PostgreSQL
DATABASE_URL=postgresql://garrettroth@localhost:5432/balance_tracker
DATABASE_TYPE=postgresql

# API Configuration
API_V1_PREFIX=/api/v1
PROJECT_NAME=Balance Tracking System - Development
VERSION=1.0.0-dev

# CORS (Permissive for development)
CORS_ORIGINS=http://localhost:3000,http://localhost:8080,http://127.0.0.1:3000
CORS_ALLOW_CREDENTIALS=true

# ===== REDIS CONFIGURATION - FIXED FOR PROPER INTEGRATION =====
# Enable rate limiting
RATE_LIMIT_ENABLED=true

# Redis connection (Database 1 for rate limiting)
RATE_LIMIT_REDIS_URL=redis://localhost:6379/1

# CRITICAL: Disable fallback to force Redis usage
RATE_LIMIT_FALLBACK_TO_MEMORY=false

# Endpoint-Specific Rate Limits (Conservative for testing)
RATE_LIMIT_AUTH_REQUESTS=5
RATE_LIMIT_TRADING_REQUESTS=10
RATE_LIMIT_INFO_REQUESTS=15
RATE_LIMIT_ADMIN_REQUESTS=3
RATE_LIMIT_REQUESTS_PER_MINUTE=20

# Advanced Rate Limiting Features
RATE_LIMIT_SLIDING_WINDOW=true
RATE_LIMIT_BURST_PROTECTION=true
RATE_LIMIT_ADMIN_BYPASS=false

# Redis Connection Settings
REDIS_POOL_SIZE=10
REDIS_TIMEOUT=5.0
REDIS_HEALTH_CHECK_INTERVAL=30

# Email Configuration (Development - Disabled)
EMAIL_ENABLED=false
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=us-east-1
SES_FROM_EMAIL=dev@localhost
SES_FROM_NAME=Trading System Dev

# Security Headers (Relaxed for development)
SECURITY_HEADERS_ENABLED=true
HTTPS_ONLY=false
HSTS_MAX_AGE=3600

# Logging
LOG_LEVEL=DEBUG
LOG_FORMAT=detailed
LOG_FILE_ENABLED=false
LOG_FILE_PATH=logs/app.log

# Monitoring
HEALTH_CHECK_ENABLED=true
METRICS_ENABLED=true

# Security Configuration
MAX_REQUEST_SIZE=10485760
REQUEST_TIMEOUT=30
""".format(timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    
    with open('.env', 'w') as f:
        f.write(redis_env_content)
    
    print("✅ Created Redis-optimized .env configuration")
    print("\n📋 Key Redis Settings:")
    print("   • RATE_LIMIT_ENABLED=true")
    print("   • RATE_LIMIT_REDIS_URL=redis://localhost:6379/1")
    print("   • RATE_LIMIT_FALLBACK_TO_MEMORY=false (CRITICAL)")
    print("   • Conservative rate limits for testing")

def validate_redis_config():
    """Validate the Redis configuration"""
    print("\n🔍 Validating Redis configuration...")
    
    required_settings = {
        'RATE_LIMIT_ENABLED': 'true',
        'RATE_LIMIT_REDIS_URL': 'redis://localhost:6379/1',
        'RATE_LIMIT_FALLBACK_TO_MEMORY': 'false'
    }
    
    if not os.path.exists('.env'):
        print("❌ .env file not found")
        return False
    
    with open('.env', 'r') as f:
        env_content = f.read()
    
    all_good = True
    for setting, expected_value in required_settings.items():
        if f"{setting}={expected_value}" in env_content:
            print(f"   ✅ {setting}={expected_value}")
        else:
            print(f"   ❌ {setting} not set to {expected_value}")
            all_good = False
    
    return all_good

def main():
    """Main fix function"""
    print("🔧 Redis Configuration Fix")
    print("=" * 40)
    
    # Step 1: Backup current .env
    backup_name = backup_env_file()
    
    # Step 2: Create Redis-optimized configuration
    create_redis_optimized_env()
    
    # Step 3: Validate configuration
    config_valid = validate_redis_config()
    
    if config_valid:
        print("\n✅ Redis configuration fix completed successfully!")
        print("\n🚀 Next Steps:")
        print("   1. Restart FastAPI application:")
        print("      python3 main.py")
        print("   2. Run the fixed validation test:")
        print("      python3 redis_rate_limiting_fix.py")
        print("   3. Monitor Redis keys:")
        print("      redis-cli -n 1 MONITOR")
    else:
        print("\n❌ Configuration validation failed")
        if backup_name:
            print(f"   Restore backup: mv {backup_name} .env")
    
    return config_valid

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
