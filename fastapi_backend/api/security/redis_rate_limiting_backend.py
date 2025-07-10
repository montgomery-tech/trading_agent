#!/usr/bin/env python3
"""
Redis Backend for Enhanced Rate Limiting System
Provides distributed rate limiting capabilities using Redis
Task 1.4.B: Redis Integration for Production
"""

import asyncio
import json
import logging
import time
from typing import Dict, Optional, Any, List
from dataclasses import asdict

try:
    import redis
    # Try newer async version first, fallback to sync version
    try:
        import redis.asyncio as aioredis
        ASYNC_REDIS_AVAILABLE = True
    except ImportError:
        # Fallback to sync Redis with asyncio wrapper
        ASYNC_REDIS_AVAILABLE = False
        aioredis = None
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None
    aioredis = None

from api.config import settings

logger = logging.getLogger(__name__)


class RedisRateLimitingBackend:
    """
    Redis backend for distributed rate limiting.

    Features:
    - Distributed rate limiting across multiple server instances
    - Connection pooling and failover
    - Automatic fallback to in-memory if Redis unavailable
    - Data persistence and cleanup
    - Health monitoring
    """

    def __init__(
        self,
        redis_url: Optional[str] = None,
        pool_size: int = 10,
        timeout: float = 5.0,
        fallback_enabled: bool = True,
        key_prefix: str = "rate_limit"
    ):
        if not REDIS_AVAILABLE:
            logger.warning("Redis not available - fallback mode only")

        self.redis_url = redis_url or getattr(settings, 'RATE_LIMIT_REDIS_URL', 'redis://localhost:6379/0')
        self.pool_size = pool_size
        self.timeout = timeout
        self.fallback_enabled = fallback_enabled
        self.key_prefix = key_prefix

        # Redis connection
        self.redis_client: Optional[redis.Redis] = None

        # Fallback storage (in-memory)
        self.fallback_storage: Dict[str, Dict[str, Any]] = {}

        # Health monitoring
        self.redis_available = False
        self.last_health_check = 0
        self.health_check_interval = 30  # seconds

        # Metrics
        self.metrics = {
            "redis_operations": 0,
            "redis_errors": 0,
            "fallback_operations": 0,
            "connection_failures": 0,
            "health_checks": 0
        }

        logger.info(f"Initialized Redis rate limiting backend: {self.redis_url}")

    async def initialize(self) -> bool:
        """Initialize Redis connection."""
        if not REDIS_AVAILABLE:
            logger.warning("Redis library not available, using fallback only")
            return False

        try:
            # Create Redis client with connection pooling
            if ASYNC_REDIS_AVAILABLE and aioredis:
                # Use async Redis if available
                self.redis_client = aioredis.from_url(
                    self.redis_url,
                    max_connections=self.pool_size,
                    socket_timeout=self.timeout,
                    socket_connect_timeout=self.timeout,
                    decode_responses=True
                )
            else:
                # Use sync Redis with connection pool
                pool = redis.ConnectionPool.from_url(
                    self.redis_url,
                    max_connections=self.pool_size,
                    socket_timeout=self.timeout,
                    socket_connect_timeout=self.timeout,
                    decode_responses=True
                )
                self.redis_client = redis.Redis(connection_pool=pool)

            # Test connection
            await self._health_check()

            if self.redis_available:
                logger.info("✅ Redis connection initialized successfully")
                return True
            else:
                logger.warning("⚠️ Redis connection failed, fallback mode enabled")
                return False

        except Exception as e:
            logger.error(f"❌ Failed to initialize Redis: {e}")
            self.metrics["connection_failures"] += 1
            return False

    async def cleanup(self):
        """Clean up Redis connections."""
        try:
            if self.redis_client:
                if ASYNC_REDIS_AVAILABLE and hasattr(self.redis_client, 'close'):
                    await self.redis_client.close()
                elif hasattr(self.redis_client, 'connection_pool'):
                    self.redis_client.connection_pool.disconnect()
            logger.info("Redis connections closed")
        except Exception as e:
            logger.error(f"Error closing Redis connections: {e}")

    async def _health_check(self) -> bool:
        """Check Redis health and availability."""
        current_time = time.time()

        # Skip if recently checked
        if current_time - self.last_health_check < self.health_check_interval:
            return self.redis_available

        self.last_health_check = current_time
        self.metrics["health_checks"] += 1

        try:
            if not self.redis_client:
                return False

            # Simple ping test
            if ASYNC_REDIS_AVAILABLE and hasattr(self.redis_client, 'ping'):
                await asyncio.wait_for(self.redis_client.ping(), timeout=self.timeout)
            else:
                # Sync Redis - run in thread
                def sync_ping():
                    return self.redis_client.ping()

                await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(None, sync_ping),
                    timeout=self.timeout
                )

            self.redis_available = True
            return True

        except Exception as e:
            logger.warning(f"Redis health check failed: {e}")
            self.redis_available = False
            return False

    def _generate_key(self, key_type: str, identifier: str) -> str:
        """Generate Redis key with proper namespacing."""
        return f"{self.key_prefix}:{key_type}:{identifier}"

    async def get_counter(self, key_type: str, identifier: str) -> Optional[Dict[str, Any]]:
        """Get rate limit counter from Redis or fallback storage."""
        full_key = self._generate_key(key_type, identifier)

        # Try Redis first
        if await self._health_check():
            try:
                if ASYNC_REDIS_AVAILABLE and hasattr(self.redis_client, 'get'):
                    data = await self.redis_client.get(full_key)
                else:
                    # Sync Redis - run in thread
                    def sync_get():
                        return self.redis_client.get(full_key)

                    data = await asyncio.get_event_loop().run_in_executor(None, sync_get)

                self.metrics["redis_operations"] += 1

                if data:
                    return json.loads(data)

                return None

            except Exception as e:
                logger.warning(f"Redis get operation failed: {e}")
                self.metrics["redis_errors"] += 1
                self.redis_available = False

        # Fallback to in-memory storage
        if self.fallback_enabled:
            self.metrics["fallback_operations"] += 1
            return self.fallback_storage.get(full_key)

        return None

    async def set_counter(self, key_type: str, identifier: str, counter_data: Dict[str, Any], ttl: int = None):
        """Set rate limit counter in Redis or fallback storage."""
        full_key = self._generate_key(key_type, identifier)

        # Try Redis first
        if await self._health_check():
            try:
                data = json.dumps(counter_data)

                if ASYNC_REDIS_AVAILABLE and hasattr(self.redis_client, 'set'):
                    if ttl:
                        await self.redis_client.setex(full_key, ttl, data)
                    else:
                        await self.redis_client.set(full_key, data)
                else:
                    # Sync Redis - run in thread
                    def sync_set():
                        if ttl:
                            return self.redis_client.setex(full_key, ttl, data)
                        else:
                            return self.redis_client.set(full_key, data)

                    await asyncio.get_event_loop().run_in_executor(None, sync_set)

                self.metrics["redis_operations"] += 1
                return True

            except Exception as e:
                logger.warning(f"Redis set operation failed: {e}")
                self.metrics["redis_errors"] += 1
                self.redis_available = False

        # Fallback to in-memory storage
        if self.fallback_enabled:
            self.metrics["fallback_operations"] += 1
            self.fallback_storage[full_key] = counter_data
            return True

        return False

    async def delete_counter(self, key_type: str, identifier: str):
        """Delete rate limit counter from Redis or fallback storage."""
        full_key = self._generate_key(key_type, identifier)

        # Try Redis first
        if await self._health_check():
            try:
                if ASYNC_REDIS_AVAILABLE and hasattr(self.redis_client, 'delete'):
                    await self.redis_client.delete(full_key)
                else:
                    # Sync Redis - run in thread
                    def sync_delete():
                        return self.redis_client.delete(full_key)

                    await asyncio.get_event_loop().run_in_executor(None, sync_delete)

                self.metrics["redis_operations"] += 1
                return True

            except Exception as e:
                logger.warning(f"Redis delete operation failed: {e}")
                self.metrics["redis_errors"] += 1
                self.redis_available = False

        # Fallback to in-memory storage
        if self.fallback_enabled:
            self.metrics["fallback_operations"] += 1
            self.fallback_storage.pop(full_key, None)
            return True

        return False

    async def cleanup_expired_counters(self):
        """Clean up expired counters to prevent memory leaks."""
        current_time = time.time()

        # Redis cleanup (automatic with TTL)
        if await self._health_check():
            try:
                # Get all rate limit keys
                pattern = f"{self.key_prefix}:*"

                if ASYNC_REDIS_AVAILABLE and hasattr(self.redis_client, 'keys'):
                    keys = await self.redis_client.keys(pattern)
                else:
                    # Sync Redis - run in thread
                    def sync_keys():
                        return self.redis_client.keys(pattern)

                    keys = await asyncio.get_event_loop().run_in_executor(None, sync_keys)

                # Redis handles TTL automatically, but we can get stats
                logger.debug(f"Redis contains {len(keys)} rate limit keys")
                self.metrics["redis_operations"] += 1

            except Exception as e:
                logger.warning(f"Redis cleanup operation failed: {e}")
                self.metrics["redis_errors"] += 1

        # Fallback storage cleanup
        if self.fallback_enabled:
            expired_keys = []

            for key, counter_data in self.fallback_storage.items():
                # Simple time-based cleanup for fallback
                if isinstance(counter_data, dict):
                    start_time = counter_data.get('start_time', 0)
                    window = counter_data.get('window', 60)
                    if current_time - start_time > window * 2:
                        expired_keys.append(key)

            for key in expired_keys:
                del self.fallback_storage[key]

            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired fallback counters")

    def get_metrics(self) -> Dict[str, Any]:
        """Get backend metrics for monitoring."""
        return {
            **self.metrics,
            "redis_available": self.redis_available,
            "fallback_enabled": self.fallback_enabled,
            "fallback_storage_size": len(self.fallback_storage),
            "last_health_check": self.last_health_check,
            "redis_url": self.redis_url.split('@')[-1] if '@' in self.redis_url else self.redis_url,  # Hide credentials
            "redis_library_available": REDIS_AVAILABLE,
            "async_redis_available": ASYNC_REDIS_AVAILABLE
        }

    async def reset_all_counters(self):
        """Reset all rate limit counters (for testing/admin purposes)."""
        # Redis reset
        if await self._health_check():
            try:
                pattern = f"{self.key_prefix}:*"

                if ASYNC_REDIS_AVAILABLE and hasattr(self.redis_client, 'keys'):
                    keys = await self.redis_client.keys(pattern)
                    if keys:
                        await self.redis_client.delete(*keys)
                else:
                    # Sync Redis - run in thread
                    def sync_reset():
                        keys = self.redis_client.keys(pattern)
                        if keys:
                            return self.redis_client.delete(*keys)
                        return 0

                    await asyncio.get_event_loop().run_in_executor(None, sync_reset)

                logger.info(f"Reset Redis rate limit counters")
                self.metrics["redis_operations"] += 1

            except Exception as e:
                logger.warning(f"Redis reset operation failed: {e}")
                self.metrics["redis_errors"] += 1

        # Fallback reset
        fallback_count = len(self.fallback_storage)
        self.fallback_storage.clear()

        if fallback_count > 0:
            logger.info(f"Reset {fallback_count} fallback rate limit counters")


