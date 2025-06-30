#!/usr/bin/env python3
"""
Enhanced Kraken Trading System MCP Server

Production-ready MCP server with full trading system integration.
"""

import sys
from pathlib import Path

# Add src to path
if __name__ == "__main__":
    src_path = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(src_path))

from mcp.server.fastmcp import FastMCP
from trading_systems.mcp_server.config import MCPServerConfig
from trading_systems.mcp_server.trading_adapter import TradingSystemAdapter

# Create the enhanced MCP server
mcp = FastMCP("Kraken Trading System - Production")

# Global adapter for tools to access
trading_adapter = None

@mcp.tool()
def ping() -> str:
    """Test server connectivity."""
    return "🏓 Pong! Kraken Trading System MCP Server is operational!"

@mcp.tool()
async def get_account_balance() -> str:
    """Get current account balance information."""
    global trading_adapter
    if not trading_adapter:
        return "❌ Trading adapter not initialized"
    
    try:
        balance = await trading_adapter.get_account_balance()
        return f"💰 Account Balance:\n{balance}"
    except Exception as e:
        return f"❌ Failed to get balance: {str(e)}"

@mcp.tool()
def get_server_status() -> str:
    """Get comprehensive server status."""
    global trading_adapter
    if not trading_adapter:
        return "❌ Trading adapter not initialized"
    
    try:
        status = trading_adapter.get_status()
        return f"✅ Server Status: {status.connection_details}"
    except Exception as e:
        return f"❌ Status check failed: {str(e)}"

@mcp.resource("market://status")
def market_status() -> str:
    """Current market status resource."""
    global trading_adapter
    if not trading_adapter:
        return "❌ Trading adapter not initialized"
    
    try:
        status = trading_adapter.get_market_status()
        return str(status)
    except Exception as e:
        return f"❌ Market status failed: {str(e)}"

async def initialize_server():
    """Initialize the trading system."""
    global trading_adapter
    
    try:
        config = MCPServerConfig()
        trading_adapter = TradingSystemAdapter(config)
        await trading_adapter.initialize()
        print("✅ Enhanced MCP server initialized successfully")
    except Exception as e:
        print(f"❌ Server initialization failed: {e}")

if __name__ == "__main__":
    import asyncio
    
    async def run():
        await initialize_server()
        mcp.run()
    
    asyncio.run(run())
