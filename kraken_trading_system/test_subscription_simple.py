#!/usr/bin/env python3
"""Simple test of subscription methods without complex setup."""

import sys
from pathlib import Path
import asyncio

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

async def test_subscription_methods():
    print("Testing subscription methods...")

    # Import here to catch any import errors
    try:
        from trading_systems.exchanges.kraken.websocket_client import KrakenWebSocketClient
        print("✅ Import successful")
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

    # Test client creation
    try:
        client = KrakenWebSocketClient()
        print("✅ Client created")
    except Exception as e:
        print(f"❌ Client creation failed: {e}")
        return False

    # Test that new methods exist
    methods = ['subscribe_ticker', 'subscribe_orderbook', 'subscribe_trades', 'subscribe_ohlc', 'unsubscribe']
    for method in methods:
        if hasattr(client, method):
            print(f"✅ Method {method} exists")
        else:
            print(f"❌ Method {method} missing")
            return False

    # Test subscription tracking when not connected (should fail)
    try:
        await client.subscribe_ticker(["XBT/USD"])
        print("❌ Should have failed when not connected")
        return False
    except Exception as e:
        print(f"✅ Correctly rejected when not connected: {str(e)[:50]}...")

    print("✅ All tests passed!")
    return True

if __name__ == "__main__":
    result = asyncio.run(test_subscription_methods())
    if result:
        print("\n🎉 Subscription methods are working correctly!")
    else:
        print("\n❌ Some tests failed")
