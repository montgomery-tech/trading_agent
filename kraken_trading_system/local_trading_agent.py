#!/usr/bin/env python3
"""
agent_1 Trading Client (Fixed)

This AI agent connects as agent_1 to the trading server and demonstrates
real trading capabilities including balance checking, market analysis, and trade execution.

Usage: python3 fixed_agent_client.py

Make sure the agent-focused trading server is running first:
python3 agent_focused_trading_server.py --http
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

# Enhanced MCP client for agent_1
class Agent1MCPClient:
    """MCP client specifically designed for agent_1 trading."""

    def __init__(self, server_url: str):
        self.server_url = server_url
        self.http_client = httpx.AsyncClient(timeout=60.0)
        self.request_id = 1

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any] = None) -> str:
        """Call an MCP tool via the direct MCP endpoint."""
        try:
            # Create proper MCP JSON-RPC request
            request_data = {
                "jsonrpc": "2.0",
                "id": self.request_id,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments or {}
                }
            }
            self.request_id += 1

            # Try the direct MCP endpoint first
            response = await self.http_client.post(
                f"{self.server_url}/mcp",
                json=request_data,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                }
            )

            if response.status_code == 200:
                try:
                    result = response.json()

                    # Handle MCP response format
                    if "result" in result:
                        tool_result = result["result"]

                        # Handle MCP content format
                        if isinstance(tool_result, dict) and "content" in tool_result:
                            content = tool_result["content"]
                            if isinstance(content, list) and len(content) > 0:
                                return content[0].get("text", str(tool_result))
                            else:
                                return str(content)
                        else:
                            return str(tool_result)
                    elif "error" in result:
                        return f"❌ MCP Error: {result['error']['message']}"
                    else:
                        return str(result)

                except json.JSONDecodeError:
                    # If JSON parsing fails, return the raw text
                    return response.text
            else:
                return f"❌ HTTP Error {response.status_code}: {response.text[:200]}"

        except Exception as e:
            return f"❌ Tool call error: {str(e)}"

    async def health_check(self) -> bool:
        """Check server health."""
        try:
            response = await self.http_client.get(f"{self.server_url}/health")
            return response.status_code == 200
        except:
            return False

    async def close(self):
        """Close the client."""
        await self.http_client.aclose()


class Agent1TradingBot:
    """
    AI Trading Bot that operates as agent_1.
    Demonstrates realistic trading scenarios and decision-making.
    """

    def __init__(self, server_url: str = "http://localhost:8000"):
        self.server_url = server_url
        self.agent_name = "agent_1"
        self.mcp_client = None

        # Trading state
        self.current_balances = {}
        self.trade_history = []
        self.market_data = {}
        self.connected = False

    async def initialize(self):
        """Initialize the trading bot."""
        print(f"🤖 Initializing {self.agent_name} Trading Bot...")
        print(f"   Target server: {self.server_url}")

        self.mcp_client = Agent1MCPClient(self.server_url)

        # Check server connectivity
        connected = await self.mcp_client.health_check()
        if not connected:
            raise ConnectionError("Cannot connect to agent-focused trading server")

        self.connected = True
        print(f"✅ {self.agent_name} connected and ready for trading!")

    # =============================================================================
    # CORE TRADING FUNCTIONS
    # =============================================================================

    async def check_my_balances(self) -> str:
        """Check current balances and update internal state."""
        print("💰 Checking my current balances...")
        result = await self.mcp_client.call_tool("get_my_balances")
        print(f"📊 Balance result: {result[:150]}...")
        return result

    async def get_market_price(self, symbol: str) -> str:
        """Get current market price for a symbol."""
        print(f"📈 Getting market price for {symbol}...")
        result = await self.mcp_client.call_tool("get_market_price", {"symbol": symbol})
        print(f"💹 Price result: {result[:100]}...")
        return result

    async def get_portfolio_summary(self) -> str:
        """Get comprehensive portfolio summary."""
        print("📊 Getting portfolio summary...")
        result = await self.mcp_client.call_tool("get_portfolio_summary")
        print(f"📈 Portfolio: {result[:150]}...")
        return result

    async def buy_asset(self, symbol: str, amount_usd: float) -> str:
        """Execute a buy order."""
        print(f"🟢 Executing BUY: ${amount_usd} of {symbol}")
        result = await self.mcp_client.call_tool("buy_asset", {
            "symbol": symbol,
            "amount_usd": amount_usd
        })

        if "✅" in result:
            print("✅ Buy order successful!")
        else:
            print(f"❌ Buy order failed: {result[:100]}")

        return result

    async def sell_asset(self, symbol: str, amount: float) -> str:
        """Execute a sell order."""
        print(f"🔴 Executing SELL: {amount} of {symbol}")
        result = await self.mcp_client.call_tool("sell_asset", {
            "symbol": symbol,
            "amount": amount
        })

        if "✅" in result:
            print("✅ Sell order successful!")
        else:
            print(f"❌ Sell order failed: {result[:100]}")

        return result

    async def execute_smart_trade(self, command: str) -> str:
        """Execute a natural language trading command."""
        print(f"🧠 Executing smart trade: '{command}'")
        result = await self.mcp_client.call_tool("execute_smart_trade", {"command": command})
        print(f"💡 Smart trade result: {result[:150]}...")
        return result

    async def debug_agent_info(self) -> str:
        """Get debug information about agent connection."""
        print("🔍 Getting agent debug info...")
        result = await self.mcp_client.call_tool("debug_agent_info")
        print(f"🔍 Debug result: {result[:200]}...")
        return result
        """Get trading history."""
        print("📋 Getting my trading history...")
        result = await self.mcp_client.call_tool("get_my_trades")
        print(f"📈 Trade history: {result[:100]}...")
        return result

    # =============================================================================
    # TRADING STRATEGIES & DEMOS
    # =============================================================================

    async def run_portfolio_check(self):
        """Run a comprehensive portfolio check."""
        print("📊 PORTFOLIO CHECK")
        print("=" * 30)

        # Check balances
        await self.check_my_balances()
        await asyncio.sleep(1)

        # Get portfolio summary
        await self.get_portfolio_summary()
        await asyncio.sleep(1)

        # Check recent trades
        await self.get_my_trades()

        print("✅ Portfolio check complete!")

    async def run_market_analysis(self):
        """Analyze current market conditions."""
        print("📈 MARKET ANALYSIS")
        print("=" * 25)

        symbols = ['BTCUSD', 'ETHUSD', 'SOLUSD', 'ADAUSD']

        for symbol in symbols:
            await self.get_market_price(symbol)
            await asyncio.sleep(0.5)

        print("✅ Market analysis complete!")

    async def run_conservative_trading_demo(self):
        """Run a conservative trading demonstration."""
        print("🛡️ CONSERVATIVE TRADING DEMO")
        print("=" * 35)

        # Check current balances first
        await self.check_my_balances()

        # Small buy order
        print("\n1. Small Bitcoin purchase...")
        await self.buy_asset("BTCUSD", 50.0)  # $50 BTC purchase
        await asyncio.sleep(2)

        # Check balance after purchase
        await self.check_my_balances()
        await asyncio.sleep(1)

        # Small Ethereum purchase
        print("\n2. Small Ethereum purchase...")
        await self.buy_asset("ETHUSD", 75.0)  # $75 ETH purchase
        await asyncio.sleep(2)

        # Portfolio summary
        print("\n3. Updated portfolio...")
        await self.get_portfolio_summary()

        print("✅ Conservative trading demo complete!")

    async def run_smart_trading_demo(self):
        """Demonstrate natural language trading."""
        print("🧠 SMART TRADING DEMO")
        print("=" * 30)

        commands = [
            "show my balance",
            "buy $25 of solana",
            "get bitcoin price",
            "buy $30 worth of ethereum",
            "show my portfolio summary",
        ]

        for i, command in enumerate(commands, 1):
            print(f"\n{i}. Command: '{command}'")
            await self.execute_smart_trade(command)
            await asyncio.sleep(2)

        print("✅ Smart trading demo complete!")

    async def run_profit_taking_demo(self):
        """Demonstrate profit-taking strategy."""
        print("💰 PROFIT TAKING DEMO")
        print("=" * 25)

        # Check current holdings
        await self.get_portfolio_summary()
        await asyncio.sleep(1)

        # Smart sell commands
        sell_commands = [
            "sell 25% of my bitcoin",
            "sell half my ethereum",
            "sell 0.1 ethereum"
        ]

        for i, command in enumerate(sell_commands, 1):
            print(f"\n{i}. Executing: '{command}'")
            result = await self.execute_smart_trade(command)

            # Only proceed if we have assets to sell
            if "Insufficient" in result or ("No" in result and "balance" in result):
                print("   ⚠️ Skipping - insufficient balance")
            else:
                await asyncio.sleep(2)

        # Final portfolio check
        print("\nFinal portfolio after profit taking:")
        await self.get_portfolio_summary()

        print("✅ Profit taking demo complete!")

    async def run_interactive_trading_session(self):
        """Run an interactive trading session."""
        print("🎮 INTERACTIVE TRADING SESSION")
        print("=" * 40)
        print("Available commands:")
        print("  'balance' - Check my balances")
        print("  'portfolio' - Portfolio summary")
        print("  'debug' - Debug agent connection info")
        print("  'price <asset>' - Get asset price (btc, eth, sol, ada)")
        print("  'buy $X <asset>' - Buy asset with USD")
        print("  'sell X <asset>' - Sell amount of asset")
        print("  'trades' - My trade history")
        print("  'smart: <command>' - Natural language trading")
        print("  'quit' - Exit session")
        print()

        while True:
            try:
                command = input("agent_1> ").strip().lower()

                if command in ['quit', 'exit', 'q']:
                    break

                if command == 'balance':
                    await self.check_my_balances()

                elif command == 'portfolio':
                    await self.get_portfolio_summary()

                elif command == 'debug':
                    await self.debug_agent_info()

                elif command.startswith('price'):
                    parts = command.split()
                    if len(parts) > 1:
                        asset = parts[1].upper()
                        symbol_map = {
                            'BTC': 'BTCUSD', 'BITCOIN': 'BTCUSD',
                            'ETH': 'ETHUSD', 'ETHEREUM': 'ETHUSD',
                            'SOL': 'SOLUSD', 'SOLANA': 'SOLUSD',
                            'ADA': 'ADAUSD', 'CARDANO': 'ADAUSD'
                        }
                        symbol = symbol_map.get(asset, f"{asset}USD")
                        await self.get_market_price(symbol)
                    else:
                        print("Usage: price <asset> (btc, eth, sol, ada)")

                elif command.startswith('buy'):
                    # Parse: buy $50 btc
                    parts = command.split()
                    if len(parts) >= 3:
                        try:
                            amount_str = parts[1].replace('$', '')
                            amount = float(amount_str)
                            asset = parts[2].upper()
                            symbol_map = {
                                'BTC': 'BTCUSD', 'BITCOIN': 'BTCUSD',
                                'ETH': 'ETHUSD', 'ETHEREUM': 'ETHUSD',
                                'SOL': 'SOLUSD', 'SOLANA': 'SOLUSD',
                                'ADA': 'ADAUSD', 'CARDANO': 'ADAUSD'
                            }
                            symbol = symbol_map.get(asset, f"{asset}USD")
                            await self.buy_asset(symbol, amount)
                        except ValueError:
                            print("Usage: buy $<amount> <asset>")
                    else:
                        print("Usage: buy $<amount> <asset>")

                elif command.startswith('sell'):
                    # Parse: sell 0.1 btc
                    parts = command.split()
                    if len(parts) >= 3:
                        try:
                            amount = float(parts[1])
                            asset = parts[2].upper()
                            symbol_map = {
                                'BTC': 'BTCUSD', 'BITCOIN': 'BTCUSD',
                                'ETH': 'ETHUSD', 'ETHEREUM': 'ETHUSD',
                                'SOL': 'SOLUSD', 'SOLANA': 'SOLUSD',
                                'ADA': 'ADAUSD', 'CARDANO': 'ADAUSD'
                            }
                            symbol = symbol_map.get(asset, f"{asset}USD")
                            await self.sell_asset(symbol, amount)
                        except ValueError:
                            print("Usage: sell <amount> <asset>")
                    else:
                        print("Usage: sell <amount> <asset>")

                elif command == 'trades':
                    await self.get_my_trades()

                elif command.startswith('smart:'):
                    smart_command = command[6:].strip()
                    await self.execute_smart_trade(smart_command)

                else:
                    print("Unknown command. Type 'quit' to exit.")

                print()  # Add spacing

            except KeyboardInterrupt:
                print("\n⚠️ Exiting interactive session...")
                break
            except Exception as e:
                print(f"❌ Error: {e}")

    async def run_full_trading_workflow(self):
        """Run a comprehensive trading workflow demonstration."""
        print("🚀 FULL TRADING WORKFLOW")
        print("=" * 35)

        workflows = [
            ("Initial Portfolio Assessment", self.run_portfolio_check),
            ("Market Analysis", self.run_market_analysis),
            ("Conservative Trading", self.run_conservative_trading_demo),
            ("Smart Trading Commands", self.run_smart_trading_demo),
            ("Final Portfolio Review", self.run_portfolio_check)
        ]

        for i, (name, workflow_func) in enumerate(workflows, 1):
            print(f"\n{'='*50}")
            print(f"WORKFLOW {i}/{len(workflows)}: {name.upper()}")
            print(f"{'='*50}")

            await workflow_func()

            if i < len(workflows):
                print(f"\n⏸️ Workflow {i} complete. Continuing in 3 seconds...")
                await asyncio.sleep(3)

        print("\n🎉 FULL TRADING WORKFLOW COMPLETE!")
        print("📊 Final Summary:")
        await self.get_portfolio_summary()

    async def cleanup(self):
        """Clean up bot resources."""
        print(f"🧹 Cleaning up {self.agent_name} Trading Bot...")

        if self.mcp_client:
            await self.mcp_client.close()
            print("✅ MCP client closed")

        print(f"✅ {self.agent_name} cleanup complete")

# =============================================================================
# MAIN EXECUTION
# =============================================================================

async def main():
    """Main function to run agent_1 trading bot."""
    print("🤖 AGENT_1 TRADING BOT")
    print("=" * 50)
    print("This AI agent operates as agent_1 and demonstrates")
    print("real trading capabilities with balance management!")
    print("=" * 50)
    print()

    bot = Agent1TradingBot()

    try:
        # Initialize the bot
        await bot.initialize()
        print()

        # Ask user what they want to do
        print("🎯 Choose a trading demonstration:")
        print("   1. Portfolio check (safe)")
        print("   2. Market analysis (safe)")
        print("   3. Conservative trading demo (small trades)")
        print("   4. Smart trading demo (natural language)")
        print("   5. Profit taking demo (sell assets)")
        print("   6. Full trading workflow (comprehensive)")
        print("   7. Interactive trading session")
        print()

        choice = input("Enter choice (1-7): ").strip()

        if choice == "1":
            await bot.run_portfolio_check()
        elif choice == "2":
            await bot.run_market_analysis()
        elif choice == "3":
            print("⚠️ This will execute REAL trades with small amounts!")
            confirm = input("Continue? (yes/no): ").strip().lower()
            if confirm == "yes":
                await bot.run_conservative_trading_demo()
            else:
                print("❌ Demo cancelled")
        elif choice == "4":
            await bot.run_smart_trading_demo()
        elif choice == "5":
            await bot.run_profit_taking_demo()
        elif choice == "6":
            print("⚠️ This will run a full trading workflow!")
            confirm = input("Continue? (yes/no): ").strip().lower()
            if confirm == "yes":
                await bot.run_full_trading_workflow()
            else:
                print("❌ Workflow cancelled")
        elif choice == "7":
            await bot.run_interactive_trading_session()
        else:
            print("❌ Invalid choice")

        print(f"\n📊 AGENT_1 SESSION SUMMARY:")
        print(f"   Connected as: {bot.agent_name}")
        print(f"   Server: {bot.server_url}")
        print(f"   Status: {'Connected' if bot.connected else 'Disconnected'}")

        # Final portfolio check
        print("\n📈 Final Portfolio Status:")
        await bot.get_portfolio_summary()

    except KeyboardInterrupt:
        print(f"\n⚠️ {bot.agent_name} interrupted by user")
    except Exception as e:
        print(f"\n❌ {bot.agent_name} error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await bot.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
