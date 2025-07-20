#!/usr/bin/env python3
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
        print("\n🎉 FIX SUCCESSFUL!")
    else:
        print("\n❌ Fix needs more work")