# Global Redis backend instance
redis_backend: Optional[RedisRateLimitingBackend] = None


async def get_redis_backend() -> RedisRateLimitingBackend:
    """Get or create Redis backend instance."""
    global redis_backend

    if redis_backend is None:
        redis_backend = RedisRateLimitingBackend()
        await redis_backend.initialize()

    return redis_backend


async def cleanup_redis_backend():
    """Cleanup Redis backend on application shutdown."""
    global redis_backend

    if redis_backend:
        await redis_backend.cleanup()
        redis_backend = None


class RedisRateLimitingBackend:
    """
    Redis backend for distributed rate limiting.

    Features:
    - Distributed rate limiting across multiple server instances
    - Connection pooling and failover
    - Automatic fallback to in-memory if Redis unavailable
    - Data persistence and cleanup
    - Health monitoring
    """

    def __init__(
        self,
        redis_url: Optional[str] = None,
        pool_size: int = 10,
        timeout: float = 5.0,
        fallback_enabled: bool = True,
        key_prefix: str = "rate_limit"
    ):
        self.redis_url = redis_url or getattr(settings, 'RATE_LIMIT_REDIS_URL', 'redis://localhost:6379/0')
        self.pool_size = pool_size
        self.timeout = timeout
        self.fallback_enabled = fallback_enabled
        self.key_prefix = key_prefix

        # Redis connection pool
        self.redis_pool: Optional[aioredis.ConnectionPool] = None
        self.redis_client: Optional[aioredis.Redis] = None

        # Fallback storage (in-memory)
        self.fallback_storage: Dict[str, Dict[str, Any]] = {}

        # Health monitoring
        self.redis_available = False
        self.last_health_check = 0
        self.health_check_interval = 30  # seconds

        # Metrics
        self.metrics = {
            "redis_operations": 0,
            "redis_errors": 0,
            "fallback_operations": 0,
            "connection_failures": 0,
            "health_checks": 0
        }

        logger.info(f"Initialized Redis rate limiting backend: {self.redis_url}")

    async def initialize(self) -> bool:
        """Initialize Redis connection pool."""
        try:
            # Create connection pool
            self.redis_pool = aioredis.ConnectionPool.from_url(
                self.redis_url,
                max_connections=self.pool_size,
                socket_timeout=self.timeout,
                socket_connect_timeout=self.timeout,
                health_check_interval=30
            )

            # Create Redis client
            self.redis_client = aioredis.Redis(
                connection_pool=self.redis_pool,
                decode_responses=True
            )

            # Test connection
            await self._health_check()

            if self.redis_available:
                logger.info("✅ Redis connection initialized successfully")
                return True
            else:
                logger.warning("⚠️ Redis connection failed, fallback mode enabled")
                return False

        except Exception as e:
            logger.error(f"❌ Failed to initialize Redis: {e}")
            self.metrics["connection_failures"] += 1
            return False

    async def cleanup(self):
        """Clean up Redis connections."""
        try:
            if self.redis_client:
                await self.redis_client.close()
            if self.redis_pool:
                await self.redis_pool.disconnect()
            logger.info("Redis connections closed")
        except Exception as e:
            logger.error(f"Error closing Redis connections: {e}")

    async def _health_check(self) -> bool:
        """Check Redis health and availability."""
        current_time = time.time()

        # Skip if recently checked
        if current_time - self.last_health_check < self.health_check_interval:
            return self.redis_available

        self.last_health_check = current_time
        self.metrics["health_checks"] += 1

        try:
            if not self.redis_client:
                return False

            # Simple ping test
            await asyncio.wait_for(
                self.redis_client.ping(),
                timeout=self.timeout
            )

            self.redis_available = True
            return True

        except (ConnectionError, TimeoutError, asyncio.TimeoutError) as e:
            logger.warning(f"Redis health check failed: {e}")
            self.redis_available = False
            return False
        except Exception as e:
            logger.error(f"Unexpected Redis health check error: {e}")
            self.redis_available = False
            return False

    def _generate_key(self, key_type: str, identifier: str) -> str:
        """Generate Redis key with proper namespacing."""
        return f"{self.key_prefix}:{key_type}:{identifier}"

    async def get_counter(self, key_type: str, identifier: str) -> Optional[Dict[str, Any]]:
        """Get rate limit counter from Redis or fallback storage."""
        full_key = self._generate_key(key_type, identifier)

        # Try Redis first
        if await self._health_check():
            try:
                data = await self.redis_client.get(full_key)
                self.metrics["redis_operations"] += 1

                if data:
                    counter_data = json.loads(data)
                    counter = SlidingWindowCounter(
                        limit=counter_data["limit"],
                        window=counter_data["window"],
                        burst_multiplier=counter_data.get("burst_multiplier", 1.5)
                    )
                    counter.requests = counter_data["requests"]
                    counter.start_time = counter_data["start_time"]
                    return counter

                return None

            except (ConnectionError, TimeoutError, RedisError) as e:
                logger.warning(f"Redis get operation failed: {e}")
                self.metrics["redis_errors"] += 1
                self.redis_available = False

        # Fallback to in-memory storage
        if self.fallback_enabled:
            self.metrics["fallback_operations"] += 1
            return self.fallback_storage.get(full_key)

        return None

    async def set_counter(self, key_type: str, identifier: str, counter_data: Dict[str, Any], ttl: int = None):
        """Set rate limit counter in Redis or fallback storage."""
        full_key = self._generate_key(key_type, identifier)

        # Prepare counter data
        counter_data = {
            "limit": counter.limit,
            "window": counter.window,
            "burst_multiplier": counter.burst_multiplier,
            "requests": counter.requests,
            "start_time": counter.start_time
        }

        # Try Redis first
        if await self._health_check():
            try:
                data = json.dumps(counter_data)

                if ttl:
                    await self.redis_client.setex(full_key, ttl, data)
                else:
                    await self.redis_client.set(full_key, data)

                self.metrics["redis_operations"] += 1
                return True

            except (ConnectionError, TimeoutError, RedisError) as e:
                logger.warning(f"Redis set operation failed: {e}")
                self.metrics["redis_errors"] += 1
                self.redis_available = False

        # Fallback to in-memory storage
        if self.fallback_enabled:
            self.metrics["fallback_operations"] += 1
            self.fallback_storage[full_key] = counter
            return True

        return False

    async def delete_counter(self, key_type: str, identifier: str):
        """Delete rate limit counter from Redis or fallback storage."""
        full_key = self._generate_key(key_type, identifier)

        # Try Redis first
        if await self._health_check():
            try:
                await self.redis_client.delete(full_key)
                self.metrics["redis_operations"] += 1
                return True

            except (ConnectionError, TimeoutError, RedisError) as e:
                logger.warning(f"Redis delete operation failed: {e}")
                self.metrics["redis_errors"] += 1
                self.redis_available = False

        # Fallback to in-memory storage
        if self.fallback_enabled:
            self.metrics["fallback_operations"] += 1
            self.fallback_storage.pop(full_key, None)
            return True

        return False

    async def cleanup_expired_counters(self):
        """Clean up expired counters to prevent memory leaks."""
        current_time = time.time()

        # Redis cleanup (automatic with TTL)
        if await self._health_check():
            try:
                # Get all rate limit keys
                pattern = f"{self.key_prefix}:*"
                keys = await self.redis_client.keys(pattern)

                # Redis handles TTL automatically, but we can get stats
                logger.debug(f"Redis contains {len(keys)} rate limit keys")
                self.metrics["redis_operations"] += 1

            except (ConnectionError, TimeoutError, RedisError) as e:
                logger.warning(f"Redis cleanup operation failed: {e}")
                self.metrics["redis_errors"] += 1

        # Fallback storage cleanup
        if self.fallback_enabled:
            expired_keys = []

            for key, counter in self.fallback_storage.items():
                if hasattr(counter, 'start_time') and hasattr(counter, 'window'):
                    if current_time - counter.start_time > counter.window * 2:
                        expired_keys.append(key)

            for key in expired_keys:
                del self.fallback_storage[key]

            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired fallback counters")

    async def get_all_counters(self) -> Dict[str, Any]:
        """Get all rate limit counters for monitoring."""
        all_counters = {}

        # Redis counters
        if await self._health_check():
            try:
                pattern = f"{self.key_prefix}:*"
                keys = await self.redis_client.keys(pattern)

                for key in keys:
                    data = await self.redis_client.get(key)
                    if data:
                        all_counters[key] = json.loads(data)

                self.metrics["redis_operations"] += len(keys) + 1

            except (ConnectionError, TimeoutError, RedisError) as e:
                logger.warning(f"Redis get_all operation failed: {e}")
                self.metrics["redis_errors"] += 1

        # Fallback counters
        for key, counter in self.fallback_storage.items():
            if hasattr(counter, '__dict__'):
                all_counters[f"fallback:{key}"] = counter.__dict__

        return all_counters

    def get_metrics(self) -> Dict[str, Any]:
        """Get backend metrics for monitoring."""
        return {
            **self.metrics,
            "redis_available": self.redis_available,
            "fallback_enabled": self.fallback_enabled,
            "fallback_storage_size": len(self.fallback_storage),
            "last_health_check": self.last_health_check,
            "redis_url": self.redis_url.split('@')[-1] if '@' in self.redis_url else self.redis_url,  # Hide credentials
        }

    async def reset_all_counters(self):
        """Reset all rate limit counters (for testing/admin purposes)."""
        # Redis reset
        if await self._health_check():
            try:
                pattern = f"{self.key_prefix}:*"
                keys = await self.redis_client.keys(pattern)

                if keys:
                    await self.redis_client.delete(*keys)
                    logger.info(f"Reset {len(keys)} Redis rate limit counters")

                self.metrics["redis_operations"] += len(keys) + 1

            except (ConnectionError, TimeoutError, RedisError) as e:
                logger.warning(f"Redis reset operation failed: {e}")
                self.metrics["redis_errors"] += 1

        # Fallback reset
        fallback_count = len(self.fallback_storage)
        self.fallback_storage.clear()

        if fallback_count > 0:
            logger.info(f"Reset {fallback_count} fallback rate limit counters")


# Global Redis backend instance
redis_backend: Optional[RedisRateLimitingBackend] = None


async def get_redis_backend() -> RedisRateLimitingBackend:
    """Get or create Redis backend instance."""
    global redis_backend

    if redis_backend is None:
        redis_backend = RedisRateLimitingBackend()
        await redis_backend.initialize()

    return redis_backend


async def cleanup_redis_backend():
    """Cleanup Redis backend on application shutdown."""
    global redis_backend

    if redis_backend:
        await redis_backend.cleanup()
        redis_backend = None
