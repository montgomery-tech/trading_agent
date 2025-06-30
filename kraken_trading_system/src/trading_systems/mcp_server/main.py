#!/usr/bin/env python3
"""
Kraken Trading System MCP Server - Main Entry Point

This module provides the main entry point for the Kraken Trading System MCP server,
using the FastMCP framework for rapid development and protocol compliance.

File Location: src/trading_systems/mcp_server/main.py
"""

import asyncio
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator, Dict, Any
from dataclasses import dataclass

# Add src to path for standalone execution
if __name__ == "__main__":
    src_path = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(src_path))

try:
    from mcp.server.fastmcp import FastMCP
    from mcp.server.session import ServerSession
    from mcp.types import TextContent, ImageContent, EmbeddedResource
except ImportError as e:
    print(f"❌ MCP SDK not installed. Please run: pip install 'mcp[cli]'")
    print(f"Error: {e}")
    sys.exit(1)

# Import trading system components
from trading_systems.config.settings import settings
from trading_systems.utils.logger import get_logger, setup_logging
from trading_systems.mcp_server.trading_adapter import TradingSystemAdapter
from trading_systems.mcp_server.config import MCPServerConfig


@dataclass
class MCPServerContext:
    """Context for MCP server lifecycle management."""
    trading_adapter: TradingSystemAdapter
    config: MCPServerConfig


# Initialize logging
setup_logging()
logger = get_logger(__name__)

# Create FastMCP server instance
mcp = FastMCP("Kraken Trading System")


@asynccontextmanager
async def server_lifespan(server: FastMCP) -> AsyncIterator[MCPServerContext]:
    """
    Manage MCP server startup and shutdown lifecycle with trading system integration.
    
    This function:
    1. Initializes the trading system adapter
    2. Sets up connections to WebSocket client and OrderManager
    3. Provides cleanup on shutdown
    """
    logger.info("🚀 Starting Kraken Trading System MCP Server")
    
    try:
        # Initialize MCP server configuration
        config = MCPServerConfig()
        logger.info("✅ MCP server configuration loaded")
        
        # Initialize trading system adapter
        trading_adapter = TradingSystemAdapter(config)
        await trading_adapter.initialize()
        logger.info("✅ Trading system adapter initialized")
        
        # Yield context to the server
        context = MCPServerContext(
            trading_adapter=trading_adapter,
            config=config
        )
        
        logger.info("🎯 MCP Server ready to accept connections")
        yield context
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize MCP server: {e}")
        raise
    finally:
        # Cleanup on shutdown
        logger.info("🔄 Shutting down MCP server...")
        if 'trading_adapter' in locals():
            await trading_adapter.shutdown()
        logger.info("✅ MCP server shutdown complete")


# Set lifespan for the server
mcp = FastMCP("Kraken Trading System", lifespan=server_lifespan)


# =============================================================================
# BASIC HEALTH CHECK TOOLS
# =============================================================================

@mcp.tool()
def get_server_status() -> str:
    """Get the current status of the MCP server and trading system."""
    try:
        ctx = mcp.get_context()
        adapter = ctx.request_context.lifespan_context["trading_adapter"]
        
        status = {
            "server_status": "online",
            "trading_system": adapter.get_status(),
            "timestamp": asyncio.get_event_loop().time()
        }
        
        return f"✅ Server Status: {status}"
        
    except Exception as e:
        logger.error(f"Error getting server status: {e}")
        return f"❌ Server Status Check Failed: {str(e)}"


@mcp.tool()
def ping() -> str:
    """Simple ping tool to test MCP server connectivity."""
    return "🏓 Pong! MCP server is responding."


# =============================================================================
# BASIC TRADING INFORMATION TOOLS
# =============================================================================

@mcp.tool()
async def get_account_balance() -> str:
    """Get current account balance information."""
    try:
        ctx = mcp.get_context()
        adapter = ctx.request_context.lifespan_context["trading_adapter"]
        
        balance_info = await adapter.get_account_balance()
        return f"💰 Account Balance: {balance_info}"
        
    except Exception as e:
        logger.error(f"Error getting account balance: {e}")
        return f"❌ Failed to get account balance: {str(e)}"


# =============================================================================
# BASIC MARKET DATA RESOURCES
# =============================================================================

@mcp.resource("market://status", title="Market Status")
def get_market_status() -> str:
    """Get current market status and system information."""
    try:
        ctx = mcp.get_context()
        adapter = ctx.request_context.lifespan_context["trading_adapter"]
        
        market_status = adapter.get_market_status()
        return f"📊 Market Status: {market_status}"
        
    except Exception as e:
        logger.error(f"Error getting market status: {e}")
        return f"❌ Market status unavailable: {str(e)}"


# =============================================================================
# ENTRY POINT
# =============================================================================

def main():
    """Main entry point for the MCP server."""
    try:
        logger.info("🚀 Starting Kraken Trading System MCP Server")
        
        # Run the FastMCP server
        # The server will use stdio transport by default for Claude Desktop integration
        mcp.run()
        
    except KeyboardInterrupt:
        logger.info("⚠️ Server interrupted by user")
    except Exception as e:
        logger.error(f"❌ Server failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()