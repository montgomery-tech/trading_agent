#!/usr/bin/env python3
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
                print(f"\nTesting {symbol}...")
                ticker = await client.get_ticker_info(symbol)
                print(f"✅ {symbol}: ${ticker['last']} (bid: ${ticker['bid']}, ask: ${ticker['ask']})")
            except Exception as e:
                print(f"❌ {symbol} failed: {e}")
        
        print("\n🎉 Ticker fix working!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_final_fix())
    print(f"\nFinal result: {'SUCCESS' if success else 'FAILED'}")
