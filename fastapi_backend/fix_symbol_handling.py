#!/usr/bin/env python3
"""
Fix the symbol handling in spread_management.py to handle both BTC/USD and BTCUSD formats
"""

import os

def fix_spread_management():
    """Update the get_pair_spread function to handle symbol formats better"""
    
    spread_file = "api/routes/spread_management.py"
    
    print(f"🔧 Fixing symbol handling in {spread_file}...")
    
    # Read the file
    with open(spread_file, "r") as f:
        content = f.read()
    
    # Find the get_pair_spread function and replace it
    old_function = '''@router.get("/spreads/{symbol}", response_model=DataResponse) 
async def get_pair_spread(
    symbol: str,
    db: DatabaseManager = Depends(get_database)
):
    """Get spread configuration for a specific trading pair"""
    try:
        # Handle both BTC/USD and BTCUSD formats
        formatted_symbol = symbol.upper().replace("/", "")
        formatted_symbol_with_slash = symbol.upper() if "/" in symbol else f"{symbol[:3]}/{symbol[3:]}".upper()
        
        query = """
            SELECT tp.id, tp.symbol, tp.base_currency, tp.quote_currency,
                   tp.spread_percentage, tp.min_trade_amount, tp.max_trade_amount,
                   tp.is_active
            FROM trading_pairs tp
            WHERE tp.symbol = ? OR tp.symbol = ?
        """
        
        results = db.execute_query(query, (formatted_symbol_with_slash, formatted_symbol))'''
    
    new_function = '''@router.get("/spreads/{symbol:path}", response_model=DataResponse) 
async def get_pair_spread(
    symbol: str,
    db: DatabaseManager = Depends(get_database)
):
    """Get spread configuration for a specific trading pair"""
    try:
        # Handle multiple symbol formats
        symbol_upper = symbol.upper()
        
        # Create different format variations
        formats_to_try = []
        
        # If it has a slash, also try without
        if "/" in symbol_upper:
            formats_to_try.append(symbol_upper)  # BTC/USD
            formats_to_try.append(symbol_upper.replace("/", ""))  # BTCUSD
        else:
            # If no slash, try to add one (assuming 3-letter base currency)
            formats_to_try.append(symbol_upper)  # BTCUSD
            if len(symbol_upper) >= 6:  # Minimum for XXX/YYY
                # Try common patterns
                formats_to_try.append(f"{symbol_upper[:3]}/{symbol_upper[3:]}")  # BTC/USD
                if len(symbol_upper) == 7:  # Might be XXX/YYYY
                    formats_to_try.append(f"{symbol_upper[:3]}/{symbol_upper[3:]}")
        
        # Build query with multiple OR conditions
        placeholders = " OR ".join(["tp.symbol = ?" for _ in formats_to_try])
        
        query = f"""
            SELECT tp.id, tp.symbol, tp.base_currency, tp.quote_currency,
                   tp.spread_percentage, tp.min_trade_amount, tp.max_trade_amount,
                   tp.is_active
            FROM trading_pairs tp
            WHERE {placeholders}
        """
        
        results = db.execute_query(query, formats_to_try)'''
    
    # Replace the function
    if old_function in content:
        content = content.replace(old_function, new_function)
        print("✅ Replaced get_pair_spread function with better symbol handling")
    else:
        print("⚠️  Could not find exact function match, trying different approach...")
        
        # Find the function by parts and replace it
        lines = content.split('\n')
        new_lines = []
        in_function = False
        skip_until_next_function = False
        
        for i, line in enumerate(lines):
            # Detect start of get_pair_spread function
            if '@router.get("/spreads/{symbol}"' in line:
                # Replace with path parameter
                new_lines.append('@router.get("/spreads/{symbol:path}", response_model=DataResponse)')
                in_function = True
                skip_until_next_function = True
                continue
            
            # Skip the old function body
            if skip_until_next_function:
                # Check if we've reached the next function or route
                if line.strip().startswith('@router.') and i > 0:
                    skip_until_next_function = False
                    in_function = False
                    
                    # Insert the new function body
                    new_function_body = '''async def get_pair_spread(
    symbol: str,
    db: DatabaseManager = Depends(get_database)
):
    """Get spread configuration for a specific trading pair"""
    try:
        # Handle multiple symbol formats
        symbol_upper = symbol.upper()
        
        # Try both with and without slash
        symbol_with_slash = symbol_upper if "/" in symbol_upper else f"{symbol_upper[:3]}/{symbol_upper[3:]}"
        symbol_without_slash = symbol_upper.replace("/", "")
        
        query = """
            SELECT tp.id, tp.symbol, tp.base_currency, tp.quote_currency,
                   tp.spread_percentage, tp.min_trade_amount, tp.max_trade_amount,
                   tp.is_active
            FROM trading_pairs tp
            WHERE tp.symbol = ? OR tp.symbol = ?
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

'''
                    new_lines.append(new_function_body)
                    new_lines.append(line)  # Add the next route decorator
                else:
                    continue  # Skip old function lines
            else:
                new_lines.append(line)
        
        content = '\n'.join(new_lines)
        print("✅ Updated function with better symbol handling")
    
    # Write back
    with open(spread_file, "w") as f:
        f.write(content)
    
    print("✅ Fixed symbol handling in spread_management.py")

def create_direct_test():
    """Create a direct test that shows the error"""
    
    test_code = '''#!/usr/bin/env python3
"""Test with more details about errors"""

import requests
import json

base_url = "http://localhost:8000"

# Test BTCUSD which gave 500 error
url = f"{base_url}/api/v1/trading-pairs/spreads/BTCUSD"

print(f"Testing: {url}")
print("-" * 50)

response = requests.get(url)
print(f"Status: {response.status_code}")

if response.status_code == 500:
    print("\\nError details:")
    try:
        error_data = response.json()
        print(json.dumps(error_data, indent=2))
    except:
        print(response.text[:500])
elif response.status_code == 200:
    data = response.json()
    print("✅ Success!")
    print(json.dumps(data, indent=2))

# Also test with slash
print("\\n" + "="*50)
url2 = f"{base_url}/api/v1/trading-pairs/spreads/BTC/USD"
print(f"Testing: {url2}")
response2 = requests.get(url2)
print(f"Status: {response2.status_code}")
'''
    
    with open("test_spread_detail.py", "w") as f:
        f.write(test_code)
    
    print("✅ Created test_spread_detail.py")

if __name__ == "__main__":
    print("🚀 Fixing Symbol Handling in Spread Routes")
    print("=" * 50)
    
    # Fix the spread management file
    fix_spread_management()
    
    # Create test script
    create_direct_test()
    
    print("\n📋 Next steps:")
    print("1. Restart FastAPI: python3 main.py")
    print("2. Run: python3 test_spread_detail.py")
    print("   This will show the actual error")
    print("\n💡 The fix:")
    print("- Changed route to use {symbol:path} to handle slashes")
    print("- Added logic to try both BTC/USD and BTCUSD formats")
    print("- Better error handling for symbol parsing")
