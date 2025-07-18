#!/usr/bin/env python3
"""
Enhanced Trade Models with Spread Support
Extends existing models to include spread-related fields
"""

from typing import Optional
from decimal import Decimal
from pydantic import BaseModel, Field

from api.models import TradeResponse as BaseTradeResponse, TradeSimulationResponse as BaseTradeSimulationResponse


class EnhancedTradeResponse(BaseTradeResponse):
    """
    Enhanced trade response that includes spread information
    
    Inherits all fields from BaseTradeResponse and adds spread-specific fields
    """
    # Market execution details (optional - can be hidden from client)
    execution_price: Optional[Decimal] = Field(None, description="Actual market execution price")
    client_price: Optional[Decimal] = Field(None, description="Price shown to client (with spread)")
    spread_amount: Optional[Decimal] = Field(None, description="Total spread amount collected")
    spread_percentage: Optional[float] = Field(None, description="Spread percentage applied")
    
    class Config:
        json_encoders = {
            Decimal: str
        }
        schema_extra = {
            "example": {
                "success": True,
                "message": "Trade executed successfully: buy 0.01 BTC/USD",
                "trade_id": "123e4567-e89b-12d3-a456-426614174000",
                "symbol": "BTC/USD",
                "side": "buy",
                "amount": "0.01",
                "price": "51000.00",  # Client price
                "total_value": "510.00",
                "fee_amount": "1.275",
                "fee_currency": "USD",
                "status": "completed",
                "base_currency_balance_before": "1.50",
                "base_currency_balance_after": "1.51",
                "quote_currency_balance_before": "1000.00",
                "quote_currency_balance_after": "488.725",
                "execution_price": "50000.00",  # Market price
                "client_price": "51000.00",     # With 2% spread
                "spread_amount": "10.00",       # $1000 spread on 0.01 BTC
                "spread_percentage": 2.0
            }
        }


class EnhancedTradeSimulationResponse(BaseTradeSimulationResponse):
    """
    Enhanced trade simulation response with spread details
    """
    # Spread information for transparency in simulation
    execution_price: Optional[Decimal] = Field(None, description="Market execution price")
    client_price: Optional[Decimal] = Field(None, description="Your price (with spread)")
    spread_amount: Optional[Decimal] = Field(None, description="Spread cost/revenue")
    spread_percentage: Optional[float] = Field(None, description="Spread percentage")
    
    class Config:
        json_encoders = {
            Decimal: str
        }
        schema_extra = {
            "example": {
                "success": True,
                "message": "Trade simulation for buy 0.01 BTC/USD",
                "symbol": "BTC/USD",
                "side": "buy",
                "amount": "0.01",
                "estimated_price": "51000.00",  # Client sees this
                "estimated_total": "510.00",
                "estimated_fee": "1.275",
                "fee_currency": "USD",
                "current_balances": {
                    "BTC": "1.50",
                    "USD": "1000.00"
                },
                "projected_balances": {
                    "BTC": "1.51",
                    "USD": "488.725"
                },
                "validation_errors": [],
                "warnings": [],
                "execution_price": "50000.00",
                "client_price": "51000.00",
                "spread_amount": "10.00",
                "spread_percentage": 2.0
            }
        }


class TradingPairSpreadUpdate(BaseModel):
    """Model for updating trading pair spread"""
    spread_percentage: Decimal = Field(..., ge=0, le=1, description="Spread percentage (0-100%)")
    
    class Config:
        schema_extra = {
            "example": {
                "spread_percentage": 0.025  # 2.5%
            }
        }


class TradingPairWithSpread(BaseModel):
    """Trading pair information including spread"""
    id: str
    symbol: str
    base_currency: str
    quote_currency: str
    spread_percentage: Decimal
    min_trade_amount: Decimal
    max_trade_amount: Optional[Decimal]
    is_active: bool
    
    class Config:
        json_encoders = {
            Decimal: str
        }
