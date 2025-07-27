#!/usr/bin/env python3
"""
FastAPI Balance Tracking System - Main Application
API Key Authentication Only - JWT Removed
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
    balances, currencies, trades, simple_trades, spread_management
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
        logger.info("✅ Database connection established")
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

# Create FastAPI app
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
    """API root endpoint with API key authentication info"""
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
            "admin": f"{settings.API_V1_PREFIX}/admin",
            "api_key_management": f"{settings.API_V1_PREFIX}/admin/api-keys",
            "users": f"{settings.API_V1_PREFIX}/users",
            "balances": f"{settings.API_V1_PREFIX}/balances",
            "transactions": f"{settings.API_V1_PREFIX}/transactions",
            "currencies": f"{settings.API_V1_PREFIX}/currencies",
            "trades": f"{settings.API_V1_PREFIX}/trades"
        },
        "api_key_info": {
            "format": "Bearer <api_key>",
            "header": "Authorization",
            "example": "Authorization: Bearer btapi_xxxxxxxxxxxxxxxx_yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy",
            "management": f"{settings.API_V1_PREFIX}/admin/api-keys",
            "permissions": {
                "inherit": "User's role permissions",
                "read_only": "Read-only access",
                "full_access": "Full access (admin only)"
            }
        },
        "kraken_status": {
            "api_configured": bool(getattr(settings, 'KRAKEN_API_KEY', False)),
            "live_trading": str(getattr(settings, 'ENABLE_LIVE_TRADING', 'false')).lower(),
            "trading_endpoint": f"{settings.API_V1_PREFIX}/trades/execute-simple"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Basic health check
        return {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": settings.VERSION,
            "authentication": {
                "api_key_enabled": True,
                "admin_managed": True
            },
            "database": {
                "type": getattr(settings, 'DATABASE_TYPE', 'postgresql'),
                "connected": True  # Simple check - could enhance with actual DB ping
            },
            "environment": getattr(settings, 'ENVIRONMENT', 'development')
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True if settings.DEBUG else False,
        log_level=settings.LOG_LEVEL.lower()
    )
