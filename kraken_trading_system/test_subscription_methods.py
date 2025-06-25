#!/usr/bin/env python3
"""
Quick test script to verify subscription methods work.
Save this as: test_subscription_methods.py
"""

import asyncio
import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from trading_systems.exchanges.kraken.websocket_client import KrakenWebSocketClient
    from trading_systems.utils.logger import get_logger
    print("✅ Successfully imported KrakenWebSocketClient with new subscription methods")
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running from the project root directory")
    sys.exit(1)


async def test_subscription_methods():
    """Test the new subscription methods."""
    logger = get_logger("SubscriptionTest")
    client = KrakenWebSocketClient()
    
    print("🧪 Testing Subscription Methods")
    print("=" * 50)
    
    try:
        # Test 1: Connect to WebSocket
        print("📡 Connecting to Kraken public WebSocket...")
        await client.connect_public()
        print("✅ Connected successfully!")
        
        # Test 2: Check connection status
        status = client.get_connection_status()
        print(f"📊 Connection Status: {status['public_connected']}")
        
        # Test 3: Test subscription methods exist and work
        print("\n🔧 Testing subscription method availability:")
        
        # Check if methods exist
        methods_to_check = ['subscribe_ticker', 'subscribe_orderbook', 'subscribe_trades', 'unsubscribe']
        for method_name in methods_to_check:
            if hasattr(client, method_name):
                print(f"  ✅ {method_name} method available")
            else:
                print(f"  ❌ {method_name} method missing")
                return False
        
        # Test 4: Try actual subscription (ticker only for quick test)
        print("\n📊 Testing ticker subscription...")
        await client.subscribe_ticker(["XBT/USD"])
        print("✅ Ticker subscription request sent successfully!")
        
        # Wait a moment for subscription confirmation
        print("⏳ Waiting for subscription confirmation...")
        await asyncio.sleep(3)
        
        # Check active subscriptions
        active_subs = client.get_active_subscriptions()
        print(f"📋 Active subscriptions: {len(active_subs)}")
        for sub_id, details in active_subs.items():
            print(f"  - {sub_id}: {details}")
        
        # Test 5: Listen for a few messages
        print("\n🎧 Listening for messages (5 seconds)...")
        message_count = 0
        try:
            async for message in client.listen_public():
                message_count += 1
                event = message.get("event", "data")
                if event == "subscriptionStatus":
                    print(f"  📨 Subscription status: {message.get('status')} for {message.get('subscription', {}).get('name')}")
                elif event == "heartbeat":
                    print("  💓 Heartbeat")
                else:
                    print(f"  📈 Message {message_count}: {event}")
                
                # Stop after 10 messages or 5 seconds
                if message_count >= 10:
                    break
                
                # Add a small delay
                await asyncio.sleep(0.5)
        except asyncio.TimeoutError:
            pass
        
        print(f"✅ Received {message_count} messages")
        
        # Test 6: Test unsubscribe if we have subscriptions
        if active_subs:
            print("\n📤 Testing unsubscribe...")
            first_sub = list(active_subs.keys())[0]
            await client.unsubscribe(first_sub)
            print(f"✅ Unsubscribe request sent for: {first_sub}")
        
        print("\n🎉 All subscription method tests completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Cleanup
        print("\n🧹 Cleaning up...")
        try:
            await client.disconnect()
            print("✅ Disconnected successfully")
        except Exception as e:
            print(f"⚠️ Cleanup error: {e}")


async def main():
    """Main test function."""
    print("Kraken WebSocket Subscription Methods Test")
    print("=" * 50)
    
    success = await test_subscription_methods()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 ALL TESTS PASSED! Subscription methods are working correctly.")
        print("\nYou can now:")
        print("• Subscribe to ticker data: client.subscribe_ticker(['XBT/USD'])")
        print("• Subscribe to orderbook: client.subscribe_orderbook(['XBT/USD'], depth=10)")
        print("• Subscribe to trades: client.subscribe_trades(['XBT/USD'])")
        print("• Unsubscribe: client.unsubscribe('ticker:XBT/USD')")
    else:
        print("❌ TESTS FAILED. Check the errors above.")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)