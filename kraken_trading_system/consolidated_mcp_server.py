#!/usr/bin/env python3
"""
Fixed Consolidated MCP Trading Server with Local File Access

Clean version without syntax errors.

Usage: python3 fixed_consolidated_mcp_server.py
"""

import asyncio
import sys
import json
import os
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

# Add your trading system to path
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

# Import dependencies
try:
    from mcp.server.fastmcp import FastMCP
    import uvicorn
    from starlette.applications import Starlette
    from starlette.routing import Route, Mount
    from starlette.responses import JSONResponse
    from starlette.middleware.cors import CORSMiddleware
    print("✅ MCP and HTTP dependencies imported successfully")
except ImportError as e:
    print(f"❌ Missing required packages: {e}")
    print("Install with: pip install mcp uvicorn starlette")
    sys.exit(1)

# Import your trading components
try:
    from trading_systems.mcp_server.config import MCPServerConfig
    from trading_systems.mcp_server.trading_adapter import TradingSystemAdapter
    print("✅ Trading system components imported successfully")
except ImportError as e:
    print(f"⚠️ Trading system import failed: {e}")
    print("🎭 Continuing in standalone mode with mock data...")
    MCPServerConfig = None
    TradingSystemAdapter = None

# =============================================================================
# GLOBAL STATE
# =============================================================================

# Global trading adapter
trading_adapter = None
server_config = None

# Create the consolidated MCP server
mcp = FastMCP("Fixed Trading Server with File Access")

# =============================================================================
# STARTUP/SHUTDOWN MANAGEMENT
# =============================================================================

async def initialize_trading_system():
    """Initialize the trading system."""
    global trading_adapter, server_config

    print("🚀 Initializing fixed MCP trading server...")
    print("📁 Local file access enabled")
    print("🔗 HTTP transport for external agents")

    if MCPServerConfig and TradingSystemAdapter:
        try:
            server_config = MCPServerConfig()
            trading_adapter = TradingSystemAdapter(server_config)
            await trading_adapter.initialize()
            print("✅ Trading system initialized successfully")
        except Exception as e:
            print(f"⚠️ Trading system initialization failed: {e}")
            print("🎭 Continuing in mock mode...")
    else:
        print("🎭 Running in mock mode (trading system not available)")

    print("✅ Fixed MCP server ready!")

async def shutdown_trading_system():
    """Shutdown the trading system."""
    global trading_adapter

    print("🔄 Shutting down trading system...")

    if trading_adapter:
        await trading_adapter.shutdown()

    print("✅ Shutdown complete!")

# =============================================================================
# BASIC TOOLS
# =============================================================================

@mcp.tool()
def ping() -> str:
    """Test connectivity to the trading server."""
    return "🏓 Pong! Fixed MCP trading server responding."

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
    global trading_adapter

    status = {
        "server_name": "Fixed MCP Trading Server",
        "timestamp": datetime.now().isoformat(),
        "features": {
            "file_access": True,
            "trading_system": trading_adapter is not None,
            "http_transport": True,
            "demo_mode": True
        },
        "project_root": str(project_root),
        "available_tools": ["ping", "get_account_balance", "get_server_status",
                          "read_file", "list_directory", "find_files",
                          "buy_eth", "sell_eth", "get_eth_price", "get_order_status"]
    }

    if trading_adapter:
        try:
            trading_status = trading_adapter.get_status()
            status["trading_system_status"] = str(trading_status)
        except Exception as e:
            status["trading_system_error"] = str(e)

    return f"✅ Server Status:\n{json.dumps(status, indent=2)}"

# =============================================================================
# FILE ACCESS TOOLS
# =============================================================================

@mcp.tool()
def read_file(file_path: str) -> str:
    """Read contents of a file from the local repository."""
    try:
        # Convert to Path and resolve relative to project root
        path = Path(file_path)
        if not path.is_absolute():
            path = project_root / path

        # Security check - ensure path is within project
        try:
            path.resolve().relative_to(project_root.resolve())
        except ValueError:
            return f"❌ Error: Access denied - path outside project directory: {file_path}"

        # Check if file exists
        if not path.exists():
            return f"❌ Error: File not found: {file_path}"

        # Check if it's actually a file
        if not path.is_file():
            return f"❌ Error: Path is not a file: {file_path}"

        # Read file contents
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        return f"📄 File: {file_path}\n\n{content}"

    except Exception as e:
        return f"❌ Error reading file {file_path}: {str(e)}"

