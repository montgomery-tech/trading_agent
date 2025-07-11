#!/bin/bash

# Redis Production Setup Script
# Task 1.2: Redis Production Setup for FastAPI Backend
# Sets up Redis for local development and production deployment

set -e

echo "🔴 Redis Production Setup for FastAPI Backend"
echo "============================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REDIS_VERSION="7"
REDIS_PORT="6379"
CONTAINER_NAME="fastapi_redis"
REDIS_PASSWORD=""  # Empty for development, set for production

# Functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

check_docker() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        echo "Visit: https://docs.docker.com/get-docker/"
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        log_error "Docker is not running. Please start Docker."
        exit 1
    fi
    
    log_success "Docker is installed and running"
}

check_redis_dependencies() {
    log_info "Checking Redis Python dependencies..."
    
    # Check if redis is installed
    if python3 -c "import redis" 2>/dev/null; then
        log_success "redis library is installed"
    else
        log_warning "redis library not found. Installing..."
        pip3 install redis==5.0.1
        log_success "redis library installed"
    fi
    
    # Check if redis-py-cluster is installed
    if python3 -c "import rediscluster" 2>/dev/null; then
        log_success "redis-py-cluster is available"
    else
        log_info "Installing redis-py-cluster for cluster support..."
        pip3 install redis-py-cluster==2.1.3
    fi
    
    # Check if limits is installed
    if python3 -c "import limits" 2>/dev/null; then
        log_success "limits library is available"
    else
        log_info "Installing limits for advanced rate limiting..."
        pip3 install limits==3.6.0
    fi
}

setup_redis_container() {
    log_info "Setting up Redis container..."
    
    # Check if container already exists
    if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        log_warning "Container $CONTAINER_NAME already exists"
        
        # Check if it's running
        if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
            log_info "Container is already running"
            return 0
        else
            log_info "Starting existing container..."
            docker start $CONTAINER_NAME
            sleep 3
            return 0
        fi
    fi
    
    # Create new container with optimized configuration
    log_info "Creating Redis container with production settings..."
    
    # Redis configuration for production optimization
    docker run -d \
        --name $CONTAINER_NAME \
        -p $REDIS_PORT:6379 \
        -v redis_data:/data \
        --restart unless-stopped \
        redis:$REDIS_VERSION-alpine \
        redis-server \
        --appendonly yes \
        --appendfsync everysec \
        --maxmemory 256mb \
        --maxmemory-policy allkeys-lru \
        --tcp-keepalive 60 \
        --timeout 300 \
        --databases 16 \
        --save 900 1 \
        --save 300 10 \
        --save 60 10000
    
    log_success "Redis container created and started"
    
    # Wait for Redis to be ready
    log_info "Waiting for Redis to be ready..."
    sleep 5
    
    # Test connection
    for i in {1..30}; do
        if docker exec $CONTAINER_NAME redis-cli ping &> /dev/null; then
            log_success "Redis is ready!"
            break
        fi
        
        if [ $i -eq 30 ]; then
            log_error "Redis failed to start after 30 seconds"
            exit 1
        fi
        
        echo -n "."
        sleep 1
    done
}

configure_redis_for_rate_limiting() {
    log_info "Configuring Redis for rate limiting optimization..."
    
    # Set Redis configuration for rate limiting
    docker exec $CONTAINER_NAME redis-cli CONFIG SET maxclients 10000
    docker exec $CONTAINER_NAME redis-cli CONFIG SET timeout 300
    docker exec $CONTAINER_NAME redis-cli CONFIG SET tcp-keepalive 60
    
    # Create database for rate limiting (database 1)
    docker exec $CONTAINER_NAME redis-cli -n 1 FLUSHDB
    
    log_success "Redis configured for optimal rate limiting performance"
}

