#!/usr/bin/env python3
"""
Enhanced Rate Limiting Service
User-aware, endpoint-specific rate limiting with sliding window algorithms
"""

import time
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from collections import defaultdict, deque
from dataclasses import dataclass
from enum import Enum
import asyncio
import json
import hashlib

logger = logging.getLogger(__name__)


class RateLimitType(Enum):
    """Rate limit types for different scenarios."""
    IP_BASED = "ip"
    USER_BASED = "user"
    ENDPOINT_BASED = "endpoint"
    COMBINED = "combined"


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting rules."""
    requests: int
    window: int  # seconds
    burst_multiplier: float = 1.5
    sliding_window: bool = True
    enabled: bool = True


@dataclass
class RateLimitResult:
    """Result of rate limit check."""
    allowed: bool
    remaining: int
    reset_time: float
    retry_after: Optional[int] = None
    limit_type: Optional[str] = None
    exceeded_by: Optional[str] = None


class SlidingWindowCounter:
    """Sliding window rate limit counter."""
    
    def __init__(self, limit: int, window: int):
        self.limit = limit
        self.window = window
        self.requests = deque()
        self.lock = asyncio.Lock()
    
    async def is_allowed(self) -> Tuple[bool, int]:
        """Check if request is allowed and return remaining count."""
        async with self.lock:
            now = time.time()
            window_start = now - self.window
            
            # Remove old requests outside the window
            while self.requests and self.requests[0] < window_start:
                self.requests.popleft()
            
            # Check if we're within limits
            if len(self.requests) >= self.limit:
                return False, 0
            
            # Add current request
            self.requests.append(now)
            remaining = self.limit - len(self.requests)
            
            return True, remaining
    
    def get_reset_time(self) -> float:
        """Get when the rate limit will reset."""
        if not self.requests:
            return time.time()
        return self.requests[0] + self.window
    
    def get_request_count(self) -> int:
        """Get current request count in window."""
        now = time.time()
        window_start = now - self.window
        
        # Count requests in current window
        count = 0
        for request_time in self.requests:
            if request_time >= window_start:
                count += 1
        
        return count


class EnhancedRateLimitingService:
    """
    Enhanced rate limiting service with user-aware, endpoint-specific limits.
    
    Features:
    - IP-based rate limiting
    - User-based rate limiting
    - Endpoint-specific limits
    - Sliding window algorithm
    - Burst protection
    - Admin bypass
    - Comprehensive metrics
    """
    
    def __init__(self):
        self.ip_counters: Dict[str, SlidingWindowCounter] = {}
        self.user_counters: Dict[str, SlidingWindowCounter] = {}
        self.endpoint_counters: Dict[str, SlidingWindowCounter] = {}
        self.combined_counters: Dict[str, SlidingWindowCounter] = {}
        
        # Configuration for different endpoint types
        self.endpoint_configs = {
            "auth": RateLimitConfig(requests=10, window=60, burst_multiplier=1.2),
            "trading": RateLimitConfig(requests=100, window=60, burst_multiplier=1.3),
            "info": RateLimitConfig(requests=200, window=60, burst_multiplier=1.5),
            "admin": RateLimitConfig(requests=5, window=60, burst_multiplier=1.0),
            "default": RateLimitConfig(requests=60, window=60, burst_multiplier=1.4)
        }
        
        # Global configuration
        self.global_config = RateLimitConfig(requests=500, window=60, burst_multiplier=2.0)
        
        # Admin bypass settings
        self.admin_bypass_enabled = True
        self.admin_roles = {"admin", "super_admin"}
        
        # Metrics
        self.metrics = {
            "total_requests": 0,
            "blocked_requests": 0,
            "ip_blocks": 0,
            "user_blocks": 0,
            "endpoint_blocks": 0,
            "admin_bypasses": 0,
            "burst_detections": 0
        }
        
        # Cleanup task
        self.cleanup_interval = 300  # 5 minutes
        self.last_cleanup = time.time()
        
        logger.info("Enhanced Rate Limiting Service initialized")
    
    def get_endpoint_type(self, path: str) -> str:
        """Determine endpoint type from path."""
        path = path.lower()
        
        if any(auth_path in path for auth_path in ["/auth", "/login", "/register"]):
            return "auth"
        elif any(trading_path in path for trading_path in ["/transactions", "/orders", "/trades"]):
            return "trading"
        elif any(admin_path in path for admin_path in ["/admin", "/manage"]):
            return "admin"
        elif any(info_path in path for info_path in ["/health", "/docs", "/openapi"]):
            return "info"
        else:
            return "default"
    
    def is_admin_user(self, user_data: Optional[Dict]) -> bool:
        """Check if user has admin privileges."""
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
        
        current_time = time.time()
        
        # Clean up IP counters
        ip_keys_to_remove = []
        for ip, counter in self.ip_counters.items():
            if current_time - counter.get_reset_time() > counter.window * 2:
                ip_keys_to_remove.append(ip)
        
        for ip in ip_keys_to_remove:
            del self.ip_counters[ip]
        
        # Clean up user counters
        user_keys_to_remove = []
        for user_id, counter in self.user_counters.items():
            if current_time - counter.get_reset_time() > counter.window * 2:
                user_keys_to_remove.append(user_id)
        
        for user_id in user_keys_to_remove:
            del self.user_counters[user_id]
        
        # Clean up endpoint counters
        endpoint_keys_to_remove = []
        for key, counter in self.endpoint_counters.items():
            if current_time - counter.get_reset_time() > counter.window * 2:
                endpoint_keys_to_remove.append(key)
        
        for key in endpoint_keys_to_remove:
            del self.endpoint_counters[key]
        
        # Clean up combined counters
        combined_keys_to_remove = []
        for key, counter in self.combined_counters.items():
            if current_time - counter.get_reset_time() > counter.window * 2:
                combined_keys_to_remove.append(key)
        
        for key in combined_keys_to_remove:
            del self.combined_counters[key]
        
        self.last_cleanup = current_time
        
        total_removed = len(ip_keys_to_remove) + len(user_keys_to_remove) + len(endpoint_keys_to_remove) + len(combined_keys_to_remove)
        if total_removed > 0:
            logger.debug(f"Cleaned up {total_removed} old rate limit counters")
    
    async def check_ip_rate_limit(self, ip: str, endpoint_type: str) -> RateLimitResult:
        """Check IP-based rate limit."""
        config = self.endpoint_configs.get(endpoint_type, self.endpoint_configs["default"])
        
        if not config.enabled:
            return RateLimitResult(allowed=True, remaining=config.requests, reset_time=time.time())
        
        # Get or create counter for this IP
        if ip not in self.ip_counters:
            self.ip_counters[ip] = SlidingWindowCounter(config.requests, config.window)
        
        counter = self.ip_counters[ip]
        allowed, remaining = await counter.is_allowed()
        
        if not allowed:
            self.metrics["ip_blocks"] += 1
            logger.warning(f"IP rate limit exceeded for {ip} on {endpoint_type}")
        
        return RateLimitResult(
            allowed=allowed,
            remaining=remaining,
            reset_time=counter.get_reset_time(),
            retry_after=config.window if not allowed else None,
            limit_type="ip",
            exceeded_by=ip if not allowed else None
        )
    
    async def check_user_rate_limit(self, user_id: str, endpoint_type: str) -> RateLimitResult:
        """Check user-based rate limit."""
        config = self.endpoint_configs.get(endpoint_type, self.endpoint_configs["default"])
        
        if not config.enabled:
            return RateLimitResult(allowed=True, remaining=config.requests, reset_time=time.time())
        
        # User limits are typically higher than IP limits
        user_limit = int(config.requests * 1.5)
        
        # Get or create counter for this user
        if user_id not in self.user_counters:
            self.user_counters[user_id] = SlidingWindowCounter(user_limit, config.window)
        
        counter = self.user_counters[user_id]
        allowed, remaining = await counter.is_allowed()
        
        if not allowed:
            self.metrics["user_blocks"] += 1
            logger.warning(f"User rate limit exceeded for {user_id} on {endpoint_type}")
        
        return RateLimitResult(
            allowed=allowed,
            remaining=remaining,
            reset_time=counter.get_reset_time(),
            retry_after=config.window if not allowed else None,
            limit_type="user",
            exceeded_by=user_id if not allowed else None
        )
    
    async def check_endpoint_rate_limit(self, endpoint_type: str, combined_key: str) -> RateLimitResult:
        """Check endpoint-specific rate limit."""
        config = self.endpoint_configs.get(endpoint_type, self.endpoint_configs["default"])
        
        if not config.enabled:
            return RateLimitResult(allowed=True, remaining=config.requests, reset_time=time.time())
        
        # Get or create counter for this endpoint/user combination
        if combined_key not in self.endpoint_counters:
            self.endpoint_counters[combined_key] = SlidingWindowCounter(config.requests, config.window)
        
        counter = self.endpoint_counters[combined_key]
        allowed, remaining = await counter.is_allowed()
        
        if not allowed:
            self.metrics["endpoint_blocks"] += 1
            logger.warning(f"Endpoint rate limit exceeded for {endpoint_type} ({combined_key})")
        
        return RateLimitResult(
            allowed=allowed,
            remaining=remaining,
            reset_time=counter.get_reset_time(),
            retry_after=config.window if not allowed else None,
            limit_type="endpoint",
            exceeded_by=combined_key if not allowed else None
        )
    
    async def check_burst_protection(self, ip: str, user_id: Optional[str], endpoint_type: str) -> RateLimitResult:
        """Check for burst protection (short-term spike detection)."""
        config = self.endpoint_configs.get(endpoint_type, self.endpoint_configs["default"])
        
        if not config.enabled:
            return RateLimitResult(allowed=True, remaining=config.requests, reset_time=time.time())
        
        # Burst protection: check for too many requests in a short time
        burst_window = 10  # 10 seconds
        burst_limit = int(config.requests * config.burst_multiplier / (config.window / burst_window))
        
        combined_key = self.generate_combined_key(ip, user_id, f"{endpoint_type}_burst")
        
        if combined_key not in self.combined_counters:
            self.combined_counters[combined_key] = SlidingWindowCounter(burst_limit, burst_window)
        
        counter = self.combined_counters[combined_key]
        allowed, remaining = await counter.is_allowed()
        
        if not allowed:
            self.metrics["burst_detections"] += 1
            logger.warning(f"Burst protection triggered for {ip} (user: {user_id}) on {endpoint_type}")
        
        return RateLimitResult(
            allowed=allowed,
            remaining=remaining,
            reset_time=counter.get_reset_time(),
            retry_after=burst_window if not allowed else None,
            limit_type="burst",
            exceeded_by=combined_key if not allowed else None
        )
    
    async def check_rate_limit(
        self, 
        ip: str, 
        path: str, 
        user_data: Optional[Dict] = None
    ) -> RateLimitResult:
        """
        Main rate limit check function.
        
        Args:
            ip: Client IP address
            path: Request path
            user_data: User information from JWT (if authenticated)
            
        Returns:
            RateLimitResult with decision and metadata
        """
        # Update metrics
        self.metrics["total_requests"] += 1
        
        # Clean up old counters periodically
        await self.cleanup_old_counters()
        
        # Determine endpoint type
        endpoint_type = self.get_endpoint_type(path)
        
        # Check for admin bypass
        if self.is_admin_user(user_data):
            self.metrics["admin_bypasses"] += 1
            logger.debug(f"Admin bypass applied for user {user_data.get('username', 'unknown')}")
            return RateLimitResult(
                allowed=True,
                remaining=9999,
                reset_time=time.time() + 3600,
                limit_type="admin_bypass"
            )
        
        user_id = user_data.get("user_id") if user_data else None
        
        # Check multiple rate limit layers
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
        
        return RateLimitResult(
            allowed=True,
            remaining=min_remaining.remaining,
            reset_time=max(r.reset_time for r in results),
            limit_type="combined"
        )
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get comprehensive rate limiting metrics."""
        return {
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
            }
        }
    
    def update_config(self, endpoint_type: str, config: RateLimitConfig):
        """Update rate limit configuration for an endpoint type."""
        self.endpoint_configs[endpoint_type] = config
        logger.info(f"Updated rate limit config for {endpoint_type}: {config}")
    
    def get_config(self, endpoint_type: str) -> RateLimitConfig:
        """Get rate limit configuration for an endpoint type."""
        return self.endpoint_configs.get(endpoint_type, self.endpoint_configs["default"])
    
    def reset_user_limits(self, user_id: str):
        """Reset rate limits for a specific user (admin function)."""
        if user_id in self.user_counters:
            del self.user_counters[user_id]
        
        # Also reset combined counters for this user
        keys_to_remove = []
        for key in self.combined_counters:
            if user_id in key:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.combined_counters[key]
        
        logger.info(f"Reset rate limits for user {user_id}")
    
    def reset_ip_limits(self, ip: str):
        """Reset rate limits for a specific IP (admin function)."""
        if ip in self.ip_counters:
            del self.ip_counters[ip]
        
        # Also reset combined counters for this IP
        keys_to_remove = []
        for key in self.combined_counters:
            if ip in key:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.combined_counters[key]
        
        logger.info(f"Reset rate limits for IP {ip}")


# Global rate limiting service instance
rate_limiting_service = EnhancedRateLimitingService()
