#!/usr/bin/env python3
"""
Debug the specific error for individual spread endpoint
"""

import requests
import json

def test_spread_endpoint_detailed():
    """Test with detailed error information"""
    
    base_url = "http://localhost:8000"
    
    # Test different formats
    test_cases = [
        ("BTC/USD", "with slash"),
        ("BTCUSD", "without slash"),
        ("BTC%2FUSD", "URL encoded"),
    ]
    
    print("🔍 Testing Individual Spread Endpoint")
    print("=" * 50)
    
    for symbol, description in test_cases:
        url = f"{base_url}/api/v1/trading-pairs/spreads/{symbol}"
        print(f"\nTesting {description}: {url}")
        print("-" * 30)
        
        try:
            response = requests.get(url)
            print(f"Status: {response.status_code}")
            
            if response.status_code == 500:
                # Get the error details
                try:
                    error_data = response.json()
                    error_msg = error_data.get('error', 'No error message')
                    print(f"Error: {error_msg}")
                    
                    # Check if it's still a placeholder issue
                    if "?" in error_msg:
                        print("❌ Still has ? placeholders!")
                    elif "syntax error" in error_msg:
                        print("❌ SQL syntax error")
                    else:
                        print("❌ Other error")
                        
                except:
                    print(f"Raw error: {response.text[:200]}")
                    
            elif response.status_code == 200:
                data = response.json()
                spread_data = data.get('data', {})
                spread_pct = spread_data.get('spread_percentage', 0) * 100
                print(f"✅ Success! Spread: {spread_pct:.2f}%")
                
            elif response.status_code == 404:
                print("❌ Not found (route not matched)")
                
        except Exception as e:
            print(f"❌ Request failed: {e}")

def check_database_directly():
    """Check what's in the database directly"""
    
    print("\n\n🔍 Checking Database Content")
    print("=" * 50)
    
    # Use the deployment package's database module
    try:
        from api.database import DatabaseManager
        from decouple import config
        
        db_url = config('DATABASE_URL')
        db = DatabaseManager(db_url)
        db.connect()
        
        # Try a simple query
        query = "SELECT symbol, spread_percentage FROM trading_pairs WHERE symbol LIKE %s"
        results = db.execute_query(query, ('%BTC%',))
        
        print("Trading pairs with BTC:")
        for row in results:
            print(f"  {row['symbol']}: {float(row['spread_percentage'])*100:.2f}%")
            
        db.disconnect()
        
    except Exception as e:
        print(f"Could not check database: {e}")

def suggest_simple_fix():
    """Suggest a simple fix"""
    
    print("\n\n💡 Quick Fix Suggestion")
    print("=" * 50)
    print("Replace the problem function in api/routes/spread_management.py with:")
    print("-" * 50)
    
    fix_code = '''@router.get("/spreads/{symbol:path}", response_model=DataResponse)
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
        )'''
    
    print(fix_code)

if __name__ == "__main__":
    test_spread_endpoint_detailed()
    check_database_directly()
    suggest_simple_fix()
