#!/usr/bin/env python3
"""
Ultra-simple WebSocket test for Kraken.
This is the most basic possible test to verify connectivity.
"""

import asyncio
import json
import ssl
import sys

try:
    import websockets
    print("✅ websockets library imported successfully")
except ImportError:
    print("❌ websockets library not found. Install with: pip install websockets")
    sys.exit(1)


def get_ssl_context():
    """Create SSL context with proper certificate handling."""
    try:
        # Try to create default SSL context
        ssl_context = ssl.create_default_context()
        return ssl_context
    except Exception as e:
        print(f"⚠️ Default SSL context failed: {e}")
        print("🔧 Using fallback SSL configuration...")

        # Fallback: create context that doesn't verify certificates
        # This is for testing only - not recommended for production
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        return ssl_context


async def simple_test():
    """Simplest possible WebSocket test."""
    url = "wss://ws.kraken.com"

    print(f"🔗 Attempting to connect to {url}")

    # Get SSL context
    ssl_context = get_ssl_context()

    try:
        # Try with SSL context
        async with websockets.connect(url, ssl=ssl_context) as websocket:
            print("✅ Connected successfully!")

            # Wait for first message (should be system status)
            print("⏳ Waiting for first message...")

            message = await asyncio.wait_for(websocket.recv(), timeout=10.0)
            data = json.loads(message)

            print("📨 First message received:")
            print(f"   Event: {data.get('event', 'unknown')}")
            print(f"   Status: {data.get('status', 'unknown')}")
            print(f"   Version: {data.get('version', 'unknown')}")

            # Wait for one more message (usually heartbeat)
            print("⏳ Waiting for second message...")
            message2 = await asyncio.wait_for(websocket.recv(), timeout=35.0)
            data2 = json.loads(message2)

            print("📨 Second message received:")
            print(f"   Event: {data2.get('event', 'unknown')}")

            print("🎉 Basic connectivity test PASSED!")
            return True

    except asyncio.TimeoutError:
        print("❌ Timeout waiting for messages")
        return False
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print(f"   Error type: {type(e).__name__}")

        # If SSL error, try without certificate verification as last resort
        if "SSL" in str(e) or "certificate" in str(e):
            print("\n🔧 Trying connection without SSL verification (testing only)...")
            return await simple_test_no_ssl_verify()

        return False


async def simple_test_no_ssl_verify():
    """Test with SSL verification disabled (for testing only)."""
    url = "wss://ws.kraken.com"

    # Create SSL context that doesn't verify certificates
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    try:
        async with websockets.connect(url, ssl=ssl_context) as websocket:
            print("✅ Connected successfully (SSL verification disabled)!")

            # Wait for first message
            message = await asyncio.wait_for(websocket.recv(), timeout=10.0)
            data = json.loads(message)

            print("📨 Message received:")
            print(f"   Event: {data.get('event', 'unknown')}")
            print(f"   Status: {data.get('status', 'unknown')}")

            print("🎉 Basic connectivity test PASSED (with SSL workaround)!")
            return True

    except Exception as e:
        print(f"❌ Even SSL workaround failed: {e}")
        return False


async def test_subscription():
    """Test basic subscription."""
    url = "wss://ws.kraken.com"

    print(f"\n🔗 Testing subscription to {url}")

    # Use the same SSL approach that worked for basic test
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    try:
        async with websockets.connect(url, ssl=ssl_context) as websocket:
            print("✅ Connected for subscription test")

            # Wait for system status
            await websocket.recv()  # system status
            print("📨 System status received")

            # Send subscription
            sub_message = {
                "event": "subscribe",
                "pair": ["XBT/USD"],
                "subscription": {"name": "ticker"}
            }

            await websocket.send(json.dumps(sub_message))
            print("📤 Subscription message sent")

            # Wait for subscription confirmation
            for i in range(5):  # Try up to 5 messages
                message = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                data = json.loads(message)

                if data.get("event") == "subscriptionStatus":
                    status = data.get("status")
                    print(f"📨 Subscription status: {status}")
                    if status == "subscribed":
                        print("🎉 Subscription test PASSED!")
                        return True
                elif data.get("event") == "heartbeat":
                    print("💓 Heartbeat received")
                else:
                    print(f"📨 Other message: {data.get('event', 'unknown')}")

            print("❌ No subscription confirmation received")
            return False

    except Exception as e:
        print(f"❌ Subscription test failed: {e}")
        return False


async def main():
    """Run all tests."""
    print("=" * 50)
    print("🧪 Ultra-Simple Kraken WebSocket Test")
    print("=" * 50)
    print()

    # Test 1: Basic connectivity
    print("Test 1: Basic Connectivity")
    print("-" * 30)
    basic_ok = await simple_test()

    if basic_ok:
        # Test 2: Subscription
        print("\nTest 2: Basic Subscription")
        print("-" * 30)
        sub_ok = await test_subscription()

        if sub_ok:
            print(f"\n🎉 ALL TESTS PASSED! WebSocket connection is working perfectly.")
        else:
            print(f"\n⚠️ Basic connection works, but subscription failed.")
    else:
        print(f"\n❌ Basic connection failed. Check your internet connection.")

    print("\n" + "=" * 50)


if __name__ == "__main__":
    print("System Information:")
    print(f"Python version: {sys.version}")
    print(f"Websockets version: {websockets.__version__}")
    print()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)