@mcp.tool()
def list_directory(dir_path: str = ".") -> str:
    """List contents of a directory in the local repository."""
    try:
        # Convert to Path and resolve relative to project root
        path = Path(dir_path)
        if not path.is_absolute():
            path = project_root / path

        # Security check - ensure path is within project
        try:
            path.resolve().relative_to(project_root.resolve())
        except ValueError:
            return f"❌ Error: Access denied - path outside project directory: {dir_path}"

        # Check if directory exists
        if not path.exists():
            return f"❌ Error: Directory not found: {dir_path}"

        if not path.is_dir():
            return f"❌ Error: Path is not a directory: {dir_path}"

        # List directory contents
        items = []
        for item in sorted(path.iterdir()):
            if item.is_file():
                size = item.stat().st_size
                items.append(f"📄 {item.name} ({size} bytes)")
            elif item.is_dir():
                items.append(f"📁 {item.name}/")
            else:
                items.append(f"❓ {item.name}")

        if not items:
            return f"📁 Directory: {dir_path}\n(empty directory)"

        return f"📁 Directory: {dir_path}\n\n" + "\n".join(items)

    except Exception as e:
        return f"❌ Error listing directory {dir_path}: {str(e)}"

@mcp.tool()
def find_files(pattern: str, directory: str = ".") -> str:
    """Find files matching a pattern in the repository."""
    try:
        # Convert to Path and resolve relative to project root
        search_path = Path(directory)
        if not search_path.is_absolute():
            search_path = project_root / search_path

        # Security check - ensure path is within project
        try:
            search_path.resolve().relative_to(project_root.resolve())
        except ValueError:
            return f"❌ Error: Access denied - path outside project directory: {directory}"

        # Check if directory exists
        if not search_path.exists():
            return f"❌ Error: Directory not found: {directory}"

        # Search for files
        matches = []
        if search_path.is_dir():
            for match in search_path.rglob(pattern):
                # Get relative path from project root
                try:
                    rel_path = match.relative_to(project_root)
                    if match.is_file():
                        size = match.stat().st_size
                        matches.append(f"📄 {rel_path} ({size} bytes)")
                    elif match.is_dir():
                        matches.append(f"📁 {rel_path}/")
                except ValueError:
                    # Skip files outside project root
                    continue

        if not matches:
            return f"🔍 No files found matching pattern '{pattern}' in {directory}"

        matches.sort()
        return f"🔍 Files matching '{pattern}' in {directory}:\n\n" + "\n".join(matches)

    except Exception as e:
        return f"❌ Error searching for pattern {pattern}: {str(e)}"

# =============================================================================
# TRADING EXECUTION TOOLS
# =============================================================================

@mcp.tool()
async def buy_eth(amount_usd: float, order_type: str = "market") -> str:
    """Buy ETH with USD."""
    global trading_adapter

    try:
        if not trading_adapter:
            return "❌ Trading system not available"

        # Safety limit - max $100 per order
        if amount_usd > 100:
            return f"❌ Safety limit: Maximum $100 per order (requested: ${amount_usd})"

        if amount_usd <= 0:
            return f"❌ Invalid amount: ${amount_usd}"

        # Get current ETH price to calculate volume
        eth_price = 2500.0  # Mock price - replace with real price lookup
        eth_volume = amount_usd / eth_price

        result = f"🔄 Processing BUY order:\n"
        result += f"   💰 Amount: ${amount_usd:.2f}\n"
        result += f"   📈 ETH Volume: {eth_volume:.6f} ETH\n"
        result += f"   📊 Price: ~${eth_price:.2f}\n"
        result += f"   🎯 Order Type: {order_type.upper()}\n\n"

        if order_type.lower() == "market":
            result += "🎭 DEMO MODE: Order simulated (no real execution)\n"
            result += f"✅ Market BUY order would be placed for {eth_volume:.6f} ETH\n"
            result += f"💡 Real implementation: trading_adapter.websocket_client.place_market_order()"
        else:
            result += f"💡 Limit orders not yet implemented in MCP interface"

        return result

    except Exception as e:
        return f"❌ Error processing buy order: {str(e)}"

