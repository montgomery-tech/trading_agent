#!/usr/bin/env python3
"""
Enhanced MCP Trading Server with Database Integration

This server integrates your trading system with the balance tracking database,
providing real balance data to AI agents.

Usage: python3 enhanced_mcp_server.py --http
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

# Import database adapter
try:
    # For now, we'll create the adapter inline until the file structure is set up
    import sqlite3
    from decimal import Decimal

    class DatabaseBalanceAdapter:
        """Simplified database adapter for MCP integration."""

        def __init__(self, db_file: str = "balance_tracker.db"):
            self.db_file = Path(project_root) / db_file
            self.conn = None
            self.current_user = "agent_1"

        async def initialize(self):
            """Initialize database connection."""
            try:
                if not self.db_file.exists():
                    print(f"⚠️ Database file not found: {self.db_file}")
                    return False

                self.conn = sqlite3.connect(str(self.db_file))
                self.conn.row_factory = sqlite3.Row

                # Test connection
                cursor = self.conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM users")
                user_count = cursor.fetchone()[0]

                print(f"✅ Database connected: {user_count} users")
                return True

            except Exception as e:
                print(f"⚠️ Database connection failed: {e}")
                return False

        async def shutdown(self):
            """Close database connection."""
            if self.conn:
                self.conn.close()

        async def get_user_balances(self, username: str = None) -> Dict[str, Any]:
            """Get all balances for a user."""
            if username is None:
                username = self.current_user

            try:
                if not self.conn:
                    return {"error": "Database not connected"}

                # Get user ID
                cursor = self.conn.cursor()
                cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
                user_row = cursor.fetchone()

                if not user_row:
                    return {"error": f"User not found: {username}"}

                user_id = user_row["id"]

                # Get balances
                cursor.execute("""
                    SELECT ub.currency_code, ub.total_balance, ub.available_balance,
                           ub.locked_balance, c.name, c.symbol
                    FROM user_balances ub
                    JOIN currencies c ON ub.currency_code = c.code
                    WHERE ub.user_id = ? AND ub.total_balance > 0
                    ORDER BY c.is_fiat DESC, ub.total_balance DESC
                """, (user_id,))

                balances = {}
                for row in cursor.fetchall():
                    currency = row["currency_code"]
                    balances[currency] = {
                        "currency_name": row["name"],
                        "symbol": row["symbol"],
                        "total_balance": str(row["total_balance"]),
                        "available_balance": str(row["available_balance"]),
                        "locked_balance": str(row["locked_balance"])
                    }

                return {
                    "user": username,
                    "balances": balances,
                    "balance_count": len(balances),
                    "timestamp": datetime.now().isoformat()
                }

            except Exception as e:
                return {"error": str(e)}

        async def get_balance_for_currency(self, currency: str, username: str = None) -> Dict[str, Any]:
            """Get balance for specific currency."""
            if username is None:
                username = self.current_user

            try:
                if not self.conn:
                    return {"error": "Database not connected"}

                # Get user ID
                cursor = self.conn.cursor()
                cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
                user_row = cursor.fetchone()

                if not user_row:
                    return {"error": f"User not found: {username}"}

                user_id = user_row["id"]

                # Get specific currency balance
                cursor.execute("""
                    SELECT ub.currency_code, ub.total_balance, ub.available_balance,
                           ub.locked_balance, c.name, c.symbol
                    FROM user_balances ub
                    JOIN currencies c ON ub.currency_code = c.code
                    WHERE ub.user_id = ? AND ub.currency_code = ?
                """, (user_id, currency.upper()))

                row = cursor.fetchone()
                if row:
                    return {
                        "user": username,
                        "currency": row["currency_code"],
                        "currency_name": row["name"],
                        "symbol": row["symbol"],
                        "total_balance": str(row["total_balance"]),
                        "available_balance": str(row["available_balance"]),
                        "locked_balance": str(row["locked_balance"])
                    }
                else:
                    return {
                        "user": username,
                        "currency": currency.upper(),
                        "total_balance": "0.00",
                        "available_balance": "0.00",
                        "locked_balance": "0.00",
                        "message": "No balance found"
                    }

            except Exception as e:
                return {"error": str(e)}

    print("✅ Database adapter created")

except Exception as e:
    print(f"⚠️ Database adapter creation failed: {e}")
    DatabaseBalanceAdapter = None

# =============================================================================
# GLOBAL STATE
# =============================================================================

# Global components
trading_adapter = None
database_adapter = None
server_config = None

# Create the enhanced MCP server
mcp = FastMCP("Enhanced Trading Server with Database")

# =============================================================================
# STARTUP/SHUTDOWN MANAGEMENT
# =============================================================================

async def initialize_enhanced_server():
    """Initialize the enhanced server with database integration."""
    global trading_adapter, database_adapter, server_config

    print("🚀 Initializing enhanced MCP trading server...")
    print("🗄️ Database integration enabled")
    print("📁 Local file access enabled")
    print("🔗 HTTP transport for external agents")

    # Initialize database adapter
    database_success = False
    if DatabaseBalanceAdapter:
        try:
            print("📊 Connecting to database...")
            database_adapter = DatabaseBalanceAdapter()
            database_success = await database_adapter.initialize()
            if database_success:
                print("✅ Database adapter initialized successfully")
            else:
                print("⚠️ Database adapter initialization failed - continuing without database")
                database_adapter = None
        except Exception as e:
            print(f"⚠️ Database adapter error: {e}")
            database_adapter = None

    # Initialize trading system
    trading_success = False
    if MCPServerConfig and TradingSystemAdapter:
        try:
            print("🏦 Initializing trading system...")
            server_config = MCPServerConfig()
            trading_adapter = TradingSystemAdapter(server_config)
            await trading_adapter.initialize()
            trading_success = True
            print("✅ Trading system initialized successfully")
        except Exception as e:
            print(f"⚠️ Trading system initialization failed: {e}")
            print("🎭 Continuing in mock mode...")
            trading_adapter = None
    else:
        print("🎭 Running in mock mode (trading system not available)")

    # Print status summary
    print(f"\n📊 INITIALIZATION SUMMARY:")
    print(f"   Database: {'✅ Connected' if database_success else '❌ Not available'}")
    print(f"   Trading System: {'✅ Connected' if trading_success else '❌ Mock mode'}")
    print(f"   File Access: ✅ Enabled")
    print(f"   HTTP Transport: ✅ Enabled")

    print("✅ Enhanced MCP server ready!")
    return True

async def shutdown_enhanced_server():
    """Shutdown the enhanced server."""
    global trading_adapter, database_adapter

    print("🔄 Shutting down enhanced server...")

    if trading_adapter:
        await trading_adapter.shutdown()

    if database_adapter:
        await database_adapter.shutdown()

    print("✅ Shutdown complete!")

# =============================================================================
# ENHANCED BALANCE TOOLS WITH DATABASE INTEGRATION
# =============================================================================

@mcp.tool()
def ping() -> str:
    """Test connectivity to the enhanced trading server."""
    return "🏓 Pong! Enhanced MCP trading server with database integration responding."

@mcp.tool()
async def get_account_balance() -> str:
    """Get current account balance from database."""
    global database_adapter, trading_adapter

    # Try database first
    if database_adapter:
        try:
            balance_data = await database_adapter.get_user_balances()
            if "balances" in balance_data and balance_data["balances"]:
                result = f"💰 Database Account Balance for {balance_data['user']}:\n\n"

                for currency, details in balance_data["balances"].items():
                    result += f"💱 {currency} ({details['currency_name']}):\n"
                    result += f"   Total: {details['total_balance']} {details['symbol']}\n"
                    result += f"   Available: {details['available_balance']} {details['symbol']}\n"
                    result += f"   Locked: {details['locked_balance']} {details['symbol']}\n\n"

                result += f"🕒 Last updated: {balance_data['timestamp']}\n"
                result += f"📊 Total currencies: {balance_data['balance_count']}"

                return result
            else:
                return f"⚠️ No balances found in database for user agent_1"
        except Exception as e:
            print(f"Database balance error: {e}")

    # Fallback to trading adapter
    if trading_adapter:
        try:
            balance = await trading_adapter.get_account_balance()
            return f"💰 Trading System Balance:\n{json.dumps(balance, indent=2)}"
        except Exception as e:
            return f"❌ Error getting balance: {str(e)}"

    # Final fallback to mock data
    mock_balance = {
        "USD": {"balance": "10000.00", "available": "8500.00"},
        "ETH": {"balance": "5.0", "available": "5.0"}
    }
    return f"💰 Mock Account Balance:\n{json.dumps(mock_balance, indent=2)}"

@mcp.tool()
async def get_balance_for_currency(currency: str) -> str:
    """Get balance for a specific currency from database."""
    global database_adapter

    if database_adapter:
        try:
            balance_data = await database_adapter.get_balance_for_currency(currency)

            if "error" not in balance_data:
                result = f"💱 {balance_data['currency']} Balance for {balance_data['user']}:\n\n"
                if "currency_name" in balance_data:
                    result += f"Currency: {balance_data['currency_name']} ({balance_data.get('symbol', currency)})\n"
                result += f"Total: {balance_data['total_balance']}\n"
                result += f"Available: {balance_data['available_balance']}\n"
                result += f"Locked: {balance_data['locked_balance']}\n"

                if balance_data.get('message'):
                    result += f"\n💡 {balance_data['message']}"

                return result
            else:
                return f"❌ Database error: {balance_data['error']}"
        except Exception as e:
            return {"error": str(e)}
    
