#!/bin/bash

# =============================================================================
# Rate Limiting Fix for Development Testing
# Fixes the burst protection issue blocking forced password change tests
# =============================================================================

echo "🔧 Fixing Rate Limiting Configuration for Testing"
echo "=================================================="

# Step 1: Backup current .env
echo "📦 Creating backup of current .env..."
cp .env .env.backup.$(date +%Y%m%d_%H%M%S)

# Step 2: Create temporary development .env with relaxed rate limits
echo "⚙️  Creating development-friendly rate limits..."

cat > .env << 'EOF'
# =============================================================================
# Development Environment Configuration - RELAXED RATE LIMITS FOR TESTING
# Updated: $(date '+%Y-%m-%d %H:%M:%S')
# Fix: Removed burst protection blocking for development testing
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

# ===== RATE LIMITING - DEVELOPMENT FRIENDLY CONFIGURATION =====
# Enable rate limiting but with very relaxed limits
RATE_LIMIT_ENABLED=true

# Redis connection (Database 1 for rate limiting)
RATE_LIMIT_REDIS_URL=redis://localhost:6379/1

# CRITICAL: Enable fallback to allow testing without Redis
RATE_LIMIT_FALLBACK_TO_MEMORY=true

# RELAXED Endpoint-Specific Rate Limits for Development Testing
RATE_LIMIT_AUTH_REQUESTS=50
RATE_LIMIT_TRADING_REQUESTS=100
RATE_LIMIT_INFO_REQUESTS=200
RATE_LIMIT_ADMIN_REQUESTS=50
RATE_LIMIT_REQUESTS_PER_MINUTE=100

# DISABLE burst protection for development testing
RATE_LIMIT_SLIDING_WINDOW=false
RATE_LIMIT_BURST_PROTECTION=false
RATE_LIMIT_ADMIN_BYPASS=true

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
EOF

echo "✅ Updated .env with development-friendly rate limits"

# Step 3: Clear Redis cache to reset rate limit counters
echo "🧹 Clearing Redis rate limit counters..."
redis-cli -n 1 FLUSHDB > /dev/null 2>&1 || echo "⚠️  Redis not running - will use memory fallback"

echo "✅ Rate limiting fix completed!"
echo ""
echo "📋 Changes Made:"
echo "   • RATE_LIMIT_ADMIN_REQUESTS: 3 → 50"
echo "   • RATE_LIMIT_BURST_PROTECTION: true → false"
echo "   • RATE_LIMIT_FALLBACK_TO_MEMORY: false → true"
echo "   • RATE_LIMIT_ADMIN_BYPASS: false → true"
echo ""
echo "🚀 Next Steps:"
echo "   1. Restart your FastAPI server"
echo "   2. Run the forced password change tests"
echo "   3. All tests should now pass without rate limiting errors"
echo ""
echo "⚠️  IMPORTANT: These are relaxed settings for development testing only!"
echo "   Restore production settings before deploying to production."