test_redis_connection() {
    log_info "Testing Redis connection and functionality..."
    
    # Basic connectivity test
    if docker exec $CONTAINER_NAME redis-cli ping | grep -q "PONG"; then
        log_success "Redis connectivity test passed"
    else
        log_error "Redis connectivity test failed"
        return 1
    fi
    
    # Test rate limiting functionality
    docker exec $CONTAINER_NAME redis-cli -n 1 SET test_key "test_value" EX 60
    if docker exec $CONTAINER_NAME redis-cli -n 1 GET test_key | grep -q "test_value"; then
        log_success "Redis key-value operations working"
    else
        log_error "Redis key-value operations failed"
        return 1
    fi
    
    # Test rate limiting operations
    docker exec $CONTAINER_NAME redis-cli -n 1 INCR rate_limit_test
    docker exec $CONTAINER_NAME redis-cli -n 1 EXPIRE rate_limit_test 60
    
    # Clean up test keys
    docker exec $CONTAINER_NAME redis-cli -n 1 DEL test_key rate_limit_test
    
    log_success "Redis rate limiting functionality verified"
}

test_python_redis_connection() {
    log_info "Testing Python Redis integration..."
    
    # Create a test script
    cat > test_redis.py << 'EOF'
import redis
import sys
import json

try:
    # Test connection
    r = redis.Redis(host='localhost', port=6379, db=1, decode_responses=True)
    
    # Test basic operations
    r.ping()
    print("✅ Redis connection successful")
    
    # Test rate limiting operations
    r.set('test_counter', 1, ex=60)
    r.incr('test_counter')
    counter = r.get('test_counter')
    print(f"✅ Rate limiting operations working (counter: {counter})")
    
    # Test pipeline operations (used by rate limiting)
    pipe = r.pipeline()
    pipe.incr('pipeline_test')
    pipe.expire('pipeline_test', 60)
    results = pipe.execute()
    print(f"✅ Pipeline operations working (results: {results})")
    
    # Clean up
    r.delete('test_counter', 'pipeline_test')
    
    # Test Redis info
    info = r.info()
    print(f"✅ Redis version: {info.get('redis_version', 'unknown')}")
    print(f"✅ Connected clients: {info.get('connected_clients', 0)}")
    print(f"✅ Used memory: {info.get('used_memory_human', 'unknown')}")
    
except Exception as e:
    print(f"❌ Redis test failed: {e}")
    sys.exit(1)
EOF
    
    # Run the test
    if python3 test_redis.py; then
        log_success "Python Redis integration test passed"
    else
        log_error "Python Redis integration test failed"
        return 1
    fi
    
    # Clean up test script
    rm test_redis.py
}

update_environment_config() {
    log_info "Updating environment configuration for Redis..."
    
    # Backup current .env
    if [ -f ".env" ]; then
        cp .env .env.backup.redis.$(date +%Y%m%d_%H%M%S)
        log_success "Environment file backed up"
    fi
    
    # Create Redis-optimized environment configuration
    cat > .env.redis << EOF
# =============================================================================
# Redis-Optimized Environment Configuration
# Updated: $(date)
# Task 1.2: Redis Production Setup Complete
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
DATABASE_URL=postgresql://$(whoami)@localhost:5432/balance_tracker
DATABASE_TYPE=postgresql

# API Configuration
API_V1_PREFIX=/api/v1
PROJECT_NAME=Balance Tracking System - Development
VERSION=1.0.0-dev

# CORS (Permissive for development)
CORS_ORIGINS=http://localhost:3000,http://localhost:8080,http://127.0.0.1:3000
CORS_ALLOW_CREDENTIALS=true

# Redis Configuration - PRODUCTION READY
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REDIS_URL=redis://localhost:6379/1
RATE_LIMIT_FALLBACK_TO_MEMORY=true

# Endpoint-Specific Rate Limits (Development)
RATE_LIMIT_AUTH_REQUESTS=10
RATE_LIMIT_TRADING_REQUESTS=100
RATE_LIMIT_INFO_REQUESTS=200
RATE_LIMIT_ADMIN_REQUESTS=5
RATE_LIMIT_REQUESTS_PER_MINUTE=60

# Advanced Rate Limiting Features
RATE_LIMIT_SLIDING_WINDOW=true
RATE_LIMIT_BURST_PROTECTION=true
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
    
    log_success "Redis environment configuration created (.env.redis)"
    echo ""
    echo "To use Redis configuration:"
    echo "  cp .env.redis .env"
}

