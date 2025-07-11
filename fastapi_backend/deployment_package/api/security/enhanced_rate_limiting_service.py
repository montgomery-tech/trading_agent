#!/usr/bin/env python3
"""
Enhanced Rate Limiting Service with Redis Integration
Updated for Task 1.4.B: Redis Integration for Production
"""

import asyncio
import hashlib
import logging
import time
from dataclasses import dataclass
from typing import Dict, Optional, Any, List
from enum import Enum

from api.config import settings

logger = logging.getLogger(__name__)


class RateLimitType(Enum):
    """Rate limit types for different scenarios."""
    IP_BASED = "ip"
    USER_BASED = "user"
    ENDPOINT_BASED = "endpoint"
    COMBINED = "combined"


@dataclass
class RateLimitResult:
    """Result of a rate limit check."""
    allowed: bool
    remaining: int
    reset_time: int
    retry_after: Optional[int] = None
    limit_type: str = "unknown"
    exceeded_by: int = 0


@dataclass
class RateLimitConfig:
    """Configuration for a specific rate limit."""
    requests: int
    window: int  # seconds
    burst_multiplier: float = 1.5
    enabled: bool = True


class SlidingWindowCounter:
    """
    Sliding window rate limiting counter.
    More accurate than fixed window, prevents burst issues.
    """

    def __init__(self, limit: int, window: int, burst_multiplier: float = 1.5):
        self.limit = limit
        self.window = window
        self.burst_multiplier = burst_multiplier
        self.requests: List[float] = []
        self.start_time = time.time()

    def is_allowed(self, current_time: Optional[float] = None) -> tuple[bool, int]:
        """Check if request is allowed and return remaining count."""
        if current_time is None:
            current_time = time.time()

        # Clean up old requests outside the window
        cutoff_time = current_time - self.window
        self.requests = [req_time for req_time in self.requests if req_time > cutoff_time]

        # Check if under limit
        current_count = len(self.requests)
        burst_limit = int(self.limit * self.burst_multiplier)

        if current_count < self.limit:
            return True, self.limit - current_count - 1  # -1 for the current request
        elif current_count < burst_limit:
            # Allow burst but mark as at capacity
            return True, 0
        else:
            return False, 0

    def add_request(self, current_time: Optional[float] = None):
        """Add a request to the counter."""
        if current_time is None:
            current_time = time.time()
        self.requests.append(current_time)

    def get_reset_time(self) -> int:
        """Get when the counter will reset."""
        if not self.requests:
            return int(time.time())
        return int(self.requests[0] + self.window)

    def get_retry_after(self, current_time: Optional[float] = None) -> Optional[int]:
        """Get seconds until next request is allowed."""
        if not self.requests:
            return None

        if current_time is None:
            current_time = time.time()

        oldest_request = self.requests[0]
        retry_time = oldest_request + self.window - current_time
        return max(0, int(retry_time))


