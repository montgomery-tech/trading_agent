#!/usr/bin/env python3
"""
Working Trading Agent with Proper MCP Integration

This agent properly connects to your MCP server and executes real trades.

Usage: python3 working_trading_agent.py

Make sure the MCP server is running first:
python3 consolidated_mcp_server.py --http
"""

import asyncio
import sys
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

# Import HTTP client
try:
    import httpx
    print("✅ HTTP client available")
except ImportError as e:
    print("❌ Missing httpx. Install with: pip install httpx")
    sys.exit(1)

# Simple MCP client implementation
class SimpleMCPClient:
    """Simplified MCP client that works with your server."""

    def __init__(self, server_url: str):
        self.server_url = server_url
        self.http_client = httpx.AsyncClient(timeout=30.0)

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any] = None) -> str:
        """Call an MCP tool via HTTP POST."""
        try:
            # Create MCP-style request
            request_data = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments or {}
                }
            }

            # Send to MCP endpoint
            response = await self.http_client.post(
                f"{self.server_url}/sse",
                json=request_data,
                headers={"Content-Type": "application/json"}
            )

            if response.status_code == 200:
                result = response.json()
                return result.get("result", {}).get("content", [{}])[0].get("text", "No result")
            else:
                return f"HTTP Error {response.status_code}: {response.text}"

        except Exception as e:
            return f"Tool call error: {str(e)}"

    async def close(self):
        """Close the client."""
        await self.http_client.aclose()