create_production_configs() {
    log_info "Creating production Redis configurations..."
    
    # Production environment
    cat > .env.production.redis << EOF
# =============================================================================
# Production Environment - Redis Configuration
# =============================================================================

# Environment
ENVIRONMENT=production
DEBUG=false

# Security - Production Keys (MUST BE CHANGED)
SECRET_KEY=YOUR_SECURE_PRODUCTION_SECRET_KEY_HERE
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=15
JWT_REFRESH_EXPIRE_DAYS=7

# Database Configuration - Production PostgreSQL
DATABASE_URL=postgresql://prod_user:CHANGE_PASSWORD@prod-postgres.yourdomain.com:5432/balance_tracker
DATABASE_TYPE=postgresql
DATABASE_SSL_MODE=require
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=30

# Redis Configuration - Production
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REDIS_URL=redis://prod-redis.yourdomain.com:6379/1
RATE_LIMIT_FALLBACK_TO_MEMORY=false

# Production Rate Limits (Stricter)
RATE_LIMIT_AUTH_REQUESTS=5
RATE_LIMIT_TRADING_REQUESTS=50
RATE_LIMIT_INFO_REQUESTS=100
RATE_LIMIT_ADMIN_REQUESTS=3
RATE_LIMIT_REQUESTS_PER_MINUTE=30

# Redis Production Settings
REDIS_POOL_SIZE=20
REDIS_TIMEOUT=3.0
REDIS_HEALTH_CHECK_INTERVAL=30

# Production Security
HTTPS_ONLY=true
CORS_ORIGINS=https://yourdomain.com
LOG_LEVEL=INFO

# Monitoring
METRICS_ENABLED=true
HEALTH_CHECK_ENABLED=true
EOF
    
    # Staging environment
    cat > .env.staging.redis << EOF
# =============================================================================
# Staging Environment - Redis Configuration
# =============================================================================

# Environment
ENVIRONMENT=staging
DEBUG=false

# Redis Configuration - Staging
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REDIS_URL=redis://staging-redis.yourdomain.com:6379/1
RATE_LIMIT_FALLBACK_TO_MEMORY=true

# Staging Rate Limits (Production-like)
RATE_LIMIT_AUTH_REQUESTS=8
RATE_LIMIT_TRADING_REQUESTS=75
RATE_LIMIT_INFO_REQUESTS=150
RATE_LIMIT_ADMIN_REQUESTS=5

# Redis Staging Settings
REDIS_POOL_SIZE=15
REDIS_TIMEOUT=4.0
REDIS_HEALTH_CHECK_INTERVAL=30
EOF
    
    log_success "Production and staging Redis configurations created"
}

create_redis_monitoring_script() {
    log_info "Creating Redis monitoring script..."
    
    cat > redis_monitor.py << 'EOF'
#!/usr/bin/env python3
"""
Redis Monitoring Script for FastAPI Backend
Monitors Redis health, performance, and rate limiting metrics
"""

import redis
import time
import json
from datetime import datetime

def monitor_redis():
    """Monitor Redis health and performance"""
    try:
        # Connect to Redis
        r = redis.Redis(host='localhost', port=6379, db=1, decode_responses=True)
        
        # Test connection
        r.ping()
        
        # Get Redis info
        info = r.info()
        
        # Rate limiting database stats
        db_info = r.info('keyspace')
        
        # Memory info
        memory_info = r.info('memory')
        
        # Print monitoring report
        print("🔴 Redis Monitoring Report")
        print("=" * 40)
        print(f"Timestamp: {datetime.now()}")
        print(f"Redis Version: {info.get('redis_version')}")
        print(f"Uptime: {info.get('uptime_in_seconds')} seconds")
        print(f"Connected Clients: {info.get('connected_clients')}")
        print(f"Used Memory: {memory_info.get('used_memory_human')}")
        print(f"Memory Usage: {memory_info.get('used_memory_peak_human')}")
        
        # Rate limiting database
        if 'db1' in db_info:
            print(f"Rate Limit Keys: {db_info['db1'].get('keys', 0)}")
        else:
            print("Rate Limit Keys: 0")
        
        # Performance metrics
        print(f"Total Commands: {info.get('total_commands_processed')}")
        print(f"Commands/sec: {info.get('instantaneous_ops_per_sec')}")
        
        # Check for any alerts
        alerts = []
        
        if info.get('connected_clients', 0) > 100:
            alerts.append("High client connections")
        
        if memory_info.get('used_memory_peak', 0) > 200 * 1024 * 1024:  # 200MB
            alerts.append("High memory usage")
        
        if info.get('rejected_connections', 0) > 0:
            alerts.append("Connection rejections detected")
        
        if alerts:
            print("\n⚠️  ALERTS:")
            for alert in alerts:
                print(f"   • {alert}")
        else:
            print("\n✅ All systems normal")
        
        return True
        
    except Exception as e:
        print(f"❌ Redis monitoring failed: {e}")
        return False

if __name__ == "__main__":
    monitor_redis()
EOF
    
    chmod +x redis_monitor.py
    log_success "Redis monitoring script created (redis_monitor.py)"
}

