# Redis Native Setup Guide (No Docker)

## Setup Complete ✅

Your Redis native installation is now ready!

### Installation Details
- **Method**: Homebrew native installation
- **Host**: localhost
- **Port**: 6379
- **Database**: 1 (rate limiting)
- **Config File**: /opt/homebrew/etc/redis.conf
- **Data Directory**: /opt/homebrew/var/db/redis
- **Log File**: /opt/homebrew/var/log/redis.log

### Configuration Files Created
- `.env.redis` - Development configuration with Redis
- `redis_monitor.py` - Redis health monitoring script
- `redis_manage.sh` - Redis management commands

### Managing Redis Service

#### Homebrew Service Commands
```bash
# Start Redis
brew services start redis

# Stop Redis
brew services stop redis

# Restart Redis
brew services restart redis

# Check status
brew services list | grep redis
```

#### Using Management Script
```bash
# All-in-one management
./redis_manage.sh start
./redis_manage.sh stop
./redis_manage.sh status
./redis_manage.sh monitor
./redis_manage.sh cli
./redis_manage.sh logs
```

#### Direct Redis Commands
```bash
# Test connection
redis-cli ping

# Connect to rate limiting database
redis-cli -n 1

# Monitor Redis activity
redis-cli MONITOR

# Get Redis information
redis-cli INFO
```

### FastAPI Integration

#### Switch to Redis Configuration
```bash
cp .env.redis .env
python3 main.py
```

#### Test Rate Limiting
```bash
# Test rate limiting endpoints
for i in {1..15}; do curl http://localhost:8000/health; echo; done
```

### Monitoring and Maintenance

#### Health Monitoring
```bash
# Run monitoring script
python3 redis_monitor.py

# Check service status
./redis_manage.sh status

# View real-time logs
./redis_manage.sh logs
```

#### Performance Tuning
Redis is configured with production-optimized settings:
- Memory limit: 256MB with LRU eviction
- Persistence: RDB snapshots + AOF logging
- Connection limit: 10,000 clients
- Slow query logging enabled

### Configuration Files

#### Redis Config Location
- Apple Silicon Mac: `/opt/homebrew/etc/redis.conf`
- Intel Mac: `/usr/local/etc/redis.conf`

#### Key Settings
```
maxmemory 256mb
maxmemory-policy allkeys-lru
appendonly yes
save 900 1 300 10 60 10000
```

### Production Deployment

For production, consider:
- **Managed Redis**: AWS ElastiCache, Google Memorystore, Azure Cache
- **Redis Cluster**: For high availability and scaling
- **Security**: Password authentication, SSL/TLS encryption
- **Monitoring**: CloudWatch, Datadog, or Prometheus integration

#### Example Production URLs
```bash
# AWS ElastiCache
RATE_LIMIT_REDIS_URL=redis://your-cluster.cache.amazonaws.com:6379/1

# Google Memorystore
RATE_LIMIT_REDIS_URL=redis://10.1.2.3:6379/1

# Azure Cache
RATE_LIMIT_REDIS_URL=redis://your-cache.redis.cache.windows.net:6380/1
```

### Troubleshooting

#### Redis Won't Start
```bash
# Check Homebrew services
brew services list | grep redis

# Check for port conflicts
lsof -i :6379

# Check Redis logs
tail -f /opt/homebrew/var/log/redis.log

# Reinstall if needed
brew uninstall redis
brew install redis
```

#### Connection Issues
```bash
# Test basic connectivity
redis-cli ping

# Check if Redis is listening
netstat -an | grep 6379

# Verify configuration
redis-cli CONFIG GET bind
redis-cli CONFIG GET port
```

#### Permission Issues
```bash
# Check data directory permissions
ls -la /opt/homebrew/var/db/redis

# Fix permissions if needed
chmod 755 /opt/homebrew/var/db/redis
chmod 644 /opt/homebrew/var/log/redis.log
```

### Uninstalling

To completely remove Redis:
```bash
# Stop service
brew services stop redis

# Uninstall
brew uninstall redis

# Remove data (optional)
rm -rf /opt/homebrew/var/db/redis
rm -f /opt/homebrew/var/log/redis.log
```

---
Generated on: Thu Jul 10 21:27:38 CDT 2025
Installation: Homebrew native Redis
