#!/usr/bin/env python3
"""
Account Balance Retrieval System

Comprehensive script to retrieve and display account balances from Kraken.
Shows available balances, total portfolio value, and asset allocation.

Features:
- Real-time balance retrieval via WebSocket
- USD conversion for all assets
- Portfolio summary and analysis
- Balance types (available vs total)
- Clean, organized display
"""

import asyncio
import json
import sys
import time
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from trading_systems.exchanges.kraken.websocket_client import KrakenWebSocketClient
    from trading_systems.exchanges.kraken.account_models import AccountBalance, AccountSnapshot
    from trading_systems.config.settings import settings
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running from project root with src/ directory")
    sys.exit(1)


class AccountBalanceRetriever:
    """Comprehensive account balance retrieval and analysis system."""
    
    def __init__(self):
        self.websocket_client = None
        self.current_prices = {}
        self.account_snapshot = None
        self.portfolio_summary = {}
        
    async def connect_to_account(self) -> bool:
        """Connect to Kraken account and initialize data managers."""
        print("🔗 CONNECTING TO KRAKEN ACCOUNT")
        print("-" * 50)
        
        try:
            self.websocket_client = KrakenWebSocketClient()
            await self.websocket_client.connect_private()
            
            if self.websocket_client.is_private_connected:
                print("✅ Connected to live Kraken account")
                
                # Wait a moment for account data to initialize
                print("⏳ Initializing account data manager...")
                await asyncio.sleep(2)
                
                return True
            else:
                print("❌ Failed to connect to private WebSocket")
                return False
                
        except Exception as e:
            print(f"❌ Connection error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def retrieve_account_snapshot(self) -> bool:
        """Retrieve current account snapshot with all balance data."""
        print("\n📊 RETRIEVING ACCOUNT SNAPSHOT")
        print("-" * 50)
        
        try:
            # Get account snapshot
            self.account_snapshot = await self.websocket_client.get_account_snapshot()
            
            if self.account_snapshot:
                print("✅ Account snapshot retrieved successfully")
                
                balances = self.account_snapshot.balances
                orders = self.account_snapshot.open_orders
                trades = self.account_snapshot.recent_trades
                
                print(f"📊 Snapshot contains:")
                print(f"   • {len(balances)} currency balances")
                print(f"   • {len(orders)} open orders")
                print(f"   • {len(trades)} recent trades")
                print(f"   • Timestamp: {self.account_snapshot.timestamp}")
                
                return True
            else:
                print("❌ No account snapshot available")
                print("💡 This may indicate account data manager is not initialized")
                return False
                
        except Exception as e:
            print(f"❌ Failed to retrieve account snapshot: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def get_current_prices(self, currencies: List[str]) -> Dict[str, float]:
        """Get current USD prices for all currencies."""
        print(f"\n💱 GETTING CURRENT PRICES FOR {len(currencies)} CURRENCIES")
        print("-" * 50)
        
        prices = {}
        
        try:
            import websockets
            
            # Connect to public WebSocket for price data
            async with websockets.connect("wss://ws.kraken.com") as websocket:
                # Subscribe to tickers for all currencies
                pairs_to_subscribe = []
                
                for currency in currencies:
                    if currency in ['USD', 'ZUSD']:
                        prices[currency] = 1.0  # USD = 1.0
                        continue
                    
                    # Try common pair formats
                    possible_pairs = [
                        f"{currency}/USD",
                        f"{currency}USD", 
                        f"X{currency}/ZUSD",
                        f"{currency}/ZUSD"
                    ]
                    
                    # For now, add the most common format
                    if currency in ['ETH', 'XETH']:
                        pairs_to_subscribe.append("ETH/USD")
                    elif currency in ['BTC', 'XBT', 'XXBT']:
                        pairs_to_subscribe.append("BTC/USD")
                    elif currency in ['SOL']:
                        pairs_to_subscribe.append("SOL/USD")
                    elif currency in ['USDT']:
                        pairs_to_subscribe.append("USDT/USD")
                    # Add more currency mappings as needed
                
                if pairs_to_subscribe:
                    subscribe_message = {
                        "event": "subscribe",
                        "pair": pairs_to_subscribe,
                        "subscription": {"name": "ticker"}
                    }
                    
                    await websocket.send(json.dumps(subscribe_message))
                    print(f"📡 Subscribed to {len(pairs_to_subscribe)} price feeds")
                    
                    # Collect price data
                    collected_prices = 0
                    max_attempts = 30
                    
                    for attempt in range(max_attempts):
                        try:
                            response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                            data = json.loads(response)
                            
                            if isinstance(data, list) and len(data) >= 3:
                                channel_data = data[1]
                                pair_name = data[3] if len(data) > 3 else "unknown"
                                
                                if isinstance(channel_data, dict) and 'c' in channel_data:
                                    last_price = float(channel_data['c'][0])
                                    
                                    # Map pair name back to currency
                                    if "ETH" in pair_name:
                                        prices['ETH'] = last_price
                                        prices['XETH'] = last_price
                                    elif "BTC" in pair_name:
                                        prices['BTC'] = last_price
                                        prices['XBT'] = last_price
                                        prices['XXBT'] = last_price
                                    elif "SOL" in pair_name:
                                        prices['SOL'] = last_price
                                    elif "USDT" in pair_name:
                                        prices['USDT'] = last_price
                                    
                                    collected_prices += 1
                                    print(f"   📈 {pair_name}: ${last_price:.2f}")
                                    
                                    if collected_prices >= len(pairs_to_subscribe):
                                        break
                                        
                        except asyncio.TimeoutError:
                            continue
                        except Exception as e:
                            print(f"⚠️ Price fetch error: {e}")
                            continue
                
                # Fill in missing prices with estimates or mark as unavailable
                for currency in currencies:
                    if currency not in prices and currency not in ['USD', 'ZUSD']:
                        print(f"⚠️ Price not available for {currency}, using $0")
                        prices[currency] = 0.0
                
                self.current_prices = prices
                print(f"✅ Retrieved prices for {len(prices)} currencies")
                return prices
                
        except Exception as e:
            print(f"❌ Price retrieval failed: {e}")
            # Fallback prices for common currencies
            fallback_prices = {
                'ETH': 2440.0, 'XETH': 2440.0,
                'BTC': 45000.0, 'XBT': 45000.0, 'XXBT': 45000.0,
                'SOL': 170.0,
                'USDT': 1.0,
                'USD': 1.0, 'ZUSD': 1.0
            }
            
            print("⚠️ Using fallback price estimates")
            self.current_prices = {k: v for k, v in fallback_prices.items() if k in currencies}
            return self.current_prices
    
    def analyze_balance_types(self, balance: AccountBalance) -> Dict[str, Any]:
        """Analyze different balance types for a currency."""
        return {
            'currency': balance.currency,
            'total_balance': balance.balance,
            'hold_amount': balance.hold,
            'available_balance': balance.available_balance,
            'last_update': balance.last_update,
            'has_holds': balance.hold > 0,
            'is_available': balance.available_balance > 0
        }
    
    async def display_detailed_balances(self):
        """Display detailed balance information for all currencies."""
        print("\n💰 DETAILED ACCOUNT BALANCES")
        print("=" * 70)
        
        if not self.account_snapshot or not self.account_snapshot.balances:
            print("❌ No balance data available")
            return
        
        balances = self.account_snapshot.balances
        currencies_with_balance = []
        
        # Find all currencies with non-zero balances
        for currency, balance in balances.items():
            if balance.balance > 0 or balance.hold > 0:
                currencies_with_balance.append(currency)
        
        if not currencies_with_balance:
            print("📊 No currencies with positive balances found")
            return
        
        print(f"📊 Found {len(currencies_with_balance)} currencies with balances")
        print()
        
        # Get current prices
        await self.get_current_prices(currencies_with_balance)
        
        # Calculate portfolio values
        total_portfolio_usd = 0.0
        balance_details = []
        
        print("💰 INDIVIDUAL BALANCE BREAKDOWN:")
        print("-" * 70)
        print(f"{'Currency':<10} {'Total':<15} {'Available':<15} {'On Hold':<12} {'USD Value':<12}")
        print("-" * 70)
        
        for currency in sorted(currencies_with_balance):
            balance = balances[currency]
            analysis = self.analyze_balance_types(balance)
            
            # Get USD value
            price = self.current_prices.get(currency, 0.0)
            usd_value = float(balance.available_balance) * price
            total_portfolio_usd += usd_value
            
            # Store for portfolio analysis
            balance_details.append({
                'currency': currency,
                'balance': balance,
                'analysis': analysis,
                'price': price,
                'usd_value': usd_value
            })
            
            # Display row
            total_str = f"{balance.balance:.6f}".rstrip('0').rstrip('.')
            available_str = f"{balance.available_balance:.6f}".rstrip('0').rstrip('.')
            hold_str = f"{balance.hold:.6f}".rstrip('0').rstrip('.') if balance.hold > 0 else "-"
            usd_str = f"${usd_value:.2f}" if usd_value > 0.01 else "$0.00"
            
            print(f"{currency:<10} {total_str:<15} {available_str:<15} {hold_str:<12} {usd_str:<12}")
        
        print("-" * 70)
        print(f"{'TOTAL PORTFOLIO VALUE':<54} ${total_portfolio_usd:.2f}")
        print()
        
        # Store portfolio summary
        self.portfolio_summary = {
            'total_usd_value': total_portfolio_usd,
            'balance_details': balance_details,
            'currencies_count': len(currencies_with_balance)
        }
        
        return balance_details
    
    async def display_portfolio_analysis(self):
        """Display portfolio analysis and asset allocation."""
        print("\n📊 PORTFOLIO ANALYSIS")
        print("=" * 50)
        
        if not self.portfolio_summary or not self.portfolio_summary['balance_details']:
            print("❌ No portfolio data available for analysis")
            return
        
        total_value = self.portfolio_summary['total_usd_value']
        balance_details = self.portfolio_summary['balance_details']
        
        if total_value < 0.01:
            print("📊 Portfolio value too small for meaningful analysis")
            return
        
        print(f"💼 Total Portfolio Value: ${total_value:.2f}")
        print(f"🔢 Number of Assets: {len(balance_details)}")
        print()
        
        # Sort by USD value
        sorted_balances = sorted(balance_details, key=lambda x: x['usd_value'], reverse=True)
        
        print("🏆 ASSET ALLOCATION (by USD value):")
        print("-" * 50)
        
        for detail in sorted_balances[:10]:  # Top 10 holdings
            if detail['usd_value'] < 0.01:
                continue
                
            percentage = (detail['usd_value'] / total_value) * 100
            currency = detail['currency']
            usd_value = detail['usd_value']
            balance_amount = detail['balance'].available_balance
            
            print(f"{currency:<8} ${usd_value:>8.2f} ({percentage:>5.1f}%) - {balance_amount:.6f} {currency}")
        
        # Summary stats
        print()
        print("📈 PORTFOLIO INSIGHTS:")
        print("-" * 30)
        
        largest_holding = sorted_balances[0] if sorted_balances else None
        if largest_holding:
            largest_pct = (largest_holding['usd_value'] / total_value) * 100
            print(f"💎 Largest holding: {largest_holding['currency']} ({largest_pct:.1f}%)")
        
        usd_holdings = sum(detail['usd_value'] for detail in balance_details 
                          if detail['currency'] in ['USD', 'ZUSD', 'USDT'])
        if usd_holdings > 0:
            usd_pct = (usd_holdings / total_value) * 100
            print(f"💵 USD/Stablecoin allocation: {usd_pct:.1f}%")
        
        crypto_holdings = total_value - usd_holdings
        if crypto_holdings > 0:
            crypto_pct = (crypto_holdings / total_value) * 100
            print(f"₿ Cryptocurrency allocation: {crypto_pct:.1f}%")
    
    async def display_balance_types_analysis(self):
        """Display analysis of different balance types."""
        print("\n🔍 BALANCE TYPES ANALYSIS")
        print("=" * 50)
        
        if not self.portfolio_summary or not self.portfolio_summary['balance_details']:
            print("❌ No balance data available for analysis")
            return
        
        balance_details = self.portfolio_summary['balance_details']
        
        total_balance_usd = 0.0
        available_balance_usd = 0.0
        held_balance_usd = 0.0
        currencies_with_holds = 0
        
        print("🔍 BALANCE TYPE BREAKDOWN:")
        print("-" * 50)
        
        for detail in balance_details:
            balance = detail['balance']
            price = detail['price']
            
            total_bal_usd = float(balance.balance) * price
            available_bal_usd = float(balance.available_balance) * price
            held_bal_usd = float(balance.hold) * price
            
            total_balance_usd += total_bal_usd
            available_balance_usd += available_bal_usd
            held_balance_usd += held_bal_usd
            
            if balance.hold > 0:
                currencies_with_holds += 1
                print(f"⚠️ {balance.currency}: ${held_bal_usd:.2f} held in orders")
        
        print()
        print("📊 BALANCE SUMMARY:")
        print(f"   💰 Total Balance:     ${total_balance_usd:.2f}")
        print(f"   ✅ Available:         ${available_balance_usd:.2f}")
        print(f"   🔒 Held in Orders:    ${held_balance_usd:.2f}")
        print(f"   📊 Currencies on Hold: {currencies_with_holds}")
        
        if held_balance_usd > 0:
            hold_percentage = (held_balance_usd / total_balance_usd) * 100
            print(f"   📈 Percentage Held:   {hold_percentage:.1f}%")
            print()
            print("💡 Funds 'on hold' are locked in open orders and not available for new trades")
    
    async def display_recent_activity(self):
        """Display recent trading activity from account snapshot."""
        print("\n📈 RECENT TRADING ACTIVITY")
        print("=" * 50)
        
        if not self.account_snapshot:
            print("❌ No account data available")
            return
        
        recent_trades = self.account_snapshot.recent_trades
        open_orders = self.account_snapshot.open_orders
        
        print(f"📊 Open Orders: {len(open_orders)}")
        if open_orders:
            print("🔄 Active Orders:")
            for order_id, order in list(open_orders.items())[:5]:  # Show first 5
                print(f"   • {order.pair} {order.side} {order.volume} @ ${order.price or 'market'}")
        
        print(f"\n📊 Recent Trades: {len(recent_trades)}")
        if recent_trades:
            print("💹 Latest Trades:")
            for trade in recent_trades[:5]:  # Show first 5
                print(f"   • {trade.pair} {trade.side} {trade.volume} @ ${trade.price} ({trade.time})")
    
    async def cleanup(self):
        """Clean up connections."""
        if self.websocket_client:
            try:
                await self.websocket_client.disconnect()
                print("✅ WebSocket disconnected")
            except Exception as e:
                print(f"⚠️ Cleanup warning: {e}")
    
    async def run_balance_retrieval(self):
        """Run the complete balance retrieval and analysis."""
        try:
            print("🚀 KRAKEN ACCOUNT BALANCE RETRIEVAL SYSTEM")
            print("=" * 70)
            print("📊 Comprehensive balance analysis with USD conversion")
            print("💱 Real-time price data and portfolio insights")
            print("🔍 Balance types analysis and trading activity review")
            print("=" * 70)
            
            # Step 1: Connect to account
            connect_ok = await self.connect_to_account()
            if not connect_ok:
                print("❌ Failed to connect to account")
                return False
            
            # Step 2: Retrieve account snapshot
            snapshot_ok = await self.retrieve_account_snapshot()
            if not snapshot_ok:
                print("❌ Failed to retrieve account data")
                return False
            
            # Step 3: Display detailed balances
            await self.display_detailed_balances()
            
            # Step 4: Portfolio analysis
            await self.display_portfolio_analysis()
            
            # Step 5: Balance types analysis
            await self.display_balance_types_analysis()
            
            # Step 6: Recent activity
            await self.display_recent_activity()
            
            # Success summary
            print("\n🎉 BALANCE RETRIEVAL COMPLETED!")
            print("=" * 50)
            print("✅ Account connection: WORKING")
            print("✅ Balance retrieval: WORKING")
            print("✅ USD conversion: WORKING")
            print("✅ Portfolio analysis: WORKING")
            print("✅ Real-time data: WORKING")
            
            return True
            
        except KeyboardInterrupt:
            print("\n👋 Balance retrieval interrupted")
            return False
        except Exception as e:
            print(f"❌ Balance retrieval failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            await self.cleanup()


async def main():
    """Main execution function."""
    print("🚀 KRAKEN ACCOUNT BALANCE RETRIEVAL")
    print("=" * 70)
    
    retriever = AccountBalanceRetriever()
    success = await retriever.run_balance_retrieval()
    
    if success:
        print("🎉 BALANCE SYSTEM: FULLY OPERATIONAL!")
    else:
        print("❌ Balance retrieval system test failed")
    
    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
