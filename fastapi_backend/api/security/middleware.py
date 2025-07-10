#!/usr/bin/env python3
"""
Updated Security Middleware with Enhanced Rate Limiting Integration
"""

import time
import logging
import re
from typing import Callable, Dict, List, Optional
from datetime import datetime, timedelta
import json
import asyncio
from collections import defaultdict

from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from api.config import settings

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses.
    FIXED: Swagger UI compatible CSP headers
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.headers = self._get_security_headers()

    def _get_security_headers(self) -> Dict[str, str]:
        """Get security headers configuration."""
        base_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
        }

        # Add HSTS header for HTTPS in production
        if getattr(settings, 'ENVIRONMENT', 'development') == 'production':
            base_headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        elif getattr(settings, 'DEBUG', True):
            # For development/testing, add a shorter HSTS for testing purposes
            base_headers["Strict-Transport-Security"] = "max-age=3600"

        # Add CSP header (Swagger UI compatible)
        if getattr(settings, 'DEBUG', True):
            # Development CSP - allows Swagger UI
            base_headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "img-src 'self' data: https:; "
                "connect-src 'self' https:"
            )
        else:
            # Production CSP - more restrictive
            base_headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data:; "
                "connect-src 'self'"
            )

        return base_headers

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add security headers to all responses."""
        response = await call_next(request)

        # Skip CSP for Swagger UI endpoints in development
        if settings.DEBUG and request.url.path in ["/docs", "/redoc", "/openapi.json"]:
            # Apply all headers except CSP for Swagger UI
            for header_name, header_value in self.headers.items():
                if header_name != "Content-Security-Policy":
                    response.headers[header_name] = header_value
        else:
            # Add all security headers
            for header_name, header_value in self.headers.items():
                response.headers[header_name] = header_value

        return response


class RequestSizeMiddleware(BaseHTTPMiddleware):
    """
    Middleware to limit request body size and prevent DoS attacks.
    """

    def __init__(self, app: ASGIApp, max_request_size: int = 10 * 1024 * 1024):  # 10MB default
        super().__init__(app)
        self.max_request_size = max_request_size

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Check request size before processing."""
        # Check Content-Length header
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_request_size:
            logger.warning(f"Request size too large: {content_length} bytes from {request.client.host}")
            return JSONResponse(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                content={
                    "success": False,
                    "error": "Request entity too large",
                    "max_size": self.max_request_size
                }
            )

        return await call_next(request)


class RequestTimeoutMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add request timeout handling.
    """

    def __init__(self, app: ASGIApp, timeout: int = 30):
        super().__init__(app)
        self.timeout = timeout

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add timeout to request processing."""
        try:
            response = await asyncio.wait_for(call_next(request), timeout=self.timeout)
            return response
        except asyncio.TimeoutError:
            logger.warning(f"Request timeout after {self.timeout}s for {request.url}")
            return JSONResponse(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                content={
                    "success": False,
                    "error": "Request timeout",
                    "timeout": self.timeout
                }
            )


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for comprehensive request/response logging.
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.sensitive_headers = {
            "authorization", "cookie", "x-api-key", "x-auth-token"
        }
        self.sensitive_fields = {
            "password", "token", "secret", "key", "auth"
        }

    def _sanitize_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Sanitize sensitive headers for logging."""
        sanitized = {}
        for key, value in headers.items():
            if key.lower() in self.sensitive_headers:
                sanitized[key] = "[REDACTED]"
            else:
                sanitized[key] = value
        return sanitized

    def _sanitize_data(self, data: Dict) -> Dict:
        """Sanitize sensitive data for logging."""
        if not isinstance(data, dict):
            return data

        sanitized = {}
        for key, value in data.items():
            if any(sensitive in key.lower() for sensitive in self.sensitive_fields):
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_data(value)
            else:
                sanitized[key] = value
        return sanitized

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Log request and response details."""
        start_time = time.time()

        # Skip logging for documentation endpoints to reduce noise
        if request.url.path not in ["/docs", "/redoc", "/openapi.json"]:
            # Log request details
            logger.info(f"Request: {request.method} {request.url}")
            logger.debug(f"Headers: {self._sanitize_headers(dict(request.headers))}")
            logger.debug(f"Client: {request.client.host}")

        # Process request
        response = await call_next(request)

        # Calculate processing time
        process_time = time.time() - start_time

        # Skip logging for documentation endpoints
        if request.url.path not in ["/docs", "/redoc", "/openapi.json"]:
            # Log response details
            logger.info(f"Response: {response.status_code} ({process_time:.3f}s)")

            # Log slow requests
            if process_time > 1.0:
                logger.warning(f"Slow request: {request.method} {request.url} took {process_time:.3f}s")

        # Add processing time header
        response.headers["X-Process-Time"] = str(round(process_time, 3))

        return response


