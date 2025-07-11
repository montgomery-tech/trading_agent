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
