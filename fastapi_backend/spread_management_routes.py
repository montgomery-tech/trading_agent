#!/usr/bin/env python3
"""
Spread Management Routes
Endpoints for configuring and managing trading pair spreads
"""

from fastapi import APIRouter, HTTPException, status, Depends
from typing import List
from decimal import Decimal
import logging

from api.models import DataResponse, ListResponse
from api.dependencies import get_database, get_current_user
from api.database import DatabaseManager
from enhanced_trade_models import TradingPairSpreadUpdate, TradingPairWithSpread

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/spreads", response_model=ListResponse)
async def get_all_spreads(
    db: DatabaseManager = Depends(get_database),
    current_user: dict = Depends(get_current_user)
):
    """
    Get spread configuration for all trading pairs
    
    Requires authentication. Admin users see all spreads.
    Regular users only see spreads for active pairs.
    """
    try:
        # Check if user is admin
        is_admin = current_user.get('role') == 'admin'
        
        query = """
            SELECT tp.id, tp.symbol, tp.base_currency, tp.quote_currency,
                   tp.spread_percentage, tp.min_trade_amount, tp.max_trade_amount,
                   tp.is_active
            FROM trading_pairs tp
        """
        
        params = []
        if not is_admin:
            query += " WHERE tp.is_active = 1"
        
        query += " ORDER BY tp.symbol"
        
        results = db.execute_query(query, params)
        
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


@router.get("/spreads/{symbol}", response_model=DataResponse)
async def get_pair_spread(
    symbol: str,
    db: DatabaseManager = Depends(get_database)
):
    """
    Get spread configuration for a specific trading pair
    
    Args:
        symbol: Trading pair symbol (e.g., 'BTC/USD')
    """
    try:
        query = """
            SELECT tp.id, tp.symbol, tp.base_currency, tp.quote_currency,
                   tp.spread_percentage, tp.min_trade_amount, tp.max_trade_amount,
                   tp.is_active
            FROM trading_pairs tp
            WHERE tp.symbol = ?
        """
        
        results = db.execute_query(query, (symbol.upper(),))
        
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
    db: DatabaseManager = Depends(get_database),
    current_user: dict = Depends(get_current_user)
):
    """
    Update spread configuration for a trading pair
    
    Requires admin role.
    
    Args:
        symbol: Trading pair symbol (e.g., 'BTC/USD')
        spread_update: New spread configuration
    """
    try:
        # Check admin permission
        if current_user.get('role') != 'admin':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can update spreads"
            )
        
        # Validate spread percentage (convert to decimal if needed)
        spread_decimal = spread_update.spread_percentage
        if spread_decimal > 1:
            # User might have entered percentage (e.g., 2.5 instead of 0.025)
            spread_decimal = spread_decimal / 100
        
        # Validate reasonable spread limits
        if spread_decimal < 0 or spread_decimal > 0.1:  # Max 10% spread
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Spread must be between 0% and 10%"
            )
        
        # Check if trading pair exists
        check_query = "SELECT id FROM trading_pairs WHERE symbol = ?"
        result = db.execute_query(check_query, (symbol.upper(),))
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Trading pair {symbol} not found"
            )
        
        # Update spread
        update_query = """
            UPDATE trading_pairs 
            SET spread_percentage = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE symbol = ?
        """
        
        affected_rows = db.execute_update(update_query, (float(spread_decimal), symbol.upper()))
        
        if affected_rows == 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update spread"
            )
        
        # Return updated configuration
        return await get_pair_spread(symbol, db)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating spread for {symbol}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating spread: {str(e)}"
        )


@router.post("/spreads/bulk-update", response_model=DataResponse)
async def bulk_update_spreads(
    updates: List[dict],
    db: DatabaseManager = Depends(get_database),
    current_user: dict = Depends(get_current_user)
):
    """
    Bulk update spreads for multiple trading pairs
    
    Requires admin role.
    
    Args:
        updates: List of {symbol: str, spread_percentage: float}
    """
    try:
        # Check admin permission
        if current_user.get('role') != 'admin':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can update spreads"
            )
        
        updated_count = 0
        errors = []
        
        for update in updates:
            try:
                symbol = update.get('symbol')
                spread = update.get('spread_percentage')
                
                if not symbol or spread is None:
                    errors.append(f"Invalid update format: {update}")
                    continue
                
                # Convert percentage if needed
                spread_decimal = Decimal(str(spread))
                if spread_decimal > 1:
                    spread_decimal = spread_decimal / 100
                
                # Validate spread limits
                if spread_decimal < 0 or spread_decimal > 0.1:
                    errors.append(f"{symbol}: Spread must be between 0% and 10%")
                    continue
                
                # Update spread
                update_query = """
                    UPDATE trading_pairs 
                    SET spread_percentage = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE symbol = ?
                """
                
                affected = db.execute_update(update_query, (float(spread_decimal), symbol.upper()))
                
                if affected > 0:
                    updated_count += 1
                else:
                    errors.append(f"{symbol}: Trading pair not found")
                    
            except Exception as e:
                errors.append(f"{update}: {str(e)}")
        
        result = {
            "updated": updated_count,
            "errors": errors,
            "total": len(updates)
        }
        
        return DataResponse(
            message=f"Updated {updated_count} of {len(updates)} trading pairs",
            data=result
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in bulk spread update: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating spreads: {str(e)}"
        )