class WorkingTradingAgent:
    """
    A working trading agent that properly connects to your MCP server
    and executes real trades through your trading system.
    """

    def __init__(self, server_url: str = "http://localhost:8000"):
        self.server_url = server_url
        self.health_endpoint = f"{server_url}/health"

        # Agent properties
        self.agent_name = "WorkingTradingAgent"
        self.mcp_client = None
        self.http_client = None

        # Trading state
        self.trade_history = []
        self.connected = False

        # Safety settings
        self.max_trade_usd = 20.0  # Conservative $20 limit
        self.max_trades_per_session = 3
        self.trade_count = 0

    async def initialize(self):
        """Initialize the agent and connections."""
        print(f"🤖 Initializing {self.agent_name}...")
        print(f"   Target server: {self.server_url}")

        # Create HTTP client for health checks
        self.http_client = httpx.AsyncClient(timeout=30.0)

        # Check server connectivity
        connected = await self.check_server_health()
        if not connected:
            raise ConnectionError("Cannot connect to MCP server")

        # Create simplified MCP client
        self.mcp_client = SimpleMCPClient(self.server_url)

        self.connected = True
        print(f"✅ {self.agent_name} initialized successfully")

    async def check_server_health(self) -> bool:
        """Check if the MCP server is running and healthy."""
        print("🔍 Checking server health...")

        try:
            response = await self.http_client.get(self.health_endpoint)
            if response.status_code == 200:
                health_data = response.json()
                print(f"✅ Server healthy: {health_data.get('server', 'Unknown')}")
                return True
            else:
                print(f"❌ Server health check failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Cannot reach server: {e}")
            print("💡 Make sure the MCP server is running:")
            print("   python3 consolidated_mcp_server.py --http")
            return False

    # =============================================================================
    # DIRECT MCP TOOL CALLS
    # =============================================================================

    async def ping_server(self) -> str:
        """Test server connectivity."""
        print("🏓 Pinging server...")
        result = await self.mcp_client.call_tool("ping")
        print(f"📨 Server response: {result}")
        return result

    async def get_account_balance(self) -> str:
        """Get current account balance."""
        print("💰 Getting account balance...")
        result = await self.mcp_client.call_tool("get_account_balance")
        print(f"📊 Balance result: {result[:200]}..." if len(result) > 200 else result)
        return result

    async def get_eth_price(self) -> str:
        """Get current ETH price."""
        print("📈 Getting ETH price...")
        result = await self.mcp_client.call_tool("get_eth_price")
        print(f"💹 Price result: {result[:200]}..." if len(result) > 200 else result)
        return result

    async def buy_eth(self, amount_usd: float) -> str:
        """Buy ETH with USD."""
        print(f"📈 Buying ${amount_usd} worth of ETH...")

        # Safety check
        if amount_usd > self.max_trade_usd:
            error_msg = f"❌ Amount ${amount_usd} exceeds safety limit of ${self.max_trade_usd}"
            print(error_msg)
            return error_msg

        if self.trade_count >= self.max_trades_per_session:
            error_msg = f"❌ Max trades ({self.max_trades_per_session}) reached for this session"
            print(error_msg)
            return error_msg

        result = await self.mcp_client.call_tool("buy_eth", {
            "amount_usd": amount_usd,
            "order_type": "market"
        })

        # Log the trade
        self.trade_count += 1
        self.trade_history.append({
            "timestamp": datetime.now().isoformat(),
            "action": "buy",
            "amount_usd": amount_usd,
            "result": result[:100] + "..." if len(result) > 100 else result
        })

        print(f"✅ Buy order result: {result[:200]}..." if len(result) > 200 else result)
        return result

    async def sell_eth(self, amount_eth: float) -> str:
        """Sell ETH for USD."""
        print(f"📉 Selling {amount_eth} ETH...")

        # Safety check
        if self.trade_count >= self.max_trades_per_session:
            error_msg = f"❌ Max trades ({self.max_trades_per_session}) reached for this session"
            print(error_msg)
            return error_msg

        result = await self.mcp_client.call_tool("sell_eth", {
            "amount_eth": amount_eth,
            "order_type": "market"
        })

        # Log the trade
        self.trade_count += 1
        self.trade_history.append({
            "timestamp": datetime.now().isoformat(),
            "action": "sell",
            "amount_eth": amount_eth,
            "result": result[:100] + "..." if len(result) > 100 else result
        })

        print(f"✅ Sell order result: {result[:200]}..." if len(result) > 200 else result)
        return result

    async def get_order_status(self) -> str:
        """Get order status."""
        print("📋 Getting order status...")
        result = await self.mcp_client.call_tool("get_order_status")
        print(f"📊 Order status: {result[:200]}..." if len(result) > 200 else result)
        return result

    async def execute_trading_prompt(self, prompt: str) -> str:
        """Execute a natural language trading prompt."""
        print(f"🤖 Processing prompt: '{prompt}'")
        result = await self.mcp_client.call_tool("execute_trading_prompt", {
            "prompt": prompt
        })
        print(f"✅ Prompt result: {result[:200]}..." if len(result) > 200 else result)
        return result

    # =============================================================================
    # DEMO WORKFLOWS
    # =============================================================================

    async def run_connectivity_test(self):
        """Test basic connectivity and tool access."""
        print("🧪 CONNECTIVITY TEST")
        print("=" * 50)

        # Test ping
        await self.ping_server()
        print()

        # Test account balance
        await self.get_account_balance()
        print()

        # Test price check
        await self.get_eth_price()
        print()

        print("✅ Connectivity test complete!")

    async def run_trading_demo(self):
        """Run a safe trading demonstration."""
        print("🎭 TRADING DEMO")
        print("=" * 50)
        print(f"Safety limits: ${self.max_trade_usd} per trade, {self.max_trades_per_session} trades max")
        print()

        # Step 1: Check account
        print("Step 1: Check account balance")
        await self.get_account_balance()
        print()

        # Step 2: Check price
        print("Step 2: Check current ETH price")
        await self.get_eth_price()
        print()

        # Step 3: Small buy order
        print("Step 3: Place small buy order")
        await self.buy_eth(5.0)  # $5 buy order
        print()

        # Step 4: Check order status
        print("Step 4: Check order status")
        await self.get_order_status()
        print()

        # Step 5: Small sell order
        print("Step 5: Place small sell order")
        await self.sell_eth(0.002)  # 0.002 ETH sell order
        print()

        print("✅ Trading demo complete!")

    async def run_natural_language_demo(self):
        """Demonstrate natural language processing."""
        print("🗣️ NATURAL LANGUAGE DEMO")
        print("=" * 50)

        prompts = [
            "What is my account balance?",
            "What's the current price of ETH?",
            "Buy $3 worth of ETH",
            "Check my recent orders",
            "Sell 0.001 ETH"
        ]

        for i, prompt in enumerate(prompts, 1):
            print(f"Demo {i}/{len(prompts)}: '{prompt}'")
            await self.execute_trading_prompt(prompt)
            print()
            await asyncio.sleep(1)  # Brief pause

        print("✅ Natural language demo complete!")

    async def run_interactive_mode(self):
        """Run interactive command mode."""
        print("🎮 INTERACTIVE MODE")
        print("=" * 50)
        print("Type commands or 'quit' to exit")
        print("Examples: 'check balance', 'buy $2 ETH', 'get price'")
        print()

        while True:
            try:
                command = input("Trading command: ").strip()
                if command.lower() in ['quit', 'exit', 'q']:
                    break
                if command:
                    await self.execute_trading_prompt(command)
                    print()
            except KeyboardInterrupt:
                print("\n⚠️ Exiting interactive mode...")
                break

    async def cleanup(self):
        """Clean up agent resources."""
        print(f"🧹 Cleaning up {self.agent_name}...")

        if self.mcp_client:
            await self.mcp_client.close()
            print("✅ MCP client closed")

        if self.http_client:
            try:
                await self.http_client.aclose()
                print("✅ HTTP client closed")
            except:
                pass  # Ignore cleanup errors

        print(f"✅ {self.agent_name} cleanup complete")

