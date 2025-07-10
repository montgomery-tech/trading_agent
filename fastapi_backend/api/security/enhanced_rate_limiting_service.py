#!/usr/bin/env python3
"""
Enhanced Rate Limiting Middleware - FIXED VERSION
Integrates with EnhancedRateLimitingService to provide comprehensive rate limiting
"""

import time
import logging
from typing import Callable, Dict, Optional
from datetime import datetime

from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from api.config import settings
from api.security.enhanced_rate_limiting_service import rate_limiting_service

logger = logging.getLogger(__name__)


class EnhancedRateLimitingMiddleware(BaseHTTPMiddleware):
    """
    Enhanced rate limiting middleware that integrates with EnhancedRateLimitingService.

    Features:
    - IP-based rate limiting
    - User-based rate limiting (when authenticated)
    - Endpoint-specific limits
    - Sliding window algorithm
    - Burst protection
    - Admin bypass
    - Comprehensive rate limit headers
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.rate_limiting_service = rate_limiting_service
        logger.info("Enhanced Rate Limiting Middleware initialized")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request through enhanced rate limiting."""

        # Skip rate limiting for documentation endpoints
        if request.url.path in ["/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)

        # Get client IP
        client_ip = self._get_client_ip(request)

        # Extract user data from JWT if available
        user_data = await self._extract_user_data(request)

        # Check rate limits
        try:
            rate_limit_result = await self.rate_limiting_service.check_rate_limit(
                ip=client_ip,
                user_id=user_data.get("user_id") if user_data else None,
                user_data=user_data,
                endpoint_path=request.url.path,
                request_method=request.method
            )

            # If rate limit exceeded, return 429 response
            if not rate_limit_result.allowed:
                logger.warning(
                    f"Rate limit exceeded for IP {client_ip}, "
                    f"path {request.url.path}, "
                    f"limit_type: {rate_limit_result.limit_type}"
                )

                response = JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "success": False,
                        "error": "Rate limit exceeded",
                        "retry_after": rate_limit_result.retry_after,
                        "limit_type": rate_limit_result.limit_type,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )

                # Add rate limit headers
                self._add_rate_limit_headers(response, rate_limit_result)
                return response

            # Process request normally
            response = await call_next(request)

            # Add rate limit headers to successful responses
            self._add_rate_limit_headers(response, rate_limit_result)

            return response

        except Exception as e:
            logger.error(f"Rate limiting error: {e}")
            # Continue with request if rate limiting fails
            return await call_next(request)

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request."""
        # Check for forwarded IP headers (in order of preference)
        forwarded_headers = [
            "X-Forwarded-For",
            "X-Real-IP",
            "CF-Connecting-IP",  # Cloudflare
            "X-Client-IP"
        ]

        for header in forwarded_headers:
            if header in request.headers:
                # Take the first IP from comma-separated list
                ip = request.headers[header].split(",")[0].strip()
                if ip:
                    return ip

        # Fallback to direct client IP
        return request.client.host if request.client else "unknown"

    async def _extract_user_data(self, request: Request) -> Optional[Dict]:
        """Extract user data from JWT token if present."""
        try:
            # Try to get Authorization header
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                return None

            # Import JWT service (avoid circular imports)
            from api.jwt_service import jwt_service

            # Extract token
            token = auth_header.split(" ")[1]

            # Decode and verify token
            payload = jwt_service.decode_token(token)

            if payload:
                return {
                    "user_id": payload.get("sub"),
                    "username": payload.get("username"),
                    "role": payload.get("role", "user")
                }
        except Exception as e:
            logger.debug(f"Could not extract user data from token: {e}")

        return None

    def _add_rate_limit_headers(self, response: Response, result) -> None:
        """Add rate limiting headers to response."""
        try:
            response.headers["X-RateLimit-Limit"] = str(
                self.rate_limiting_service.get_config("default").requests
            )
            response.headers["X-RateLimit-Remaining"] = str(result.remaining)
            response.headers["X-RateLimit-Reset"] = str(int(result.reset_time))
            response.headers["X-RateLimit-Type"] = result.limit_type or "combined"

            if hasattr(result, 'retry_after') and result.retry_after:
                response.headers["Retry-After"] = str(result.retry_after)
        except Exception as e:
            logger.debug(f"Failed to add rate limit headers: {e}")


class RateLimitingConfigMiddleware(BaseHTTPMiddleware):
    """
    Middleware to handle rate limiting configuration and monitoring endpoints.
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.rate_limiting_service = rate_limiting_service

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Handle rate limiting configuration endpoints."""

        # Handle rate limiting metrics endpoint
        if request.url.path == "/api/rate-limit/metrics" and request.method == "GET":
            return await self._handle_metrics_request(request)

        # Handle rate limiting configuration endpoint
        if request.url.path == "/api/rate-limit/config" and request.method in ["GET", "POST"]:
            return await self._handle_config_request(request)

        # Handle rate limiting reset endpoint
        if request.url.path.startswith("/api/rate-limit/reset") and request.method == "POST":
            return await self._handle_reset_request(request)

        # Continue with normal processing
        return await call_next(request)

    async def _handle_metrics_request(self, request: Request) -> Response:
        """Handle metrics endpoint request."""
        try:
            metrics = self.rate_limiting_service.get_metrics()
            return JSONResponse(content={
                "success": True,
                "data": metrics,
                "timestamp": datetime.utcnow().isoformat()
            })
        except Exception as e:
            logger.error(f"Error retrieving rate limiting metrics: {e}")
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": f"Failed to retrieve metrics: {str(e)}"
                }
            )

    async def _handle_config_request(self, request: Request) -> Response:
        """Handle configuration endpoint request."""
        try:
            if request.method == "GET":
                # Return current configuration
                configs = {}
                for endpoint_type in self.rate_limiting_service.endpoint_configs:
                    config = self.rate_limiting_service.get_config(endpoint_type)
                    configs[endpoint_type] = {
                        "requests": config.requests,
                        "window": config.window,
                        "burst_multiplier": config.burst_multiplier,
                        "enabled": config.enabled
                    }

                return JSONResponse(content={
                    "success": True,
                    "data": {
                        "configurations": configs
                    },
                    "timestamp": datetime.utcnow().isoformat()
                })

            elif request.method == "POST":
                # Update configuration (admin only)
                user_data = await self._extract_user_from_request(request)
                if not self._is_admin_user(user_data):
                    return JSONResponse(
                        status_code=403,
                        content={
                            "success": False,
                            "error": "Admin privileges required"
                        }
                    )

                # TODO: Implement configuration update logic
                return JSONResponse(content={
                    "success": True,
                    "message": "Configuration update endpoint placeholder"
                })

        except Exception as e:
            logger.error(f"Error handling config request: {e}")
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": f"Failed to handle config request: {str(e)}"
                }
            )

    async def _handle_reset_request(self, request: Request) -> Response:
        """Handle rate limit reset endpoint request."""
        try:
            # Extract admin user check
            user_data = await self._extract_user_from_request(request)
            if not self._is_admin_user(user_data):
                return JSONResponse(
                    status_code=403,
                    content={
                        "success": False,
                        "error": "Admin privileges required"
                    }
                )

            # Reset counters
            await self.rate_limiting_service.reset_counters("all")

            return JSONResponse(content={
                "success": True,
                "message": "Rate limit counters reset successfully",
                "timestamp": datetime.utcnow().isoformat()
            })

        except Exception as e:
            logger.error(f"Error handling reset request: {e}")
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": f"Failed to reset counters: {str(e)}"
                }
            )

    async def _extract_user_from_request(self, request: Request) -> Optional[Dict]:
        """Extract user data from request for admin checks."""
        try:
            # Try to get Authorization header
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                return None

            # Import JWT service (avoid circular imports)
            from api.jwt_service import jwt_service

            # Extract token
            token = auth_header.split(" ")[1]

            # Decode and verify token
            payload = jwt_service.decode_token(token)

            if payload:
                return {
                    "user_id": payload.get("sub"),
                    "username": payload.get("username"),
                    "role": payload.get("role", "user")
                }
        except Exception as e:
            logger.debug(f"Could not extract user data from token: {e}")

        return None

    def _is_admin_user(self, user_data: Optional[Dict]) -> bool:
        """Check if user has admin privileges."""
        if not user_data:
            return False

        user_role = user_data.get("role", "").lower()
        return user_role in {"admin", "super_admin", "superuser"}


def create_enhanced_rate_limiting_middleware(app):
    """
    Factory function to create and configure enhanced rate limiting middleware.

    Args:
        app: FastAPI application instance

    Returns:
        App with enhanced rate limiting middleware applied
    """
    # Add configuration middleware first (for admin endpoints)
    app.add_middleware(RateLimitingConfigMiddleware)

    # Add main rate limiting middleware
    app.add_middleware(EnhancedRateLimitingMiddleware)

    logger.info("Enhanced rate limiting middleware stack configured")
    return app