class EnhancedRateLimitingService:
    """
    Enhanced rate limiting service with Redis backend support.

    Features:
    - Distributed rate limiting using Redis
    - Fallback to in-memory if Redis unavailable
    - User-aware and IP-based rate limiting
    - Endpoint-specific limits
    - Sliding window algorithm
    - Burst protection
    - Admin bypass capabilities
    """

    def __init__(self):
        # Redis backend (imported here to avoid circular imports)
        self.redis_backend = None
        self._redis_initialized = False

        # Endpoint-specific configurations
        self.endpoint_configs = {
            "auth": RateLimitConfig(
                requests=getattr(settings, 'RATE_LIMIT_AUTH_REQUESTS', 10),
                window=60,
                burst_multiplier=1.2
            ),
            "trading": RateLimitConfig(
                requests=getattr(settings, 'RATE_LIMIT_TRADING_REQUESTS', 100),
                window=60,
                burst_multiplier=1.5
            ),
            "info": RateLimitConfig(
                requests=getattr(settings, 'RATE_LIMIT_INFO_REQUESTS', 200),
                window=60,
                burst_multiplier=2.0
            ),
            "admin": RateLimitConfig(
                requests=getattr(settings, 'RATE_LIMIT_ADMIN_REQUESTS', 5),
                window=60,
                burst_multiplier=1.0
            ),
            "default": RateLimitConfig(
                requests=getattr(settings, 'RATE_LIMIT_REQUESTS_PER_MINUTE', 60),
                window=60,
                burst_multiplier=1.5
            )
        }

        # Fallback in-memory storage (used when Redis unavailable)
        self.ip_counters: Dict[str, SlidingWindowCounter] = {}
        self.user_counters: Dict[str, SlidingWindowCounter] = {}
        self.endpoint_counters: Dict[str, SlidingWindowCounter] = {}
        self.combined_counters: Dict[str, SlidingWindowCounter] = {}

        # Admin bypass settings
        self.admin_bypass_enabled = getattr(settings, 'RATE_LIMIT_ADMIN_BYPASS', True)
        self.admin_roles = {"admin", "superuser", "system"}

        # Cleanup settings
        self.cleanup_interval = 300  # 5 minutes
        self.last_cleanup = time.time()

        # Metrics
        self.metrics = {
            "total_requests": 0,
            "allowed_requests": 0,
            "blocked_requests": 0,
            "redis_operations": 0,
            "fallback_operations": 0,
            "admin_bypasses": 0,
            "burst_allowances": 0
        }

        logger.info("Enhanced Rate Limiting Service initialized")

    async def initialize_redis(self):
        """Initialize Redis backend."""
        if self._redis_initialized:
            return

        try:
            # Import here to avoid circular imports
            from api.security.redis_rate_limiting_backend import get_redis_backend

            self.redis_backend = await get_redis_backend()
            self._redis_initialized = True

            logger.info("✅ Redis backend initialized for rate limiting")

        except Exception as e:
            logger.warning(f"⚠️ Redis backend initialization failed: {e}")
            logger.info("📦 Falling back to in-memory rate limiting")

    async def _get_counter(self, key_type: str, identifier: str, config: RateLimitConfig) -> SlidingWindowCounter:
        """Get or create a rate limiting counter."""
        # Try Redis backend first
        if self.redis_backend and self.redis_backend.redis_available:
            try:
                counter_data = await self.redis_backend.get_counter(key_type, identifier)
                if counter_data:
                    counter = SlidingWindowCounter(
                        limit=config.requests,
                        window=config.window,
                        burst_multiplier=config.burst_multiplier
                    )
                    counter.requests = counter_data.get("requests", [])
                    counter.start_time = counter_data.get("start_time", time.time())
                    return counter

                # Create new counter
                counter = SlidingWindowCounter(
                    limit=config.requests,
                    window=config.window,
                    burst_multiplier=config.burst_multiplier
                )

                # Store in Redis with TTL
                counter_data = {
                    "requests": counter.requests,
                    "start_time": counter.start_time,
                    "limit": counter.limit,
                    "window": counter.window,
                    "burst_multiplier": counter.burst_multiplier
                }
                await self.redis_backend.set_counter(
                    key_type, identifier, counter_data, ttl=config.window * 2
                )

                self.metrics["redis_operations"] += 1
                return counter

            except Exception as e:
                logger.warning(f"Redis counter operation failed: {e}")
                # Fall through to in-memory fallback

        # Fallback to in-memory storage
        storage_map = {
            "ip": self.ip_counters,
            "user": self.user_counters,
            "endpoint": self.endpoint_counters,
            "combined": self.combined_counters
        }

        storage = storage_map.get(key_type, self.combined_counters)

        if identifier not in storage:
            storage[identifier] = SlidingWindowCounter(
                limit=config.requests,
                window=config.window,
                burst_multiplier=config.burst_multiplier
            )

        self.metrics["fallback_operations"] += 1
        return storage[identifier]

    async def _update_counter(self, key_type: str, identifier: str, counter: SlidingWindowCounter):
        """Update counter in storage."""
        # Try Redis backend first
        if self.redis_backend and self.redis_backend.redis_available:
            try:
                counter_data = {
                    "requests": counter.requests,
                    "start_time": counter.start_time,
                    "limit": counter.limit,
                    "window": counter.window,
                    "burst_multiplier": counter.burst_multiplier
                }
                await self.redis_backend.set_counter(
                    key_type, identifier, counter_data, ttl=counter.window * 2
                )
                return
            except Exception as e:
                logger.warning(f"Redis counter update failed: {e}")

        # Fallback: counter is already updated in memory

    def _determine_endpoint_type(self, path: str) -> str:
        """Determine endpoint type from request path."""
        if "/auth" in path:
            return "auth"
        elif any(keyword in path for keyword in ["/trade", "/order", "/transaction"]):
            return "trading"
        elif "/admin" in path:
            return "admin"
        elif any(keyword in path for keyword in ["/user", "/balance", "/currency", "/health"]):
            return "info"
        else:
            return "default"

    def _is_admin_user(self, user_data: Optional[Dict[str, Any]]) -> bool:
        """Check if user should bypass rate limits."""
        if not user_data or not self.admin_bypass_enabled:
            return False

        user_role = user_data.get("role", "").lower()
        return user_role in self.admin_roles

    def generate_combined_key(self, ip: str, user_id: Optional[str], endpoint_type: str) -> str:
        """Generate a combined key for multi-dimensional rate limiting."""
        components = [ip, user_id or "anonymous", endpoint_type]
        key_string = "|".join(components)
        return hashlib.md5(key_string.encode()).hexdigest()

    async def cleanup_old_counters(self):
        """Clean up old rate limit counters to prevent memory leaks."""
        if time.time() - self.last_cleanup < self.cleanup_interval:
            return

        # Redis cleanup (handled by Redis backend)
        if self.redis_backend:
            try:
                await self.redis_backend.cleanup_expired_counters()
            except Exception as e:
                logger.warning(f"Redis cleanup failed: {e}")

        # In-memory cleanup
        current_time = time.time()

        for storage in [self.ip_counters, self.user_counters,
                       self.endpoint_counters, self.combined_counters]:
            keys_to_remove = []
            for key, counter in storage.items():
                if current_time - counter.get_reset_time() > counter.window * 2:
                    keys_to_remove.append(key)

            for key in keys_to_remove:
                del storage[key]

        self.last_cleanup = current_time

    async def check_ip_rate_limit(self, ip: str, endpoint_type: str) -> RateLimitResult:
        """Check IP-based rate limit."""
        config = self.endpoint_configs.get(endpoint_type, self.endpoint_configs["default"])
        if not config.enabled:
            return RateLimitResult(allowed=True, remaining=config.requests, reset_time=0, limit_type="ip")

        counter = await self._get_counter("ip", ip, config)
        allowed, remaining = counter.is_allowed()

        if allowed:
            counter.add_request()
            await self._update_counter("ip", ip, counter)

        return RateLimitResult(
            allowed=allowed,
            remaining=remaining,
            reset_time=counter.get_reset_time(),
            retry_after=counter.get_retry_after() if not allowed else None,
            limit_type="ip",
            exceeded_by=len(counter.requests) - config.requests if not allowed else 0
        )

    async def check_user_rate_limit(self, user_id: str, endpoint_type: str) -> RateLimitResult:
        """Check user-based rate limit."""
        config = self.endpoint_configs.get(endpoint_type, self.endpoint_configs["default"])
        if not config.enabled:
            return RateLimitResult(allowed=True, remaining=config.requests, reset_time=0, limit_type="user")

        counter = await self._get_counter("user", user_id, config)
        allowed, remaining = counter.is_allowed()

        if allowed:
            counter.add_request()
            await self._update_counter("user", user_id, counter)

        return RateLimitResult(
            allowed=allowed,
            remaining=remaining,
            reset_time=counter.get_reset_time(),
            retry_after=counter.get_retry_after() if not allowed else None,
            limit_type="user",
            exceeded_by=len(counter.requests) - config.requests if not allowed else 0
        )

    async def check_endpoint_rate_limit(self, endpoint_type: str, combined_key: str) -> RateLimitResult:
        """Check endpoint-specific rate limit."""
        config = self.endpoint_configs.get(endpoint_type, self.endpoint_configs["default"])
        if not config.enabled:
            return RateLimitResult(allowed=True, remaining=config.requests, reset_time=0, limit_type="endpoint")

        counter = await self._get_counter("endpoint", combined_key, config)
        allowed, remaining = counter.is_allowed()

        if allowed:
            counter.add_request()
            await self._update_counter("endpoint", combined_key, counter)

        return RateLimitResult(
            allowed=allowed,
            remaining=remaining,
            reset_time=counter.get_reset_time(),
            retry_after=counter.get_retry_after() if not allowed else None,
            limit_type="endpoint",
            exceeded_by=len(counter.requests) - config.requests if not allowed else 0
        )

    async def check_burst_protection(self, ip: str, user_id: Optional[str], endpoint_type: str) -> RateLimitResult:
        """Check burst protection (short-term spike detection)."""
        config = self.endpoint_configs.get(endpoint_type, self.endpoint_configs["default"])

        # Create shorter window for burst detection
        burst_config = RateLimitConfig(
            requests=int(config.requests * 0.3),  # 30% of normal limit
            window=30,  # 30 second window
            burst_multiplier=1.0
        )

        burst_key = f"burst_{ip}_{user_id or 'anon'}_{endpoint_type}"
        counter = await self._get_counter("combined", burst_key, burst_config)
        allowed, remaining = counter.is_allowed()

        if allowed:
            counter.add_request()
            await self._update_counter("combined", burst_key, counter)

        return RateLimitResult(
            allowed=allowed,
            remaining=remaining,
            reset_time=counter.get_reset_time(),
            retry_after=counter.get_retry_after() if not allowed else None,
            limit_type="burst",
            exceeded_by=len(counter.requests) - burst_config.requests if not allowed else 0
        )

    async def check_rate_limit(
        self,
        ip: str,
        user_id: Optional[str] = None,
        user_data: Optional[Dict[str, Any]] = None,
        endpoint_path: str = "/",
        request_method: str = "GET"
    ) -> RateLimitResult:
        """
        Comprehensive rate limit check.

        Checks multiple dimensions:
        1. IP-based rate limiting
        2. User-based rate limiting (if authenticated)
        3. Endpoint-specific rate limiting
        4. Burst protection
        5. Admin bypass
        """
        # Initialize Redis if not done yet
        if not self._redis_initialized:
            await self.initialize_redis()

        # Cleanup old counters periodically
        await self.cleanup_old_counters()

        self.metrics["total_requests"] += 1

        # Admin bypass check
        if self._is_admin_user(user_data):
            self.metrics["admin_bypasses"] += 1
            logger.debug(f"Admin bypass granted for user {user_id}")
            return RateLimitResult(
                allowed=True,
                remaining=999999,
                reset_time=int(time.time() + 3600),
                limit_type="admin_bypass"
            )

        # Determine endpoint type
        endpoint_type = self._determine_endpoint_type(endpoint_path)

        # Run all rate limit checks
        results = []

        # 1. IP-based rate limiting
        ip_result = await self.check_ip_rate_limit(ip, endpoint_type)
        results.append(ip_result)

        # 2. User-based rate limiting (if authenticated)
        if user_id:
            user_result = await self.check_user_rate_limit(user_id, endpoint_type)
            results.append(user_result)

        # 3. Endpoint-specific rate limiting
        combined_key = self.generate_combined_key(ip, user_id, endpoint_type)
        endpoint_result = await self.check_endpoint_rate_limit(endpoint_type, combined_key)
        results.append(endpoint_result)

        # 4. Burst protection
        burst_result = await self.check_burst_protection(ip, user_id, endpoint_type)
        results.append(burst_result)

        # Find the most restrictive result
        blocked_results = [r for r in results if not r.allowed]

        if blocked_results:
            # Request is blocked - find the most restrictive limit
            most_restrictive = min(blocked_results, key=lambda r: r.retry_after or 0)
            self.metrics["blocked_requests"] += 1

            logger.warning(
                f"Rate limit exceeded: {most_restrictive.limit_type} limit for "
                f"IP={ip}, User={user_id}, Endpoint={endpoint_type}, "
                f"Exceeded by={most_restrictive.exceeded_by}"
            )

            return most_restrictive

        # Request is allowed - return the most restrictive remaining count
        min_remaining = min(results, key=lambda r: r.remaining)
        self.metrics["allowed_requests"] += 1

        return RateLimitResult(
            allowed=True,
            remaining=min_remaining.remaining,
            reset_time=max(r.reset_time for r in results),
            limit_type="combined"
        )

    def get_metrics(self) -> Dict[str, Any]:
        """Get comprehensive rate limiting metrics."""
        base_metrics = {
            **self.metrics,
            "active_counters": {
                "ip_counters": len(self.ip_counters),
                "user_counters": len(self.user_counters),
                "endpoint_counters": len(self.endpoint_counters),
                "combined_counters": len(self.combined_counters)
            },
            "configurations": {
                endpoint_type: {
                    "requests": config.requests,
                    "window": config.window,
                    "burst_multiplier": config.burst_multiplier,
                    "enabled": config.enabled
                }
                for endpoint_type, config in self.endpoint_configs.items()
            },
            "redis_backend_initialized": self._redis_initialized
        }

        # Add Redis backend metrics if available
        if self.redis_backend:
            redis_metrics = self.redis_backend.get_metrics()
            base_metrics["redis_backend"] = redis_metrics

        return base_metrics

    def update_config(self, endpoint_type: str, config: RateLimitConfig):
        """Update rate limit configuration for an endpoint type."""
        self.endpoint_configs[endpoint_type] = config
        logger.info(f"Updated rate limit config for {endpoint_type}: {config}")

    def get_config(self, endpoint_type: str) -> RateLimitConfig:
        """Get rate limit configuration for an endpoint type."""
        return self.endpoint_configs.get(endpoint_type, self.endpoint_configs["default"])

    async def reset_counters(self, scope: str = "all"):
        """Reset rate limit counters for testing/admin purposes."""
        if scope == "all" or scope == "memory":
            # Reset in-memory counters
            self.ip_counters.clear()
            self.user_counters.clear()
            self.endpoint_counters.clear()
            self.combined_counters.clear()
            logger.info("Reset all in-memory rate limit counters")

        if scope == "all" or scope == "redis":
            # Reset Redis counters
            if self.redis_backend:
                await self.redis_backend.reset_all_counters()
                logger.info("Reset all Redis rate limit counters")

    async def get_counter_status(self, ip: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get detailed counter status for monitoring/debugging."""
        status = {
            "ip": ip,
            "user_id": user_id,
            "timestamp": time.time(),
            "counters": {}
        }

        # Check each endpoint type
        for endpoint_type in self.endpoint_configs.keys():
            endpoint_status = {
                "config": {
                    "requests": self.endpoint_configs[endpoint_type].requests,
                    "window": self.endpoint_configs[endpoint_type].window,
                    "enabled": self.endpoint_configs[endpoint_type].enabled
                },
                "ip_counter": None,
                "user_counter": None,
                "combined_counter": None
            }

            # Get IP counter status
            try:
                ip_counter = await self._get_counter("ip", ip, self.endpoint_configs[endpoint_type])
                allowed, remaining = ip_counter.is_allowed()
                endpoint_status["ip_counter"] = {
                    "allowed": allowed,
                    "remaining": remaining,
                    "current_requests": len(ip_counter.requests),
                    "reset_time": ip_counter.get_reset_time()
                }
            except Exception as e:
                endpoint_status["ip_counter"] = {"error": str(e)}

            # Get user counter status if user authenticated
            if user_id:
                try:
                    user_counter = await self._get_counter("user", user_id, self.endpoint_configs[endpoint_type])
                    allowed, remaining = user_counter.is_allowed()
                    endpoint_status["user_counter"] = {
                        "allowed": allowed,
                        "remaining": remaining,
                        "current_requests": len(user_counter.requests),
                        "reset_time": user_counter.get_reset_time()
                    }
                except Exception as e:
                    endpoint_status["user_counter"] = {"error": str(e)}

            status["counters"][endpoint_type] = endpoint_status

        return status


# Global rate limiting service instance
rate_limiting_service = EnhancedRateLimitingService()
