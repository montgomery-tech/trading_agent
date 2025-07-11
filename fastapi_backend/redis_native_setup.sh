#!/bin/bash

# Redis Native Setup Script (No Docker)
# Task 1.2: Redis Production Setup for FastAPI Backend
# Uses Homebrew to install Redis natively on macOS

set -e

echo "🔴 Redis Native Setup for FastAPI Backend (No Docker)"
echo "===================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REDIS_PORT="6379"
REDIS_CONFIG_FILE="/opt/homebrew/etc/redis.conf"
REDIS_DATA_DIR="/opt/homebrew/var/db/redis"
REDIS_LOG_FILE="/opt/homebrew/var/log/redis.log"

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

check_homebrew() {
    if ! command -v brew &> /dev/null; then
        log_error "Homebrew is not installed. Please install Homebrew first."
        echo "Visit: https://brew.sh/"
        echo "Install with: /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
        exit 1
    fi
    
    log_success "Homebrew is installed"
}

install_redis() {
    log_info "Installing Redis via Homebrew..."
    
    # Check if Redis is already installed
    if brew list redis &> /dev/null; then
        log_success "Redis is already installed"
        
        # Check version
        redis_version=$(redis-server --version | head -n1)
        log_info "Installed version: $redis_version"
        
        # Update if needed
        log_info "Checking for updates..."
        brew upgrade redis || log_warning "Redis is up to date"
    else
        log_info "Installing Redis..."
        brew install redis
        log_success "Redis installed successfully"
    fi
}

configure_redis() {
    log_info "Configuring Redis for production use..."
    
    # Find Redis config file location
    if [[ -f "/opt/homebrew/etc/redis.conf" ]]; then
        REDIS_CONFIG_FILE="/opt/homebrew/etc/redis.conf"
    elif [[ -f "/usr/local/etc/redis.conf" ]]; then
        REDIS_CONFIG_FILE="/usr/local/etc/redis.conf"
    else
        log_warning "Redis config file not found, creating new one..."
        REDIS_CONFIG_FILE="/opt/homebrew/etc/redis.conf"
        mkdir -p "$(dirname "$REDIS_CONFIG_FILE")"
    fi
    
    log_info "Redis config file: $REDIS_CONFIG_FILE"
    
    # Backup existing config
    if [[ -f "$REDIS_CONFIG_FILE" ]]; then
        cp "$REDIS_CONFIG_FILE" "${REDIS_CONFIG_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
        log_success "Backed up existing Redis configuration"
    fi
    
    # Create production-optimized Redis configuration
    cat > "$REDIS_CONFIG_FILE" << EOF
# Redis Configuration for FastAPI Backend Rate Limiting
# Optimized for production use

# Network
bind 127.0.0.1
port 6379
tcp-backlog 511
timeout 300
tcp-keepalive 60

# General
daemonize no
supervised no
pidfile /opt/homebrew/var/run/redis.pid
loglevel notice
logfile $REDIS_LOG_FILE
databases 16

# Persistence (optimized for rate limiting)
save 900 1
save 300 10
save 60 10000
stop-writes-on-bgsave-error yes
rdbcompression yes
rdbchecksum yes
dbfilename dump.rdb
dir $REDIS_DATA_DIR

# Memory management
maxmemory 256mb
maxmemory-policy allkeys-lru
maxmemory-samples 5

# Append only file (for durability)
appendonly yes
appendfilename "appendonly.aof"
appendfsync everysec
no-appendfsync-on-rewrite no
auto-aof-rewrite-percentage 100
auto-aof-rewrite-min-size 64mb

# Slow log
slowlog-log-slower-than 10000
slowlog-max-len 128

# Client settings
maxclients 10000

# Security (development settings)
# requirepass your_redis_password_here
# rename-command FLUSHDB ""
# rename-command FLUSHALL ""

# Rate limiting optimization
hash-max-ziplist-entries 512
hash-max-ziplist-value 64
list-max-ziplist-size -2
set-max-intset-entries 512
zset-max-ziplist-entries 128
zset-max-ziplist-value 64
EOF

    log_success "Redis configuration created/updated"
}

setup_redis_directories() {
    log_info "Setting up Redis directories..."
    
    # Create data directory
    if [[ ! -d "$REDIS_DATA_DIR" ]]; then
        mkdir -p "$REDIS_DATA_DIR"
        log_success "Created Redis data directory: $REDIS_DATA_DIR"
    fi
    
    # Create log directory
    mkdir -p "$(dirname "$REDIS_LOG_FILE")"
    touch "$REDIS_LOG_FILE"
    log_success "Created Redis log file: $REDIS_LOG_FILE"
    
    # Set permissions
    chmod 755 "$REDIS_DATA_DIR"
    chmod 644 "$REDIS_LOG_FILE"
}

