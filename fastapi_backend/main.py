#!/usr/bin/env python3
"""
Balance Tracking System - FastAPI Backend
Updated main application with JWT authentication support
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from datetime import datetime
import logging

from api.config import settings
from api.database import DatabaseManager
from api.routes import users, transactions, balances, currencies
# NEW: Import authentication routes
from api.auth_routes import router as auth_router

# Setup logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("🚀 Starting Balance Tracking API with Authentication...")

    # Initialize database
    db = DatabaseManager(settings.DATABASE_URL)
    try:
        db.connect()
        app.state.database = db
        logger.info("✅ Database initialized")

        # Log authentication configuration
        logger.info(f"✅ JWT Authentication enabled")
        logger.info(f"✅ Token expiration: {settings.JWT_EXPIRE_MINUTES} minutes")
        logger.info(f"✅ Environment: {settings.ENVIRONMENT}")
        logger.info(f"✅ Email verification: {'Required' if getattr(settings, 'EMAIL_ENABLED', False) else 'Disabled'}")

    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise

    yield

    # Cleanup
    logger.info("🛑 Shutting down...")
    if hasattr(app.state, 'database'):
        app.state.database.disconnect()


# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="REST API for managing user balances, transactions, and trading with JWT authentication",
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware with secure settings
cors_origins = getattr(settings, 'CORS_ORIGINS', ["http://localhost:3000"])
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
)

# Include authentication routes (NEW)
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
    """API root endpoint with authentication info"""
    return {
        "message": f"{settings.PROJECT_NAME} API",
        "version": settings.VERSION,
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "authentication": "JWT Bearer Token",
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
    """Enhanced health check endpoint with authentication status"""
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


if __name__ == "__main__":
    import uvicorn

    print(f"🚀 Starting {settings.PROJECT_NAME}...")
    print("📚 API Documentation: http://localhost:8000/docs")
    print("🏥 Health Check: http://localhost:8000/health")
    print("🔐 Authentication endpoints available at /api/v1/auth/*")
    print(f"🔑 JWT Token expiration: {settings.JWT_EXPIRE_MINUTES} minutes")

    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
