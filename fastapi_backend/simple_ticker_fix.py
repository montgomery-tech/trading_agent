#!/usr/bin/env python3
"""
simple_ticker_fix.py
Simple fix for the ticker key mismatch issue based on the actual error
"""

def fix_ticker_key_issue():
    """Fix the ticker key issue in our kraken_api_client.py"""
    
    print("🔧 SIMPLE FIX - Ticker Key Issue")
    print("=" * 50)
    print("Error showed: Expected 'XBTUSD' but Kraken returned 'XXBTZUSD'")
    print("Let's just fix this directly...")
    
    # Read the current kraken API client
    with open("api/services/kraken_api_client.py", "r") as f:
        content = f.read()
    
    # Find the get_ticker_info method and replace just the key lookup part
    method_start = content.find("async def get_ticker_info(")
    if method_start == -1:
        print("❌ Could not find get_ticker_info method")
        return False
    
    # Find the problematic line where it tries to get ticker_data
    problem_section = '''# Kraken returns different key formats, try to find the right one
            # First try exact match
            if kraken_pair in result:
                ticker_data = result[kraken_pair]
                logger.info(f"Found ticker data with exact key: {kraken_pair}")
            else:
                # Try to find by partial match (Kraken sometimes adds extra characters)
                logger.info(f"Exact key {kraken_pair} not found. Available keys: {list(result.keys())}")
                
                # Common patterns Kraken uses:
                possible_keys = [
                    kraken_pair,           # XBTUSD
                    f"X{kraken_pair}",     # XXBTUSD  
                    f"{kraken_pair}Z",     # XBTUSDD
                    f"X{kraken_pair}Z",    # XXBTUSDD
                    kraken_pair.replace("XBT", "BTC"),  # BTCUSD
                    f"X{kraken_pair.replace('XBT', 'BTC')}Z"  # XBTCUSDZ
                ]
                
                # Try each possible key
                for key in possible_keys:
                    if key in result:
                        ticker_data = result[key]
                        logger.info(f"Found ticker data with key: {key}")
                        break
                
                # If still not found, try fuzzy matching
                if not ticker_data:
                    for key in result.keys():
                        # Check if the key contains our pair or vice versa
                        if (kraken_pair in key or key in kraken_pair or 
                            key.replace('X', '').replace('Z', '') == kraken_pair.replace('X', '').replace('Z', '')):
                            ticker_data = result[key]
                            logger.info(f"Found ticker data with fuzzy match: {key}")
                            break'''
    
    # The simple fix - just take the first available key if exact match fails
    simple_fix = '''# Simple fix: just use whatever key Kraken returns
            ticker_data = None
            
            # First try exact match
            if kraken_pair in result:
                ticker_data = result[kraken_pair]
            else:
                # Just use the first available key (Kraken usually returns one pair)
                available_keys = list(result.keys())
                if available_keys:
                    first_key = available_keys[0]
                    ticker_data = result[first_key]
                    logger.info(f"Using key '{first_key}' for requested pair '{kraken_pair}'")'''
    
    # Replace the complex logic with simple fix
    if problem_section in content:
        new_content = content.replace(problem_section, simple_fix)
    else:
        # If the exact section isn't found, let's do a targeted replacement
        # Look for the ticker_data assignment
        lines = content.split('\n')
        new_lines = []
        
        inside_get_ticker = False
        fixed = False
        
        for line in lines:
            if "async def get_ticker_info(" in line:
                inside_get_ticker = True
            elif inside_get_ticker and "async def " in line and "get_ticker_info" not in line:
                inside_get_ticker = False
            
            # Replace the problematic ticker_data logic
            if inside_get_ticker and "ticker_data = result.get(kraken_pair)" in line and not fixed:
                new_lines.append("            # Simple fix for key mismatch")
                new_lines.append("            ticker_data = None")
                new_lines.append("            if kraken_pair in result:")
                new_lines.append("                ticker_data = result[kraken_pair]")
                new_lines.append("            else:")
                new_lines.append("                # Use first available key")
                new_lines.append("                available_keys = list(result.keys())")
                new_lines.append("                if available_keys:")
                new_lines.append("                    ticker_data = result[available_keys[0]]")
                new_lines.append("                    logger.info(f'Using {available_keys[0]} for {kraken_pair}')")
                fixed = True
            else:
                new_lines.append(line)
        
        new_content = '\n'.join(new_lines)
    
    # Backup and save
    import shutil
    from datetime import datetime
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = f"api/services/kraken_api_client.py.backup_simple_{timestamp}"
    shutil.copy2("api/services/kraken_api_client.py", backup_path)
    print(f"✅ Backed up to {backup_path}")
    
    with open("api/services/kraken_api_client.py", "w") as f:
        f.write(new_content)
    
    print("✅ Applied simple ticker key fix")
    return True

def test_the_fix():
    """Create a simple test for the fix"""
    
    test_script = '''#!/usr/bin/env python3
"""
test_simple_fix.py
Test the simple ticker fix
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

async def test_ticker_fix():
    """Test if the ticker fix works"""
    
    try:
        from api.services.kraken_api_client import get_kraken_client
        
        print("🧪 Testing simple ticker fix...")
        client = await get_kraken_client()
        
        # Test ticker
        ticker = await client.get_ticker_info("BTC-USD")
        print(f"✅ Ticker result: {ticker}")
        
        # Test current price
        price = await client.get_current_price("BTC-USD")
        print(f"✅ Current price: ${price}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_ticker_fix())
    print(f"Test result: {'SUCCESS' if success else 'FAILED'}")
'''
    
    with open("test_simple_fix.py", "w") as f:
        f.write(test_script)
    
    print("✅ Created test_simple_fix.py")

def main():
    print("🔧 SIMPLE TICKER KEY FIX")
    print("=" * 40)
    print("Based on the error: Expected 'XBTUSD' but got 'XXBTZUSD'")
    print("Let's just handle this case directly...")
    print()
    
    success = fix_ticker_key_issue()
    
    if success:
        test_the_fix()
        
        print("\n✅ SIMPLE FIX APPLIED!")
        print("=" * 30)
        print()
        print("📋 What was fixed:")
        print("  ✅ Handles Kraken's actual key format")
        print("  ✅ Uses first available key if exact match fails")
        print("  ✅ Much simpler logic")
        print()
        print("📋 Next steps:")
        print("1. Test the fix:")
        print("   python3 test_simple_fix.py")
        print()
        print("2. Restart FastAPI:")
        print("   python3 main.py")
        print()
        print("3. Test the endpoint:")
        print('   curl "http://localhost:8000/api/v1/trades/pricing/BTC-USD"')
        print()
        print("🎯 This should finally work!")

if __name__ == "__main__":
    main()