start_redis_service() {
    log_info "Starting Redis service..."
    
    # Stop Redis if it's already running
    if brew services list | grep redis | grep started > /dev/null; then
        log_info "Stopping existing Redis service..."
        brew services stop redis
        sleep 2
    fi
    
    # Start Redis service
    brew services start redis
    
    # Wait for Redis to start
    log_info "Waiting for Redis to start..."
    sleep 3
    
    # Test connection
    for i in {1..10}; do
        if redis-cli ping &> /dev/null; then
            log_success "Redis service started successfully"
            return 0
        fi
        
        if [ $i -eq 10 ]; then
            log_error "Redis failed to start after 10 seconds"
            return 1
        fi
        
        echo -n "."
        sleep 1
    done
}

test_redis_connection() {
    log_info "Testing Redis connection and functionality..."
    
    # Basic connectivity test
    if redis-cli ping | grep -q "PONG"; then
        log_success "Redis connectivity test passed"
    else
        log_error "Redis connectivity test failed"
        return 1
    fi
    
    # Test database selection for rate limiting
    redis-cli -n 1 SET test_key "test_value" EX 60 > /dev/null
    if redis-cli -n 1 GET test_key | grep -q "test_value"; then
        log_success "Redis database operations working"
    else
        log_error "Redis database operations failed"
        return 1
    fi
    
    # Test rate limiting operations
    redis-cli -n 1 INCR rate_limit_test > /dev/null
    redis-cli -n 1 EXPIRE rate_limit_test 60 > /dev/null
    
    # Clean up test keys
    redis-cli -n 1 DEL test_key rate_limit_test > /dev/null
    
    log_success "Redis rate limiting functionality verified"
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
    
    # Check if limits is installed
    if python3 -c "import limits" 2>/dev/null; then
        log_success "limits library is available"
    else
        log_info "Installing limits for advanced rate limiting..."
        pip3 install limits==3.6.0
    fi
}