@mcp.tool()
async def sell_eth(amount_eth: float, order_type: str = "market") -> str:
    """Sell ETH for USD."""
    global trading_adapter

    try:
        if not trading_adapter:
            return "❌ Trading system not available"

        # Safety limit - max 0.1 ETH per order
        if amount_eth > 0.1:
            return f"❌ Safety limit: Maximum 0.1 ETH per order (requested: {amount_eth})"

        if amount_eth <= 0:
            return f"❌ Invalid amount: {amount_eth} ETH"

        # Get current ETH price
        eth_price = 2500.0  # Mock price - replace with real price lookup
        usd_value = amount_eth * eth_price

        result = f"🔄 Processing SELL order:\n"
        result += f"   📉 ETH Amount: {amount_eth:.6f} ETH\n"
        result += f"   💰 USD Value: ~${usd_value:.2f}\n"
        result += f"   📊 Price: ~${eth_price:.2f}\n"
        result += f"   🎯 Order Type: {order_type.upper()}\n\n"

        if order_type.lower() == "market":
            result += "🎭 DEMO MODE: Order simulated (no real execution)\n"
            result += f"✅ Market SELL order would be placed for {amount_eth:.6f} ETH\n"
            result += f"💡 Real implementation: trading_adapter.websocket_client.place_market_order()"
        else:
            result += f"💡 Limit orders not yet implemented in MCP interface"

        return result

    except Exception as e:
        return f"❌ Error processing sell order: {str(e)}"

@mcp.tool()
async def get_eth_price() -> str:
    """Get current ETH/USD price and market data."""
    try:
        # Mock data for now
        mock_data = {
            "symbol": "ETH/USD",
            "last_price": 2487.50,
            "bid": 2487.25,
            "ask": 2487.75,
            "high_24h": 2520.00,
            "low_24h": 2450.00,
            "volume_24h": "125,432.50",
            "change_24h": "+1.25%"
        }

        result = f"📊 ETH/USD Market Data:\n\n"
        result += f"💰 Last Price: ${mock_data['last_price']:.2f}\n"
        result += f"📈 Bid: ${mock_data['bid']:.2f}\n"
        result += f"📉 Ask: ${mock_data['ask']:.2f}\n"
        result += f"⬆️ 24h High: ${mock_data['high_24h']:.2f}\n"
        result += f"⬇️ 24h Low: ${mock_data['low_24h']:.2f}\n"
        result += f"📊 24h Volume: {mock_data['volume_24h']} ETH\n"
        result += f"📈 24h Change: {mock_data['change_24h']}\n\n"
        result += f"🎭 DEMO MODE: Using mock market data\n"
        result += f"💡 Real implementation: trading_adapter.websocket_client.get_ticker()"

        return result

    except Exception as e:
        return f"❌ Error getting ETH price: {str(e)}"

@mcp.tool()
async def get_order_status(order_id: str = "") -> str:
    """Get status of orders."""
    try:
        if order_id:
            # Check specific order
            result = f"🔍 Order Status Check:\n"
            result += f"   Order ID: {order_id}\n\n"
            result += f"🎭 DEMO MODE: Simulated order status\n"
            result += f"   Status: FILLED\n"
            result += f"   Type: MARKET BUY\n"
            result += f"   Symbol: ETH/USD\n"
            result += f"   Amount: 0.004 ETH\n"
            result += f"   Price: $2,487.50\n"
            result += f"   Total: $9.95\n"
            result += f"   Fee: $0.05\n"
        else:
            # Show recent orders
            result = f"📋 Recent Orders:\n\n"
            result += f"🎭 DEMO MODE: Mock order history\n"
            result += f"1️⃣ Order #KRK-12345:\n"
            result += f"   Status: FILLED | BUY 0.004 ETH @ $2,487.50\n"
            result += f"2️⃣ Order #KRK-12344:\n"
            result += f"   Status: FILLED | SELL 0.003 ETH @ $2,475.00\n"

        return result

    except Exception as e:
        return f"❌ Error getting order status: {str(e)}"

