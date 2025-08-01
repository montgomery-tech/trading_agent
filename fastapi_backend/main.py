#!/usr/bin/env python3
"""
FastAPI Balance Tracking System - Main Application
Using API Key Authentication (JWT authentication removed)
FIXED: Database properly stored in app.state for dependency injection
"""

import logging
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer

from api.config import settings
from api.database import DatabaseManager
from api.security.middleware import security_exception_handler
from api.routes import (
    admin, api_key_admin, users, transactions,
    balances, currencies, trades, simple_trades, spread_management, trading_pairs
)

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database manager
db_manager = DatabaseManager(settings.DATABASE_URL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    try:
        logger.info("🚀 Starting Balance Tracking API with API Key Authentication")
        db_manager.connect()

        # 🔑 CRITICAL FIX: Store database in app.state for dependency injection
        app.state.database = db_manager

        logger.info("✅ Database connection established")
        logger.info("✅ Database stored in app.state for dependency injection")
        yield
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise
    finally:
        # Shutdown
        try:
            db_manager.disconnect()
            logger.info("✅ Database connection closed")
        except Exception as e:
            logger.error(f"❌ Error closing database: {e}")


# Create FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Balance Tracking System with API Key Authentication",
    lifespan=lifespan
)

# Add security middleware
security = HTTPBearer()

# Add CORS middleware
cors_origins = getattr(settings, 'CORS_ORIGINS', ["http://localhost:3000"])
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
)

# Add enhanced exception handlers
app.add_exception_handler(HTTPException, security_exception_handler)

# Include admin routes
app.include_router(
    admin.router,
    prefix=f"{settings.API_V1_PREFIX}/admin",
    tags=["Admin Management"]
)

# Include API key management routes
app.include_router(
    api_key_admin.router,
    prefix=f"{settings.API_V1_PREFIX}/admin",
    tags=["API Key Management"]
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

app.include_router(
    trades.router,
    prefix=f"{settings.API_V1_PREFIX}/trades",
    tags=["Trades"]
)

app.include_router(
    simple_trades.router,
    prefix="/api/v1/trades",
    tags=["Simple Trades"]
)

app.include_router(
    spread_management.router,
    prefix="/api/v1/trading-pairs",
    tags=["Trading Pairs"]
)


# Root endpoints
@app.get("/")
async def root():
    """API root endpoint with authentication and security info"""
    return {
        "message": f"{settings.PROJECT_NAME} API",
        "version": settings.VERSION,
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "authentication": "API Key Authentication",
        "security": {
            "input_validation": "enabled",
            "rate_limiting": "enabled" if getattr(settings, 'RATE_LIMIT_ENABLED', True) else "disabled",
            "security_headers": "enabled",
            "request_size_limit": f"{getattr(settings, 'MAX_REQUEST_SIZE', 10485760) / 1024 / 1024:.1f}MB"
        },
        "documentation": "/docs",
        "endpoints": {
            "health": "/health",
            "api_key_management": f"{settings.API_V1_PREFIX}/admin/api-keys",
            "users": f"{settings.API_V1_PREFIX}/users",
            "balances": f"{settings.API_V1_PREFIX}/balances",
            "transactions": f"{settings.API_V1_PREFIX}/transactions",
            "currencies": f"{settings.API_V1_PREFIX}/currencies",
            "trades": f"{settings.API_V1_PREFIX}/trades",
            "trading_pairs": "/api/v1/trading-pairs"
        },
        "api_key_scopes": {
            "read_only": "Read access to user data",
            "read_write": "Read and write access to user data",
            "inherit": "Inherit user permissions",
            "full_access": "Full access (admin users only)"
        },
        "getting_started": {
            "step_1": "Contact admin to create your API key",
            "step_2": "Include API key in Authorization header: 'Bearer <api_key>'",
            "step_3": "Make requests to protected endpoints",
            "example": f"curl -H 'Authorization: Bearer <api_key>' {settings.API_V1_PREFIX}/balances"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        app.state.database.test_connection()

        return {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "authentication": "API Key Authentication",
            "database": {
                "status": "connected",
                "type": settings.DATABASE_TYPE
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": str(e)
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True if settings.DEBUG else False,
        log_level=settings.LOG_LEVEL.lower()
    )


# Include basic trading pairs routes
app.include_router(
    trading_pairs.router,
    prefix=f"{settings.API_V1_PREFIX}/trading-pairs",
    tags=["Trading Pairs Basic"]
)
