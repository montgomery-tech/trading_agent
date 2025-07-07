#!/usr/bin/env python3
"""
Balance Tracking System - FastAPI Backend
Simplified working version for immediate testing
"""

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from pathlib import Path
from datetime import datetime
import sqlite3
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SimpleDatabase:
    """Simple database manager for initial testing"""

    def __init__(self, db_path="balance_tracker.db"):
        self.db_path = db_path
        self.connection = None

    def connect(self):
        if not Path(self.db_path).exists():
            raise FileNotFoundError(f"Database file not found: {self.db_path}")

        self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        logger.info("✅ Database connected")

    def disconnect(self):
        if self.connection:
            self.connection.close()
            logger.info("Database disconnected")

    def test_connection(self):
        cursor = self.connection.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM users")
        result = cursor.fetchone()
        cursor.close()
        return result['count'] if result else 0

    def get_stats(self):
        cursor = self.connection.cursor()
        stats = {}

        tables = ["users", "currencies", "user_balances", "transactions"]
        for table in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
                result = cursor.fetchone()
                stats[table] = result['count'] if result else 0
            except:
                stats[table] = 0

        cursor.close()
        return stats


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("🚀 Starting Balance Tracking API...")

    # Initialize database
    db = SimpleDatabase()
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
    title="Balance Tracking System API",
    description="REST API for managing user balances and transactions",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "message": "Balance Tracking System API",
        "version": "1.0.0",
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "documentation": "/docs",
        "endpoints": {
            "health": "/health",
            "users": "/api/v1/users",
            "balances": "/api/v1/balances",
            "transactions": "/api/v1/transactions",
            "currencies": "/api/v1/currencies"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        db = app.state.database
        user_count = db.test_connection()
        stats = db.get_stats()

        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "database": {
                "status": "connected",
                "type": "sqlite",
                "stats": stats
            },
            "version": "1.0.0"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service unhealthy: {str(e)}"
        )


# Basic API endpoints
@app.get("/api/v1/users/{username}")
async def get_user(username: str):
    """Get user by username"""
    try:
        db = app.state.database
        cursor = db.connection.cursor()

        cursor.execute("""
            SELECT id, username, email, first_name, last_name,
                   is_active, is_verified, created_at
            FROM users WHERE username = ? AND is_active = 1
        """, (username,))

        user = cursor.fetchone()
        cursor.close()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User '{username}' not found"
            )

        return dict(user)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving user: {str(e)}"
        )


@app.get("/api/v1/balances/user/{username}")
async def get_user_balances(username: str):
    """Get balances for a user"""
    try:
        db = app.state.database
        cursor = db.connection.cursor()

        # First get user ID
        cursor.execute("SELECT id FROM users WHERE username = ? AND is_active = 1", (username,))
        user = cursor.fetchone()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User '{username}' not found"
            )

        # Get balances
        cursor.execute("""
            SELECT ub.currency_code, ub.total_balance, ub.available_balance,
                   ub.locked_balance, ub.updated_at, c.name, c.symbol, c.is_fiat
            FROM user_balances ub
            JOIN currencies c ON ub.currency_code = c.code
            WHERE ub.user_id = ?
            ORDER BY c.is_fiat DESC, ub.total_balance DESC
        """, (user['id'],))

        balances = cursor.fetchall()
        cursor.close()

        return [dict(balance) for balance in balances]

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving balances: {str(e)}"
        )


@app.get("/api/v1/currencies")
async def get_currencies(active_only: bool = True):
    """Get available currencies"""
    try:
        db = app.state.database
        cursor = db.connection.cursor()

        query = "SELECT code, name, symbol, decimal_places, is_fiat, is_active FROM currencies"
        if active_only:
            query += " WHERE is_active = 1"
        query += " ORDER BY is_fiat DESC, code"

        cursor.execute(query)
        currencies = cursor.fetchall()
        cursor.close()

        return [dict(currency) for currency in currencies]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving currencies: {str(e)}"
        )


@app.post("/api/v1/transactions/deposit")
async def create_deposit(deposit_data: dict):
    """Create a deposit transaction"""
    try:
        username = deposit_data.get('username')
        amount = float(deposit_data.get('amount', 0))
        currency_code = deposit_data.get('currency_code', '').upper()
        description = deposit_data.get('description')

        if not username or amount <= 0 or not currency_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid request data"
            )

        db = app.state.database
        cursor = db.connection.cursor()

        # Get user
        cursor.execute("SELECT id FROM users WHERE username = ? AND is_active = 1", (username,))
        user = cursor.fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Get currency
        cursor.execute("SELECT code FROM currencies WHERE code = ? AND is_active = 1", (currency_code,))
        currency = cursor.fetchone()
        if not currency:
            raise HTTPException(status_code=404, detail="Currency not found")

        # Get current balance
        cursor.execute("""
            SELECT total_balance FROM user_balances
            WHERE user_id = ? AND currency_code = ?
        """, (user['id'], currency_code))

        current_balance_row = cursor.fetchone()
        current_balance = float(current_balance_row['total_balance']) if current_balance_row else 0.0
        new_balance = current_balance + amount

        # Create transaction and update balance
        import uuid
        transaction_id = str(uuid.uuid4())

        cursor.execute("""
            INSERT INTO transactions (
                id, user_id, transaction_type, status, amount, currency_code,
                balance_before, balance_after, description, created_at, processed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, (transaction_id, user['id'], 'deposit', 'completed', amount, currency_code,
              current_balance, new_balance, description))

        # Update or create balance
        if current_balance_row:
            cursor.execute("""
                UPDATE user_balances
                SET total_balance = ?, available_balance = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND currency_code = ?
            """, (new_balance, new_balance, user['id'], currency_code))
        else:
            balance_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO user_balances (id, user_id, currency_code, total_balance, available_balance, locked_balance)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (balance_id, user['id'], currency_code, new_balance, new_balance, 0))

        db.connection.commit()
        cursor.close()

        return {
            "success": True,
            "message": f"Deposit of {amount} {currency_code} completed successfully",
            "transaction_id": transaction_id,
            "new_balance": new_balance
        }

    except HTTPException:
        raise
    except Exception as e:
        db.connection.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing deposit: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn

    print("🚀 Starting Balance Tracking API...")
    print("📚 API Documentation: http://localhost:8000/docs")
    print("🏥 Health Check: http://localhost:8000/health")

    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )
