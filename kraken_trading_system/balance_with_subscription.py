#!/usr/bin/env python3
"""
Account Balance Retrieval with Explicit Subscription

The WebSocket connection works, but we need to explicitly subscribe to balance feeds
to get account balance data. This script subscribes to the necessary feeds and waits
for balance data to populate.
"""

import asyncio
import json
import sys
import time
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional, Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from trading_systems.exchanges.kraken.websocket_client import KrakenWebSocketClient
    from trading_systems.config.settings import settings
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)


class AccountBalanceWithSubscription:
    """Account balance retrieval with explicit balance feed subscription."""
    
    def __init__(self):
        self.websocket_client = None
        self.current_prices = {}
        self.balance_data_received = False
        
    async def connect_and_subscribe(self) -> bool:
        """Connect to WebSocket and subscribe to balance feeds."""
        print("🔗 CONNECTING AND SUBSCRIBING TO BALANCE FEEDS")
        print("-" * 50)
        
        try:
            self.websocket_client = KrakenWebSocketClient()
            await self.websocket_client.connect_private()
            
            if not self.websocket_client.is_private_connected:
                print("❌ Private WebSocket connection failed")
                return False
            
            print("✅ Connected to private WebSocket")
            
            # Wait for initial connection setup
            await asyncio.sleep(2)
            
            # Subscribe to account data feeds
            print("📊 Subscribing to account data feeds...")
            
            try:
                # Subscribe to own trades (this often triggers balance updates)
                await self.websocket_client.subscribe_own_trades()
                print("✅ Subscribed to ownTrades feed")
                
                # Subscribe to open orders
                await self.websocket_client.subscribe_open_orders()
                print("✅ Subscribed to openOrders feed")
                
                # Wait for subscriptions to be confirmed and data to arrive
                print("⏳ Waiting for account data to populate...")
                await asyncio.sleep(5)
                
                return True
                
            except Exception as e:
                print(f"⚠️ Subscription error: {e}")
                # Continue anyway - connection might still work
                return True
                
        except Exception as e:
            print(f"❌ Connection error: {e}")
            return False
    
    async def check_balance_data_multiple_times(self) -> bool:
        """Check for balance data multiple times with delays."""
        print("\n🔍 CHECKING FOR BALANCE DATA")
        print("-" * 50)
        
        max_attempts = 10
        
        for attempt in range(max_attempts):
            print(f"📊 Attempt {attempt + 1}/{max_attempts}: Checking account snapshot...")
            
            try:
                snapshot = await self.websocket_client.get_account_snapshot()
                
                if snapshot:
                    balance_count = len(snapshot.balances)
                    orders_count = len(snapshot.open_orders)
                    trades_count = len(snapshot.recent_trades)
                    
                    print(f"   📊 Balances: {balance_count}")
                    print(f"   📊 Open orders: {orders_count}")
                    print(f"   📊 Recent trades: {trades_count}")
                    
                    if balance_count > 0:
                        print("✅ Balance data found!")
                        self.balance_data_received = True
                        return True
                    elif orders_count > 0 or trades_count > 0:
                        print("📊 Some account data found, balances may still be loading...")
                    else:
                        print("⏳ No account data yet, waiting...")
                else:
                    print("❌ No account snapshot available")
                
                # Wait before next attempt
                if attempt < max_attempts - 1:
                    await asyncio.sleep(3)
                    
            except Exception as e:
                print(f"❌ Error checking snapshot: {e}")
                await asyncio.sleep(2)
        
        print("⚠️ No balance data received after multiple attempts")
        return False
    
    async def try_rest_api_fallback(self) -> Dict[str, Any]:
        """Try REST API as fallback for balance data."""
        print("\n🔄 TRYING REST API FALLBACK FOR BALANCE DATA")
        print("-" * 50)
        
        try:
            from trading_systems.exchanges.kraken.rest_client import EnhancedKrakenRestClient
            
            rest_client = EnhancedKrakenRestClient()
            
            # Test authentication
            auth_ok = await rest_client.test_authentication()
            if not auth_ok:
                print("❌ REST API authentication failed")
                return {}
            
            print("✅ REST API authentication successful")
            
            # Get balance data
            balance_response = await rest_client.get_account_balance()
            
            if "result" in balance_response:
                balances = balance_response["result"]
                print(f"✅ Retrieved {len(balances)} balance entries via REST API")
                
                # Filter out zero balances
                non_zero_balances = {k: v for k, v in balances.items() if float(v) > 0}
                print(f"📊 Non-zero balances: {len(non_zero_balances)}")
                
                return non_zero_balances
            else:
                print(f"❌ Invalid REST API response: {balance_response}")
                return {}
                
        except Exception as e:
            print(f"❌ REST API fallback failed: {e}")
            return {}
    
    async def display_balance_comparison(self, rest_balances: Dict[str, Any]):
        """Display balance data from both WebSocket and REST API."""
        print("\n📊 BALANCE DATA COMPARISON")
        print("=" * 70)
        
        # WebSocket balances
        ws_balances = {}
        if self.websocket_client:
            try:
                snapshot = await self.websocket_client.get_account_snapshot()
                if snapshot and snapshot.balances:
                    ws_balances = {
                        currency: float(balance.balance) 
                        for currency, balance in snapshot.balances.items() 
                        if balance.balance > 0
                    }
            except:
                pass
        
        print(f"📊 WebSocket Balances: {len(ws_balances)} currencies")
        print(f"📊 REST API Balances: {len(rest_balances)} currencies")
        print()
        
        # Combine all currencies
        all_currencies = set(ws_balances.keys()) | set(rest_balances.keys())
        
        if not all_currencies:
            print("❌ No balance data available from either source")
            print()
            print("💡 POSSIBLE REASONS:")
            print("   • Account has zero balances")
            print("   • API permissions don't include balance access")
            print("   • WebSocket feeds need more time to populate")
            print("   • Account data subscriptions not working")
            return
        
        print("💰 BALANCE BREAKDOWN:")
        print("-" * 70)
        print(f"{'Currency':<10} {'WebSocket':<15} {'REST API':<15} {'Status':<15}")
        print("-" * 70)
        
        for currency in sorted(all_currencies):
            ws_amount = ws_balances.get(currency, 0.0)
            rest_amount = float(rest_balances.get(currency, '0'))
            
            ws_str = f"{ws_amount:.6f}".rstrip('0').rstrip('.') if ws_amount > 0 else "-"
            rest_str = f"{rest_amount:.6f}".rstrip('0').rstrip('.') if rest_amount > 0 else "-"
            
            if ws_amount > 0 and rest_amount > 0:
                status = "✅ Both"
            elif rest_amount > 0:
                status = "🔄 REST only"
            elif ws_amount > 0:
                status = "📡 WS only"
            else:
                status = "❌ Neither"
            
            print(f"{currency:<10} {ws_str:<15} {rest_str:<15} {status:<15}")
        
        print("-" * 70)
        
        # Analysis
        print("\n🔍 ANALYSIS:")
        if len(rest_balances) > len(ws_balances):
            print("📊 REST API shows more balance data than WebSocket")
            print("💡 WebSocket account data feeds may need more time or different subscriptions")
        elif len(ws_balances) > 0:
            print("📊 WebSocket balance data is working")
        else:
            print("📊 WebSocket account data is not populating")
            print("💡 Use REST API fallback for reliable balance data")
    
    async def test_websocket_message_monitoring(self):
        """Monitor WebSocket messages to see what's being received."""
        print("\n🔍 MONITORING WEBSOCKET MESSAGES")
        print("-" * 50)
        
        if not self.websocket_client or not self.websocket_client.is_private_connected:
            print("❌ No private WebSocket connection")
            return
        
        print("📡 Monitoring private WebSocket messages for 10 seconds...")
        print("Looking for balance-related data...")
        
        # Monitor messages for a short time
        start_time = time.time()
        message_count = 0
        
        try:
            while time.time() - start_time < 10:  # Monitor for 10 seconds
                try:
                    if not self.websocket_client.private_message_queue.empty():
                        message = await asyncio.wait_for(
                            self.websocket_client.private_message_queue.get(), 
                            timeout=1.0
                        )
                        
                        message_count += 1
                        
                        # Analyze message
                        if isinstance(message, list) and len(message) >= 3:
                            channel = message[2] if len(message) > 2 else 'unknown'
                            data = message[1] if len(message) > 1 else {}
                            
                            print(f"📨 Message {message_count}: {channel}")
                            
                            if channel == 'ownTrades':
                                print("   💹 Trade data received")
                            elif channel == 'openOrders':
                                print("   📋 Order data received")
                            elif 'balance' in str(message).lower():
                                print("   💰 Balance-related data!")
                        
                        elif isinstance(message, dict):
                            if any(key in message for key in ['balance', 'USD', 'ETH', 'BTC']):
                                print(f"📨 Potential balance data: {list(message.keys())}")
                        
                        # Put message back for other processors
                        await self.websocket_client.private_message_queue.put(message)
                    else:
                        await asyncio.sleep(0.1)
                        
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    print(f"⚠️ Message monitoring error: {e}")
                    break
                    
        except Exception as e:
            print(f"❌ Message monitoring failed: {e}")
        
        print(f"📊 Monitored {message_count} messages")
        if message_count == 0:
            print("⚠️ No private messages received - account data feeds may not be active")
    
    async def cleanup(self):
        """Clean up connections."""
        if self.websocket_client:
            try:
                await self.websocket_client.disconnect()
                print("✅ WebSocket disconnected")
            except:
                pass
    
    async def run_balance_retrieval_with_subscription(self):
        """Run complete balance retrieval with subscription and fallback."""
        try:
            print("🚀 ACCOUNT BALANCE RETRIEVAL WITH EXPLICIT SUBSCRIPTION")
            print("=" * 70)
            print("🔧 Approach: Subscribe to account feeds and monitor for data")
            print("🔄 Fallback: Use REST API if WebSocket data doesn't populate")
            print("=" * 70)
            
            # Step 1: Connect and subscribe
            connected = await self.connect_and_subscribe()
            if not connected:
                print("❌ Connection failed")
                return False
            
            # Step 2: Monitor messages to see what's happening
            await self.test_websocket_message_monitoring()
            
            # Step 3: Check for balance data multiple times
            balance_found = await self.check_balance_data_multiple_times()
            
            # Step 4: Try REST API fallback
            rest_balances = await self.try_rest_api_fallback()
            
            # Step 5: Compare results
            await self.display_balance_comparison(rest_balances)
            
            # Summary
            print("\n🎉 BALANCE RETRIEVAL ANALYSIS COMPLETED!")
            print("=" * 50)
            print(f"✅ WebSocket connection: WORKING")
            print(f"✅ Account subscriptions: ATTEMPTED")
            print(f"✅ Balance data found: {'YES' if balance_found else 'NO'}")
            print(f"✅ REST API fallback: {'WORKING' if rest_balances else 'FAILED'}")
            
            if rest_balances:
                print(f"✅ Reliable balance data available via REST API")
                print("💡 Recommend using REST API fallback for balance retrieval")
            elif balance_found:
                print(f"✅ WebSocket balance data working")
            else:
                print("⚠️ No balance data available from either source")
            
            return True
            
        except Exception as e:
            print(f"❌ Balance retrieval with subscription failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            await self.cleanup()


async def main():
    """Main execution function."""
    retriever = AccountBalanceWithSubscription()
    success = await retriever.run_balance_retrieval_with_subscription()
    
    if success:
        print("🎉 BALANCE ANALYSIS COMPLETED!")
    else:
        print("❌ Balance analysis failed")
    
    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
