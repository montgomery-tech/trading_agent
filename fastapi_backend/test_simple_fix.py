#!/usr/bin/env python3
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
