#!/usr/bin/env python3
"""
Fixed Redis Backend for Enhanced Rate Limiting System
Fixes Redis 5.x/6.x compatibility issues and async client initialization
"""

import asyncio
import json
import logging
import time
from typing import Dict, Optional, Any, List
from dataclasses import asdict

try:
    import redis
    # For Redis 5.x/6.x, use the correct import path
    try:
        import redis.asyncio as aioredis
        ASYNC_REDIS_AVAILABLE = True
    except ImportError:
        try:
            # Fallback for older Redis versions
            import aioredis
            ASYNC_REDIS_AVAILABLE = True
        except ImportError:
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
    Fixed Redis backend for distributed rate limiting.

    Fixes:
    - Redis 5.x/6.x compatibility
    - Proper async client initialization
    - Better error handling for connection issues
    - Graceful fallback when Redis is unavailable
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

        # Redis connection
        self.redis_client: Optional[Any] = None

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
        if not REDIS_AVAILABLE:
            logger.warning("Redis library not available, using fallback only")
        elif not ASYNC_REDIS_AVAILABLE:
            logger.warning("Async Redis not available, using sync Redis with wrapper")

    async def initialize(self) -> bool:
        """Initialize Redis connection with proper error handling."""
        if not REDIS_AVAILABLE:
            logger.warning("Redis library not available, using fallback only")
            return False

        try:
            if ASYNC_REDIS_AVAILABLE and aioredis:
                # Use async Redis client
                self.redis_client = aioredis.from_url(
                    self.redis_url,
                    max_connections=self.pool_size,
                    socket_timeout=self.timeout,
                    socket_connect_timeout=self.timeout,
                    decode_responses=True
                )
                logger.info("Using async Redis client")
            else:
                # Use sync Redis with asyncio wrapper
                pool = redis.ConnectionPool.from_url(
                    self.redis_url,
                    max_connections=self.pool_size,
                    socket_timeout=self.timeout,
                    socket_connect_timeout=self.timeout,
                    decode_responses=True
                )
                self.redis_client = redis.Redis(connection_pool=pool)
                logger.info("Using sync Redis client with async wrapper")

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
            self.redis_client = None
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
        """Check Redis health with proper async handling."""
        current_time = time.time()

        # Skip if recently checked
        if current_time - self.last_health_check < self.health_check_interval:
            return self.redis_available

        self.last_health_check = current_time
        self.metrics["health_checks"] += 1

        try:
            if not self.redis_client:
                return False

            # Use appropriate ping method based on client type
            if ASYNC_REDIS_AVAILABLE and hasattr(self.redis_client, 'ping'):
                # Async client
                await asyncio.wait_for(
                    self.redis_client.ping(),
                    timeout=self.timeout
                )
            else:
                # Sync client - wrap in executor
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None,
                    lambda: self.redis_client.ping()
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
        redis_key = self._generate_key(key_type, identifier)

        # Try Redis first
        if await self._health_check():
            try:
                if ASYNC_REDIS_AVAILABLE and hasattr(self.redis_client, 'get'):
                    # Async Redis
                    data = await self.redis_client.get(redis_key)
                else:
                    # Sync Redis with executor
                    loop = asyncio.get_event_loop()
                    data = await loop.run_in_executor(
                        None,
                        lambda: self.redis_client.get(redis_key)
                    )

                if data:
                    self.metrics["redis_operations"] += 1
                    return json.loads(data)

            except Exception as e:
                logger.warning(f"Redis get operation failed: {e}")
                self.metrics["redis_errors"] += 1

        # Fallback to in-memory storage
        self.metrics["fallback_operations"] += 1
        return self.fallback_storage.get(redis_key)

    async def set_counter(self, key_type: str, identifier: str, data: Dict[str, Any], ttl: int = 3600) -> bool:
        """Set rate limit counter in Redis or fallback storage."""
        redis_key = self._generate_key(key_type, identifier)
        json_data = json.dumps(data)

        # Try Redis first
        if await self._health_check():
            try:
                if ASYNC_REDIS_AVAILABLE and hasattr(self.redis_client, 'setex'):
                    # Async Redis
                    await self.redis_client.setex(redis_key, ttl, json_data)
                else:
                    # Sync Redis with executor
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(
                        None,
                        lambda: self.redis_client.setex(redis_key, ttl, json_data)
                    )

                self.metrics["redis_operations"] += 1
                return True

            except Exception as e:
                logger.warning(f"Redis set operation failed: {e}")
                self.metrics["redis_errors"] += 1

        # Fallback to in-memory storage
        self.fallback_storage[redis_key] = data
        self.metrics["fallback_operations"] += 1
        return False  # Indicates fallback was used

    async def get_all_counters(self) -> Dict[str, Any]:
        """Get all rate limit counters from Redis and fallback storage."""
        all_counters = {}

        # Redis counters
        if await self._health_check():
            try:
                pattern = f"{self.key_prefix}:*"

                if ASYNC_REDIS_AVAILABLE and hasattr(self.redis_client, 'keys'):
                    # Async Redis
                    keys = await self.redis_client.keys(pattern)
                    for key in keys:
                        data = await self.redis_client.get(key)
                        if data:
                            all_counters[key] = json.loads(data)
                else:
                    # Sync Redis with executor
                    loop = asyncio.get_event_loop()
                    keys = await loop.run_in_executor(
                        None,
                        lambda: self.redis_client.keys(pattern)
                    )
                    for key in keys:
                        data = await loop.run_in_executor(
                            None,
                            lambda k=key: self.redis_client.get(k)
                        )
                        if data:
                            all_counters[key] = json.loads(data)

                self.metrics["redis_operations"] += len(keys) + 1

            except Exception as e:
                logger.warning(f"Redis get_all operation failed: {e}")
                self.metrics["redis_errors"] += 1

        # Fallback counters
        for key, counter in self.fallback_storage.items():
            if key not in all_counters:  # Don't override Redis data
                all_counters[f"fallback:{key}"] = counter

        return all_counters

    def get_metrics(self) -> Dict[str, Any]:
        """Get backend metrics for monitoring."""
        return {
            **self.metrics,
            "redis_available": self.redis_available,
            "fallback_enabled": self.fallback_enabled,
            "fallback_storage_size": len(self.fallback_storage),
            "last_health_check": self.last_health_check,
            "redis_url": self.redis_url.split('@')[-1] if '@' in self.redis_url else self.redis_url,
            "async_redis_available": ASYNC_REDIS_AVAILABLE,
            "redis_library_available": REDIS_AVAILABLE
        }

    async def reset_all_counters(self):
        """Reset all rate limit counters (for testing/admin purposes)."""
        # Redis reset
        if await self._health_check():
            try:
                pattern = f"{self.key_prefix}:*"

                if ASYNC_REDIS_AVAILABLE and hasattr(self.redis_client, 'keys'):
                    # Async Redis
                    keys = await self.redis_client.keys(pattern)
                    if keys:
                        await self.redis_client.delete(*keys)
                else:
                    # Sync Redis with executor
                    loop = asyncio.get_event_loop()
                    keys = await loop.run_in_executor(
                        None,
                        lambda: self.redis_client.keys(pattern)
                    )
                    if keys:
                        await loop.run_in_executor(
                            None,
                            lambda: self.redis_client.delete(*keys)
                        )

                logger.info(f"Reset {len(keys) if keys else 0} Redis rate limit counters")
                self.metrics["redis_operations"] += len(keys) + 1 if keys else 1

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
