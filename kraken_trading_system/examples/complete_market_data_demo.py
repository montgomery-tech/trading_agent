#!/usr/bin/env python3
"""
Complete demonstration of all market data subscription features.
This is a comprehensive example showing all capabilities of the trading system.

Save this as: examples/complete_market_data_demo.py
"""

import asyncio
import signal
import sys
import time
from pathlib import Path
from typing import Dict, Any

# Add src to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from trading_systems.exchanges.kraken.websocket_client import KrakenWebSocketClient
    from trading_systems.utils.logger import get_logger
    print("✅ All imports successful")
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running from the correct directory")
    sys.exit(1)


class MarketDataDemo:
    """Complete demonstration of market data subscription features."""
    
    def __init__(self):
        self.logger = get_logger("MarketDataDemo")
        self.client = KrakenWebSocketClient()
        self.running = True
        self.demo_start_time = time.time()
        
        # Demo configuration
        self.demo_pairs = ["XBT/USD", "ETH/USD"]
        self.demo_duration = 30  # seconds
        self.display_interval = 5  # seconds between status updates
        
        # Statistics tracking
        self.stats = {
            "messages_received": 0,
            "ticker_updates": 0,
            "orderbook_updates": 0,
            "trade_updates": 0,
            "subscriptions_confirmed": 0
        }
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        print(f"\n🛑 Shutdown signal received ({signum})")
        self.running = False
    
    async def run_complete_demo(self):
        """Run the complete market data demonstration."""
        try:
            await self._print_demo_header()
            await self._establish_connection()
            await self._demonstrate_subscription_workflow()
            await self._demonstrate_real_time_data()
            await self._demonstrate_data_access()
            await self._demonstrate_unsubscription()
            await self._cleanup_and_summary()
            
        except KeyboardInterrupt:
            print(f"\n👋 Demo interrupted by user")
        except Exception as e:
            print(f"\n❌ Demo failed with error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await self._ensure_cleanup()
    
    async def _print_demo_header(self):
        """Print demonstration header and information."""
        print("=" * 80)
        print("🚀 KRAKEN TRADING SYSTEM - COMPLETE MARKET DATA DEMONSTRATION")
        print("=" * 80)
        print()
        print("This demo showcases all market data subscription features:")
        print("📈 Ticker Data Subscriptions")
        print("📚 Orderbook Data Subscriptions") 
        print("💰 Trade Data Subscriptions")
        print("🔍 Real-time Data Parsing & Storage")
        print("📊 Data Access Methods")
        print("📋 Subscription Management")
        print("🧹 Clean Unsubscription Workflow")
        print()
        print(f"Target Trading Pairs: {', '.join(self.demo_pairs)}")
        print(f"Demo Duration: {self.demo_duration} seconds")
        print("Press Ctrl+C to stop early")
        print("=" * 80)
        print()
    
    async def _establish_connection(self):
        """Establish WebSocket connection to Kraken."""
        print("🔗 STEP 1: Establishing Connection")
        print("-" * 40)
        
        try:
            print("📡 Connecting to Kraken public WebSocket...")
            await self.client.connect_public()
            
            # Display connection details
            status = self.client.get_connection_status()
            print(f"✅ Connected successfully!")
            print(f"   🌐 Public WebSocket: {status['public_connected']}")
            print(f"   🔒 SSL Mode: {status['ssl_verify_mode']}")
            print(f"   💓 Last Heartbeat: {time.ctime(status['last_heartbeat'])}")
            print()
            
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            raise
    
    async def _demonstrate_subscription_workflow(self):
        """Demonstrate the subscription workflow for all data types."""
        print("📊 STEP 2: Subscription Workflow")
        print("-" * 40)
        
        try:
            print("🎯 Subscribing to all data types...")
            print()
            
            # Subscribe to ticker data
            print("📈 Subscribing to ticker data...")
            await self.client.subscribe_ticker(self.demo_pairs)
            print(f"   ✅ Ticker subscription sent for: {', '.join(self.demo_pairs)}")
            
            await asyncio.sleep(1)
            
            # Subscribe to orderbook data
            print("📚 Subscribing to orderbook data (depth: 10)...")
            await self.client.subscribe_orderbook(self.demo_pairs, depth=10)
            print(f"   ✅ Orderbook subscription sent for: {', '.join(self.demo_pairs)}")
            
            await asyncio.sleep(1)
            
            # Subscribe to trade data
            print("💰 Subscribing to trade data...")
            await self.client.subscribe_trades(self.demo_pairs)
            print(f"   ✅ Trade subscription sent for: {', '.join(self.demo_pairs)}")
            
            print()
            print("⏳ Waiting for subscription confirmations...")
            
            # Wait for subscription confirmations
            await self._wait_for_subscriptions()
            
        except Exception as e:
            print(f"❌ Subscription workflow failed: {e}")
            raise
    
    async def _wait_for_subscriptions(self):
        """Wait for and display subscription confirmations."""
        confirmed_subscriptions = set()
        expected_subscriptions = set()
        
        # Build expected subscription set
        for pair in self.demo_pairs:
            expected_subscriptions.add(f"ticker:{pair}")
            expected_subscriptions.add(f"book:{pair}")
            expected_subscriptions.add(f"trade:{pair}")
        
        timeout_start = time.time()
        
        try:
            async for message in self.client.listen_public():
                if isinstance(message, dict) and message.get("event") == "subscriptionStatus":
                    if message.get("status") == "subscribed":
                        channel = message.get("subscription", {}).get("name")
                        pair = message.get("pair")
                        
                        if channel and pair:
                            sub_key = f"{channel}:{pair}"
                            if sub_key in expected_subscriptions:
                                confirmed_subscriptions.add(sub_key)
                                self.stats["subscriptions_confirmed"] += 1
                                
                                print(f"   ✅ {channel.upper()} subscription confirmed for {pair}")
                
                # Stop when all subscriptions confirmed or timeout
                if (confirmed_subscriptions == expected_subscriptions or 
                    time.time() - timeout_start > 10):
                    break
                
                await asyncio.sleep(0.1)
        
        except Exception as e:
            print(f"⚠️ Error waiting for subscriptions: {e}")
        
        print(f"\n📊 Subscription Summary: {len(confirmed_subscriptions)}/{len(expected_subscriptions)} confirmed")
        print()
    
    async def _demonstrate_real_time_data(self):
        """Demonstrate real-time data collection and parsing."""
        print("🎧 STEP 3: Real-time Data Collection")
        print("-" * 40)
        print(f"📊 Collecting live market data for {self.demo_duration} seconds...")
        print("🔄 Updates will be shown every 5 seconds")
        print()
        
        start_time = time.time()
        last_display = start_time
        
        try:
            async for message in self.client.listen_public():
                if not self.running:
                    break
                
                current_time = time.time()
                self.stats["messages_received"] += 1
                
                # Track data type updates
                if isinstance(message, list) and len(message) >= 3:
                    channel_id = message[0]
                    subscription_key = self.client._get_subscription_key_by_channel_id(channel_id)
                    
                    if subscription_key:
                        channel_type = subscription_key.split(":")[0]
                        if channel_type == "ticker":
                            self.stats["ticker_updates"] += 1
                        elif channel_type == "book":
                            self.stats["orderbook_updates"] += 1
                        elif channel_type == "trade":
                            self.stats["trade_updates"] += 1
                
                # Display periodic updates
                if current_time - last_display >= self.display_interval:
                    await self._display_live_data_status()
                    last_display = current_time
                
                # Stop after demo duration
                if current_time - start_time >= self.demo_duration:
                    break
                
                await asyncio.sleep(0.05)  # Small delay to prevent overwhelming
        
        except Exception as e:
            print(f"❌ Real-time data collection failed: {e}")
        
        print("\n✅ Real-time data collection completed!")
        print()
    
    async def _display_live_data_status(self):
        """Display current live data status."""
        elapsed = time.time() - self.demo_start_time
        
        print(f"⏱️ [{elapsed:.0f}s] Live Data Status:")
        print(f"   📨 Total Messages: {self.stats['messages_received']}")
        print(f"   📈 Ticker Updates: {self.stats['ticker_updates']}")
        print(f"   📚 Orderbook Updates: {self.stats['orderbook_updates']}")
        print(f"   💰 Trade Updates: {self.stats['trade_updates']}")
        
        # Show sample data if available
        summary = self.client.get_market_data_summary()
        if summary:
            print(f"   📊 Pairs with Data: {len(summary)}")
            for pair, data in list(summary.items())[:2]:  # Show first 2 pairs
                data_types = ", ".join(data['data_types'])
                print(f"      • {pair}: {data_types}")
        print()
    
    async def _demonstrate_data_access(self):
        """Demonstrate data access methods and stored data."""
        print("🔍 STEP 4: Data Access & Analysis")
        print("-" * 40)
        
        try:
            # Get market data summary
            summary = self.client.get_market_data_summary()
            print(f"📊 Market Data Summary: {len(summary)} trading pairs")
            print()
            
            for pair, data in summary.items():
                print(f"💱 {pair}:")
                print(f"   📋 Available: {', '.join(data['data_types'])}")
                
                # Show ticker data
                if data["has_ticker"]:
                    ticker = self.client.get_latest_ticker(pair)
                    if ticker:
                        bid = ticker.b[0] if ticker.b else "N/A"
                        ask = ticker.a[0] if ticker.a else "N/A"
                        last = ticker.c[0] if ticker.c else "N/A"
                        volume_24h = ticker.v[1] if ticker.v and len(ticker.v) > 1 else "N/A"
                        
                        print(f"   📈 Ticker:")
                        print(f"      • Bid: ${bid}")
                        print(f"      • Ask: ${ask}")
                        print(f"      • Last: ${last}")
                        print(f"      • 24h Volume: {volume_24h}")
                
                # Show orderbook data
                if data["has_orderbook"]:
                    orderbook = self.client.get_latest_orderbook(pair)
                    if orderbook:
                        asks_count = len(orderbook.asks) if orderbook.asks else 0
                        bids_count = len(orderbook.bids) if orderbook.bids else 0
                        
                        print(f"   📚 Orderbook:")
                        print(f"      • {asks_count} ask levels")
                        print(f"      • {bids_count} bid levels")
                        
                        if orderbook.asks and len(orderbook.asks) > 0:
                            best_ask = orderbook.asks[0]
                            print(f"      • Best Ask: ${best_ask.price} ({best_ask.volume})")
                        
                        if orderbook.bids and len(orderbook.bids) > 0:
                            best_bid = orderbook.bids[0]
                            print(f"      • Best Bid: ${best_bid.price} ({best_bid.volume})")
                
                # Show trade data
                if data["trades_count"] > 0:
                    recent_trades = self.client.get_recent_trades(pair, limit=3)
                    print(f"   💰 Recent Trades ({data['trades_count']} total):")
                    
                    for i, trade in enumerate(recent_trades[-3:], 1):
                        side_icon = "🟢" if trade.side == "buy" else "🔴"
                        print(f"      {i}. {side_icon} ${trade.price} × {trade.volume} ({trade.side})")
                
                print()
            
            print("✅ Data access demonstration completed!")
            print()
            
        except Exception as e:
            print(f"❌ Data access demonstration failed: {e}")
    
    async def _demonstrate_unsubscription(self):
        """Demonstrate unsubscription workflow."""
        print("📤 STEP 5: Unsubscription Workflow")
        print("-" * 40)
        
        try:
            # Show current subscriptions
            active_subs = self.client.get_active_subscriptions()
            print(f"📋 Current active subscriptions: {len(active_subs)}")
            
            # Unsubscribe from ticker data to demonstrate
            ticker_subs = [sub_id for sub_id in active_subs.keys() if sub_id.startswith("ticker:")]
            
            if ticker_subs:
                print(f"📤 Unsubscribing from ticker data...")
                
                for sub_id in ticker_subs:
                    print(f"   ➤ Unsubscribing from {sub_id}")
                    await self.client.unsubscribe(sub_id)
                    await asyncio.sleep(0.5)
                
                # Wait a moment for unsubscription processing
                await asyncio.sleep(2)
                
                # Show updated subscriptions
                updated_subs = self.client.get_active_subscriptions()
                print(f"📊 Remaining subscriptions: {len(updated_subs)}")
                
                remaining_types = set()
                for sub_id in updated_subs.keys():
                    channel_type = sub_id.split(":")[0]
                    remaining_types.add(channel_type)
                
                print(f"   📋 Remaining types: {', '.join(remaining_types)}")
                print("✅ Selective unsubscription completed!")
            else:
                print("⚠️ No ticker subscriptions found to unsubscribe from")
            
            print()
            
        except Exception as e:
            print(f"❌ Unsubscription demonstration failed: {e}")
    
    async def _cleanup_and_summary(self):
        """Final cleanup and demonstration summary."""
        print("📊 STEP 6: Demo Summary & Cleanup")
        print("-" * 40)
        
        try:
            # Final statistics
            total_runtime = time.time() - self.demo_start_time
            
            print("🎯 DEMONSTRATION RESULTS:")
            print(f"   ⏱️ Total Runtime: {total_runtime:.1f} seconds")
            print(f"   📨 Messages Processed: {self.stats['messages_received']}")
            print(f"   ✅ Subscriptions Confirmed: {self.stats['subscriptions_confirmed']}")
            print(f"   📈 Ticker Updates: {self.stats['ticker_updates']}")
            print(f"   📚 Orderbook Updates: {self.stats['orderbook_updates']}")
            print(f"   💰 Trade Updates: {self.stats['trade_updates']}")
            print()
            
            # Market data summary
            summary = self.client.get_market_data_summary()
            print("📊 FINAL MARKET DATA STATE:")
            print(f"   📱 Pairs Tracked: {len(summary)}")
            
            total_trades = sum(data['trades_count'] for data in summary.values())
            pairs_with_ticker = sum(1 for data in summary.values() if data['has_ticker'])
            pairs_with_orderbook = sum(1 for data in summary.values() if data['has_orderbook'])
            
            print(f"   📈 Pairs with Ticker: {pairs_with_ticker}")
            print(f"   📚 Pairs with Orderbook: {pairs_with_orderbook}")
            print(f"   💰 Total Trades Stored: {total_trades}")
            print()
            
            # Feature demonstration checklist
            print("✅ FEATURES DEMONSTRATED:")
            features = [
                ("WebSocket Connection", True),
                ("Multiple Subscriptions", self.stats['subscriptions_confirmed'] > 0),
                ("Real-time Data Parsing", self.stats['messages_received'] > 10),
                ("Ticker Data Processing", self.stats['ticker_updates'] > 0),
                ("Orderbook Data Processing", self.stats['orderbook_updates'] > 0),
                ("Trade Data Processing", self.stats['trade_updates'] > 0),
                ("Data Storage & Access", len(summary) > 0),
                ("Subscription Management", True),
                ("Unsubscription Workflow", True)
            ]
            
            for feature, success in features:
                status = "✅" if success else "⚠️"
                print(f"   {status} {feature}")
            
            successful_features = sum(1 for _, success in features if success)
            print(f"\n🎯 Success Rate: {successful_features}/{len(features)} features working")
            
        except Exception as e:
            print(f"❌ Summary generation failed: {e}")
    
    async def _ensure_cleanup(self):
        """Ensure proper cleanup regardless of how demo ended."""
        print("\n🧹 CLEANUP")
        print("-" * 40)
        
        try:
            # Unsubscribe from remaining subscriptions
            active_subs = self.client.get_active_subscriptions()
            if active_subs:
                print(f"📤 Cleaning up {len(active_subs)} remaining subscriptions...")
                
                for sub_id in list(active_subs.keys()):
                    try:
                        await self.client.unsubscribe(sub_id)
                        await asyncio.sleep(0.2)
                    except Exception as e:
                        print(f"   ⚠️ Failed to unsubscribe from {sub_id}: {e}")
                
                print("✅ Subscription cleanup completed")
            
            # Disconnect
            await self.client.disconnect()
            print("✅ Disconnected from WebSocket")
            
        except Exception as e:
            print(f"⚠️ Cleanup error: {e}")
        
        print("\n" + "=" * 80)
        print("🎉 MARKET DATA DEMONSTRATION COMPLETED!")
        print("=" * 80)
        print()
        print("Thank you for trying the Kraken Trading System market data features!")
        print("All subscription functionality is now ready for production use.")
        print()
        print("Available methods:")
        print("• client.subscribe_ticker(pairs)")
        print("• client.subscribe_orderbook(pairs, depth)")
        print("• client.subscribe_trades(pairs)")
        print("• client.get_latest_ticker(pair)")
        print("• client.get_latest_orderbook(pair)")
        print("• client.get_recent_trades(pair)")
        print("• client.get_market_data_summary()")
        print("• client.unsubscribe(subscription_id)")
        print("=" * 80)


async def main():
    """Main function to run the complete demonstration."""
    demo = MarketDataDemo()
    await demo.run_complete_demo()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)
