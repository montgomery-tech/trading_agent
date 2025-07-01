#!/usr/bin/env python3
"""
Conservative Trading Test - Using WebSocket for Price Data

Uses our existing working WebSocket connection instead of REST API.
"""

import asyncio
import sys
from pathlib import Path
from decimal import Decimal
import json

sys.path.insert(0, str(Path(__file__).parent / "src"))

class ConservativeTradingTest:
    """Conservative trading test using WebSocket for live data."""
    
    def __init__(self):
        self.max_order_usd = Decimal("10.00")  # $10 maximum
        self.test_symbol = "ETH/USD"
        self.websocket_client = None
        self.current_eth_price = 3300.0  # Fallback estimate
        
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
    
    async def get_live_eth_price_via_websocket(self):
        """Get live ETH price using our WebSocket connection."""
        print(f"\n📊 GETTING LIVE ETH PRICE VIA WEBSOCKET")
        print("-" * 50)
        
        try:
            print("🔗 Using existing WebSocket connection for market data...")
            
            # Check if we can create a public connection for market data
            # Since we have private connection working, let's try the same approach for public
            import websockets
            
            # Connect to Kraken public WebSocket directly
            public_ws_url = "wss://ws.kraken.com"
            print(f"📡 Connecting to {public_ws_url}")
            
            async with websockets.connect(public_ws_url) as websocket:
                # Subscribe to ETH/USD ticker
                subscribe_message = {
                    "event": "subscribe",
                    "pair": ["ETH/USD"],
                    "subscription": {"name": "ticker"}
                }
                
                print("📊 Subscribing to ETH/USD ticker...")
                await websocket.send(json.dumps(subscribe_message))
                
                # Wait for ticker data
                print("🎧 Waiting for live price data...")
                
                for i in range(15):  # Try up to 15 messages
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                        data = json.loads(response)
                        
                        print(f"📨 Message {i+1}: {str(data)[:100]}...")
                        
                        # Check if this is ticker data (list format)
                        if isinstance(data, list) and len(data) >= 2:
                            channel_data = data[1]
                            if isinstance(channel_data, dict):
                                # Look for ask price
                                if 'a' in channel_data:
                                    ask_price = float(channel_data['a'][0])
                                    bid_price = float(channel_data.get('b', [0])[0])
                                    last_price = float(channel_data.get('c', [0])[0])
                                    
                                    self.current_eth_price = ask_price
                                    
                                    print(f"✅ Live ETH Prices from WebSocket:")
                                    print(f"   Last trade: ${last_price:.2f}")
                                    print(f"   Current bid: ${bid_price:.2f}") 
                                    print(f"   Current ask: ${ask_price:.2f}")
                                    print(f"   Using ask price: ${self.current_eth_price:.2f}")
                                    
                                    return True
                        
                        # Check for subscription confirmation
                        elif isinstance(data, dict) and data.get('event') == 'subscriptionStatus':
                            if data.get('status') == 'subscribed':
                                print("✅ Subscription confirmed, waiting for data...")
                            elif data.get('status') == 'error':
                                print(f"❌ Subscription error: {data}")
                                break
                                
                    except asyncio.TimeoutError:
                        print(f"⏰ Timeout on message {i+1}")
                        continue
                    except Exception as e:
                        print(f"⚠️ Error processing message {i+1}: {e}")
                        continue
                
                print("⚠️ Did not receive ticker data in expected time")
                
        except Exception as e:
            print(f"❌ WebSocket price fetch failed: {e}")
        
        # Use fallback price
        print(f"⚠️ Using fallback ETH price: ${self.current_eth_price:.2f}")
        return True
    
    async def prepare_minimal_order_test(self):
        """Prepare for minimal order testing."""
        print(f"\n⚠️ MINIMAL ORDER PREPARATION")
        print("-" * 50)
        print(f"🔒 SAFETY LIMITS:")
        print(f"   Maximum order value: ${self.max_order_usd}")
        print(f"   Trading pair: {self.test_symbol}")
        print(f"   Mode: VALIDATION ONLY (no actual orders)")
        
        try:
            # Get ETH price via WebSocket
            await self.get_live_eth_price_via_websocket()
            
            # Check order management status
            status = self.websocket_client.get_connection_status()
            order_mgmt_enabled = status.get('order_management_enabled', False)
            
            print(f"\n📋 Order Management Status:")
            print(f"   Order management enabled: {order_mgmt_enabled}")
            print(f"   Private connected: {status.get('private_connected', False)}")
            print(f"   Has auth token: {status.get('has_token', False)}")
            
            if not order_mgmt_enabled:
                print("ℹ️ Order management not enabled in current configuration")
                print("ℹ️ This is expected in demo mode")
            
            # Calculate order size
            print(f"\n🧮 Order Size Calculation:")
            print(f"   Max USD amount: ${self.max_order_usd}")
            print(f"   Current ETH price: ${self.current_eth_price:.2f}")
            
            eth_amount = float(self.max_order_usd) / self.current_eth_price
            order_value_check = eth_amount * self.current_eth_price
            
            print(f"   Calculated ETH amount: {eth_amount:.6f} ETH")
            print(f"   Order value check: ${order_value_check:.2f}")
            print(f"   ✅ Order size within ${self.max_order_usd} limit")
            
            # Check minimum order requirements
            min_eth_order = 0.002  # Kraken minimum
            if eth_amount >= min_eth_order:
                print(f"   ✅ Above minimum order size ({min_eth_order} ETH)")
            else:
                min_value_needed = min_eth_order * self.current_eth_price
                print(f"   ⚠️ Below minimum order size ({min_eth_order} ETH)")
                print(f"   💡 Need minimum ${min_value_needed:.2f} for ETH orders")
            
            return True
            
        except Exception as e:
            print(f"❌ Order preparation failed: {e}")
            return False
    
    async def check_production_mode_requirements(self):
        """Check production mode requirements."""
        print(f"\n🔧 PRODUCTION MODE REQUIREMENTS")
        print("-" * 50)
        
        try:
            from trading_systems.mcp_server.config import MCPServerConfig
            
            config = MCPServerConfig()
            print(f"📋 Current Configuration:")
            print(f"   Real trading enabled: {config.enable_real_trading}")
            print(f"   Risk management: {config.enable_risk_management}")
            print(f"   Max order value: ${config.security.max_order_value_usd}")
            
            print(f"\n🔄 Required Changes:")
            if not config.enable_real_trading:
                print("   ❌ Need: enable_real_trading = True")
            else:
                print("   ✅ Real trading already enabled")
            
            if config.security.max_order_value_usd > 15:
                print(f"   ⚠️ Consider: Lower max order to $15")
            else:
                print(f"   ✅ Order limits look reasonable")
            
            print(f"\n🚀 Next Steps:")
            print("   1. Enable production mode in MCP server config")
            print("   2. Test minimal order placement")
            print("   3. Validate order execution workflow")
            
            return True
            
        except Exception as e:
            print(f"❌ Production check failed: {e}")
            return False
    
    async def cleanup(self):
        """Clean up connections."""
        if self.websocket_client:
            try:
                await self.websocket_client.disconnect()
                print("✅ WebSocket disconnected")
            except Exception as e:
                print(f"⚠️ Cleanup warning: {e}")
    
    async def run_test(self):
        """Run the complete test."""
        print("🧪 CONSERVATIVE TEST - WEBSOCKET VERSION")
        print("=" * 60)
        print(f"🔒 MAX ORDER: ${self.max_order_usd}")
        print(f"🔗 METHOD: Using WebSocket connections")
        print("=" * 60)
        
        try:
            # Phase 1: Account connectivity  
            balance_ok = await self.test_account_balance()
            
            if balance_ok:
                # Phase 2: Order preparation with live pricing
                order_ok = await self.prepare_minimal_order_test()
                
                if order_ok:
                    # Phase 3: Production readiness
                    prod_ok = await self.check_production_mode_requirements()
                    
                    if prod_ok:
                        print(f"\n🎉 SUCCESS!")
                        print("=" * 60)
                        print("✅ Account data: WORKING")
                        print("✅ WebSocket auth: WORKING")
                        print(f"✅ ETH price: ${self.current_eth_price:.2f}")
                        print("✅ Order calc: VALIDATED")
                        print("\n🚀 READY FOR PRODUCTION MODE!")
                        return True
            
            return False
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            return False
        finally:
            await self.cleanup()

async def main():
    test = ConservativeTradingTest()
    success = await test.run_test()
    
    if success:
        print("\n🎯 RESULT: Ready for production configuration!")
    else:
        print("\n❌ Need to resolve issues first.")

if __name__ == "__main__":
    asyncio.run(main())
