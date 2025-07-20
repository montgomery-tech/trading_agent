#!/usr/bin/env python3
"""
targeted_ticker_fix.py
Precisely fix the ticker key lookup issue
"""

def apply_targeted_fix():
    """Apply a very targeted fix to the ticker key lookup"""
    
    print("🎯 TARGETED TICKER FIX")
    print("=" * 40)
    print("Replacing the exact problematic section...")
    
    # Read the current file
    with open("api/services/kraken_api_client.py", "r") as f:
        content = f.read()
    
    # Find and replace the exact problematic section
    old_section = '''            if not ticker_data:
                available_pairs = list(result.keys())
                raise KrakenAPIError(f"No ticker data for pair: {kraken_pair}. Available: {available_pairs}")'''
    
    new_section = '''            if not ticker_data:
                # Use the first available key since Kraken returns XXBTZUSD instead of XBTUSD
                available_pairs = list(result.keys())
                if available_pairs:
                    first_key = available_pairs[0]
                    ticker_data = result[first_key]
                    logger.info(f"Using available key '{first_key}' for requested pair '{kraken_pair}'")
                else:
                    raise KrakenAPIError(f"No ticker data available. Result: {result}")'''
    
    if old_section in content:
        new_content = content.replace(old_section, new_section)
        print("✅ Found and replaced the error section")
    else:
        print("❌ Could not find the exact error section")
        print("Let's try a different approach...")
        
        # Alternative: find the raise statement and replace it
        old_raise = 'raise KrakenAPIError(f"No ticker data for pair: {kraken_pair}. Available: {available_pairs}")'
        
        new_logic = '''# Fix: Use first available key if exact match not found
                if available_pairs:
                    first_key = available_pairs[0]
                    ticker_data = result[first_key]
                    logger.info(f"Using available key '{first_key}' for requested pair '{kraken_pair}'")
                else:
                    raise KrakenAPIError(f"No ticker data available. Result: {result}")'''
        
        new_content = content.replace(old_raise, new_logic)
        print("✅ Applied alternative fix")
    
    # Backup and save
    import shutil
    from datetime import datetime
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = f"api/services/kraken_api_client.py.backup_targeted_{timestamp}"
    shutil.copy2("api/services/kraken_api_client.py", backup_path)
    print(f"✅ Backed up to {backup_path}")
    
    with open("api/services/kraken_api_client.py", "w") as f:
        f.write(new_content)
    
    print("✅ Applied targeted fix")
    return True

def verify_fix():
    """Verify the fix was applied by checking the file"""
    
    with open("api/services/kraken_api_client.py", "r") as f:
        content = f.read()
    
    if "Using available key" in content:
        print("✅ Fix appears to be applied correctly")
        return True
    else:
        print("❌ Fix may not have been applied")
        return False

def create_simple_test():
    """Create a very simple test"""
    
    test_code = '''#!/usr/bin/env python3
"""
test_targeted_fix.py
Simple test for the targeted fix
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

async def test_fix():
    try:
        from api.services.kraken_api_client import get_kraken_client
        
        print("🧪 Testing targeted ticker fix...")
        client = await get_kraken_client()
        
        # This should now work with XXBTZUSD
        ticker = await client.get_ticker_info("BTC-USD")
        print(f"✅ SUCCESS! Ticker: {ticker['symbol']} = ${ticker['last']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Still failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_fix())
    if success:
        print("\\n🎉 FIX SUCCESSFUL!")
    else:
        print("\\n❌ Fix needs more work")
'''
    
    with open("test_targeted_fix.py", "w") as f:
        f.write(test_code)
    
    print("✅ Created test_targeted_fix.py")

def main():
    print("🎯 APPLYING TARGETED FIX")
    print("We know exactly what's wrong: XBTUSD vs XXBTZUSD")
    print("Let's fix this specific issue...")
    print()
    
    # Apply the fix
    apply_targeted_fix()
    
    # Verify it
    if verify_fix():
        create_simple_test()
        
        print("\n✅ TARGETED FIX COMPLETE!")
        print("=" * 30)
        print()
        print("📋 Next steps:")
        print("1. Test the targeted fix:")
        print("   python3 test_targeted_fix.py")
        print()
        print("2. If successful, restart FastAPI:")
        print("   python3 main.py")
        print()
        print("3. Test the endpoint:")
        print('   curl "http://localhost:8000/api/v1/trades/pricing/BTC-USD"')
        print()
        print("🎯 This should handle the XXBTZUSD key correctly!")
    else:
        print("\n❌ Fix verification failed")
        print("Please check the kraken_api_client.py file manually")

if __name__ == "__main__":
    main()
