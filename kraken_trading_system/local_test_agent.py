#!/usr/bin/env python3
"""
Local Test Agent for MCP Trading Server

This agent demonstrates how an external AI agent would connect to and
trade through your MCP server.

Usage: python3 local_test_agent.py

Make sure the HTTP MCP server is running first!
"""

import asyncio
import sys
import json
import random
from pathlib import Path
from typing import Dict, Any

# You'll need to install these for HTTP MCP client
try:
    import httpx
    from mcp.client import ClientSession
    from mcp.client.sse import SseClientTransport
except ImportError as e:
    print("❌ Missing required packages for MCP client:")
    print("   pip install httpx mcp")
    sys.exit(1)


class LocalTradingAgent:
    """
    A simple AI trading agent that connects to your MCP server.
    
    This demonstrates the full external agent workflow:
    1. Connect to HTTP MCP server
    2. Initialize MCP session
    3. Use trading tools
    4. Make trading decisions
    5. Execute trades
    """
    
    def __init__(self, server_url: str = "http://localhost:8000/sse"):
        self.server_url = server_url
        self.session = None
        self.agent_name = "LocalTestAgent"
        self.portfolio = {}
        self.trade_count = 0
        
    async def connect(self):
        """Connect to the MCP trading server."""
        print(f"🔗 {self.agent_name} connecting to MCP server...")
        print(f"   Server URL: {self.server_url}")
        
        try:
            # Create SSE transport for MCP
            transport = SseClientTransport(self.server_url)
            
            # Create MCP session
            self.session = ClientSession(transport)
            
            # Initialize the session
            init_result = await self.session.initialize()
            
            print(f"✅ Connected successfully!")
            print(f"   Server: {init_result.server_info.name}")
            print(f"   Version: {init_result.server_info.version}")
            print(f"   Available tools: {len(init_result.capabilities.tools or [])}")
            
            return True
            
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False
    
    async def test_basic_connectivity(self):
        """Test basic MCP tools to verify connection."""
        print("\n🧪 Testing basic connectivity...")
        
        try:
            # Test ping
            ping_result = await self.session.call_tool("ping")
            print(f"   Ping: {ping_result.content[0].text}")
            
            # Test server status
            status_result = await self.session.call_tool("get_server_status")
            status_data = json.loads(status_result.content[0].text)
            print(f"   Server Status: {status_data['status']}")
            print(f"   Mode: {status_data['data']['connection_details']['mode']}")
            
            return True
            
        except Exception as e:
            print(f"❌ Basic connectivity test failed: {e}")
            return False
    
    async def get_account_info(self):
        """Get current account balance."""
        print("\n💰 Checking account balance...")
        
        try:
            balance_result = await self.session.call_tool("get_account_balance")
            balance_data = json.loads(balance_result.content[0].text)
            
            if balance_data["status"] == "success":
                self.portfolio = balance_data["data"]
                print("   Current Portfolio:")
                for currency, info in self.portfolio.items():
                    print(f"     {currency}: {info['balance']} (Available: {info['available']})")
                return True
            else:
                print(f"❌ Failed to get balance: {balance_data['message']}")
                return False
                
        except Exception as e:
            print(f"❌ Account info failed: {e}")
            return False
    
    async def analyze_market(self, symbol: str) -> Dict[str, Any]:
        """Analyze market conditions for a symbol."""
        print(f"\n📊 Analyzing market for {symbol}...")
        
        try:
            market_result = await self.session.call_tool("get_market_data", {"symbol": symbol})
            market_data = json.loads(market_result.content[0].text)
            
            if market_data["status"] == "success":
                data = market_data["data"]
                print(f"   {symbol} Price: ${data['price']}")
                print(f"   24h Change: {data['change_24h']}%")
                print(f"   Spread: ${data['ask'] - data['bid']:.2f}")
                
                # Simple trading decision logic
                change = data['change_24h']
                
                if change > 2:
                    decision = {"action": "sell", "reason": "Price up significantly", "confidence": 0.7}
                elif change < -2:
                    decision = {"action": "buy", "reason": "Price down significantly", "confidence": 0.8}
                else:
                    decision = {"action": "hold", "reason": "Price stable", "confidence": 0.5}
                
                decision["market_data"] = data
                return decision
            else:
                print(f"❌ Market analysis failed: {market_data['message']}")
                return {"action": "hold", "reason": "Market data unavailable"}
                
        except Exception as e:
            print(f"❌ Market analysis failed: {e}")
            return {"action": "hold", "reason": "Analysis error"}
    
    async def execute_trade(self, symbol: str, side: str, amount: float, reason: str):
        """Execute a trade based on analysis."""
        print(f"\n🚀 Executing trade: {side.upper()} {amount} {symbol}")
        print(f"   Reason: {reason}")
        
        try:
            trade_result = await self.session.call_tool("place_demo_order", {
                "symbol": symbol,
                "side": side,
                "amount": amount,
                "order_type": "market"
            })
            
            trade_data = json.loads(trade_result.content[0].text)
            
            if trade_data["status"] == "success":
                order = trade_data["data"]
                self.trade_count += 1
                
                print(f"✅ Trade executed successfully!")
                print(f"   Order ID: {order['order_id']}")
                print(f"   Price: ${order['price']}")
                print(f"   Status: {order['status']}")
                print(f"   Total trades by agent: {self.trade_count}")
                
                return order
            else:
                print(f"❌ Trade failed: {trade_data['message']}")
                return None
                
        except Exception as e:
            print(f"❌ Trade execution failed: {e}")
            return None
    
    async def run_trading_strategy(self, cycles: int = 5):
        """Run a simple trading strategy for testing."""
        print(f"\n🎯 {self.agent_name} starting trading strategy...")
        print(f"   Running {cycles} analysis cycles")
        print(f"   Will analyze multiple markets and make trading decisions")
        
        symbols = ["XBTUSD", "ETHUSD", "ADAUSD", "SOLUSD"]
        
        for cycle in range(cycles):
            print(f"\n" + "="*60)
            print(f"📈 TRADING CYCLE {cycle + 1}/{cycles}")
            print("="*60)
            
            # Analyze each market
            for symbol in symbols:
                decision = await self.analyze_market(symbol)
                
                if decision["action"] in ["buy", "sell"] and decision["confidence"] > 0.6:
                    # Calculate trade amount based on symbol
                    if symbol == "XBTUSD":
                        amount = 0.001  # Small BTC amount
                    elif symbol == "ETHUSD":
                        amount = 0.01   # Small ETH amount
                    else:
                        amount = 10     # Larger amount for cheaper coins
                    
                    await self.execute_trade(
                        symbol=symbol,
                        side=decision["action"],
                        amount=amount,
                        reason=decision["reason"]
                    )
                else:
                    print(f"   💤 Holding {symbol} - {decision['reason']}")
                
                # Small delay between trades
                await asyncio.sleep(1)
            
            # Delay between cycles
            if cycle < cycles - 1:
                print(f"\n⏳ Waiting before next cycle...")
                await asyncio.sleep(3)
        
        print(f"\n🏁 Trading strategy completed!")
        print(f"   Total trades executed: {self.trade_count}")
    
    async def run_full_test(self):
        """Run the complete agent test workflow."""
        print("🎯 LOCAL TRADING AGENT - FULL TEST WORKFLOW")
        print("="*60)
        print(f"Agent: {self.agent_name}")
        print(f"Target: HTTP MCP Trading Server")
        print("="*60)
        
        # Step 1: Connect to MCP server
        if not await self.connect():
            return False
        
        # Step 2: Test basic connectivity
        if not await self.test_basic_connectivity():
            return False
        
        # Step 3: Get account information
        if not await self.get_account_info():
            return False
        
        # Step 4: Run trading strategy
        await self.run_trading_strategy(cycles=3)
        
        print("\n🎉 FULL TEST COMPLETED SUCCESSFULLY!")
        print("="*60)
        print("✅ External agent can:")
        print("   • Connect to HTTP MCP server")
        print("   • Use all trading tools")
        print("   • Analyze markets")
        print("   • Execute trades")
        print("   • Run autonomous trading strategies")
        print("\n🚀 Ready for production deployment!")
        
        return True
    
    async def cleanup(self):
        """Clean up the agent connection."""
        if self.session:
            await self.session.close()
            print(f"🔌 {self.agent_name} disconnected from MCP server")


async def main():
    """Main function to run the test agent."""
    
    # Check if server is running
    print("🔍 Checking if MCP server is running...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/health", timeout=5)
            if response.status_code == 200:
                print("✅ MCP server is running!")
            else:
                print("❌ MCP server health check failed")
                return
    except Exception as e:
        print("❌ Cannot connect to MCP server. Make sure it's running:")
        print("   python3 local_http_trading_server.py")
        return
    
    # Create and run the test agent
    agent = LocalTradingAgent()
    
    try:
        success = await agent.run_full_test()
        
        if success:
            print("\n🎉 LOCAL AGENT TEST: SUCCESS!")
            print("Your MCP server is ready for external agents!")
        else:
            print("\n❌ LOCAL AGENT TEST: FAILED!")
            print("Check the error messages above.")
            
    except KeyboardInterrupt:
        print("\n⚠️ Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
    finally:
        await agent.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
