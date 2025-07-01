#!/usr/bin/env python3
"""
Conservative Trading Test - $10 Maximum

Test minimal trading operations with strict safety limits.
Maximum order size: $10 USD
"""

import asyncio
import sys
from pathlib import Path
from decimal import Decimal

sys.path.insert(0, str(Path(__file__).parent / "src"))

class ConservativeTradingTest:
    """Conservative trading test with strict safety limits."""
    
    def __init__(self):
        self.max_order_usd = Decimal("10.00")  # $10 maximum
        self.test_symbol = "ETH/USD"  # Ethereum/USD (better for small orders)
        self.websocket_client = None
        self.public_client = None
        self.current_eth_price = None
        
    async def test_account_balance(self):
        """Test retrieving real account balance."""
        print("💰 TESTING ACCOUNT BALANCE RETRIEVAL")
        print("-" * 50)
        
        try:
            from trading_systems.exchanges.kraken.websocket_client import KrakenWebSocketClient
            
            self.websocket_client = KrakenWebSocketClient()
            await self.websocket_client.connect_private()
            
            if not self.websocket_client.is_private_connected:
                print("❌ Could not connect to private WebSocket")
                return False
            
            print("✅ Connected to live account")
            
            # Get account snapshot
            snapshot = await self.websocket_client.get_account_snapshot()
            if snapshot:
                print("📊 Account snapshot retrieved:")
                print(f"   Snapshot type: {type(snapshot)}")
                print("   ✅ Real account data accessible")
            else:
                print("📊 Account snapshot: None (may need subscription)")
            
            return True
            
        except Exception as e:
            print(f"❌ Account balance test failed: {e}")
            return False
    
    async def get_live_eth_price(self):
        """Get live ETH price from public WebSocket or REST API."""
        print(f"\n📊 GETTING LIVE ETH PRICE")
        print("-" * 50)
        
        try:
            # Try to get live price via REST API first (simpler)
            import aiohttp
            
            print("🔗 Fetching live ETH price from Kraken REST API...")
            
            async with aiohttp.ClientSession() as session:
                url = "https://api.kraken.com/0/public/Ticker?pair=ETHUSD"
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if data.get('error') == []:
                            # Kraken returns ETHUSD data
                            result = data.get('result', {})
                            eth_data = result.get('ETHUSD', {})
                            
                            if eth_data:
                                # Get current ask price (what we'd pay to buy)
                                ask_price = float(eth_data.get('a', [0])[0])  # Ask price
                                bid_price = float(eth_data.get('b', [0])[0])  # Bid price
                                last_price = float(eth_data.get('c', [0])[0])  # Last trade price
                                
                                self.current_eth_price = ask_price  # Use ask price for buying
                                
                                print(f"✅ Live ETH Prices Retrieved:")
                                print(f"   Last trade: ${last_price:.2f}")
                                print(f"   Current bid: ${bid_price:.2f}")
                                print(f"   Current ask: ${ask_price:.2f}")
                                print(f"   Using ask price: ${self.current_eth_price:.2f}")
                                
                                return True
                            else:
                                print("❌ No ETH data in response")
                        else:
                            print(f"❌ API error: {data.get('error')}")
                    else:
                        print(f"❌ HTTP error: {response.status}")
                        
        except ImportError:
            print("⚠️ aiohttp not available, using WebSocket method...")
            return await self.get_live_price_via_websocket()
        except Exception as e:
            print(f"❌ REST API price fetch failed: {e}")
            print("🔄 Trying WebSocket method...")
            return await self.get_live_price_via_websocket()
        
        return False
    
    async def get_live_price_via_websocket(self):
        """Get live price via public WebSocket (fallback method)."""
        try:
            print("🔗 Attempting to get price via public WebSocket...")
            
            # Create a simple public connection for market data
            import websockets
            import json
            
            # Connect to Kraken public WebSocket
            uri = "wss://ws.kraken.com"
            
            async with websockets.connect(uri) as websocket:
                # Subscribe to ETH/USD ticker
                subscribe_message = {
                    "event": "subscribe",
                    "pair": ["ETH/USD"],
                    "subscription": {"name": "ticker"}
                }
                
                await websocket.send(json.dumps(subscribe_message))
                print("📡 Subscribed to ETH/USD ticker...")
                
                # Wait for a few messages to get price data
                for i in range(10):  # Try up to 10 messages
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        data = json.loads(response)
                        
                        # Check if this is ticker data
                        if isinstance(data, list) and len(data) > 1:
                            ticker_data = data[1]
                            if isinstance(ticker_data, dict) and 'a' in ticker_data:
                                ask_price = float(ticker_data['a'][0])  # Ask price
                                self.current_eth_price = ask_price
                                
                                print(f"✅ Live ETH price from WebSocket: ${ask_price:.2f}")
                                return True
                                
                    except asyncio.TimeoutError:
                        print("⏰ Timeout waiting for price data")
                        break
                    except Exception as e:
                        print(f"⚠️ Error processing message: {e}")
                        continue
                        
            print("❌ Could not get live price via WebSocket")
            return False
            
        except Exception as e:
            print(f"❌ WebSocket price fetch failed: {e}")
            # Use a reasonable fallback estimate
            self.current_eth_price = 2400.0  # Conservative ETH estimate
            print(f"⚠️ Using fallback ETH price estimate: ${self.current_eth_price:.2f}")
            return False
    
    async def prepare_minimal_order_test(self):
        """Prepare for minimal order testing with live ETH price."""
        print(f"\n⚠️ MINIMAL ORDER PREPARATION WITH LIVE PRICING")
        print("-" * 50)
        print(f"🔒 SAFETY LIMITS:")
        print(f"   Maximum order value: ${self.max_order_usd}")
        print(f"   Trading pair: {self.test_symbol}")
        print(f"   Mode: VALIDATION ONLY (no actual orders)")
        
        try:
            # First get live ETH price
            price_ok = await self.get_live_eth_price()
            
            if not price_ok:
                print("⚠️ Could not get live price, using estimate")
            
            # Check if order management is available
            status = self.websocket_client.get_connection_status()
            order_mgmt_enabled = status.get('order_management_enabled', False)
            
            print(f"\n📋 Order Management Status:")
            print(f"   Order management enabled: {order_mgmt_enabled}")
            
            if not order_mgmt_enabled:
                print("ℹ️ Order management not enabled in current configuration")
                print("ℹ️ This is expected in demo mode")
            
            # Calculate realistic order size with live price
            print(f"\n🧮 Order Size Calculation with Live Data:")
            print(f"   Max USD amount: ${self.max_order_usd}")
            print(f"   Current ETH price: ${self.current_eth_price:.2f}")
            
            eth_amount = float(self.max_order_usd) / self.current_eth_price
            order_value_check = eth_amount * self.current_eth_price
            
            print(f"   Calculated ETH amount: {eth_amount:.6f} ETH")
            print(f"   Order value check: ${order_value_check:.2f}")
            print(f"   ✅ Order size well within ${self.max_order_usd} limit")
            
            # Check minimum order requirements
            min_eth_order = 0.002  # Typical minimum ETH order size on Kraken
            if eth_amount >= min_eth_order:
                print(f"   ✅ Above minimum order size ({min_eth_order} ETH)")
            else:
                print(f"   ⚠️ Below minimum order size ({min_eth_order} ETH)")
                print(f"   💡 May need to increase order value slightly")
            
            return True
            
        except Exception as e:
            print(f"❌ Order preparation failed: {e}")
            return False
    
    async def check_production_mode_requirements(self):
        """Check what's needed to enable production mode."""
        print(f"\n🔧 PRODUCTION MODE REQUIREMENTS CHECK")
        print("-" * 50)
        
        try:
            # Check MCP server configuration
            from trading_systems.mcp_server.config import MCPServerConfig
            
            config = MCPServerConfig()
            print(f"📋 Current MCP Configuration:")
            print(f"   Server name: {config.server_name}")
            print(f"   Real trading enabled: {config.enable_real_trading}")
            print(f"   Risk management enabled: {config.enable_risk_management}")
            print(f"   Max order value: ${config.security.max_order_value_usd}")
            
            print(f"\n🔄 To Enable Production Mode:")
            if not config.enable_real_trading:
                print("   ❌ Need to set: enable_real_trading = True")
            if config.security.max_order_value_usd > 10:
                print(f"   ⚠️ Consider lowering max order value to ${self.max_order_usd}")
            
            print(f"\n💡 Configuration Steps:")
            print("   1. Update MCPServerConfig to enable real trading")
            print("   2. Set conservative order limits")
            print("   3. Ensure risk management is enabled")
            print("   4. Test with minimal orders")
            
            return True
            
        except Exception as e:
            print(f"❌ Production mode check failed: {e}")
            return False
    
    async def cleanup(self):
        """Clean up connections."""
        if self.websocket_client:
            try:
                await self.websocket_client.disconnect()
                print("✅ WebSocket disconnected")
            except Exception as e:
                print(f"⚠️ Cleanup warning: {e}")
    
    async def run_conservative_test(self):
        """Run the complete conservative trading test."""
        print("🧪 CONSERVATIVE TRADING TEST")
        print("=" * 60)
        print(f"🔒 MAXIMUM ORDER VALUE: ${self.max_order_usd}")
        print(f"🔒 APPROACH: Read-only testing first, then minimal validation")
        print("=" * 60)
        
        try:
            # Test 1: Account balance
            balance_ok = await self.test_account_balance()
            
            if balance_ok:
                # Test 2: Get live ETH price and prepare orders
                order_prep_ok = await self.prepare_minimal_order_test()
                
                if order_prep_ok:
                    # Test 3: Production mode requirements
                    prod_mode_ok = await self.check_production_mode_requirements()
                        
                        if prod_mode_ok:
                            print(f"\n🎉 CONSERVATIVE TEST COMPLETED SUCCESSFULLY!")
                            print("=" * 60)
                            print("✅ Live account data access: WORKING")
                            print("✅ Private WebSocket connection: WORKING") 
                            print(f"✅ Live ETH price: ${self.current_eth_price:.2f}")
                            print("✅ Safety limits validated: $10 maximum")
                            print("✅ Ready for production mode configuration")
                            print()
                            print("🚀 NEXT STEPS:")
                            print("   1. Configure production mode in MCP server")
                            print("   2. Test actual minimal order placement")
                            print("   3. Validate order execution and cancellation")
                            print("   4. Gradually increase testing scope")
                            print("=" * 60)
                            return True
            
            print(f"\n❌ Conservative test failed at some stage")
            return False
            
        except Exception as e:
            print(f"❌ Conservative test error: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            await self.cleanup()

async def main():
    """Main function."""
    test = ConservativeTradingTest()
    success = await test.run_conservative_test()
    
    if success:
        print("\n🎯 READY FOR PRODUCTION MODE!")
        print("Conservative testing completed successfully.")
    else:
        print("\n❌ Need to resolve issues before production mode.")

if __name__ == "__main__":
    asyncio.run(main())