#!/usr/bin/env python3
"""
Local HTTP MCP Server for Testing External Agents

This creates an HTTP-accessible version of your MCP trading server
for testing with local AI agents.

Usage: python3 local_http_trading_server.py
"""

import asyncio
import sys
from pathlib import Path
import uvicorn
from mcp.server.fastmcp import FastMCP
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware

# Add your trading system to path
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

# Import your existing components
from trading_systems.mcp_server.config import MCPServerConfig
from trading_systems.mcp_server.trading_adapter import TradingSystemAdapter

# Global trading adapter
trading_adapter = None

# Create MCP server
mcp = FastMCP("Kraken Trading System - Local HTTP")

async def initialize_trading_adapter():
    """Initialize the trading adapter."""
    global trading_adapter
    
    print("🚀 Starting Local HTTP MCP Trading Server...")
    print("🔗 External agents can connect via HTTP")
    
    # Initialize trading system
    config = MCPServerConfig()
    trading_adapter = TradingSystemAdapter(config)
    await trading_adapter.initialize()
    
    print("✅ Trading system ready for local agent connections")
    print("📡 MCP endpoint: http://localhost:8000/sse")

async def shutdown_trading_adapter():
    """Shutdown the trading adapter."""
    global trading_adapter
    
    if trading_adapter:
        await trading_adapter.shutdown()
    print("🔄 Local HTTP MCP Server shutdown complete")

# =============================================================================
# MCP TOOLS - Enhanced for External Agent Testing
# =============================================================================

@mcp.tool()
def ping() -> str:
    """Test connectivity to the trading server."""
    return "🏓 Pong! HTTP MCP trading server is responding to external agent."

@mcp.tool()
async def get_account_balance() -> dict:
    """Get current account balance information."""
    try:
        global trading_adapter
        if not trading_adapter:
            return {"status": "error", "message": "Trading adapter not initialized"}
            
        balance_info = await trading_adapter.get_account_balance()
        return {
            "status": "success",
            "data": balance_info,
            "message": "Account balance retrieved for external agent",
            "timestamp": "2025-06-30T21:30:00Z"
        }
        
    except Exception as e:
        return {
            "status": "error", 
            "data": None,
            "message": f"Failed to get account balance: {str(e)}"
        }

@mcp.tool()
def get_server_status() -> dict:
    """Get current server and trading system status."""
    try:
        global trading_adapter
        if not trading_adapter:
            return {"status": "error", "message": "Trading adapter not initialized"}
            
        status = trading_adapter.get_status()
        return {
            "status": "success",
            "data": {
                "websocket_connected": status.websocket_connected,
                "order_manager_active": status.order_manager_active,
                "account_data_available": status.account_data_available,
                "last_update": status.last_update.isoformat(),
                "connection_details": status.connection_details,
                "server_mode": "HTTP",
                "external_access": True
            },
            "message": "Server status retrieved for external agent"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "data": None, 
            "message": f"Failed to get server status: {str(e)}"
        }

@mcp.tool()
async def place_demo_order(symbol: str, side: str, amount: float, order_type: str = "market") -> dict:
    """
    Place a demo trading order (safe for testing).
    
    Args:
        symbol: Trading pair (e.g., "XBTUSD", "ETHUSD")
        side: "buy" or "sell"
        amount: Order amount
        order_type: "market" or "limit"
    """
    try:
        # Validate inputs
        if side not in ["buy", "sell"]:
            return {"status": "error", "message": "Side must be 'buy' or 'sell'"}
        
        if amount <= 0:
            return {"status": "error", "message": "Amount must be positive"}
        
        if symbol not in ["XBTUSD", "ETHUSD", "ADAUSD", "SOLUSD"]:
            return {"status": "error", "message": f"Unsupported symbol: {symbol}"}
        
        # Simulate order placement (always demo mode for local testing)
        import random
        import time
        
        order_id = f"demo_{int(time.time())}_{symbol}_{side}"
        price = random.uniform(50000, 70000) if symbol == "XBTUSD" else random.uniform(3000, 4000)
        
        return {
            "status": "success",
            "data": {
                "order_id": order_id,
                "symbol": symbol,
                "side": side,
                "amount": amount,
                "order_type": order_type,
                "price": round(price, 2),
                "status": "filled",
                "demo_mode": True,
                "external_agent": True,
                "timestamp": "2025-06-30T21:30:00Z"
            },
            "message": f"Demo order placed by external agent: {side} {amount} {symbol}"
        }
            
    except Exception as e:
        return {
            "status": "error",
            "data": None,
            "message": f"Failed to place order: {str(e)}"
        }