@mcp.tool()
async def execute_trading_prompt(prompt: str) -> str:
    """Execute a natural language trading command."""
    try:
        prompt_lower = prompt.lower().strip()

        # Command recognition and routing
        if "balance" in prompt_lower or "account" in prompt_lower:
            return await get_account_balance()

        elif "price" in prompt_lower and "eth" in prompt_lower:
            return await get_eth_price()

        elif "buy" in prompt_lower and "eth" in prompt_lower:
            # Extract USD amount using simple regex
            usd_match = re.search(r'\$(\d+(?:\.\d+)?)', prompt_lower)
            if not usd_match:
                usd_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:dollars?|usd)', prompt_lower)

            if usd_match:
                amount_usd = float(usd_match.group(1))
                return await buy_eth(amount_usd)
            else:
                return "❓ Could not parse USD amount. Try: 'buy $10 worth of ETH'"

        elif "sell" in prompt_lower and "eth" in prompt_lower:
            # Extract ETH amount using simple regex
            eth_match = re.search(r'(\d+(?:\.\d+)?)\s*eth', prompt_lower)

            if eth_match:
                amount_eth = float(eth_match.group(1))
                return await sell_eth(amount_eth)
            else:
                return "❓ Could not parse ETH amount. Try: 'sell 0.01 ETH'"

        elif "order" in prompt_lower:
            return await get_order_status()

        else:
            return "❓ Command not understood. Try: 'buy $10 ETH', 'sell 0.01 ETH', 'check price', 'show balance'"

    except Exception as e:
        return f"❌ Error processing prompt: {str(e)}"

# =============================================================================
# RESOURCES
# =============================================================================

@mcp.resource("market://status")
def market_status() -> str:
    """Current market status resource."""
    return json.dumps({
        "status": "demo_mode",
        "timestamp": datetime.now().isoformat(),
        "message": "Market data integration available"
    })

@mcp.resource("files://project")
def project_structure() -> str:
    """Project structure resource."""
    try:
        structure = []
        for root, dirs, files in os.walk(project_root):
            # Skip hidden directories and common build directories
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'node_modules']]

            level = root.replace(str(project_root), '').count(os.sep)
            indent = '  ' * level
            structure.append(f"{indent}{os.path.basename(root)}/")

            subindent = '  ' * (level + 1)
            for file in files:
                if not file.startswith('.') and not file.endswith('.pyc'):
                    structure.append(f"{subindent}{file}")

        return "📁 Project Structure:\n\n" + "\n".join(structure[:50])  # Limit output
    except Exception as e:
        return f"❌ Error reading project structure: {str(e)}"

# =============================================================================
# MAIN EXECUTION
# =============================================================================

async def main_async():
    """Async main entry point."""
    print("🎯 FIXED CONSOLIDATED MCP TRADING SERVER")
    print("=" * 60)
    print("Features:")
    print("  📁 Local file access for strategies and configs")
    print("  🏦 Trading system integration")
    print("  🔗 HTTP transport for external agents")
    print("  🎭 Demo mode with mock data")
    print("=" * 60)

    # Initialize trading system first
    await initialize_trading_system()

    # Health check endpoint
    async def health_check(request):
        return JSONResponse({
            "status": "healthy",
            "server": "Fixed Consolidated MCP Trading Server",
            "features": ["file_access", "trading", "http_transport"],
            "timestamp": datetime.now().isoformat()
        })

    # Run with both stdio and HTTP support
    if len(sys.argv) > 1 and sys.argv[1] == "--http":
        print("🌐 Starting HTTP server mode...")

        # Create routes
        routes = [
            Route("/health", health_check, methods=["GET"]),
            Route("/", health_check, methods=["GET"])
        ]

        # Mount MCP SSE endpoint
        try:
            sse_app = mcp.sse_app()
            routes.append(Mount("/sse", app=sse_app))
            print("📡 MCP SSE endpoint: http://localhost:8000/sse")
        except Exception as e:
            print(f"⚠️ SSE mounting failed: {e}")

        # Create app with routes
        app = Starlette(routes=routes)

        # Add CORS middleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        print("🚀 Server starting on http://localhost:8000")

        # Use uvicorn server directly in async context
        import uvicorn
        config = uvicorn.Config(app, host="127.0.0.1", port=8000, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()
    else:
        print("📱 Starting stdio mode...")
        print("💡 Use --http flag for HTTP server mode")
        await mcp.run_stdio_async()

def main():
    """Main entry point."""
    asyncio.run(main_async())

if __name__ == "__main__":
    main()
