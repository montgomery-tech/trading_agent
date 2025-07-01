#!/usr/bin/env python3
"""
Simple HTTP MCP Server - Compatible Version

This is a simplified version that avoids the lifespan issues
and uses a pattern similar to your working stdio server.

Usage: python3 simple_http_server.py
"""

import asyncio
import sys
import json
from pathlib import Path

# Add your trading system to path
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

# Try imports - show helpful error if missing
try:
    import uvicorn
    from starlette.applications import Starlette
    from starlette.routing import Route
    from starlette.responses import JSONResponse
    from starlette.middleware.cors import CORSMiddleware
    from mcp.server.fastmcp import FastMCP
    from mcp.server.sse import SseServerTransport
except ImportError as e:
    print(f"❌ Missing required packages: {e}")
    print("Install with: pip install uvicorn starlette mcp")
    sys.exit(1)

# Import your trading components
from trading_systems.mcp_server.config import MCPServerConfig
from trading_systems.mcp_server.trading_adapter import TradingSystemAdapter

# Global variables
trading_adapter = None
mcp_server = FastMCP("Simple HTTP Trading Server")

# =============================================================================
# SERVER STARTUP/SHUTDOWN
# =============================================================================

async def startup_server():
    """Initialize the trading system."""
    global trading_adapter
    
    print("🚀 Initializing trading system...")
    
    config = MCPServerConfig()
    trading_adapter = TradingSystemAdapter(config)
    await trading_adapter.initialize()
    
    print("✅ Trading system ready!")

async def shutdown_server():
    """Clean shutdown of trading system."""
    global trading_adapter
    
    print("🔄 Shutting down trading system...")
    
    if trading_adapter:
        await trading_adapter.shutdown()
    
    print("✅ Shutdown complete!")

# =============================================================================
# MCP TOOLS - Simple versions
# =============================================================================

@mcp_server.tool()
def ping() -> str:
    """Test connectivity to the trading server."""
    return "🏓 Pong! Simple HTTP MCP server responding."

@mcp_server.tool()
async def get_account_balance() -> str:
    """Get current account balance information."""
    try:
        if not trading_adapter:
            return "❌ Trading adapter not ready"
            
        balance_info = await trading_adapter.get_account_balance()
        
        # Return as JSON string for simplicity
        result = {
            "status": "success",
            "data": balance_info,
            "message": "Balance retrieved via HTTP MCP"
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return f"❌ Error getting balance: {str(e)}"

@mcp_server.tool()
def get_server_status() -> str:
    """Get current server status."""
    try:
        if not trading_adapter:
            return "❌ Trading adapter not ready"
            
        status = trading_adapter.get_status()
        
        result = {
            "status": "success",
            "data": {
                "websocket_connected": status.websocket_connected,
                "order_manager_active": status.order_manager_active,
                "demo_mode": status.connection_details.get("mode") == "demo",
                "server_type": "HTTP MCP",
                "external_agent_ready": True
            },
            "message": "Status retrieved via HTTP MCP"
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return f"❌ Error getting status: {str(e)}"

@mcp_server.tool()
def place_demo_order(symbol: str, side: str, amount: float) -> str:
    """
    Place a demo order for testing.
    
    Args:
        symbol: Trading pair (e.g. "XBTUSD")
        side: "buy" or "sell" 
        amount: Order amount
    """
    try:
        # Validate inputs
        if side not in ["buy", "sell"]:
            return "❌ Side must be 'buy' or 'sell'"
        
        if amount <= 0:
            return "❌ Amount must be positive"
        
        # Simulate order for demo
        import time
        order_id = f"demo_{int(time.time())}_{symbol}_{side}"
        
        result = {
            "status": "success",
            "data": {
                "order_id": order_id,
                "symbol": symbol,
                "side": side,
                "amount": amount,
                "demo_mode": True,
                "filled": True,
                "server_type": "HTTP MCP"
            },
            "message": f"Demo order placed: {side} {amount} {symbol}"
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return f"❌ Error placing order: {str(e)}"

@mcp_server.tool()
def get_market_data(symbol: str = "XBTUSD") -> str:
    """
    Get market data for a symbol.
    
    Args:
        symbol: Trading pair (default: "XBTUSD")
    """
    try:
        import random
        
        # Simulate market data
        prices = {
            "XBTUSD": 65000,
            "ETHUSD": 3500,
            "ADAUSD": 0.45,
            "SOLUSD": 180
        }
        
        base_price = prices.get(symbol, 50000)
        current_price = base_price * (1 + random.uniform(-0.02, 0.02))
        
        result = {
            "status": "success",
            "data": {
                "symbol": symbol,
                "price": round(current_price, 2),
                "change_24h": round(random.uniform(-5, 5), 2),
                "volume": random.randint(1000, 10000),
                "server_type": "HTTP MCP"
            },
            "message": f"Market data for {symbol}"
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return f"❌ Error getting market data: {str(e)}"

# =============================================================================
# MCP RESOURCES
# =============================================================================

@mcp_server.resource("trading://info")
def get_trading_info() -> str:
    """Get trading server information."""
    info = {
        "server_name": "Simple HTTP MCP Trading Server",
        "version": "1.0.0",
        "transport": "HTTP/SSE",
        "demo_mode": True,
        "available_tools": [
            "ping",
            "get_account_balance",
            "get_server_status", 
            "place_demo_order",
            "get_market_data"
        ],
        "test_ready": True
    }
    
    return json.dumps(info, indent=2)

# =============================================================================
# HTTP SERVER SETUP
# =============================================================================

def create_app():
    """Create the HTTP application."""
    app = Starlette()
    
    # Add CORS for local testing
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add MCP SSE endpoint
    sse_transport = SseServerTransport("/sse")
    sse_transport.mount(app, mcp_server)
    
    # Simple health check
    async def health(request):
        return JSONResponse({
            "status": "healthy",
            "server": "Simple HTTP MCP Trading Server",
            "mcp_endpoint": "/sse",
            "ready": trading_adapter is not None
        })
    
    # API info
    async def info(request):
        return JSONResponse({
            "name": "Simple HTTP MCP Trading Server",
            "mcp_endpoint": "http://localhost:8000/sse",
            "tools": ["ping", "get_account_balance", "get_server_status", "place_demo_order", "get_market_data"],
            "demo_mode": True,
            "test_ready": True
        })
    
    app.routes = [
        Route("/health", health, methods=["GET"]),
        Route("/", info, methods=["GET"]),
    ]
    
    return app

# =============================================================================
# MAIN FUNCTION
# =============================================================================

async def main():
    """Main function with proper async handling."""
    print("🎯 SIMPLE HTTP MCP TRADING SERVER")
    print("=" * 50)
    
    try:
        # Initialize trading system first
        await startup_server()
        
        # Create app
        app = create_app()
        
        print("🚀 Starting HTTP server on localhost:8000")
        print("📡 MCP endpoint: http://localhost:8000/sse")
        print("🏥 Health check: http://localhost:8000/health")
        print("🤖 Ready for external agent testing!")
        print()
        print("💡 In another terminal, run:")
        print("   python3 local_test_agent.py")
        
        # Run server
        config = uvicorn.Config(
            app=app,
            host="127.0.0.1",
            port=8000,
            log_level="info"
        )
        
        server = uvicorn.Server(config)
        await server.serve()
        
    except KeyboardInterrupt:
        print("\n⚠️ Server interrupted by user")
    except Exception as e:
        print(f"\n❌ Server error: {e}")
    finally:
        await shutdown_server()

if __name__ == "__main__":
    asyncio.run(main())
