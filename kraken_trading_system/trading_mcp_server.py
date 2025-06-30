#!/usr/bin/env python3
"""
Trading System MCP Server

A working MCP server that integrates with your trading system.
"""

import sys
import asyncio
import json
from pathlib import Path
from datetime import datetime

# Add src to path
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

try:
    from mcp.server.fastmcp import FastMCP
    print("✅ MCP SDK imported successfully")
except ImportError as e:
    print(f"❌ MCP SDK import failed: {e}")
    sys.exit(1)

# Initialize the FastMCP server
mcp = FastMCP("Trading System")

# Global trading components
trading_adapter = None
config = None

async def initialize_trading_system():
    """Initialize the trading system components."""
    global trading_adapter, config
    
    try:
        print("🔄 Initializing trading system...")
        
        from trading_systems.mcp_server.config import MCPServerConfig
        from trading_systems.mcp_server.trading_adapter import TradingSystemAdapter
        
        config = MCPServerConfig()
        trading_adapter = TradingSystemAdapter(config)
        await trading_adapter.initialize()
        
        print("✅ Trading system initialized successfully")
        
    except Exception as e:
        print(f"⚠️ Trading system initialization failed: {e}")
        print("🎭 Continuing in mock mode...")

# =============================================================================
# MCP TOOLS FOR CLAUDE
# =============================================================================

@mcp.tool()
def ping() -> str:
    """Test connectivity to the Kraken trading system."""
    return "🏓 Pong! Trading System MCP Server is operational!"

@mcp.tool()
async def get_account_balance() -> str:
    """Get current account balance information."""
    global trading_adapter
    
    if trading_adapter:
        try:
            balance = await trading_adapter.get_account_balance()
            return f"💰 Account Balance:\n{json.dumps(balance, indent=2)}"
        except Exception as e:
            return f"❌ Error getting balance: {str(e)}"
    else:
        # Mock data for demo
        mock_balance = {
            "USD": {"balance": "10000.00", "available": "8500.00"},
            "XBT": {"balance": "0.25", "available": "0.25"},
            "ETH": {"balance": "5.0", "available": "5.0"}
        }
        return f"💰 Demo Account Balance:\n{json.dumps(mock_balance, indent=2)}"

@mcp.tool()
def get_server_status() -> str:
    """Get comprehensive server and trading system status."""
    global trading_adapter, config
    
    status = {
        "server": "online",
        "timestamp": datetime.now().isoformat(),
        "mcp_server": "Trading System",
        "version": "1.0.0"
    }
    
    if trading_adapter and config:
        try:
            adapter_status = trading_adapter.get_status()
            status.update({
                "trading_system": adapter_status.connection_details,
                "security": {
                    "authentication_required": config.security.require_authentication,
                    "max_order_value": config.security.max_order_value_usd,
                    "rate_limiting": True
                }
            })
        except Exception as e:
            status["trading_system_error"] = str(e)
    else:
        status["trading_system"] = "mock_mode"
    
    return f"✅ Server Status:\n{json.dumps(status, indent=2)}"

@mcp.tool()
def get_market_info() -> str:
    """Get current market information and trading pairs."""
    global trading_adapter
    
    if trading_adapter:
        try:
            market_status = trading_adapter.get_market_status()
            return f"📊 Market Status:\n{json.dumps(market_status, indent=2)}"
        except Exception as e:
            return f"❌ Error getting market info: {str(e)}"
    else:
        # Mock market data
        mock_market = {
            "status": "online",
            "trading_pairs": ["XBT/USD", "ETH/USD", "ADA/USD"],
            "timestamp": datetime.now().isoformat(),
            "mode": "demo"
        }
        return f"📊 Demo Market Info:\n{json.dumps(mock_market, indent=2)}"

# =============================================================================
# MCP RESOURCES FOR CLAUDE
# =============================================================================

@mcp.resource("trading://status")
def trading_status_resource() -> str:
    """Real-time trading system status resource."""
    global trading_adapter
    
    if trading_adapter:
        try:
            status = trading_adapter.get_status()
            return json.dumps({
                "resource_type": "trading_status",
                "status": status.connection_details,
                "timestamp": datetime.now().isoformat()
            }, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)
    else:
        return json.dumps({
            "resource_type": "trading_status", 
            "status": "demo_mode",
            "timestamp": datetime.now().isoformat()
        }, indent=2)

@mcp.resource("market://data")
def market_data_resource() -> str:
    """Market data resource for analysis."""
    return json.dumps({
        "resource_type": "market_data",
        "pairs": ["XBT/USD", "ETH/USD"],
        "status": "demo",
        "timestamp": datetime.now().isoformat()
    }, indent=2)

# =============================================================================
# SERVER LIFECYCLE
# =============================================================================

async def server_startup():
    """Server startup routine."""
    print("🚀 Starting Trading System MCP Server...")
    await initialize_trading_system()
    print("✅ MCP Server ready for connections")

async def server_shutdown():
    """Server shutdown routine."""
    global trading_adapter
    
    print("🔄 Shutting down MCP Server...")
    
    if trading_adapter:
        try:
            await trading_adapter.shutdown()
            print("✅ Trading system shutdown complete")
        except Exception as e:
            print(f"⚠️ Error during shutdown: {e}")
    
    print("✅ MCP Server shutdown complete")

# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

async def main():
    """Main server function."""
    try:
        await server_startup()
        
        # Run the FastMCP server
        # Note: mcp.run() is blocking, so startup must happen before
        mcp.run()
        
    except KeyboardInterrupt:
        print("⚠️ Server interrupted by user")
    except Exception as e:
        print(f"❌ Server error: {e}")
    finally:
        await server_shutdown()

if __name__ == "__main__":
    # For direct testing
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        async def test_server():
            await server_startup()
            
            # Test tools
            print("\n🧪 Testing MCP tools:")
            print(f"ping: {ping()}")
            print(f"balance: {await get_account_balance()}")
            print(f"status: {get_server_status()}")
            print(f"market: {get_market_info()}")
            
            await server_shutdown()
        
        asyncio.run(test_server())
    else:
        # Normal server run for Claude Desktop
        asyncio.run(main())
