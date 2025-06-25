"""
Market Data Subscription Example

This example demonstrates how to use the new subscription methods
to subscribe to ticker, orderbook, and trade data from Kraken.

Save this as: examples/market_data_subscriptions.py
"""

import asyncio
import signal
import sys
from pathlib import Path

# Add src to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from trading_system.exchanges.kraken.websocket_client import KrakenWebSocketClient
from trading_system.utils.logger import get_logger


class MarketDataSubscriptionExample:
    """Demonstrate market data subscriptions."""
    
    def __init__(self):
        self.logger = get_logger("MarketDataSubscriptionExample")
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
            
            # Display initial connection status
            status = self.client.get_connection_status()
            self.logger.info("Connection status", **status)
            
            # Subscribe to different data types
            await self._demonstrate_subscriptions()
            
            # Listen for messages and display subscription results
            await self._listen_for_subscription_data()
            
        except KeyboardInterrupt:
            self.logger.info("Interrupted by user")
        except Exception as e:
            self.logger.error("Error in example", error=str(e), exc_info=True)
        finally:
            await self._cleanup()
    
    async def _demonstrate_subscriptions(self):
        """Demonstrate different subscription methods."""
        pairs = ["XBT/USD", "ETH/USD"]
        
        self.logger.info("=== SUBSCRIPTION DEMONSTRATION ===")
        
        # 1. Subscribe to ticker data
        self.logger.info("📊 Subscribing to ticker data", pairs=pairs)
        await self.client.subscribe_ticker(pairs)
        await asyncio.sleep(2)  # Wait for subscription confirmation
        
        # 2. Subscribe to orderbook data
        self.logger.info("📚 Subscribing to orderbook data", pairs=pairs, depth=10)
        await self.client.subscribe_orderbook(pairs, depth=10)
        await asyncio.sleep(2)  # Wait for subscription confirmation
        
        # 3. Subscribe to trade data
        self.logger.info("💰 Subscribing to trade data", pairs=pairs)
        await self.client.subscribe_trades(pairs)
        await asyncio.sleep(2)  # Wait for subscription confirmation
        
        # Display active subscriptions
        active_subs = self.client.get_active_subscriptions()
        self.logger.info("📋 Active subscriptions", count=len(active_subs))
        for sub_id, details in active_subs.items():
            self.logger.info(
                "Subscription",
                id=sub_id,
                channel=details["channel"],
                pair=details["pair"],
                channel_id=details["channel_id"]
            )
    
    async def _listen_for_subscription_data(self):
        """Listen for and categorize incoming subscription data."""
        self.logger.info("🎧 Listening for subscription data (Press Ctrl+C to stop)...")
        
        message_counts = {
            "ticker": 0,
            "book": 0, 
            "trade": 0,
            "other": 0
        }
        
        total_messages = 0
        max_messages = 100  # Limit for demo
        
        try:
            async for message in self.client.listen_public():
                if not self.running:
                    break
                
                total_messages += 1
                
                # Categorize and display messages
                message_type = self._categorize_message(message)
                message_counts[message_type] += 1
                
                if message_type in ["ticker", "book", "trade"]:
                    self.logger.info(
                        f"📈 {message_type.upper()} data received",
                        channel_id=message.get("channelID"),
                        data_points=len(message) if isinstance(message, list) else 1
                    )
                elif message_type == "other":
                    event = message.get("event", "unknown")
                    if event == "subscriptionStatus":
                        self.logger.info(
                            "✅ Subscription status",
                            status=message.get("status"),
                            channel=message.get("subscription", {}).get("name"),
                            pair=message.get("pair")
                        )
                    elif event == "heartbeat":
                        self.logger.info("💓 Heartbeat received")
                    else:
                        self.logger.info(f"📨 Other message: {event}")
                
                # Display periodic summary
                if total_messages % 20 == 0:
                    self.logger.info(
                        "📊 Message Summary",
                        total=total_messages,
                        ticker=message_counts["ticker"],
                        orderbook=message_counts["book"],
                        trades=message_counts["trade"],
                        other=message_counts["other"]
                    )
                
                # Stop after max messages for demo
                if total_messages >= max_messages:
                    self.logger.info(f"Received {max_messages} messages, stopping demo")
                    break
                
                # Small delay to avoid overwhelming the console
                await asyncio.sleep(0.1)
        
        except Exception as e:
            self.logger.error("Error listening for messages", error=str(e))
        
        # Final summary
        self.logger.info(
            "📈 Final Statistics",
            total_messages=total_messages,
            ticker_messages=message_counts["ticker"],
            orderbook_messages=message_counts["book"],
            trade_messages=message_counts["trade"],
            other_messages=message_counts["other"]
        )
    
    def _categorize_message(self, message):
        """Categorize incoming messages by type."""
        if isinstance(message, list):
            # Array messages are market data
            # Channel ID should help us determine the type
            # For now, we'll categorize as "data"
            return "data"
        elif isinstance(message, dict):
            event = message.get("event")
            if event in ["systemStatus", "subscriptionStatus", "heartbeat"]:
                return "other"
            
            # Try to determine data type from channel info
            channel_name = message.get("channelName", "")
            if "ticker" in channel_name.lower():
                return "ticker"
            elif "book" in channel_name.lower():
                return "book" 
            elif "trade" in channel_name.lower():
                return "trade"
            else:
                return "other"
        
        return "unknown"
    
    async def _cleanup(self):
        """Clean up resources and demonstrate unsubscription."""
        self.logger.info("🧹 Cleaning up...")
        
        # Demonstrate unsubscription
        active_subs = self.client.get_active_subscriptions()
        if active_subs:
            self.logger.info("📤 Unsubscribing from active subscriptions")
            for sub_id in list(active_subs.keys()):
                try:
                    await self.client.unsubscribe(sub_id)
                    self.logger.info(f"✅ Unsubscribed from {sub_id}")
                    await asyncio.sleep(0.5)  # Brief delay between unsubscriptions
                except Exception as e:
                    self.logger.error(f"Failed to unsubscribe from {sub_id}", error=str(e))
        
        # Disconnect
        try:
            await self.client.disconnect()
            self.logger.info("Disconnected from WebSocket")
        except Exception as e:
            self.logger.error("Error during cleanup", error=str(e))


async def main():
    """Main function to run the example."""
    example = MarketDataSubscriptionExample()
    await example.run()


if __name__ == "__main__":
    print("=" * 70)
    print("Kraken Trading System - Market Data Subscription Example")
    print("=" * 70)
    print()
    print("This example demonstrates:")
    print("• Subscribing to ticker data for multiple pairs")
    print("• Subscribing to orderbook data with custom depth")
    print("• Subscribing to trade data")
    print("• Managing active subscriptions")
    print("• Receiving and categorizing market data")
    print("• Graceful unsubscription and cleanup")
    print()
    print("Trading pairs: XBT/USD, ETH/USD")
    print("Orderbook depth: 10 levels")
    print("Max messages: 100 (for demo)")
    print()
    print("Press Ctrl+C to stop the example")
    print("=" * 70)
    print()
    
    # Run the example
    asyncio.run(main())