# =============================================================================
# MAIN EXECUTION
# =============================================================================

async def main():
    """Main function to run the working trading agent."""
    print("🤖 WORKING TRADING AGENT")
    print("=" * 60)
    print("This agent properly connects to your MCP server and")
    print("executes REAL trades through your trading system!")
    print("=" * 60)
    print()

    agent = WorkingTradingAgent()

    try:
        # Initialize the agent
        await agent.initialize()
        print()

        # Ask user what they want to do
        print("🎯 Choose an option:")
        print("   1. Connectivity test (safe)")
        print("   2. Trading demo (small real trades)")
        print("   3. Natural language demo")
        print("   4. Interactive mode")
        print()

        choice = input("Enter choice (1-4): ").strip()

        if choice == "1":
            await agent.run_connectivity_test()
        elif choice == "2":
            print("⚠️ This will execute REAL trades with small amounts!")
            confirm = input("Continue? (yes/no): ").strip().lower()
            if confirm == "yes":
                await agent.run_trading_demo()
            else:
                print("❌ Trading demo cancelled")
        elif choice == "3":
            await agent.run_natural_language_demo()
        elif choice == "4":
            await agent.run_interactive_mode()
        else:
            print("❌ Invalid choice")

        print("\n📊 AGENT SESSION SUMMARY:")
        print(f"   Trades executed: {agent.trade_count}")
        print(f"   Trade history: {len(agent.trade_history)} entries")
        if agent.trade_history:
            print("   Recent trades:")
            for trade in agent.trade_history[-3:]:
                action = trade.get('action', 'unknown')
                timestamp = trade.get('timestamp', 'unknown')
                if 'amount_usd' in trade:
                    amount = f"${trade['amount_usd']}"
                elif 'amount_eth' in trade:
                    amount = f"{trade['amount_eth']} ETH"
                else:
                    amount = "unknown amount"
                print(f"     {timestamp}: {action} {amount}")

    except KeyboardInterrupt:
        print("\n⚠️ Agent interrupted by user")
    except Exception as e:
        print(f"\n❌ Agent error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await agent.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