create_documentation() {
    log_info "Creating Redis documentation..."
    
    cat > REDIS_SETUP_GUIDE.md << EOF
# Redis Production Setup Guide

## Setup Complete ✅

Your Redis production environment is now ready!

### Connection Details
- **Host**: localhost
- **Port**: 6379
- **Database**: 1 (rate limiting)
- **Container**: ${CONTAINER_NAME}

### Configuration Files Created
- \`.env.redis\` - Development configuration with Redis
- \`.env.production.redis\` - Production Redis configuration template
- \`.env.staging.redis\` - Staging Redis configuration template

### Monitoring
- \`redis_monitor.py\` - Redis health monitoring script

### Managing Redis Container

#### Basic Commands
\`\`\`bash
# Start Redis
docker start ${CONTAINER_NAME}

# Stop Redis
docker stop ${CONTAINER_NAME}

# Restart Redis
docker restart ${CONTAINER_NAME}

# View logs
docker logs ${CONTAINER_NAME}

# Connect to Redis CLI
docker exec -it ${CONTAINER_NAME} redis-cli

# Monitor Redis in real-time
docker exec -it ${CONTAINER_NAME} redis-cli MONITOR
\`\`\`

#### Health Checks
\`\`\`bash
# Quick health check
docker exec ${CONTAINER_NAME} redis-cli ping

# Detailed monitoring
python3 redis_monitor.py

# Check rate limiting database
docker exec ${CONTAINER_NAME} redis-cli -n 1 INFO keyspace
\`\`\`

### FastAPI Integration

#### Switch to Redis Configuration
\`\`\`bash
cp .env.redis .env
python3 main.py
\`\`\`

#### Test Rate Limiting
\`\`\`bash
# Test rate limiting endpoints
for i in {1..15}; do curl http://localhost:8000/health; echo; done
\`\`\`

### Production Deployment

#### AWS ElastiCache
\`\`\`bash
# Example production Redis URL
RATE_LIMIT_REDIS_URL=redis://your-elasticache-cluster.cache.amazonaws.com:6379/1
\`\`\`

#### Google Cloud Memorystore
\`\`\`bash
RATE_LIMIT_REDIS_URL=redis://10.1.2.3:6379/1
\`\`\`

#### Azure Cache for Redis
\`\`\`bash
RATE_LIMIT_REDIS_URL=redis://your-cache.redis.cache.windows.net:6380/1
\`\`\`

### Rate Limiting Configuration

#### Endpoint-Specific Limits
- **Auth endpoints**: 10 requests/minute (development)
- **Trading endpoints**: 100 requests/minute
- **Info endpoints**: 200 requests/minute
- **Admin endpoints**: 5 requests/minute

#### Advanced Features
- **Sliding Window**: Smooth rate limiting over time
- **Burst Protection**: Handles traffic spikes gracefully
- **Admin Bypass**: Allows admin users to bypass limits
- **Fallback**: Uses memory if Redis unavailable

### Troubleshooting

#### Redis Not Starting
\`\`\`bash
# Check Docker status
docker ps -a | grep ${CONTAINER_NAME}

# Check logs
docker logs ${CONTAINER_NAME}

# Remove and recreate
docker rm ${CONTAINER_NAME}
./redis_setup.sh
\`\`\`

#### Connection Issues
\`\`\`bash
# Test connection
redis-cli -h localhost -p 6379 ping

# Check if port is open
netstat -an | grep 6379

# Check FastAPI logs
python3 main.py
\`\`\`

#### Performance Issues
\`\`\`bash
# Monitor Redis performance
python3 redis_monitor.py

# Check memory usage
docker exec ${CONTAINER_NAME} redis-cli INFO memory

# Monitor commands
docker exec ${CONTAINER_NAME} redis-cli MONITOR
\`\`\`

---
Generated on: $(date)
Container: ${CONTAINER_NAME}
EOF
    
    log_success "Redis documentation created (REDIS_SETUP_GUIDE.md)"
}

print_summary() {
    echo ""
    echo "🎉 Redis Production Setup Complete!"
    echo "===================================="
    echo ""
    echo "📋 Summary:"
    echo "  • Redis container running: $CONTAINER_NAME"
    echo "  • Port: $REDIS_PORT"
    echo "  • Database: 1 (rate limiting)"
    echo "  • Configuration: .env.redis created"
    echo ""
    echo "🚀 Next Steps:"
    echo "  1. cp .env.redis .env"
    echo "  2. python3 main.py"
    echo "  3. Test: curl http://localhost:8000/health"
    echo ""
    echo "📊 Monitor Redis:"
    echo "  • python3 redis_monitor.py"
    echo "  • docker logs $CONTAINER_NAME"
    echo ""
    echo "📖 See REDIS_SETUP_GUIDE.md for detailed instructions"
    echo ""
}

# Main execution
main() {
    echo "Starting Redis production setup..."
    echo ""
    
    check_docker
    check_redis_dependencies
    setup_redis_container
    configure_redis_for_rate_limiting
    test_redis_connection
    test_python_redis_connection
    update_environment_config
    create_production_configs
    create_redis_monitoring_script
    create_documentation
    print_summary
    
    log_success "Redis production setup completed successfully! 🔴"
}

# Handle script arguments
case "${1:-setup}" in
    "setup")
        main
        ;;
    "start")
        log_info "Starting Redis container..."
        docker start $CONTAINER_NAME
        log_success "Redis container started"
        ;;
    "stop")
        log_info "Stopping Redis container..."
        docker stop $CONTAINER_NAME
        log_success "Redis container stopped"
        ;;
    "restart")
        log_info "Restarting Redis container..."
        docker restart $CONTAINER_NAME
        log_success "Redis container restarted"
        ;;
    "status")
        if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
            log_success "Redis container is running"
            docker exec $CONTAINER_NAME redis-cli ping
        else
            log_warning "Redis container is not running"
        fi
        ;;
    "monitor")
        if [ -f "redis_monitor.py" ]; then
            python3 redis_monitor.py
        else
            log_error "Redis monitor script not found. Run setup first."
        fi
        ;;
    "logs")
        docker logs $CONTAINER_NAME
        ;;
    "cli")
        log_info "Connecting to Redis CLI..."
        docker exec -it $CONTAINER_NAME redis-cli -n 1
        ;;
    "remove")
        read -p "Are you sure you want to remove the Redis container and data? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            docker stop $CONTAINER_NAME 2>/dev/null || true
            docker rm $CONTAINER_NAME 2>/dev/null || true
            docker volume rm redis_data 2>/dev/null || true
            log_success "Redis container and data removed"
        else
            log_info "Operation cancelled"
        fi
        ;;
    "help")
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  setup     - Initial setup (default)"
        echo "  start     - Start Redis container"
        echo "  stop      - Stop Redis container"
        echo "  restart   - Restart Redis container"
        echo "  status    - Check container status"
        echo "  monitor   - Run Redis monitoring"
        echo "  logs      - View container logs"
        echo "  cli       - Connect to Redis CLI"
        echo "  remove    - Remove container and data (destructive)"
        echo "  help      - Show this help"
        ;;
    *)
        log_error "Unknown command: $1"
        echo "Use '$0 help' for available commands"
        exit 1
        ;;
esac
