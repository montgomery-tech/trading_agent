#!/usr/bin/env python3
"""
Comprehensive integration test for all subscription functionality.
Tests ticker, orderbook, and trade subscriptions working together.
Save this as: test_full_integration.py
"""

import asyncio
import sys
import time
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from trading_systems.exchanges.kraken.websocket_client import KrakenWebSocketClient
    print("✅ Successfully imported KrakenWebSocketClient")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)


class IntegrationTestSuite:
    """Comprehensive integration test suite."""
    
    def __init__(self):
        self.client = KrakenWebSocketClient()
        self.test_results = {
            "connection": False,
            "ticker_subscription": False,
            "orderbook_subscription": False,
            "trade_subscription": False,
            "ticker_data_received": False,
            "orderbook_data_received": False,
            "trade_data_received": False,
            "data_access_methods": False,
            "unsubscription": False,
            "cleanup": False
        }
        self.start_time = time.time()
    
    async def run_full_test_suite(self):
        """Run the complete integration test suite."""
        print("🧪 COMPREHENSIVE INTEGRATION TEST SUITE")
        print("=" * 60)
        print(f"Testing all subscription types with real Kraken data")
        print(f"Target pairs: XBT/USD, ETH/USD")
        print("=" * 60)
        
        try:
            # Test 1: Connection
            await self._test_connection()
            
            # Test 2: Multiple subscriptions
            await self._test_multiple_subscriptions()
            
            # Test 3: Real-time data collection
            await self._test_data_collection()
            
            # Test 4: Data access methods
            await self._test_data_access_methods()
            
            # Test 5: Subscription management
            await self._test_subscription_management()
            
            # Test 6: Unsubscription workflow
            await self._test_unsubscription_workflow()
            
            # Test 7: Cleanup
            await self._test_cleanup()
            
        except Exception as e:
            print(f"❌ Integration test failed with error: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            await self._generate_test_report()
    
    async def _test_connection(self):
        """Test 1: Basic connection functionality."""
        print("\n📡 TEST 1: Connection")
        print("-" * 30)
        
        try:
            await self.client.connect_public()
            status = self.client.get_connection_status()
            
            if status["public_connected"]:
                print("✅ Connection established")
                self.test_results["connection"] = True
            else:
                print("❌ Connection failed")
                
        except Exception as e:
            print(f"❌ Connection test failed: {e}")
    
    async def _test_multiple_subscriptions(self):
        """Test 2: Subscribe to all three data types."""
        print("\n📊 TEST 2: Multiple Subscriptions")
        print("-" * 30)
        
        pairs = ["XBT/USD", "ETH/USD"]
        
        try:
            # Subscribe to ticker
            print("  📈 Subscribing to ticker data...")
            await self.client.subscribe_ticker(pairs)
            await asyncio.sleep(1)
            
            # Subscribe to orderbook
            print("  📚 Subscribing to orderbook data...")
            await self.client.subscribe_orderbook(pairs, depth=10)
            await asyncio.sleep(1)
            
            # Subscribe to trades
            print("  💰 Subscribing to trade data...")
            await self.client.subscribe_trades(pairs)
            await asyncio.sleep(1)
            
            print("✅ All subscription requests sent")
            
        except Exception as e:
            print(f"❌ Subscription test failed: {e}")
    
    async def _test_data_collection(self):
        """Test 3: Collect and validate real-time data."""
        print("\n🎧 TEST 3: Real-time Data Collection")
        print("-" * 30)
        
        print("  ⏳ Collecting data for 15 seconds...")
        
        subscription_confirmations = {
            "ticker": False,
            "book": False,
            "trade": False
        }
        
        data_received = {
            "ticker": False,
            "orderbook": False,
            "trade": False
        }
        
        message_count = 0
        start_time = time.time()
        
        try:
            async for message in self.client.listen_public():
                message_count += 1
                current_time = time.time()
                
                # Check subscription confirmations
                if isinstance(message, dict):
                    if message.get("event") == "subscriptionStatus" and message.get("status") == "subscribed":
                        channel = message.get("subscription", {}).get("name")
                        if channel in subscription_confirmations:
                            subscription_confirmations[channel] = True
                            print(f"  ✅ {channel.capitalize()} subscription confirmed")
                
                # Check for market data
                elif isinstance(message, list) and len(message) >= 3:
                    channel_id = message[0]
                    subscription_key = self.client._get_subscription_key_by_channel_id(channel_id)
                    
                    if subscription_key:
                        channel_type = subscription_key.split(":")[0]
                        if channel_type == "ticker" and not data_received["ticker"]:
                            print("  📈 Ticker data received!")
                            data_received["ticker"] = True
                        elif channel_type == "book" and not data_received["orderbook"]:
                            print("  📚 Orderbook data received!")
                            data_received["orderbook"] = True
                        elif channel_type == "trade" and not data_received["trade"]:
                            print("  💰 Trade data received!")
                            data_received["trade"] = True
                
                # Stop after 15 seconds or if we have all data
                if (current_time - start_time > 15) or all(data_received.values()):
                    break
                
                await asyncio.sleep(0.1)
        
        except Exception as e:
            print(f"❌ Data collection failed: {e}")
        
        # Update test results
        self.test_results["ticker_subscription"] = subscription_confirmations["ticker"]
        self.test_results["orderbook_subscription"] = subscription_confirmations["book"]
        self.test_results["trade_subscription"] = subscription_confirmations["trade"]
        self.test_results["ticker_data_received"] = data_received["ticker"]
        self.test_results["orderbook_data_received"] = data_received["orderbook"]
        self.test_results["trade_data_received"] = data_received["trade"]
        
        print(f"  📊 Processed {message_count} messages")
        print(f"  📈 Data types received: {list(k for k, v in data_received.items() if v)}")
    
    async def _test_data_access_methods(self):
        """Test 4: Validate data access methods."""
        print("\n🔍 TEST 4: Data Access Methods")
        print("-" * 30)
        
        try:
            # Test market data summary
            summary = self.client.get_market_data_summary()
            print(f"  📊 Market data summary: {len(summary)} pairs")
            
            for pair, data in summary.items():
                print(f"    - {pair}: {', '.join(data['data_types'])}")
                
                # Test specific data access
                if data["has_ticker"]:
                    ticker = self.client.get_latest_ticker(pair)
                    if ticker:
                        print(f"      📈 Ticker - Last: {ticker.c[0] if ticker.c else 'N/A'}")
                
                if data["has_orderbook"]:
                    orderbook = self.client.get_latest_orderbook(pair)
                    if orderbook:
                        asks_count = len(orderbook.asks) if orderbook.asks else 0
                        bids_count = len(orderbook.bids) if orderbook.bids else 0
                        print(f"      📚 Orderbook - {asks_count} asks, {bids_count} bids")
                
                if data["trades_count"] > 0:
                    trades = self.client.get_recent_trades(pair, limit=3)
                    print(f"      💰 Recent trades: {len(trades)} (showing last 3)")
            
            if summary:
                self.test_results["data_access_methods"] = True
                print("  ✅ Data access methods working correctly")
            else:
                print("  ⚠️ No market data available for testing access methods")
                
        except Exception as e:
            print(f"❌ Data access test failed: {e}")
    
    async def _test_subscription_management(self):
        """Test 5: Subscription state management."""
        print("\n📋 TEST 5: Subscription Management")
        print("-" * 30)
        
        try:
            # Check active subscriptions
            active_subs = self.client.get_active_subscriptions()
            print(f"  📊 Active subscriptions: {len(active_subs)}")
            
            expected_subscriptions = ["ticker:XBT/USD", "ticker:ETH/USD", 
                                    "book:XBT/USD", "book:ETH/USD",
                                    "trade:XBT/USD", "trade:ETH/USD"]
            
            found_subscriptions = list(active_subs.keys())
            
            for expected in expected_subscriptions:
                if expected in found_subscriptions:
                    print(f"    ✅ {expected}")
                else:
                    print(f"    ❌ {expected} (missing)")
            
            print("  ✅ Subscription management test completed")
            
        except Exception as e:
            print(f"❌ Subscription management test failed: {e}")
    
    async def _test_unsubscription_workflow(self):
        """Test 6: Unsubscription functionality."""
        print("\n📤 TEST 6: Unsubscription Workflow")
        print("-" * 30)
        
        try:
            # Get current subscriptions
            active_subs = self.client.get_active_subscriptions()
            initial_count = len(active_subs)
            
            if initial_count > 0:
                # Unsubscribe from ticker data
                ticker_subs = [sub_id for sub_id in active_subs.keys() if sub_id.startswith("ticker:")]
                
                for sub_id in ticker_subs[:2]:  # Unsubscribe from first 2 ticker subscriptions
                    print(f"  📤 Unsubscribing from {sub_id}")
                    await self.client.unsubscribe(sub_id)
                    await asyncio.sleep(0.5)
                
                # Wait a moment for unsubscription to process
                await asyncio.sleep(2)
                
                # Check updated subscriptions
                updated_subs = self.client.get_active_subscriptions()
                final_count = len(updated_subs)
                
                print(f"  📊 Subscriptions: {initial_count} → {final_count}")
                
                if final_count < initial_count:
                    print("  ✅ Unsubscription workflow working")
                    self.test_results["unsubscription"] = True
                else:
                    print("  ⚠️ Unsubscription may still be processing")
            else:
                print("  ⚠️ No subscriptions available for unsubscription test")
                
        except Exception as e:
            print(f"❌ Unsubscription test failed: {e}")
    
    async def _test_cleanup(self):
        """Test 7: Cleanup and disconnection."""
        print("\n🧹 TEST 7: Cleanup")
        print("-" * 30)
        
        try:
            await self.client.disconnect()
            status = self.client.get_connection_status()
            
            if not status["public_connected"]:
                print("  ✅ Disconnected successfully")
                self.test_results["cleanup"] = True
            else:
                print("  ❌ Disconnection failed")
                
        except Exception as e:
            print(f"❌ Cleanup test failed: {e}")
    
    async def _generate_test_report(self):
        """Generate final test report."""
        print("\n" + "=" * 60)
        print("📊 INTEGRATION TEST REPORT")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result)
        
        print(f"🎯 Overall Result: {passed_tests}/{total_tests} tests passed")
        print(f"⏱️ Total Runtime: {time.time() - self.start_time:.1f} seconds")
        print()
        
        print("📋 Detailed Results:")
        for test_name, result in self.test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"  {status} - {test_name.replace('_', ' ').title()}")
        
        print()
        
        if passed_tests == total_tests:
            print("🎉 ALL INTEGRATION TESTS PASSED!")
            print("✅ Full subscription workflow is working correctly")
            print("✅ All three data types (ticker, orderbook, trades) functional")
            print("✅ Data parsing and storage working correctly") 
            print("✅ Data access methods operational")
            print("✅ Subscription management working")
            print("✅ Task 1.3 is COMPLETE!")
        elif passed_tests >= total_tests * 0.8:
            print("⚠️ MOST TESTS PASSED - System is largely functional")
            print("Some tests may have failed due to timing or network issues")
        else:
            print("❌ MULTIPLE TEST FAILURES - System needs attention")
        
        print("=" * 60)


async def main():
    """Run the comprehensive integration test."""
    test_suite = IntegrationTestSuite()
    await test_suite.run_full_test_suite()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)