class CORSSecurityMiddleware(BaseHTTPMiddleware):
    """
    Enhanced CORS middleware with security validation.
    """

    def __init__(self, app: ASGIApp, allowed_origins: Optional[List[str]] = None):
        super().__init__(app)
        self.allowed_origins = allowed_origins or []
        self.allowed_methods = ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]
        self.allowed_headers = [
            "Authorization", "Content-Type", "X-Requested-With", "Accept", "Origin"
        ]

    def _is_origin_allowed(self, origin: str) -> bool:
        """Check if origin is allowed."""
        if not self.allowed_origins:
            return False

        # Exact match
        if origin in self.allowed_origins:
            return True

        # Wildcard support (be careful with this in production)
        for allowed_origin in self.allowed_origins:
            if allowed_origin == "*":
                return True
            if allowed_origin.endswith("*"):
                prefix = allowed_origin[:-1]
                if origin.startswith(prefix):
                    return True

        return False

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Handle CORS with security validation."""
        origin = request.headers.get("origin")

        # Handle preflight requests
        if request.method == "OPTIONS":
            if origin and self._is_origin_allowed(origin):
                return Response(
                    headers={
                        "Access-Control-Allow-Origin": origin,
                        "Access-Control-Allow-Methods": ", ".join(self.allowed_methods),
                        "Access-Control-Allow-Headers": ", ".join(self.allowed_headers),
                        "Access-Control-Allow-Credentials": "true",
                        "Access-Control-Max-Age": "86400"  # 24 hours
                    }
                )
            else:
                return Response(status_code=403)

        # Process regular request
        response = await call_next(request)

        # Add CORS headers if origin is allowed
        if origin and self._is_origin_allowed(origin):
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"

        return response


class SecurityValidationMiddleware(BaseHTTPMiddleware):
    """
    Middleware for comprehensive security validation.
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.suspicious_patterns = [
            # Common attack patterns
            re.compile(r'<script[^>]*>', re.IGNORECASE),
            re.compile(r'javascript:', re.IGNORECASE),
            re.compile(r'vbscript:', re.IGNORECASE),
            re.compile(r'onload\s*=', re.IGNORECASE),
            re.compile(r'onerror\s*=', re.IGNORECASE),
            re.compile(r'eval\s*\(', re.IGNORECASE),
            re.compile(r'expression\s*\(', re.IGNORECASE),
        ]

        self.blocked_user_agents = [
            re.compile(r'sqlmap', re.IGNORECASE),
            re.compile(r'nikto', re.IGNORECASE),
            re.compile(r'dirb', re.IGNORECASE),
            re.compile(r'nessus', re.IGNORECASE),
            re.compile(r'openvas', re.IGNORECASE),
            re.compile(r'burp', re.IGNORECASE),
        ]

    def _check_suspicious_content(self, content: str) -> bool:
        """Check for suspicious patterns in content."""
        for pattern in self.suspicious_patterns:
            if pattern.search(content):
                return True
        return False

    def _check_user_agent(self, user_agent: str) -> bool:
        """Check if user agent is blocked."""
        if not user_agent:
            return False

        for pattern in self.blocked_user_agents:
            if pattern.search(user_agent):
                return True
        return False

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Validate request for security threats."""
        # Skip security validation for documentation endpoints
        if request.url.path in ["/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)

        # Check user agent
        user_agent = request.headers.get("user-agent", "")
        if self._check_user_agent(user_agent):
            logger.warning(f"Blocked suspicious user agent: {user_agent} from {request.client.host}")
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"success": False, "error": "Access denied"}
            )

        # Check for suspicious patterns in URL
        url_str = str(request.url)
        if self._check_suspicious_content(url_str):
            logger.warning(f"Suspicious URL pattern detected: {url_str} from {request.client.host}")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"success": False, "error": "Invalid request"}
            )

        # Check request headers for suspicious content
        for header_name, header_value in request.headers.items():
            if self._check_suspicious_content(header_value):
                logger.warning(f"Suspicious header content in {header_name}: {header_value} from {request.client.host}")
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"success": False, "error": "Invalid request"}
                )

        return await call_next(request)


class DNSRebindingProtectionMiddleware(BaseHTTPMiddleware):
    """
    Middleware to protect against DNS rebinding attacks.
    """

    def __init__(self, app: ASGIApp, allowed_hosts: Optional[List[str]] = None):
        super().__init__(app)
        self.allowed_hosts = allowed_hosts or ["localhost", "127.0.0.1", "0.0.0.0"]
        if hasattr(settings, 'ALLOWED_HOSTS'):
            self.allowed_hosts.extend(settings.ALLOWED_HOSTS)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Validate Host header to prevent DNS rebinding."""
        host = request.headers.get("host")

        if not host:
            logger.warning(f"Request without Host header from {request.client.host}")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"success": False, "error": "Host header required"}
            )

        # Extract hostname (remove port if present)
        hostname = host.split(":")[0]

        # Check if host is allowed
        if hostname not in self.allowed_hosts:
            # Allow if it's a development environment
            if settings.DEBUG and hostname in ["localhost", "127.0.0.1"]:
                pass
            else:
                logger.warning(f"Invalid Host header: {host} from {request.client.host}")
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"success": False, "error": "Invalid host"}
                )

        return await call_next(request)

