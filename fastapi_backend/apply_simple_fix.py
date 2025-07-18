#!/usr/bin/env python3
"""
Apply the simple fix to spread_management.py
"""

import os

def apply_fix():
    """Replace the get_pair_spread function with a working version"""
    
    spread_file = "api/routes/spread_management.py"
    
    print(f"🔧 Fixing {spread_file}...")
    
    # Read the file
    with open(spread_file, "r") as f:
        lines = f.readlines()
    
    # Find the start and end of get_pair_spread function
    start_idx = None
    end_idx = None
    
    for i, line in enumerate(lines):
        if '@router.get("/spreads/{symbol' in line and start_idx is None:
            start_idx = i
        elif start_idx is not None and '@router.' in line:
            end_idx = i
            break
    
    if start_idx is None:
        print("❌ Could not find get_pair_spread function")
        return False
    
    # If no end found, it might be the last function
    if end_idx is None:
        end_idx = len(lines)
    
    print(f"Found function from line {start_idx+1} to {end_idx}")
    
    # Create the new function
    new_function = '''@router.get("/spreads/{symbol:path}", response_model=DataResponse)
async def get_pair_spread(
    symbol: str,
    db: DatabaseManager = Depends(get_database)
):
    """Get spread configuration for a specific trading pair"""
    try:
        # Simple query that should work
        query = """
            SELECT tp.id, tp.symbol, tp.base_currency, tp.quote_currency,
                   tp.spread_percentage, tp.min_trade_amount, tp.max_trade_amount,
                   tp.is_active
            FROM trading_pairs tp
            WHERE UPPER(tp.symbol) = %s
        """
        
        # Normalize the symbol
        normalized_symbol = symbol.upper().strip()
        
        results = db.execute_query(query, (normalized_symbol,))
        
        if not results:
            # Try without slash if it has one
            if "/" in normalized_symbol:
                alt_symbol = normalized_symbol.replace("/", "")
                results = db.execute_query(query, (alt_symbol,))
            # Try with slash if it doesn't have one
            elif len(normalized_symbol) >= 6:
                alt_symbol = f"{normalized_symbol[:3]}/{normalized_symbol[3:]}"
                results = db.execute_query(query, (alt_symbol,))
        
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

'''
    
    # Replace the function
    new_lines = lines[:start_idx] + [new_function] + lines[end_idx:]
    
    # Write back
    with open(spread_file, "w") as f:
        f.writelines(new_lines)
    
    print("✅ Replaced get_pair_spread function")
    return True

def verify_fix():
    """Check that the fix was applied"""
    
    spread_file = "api/routes/spread_management.py"
    
    with open(spread_file, "r") as f:
        content = f.read()
    
    # Check for signs of the fix
    if "WHERE UPPER(tp.symbol) = %s" in content:
        print("✅ Fix verified - simple query in place")
        return True
    else:
        print("❌ Fix not verified")
        return False

if __name__ == "__main__":
    print("🚀 Applying Simple Fix for Spread Endpoint")
    print("=" * 50)
    
    if apply_fix():
        if verify_fix():
            print("\n✅ Fix applied successfully!")
            print("\n📋 Next steps:")
            print("1. Restart FastAPI: python3 main.py")
            print("2. Test again: python3 test_spread_functionality.py")
            print("\nThe endpoint should now work for:")
            print("  - /api/v1/trading-pairs/spreads/BTC/USD")
            print("  - /api/v1/trading-pairs/spreads/BTCUSD")
        else:
            print("\n⚠️ Fix may not have been applied correctly")
    else:
        print("\n❌ Could not apply fix")
