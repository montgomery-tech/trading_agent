"""
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