# Add this class to the existing middleware.py file

class IPRateLimitMiddleware(BaseHTTPMiddleware):
    """
    Basic IP-based rate limiting middleware (fallback when enhanced rate limiting is unavailable).
    """

    def __init__(self, app: ASGIApp, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.window_size = 60  # 1 minute window
        self.ip_requests = defaultdict(list)
        self.last_cleanup = time.time()
        logger.info(f"Basic IP Rate Limiting initialized: {requests_per_minute} requests per minute")

    def _cleanup_old_requests(self):
        """Clean up old request records to prevent memory leaks."""
        current_time = time.time()

        # Only cleanup every 30 seconds to avoid overhead
        if current_time - self.last_cleanup < 30:
            return

        cutoff_time = current_time - self.window_size

        # Remove old requests for all IPs
        for ip in list(self.ip_requests.keys()):
            # Filter out old requests
            self.ip_requests[ip] = [
                req_time for req_time in self.ip_requests[ip]
                if req_time > cutoff_time
            ]

            # Remove empty entries
            if not self.ip_requests[ip]:
                del self.ip_requests[ip]

        self.last_cleanup = current_time

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request."""
        # Check for forwarded IP headers
        forwarded_headers = ["X-Forwarded-For", "X-Real-IP", "CF-Connecting-IP"]

        for header in forwarded_headers:
            if header in request.headers:
                ip = request.headers[header].split(",")[0].strip()
                if ip:
                    return ip

        # Fallback to direct client IP
        return request.client.host if request.client else "unknown"

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Apply basic IP rate limiting."""

        # Skip rate limiting for documentation endpoints
        if request.url.path in ["/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)

        # Clean up old requests periodically
        self._cleanup_old_requests()

        # Get client IP
        client_ip = self._get_client_ip(request)
        current_time = time.time()
        window_start = current_time - self.window_size

        # Get requests for this IP in the current window
        ip_requests = self.ip_requests[client_ip]

        # Filter to only requests in the current window
        recent_requests = [req_time for req_time in ip_requests if req_time > window_start]

        # Check if limit exceeded
        if len(recent_requests) >= self.requests_per_minute:
            # Calculate when the rate limit will reset
            oldest_request = min(recent_requests) if recent_requests else current_time
            reset_time = oldest_request + self.window_size
            retry_after = max(1, int(reset_time - current_time))

            logger.warning(
                f"Basic rate limit exceeded for IP {client_ip}: "
                f"{len(recent_requests)} requests in last {self.window_size}s"
            )

            # Update metrics
            security_metrics.increment_rate_limited()

            response = JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "success": False,
                    "error": "Rate limit exceeded",
                    "retry_after": retry_after,
                    "limit_type": "ip_basic",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

            # Add rate limit headers
            response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
            response.headers["X-RateLimit-Remaining"] = "0"
            response.headers["X-RateLimit-Reset"] = str(int(reset_time))
            response.headers["X-RateLimit-Type"] = "ip_basic"
            response.headers["Retry-After"] = str(retry_after)

            return response

        # Request is allowed - record it
        recent_requests.append(current_time)
        self.ip_requests[client_ip] = recent_requests

        # Process request normally
        response = await call_next(request)

        # Add rate limit headers to successful responses
        remaining = self.requests_per_minute - len(recent_requests)
        next_reset = window_start + self.window_size

        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(next_reset))
        response.headers["X-RateLimit-Type"] = "ip_basic"

        return response

# Factory function to create configured middleware
def create_security_middleware_stack(app):
    """
    Create and configure all security middleware.

    Args:
        app: FastAPI application instance

    Returns:
        App with security middleware applied
    """
    # Request size limiting
    max_request_size = getattr(settings, 'MAX_REQUEST_SIZE', 10 * 1024 * 1024)  # 10MB
    app.add_middleware(RequestSizeMiddleware, max_request_size=max_request_size)

    # Request timeout
    request_timeout = getattr(settings, 'REQUEST_TIMEOUT', 30)
    app.add_middleware(RequestTimeoutMiddleware, timeout=request_timeout)

    # ENHANCED RATE LIMITING (NEW)
    # Import and use the enhanced rate limiting middleware
    try:
        from api.security.enhanced_rate_limiting_middleware import create_enhanced_rate_limiting_middleware
        app = create_enhanced_rate_limiting_middleware(app)
    except ImportError:
        logger.warning("Enhanced rate limiting not available, using basic rate limiting")
        # Fallback to basic rate limiting if needed
        if getattr(settings, 'RATE_LIMIT_ENABLED', True):
            from api.security.middleware import IPRateLimitMiddleware
            requests_per_minute = getattr(settings, 'RATE_LIMIT_REQUESTS_PER_MINUTE', 60)
            app.add_middleware(IPRateLimitMiddleware, requests_per_minute=requests_per_minute)

    # CORS with security validation
    cors_origins = getattr(settings, 'CORS_ORIGINS', [])
    if cors_origins:
        app.add_middleware(CORSSecurityMiddleware, allowed_origins=cors_origins)

    # DNS rebinding protection
    allowed_hosts = getattr(settings, 'ALLOWED_HOSTS', ["localhost", "127.0.0.1"])
    app.add_middleware(DNSRebindingProtectionMiddleware, allowed_hosts=allowed_hosts)

    # Security validation
    app.add_middleware(SecurityValidationMiddleware)

    # Request logging
    app.add_middleware(RequestLoggingMiddleware)

    # Security headers (should be last to ensure headers are added to all responses)
    app.add_middleware(SecurityHeadersMiddleware)

    logger.info("Security middleware stack configured with enhanced rate limiting")
    return app


# Exception handlers for security-related errors
async def security_exception_handler(request: Request, exc: HTTPException):
    """Custom exception handler for security-related errors."""
    # Log security incidents
    if exc.status_code in [400, 401, 403, 429]:
        logger.warning(
            f"Security incident: {exc.status_code} - {exc.detail} "
            f"from {request.client.host} accessing {request.url}"
        )

    # Return consistent error format
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.detail,
            "timestamp": datetime.utcnow().isoformat(),
            "path": str(request.url.path)
        }
    )


# Security metrics collection (for monitoring)
class SecurityMetrics:
    """Collect security-related metrics."""

    def __init__(self):
        self.blocked_requests = 0
        self.rate_limited_requests = 0
        self.suspicious_requests = 0
        self.invalid_hosts = 0

    def increment_blocked(self):
        self.blocked_requests += 1

    def increment_rate_limited(self):
        self.rate_limited_requests += 1

    def increment_suspicious(self):
        self.suspicious_requests += 1

    def increment_invalid_host(self):
        self.invalid_hosts += 1

    def get_metrics(self) -> Dict[str, int]:
        return {
            "blocked_requests": self.blocked_requests,
            "rate_limited_requests": self.rate_limited_requests,
            "suspicious_requests": self.suspicious_requests,
            "invalid_hosts": self.invalid_hosts
        }


# Global metrics instance
security_metrics = SecurityMetrics()
