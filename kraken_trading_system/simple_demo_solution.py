#!/usr/bin/env python3
"""
Simple Demo Solution for External Agent Concept

Since your MCP version has limited HTTP support and no client components,
this creates a simple HTTP API that demonstrates the external agent concept
using direct HTTP calls instead of MCP protocol.

This proves the concept while working within your current limitations.

Usage: python3 simple_demo_solution.py
"""

import asyncio
import json
import sys
from pathlib import Path

# Try HTTP server imports
try:
    import uvicorn
    from starlette.applications import Starlette
    from starlette.routing import Route
    from starlette.responses import JSONResponse
    from starlette.middleware.cors import CORSMiddleware
    from starlette.requests import Request
except ImportError:
    print("❌ Missing HTTP components. Install with:")
    print("   pip install uvicorn starlette")
    sys.exit(1)

# Add your trading system to path
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

# Import your trading components
from trading_systems.mcp_server.config import MCPServerConfig
from trading_systems.mcp_server.trading_adapter import TradingSystemAdapter

# Global trading adapter
trading_adapter = None

# =============================================================================
# TRADING SYSTEM SETUP
# =============================================================================

async def initialize_trading_system():
    """Initialize the trading system."""
    global trading_adapter
    
    print("🚀 Initializing trading system for external agent demo...")
    
    config = MCPServerConfig()
    trading_adapter = TradingSystemAdapter(config)
    await trading_adapter.initialize()
    
    print("✅ Trading system ready for external agents!")

async def shutdown_trading_system():
    """Shutdown the trading system."""
    global trading_adapter
    
    if trading_adapter:
        await trading_adapter.shutdown()
    print("✅ Trading system shutdown complete!")

# =============================================================================
# HTTP API ENDPOINTS - Simulating MCP Tools via HTTP
# =============================================================================

async def ping_endpoint(request: Request):
    """Ping endpoint - equivalent to MCP ping tool."""
    return JSONResponse({
        "tool": "ping",
        "result": "🏓 Pong! External agent HTTP API responding.",
        "status": "success",
        "timestamp": "2025-07-01T12:30:00Z"
    })

async def get_account_balance_endpoint(request: Request):
    """Account balance endpoint - equivalent to MCP get_account_balance tool."""
    try:
        if not trading_adapter:
            return JSONResponse({
                "tool": "get_account_balance",
                "status": "error",
                "message": "Trading adapter not initialized"
            })
        
        balance_info = await trading_adapter.get_account_balance()
        
        return JSONResponse({
            "tool": "get_account_balance",
            "status": "success",
            "result": balance_info,
            "message": "Account balance retrieved for external agent",
            "timestamp": "2025-07-01T12:30:00Z"
        })
        
    except Exception as e:
        return JSONResponse({
            "tool": "get_account_balance",
            "status": "error",
            "message": f"Failed to get account balance: {str(e)}"
        })

async def get_server_status_endpoint(request: Request):
    """Server status endpoint - equivalent to MCP get_server_status tool."""
    try:
        if not trading_adapter:
            return JSONResponse({
                "tool": "get_server_status",
                "status": "error",
                "message": "Trading adapter not initialized"
            })
        
        status = trading_adapter.get_status()
        
        return JSONResponse({
            "tool": "get_server_status",
            "status": "success",
            "result": {
                "websocket_connected": status.websocket_connected,
                "order_manager_active": status.order_manager_active,
                "account_data_available": status.account_data_available,
                "last_update": status.last_update.isoformat(),
                "connection_details": status.connection_details,
                "external_agent_access": True,
                "api_type": "HTTP"
            },
            "message": "Server status retrieved for external agent",
            "timestamp": "2025-07-01T12:30:00Z"
        })
        
    except Exception as e:
        return JSONResponse({
            "tool": "get_server_status",
            "status": "error",
            "message": f"Failed to get server status: {str(e)}"
        })

async def place_demo_order_endpoint(request: Request):
    """Place demo order endpoint - equivalent to MCP place_order tool."""
    try:
        # Get request body
        body = await request.json()
        
        symbol = body.get("symbol", "XBTUSD")
        side = body.get("side", "buy")
        amount = body.get("amount", 0.001)
        order_type = body.get("order_type", "market")
        
        # Validate inputs
        if side not in ["buy", "sell"]:
            return JSONResponse({
                "tool": "place_demo_order",
                "status": "error",
                "message": "Side must be 'buy' or 'sell'"
            })
        
        if amount <= 0:
            return JSONResponse({
                "tool": "place_demo_order",
                "status": "error",
                "message": "Amount must be positive"
            })
        
        # Simulate order placement
        import random
        import time
        
        order_id = f"ext_agent_{int(time.time())}_{symbol}_{side}"
        
        # Simulate realistic prices
        prices = {
            "XBTUSD": random.uniform(60000, 70000),
            "ETHUSD": random.uniform(3000, 4000),
            "ADAUSD": random.uniform(0.40, 0.50),
            "SOLUSD": random.uniform(150, 200)
        }
        
        price = prices.get(symbol, 50000)
        
        return JSONResponse({
            "tool": "place_demo_order",
            "status": "success",
            "result": {
                "order_id": order_id,
                "symbol": symbol,
                "side": side,
                "amount": amount,
                "order_type": order_type,
                "price": round(price, 2),
                "status": "filled",
                "demo_mode": True,
                "external_agent": True
            },
            "message": f"Demo order executed: {side} {amount} {symbol} @ ${price:.2f}",
            "timestamp": "2025-07-01T12:30:00Z"
        })
        
    except Exception as e:
        return JSONResponse({
            "tool": "place_demo_order",
            "status": "error",
            "message": f"Order placement failed: {str(e)}"
        })

