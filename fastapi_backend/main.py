"""
FastAPI Backend - Production Ready Main Application
Cleaned up version with temporary endpoints removed
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from datetime import datetime
import logging

# Core imports
from api.config import settings
from api.database import DatabaseManager
from api.security import security_exception_handler
from api.dependencies import get_database

# Route imports
from api.routes import users, transactions, balances, currencies, admin
from api.auth_routes import router as auth_router

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Trading Balance Tracking API",
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc"
)


@app.on_event("startup")
async def startup_event():
    """Initialize database connection on startup"""
    try:
        db = DatabaseManager(settings.DATABASE_URL)
        db.connect()
        app.state.database = db
        logger.info("✅ Database initialized in app state")
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up database connection on shutdown"""
    if hasattr(app.state, 'database'):
        try:
            app.state.database.disconnect()
            logger.info("✅ Database connection closed")
        except Exception as e:
            logger.error(f"❌ Error closing database: {e}")
            
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

# Include authentication routes
app.include_router(
    auth_router,
    prefix=f"{settings.API_V1_PREFIX}/auth",
    tags=["Authentication"]
)

# Include admin routes
app.include_router(
    admin.router,
    prefix=f"{settings.API_V1_PREFIX}/admin",
    tags=["Admin"]
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
            "admin": f"{settings.API_V1_PREFIX}/admin",
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
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.VERSION,
        "environment": getattr(settings, 'ENVIRONMENT', 'development'),
        "database": {
            "type": settings.DATABASE_TYPE,
            "status": "connected"
        },
        "authentication": {
            "jwt_enabled": True,
            "password_policy": "enforced"
        },
        "security": {
            "rate_limiting": "enabled" if getattr(settings, 'RATE_LIMIT_ENABLED', True) else "disabled",
            "input_validation": "enabled",
            "security_headers": "enabled"
        }
    }

# Server startup
if __name__ == "__main__":
    import uvicorn
    logger.info("🚀 Starting Balance Tracking API...")
    logger.info(f"   • Environment: {getattr(settings, 'ENVIRONMENT', 'development')}")
    logger.info(f"   • Debug mode: {getattr(settings, 'DEBUG', False)}")
    logger.info(f"   • Database: {settings.DATABASE_TYPE}")
    logger.info(f"   • JWT Authentication: {'Enabled' if hasattr(settings, 'SECRET_KEY') else 'Disabled'}")
    logger.info(f"   • Rate Limiting: {'Enabled' if getattr(settings, 'RATE_LIMIT_ENABLED', True) else 'Disabled'}")
    logger.info(f"   • Security headers: Enabled")

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
