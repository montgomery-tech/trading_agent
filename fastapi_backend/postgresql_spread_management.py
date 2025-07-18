#!/usr/bin/env python3
"""
PostgreSQL-compatible spread management routes
"""

from fastapi import APIRouter, HTTPException, status, Depends
from typing import List, Optional
from decimal import Decimal
from pydantic import BaseModel, Field
import logging

from api.models import DataResponse, ListResponse
from api.dependencies import get_database
from api.database import DatabaseManager

logger = logging.getLogger(__name__)

# Model for spread updates
class TradingPairSpreadUpdate(BaseModel):
    spread_percentage: float = Field(..., ge=0, le=1, description="Spread percentage (0-1)")

router = APIRouter()


@router.get("/spreads", response_model=ListResponse)
async def get_all_spreads(
    db: DatabaseManager = Depends(get_database)
):
    """Get spread configuration for all trading pairs"""
    try:
        query = """
            SELECT tp.id, tp.symbol, tp.base_currency, tp.quote_currency,
                   tp.spread_percentage, tp.min_trade_amount, tp.max_trade_amount,
                   tp.is_active
            FROM trading_pairs tp
            WHERE tp.is_active = true
            ORDER BY tp.symbol
        """
        
        results = db.execute_query(query)
        
        trading_pairs = []
        for row in results:
            pair = {
                "id": row['id'],
                "symbol": row['symbol'],
                "base_currency": row['base_currency'],
                "quote_currency": row['quote_currency'],
                "spread_percentage": float(row['spread_percentage']),
                "spread_percentage_display": f"{float(row['spread_percentage']) * 100:.2f}%",
                "min_trade_amount": str(row['min_trade_amount']),
                "max_trade_amount": str(row['max_trade_amount']) if row['max_trade_amount'] else None,
                "is_active": bool(row['is_active'])
            }
            trading_pairs.append(pair)
        
        return ListResponse(
            message=f"Retrieved {len(trading_pairs)} trading pairs with spreads",
            data=trading_pairs
        )
        
    except Exception as e:
        logger.error(f"Error retrieving spreads: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving spreads: {str(e)}"
        )


@router.get("/spreads/{symbol:path}", response_model=DataResponse) 
async def get_pair_spread(
    symbol: str,
    db: DatabaseManager = Depends(get_database)
):
    """Get spread configuration for a specific trading pair"""
    try:
        # Handle both BTC/USD and BTCUSD formats
        symbol_upper = symbol.upper()
        
        # Try both with and without slash
        if "/" in symbol_upper:
            symbol_with_slash = symbol_upper
            symbol_without_slash = symbol_upper.replace("/", "")
        else:
            symbol_without_slash = symbol_upper
            # Assume 3-letter base currency for formatting
            if len(symbol_upper) >= 6:
                symbol_with_slash = f"{symbol_upper[:3]}/{symbol_upper[3:]}"
            else:
                symbol_with_slash = symbol_upper
        
        query = """
            SELECT tp.id, tp.symbol, tp.base_currency, tp.quote_currency,
                   tp.spread_percentage, tp.min_trade_amount, tp.max_trade_amount,
                   tp.is_active
            FROM trading_pairs tp
            WHERE tp.symbol = %s OR tp.symbol = %s
        """
        
        results = db.execute_query(query, (symbol_with_slash, symbol_without_slash))
        
        if not results:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Trading pair {symbol} not found"
            )
        
        row = results[0]
        pair_data = {
            "id": row['id'],
            "symbol": row['symbol'],
            "base_currency": row['base_currency'],
            "quote_currency": row['quote_currency'],
            "spread_percentage": float(row['spread_percentage']),
            "spread_percentage_display": f"{float(row['spread_percentage']) * 100:.2f}%",
            "min_trade_amount": str(row['min_trade_amount']),
            "max_trade_amount": str(row['max_trade_amount']) if row['max_trade_amount'] else None,
            "is_active": bool(row['is_active'])
        }
        
        return DataResponse(
            message=f"Spread configuration for {symbol}",
            data=pair_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving spread for {symbol}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving spread: {str(e)}"
        )


@router.put("/spreads/{symbol}", response_model=DataResponse)
async def update_pair_spread(
    symbol: str,
    spread_update: TradingPairSpreadUpdate,
    db: DatabaseManager = Depends(get_database)
):
    """Update spread configuration for a trading pair"""
    try:
        spread_decimal = spread_update.spread_percentage
        if spread_decimal > 1:
            spread_decimal = spread_decimal / 100
        
        if spread_decimal < 0 or spread_decimal > 0.1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Spread must be between 0% and 10%"
            )
        
        # Check if trading pair exists
        check_query = "SELECT id FROM trading_pairs WHERE symbol = %s"
        result = db.execute_query(check_query, (symbol.upper(),))
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Trading pair {symbol} not found"
            )
        
        # Update spread
        update_query = """
            UPDATE trading_pairs 
            SET spread_percentage = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE symbol = %s
        """
        
        affected_rows = db.execute_update(update_query, (float(spread_decimal), symbol.upper()))
        
        if affected_rows == 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update spread"
            )
        
        return await get_pair_spread(symbol, db)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating spread for {symbol}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating spread: {str(e)}"
        )