@mcp.tool()
def get_market_data(symbol: str = "XBTUSD") -> dict:
    """
    Get current market data for a symbol.
    
    Args:
        symbol: Trading pair (e.g., "XBTUSD", "ETHUSD")
    """
    try:
        import random
        
        # Simulate market data
        if symbol == "XBTUSD":
            base_price = 65000
        elif symbol == "ETHUSD":
            base_price = 3500
        elif symbol == "ADAUSD":
            base_price = 0.45
        elif symbol == "SOLUSD":
            base_price = 180
        else:
            return {"status": "error", "message": f"Unsupported symbol: {symbol}"}
        
        # Add some random variation
        current_price = base_price * (1 + random.uniform(-0.02, 0.02))
        
        return {
            "status": "success",
            "data": {
                "symbol": symbol,
                "price": round(current_price, 2),
                "bid": round(current_price * 0.999, 2),
                "ask": round(current_price * 1.001, 2),
                "volume_24h": random.randint(1000, 10000),
                "change_24h": round(random.uniform(-5, 5), 2),
                "timestamp": "2025-06-30T21:30:00Z"
            },
            "message": f"Market data retrieved for {symbol}"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "data": None,
            "message": f"Failed to get market data: {str(e)}"
        }

# =============================================================================
# MCP RESOURCES
# =============================================================================

@mcp.resource("market://status", title="Market Status")
def get_market_status() -> str:
    """Get current market status and system information."""
    try:
        global trading_adapter
        if not trading_adapter:
            return "❌ Trading adapter not initialized"
            
        market_status = trading_adapter.get_market_status()
        return f"📊 Market Status (HTTP): {market_status}"
        
    except Exception as e:
        return f"❌ Market status unavailable: {str(e)}"

@mcp.resource("trading://capabilities", title="Trading Capabilities")
def get_trading_capabilities() -> dict:
    """Get information about what external agents can do."""
    return {
        "server_info": {
            "name": "Kraken Trading System",
            "version": "1.0.0",
            "transport": "HTTP/SSE",
            "mode": "local_testing"
        },
        "available_tools": [
            "ping",
            "get_account_balance", 
            "get_server_status",
            "place_demo_order",
            "get_market_data"
        ],
        "available_resources": [
            "market://status",
            "trading://capabilities"
        ],
        "supported_symbols": ["XBTUSD", "ETHUSD", "ADAUSD", "SOLUSD"],
        "demo_mode": True,
        "external_agent_ready": True
    }

# =============================================================================
# HTTP SERVER SETUP
# =============================================================================

def create_app():
    """Create the Starlette application with MCP integration."""
    
    # Create the ASGI app
    app = Starlette()
    
    # Add CORS middleware for local testing
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allow all origins for local testing
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add MCP SSE transport
    sse_transport = SseServerTransport("/sse")
    sse_transport.mount(app, mcp)
    
    # Health check endpoint
    async def health_check(request):
        return JSONResponse({
            "status": "healthy",
            "server": "Kraken Trading MCP Server (Local)",
            "transport": "HTTP/SSE",
            "mode": "local_testing",
            "endpoints": {
                "sse": "/sse",
                "health": "/health"
            },
            "external_agents": "ready"
        })
    
    # API info endpoint
    async def api_info(request):
        return JSONResponse({
            "name": "Kraken Trading MCP Server",
            "version": "1.0.0",
            "transport": "HTTP/SSE", 
            "mcp_endpoint": "http://localhost:8000/sse",
            "tools": ["ping", "get_account_balance", "get_server_status", "place_demo_order", "get_market_data"],
            "resources": ["market://status", "trading://capabilities"],
            "demo_mode": True,
            "local_testing": True
        })
    
    # Add routes
    app.routes = [
        Route("/health", health_check, methods=["GET"]),
        Route("/api/info", api_info, methods=["GET"]),
        Route("/", api_info, methods=["GET"]),  # Default route
    ]
    
    return app

def main():
    """Main entry point for local HTTP MCP server."""
    print("🎯 KRAKEN TRADING SYSTEM - LOCAL HTTP MCP SERVER")
    print("=" * 60)
    print("Starting HTTP MCP server for external agent testing...")
    print("=" * 60)
    
    # Create the ASGI app
    app = create_app()
    
    print("🚀 Server starting on http://localhost:8000")
    print("📡 MCP endpoint: http://localhost:8000/sse") 
    print("🏥 Health check: http://localhost:8000/health")
    print("📋 API info: http://localhost:8000/api/info")
    print("🤖 Ready for external AI agent connections!")
    print()
    print("💡 To test with external agent:")
    print("   1. Keep this server running")
    print("   2. Run the test agent in another terminal")
    print("   3. Watch the trading interactions")
    
    # Initialize trading adapter before starting server
    async def startup():
        await initialize_trading_adapter()
    
    async def shutdown():
        await shutdown_trading_adapter()
    
    # Add startup and shutdown events
    @app.on_event("startup")
    async def startup_event():
        await startup()
    
    @app.on_event("shutdown") 
    async def shutdown_event():
        await shutdown()
    
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        log_level="info",
        reload=False
    )

if __name__ == "__main__":
    main()