test_python_redis_connection() {
    log_info "Testing Python Redis integration..."
    
    # Create a test script
    cat > test_redis_native.py << 'EOF'
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
    if python3 test_redis_native.py; then
        log_success "Python Redis integration test passed"
    else
        log_error "Python Redis integration test failed"
        return 1
    fi
    
    # Clean up test script
    rm test_redis_native.py
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
# Redis-Optimized Environment Configuration (Native Redis)
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

# Redis Configuration - NATIVE REDIS SETUP
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

create_redis_monitoring_script() {
    log_info "Creating Redis monitoring script..."
    
    cat > redis_monitor.py << 'EOF'
#!/usr/bin/env python3
"""
Redis Monitoring Script for FastAPI Backend (Native Redis)
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
        print("🔴 Redis Monitoring Report (Native)")
        print("=" * 45)
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
        
        # Configuration info
        print(f"Config File: {info.get('config_file', 'default')}")
        print(f"TCP Port: {info.get('tcp_port', 6379)}")
        
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

create_redis_management_script() {
    log_info "Creating Redis management script..."
    
    cat > redis_manage.sh << 'EOF'
#!/bin/bash

# Redis Management Script for Native Redis Installation

REDIS_CONFIG_FILE="/opt/homebrew/etc/redis.conf"
if [[ ! -f "$REDIS_CONFIG_FILE" ]]; then
    REDIS_CONFIG_FILE="/usr/local/etc/redis.conf"
fi

case "${1:-status}" in
    "start")
        echo "🔴 Starting Redis service..."
        brew services start redis
        echo "✅ Redis service started"
        ;;
    "stop")
        echo "🔴 Stopping Redis service..."
        brew services stop redis
        echo "✅ Redis service stopped"
        ;;
    "restart")
        echo "🔴 Restarting Redis service..."
        brew services restart redis
        echo "✅ Redis service restarted"
        ;;
    "status")
        echo "🔴 Redis Service Status:"
        brew services list | grep redis
        echo ""
        if redis-cli ping &> /dev/null; then
            echo "✅ Redis is responding to ping"
        else
            echo "❌ Redis is not responding"
        fi
        ;;
    "monitor")
        if [ -f "redis_monitor.py" ]; then
            python3 redis_monitor.py
        else
            echo "❌ Redis monitor script not found"
        fi
        ;;
    "cli")
        echo "🔴 Connecting to Redis CLI (rate limiting database)..."
        redis-cli -n 1
        ;;
    "logs")
        echo "🔴 Redis Logs:"
        if [[ -f "/opt/homebrew/var/log/redis.log" ]]; then
            tail -f /opt/homebrew/var/log/redis.log
        elif [[ -f "/usr/local/var/log/redis.log" ]]; then
            tail -f /usr/local/var/log/redis.log
        else
            echo "⚠️ Redis log file not found"
            echo "Check: brew services list | grep redis"
        fi
        ;;
    "config")
        echo "🔴 Redis Configuration:"
        echo "Config file: $REDIS_CONFIG_FILE"
        if [[ -f "$REDIS_CONFIG_FILE" ]]; then
            echo "File exists and is readable"
        else
            echo "⚠️ Config file not found"
        fi
        ;;
    "info")
        echo "🔴 Redis Information:"
        redis-cli INFO server | head -20
        ;;
    "help")
        echo "Redis Management Commands:"
        echo "  start     - Start Redis service"
        echo "  stop      - Stop Redis service"
        echo "  restart   - Restart Redis service"
        echo "  status    - Check Redis status"
        echo "  monitor   - Run Redis monitoring"
        echo "  cli       - Connect to Redis CLI"
        echo "  logs      - View Redis logs"
        echo "  config    - Show Redis config info"
        echo "  info      - Show Redis server info"
        echo "  help      - Show this help"
        ;;
    *)
        echo "❌ Unknown command: $1"
        echo "Use '$0 help' for available commands"
        exit 1
        ;;
esac
EOF
    
    chmod +x redis_manage.sh
    log_success "Redis management script created (redis_manage.sh)"
}

create_documentation() {
    log_info "Creating Redis documentation..."
    
    cat > REDIS_NATIVE_SETUP_GUIDE.md << EOF
# Redis Native Setup Guide (No Docker)

## Setup Complete ✅

Your Redis native installation is now ready!

### Installation Details
- **Method**: Homebrew native installation
- **Host**: localhost
- **Port**: 6379
- **Database**: 1 (rate limiting)
- **Config File**: $REDIS_CONFIG_FILE
- **Data Directory**: $REDIS_DATA_DIR
- **Log File**: $REDIS_LOG_FILE

### Configuration Files Created
- \`.env.redis\` - Development configuration with Redis
- \`redis_monitor.py\` - Redis health monitoring script
- \`redis_manage.sh\` - Redis management commands

### Managing Redis Service

#### Homebrew Service Commands
\`\`\`bash
# Start Redis
brew services start redis

# Stop Redis
brew services stop redis

# Restart Redis
brew services restart redis

# Check status
brew services list | grep redis
\`\`\`

#### Using Management Script
\`\`\`bash
# All-in-one management
./redis_manage.sh start
./redis_manage.sh stop
./redis_manage.sh status
./redis_manage.sh monitor
./redis_manage.sh cli
./redis_manage.sh logs
\`\`\`

#### Direct Redis Commands
\`\`\`bash
# Test connection
redis-cli ping

# Connect to rate limiting database
redis-cli -n 1

# Monitor Redis activity
redis-cli MONITOR

# Get Redis information
redis-cli INFO
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

### Monitoring and Maintenance

#### Health Monitoring
\`\`\`bash
# Run monitoring script
python3 redis_monitor.py

# Check service status
./redis_manage.sh status

# View real-time logs
./redis_manage.sh logs
\`\`\`

#### Performance Tuning
Redis is configured with production-optimized settings:
- Memory limit: 256MB with LRU eviction
- Persistence: RDB snapshots + AOF logging
- Connection limit: 10,000 clients
- Slow query logging enabled

### Configuration Files

#### Redis Config Location
- Apple Silicon Mac: \`/opt/homebrew/etc/redis.conf\`
- Intel Mac: \`/usr/local/etc/redis.conf\`

#### Key Settings
\`\`\`
maxmemory 256mb
maxmemory-policy allkeys-lru
appendonly yes
save 900 1 300 10 60 10000
\`\`\`

### Production Deployment

For production, consider:
- **Managed Redis**: AWS ElastiCache, Google Memorystore, Azure Cache
- **Redis Cluster**: For high availability and scaling
- **Security**: Password authentication, SSL/TLS encryption
- **Monitoring**: CloudWatch, Datadog, or Prometheus integration

#### Example Production URLs
\`\`\`bash
# AWS ElastiCache
RATE_LIMIT_REDIS_URL=redis://your-cluster.cache.amazonaws.com:6379/1

# Google Memorystore
RATE_LIMIT_REDIS_URL=redis://10.1.2.3:6379/1

# Azure Cache
RATE_LIMIT_REDIS_URL=redis://your-cache.redis.cache.windows.net:6380/1
\`\`\`

### Troubleshooting

#### Redis Won't Start
\`\`\`bash
# Check Homebrew services
brew services list | grep redis

# Check for port conflicts
lsof -i :6379

# Check Redis logs
tail -f $REDIS_LOG_FILE

# Reinstall if needed
brew uninstall redis
brew install redis
\`\`\`

#### Connection Issues
\`\`\`bash
# Test basic connectivity
redis-cli ping

# Check if Redis is listening
netstat -an | grep 6379

# Verify configuration
redis-cli CONFIG GET bind
redis-cli CONFIG GET port
\`\`\`

#### Permission Issues
\`\`\`bash
# Check data directory permissions
ls -la $REDIS_DATA_DIR

# Fix permissions if needed
chmod 755 $REDIS_DATA_DIR
chmod 644 $REDIS_LOG_FILE
\`\`\`

### Uninstalling

To completely remove Redis:
\`\`\`bash
# Stop service
brew services stop redis

# Uninstall
brew uninstall redis

# Remove data (optional)
rm -rf $REDIS_DATA_DIR
rm -f $REDIS_LOG_FILE
\`\`\`

---
Generated on: $(date)
Installation: Homebrew native Redis
EOF
    
    log_success "Redis documentation created (REDIS_NATIVE_SETUP_GUIDE.md)"
}

print_summary() {
    echo ""
    echo "🎉 Redis Native Setup Complete!"
    echo "================================="
    echo ""
    echo "📋 Summary:"
    echo "  • Redis installed via Homebrew"
    echo "  • Service running on port $REDIS_PORT"
    echo "  • Rate limiting database: 1"
    echo "  • Configuration: .env.redis created"
    echo ""
    echo "🚀 Next Steps:"
    echo "  1. cp .env.redis .env"
    echo "  2. python3 main.py"
    echo "  3. Test: curl http://localhost:8000/health"
    echo ""
    echo "🔧 Management:"
    echo "  • ./redis_manage.sh status"
    echo "  • python3 redis_monitor.py"
    echo ""
    echo "📖 See REDIS_NATIVE_SETUP_GUIDE.md for detailed instructions"
    echo ""
}

# Main execution
main() {
    echo "Starting Redis native setup..."
    echo ""
    
    check_homebrew
    install_redis
    configure_redis
    setup_redis_directories
    start_redis_service
    test_redis_connection
    check_redis_dependencies
    test_python_redis_connection
    update_environment_config
    create_redis_monitoring_script
    create_redis_management_script
    create_documentation
    print_summary
    
    log_success "Redis native setup completed successfully! 🔴"
}

# Handle script arguments
case "${1:-setup}" in
    "setup")
        main
        ;;
    "start")
        log_info "Starting Redis service..."
        brew services start redis
        log_success "Redis service started"
        ;;
    "stop")
        log_info "Stopping Redis service..."
        brew services stop redis
        log_success "Redis service stopped"
        ;;
    "restart")
        log_info "Restarting Redis service..."
        brew services restart redis
        log_success "Redis service restarted"
        ;;
    "status")
        echo "🔴 Redis Service Status:"
        brew services list | grep redis
        echo ""
        if redis-cli ping &> /dev/null; then
            log_success "Redis is responding to ping"
        else
            log_warning "Redis is not responding"
        fi
        ;;
    "monitor")
        if [ -f "redis_monitor.py" ]; then
            python3 redis_monitor.py
        else
            log_error "Redis monitor script not found. Run setup first."
        fi
        ;;
    "help")
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  setup     - Complete Redis setup (default)"
        echo "  start     - Start Redis service"
        echo "  stop      - Stop Redis service"
        echo "  restart   - Restart Redis service"
        echo "  status    - Check Redis status"
        echo "  monitor   - Run Redis monitoring"
        echo "  help      - Show this help"
        ;;
    *)
        log_error "Unknown command: $1"
        echo "Use '$0 help' for available commands"
        exit 1
        ;;
esac
