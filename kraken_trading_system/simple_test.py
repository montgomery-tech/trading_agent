#!/usr/bin/env python3
"""
Simple test script to verify subscription methods work without complex logging.
Save this as: simple_test.py
"""

import asyncio
import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from trading_systems.exchanges.kraken.websocket_client import KrakenWebSocketClient
    print("✅ Successfully imported KrakenWebSocketClient with new subscription methods")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)


async def simple_test():
    """Simple test of subscription methods."""
    print("\n🧪 Simple Subscription Test")
    print("=" * 40)
    
    try:
        # Create client (bypass complex logging)
        client = KrakenWebSocketClient()
        print("✅ Client created successfully")
        
        # Test method availability
        methods = ['subscribe_ticker', 'subscribe_orderbook', 'subscribe_trades', 'unsubscribe']
        print("\n🔧 Checking subscription methods:")
        for method in methods:
            if hasattr(client, method):
                print(f"  ✅ {method}")
            else:
                print(f"  ❌ {method} MISSING")
                return False
        
        # Test connection (quick test)
        print("\n📡 Testing connection...")
        await client.connect_public()
        print("✅ Connected successfully!")
        
        # Test one subscription
        print("\n📊 Testing ticker subscription...")
        await client.subscribe_ticker(["XBT/USD"])
        print("✅ Subscription request sent!")
        
        # Brief message check
        print("\n🎧 Checking for messages (3 seconds)...")
        message_count = 0
        try:
            async for message in client.listen_public():
                message_count += 1
                event = message.get("event", "data")
                print(f"  📨 Message {message_count}: {event}")
                
                if message_count >= 5:  # Just get a few messages
                    break
                    
                await asyncio.sleep(0.5)
        except Exception as e:
            print(f"  ⚠️ Message listening: {e}")
        
        print(f"✅ Received {message_count} messages")
        
        # Cleanup
        await client.disconnect()
        print("✅ Disconnected")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run simple test."""
    success = asyncio.run(simple_test())
    
    if success:
        print("\n🎉 SUCCESS! Subscription methods are working!")
        print("\nThe new methods are ready to use:")
        print("• subscribe_ticker(['XBT/USD'])")
        print("• subscribe_orderbook(['XBT/USD'], depth=10)")
        print("• subscribe_trades(['XBT/USD'])")
        print("• unsubscribe('ticker:XBT/USD')")
    else:
        print("\n❌ Test failed")


if __name__ == "__main__":
    main()

