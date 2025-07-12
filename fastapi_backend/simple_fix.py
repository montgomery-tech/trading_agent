#!/usr/bin/env python3
"""
Simple fix for model import issues
Creates proper __init__.py files with required models
"""

import os
from pathlib import Path

def create_init_files():
    """Create __init__.py files for proper package structure"""
    
    # Create empty __init__.py files
    init_files = [
        'api/__init__.py',
        'api/models/__init__.py', 
        'api/services/__init__.py',
        'api/routes/__init__.py'
    ]
    
    for file_path in init_files:
        Path(file_path).touch()
        print(f"✅ Created {file_path}")

def create_models_init():
    """Create api/models/__init__.py with essential models"""
    
    models_init_content = '''"""
Models package - Essential models for FastAPI routes
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from enum import Enum

# Essential response models that the routes expect
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

class CurrencyResponse(BaseModel):
    """Currency response model"""
    code: str
    name: str
    symbol: Optional[str]
    decimal_places: int
    is_fiat: bool
    is_active: bool

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

# Transaction models
class TransactionType(str, Enum):
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    TRADE_BUY = "trade_buy"
    TRADE_SELL = "trade_sell"

class TransactionStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class TransactionRequest(BaseModel):
    """Base transaction request model"""
    username: str = Field(..., min_length=3, max_length=50)
    amount: Decimal = Field(..., gt=0)
    currency_code: str = Field(..., min_length=3, max_length=4)
    description: Optional[str] = Field(None, max_length=500)

class DepositRequest(TransactionRequest):
    """Deposit transaction request"""
    force_create_balance: bool = Field(False)

class WithdrawalRequest(TransactionRequest):
    """Withdrawal transaction request"""
    allow_partial: bool = Field(False)

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
    created_at: datetime

    class Config:
        json_encoders = {
            Decimal: str
        }

# Import user admin models if they exist
try:
    from .user_admin import *
except ImportError:
    pass
'''
    
    with open('api/models/__init__.py', 'w') as f:
        f.write(models_init_content)
    
    print("✅ Created api/models/__init__.py with essential models")

def main():
    """Run the fix"""
    print("🔧 Fixing Model Import Issues")
    print("=" * 30)
    
    create_init_files()
    create_models_init()
    
    print("\n🎉 Fix completed!")
    print("✅ Your FastAPI server should now start without import errors")
    print("\n🚀 Try running: python3 main.py")

if __name__ == "__main__":
    main()
