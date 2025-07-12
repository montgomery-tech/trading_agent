#!/bin/bash

# =============================================================================
# Redis Cleanup Script
# Clears rate limiting counters to reset limits
# =============================================================================

echo "🧹 Clearing Redis Rate Limiting Counters"
echo "========================================"

# Try to clear database 1 (rate limiting)
if redis-cli -n 1 ping > /dev/null 2>&1; then
    echo "✅ Redis is running"
    
    # Show current keys
    key_count=$(redis-cli -n 1 DBSIZE | grep -o '[0-9]*')
    echo "📊 Current keys in database 1: $key_count"
    
    if [ "$key_count" -gt 0 ]; then
        echo "🗑️  Clearing rate limiting database..."
        redis-cli -n 1 FLUSHDB
        echo "✅ Rate limiting counters cleared"
    else
        echo "✅ No rate limiting counters to clear"
    fi
    
    # Verify cleanup
    new_count=$(redis-cli -n 1 DBSIZE | grep -o '[0-9]*')
    echo "📊 Keys after cleanup: $new_count"
    
else
    echo "⚠️  Redis is not running or not accessible"
    echo "   Rate limiting will fall back to memory"
fi

echo ""
echo "🚀 Ready to test! Rate limits have been reset."
