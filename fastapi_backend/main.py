#!/usr/bin/env python3
"""
Balance Tracking System - FastAPI Backend
Updated main application with JWT authentication support and Task 1.3 Security Framework
"""

from fastapi import FastAPI, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from datetime import datetime
import logging

from api.config import settings
from api.database import DatabaseManager
from api.routes import users, transactions, balances, currencies

from api.auth_routes import router as auth_router

from api.security import (
    create_security_middleware_stack,
    security_exception_handler,
    EnhancedErrorResponse
)

from api.security.redis_rate_limiting_backend import cleanup_redis_backend

# Setup logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager with Redis integration"""
    logger.info("🚀 Starting Balance Tracking API...")

    # Initialize database
    db = DatabaseManager(settings.DATABASE_URL)
    try:
        db.connect()
        app.state.database = db
        logger.info("✅ Database initialized")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise

    # Initialize Redis backend for rate limiting
    try:
        from api.security.enhanced_rate_limiting_service import rate_limiting_service
        await rate_limiting_service.initialize_redis()
        logger.info("✅ Redis rate limiting backend initialized")
    except Exception as e:
        logger.warning(f"⚠️ Redis initialization failed, using fallback: {e}")

    # Log production readiness status
    logger.info("🏭 Production Configuration Status:")
    logger.info(f"   • Environment: {settings.ENVIRONMENT}")
    logger.info(f"   • Database: {settings.DATABASE_TYPE}")
    logger.info(f"   • JWT Authentication: {'Enabled' if hasattr(settings, 'SECRET_KEY') else 'Disabled'}")
    logger.info(f"   • Rate Limiting: {'Enabled' if getattr(settings, 'RATE_LIMIT_ENABLED', True) else 'Disabled'}")
    logger.info(f"   • Redis Backend: {'Configured' if hasattr(settings, 'RATE_LIMIT_REDIS_URL') else 'Not Configured'}")
    logger.info(f"   • Max request size: {getattr(settings, 'MAX_REQUEST_SIZE', 10485760) / 1024 / 1024:.1f}MB")
    logger.info(f"   • Request timeout: {getattr(settings, 'REQUEST_TIMEOUT', 30)}s")
    logger.info(f"   • Input validation: Enabled")
    logger.info(f"   • Security headers: Enabled")

    yield

    # Cleanup
    logger.info("🛑 Shutting down...")

    # Cleanup Redis connections
    try:
        await cleanup_redis_backend()
        logger.info("✅ Redis backend cleaned up")
    except Exception as e:
        logger.warning(f"⚠️ Redis cleanup warning: {e}")

    # Cleanup database
    if hasattr(app.state, 'database'):
        app.state.database.disconnect()
        logger.info("✅ Database disconnected")


# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="REST API for managing user balances, transactions, and trading with JWT authentication and comprehensive security",
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# NEW: Apply Task 1.3 Security Middleware Stack FIRST (before CORS)
app = create_security_middleware_stack(app)

# Add CORS middleware with secure settings (after security middleware)
cors_origins = getattr(settings, 'CORS_ORIGINS', ["http://localhost:3000"])
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
)

# NEW: Add enhanced exception handlers
app.add_exception_handler(HTTPException, security_exception_handler)

# Include authentication routes (from Task 1.2)
app.include_router(
    auth_router,
    prefix=f"{settings.API_V1_PREFIX}/auth",
    tags=["Authentication"]
)

# Include existing API routes
app.include_router(
    users.router,
    prefix=f"{settings.API_V1_PREFIX}/users",
    tags=["Users"]
)

app.include_router(
    transactions.router,
    prefix=f"{settings.API_V1_PREFIX}/transactions",
    tags=["Transactions"]
)

app.include_router(
    balances.router,
    prefix=f"{settings.API_V1_PREFIX}/balances",
    tags=["Balances"]
)

app.include_router(
    currencies.router,
    prefix=f"{settings.API_V1_PREFIX}/currencies",
    tags=["Currencies"]
)