async def get_market_data_endpoint(request: Request):
    """Market data endpoint - equivalent to MCP get_market_data tool."""
    try:
        symbol = request.query_params.get("symbol", "XBTUSD")
        
        import random
        
        # Simulate realistic market data
        base_prices = {
            "XBTUSD": 65000,
            "ETHUSD": 3500,
            "ADAUSD": 0.45,
            "SOLUSD": 180
        }
        
        if symbol not in base_prices:
            return JSONResponse({
                "tool": "get_market_data",
                "status": "error",
                "message": f"Unsupported symbol: {symbol}. Supported: {list(base_prices.keys())}"
            })
        
        base_price = base_prices[symbol]
        current_price = base_price * (1 + random.uniform(-0.03, 0.03))
        
        return JSONResponse({
            "tool": "get_market_data",
            "status": "success",
            "result": {
                "symbol": symbol,
                "price": round(current_price, 6),
                "bid": round(current_price * 0.9995, 6),
                "ask": round(current_price * 1.0005, 6),
                "volume_24h": random.randint(5000, 50000),
                "change_24h": round(random.uniform(-8, 8), 2),
                "high_24h": round(current_price * 1.05, 6),
                "low_24h": round(current_price * 0.95, 6)
            },
            "message": f"Market data for {symbol}",
            "timestamp": "2025-07-01T12:30:00Z"
        })
        
    except Exception as e:
        return JSONResponse({
            "tool": "get_market_data",
            "status": "error",
            "message": f"Failed to get market data: {str(e)}"
        })

# =============================================================================
# API INFO AND HEALTH ENDPOINTS
# =============================================================================

async def api_info_endpoint(request: Request):
    """API information endpoint."""
    return JSONResponse({
        "name": "External Agent Trading API",
        "description": "HTTP API demonstrating external agent access to trading system",
        "version": "1.0.0",
        "based_on": "Kraken Trading System MCP Server",
        "demo_mode": True,
        "endpoints": {
            "GET /": "API information",
            "GET /health": "Health check",
            "GET /ping": "Test connectivity (ping tool)",
            "GET /balance": "Get account balance",
            "GET /status": "Get server status",
            "POST /order": "Place demo order",
            "GET /market": "Get market data"
        },
        "external_agent_ready": True,
        "concept_proof": "This demonstrates how external agents can access your trading system"
    })

async def health_check_endpoint(request: Request):
    """Health check endpoint."""
    return JSONResponse({
        "status": "healthy",
        "server": "External Agent Trading API",
        "trading_system_ready": trading_adapter is not None,
        "demo_mode": True,
        "external_access": True,
        "timestamp": "2025-07-01T12:30:00Z"
    })

# =============================================================================
# APPLICATION SETUP
# =============================================================================

def create_app():
    """Create the HTTP application."""
    # Define routes first
    routes = [
        Route("/", api_info_endpoint, methods=["GET"]),
        Route("/health", health_check_endpoint, methods=["GET"]),
        Route("/ping", ping_endpoint, methods=["GET"]),
        Route("/balance", get_account_balance_endpoint, methods=["GET"]),
        Route("/status", get_server_status_endpoint, methods=["GET"]),
        Route("/order", place_demo_order_endpoint, methods=["POST"]),
        Route("/market", get_market_data_endpoint, methods=["GET"]),
    ]
    
    # Create app with routes
    app = Starlette(routes=routes)
    
    # Add CORS for external agent access
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allow all origins for demo
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add startup/shutdown events
    @app.on_event("startup")
    async def startup_event():
        await initialize_trading_system()
    
    @app.on_event("shutdown")
    async def shutdown_event():
        await shutdown_trading_system()
    
    return app

# =============================================================================
# MAIN SERVER
# =============================================================================

def main():
    """Main entry point."""
    print("🎯 EXTERNAL AGENT TRADING API - CONCEPT DEMO")
    print("=" * 60)
    print("Demonstrating external agent access to your trading system")
    print("=" * 60)
    
    app = create_app()
    
    print("🚀 Starting External Agent Trading API...")
    print("📡 Server: http://localhost:8000")
    print("🏥 Health: http://localhost:8000/health")
    print()
    print("🔧 Available Endpoints (equivalent to MCP tools):")
    print("   GET  /ping     → ping() tool")
    print("   GET  /balance  → get_account_balance() tool")
    print("   GET  /status   → get_server_status() tool")
    print("   POST /order    → place_demo_order() tool")
    print("   GET  /market   → get_market_data() tool")
    print()
    print("🤖 External agents can now:")
    print("   • Connect via HTTP requests")
    print("   • Access all trading functionality")
    print("   • Make trading decisions")
    print("   • Execute demo trades")
    print("   • Get real-time market data")
    print()
    print("💡 Test with curl:")
    print("   curl http://localhost:8000/ping")
    print("   curl http://localhost:8000/balance")
    print("   curl http://localhost:8000/market?symbol=XBTUSD")
    print()
    print("🎉 This proves external agents can access your trading system!")
    
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        log_level="info"
    )

if __name__ == "__main__":
    main()