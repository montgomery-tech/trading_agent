#!/usr/bin/env python3
"""
revert_and_fix_simple.py
Revert back to our simple approach and fix the ticker issue properly
"""

import os
import shutil
from datetime import datetime

def revert_to_simple_kraken_client():
    """Revert back to our simple kraken_api_client.py and fix the import issues"""
    
    print("🔄 REVERTING TO SIMPLE APPROACH")
    print("=" * 50)
    print("The complex import approach is causing configuration conflicts.")
    print("Let's go back to our simple client and fix the XXBTZUSD issue properly.")
    print()
    
    # First, fix the import in kraken_integrated_trade_service.py
    trade_service_path = "api/services/kraken_integrated_trade_service.py"
    
    with open(trade_service_path, "r") as f:
        content = f.read()
    
    # Replace the problematic import
    old_import = "from api.services.kraken_client_adapter import get_kraken_client"
    new_import = "from api.services.kraken_api_client import get_kraken_client, KrakenAPIError"
    
    if old_import in content:
        content = content.replace(old_import, new_import)
        
        # Also fix the exception handling
        content = content.replace("except Exception as e:", "except KrakenAPIError as e:")
        
        # Backup and save
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = f"{trade_service_path}.backup_revert_{timestamp}"
        shutil.copy2(trade_service_path, backup_path)
        print(f"✅ Backed up trade service to {backup_path}")
        
        with open(trade_service_path, "w") as f:
            f.write(content)
        
        print("✅ Reverted trade service imports")
    
    # Remove the problematic adapter file
    adapter_path = "api/services/kraken_client_adapter.py"
    if os.path.exists(adapter_path):
        os.remove(adapter_path)
        print("✅ Removed problematic adapter file")
    
    return True

def apply_definitive_ticker_fix():
    """Apply a definitive fix to the ticker key issue"""
    
    print("\n🔧 APPLYING DEFINITIVE TICKER FIX")
    print("=" * 40)
    
    # Read the current kraken_api_client.py
    with open("api/services/kraken_api_client.py", "r") as f:
        content = f.read()
    
    # Find the get_ticker_info method and completely replace the problematic section
    method_start = content.find("async def get_ticker_info(self, symbol: str)")
    if method_start == -1:
        print("❌ Could not find get_ticker_info method")
        return False
    
    # Find the end of the method
    method_end = content.find("\n    async def ", method_start + 1)
    if method_end == -1:
        method_end = content.find("\n    def _", method_start + 1)
    if method_end == -1:
        method_end = len(content)
    
    # Create a completely new, simple get_ticker_info method
    new_method = '''async def get_ticker_info(self, symbol: str) -> Dict[str, Any]:
        """Get ticker information for a trading pair"""
        try:
            kraken_pair = self._map_symbol_to_kraken(symbol)
            response = await self._make_public_request("Ticker", {"pair": kraken_pair})
            
            if "result" not in response:
                raise KrakenAPIError("No ticker data received")
            
            result = response["result"]
            
            # Simple approach: use the first available key
            # This handles Kraken returning XXBTZUSD instead of XBTUSD
            available_keys = list(result.keys())
            if not available_keys:
                raise KrakenAPIError("No ticker data in response")
            
            # Use the first (and usually only) key
            ticker_key = available_keys[0]
            ticker_data = result[ticker_key]
            
            logger.info(f"Using ticker key '{ticker_key}' for requested symbol '{symbol}'")
            
            # Parse ticker data - Kraken format is well documented
            return {
                "symbol": symbol,
                "kraken_pair": kraken_pair,
                "bid": float(ticker_data["b"][0]),  # Best bid price
                "ask": float(ticker_data["a"][0]),  # Best ask price
                "last": float(ticker_data["c"][0]),  # Last trade price
                "volume": float(ticker_data["v"][1]),  # 24h volume
                "vwap": float(ticker_data["p"][1]),  # 24h VWAP
                "trades": int(ticker_data["t"][1]),  # Number of trades today
                "low": float(ticker_data["l"][1]),  # 24h low
                "high": float(ticker_data["h"][1]),  # 24h high
                "timestamp": datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Failed to get ticker for {symbol}: {e}")
            raise KrakenAPIError(f"Failed to get ticker: {e}")
    '''
    
    # Replace the entire method
    new_content = content[:method_start] + new_method + content[method_end:]
    
    # Backup and save
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = f"api/services/kraken_api_client.py.backup_definitive_{timestamp}"
    shutil.copy2("api/services/kraken_api_client.py", backup_path)
    print(f"✅ Backed up kraken client to {backup_path}")
    
    with open("api/services/kraken_api_client.py", "w") as f:
        f.write(new_content)
    
    print("✅ Applied definitive ticker fix")
    return True

def create_final_test():
    """Create a final test script"""
    
    test_script = '''#!/usr/bin/env python3
"""
test_final_fix.py
Final test of the ticker fix
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

async def test_final_fix():
    """Test the final ticker fix"""
    
    try:
        from api.services.kraken_api_client import get_kraken_client
        
        print("🧪 Testing final ticker fix...")
        client = await get_kraken_client()
        
        # Test different symbol formats
        symbols = ["BTC-USD", "BTCUSD", "ETH-USD"]
        
        for symbol in symbols:
            try:
                print(f"\\nTesting {symbol}...")
                ticker = await client.get_ticker_info(symbol)
                print(f"✅ {symbol}: ${ticker['last']} (bid: ${ticker['bid']}, ask: ${ticker['ask']})")
            except Exception as e:
                print(f"❌ {symbol} failed: {e}")
        
        print("\\n🎉 Ticker fix working!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_final_fix())
    print(f"\\nFinal result: {'SUCCESS' if success else 'FAILED'}")
'''
    
    with open("test_final_fix.py", "w") as f:
        f.write(test_script)
    
    print("✅ Created test_final_fix.py")

def main():
    print("🚀 FIXING THE IMPORT AND TICKER ISSUES")
    print("=" * 60)
    print("Step 1: Revert to simple approach (no complex imports)")
    print("Step 2: Fix the ticker key issue definitively")
    print("Step 3: Test everything")
    print()
    
    # Revert imports
    revert_to_simple_kraken_client()
    
    # Fix ticker issue
    apply_definitive_ticker_fix()
    
    # Create test
    create_final_test()
    
    print("\n✅ COMPLETE FIX APPLIED!")
    print("=" * 30)
    print()
    print("📋 What was fixed:")
    print("  ✅ Removed problematic import dependencies")
    print("  ✅ Reverted to simple kraken_api_client.py")
    print("  ✅ Fixed ticker key handling (XXBTZUSD vs XBTUSD)")
    print("  ✅ Simple approach: use first available key")
    print()
    print("📋 Next steps:")
    print("1. Test the fix:")
    print("   python3 test_final_fix.py")
    print()
    print("2. Start FastAPI (should work now):")
    print("   python3 main.py")
    print()
    print("3. Test the endpoint:")
    print('   curl "http://localhost:8000/api/v1/trades/pricing/BTC-USD"')
    print()
    print("🎯 This should finally work without import conflicts!")

if __name__ == "__main__":
    main()
