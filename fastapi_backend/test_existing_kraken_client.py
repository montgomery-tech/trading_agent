#!/usr/bin/env python3
"""
test_existing_kraken_client.py
Test the existing Kraken REST client directly
"""

import asyncio
import sys
from pathlib import Path

# Add kraken system to path
kraken_path = Path(__file__).parent / "kraken_trading_system" / "src"
if kraken_path.exists():
    sys.path.insert(0, str(kraken_path))

async def test_existing_client():
    """Test the existing Kraken REST client"""
    
    try:
        from trading_systems.exchanges.kraken.rest_client import EnhancedKrakenRestClient
        print("✅ Successfully imported existing Kraken REST client")
        
        client = EnhancedKrakenRestClient()
        print("✅ Created client instance")
        
        # Test server time (public endpoint)
        result = await client.get_server_time()
        print(f"✅ Server time: {result}")
        
        # Test ticker (if method exists)
        if hasattr(client, 'get_ticker'):
            ticker = await client.get_ticker("XBTUSD")
            print(f"✅ Ticker: {ticker}")
        else:
            print("⚠️  No get_ticker method, trying direct API call")
            # Try direct API call
            result = await client._make_request_with_retry(
                "GET", "/0/public/Ticker", {"pair": "XBTUSD"}, authenticated=False
            )
            print(f"✅ Direct ticker call: {result}")
        
        await client.close()
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_existing_client())
    if success:
        print("\n🎉 Existing Kraken client is working!")
    else:
        print("\n❌ Existing Kraken client has issues")
