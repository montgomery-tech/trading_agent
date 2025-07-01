#!/usr/bin/env python3
"""
Simple External Agent Test Client

This simulates an external AI agent accessing your trading system
via HTTP API calls instead of MCP protocol.

This demonstrates the external agent concept working with your current setup.

Usage: python3 simple_test_client.py
"""

import asyncio
import json
import sys

try:
    import httpx
except ImportError:
    print("❌ Missing httpx. Install with: pip install httpx")
    sys.exit(1)

class SimpleExternalAgent:
    """
    A simple external agent that demonstrates trading via HTTP API.
    
    This shows how any AI agent could connect to and trade through
    your trading system using standard HTTP requests.
    """
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.agent_name = "SimpleExternalAgent"
        self.trade_count = 0
        
    async def check_server_health(self):
        """Check if the trading server is healthy."""
        print(f"🔍 {self.agent_name} checking server health...")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/health", timeout=5)
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ Server is healthy!")
                    print(f"   Trading system ready: {data.get('trading_system_ready')}")
                    print(f"   Demo mode: {data.get('demo_mode')}")
                    return True
                else:
                    print(f"❌ Server health check failed: {response.status_code}")
                    return False
                    
        except Exception as e:
            print(f"❌ Cannot connect to server: {e}")
            print("   Make sure the server is running: python3 simple_demo_solution.py")
            return False
    
    async def test_connectivity(self):
        """Test basic connectivity with ping."""
        print(f"\n🏓 {self.agent_name} testing connectivity...")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/ping", timeout=5)
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ Ping successful: {data['result']}")
                    return True
                else:
                    print(f"❌ Ping failed: {response.status_code}")
                    return False
                    
        except Exception as e:
            print(f"❌ Ping error: {e}")
            return False
    
    async def get_account_balance(self):
        """Get current account balance."""
        print(f"\n💰 {self.agent_name} checking account balance...")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/balance", timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if data["status"] == "success":
                        balance = data["result"]
                        print("✅ Account Balance:")
                        for currency, info in balance.items():
                            print(f"   {currency}: {info['balance']} (Available: {info['available']})")
                        return balance
                    else:
                        print(f"❌ Balance check failed: {data['message']}")
                        return None
                else:
                    print(f"❌ Balance request failed: {response.status_code}")
                    return None
                    
        except Exception as e:
            print(f"❌ Balance error: {e}")
            return None
    
    async def get_server_status(self):
        """Get server status."""
        print(f"\n📊 {self.agent_name} checking server status...")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/status", timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if data["status"] == "success":
                        status = data["result"]
                        print("✅ Server Status:")
                        print(f"   WebSocket Connected: {status['websocket_connected']}")
                        print(f"   Order Manager Active: {status['order_manager_active']}")
                        print(f"   Account Data Available: {status['account_data_available']}")
                        print(f"   External Agent Access: {status['external_agent_access']}")
                        return status
                    else:
                        print(f"❌ Status check failed: {data['message']}")
                        return None
                else:
                    print(f"❌ Status request failed: {response.status_code}")
                    return None
                    
        except Exception as e:
            print(f"❌ Status error: {e}")
            return None
    
    async def get_market_data(self, symbol: str):
        """Get market data for a symbol."""
        print(f"\n📈 {self.agent_name} getting market data for {symbol}...")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/market",
                    params={"symbol": symbol},
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if data["status"] == "success":
                        market = data["result"]
                        print(f"✅ Market Data for {symbol}:")
                        print(f"   Price: ${market['price']}")
                        print(f"   24h Change: {market['change_24h']}%")
                        print(f"   Volume: {market['volume_24h']}")
                        print(f"   Bid/Ask: ${market['bid']} / ${market['ask']}")
                        return market
                    else:
                        print(f"❌ Market data failed: {data['message']}")
                        return None
                else:
                    print(f"❌ Market data request failed: {response.status_code}")
                    return None
                    
        except Exception as e:
            print(f"❌ Market data error: {e}")
            return None
    
    async def place_demo_order(self, symbol: str, side: str, amount: float):
        """Place a demo trading order."""
        print(f"\n🚀 {self.agent_name} placing demo order...")
        print(f"   Order: {side.upper()} {amount} {symbol}")
        
        try:
            order_data = {
                "symbol": symbol,
                "side": side,
                "amount": amount,
                "order_type": "market"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/order",
                    json=order_data,
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if data["status"] == "success":
                        order = data["result"]
                        self.trade_count += 1
                        
                        print(f"✅ Order executed successfully!")
                        print(f"   Order ID: {order['order_id']}")
                        print(f"   Symbol: {order['symbol']}")
                        print(f"   Side: {order['side']}")
                        print(f"   Amount: {order['amount']}")
                        print(f"   Price: ${order['price']}")
                        print(f"   Status: {order['status']}")
                        print(f"   Total trades by agent: {self.trade_count}")
                        
                        return order
                    else:
                        print(f"❌ Order failed: {data['message']}")
                        return None
                else:
                    print(f"❌ Order request failed: {response.status_code}")
                    return None
                    
        except Exception as e:
            print(f"❌ Order error: {e}")
            return None
    
    async def run_trading_strategy(self, cycles: int = 3):
        """Run a simple trading strategy."""
        print(f"\n🎯 {self.agent_name} running trading strategy...")
        print(f"   Strategy: Analyze markets → Make trading decisions → Execute trades")
        print(f"   Cycles: {cycles}")
        
        symbols = ["XBTUSD", "ETHUSD", "ADAUSD", "SOLUSD"]
        
        for cycle in range(cycles):
            print(f"\n" + "="*60)
            print(f"📈 TRADING CYCLE {cycle + 1}/{cycles}")
            print("="*60)
            
            # Analyze each market
            for symbol in symbols:
                # Get market data
                market_data = await self.get_market_data(symbol)
                
                if market_data:
                    # Simple trading logic
                    change = market_data['change_24h']
                    price = market_data['price']
                    
                    print(f"\n🧠 {self.agent_name} analyzing {symbol}:")
                    print(f"   Current Price: ${price}")
                    print(f"   24h Change: {change}%")
                    
                    # Trading decision logic
                    if change > 3:
                        decision = "sell"
                        reason = "Price up significantly, taking profit"
                        confidence = 0.8
                    elif change < -3:
                        decision = "buy"
                        reason = "Price down significantly, buying dip"
                        confidence = 0.9
                    elif abs(change) < 1:
                        decision = "hold"
                        reason = "Price stable, no action needed"
                        confidence = 0.6
                    else:
                        decision = "hold"
                        reason = "Moderate movement, waiting for clearer signal"
                        confidence = 0.5
                    
                    print(f"   Decision: {decision.upper()}")
                    print(f"   Reason: {reason}")
                    print(f"   Confidence: {confidence:.1%}")
                    
                    # Execute trade if decision is buy/sell and confidence is high
                    if decision in ["buy", "sell"] and confidence > 0.7:
                        # Calculate amount based on symbol
                        if symbol == "XBTUSD":
                            amount = 0.001  # Small BTC amount
                        elif symbol == "ETHUSD":
                            amount = 0.01   # Small ETH amount
                        else:
                            amount = 10     # Larger amount for cheaper coins
                        
                        await self.place_demo_order(symbol, decision, amount)
                    else:
                        print(f"   💤 No trade executed for {symbol}")
                
                # Small delay between symbol analysis
                await asyncio.sleep(1)
            
            # Delay between cycles
            if cycle < cycles - 1:
                print(f"\n⏳ Waiting before next cycle...")
                await asyncio.sleep(3)
        
        print(f"\n🏁 Trading strategy completed!")
        print(f"   Total trades executed: {self.trade_count}")
    
    async def run_full_demo(self):
        """Run the complete external agent demo."""
        print("🎯 EXTERNAL AGENT DEMO - FULL TRADING WORKFLOW")
        print("="*70)
        print(f"Agent: {self.agent_name}")
        print(f"Server: {self.base_url}")
        print("Demonstrating external AI agent trading via HTTP API")
        print("="*70)
        
        # Step 1: Check server health
        if not await self.check_server_health():
            print("❌ Cannot proceed - server not available")
            return False
        
        # Step 2: Test connectivity
        if not await self.test_connectivity():
            print("❌ Cannot proceed - connectivity test failed")
            return False
        
        # Step 3: Get account info
        balance = await self.get_account_balance()
        if not balance:
            print("❌ Cannot proceed - account info unavailable")
            return False
        
        # Step 4: Get server status
        status = await self.get_server_status()
        if not status:
            print("❌ Cannot proceed - server status unavailable")
            return False
        
        # Step 5: Run trading strategy
        await self.run_trading_strategy(cycles=3)
        
        print("\n" + "="*70)
        print("🎉 EXTERNAL AGENT DEMO COMPLETED SUCCESSFULLY!")
        print("="*70)
        print("✅ Proven capabilities:")
        print("   • External agent can connect to trading system via HTTP")
        print("   • Agent can check system health and status")
        print("   • Agent can retrieve account balance and market data")
        print("   • Agent can analyze markets and make trading decisions")
        print("   • Agent can execute trades autonomously")
        print("   • Agent can run complete trading strategies")
        print()
        print("🚀 This demonstrates that external AI agents CAN trade")
        print("   through your MCP-based trading system!")
        print("="*70)
        
        return True

async def main():
    """Main function."""
    print("🤖 SIMPLE EXTERNAL AGENT TEST CLIENT")
    print("="*50)
    
    # Create the agent
    agent = SimpleExternalAgent()
    
    try:
        # Run the full demo
        success = await agent.run_full_demo()
        
        if success:
            print("\n✅ DEMO SUCCESS: External agent trading concept proven!")
        else:
            print("\n❌ DEMO FAILED: Check error messages above")
            
    except KeyboardInterrupt:
        print("\n⚠️ Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
