#!/usr/bin/env python3
"""
Balance Tracking System - FastAPI Backend
Updated main application with trading pairs support
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from datetime import datetime
import logging

from api.config import settings
from api.database import DatabaseManager
from api.routes import users, transactions, balances, currencies, trading_pairs
from api.routes import trades  # NEW: Import trades route

# Setup logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
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

    yield

    # Cleanup
    logger.info("🛑 Shutting down...")
    if hasattr(app.state, 'database'):
        app.state.database.disconnect()


# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="REST API for managing user balances, transactions, and trading",
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
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

# NEW: Include trading pairs router
app.include_router(
    trading_pairs.router,
    prefix=f"{settings.API_V1_PREFIX}/trading-pairs",
    tags=["Trading Pairs"]
)

# NEW: Include trades router
app.include_router(
    trades.router,
    prefix=f"{settings.API_V1_PREFIX}/trades",
    tags=["Trades"]
)


# Root endpoints
@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "message": f"{settings.PROJECT_NAME} API",
        "version": settings.VERSION,
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "documentation": "/docs",
        "endpoints": {
            "health": "/health",
            "users": f"{settings.API_V1_PREFIX}/users",
            "balances": f"{settings.API_V1_PREFIX}/balances",
            "transactions": f"{settings.API_V1_PREFIX}/transactions",
            "currencies": f"{settings.API_V1_PREFIX}/currencies",
            "trading_pairs": f"{settings.API_V1_PREFIX}/trading-pairs",  # NEW
            "trades": f"{settings.API_V1_PREFIX}/trades"  # NEW
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        db = app.state.database
        db.test_connection()
        stats = db.get_stats()

        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "database": {
                "status": "connected",
                "type": "sqlite",
                "stats": stats
            },
            "version": settings.VERSION
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
    print("🔗 Trading Pairs: http://localhost:8000/api/v1/trading-pairs")
    print("💱 Trades: http://localhost:8000/api/v1/trades")

    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
