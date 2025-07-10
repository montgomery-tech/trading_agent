#!/usr/bin/env python3
"""
Security Middleware for the Balance Tracking API
Request processing, security headers, and attack prevention
"""

import time
import logging
from typing import Callable, Dict, List, Optional
from datetime import datetime, timedelta
import json
import asyncio
from collections import defaultdict

from fastapi import Request, Response, HTTPException, status
from fastapi.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware as StarletteBaseHTTPMiddleware

from api.config import settings

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses.

    Adds headers for:
    - XSS Protection
    - Content Type Options
    - Frame Options
    - HSTS (if HTTPS)
    - Content Security Policy
    - Referrer Policy
    """

    def __init__(self, app):
        super().__init__(app)
        self.headers = self._get_security_headers()

    def _get_security_headers(self) -> Dict[str, str]:
        """Get security headers configuration."""
        headers = {
            # Prevent XSS attacks
            "X-XSS-Protection": "1; mode=block",

            # Prevent MIME type sniffing
            "X-Content-Type-Options": "nosniff",

            # Prevent clickjacking
            "X-Frame-Options": "DENY",

            # Control referrer information
            "Referrer-Policy": "strict-origin-when-cross-origin",

            # Content Security Policy
            "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'",

            # Permissions Policy (formerly Feature Policy)
            "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=()",

            # Server identification
            "Server": "Balance-Tracking-API",

            # API versioning
            "API-Version": settings.VERSION,
        }

        # Add HSTS header if HTTPS is enabled
        if getattr(settings, 'HTTPS_ONLY', False):
            hsts_max_age = getattr(settings, 'HSTS_MAX_AGE', 31536000)  # 1 year
            headers["Strict-Transport-Security"] = f"max-age={hsts_max_age}; includeSubDomains; preload"

        return headers

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add security headers to all responses."""
        response = await call_next(request)

        # Add security headers
        for header_name, header_value in self.headers.items():
            response.headers[header_name] = header_value

        return response


class RequestSizeMiddleware(BaseHTTPMiddleware):
    """
    Middleware to limit request body size and prevent DoS attacks.
    """

    def __init__(self, app, max_request_size: int = 10 * 1024 * 1024):  # 10MB default
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

    def __init__(self, app, timeout: int = 30):
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


class IPRateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple IP-based rate limiting middleware.

    Note: In production, consider using Redis or a proper rate limiting service.
    """

    def __init__(self, app, requests_per_minute: int = 60, window_minutes: int = 1):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.window_minutes = window_minutes
        self.request_counts: Dict[str, List[datetime]] = defaultdict(list)
        self.cleanup_interval = timedelta(minutes=5)
        self.last_cleanup = datetime.now()

    def _cleanup_old_requests(self):
        """Clean up old request records."""
        now = datetime.now()
        if now - self.last_cleanup < self.cleanup_interval:
            return

        cutoff_time = now - timedelta(minutes=self.window_minutes)
        for ip in list(self.request_counts.keys()):
            self.request_counts[ip] = [
                timestamp for timestamp in self.request_counts[ip]
                if timestamp > cutoff_time
            ]
            if not self.request_counts[ip]:
                del self.request_counts[ip]

        self.last_cleanup = now

    def _is_rate_limited(self, client_ip: str) -> bool:
        """Check if client IP is rate limited."""
        now = datetime.now()
        cutoff_time = now - timedelta(minutes=self.window_minutes)

        # Clean up old requests for this IP
        self.request_counts[client_ip] = [
            timestamp for timestamp in self.request_counts[client_ip]
            if timestamp > cutoff_time
        ]

        # Check if rate limit exceeded
        if len(self.request_counts[client_ip]) >= self.requests_per_minute:
            return True

        # Add current request
        self.request_counts[client_ip].append(now)
        return False

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Apply rate limiting based on client IP."""
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)

        client_ip = request.client.host

        # Clean up old requests periodically
        self._cleanup_old_requests()

        # Check rate limit
        if self._is_rate_limited(client_ip):
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "success": False,
                    "error": "Rate limit exceeded",
                    "retry_after": self.window_minutes * 60
                },
                headers={
                    "Retry-After": str(self.window_minutes * 60),
                    "X-RateLimit-Limit": str(self.requests_per_minute),
                    "X-RateLimit-Window": str(self.window_minutes * 60)
                }
            )

        # Add rate limit headers to response
        response = await call_next(request)
        remaining = max(0, self.requests_per_minute - len(self.request_counts[client_ip]))

        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(time.time() + self.window_minutes * 60))

        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for comprehensive request/response logging.
    """

    def __init__(self, app):
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

        # Log request details
        logger.info(f"Request: {request.method} {request.url}")
        logger.debug(f"Headers: {self._sanitize_headers(dict(request.headers))}")
        logger.debug(f"Client: {request.client.host}")

        # Process request
        response = await call_next(request)

        # Calculate processing time
        process_time = time.time() - start_time

        # Log response details
        logger.info(f"Response: {response.status_code} ({process_time:.3f}s)")

        # Add processing time header
        response.headers["X-Process-Time"] = str(round(process_time, 3))

        # Log slow requests
        if process_time > 1.0:
            logger.warning(f"Slow request: {request.method} {request.url} took {process_time:.3f}s")

        return response


class CORSSecurityMiddleware(BaseHTTPMiddleware):
    """
    Enhanced CORS middleware with security validation.
    """

    def __init__(self, app, allowed_origins: Optional[List[str]] = None):
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

    def __init__(self, app):
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

    def __init__(self, app, allowed_hosts: Optional[List[str]] = None):
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

    # Rate limiting (if enabled)
    if getattr(settings, 'RATE_LIMIT_ENABLED', True):
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

    logger.info("Security middleware stack configured")
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