# Root endpoints
@app.get("/")
async def root():
    """API root endpoint with authentication and security info"""
    return {
        "message": f"{settings.PROJECT_NAME} API",
        "version": settings.VERSION,
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "authentication": "JWT Bearer Token",
        "security": {
            "input_validation": "enabled",
            "rate_limiting": "enabled" if getattr(settings, 'RATE_LIMIT_ENABLED', True) else "disabled",
            "security_headers": "enabled",
            "request_size_limit": f"{getattr(settings, 'MAX_REQUEST_SIZE', 10485760) / 1024 / 1024:.1f}MB"
        },
        "documentation": "/docs",
        "endpoints": {
            "health": "/health",
            "authentication": f"{settings.API_V1_PREFIX}/auth",
            "users": f"{settings.API_V1_PREFIX}/users",
            "balances": f"{settings.API_V1_PREFIX}/balances",
            "transactions": f"{settings.API_V1_PREFIX}/transactions",
            "currencies": f"{settings.API_V1_PREFIX}/currencies"
        },
        "auth_endpoints": {
            "register": f"{settings.API_V1_PREFIX}/auth/register",
            "login": f"{settings.API_V1_PREFIX}/auth/login",
            "refresh": f"{settings.API_V1_PREFIX}/auth/refresh",
            "logout": f"{settings.API_V1_PREFIX}/auth/logout",
            "profile": f"{settings.API_V1_PREFIX}/auth/me",
            "change_password": f"{settings.API_V1_PREFIX}/auth/change-password"
        }
    }


@app.get("/health")
async def health_check():
    """Enhanced health check endpoint with authentication and security status"""
    try:
        db = app.state.database
        db.test_connection()

        # Check if we have any users (authentication system working)
        user_count_query = "SELECT COUNT(*) as count FROM users"
        user_result = db.execute_query(user_count_query)
        user_count = user_result[0]['count'] if user_result else 0

        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "database": {
                "status": "connected",
                "type": settings.DATABASE_TYPE,
                "users": user_count
            },
            "authentication": {
                "jwt_enabled": True,
                "token_expiration_minutes": settings.JWT_EXPIRE_MINUTES,
                "algorithm": settings.JWT_ALGORITHM
            },
            "security": {
                "input_validation": "enabled",
                "rate_limiting": "enabled" if getattr(settings, 'RATE_LIMIT_ENABLED', True) else "disabled",
                "security_headers": "enabled",
                "cors_configured": len(getattr(settings, 'CORS_ORIGINS', [])) > 0,
                "max_request_size_mb": getattr(settings, 'MAX_REQUEST_SIZE', 10485760) / 1024 / 1024,
                "request_timeout_seconds": getattr(settings, 'REQUEST_TIMEOUT', 30)
            },
            "version": settings.VERSION,
            "environment": settings.ENVIRONMENT
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }


# NEW: Global exception handler for unhandled exceptions
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled exceptions."""
    logger.error(f"Unhandled exception: {str(exc)}")

    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "timestamp": datetime.utcnow().isoformat()
        }
    )

# Add Redis monitoring endpoint
@app.get("/api/redis/health")
async def redis_health():
    """Redis health check endpoint"""
    try:
        from api.security.enhanced_rate_limiting_service import rate_limiting_service

        if not rate_limiting_service._redis_initialized:
            return JSONResponse(
                status_code=503,
                content={
                    "status": "error",
                    "message": "Redis not initialized",
                    "fallback_active": True
                }
            )

        if not rate_limiting_service.redis_backend:
            return JSONResponse(
                status_code=503,
                content={
                    "status": "error",
                    "message": "Redis backend not available",
                    "fallback_active": True
                }
            )

        # Check Redis health
        redis_available = await rate_limiting_service.redis_backend._health_check()

        if redis_available:
            return {
                "status": "healthy",
                "redis_available": True,
                "fallback_active": False,
                "metrics": rate_limiting_service.redis_backend.get_metrics()
            }
        else:
            return JSONResponse(
                status_code=503,
                content={
                    "status": "degraded",
                    "redis_available": False,
                    "fallback_active": True,
                    "message": "Redis unavailable, using fallback"
                }
            )

    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": f"Health check failed: {str(e)}",
                "fallback_active": True
            }
        )


if __name__ == "__main__":
    import uvicorn

    print(f"🚀 Starting {settings.PROJECT_NAME}...")
    print("📚 API Documentation: http://localhost:8000/docs")
    print("🏥 Health Check: http://localhost:8000/health")
    print("🔐 Authentication endpoints available at /api/v1/auth/*")
    print(f"🔑 JWT Token expiration: {settings.JWT_EXPIRE_MINUTES} minutes")
    print("🛡️ Security Framework: Input validation, rate limiting, security headers enabled")

    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
