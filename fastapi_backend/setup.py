#!/usr/bin/env python3
"""
Modular FastAPI Structure - File Creation Script
Creates organized, production-ready FastAPI structure
"""

import os
from pathlib import Path

def create_modular_structure():
    """Create the modular FastAPI structure with all files"""
    
    # Create directory structure
    base_dir = Path(".")
    
    # Create directories
    api_dir = base_dir / "api"
    routes_dir = api_dir / "routes"
    
    api_dir.mkdir(exist_ok=True)
    routes_dir.mkdir(exist_ok=True)
    
    # File contents
    files = {
        "api/__init__.py": "",
        
        "api/config.py": '''"""
Configuration settings for the Balance Tracking API
"""

import os
from pathlib import Path


class Settings:
    """Application settings and configuration"""
    
    # Database configuration
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///balance_tracker.db")
    DATABASE_TYPE: str = "sqlite"
    
    # Security settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", "30"))
    
    # API settings
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "Balance Tracking System"
    VERSION: str = "1.0.0"
    
    # Rate limiting
    RATE_LIMIT_REQUESTS: int = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
    RATE_LIMIT_WINDOW: int = int(os.getenv("RATE_LIMIT_WINDOW", "60"))
    
    # Pagination defaults
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100
    
    # Transaction settings
    MIN_TRANSACTION_AMOUNT: float = 0.00000001
    MAX_TRANSACTION_AMOUNT: float = 999999999999.99
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"

# Global settings instance
settings = Settings()
''',

        "api/models.py": '''"""
Pydantic models for request/response validation
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from decimal import Decimal
from datetime import datetime
from enum import Enum


class TransactionType(str, Enum):
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    TRADE_BUY = "trade_buy"
    TRADE_SELL = "trade_sell"
    TRANSFER_IN = "transfer_in"
    TRANSFER_OUT = "transfer_out"
    FEE = "fee"
    ADJUSTMENT = "adjustment"


class TransactionStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


# Request Models
class TransactionRequest(BaseModel):
    """Base transaction request model"""
    username: str = Field(..., min_length=3, max_length=50)
    amount: Decimal = Field(..., gt=0, description="Transaction amount (must be positive)")
    currency_code: str = Field(..., min_length=3, max_length=4)
    description: Optional[str] = Field(None, max_length=500)
    external_reference: Optional[str] = Field(None, max_length=255)
    
    @validator('amount')
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError('Amount must be positive')
        if v > Decimal('999999999999.99'):
            raise ValueError('Amount exceeds maximum limit')
        return v
    
    @validator('currency_code')
    def validate_currency_code(cls, v):
        return v.upper().strip()
    
    @validator('username')
    def validate_username(cls, v):
        return v.strip()


class DepositRequest(TransactionRequest):
    """Deposit transaction request"""
    force_create_balance: bool = Field(False, description="Create balance if it doesn't exist")


class WithdrawalRequest(TransactionRequest):
    """Withdrawal transaction request"""
    allow_partial: bool = Field(False, description="Allow partial withdrawal if insufficient funds")


# Response Models
class TransactionResponse(BaseModel):
    """Transaction response model"""
    success: bool
    message: str
    transaction_id: str
    transaction_type: str
    status: str
    amount: Decimal
    currency_code: str
    balance_before: Decimal
    balance_after: Decimal
    fee_amount: Optional[Decimal] = None
    description: Optional[str] = None
    external_reference: Optional[str] = None
    created_at: datetime
    processed_at: Optional[datetime] = None
    
    class Config:
        json_encoders = {
            Decimal: str
        }


class BalanceResponse(BaseModel):
    """Balance response model"""
    currency_code: str
    currency_name: str
    currency_symbol: Optional[str]
    total_balance: Decimal
    available_balance: Decimal
    locked_balance: Decimal
    is_fiat: bool
    updated_at: datetime
    
    class Config:
        json_encoders = {
            Decimal: str
        }


class UserResponse(BaseModel):
    """User response model"""
    id: str
    username: str
    email: str
    first_name: Optional[str]
    last_name: Optional[str]
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime]


class CurrencyResponse(BaseModel):
    """Currency response model"""
    code: str
    name: str
    symbol: Optional[str]
    decimal_places: int
    is_fiat: bool
    is_active: bool


# API Response Wrappers
class ApiResponse(BaseModel):
    """Base API response"""
    success: bool = True
    message: str = "Operation completed successfully"
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class DataResponse(ApiResponse):
    """Response with data"""
    data: Any


class ListResponse(ApiResponse):
    """Response with list data and pagination"""
    data: List[Any]
    pagination: Optional[Dict[str, Any]] = None
''',

        "api/database.py": '''"""
Database management for the Balance Tracking API
"""

import sqlite3
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from contextlib import contextmanager
from decimal import Decimal

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Database connection and operation manager"""
    
    def __init__(self, database_url: str = "balance_tracker.db"):
        self.database_url = database_url
        self.connection = None
        
    def connect(self):
        """Establish database connection"""
        try:
            # Handle both file path and sqlite:/// URL format
            if self.database_url.startswith("sqlite:///"):
                db_path = self.database_url.replace("sqlite:///", "")
            else:
                db_path = self.database_url
            
            if not Path(db_path).exists():
                raise FileNotFoundError(f"Database file not found: {db_path}")
            
            self.connection = sqlite3.connect(db_path, check_same_thread=False)
            self.connection.row_factory = sqlite3.Row
            self.connection.execute("PRAGMA foreign_keys = ON")
            
            logger.info(f"✅ Connected to SQLite database: {db_path}")
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to database: {e}")
            raise
    
    def disconnect(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            self.connection = None
            logger.info("Database connection closed")
    
    def test_connection(self):
        """Test database connection"""
        if not self.connection:
            raise Exception("No database connection")
        
        cursor = self.connection.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        cursor.close()
        
        if not result:
            raise Exception("Database connection test failed")
        
        return True
    
    @contextmanager
    def get_cursor(self):
        """Get database cursor with automatic cleanup"""
        cursor = self.connection.cursor()
        try:
            yield cursor
        finally:
            cursor.close()
    
    def execute_query(self, query: str, params: tuple = None) -> List[Dict]:
        """Execute a SELECT query and return results"""
        with self.get_cursor() as cursor:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            results = []
            for row in cursor.fetchall():
                results.append(dict(row))
            
            return results
    
    def execute_command(self, command: str, params: tuple = None) -> int:
        """Execute an INSERT/UPDATE/DELETE command"""
        with self.get_cursor() as cursor:
            if params:
                cursor.execute(command, params)
            else:
                cursor.execute(command)
            
            self.connection.commit()
            return cursor.rowcount
    
    def execute_transaction(self, commands: List[tuple]) -> bool:
        """Execute multiple commands in a transaction"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("BEGIN TRANSACTION")
                
                for command, params in commands:
                    if params:
                        cursor.execute(command, params)
                    else:
                        cursor.execute(command)
                
                self.connection.commit()
                return True
                
        except Exception as e:
            self.connection.rollback()
            logger.error(f"Transaction failed: {e}")
            raise
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        stats = {}
        tables = ["users", "currencies", "user_balances", "transactions", "trades"]
        
        for table in tables:
            try:
                result = self.execute_query(f"SELECT COUNT(*) as count FROM {table}")
                stats[table] = result[0]["count"] if result else 0
            except:
                stats[table] = 0
        
        return stats
''',

        "api/dependencies.py": '''"""
Dependency injection for FastAPI
"""

from fastapi import Depends, HTTPException, status, Request
from api.database import DatabaseManager
from api.config import settings
import logging

logger = logging.getLogger(__name__)


def get_database(request: Request) -> DatabaseManager:
    """Get database instance from app state"""
    if not hasattr(request.app.state, 'database'):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not available"
        )
    
    return request.app.state.database


def validate_user_exists(username: str, db: DatabaseManager = Depends(get_database)):
    """Validate that a user exists and is active"""
    query = "SELECT id, username, is_active FROM users WHERE username = ?"
    results = db.execute_query(query, (username,))
    
    if not results:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{username}' not found"
        )
    
    user = results[0]
    if not user['is_active']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User '{username}' is not active"
        )
    
    return user


def validate_currency_exists(currency_code: str, db: DatabaseManager = Depends(get_database)):
    """Validate that a currency exists and is active"""
    query = "SELECT code, name, is_active FROM currencies WHERE code = ?"
    results = db.execute_query(query, (currency_code.upper(),))
    
    if not results:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Currency '{currency_code}' not found"
        )
    
    currency = results[0]
    if not currency['is_active']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Currency '{currency_code}' is not active"
        )
    
    return currency


def get_pagination_params(page: int = 1, page_size: int = 20):
    """Get pagination parameters with validation"""
    if page < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Page number must be 1 or greater"
        )
    
    if page_size < 1 or page_size > settings.MAX_PAGE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Page size must be between 1 and {settings.MAX_PAGE_SIZE}"
        )
    
    offset = (page - 1) * page_size
    return {"page": page, "page_size": page_size, "offset": offset}
''',

        "api/routes/__init__.py": "",

        "new_main.py": '''#!/usr/bin/env python3
"""
Balance Tracking System - FastAPI Backend
Modular main application
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from datetime import datetime
import logging

from api.config import settings
from api.database import DatabaseManager
from api.routes import users, transactions, balances, currencies

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
    description="REST API for managing user balances and transactions",
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
            "currencies": f"{settings.API_V1_PREFIX}/currencies"
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
    
    uvicorn.run(
        "new_main:app",
        host="127.0.0.1",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
'''
    }
    
    # Create all files
    for file_path, content in files.items():
        full_path = base_dir / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content)
        print(f"✅ Created: {full_path}")
    
    print(f"""
🎉 Modular FastAPI structure created!

📁 Structure:
{base_dir}/
├── api/
│   ├── __init__.py
│   ├── config.py           # Settings and configuration
│   ├── models.py           # Pydantic models
│   ├── database.py         # Database operations
│   ├── dependencies.py     # Dependency injection
│   └── routes/
│       └── __init__.py
├── new_main.py             # New modular main application
└── main.py                 # Your existing working app

🔧 Next Steps:
1. Create the route files (transactions.py, balances.py, etc.)
2. Test the new modular structure
3. Compare with your working main.py

📚 The new structure provides:
- Better organization and maintainability
- Separation of concerns
- Easier testing and debugging
- Production-ready architecture
""")

if __name__ == "__main__":
    create_modular_structure()
