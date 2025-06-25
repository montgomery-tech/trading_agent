"""
Market Data Subscription Example

This example demonstrates the new subscription functionality implemented in Task 1.3.1.
It shows how to:
1. Connect to Kraken WebSocket
2. Subscribe to various market data channels
3. Handle subscription confirmations
4. Display active subscriptions
5. Unsubscribe and clean up

Run this example to test the subscription methods are working properly.
"""

import asyncio
import signal
import sys
from pathlib import Path

# Add src to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from trading_system.exchanges.kraken.websocket_client import KrakenWebSocketClient
from trading_system.utils.logger import get_logger


class SubscriptionExample:
    """Market data subscription demonstration."""

    def __init__(self):
        self.logger = get_logger("SubscriptionExample")
        self.client = KrakenWebSocketClient()
        self.running = True

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        self.logger.info("Shutdown signal received", signal=signum)
        self.running = False

    async def run(self):
        """Run the subscription example."""
        try:
            self.logger.info("Starting market data subscription example")

            # Connect to public WebSocket
            self.logger.info("Connecting to Kraken public WebSocket...")
            await self.client.connect_public()
            self.logger.info("Connected successfully!")

            # Wait a moment for connection to stabilize
            await asyncio.sleep(2)

            # Demonstrate various subscription types
            await self._demonstrate_subscriptions()

            # Listen for messages and show subscription confirmations
            await self._listen_for_confirmations()

            # Show active subscriptions
            self._display_active_subscriptions()

            # Demonstrate unsubscription
            await self._demonstrate_unsubscription()

        except KeyboardInterrupt:
            self.logger.info("Interrupted by user")
        except Exception as e:
            self.logger.error("Error in example", error=str(e), exc_info=True)
        finally:
            await self._cleanup()

    async def _demonstrate_subscriptions(self):
        """Demonstrate different types of subscriptions."""
        self.logger.info("=" * 50)
        self.logger.info("DEMONSTRATING SUBSCRIPTION METHODS")
        self.logger.info("=" * 50)

        # 1. Subscribe to ticker data
        self.logger.info("1. Subscribing to ticker data for BTC/USD and ETH/USD...")
        ticker_result = await self.client.subscribe_ticker(["XBT/USD", "ETH/USD"])
        self.logger.info("Ticker subscription sent", **ticker_result)

        await asyncio.sleep(1)

        # 2. Subscribe to orderbook data
        self.logger.info("2. Subscribing to orderbook data for BTC/USD (depth=10)...")
        book_result = await self.client.subscribe_orderbook(["XBT/USD"], depth=10)
        self.logger.info("Orderbook subscription sent", **book_result)

        await asyncio.sleep(1)

        # 3. Subscribe to trade data
        self.logger.info("3. Subscribing to trade data for BTC/USD...")
        trade_result = await self.client.subscribe_trades(["XBT/USD"])
        self.logger.info("Trade subscription sent", **trade_result)

        await asyncio.sleep(1)

        # 4. Subscribe to OHLC data
        self.logger.info("4. Subscribing to OHLC data for BTC/USD (1-minute)...")
        ohlc_result = await self.client.subscribe_ohlc(["XBT/USD"], interval=1)
        self.logger.info("OHLC subscription sent", **ohlc_result)

        await asyncio.sleep(1)

        # 5. Subscribe to orderbook with different depth
        self.logger.info("5. Subscribing to orderbook data for ETH/USD (depth=25)...")
        book_result2 = await self.client.subscribe_orderbook(["ETH/USD"], depth=25)
        self.logger.info("Orderbook subscription sent", **book_result2)

        self.logger.info("All subscriptions sent! Waiting for confirmations...")

    async def _listen_for_confirmations(self):
        """Listen for subscription confirmation messages."""
        self.logger.info("=" * 50)
        self.logger.info("LISTENING FOR SUBSCRIPTION CONFIRMATIONS")
        self.logger.info("=" * 50)

        confirmations_received = 0
        max_confirmations = 5  # We sent 5 subscriptions
        timeout_seconds = 30

        try:
            async for message in self.client.listen_public():
                if not self.running:
                    break

                if isinstance(message, dict):
                    event = message.get("event")

                    if event == "subscriptionStatus":
                        status = message.get("status")
                        channel = message.get("channelName")
                        pair = message.get("pair")
                        channel_id = message.get("channelID")

                        if status == "subscribed":
                            confirmations_received += 1
                            self.logger.info(
                                f"✅ SUBSCRIPTION CONFIRMED [{confirmations_received}/{max_confirmations}]",
                                channel=channel,
                                pair=pair,
                                channel_id=channel_id
                            )
                        elif status == "error":
                            self.logger.error(
                                "❌ SUBSCRIPTION ERROR",
                                channel=channel,
                                pair=pair,
                                error=message.get("errorMessage")
                            )

                    elif event == "heartbeat":
                        self.logger.info("💓 Heartbeat received")

                    # Stop after receiving all confirmations
                    if confirmations_received >= max_confirmations:
                        self.logger.info("All subscription confirmations received!")
                        break

                # Timeout protection
                timeout_seconds -= 0.1
                if timeout_seconds <= 0:
                    self.logger.warning("Timeout waiting for confirmations")
                    break

                await asyncio.sleep(0.1)

        except Exception as e:
            self.logger.error("Error listening for confirmations", error=str(e))

    def _display_active_subscriptions(self):
        """Display currently active subscriptions."""
        self.logger.info("=" * 50)
        self.logger.info("ACTIVE SUBSCRIPTIONS")
        self.logger.info("=" * 50)

        status = self.client.get_connection_status()
        active_subs = self.client.get_active_subscriptions()

        self.logger.info(f"Total subscriptions: {status['subscription_count']}")
        self.logger.info(f"Active channels: {status['active_channels']}")

        for channel, subscriptions in active_subs.items():
            self.logger.info(f"📊 {channel.upper()} channel:")
            for sub in subscriptions:
                self.logger.info(f"  - {sub}")

    async def _demonstrate_unsubscription(self):
        """Demonstrate unsubscription functionality."""
        self.logger.info("=" * 50)
        self.logger.info("DEMONSTRATING UNSUBSCRIPTION")
        self.logger.info("=" * 50)

        # Wait a moment
        await asyncio.sleep(2)

        # Unsubscribe from ticker data
        self.logger.info("Unsubscribing from ticker data for ETH/USD...")
        unsub_result = await self.client.unsubscribe("ticker", ["ETH/USD"])
        self.logger.info("Unsubscription sent", **unsub_result)

        await asyncio.sleep(1)

        # Unsubscribe from orderbook with specific depth
        self.logger.info("Unsubscribing from orderbook ETH/USD depth=25...")
        unsub_result2 = await self.client.unsubscribe("book", ["ETH/USD"], depth=25)
        self.logger.info("Unsubscription sent", **unsub_result2)

        await asyncio.sleep(2)

        # Show updated subscriptions
        self.logger.info("Updated active subscriptions:")
        active_subs = self.client.get_active_subscriptions()
        for channel, subscriptions in active_subs.items():
            self.logger.info(f"📊 {channel.upper()} channel:")
            for sub in subscriptions:
                self.logger.info(f"  - {sub}")

    async def _cleanup(self):
        """Clean up resources."""
        self.logger.info("=" * 50)
        self.logger.info("CLEANING UP")
        self.logger.info("=" * 50)

        try:
            # Show final status
            status = self.client.get_connection_status()
            self.logger.info("Final connection status", **status)

            # Disconnect
            await self.client.disconnect()
            self.logger.info("Disconnected from WebSocket")

        except Exception as e:
            self.logger.error("Error during cleanup", error=str(e))


async def main():
    """Main function to run the subscription example."""
    example = SubscriptionExample()
    await example.run()


if __name__ == "__main__":
    print("=" * 70)
    print("Kraken Trading System - Market Data Subscription Example")
    print("=" * 70)
    print()
    print("This example demonstrates:")
    print("• Subscribing to ticker, orderbook, trade, and OHLC data")
    print("• Handling subscription confirmations")
    print("• Tracking active subscriptions")
    print("• Unsubscribing from specific channels")
    print("• Proper cleanup and resource management")
    print()
    print("Expected behavior:")
    print("1. Connect to Kraken WebSocket")
    print("2. Send 5 different subscription requests")
    print("3. Receive and display subscription confirmations")
    print("4. Show all active subscriptions")
    print("5. Demonstrate unsubscription")
    print("6. Clean up and disconnect")
    print()
    print("Press Ctrl+C to stop the example")
    print("=" * 70)
    print()

    # Run the example
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Example stopped by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)
