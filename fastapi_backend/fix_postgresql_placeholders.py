#!/usr/bin/env python3
"""
Fix PostgreSQL placeholder syntax in spread_management.py
PostgreSQL uses %s, not ? for placeholders
"""

import os

def fix_placeholders():
    """Replace ? with %s in spread_management.py"""
    
    spread_file = "api/routes/spread_management.py"
    
    print(f"🔧 Fixing PostgreSQL placeholders in {spread_file}...")
    
    # Read the file
    with open(spread_file, "r") as f:
        content = f.read()
    
    # Count replacements
    count = content.count('?')
    
    # Replace ? with %s for PostgreSQL
    content = content.replace('WHERE tp.symbol = ?', 'WHERE tp.symbol = %s')
    content = content.replace('WHERE tp.symbol = ? OR tp.symbol = ?', 'WHERE tp.symbol = %s OR tp.symbol = %s')
    content = content.replace('WHERE symbol = ?', 'WHERE symbol = %s')
    content = content.replace('SET spread_percentage = ?', 'SET spread_percentage = %s')
    content = content.replace('WHERE tp.is_active = 1', 'WHERE tp.is_active = true')  # PostgreSQL boolean
    
    # Also need to check execute_query calls - they might need tuples
    lines = content.split('\n')
    fixed_lines = []
    
    for line in lines:
        # Fix execute_query calls that pass single parameters
        if 'db.execute_query' in line and ', (' in line and line.strip().endswith('))'):
            # This is likely a single parameter passed as (param,)
            # It's already correct for PostgreSQL
            fixed_lines.append(line)
        elif 'db.execute_query' in line and not ', (' in line and '?' in line:
            # This might need fixing
            print(f"⚠️  Check this line: {line.strip()}")
            fixed_lines.append(line)
        else:
            fixed_lines.append(line)
    
    content = '\n'.join(fixed_lines)
    
    # Write back
    with open(spread_file, "w") as f:
        f.write(content)
    
    print(f"✅ Replaced {count} placeholder(s) from ? to %s")
    print("✅ Fixed boolean syntax for PostgreSQL")

def create_postgresql_compatible_routes():
    """Create a fully PostgreSQL-compatible version"""
    
    clean_routes = '''#!/usr/bin/env python3
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
'''
    
    # Save as backup
    with open("postgresql_spread_management.py", "w") as f:
        f.write(clean_routes)
    
    print("✅ Created postgresql_spread_management.py as reference")

if __name__ == "__main__":
    print("🚀 Fixing PostgreSQL Placeholder Syntax")
    print("=" * 50)
    
    # Fix the placeholders
    fix_placeholders()
    
    # Create clean version
    create_postgresql_compatible_routes()
    
    print("\n📋 Done! Changes made:")
    print("1. Replaced ? with %s for PostgreSQL compatibility")
    print("2. Changed is_active = 1 to is_active = true")
    print("3. Created postgresql_spread_management.py as reference")
    
    print("\n🔧 Next steps:")
    print("1. Restart FastAPI: python3 main.py")
    print("2. Test again: python3 test_spread_functionality.py")
    
    print("\n💡 If still having issues:")
    print("   cp postgresql_spread_management.py api/routes/spread_management.py")
    print("   This will use the clean PostgreSQL-compatible version")
