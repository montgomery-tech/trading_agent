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
