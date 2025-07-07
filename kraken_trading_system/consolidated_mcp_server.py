#!/usr/bin/env python3
"""
Agent-Focused Trading Server for agent_1

This server provides trading-focused tools specifically designed for AI agents.
The local agent connects as 'agent_1' and can check balances, get prices, and execute trades.

Usage: python3 agent_focused_trading_server.py [--http]
"""

# =============================================================================
# IMPORTS
# =============================================================================

import asyncio
import json
import os
import re
import sqlite3
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

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

# Import your trading components (optional)
try:
    from trading_systems.mcp_server.config import MCPServerConfig
    from trading_systems.mcp_server.trading_adapter import TradingSystemAdapter
    print("✅ Trading system components imported successfully")
except ImportError as e:
    print(f"⚠️ Trading system import failed: {e}")
    print("🎭 Continuing in standalone mode...")
    MCPServerConfig = None
    TradingSystemAdapter = None

# =============================================================================
# CONSTANTS
# =============================================================================

AGENT_USERNAME = "agent_1"
DB_FILE = "balance_tracker.db"

# =============================================================================
# DATABASE MANAGER CLASS
# =============================================================================

class DatabaseManager:
    """Manages SQLite database connections and operations."""

    def __init__(self, db_file: str = DB_FILE):
        self.db_file = db_file
        self.connection = None

    def connect(self) -> bool:
        """Connect to the database."""
        try:
            if not Path(self.db_file).exists():
                print(f"⚠️ Database file '{self.db_file}' not found!")
                print("📝 Creating new database with schema...")
                self._create_database_schema()

            self.connection = sqlite3.connect(self.db_file, check_same_thread=False)
            self.connection.row_factory = sqlite3.Row
            self.connection.execute("PRAGMA foreign_keys = ON")
            print(f"✅ Connected to database: {self.db_file}")
            return True
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            return False

    def disconnect(self):
        """Disconnect from database."""
        if self.connection:
            self.connection.close()
            self.connection = None
            print("✅ Database disconnected")

    def execute_query(self, query: str, params: tuple = ()) -> List[Dict]:
        """Execute a SELECT query and return results."""
        if not self.connection:
            raise ConnectionError("Database not connected")

        try:
            cursor = self.connection.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            raise Exception(f"Query execution failed: {e}")

    def execute_update(self, query: str, params: tuple = ()) -> int:
        """Execute an INSERT/UPDATE/DELETE query and return affected rows."""
        if not self.connection:
            raise ConnectionError("Database not connected")

        try:
            cursor = self.connection.cursor()
            cursor.execute(query, params)
            self.connection.commit()
            return cursor.rowcount
        except Exception as e:
            self.connection.rollback()
            raise Exception(f"Update execution failed: {e}")

    def _create_database_schema(self):
        """Create the database schema if it doesn't exist (without inserting mock data)."""
        schema_sql = """
-- SQLite version of the User Balance Tracking System Schema
PRAGMA foreign_keys = ON;

-- Users Table
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    is_active BOOLEAN DEFAULT 1,
    is_verified BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    CHECK (LENGTH(username) >= 3)
);

-- Currencies Table
CREATE TABLE IF NOT EXISTS currencies (
    code VARCHAR(10) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    symbol VARCHAR(10),
    decimal_places INTEGER DEFAULT 8,
    is_active BOOLEAN DEFAULT 1,
    is_fiat BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CHECK (decimal_places >= 0 AND decimal_places <= 18)
);

-- User Balances Table
CREATE TABLE IF NOT EXISTS user_balances (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    currency_code VARCHAR(10) NOT NULL REFERENCES currencies(code),
    total_balance DECIMAL(28, 18) DEFAULT 0 NOT NULL,
    available_balance DECIMAL(28, 18) DEFAULT 0 NOT NULL,
    locked_balance DECIMAL(28, 18) DEFAULT 0 NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, currency_code),
    CHECK (total_balance >= 0),
    CHECK (available_balance >= 0),
    CHECK (locked_balance >= 0),
    CHECK (total_balance = available_balance + locked_balance)
);

-- Transactions Table
CREATE TABLE IF NOT EXISTS transactions (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    user_id TEXT NOT NULL REFERENCES users(id),
    external_id VARCHAR(255),
    transaction_type VARCHAR(20) NOT NULL CHECK (transaction_type IN ('deposit', 'withdrawal', 'trade_buy', 'trade_sell', 'transfer_in', 'transfer_out', 'fee', 'adjustment')),
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'cancelled', 'rejected')),
    amount DECIMAL(28, 18) NOT NULL,
    currency_code VARCHAR(10) NOT NULL REFERENCES currencies(code),
    fee_amount DECIMAL(28, 18) DEFAULT 0,
    fee_currency_code VARCHAR(10) REFERENCES currencies(code),
    balance_before DECIMAL(28, 18),
    balance_after DECIMAL(28, 18),
    description TEXT,
    metadata TEXT,
    related_transaction_id TEXT REFERENCES transactions(id),
    external_reference VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP,
    CHECK (amount > 0),
    CHECK (fee_amount >= 0)
);

-- Trading Pairs Table
CREATE TABLE IF NOT EXISTS trading_pairs (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    base_currency VARCHAR(10) NOT NULL REFERENCES currencies(code),
    quote_currency VARCHAR(10) NOT NULL REFERENCES currencies(code),
    symbol VARCHAR(20) NOT NULL UNIQUE,
    min_trade_amount DECIMAL(28, 18) DEFAULT 0,
    max_trade_amount DECIMAL(28, 18),
    price_precision INTEGER DEFAULT 8,
    amount_precision INTEGER DEFAULT 8,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CHECK (base_currency != quote_currency),
    CHECK (min_trade_amount >= 0)
);

-- Trades Table
CREATE TABLE IF NOT EXISTS trades (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    user_id TEXT NOT NULL REFERENCES users(id),
    trading_pair_id TEXT NOT NULL REFERENCES trading_pairs(id),
    side VARCHAR(4) NOT NULL CHECK (side IN ('buy', 'sell')),
    amount DECIMAL(28, 18) NOT NULL,
    price DECIMAL(28, 18) NOT NULL,
    total_value DECIMAL(28, 18) NOT NULL,
    fee_amount DECIMAL(28, 18) DEFAULT 0,
    fee_currency_code VARCHAR(10) REFERENCES currencies(code),
    status VARCHAR(20) DEFAULT 'pending',
    executed_at TIMESTAMP,
    base_transaction_id TEXT REFERENCES transactions(id),
    quote_transaction_id TEXT REFERENCES transactions(id),
    fee_transaction_id TEXT REFERENCES transactions(id),
    external_trade_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CHECK (amount > 0),
    CHECK (price > 0)
);

-- Only insert currencies if they don't exist (no default user data)
INSERT OR IGNORE INTO currencies (code, name, symbol, decimal_places, is_active, is_fiat) VALUES
('USD', 'US Dollar', '$', 2, 1, 1),
('EUR', 'Euro', '€', 2, 1, 1),
('BTC', 'Bitcoin', '₿', 8, 1, 0),
('ETH', 'Ethereum', 'Ξ', 8, 1, 0),
('XBT', 'Bitcoin (Kraken)', 'XBT', 8, 1, 0),
('SOL', 'Solana', 'SOL', 8, 1, 0),
('ADA', 'Cardano', '₳', 8, 1, 0);

-- Only insert trading pairs if they don't exist
INSERT OR IGNORE INTO trading_pairs (base_currency, quote_currency, symbol, min_trade_amount, is_active) VALUES
('BTC', 'USD', 'BTCUSD', 0.0001, 1),
('ETH', 'USD', 'ETHUSD', 0.001, 1),
('XBT', 'USD', 'XBTUSD', 0.0001, 1),
('SOL', 'USD', 'SOLUSD', 0.01, 1),
('ADA', 'USD', 'ADAUSD', 1.0, 1),
('ETH', 'BTC', 'ETHBTC', 0.001, 1);
"""

        # Create database with schema (no mock user data)
        conn = sqlite3.connect(self.db_file)
        conn.executescript(schema_sql)
        conn.close()
        print("✅ Database schema created successfully (no mock data)")

# =============================================================================
# GLOBAL STATE
# =============================================================================

# Global instances
trading_adapter = None
server_config = None
db_manager = None
agent_user_id = None

# Create the MCP server instance
mcp = FastMCP("Agent-Focused Trading Server for agent_1")

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_market_price_data(symbol: str) -> Optional[Dict[str, Any]]:
    """Get real market price data for a trading symbol."""
    global trading_adapter

    try:
        # If we have a real trading adapter, use it
        if trading_adapter:
            # This would connect to your real trading system
            # trading_adapter.get_ticker(symbol)
            pass

        # For now, return None to indicate no real price data available
        # This forces the system to handle the "no price data" case properly
        return None

    except Exception as e:
        print(f"⚠️ Error getting real market data for {symbol}: {e}")
        return None

async def setup_agent_1() -> bool:
    """Find existing agent_1 user in the database."""
    global agent_user_id

    try:
        # Find existing agent_1
        query = "SELECT id, username FROM users WHERE username = ?"
        rows = db_manager.execute_query(query, (AGENT_USERNAME,))

        if rows:
            agent_user_id = rows[0]['id']
            print(f"✅ Found existing agent_1 with ID: {agent_user_id}")

            # Verify balances exist for this user
            balance_check_query = "SELECT COUNT(*) as count FROM user_balances WHERE user_id = ?"
            balance_rows = db_manager.execute_query(balance_check_query, (agent_user_id,))
            balance_count = balance_rows[0]['count'] if balance_rows else 0
            print(f"📊 Found {balance_count} balance records for agent_1")

            if balance_count > 0:
                # Show what balances we found
                preview_query = """
                    SELECT currency_code, total_balance, available_balance
                    FROM user_balances
                    WHERE user_id = ?
                    ORDER BY total_balance DESC
                """
                preview_rows = db_manager.execute_query(preview_query, (agent_user_id,))
                print(f"💰 Balance preview:")
                for row in preview_rows:
                    print(f"   {row['currency_code']}: {row['total_balance']} (available: {row['available_balance']})")

            return True
        else:
            print(f"❌ agent_1 user not found in database!")
            print(f"   Please ensure agent_1 exists in the users table")

            # Show what users do exist
            all_users_query = "SELECT username, id FROM users LIMIT 5"
            all_users = db_manager.execute_query(all_users_query)
            if all_users:
                print(f"📋 Available users:")
                for user in all_users:
                    print(f"   {user['username']} (ID: {user['id']})")

            return False

    except Exception as e:
        print(f"❌ Error finding agent_1: {e}")
        return False

async def initialize_system():
    """Initialize the trading system and database."""
    global trading_adapter, server_config, db_manager

    print("🚀 Initializing agent-focused trading server...")
    print("🤖 Target agent: agent_1")
    print("🗄️ Database with balance tracking")
    print("💹 Real trading system integration")
    print("🔗 HTTP transport for external agents")
    print("⚠️ No mock data - real agent_1 and live prices only")

    # Initialize database
    db_manager = DatabaseManager(DB_FILE)
    if not db_manager.connect():
        print("❌ Database initialization failed")
        sys.exit(1)

    # Set up agent_1
    if not await setup_agent_1():
        print("❌ Agent setup failed")
        sys.exit(1)

    # Initialize trading system if available
    if MCPServerConfig and TradingSystemAdapter:
        try:
            server_config = MCPServerConfig()
            trading_adapter = TradingSystemAdapter(server_config)
            await trading_adapter.initialize()
            print("✅ Real trading system initialized successfully")
            print("📊 Live market data available")
        except Exception as e:
            print(f"⚠️ Trading system initialization failed: {e}")
            print("💡 Real-time price data will not be available")
            print("💡 Connect your trading system for live prices and trade execution")
    else:
        print("💡 No real trading system connected")
        print("💡 Real-time price data will not be available")
        print("💡 Connect your trading system for live prices and trade execution")

    print("✅ Agent-focused trading server ready!")

async def shutdown_system():
    """Shutdown the trading system and database."""
    global trading_adapter, db_manager

    print("🔄 Shutting down system...")

    if trading_adapter:
        await trading_adapter.shutdown()

    if db_manager:
        db_manager.disconnect()

    print("✅ Shutdown complete!")

# =============================================================================
# MCP TOOLS - BASIC TOOLS
# =============================================================================

@mcp.tool()
def ping() -> str:
    """Test connectivity to the trading server."""
    return f"🏓 Pong! Agent-focused trading server responding. Connected as: {AGENT_USERNAME}"

@mcp.tool()
def get_server_status() -> str:
    """Get comprehensive server and trading system status."""
    global trading_adapter, db_manager, agent_user_id

    status = {
        "server_name": "Agent-Focused Trading Server",
        "agent_username": AGENT_USERNAME,
        "agent_authenticated": agent_user_id is not None,
        "timestamp": datetime.now().isoformat(),
        "features": {
            "database_access": db_manager is not None and db_manager.connection is not None,
            "agent_trading": True,
            "market_data": trading_adapter is not None,
            "balance_management": True,
            "trade_execution": True,
            "http_transport": True
        },
        "database": {
            "file": DB_FILE,
            "connected": db_manager is not None and db_manager.connection is not None
        },
        "available_tools": [
            "ping", "get_my_balances", "get_portfolio_summary", "get_all_asset_positions",
            "get_market_price", "get_available_pairs", "buy_asset", "sell_asset",
            "get_my_trades", "execute_smart_trade", "get_server_status"
        ]
    }

    if db_manager and db_manager.connection:
        try:
            # Get database stats
            user_count = db_manager.execute_query("SELECT COUNT(*) as count FROM users")
            status["database"]["users"] = user_count[0]['count'] if user_count else 0

            if agent_user_id:
                balance_count = db_manager.execute_query(
                    "SELECT COUNT(*) as count FROM user_balances WHERE user_id = ?",
                    (agent_user_id,)
                )
                status["agent_stats"] = {
                    "balances": balance_count[0]['count'] if balance_count else 0
                }
        except Exception as e:
            status["database"]["error"] = str(e)

    return f"✅ Server Status:\n{json.dumps(status, indent=2)}"

# =============================================================================
# MCP TOOLS - BALANCE MANAGEMENT
# =============================================================================

@mcp.tool()
def get_my_balances() -> str:
    """Get current balances for agent_1."""
    try:
        if not db_manager or not agent_user_id:
            return "❌ Database or agent not initialized"

        query = """
            SELECT ub.currency_code, ub.total_balance, ub.available_balance, ub.locked_balance,
                   ub.updated_at, c.name, c.symbol, c.is_fiat
            FROM user_balances ub
            JOIN currencies c ON ub.currency_code = c.code
            WHERE ub.user_id = ?
            ORDER BY c.is_fiat DESC, ub.total_balance DESC
        """

        balances = db_manager.execute_query(query, (agent_user_id,))

        if not balances:
            return "💰 No balance records found for agent_1"

        result = f"💰 MY COMPLETE BALANCES (agent_1)\n"
        result += "=" * 45 + "\n"

        total_usd_value = 0
        assets_with_balance = 0
        zero_balance_assets = 0

        for balance in balances:
            currency = balance['currency_code']
            symbol = balance.get('symbol', currency)
            name = balance['name']
            total = float(balance['total_balance'])
            available = float(balance['available_balance'])
            locked = float(balance['locked_balance'])
            is_fiat = balance['is_fiat']

            # Count assets
            if total > 0:
                assets_with_balance += 1
            else:
                zero_balance_assets += 1

            result += f"\n💱 {currency} ({name}):\n"
            result += f"   Available: {available:,.8f} {symbol}\n"
            result += f"   Locked:    {locked:,.8f} {symbol}\n"
            result += f"   Total:     {total:,.8f} {symbol}\n"

            # Calculate USD value for non-fiat currencies
            if not is_fiat and currency != 'USD' and total > 0:
                price_data = get_market_price_data(f"{currency}USD")
                if price_data:
                    usd_value = total * price_data['price']
                    total_usd_value += usd_value
                    result += f"   USD Value: ${usd_value:,.2f} (@ ${price_data['price']:,.2f})\n"
                else:
                    result += f"   USD Value: Real-time data N/A\n"
            elif currency == 'USD':
                total_usd_value += total

        result += f"\n📊 PORTFOLIO SUMMARY:\n"
        result += f"   Assets with balance: {assets_with_balance}\n"
        result += f"   Zero balance assets: {zero_balance_assets}\n"
        result += f"   Total assets tracked: {len(balances)}\n"
        result += f"💵 Total Portfolio Value: ${total_usd_value:,.2f}"
        result += f"\n⏰ Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

        return result

    except Exception as e:
        return f"❌ Error getting balances: {str(e)}"

@mcp.tool()
def get_all_asset_positions() -> str:
    """Get complete view of all possible assets and agent_1's position in each."""
    try:
        if not db_manager or not agent_user_id:
            return "❌ Database or agent not initialized"

        # Get all currencies and user's balances (if any)
        query = """
            SELECT c.code, c.name, c.symbol, c.is_fiat, c.is_active,
                   COALESCE(ub.total_balance, 0) as total_balance,
                   COALESCE(ub.available_balance, 0) as available_balance,
                   COALESCE(ub.locked_balance, 0) as locked_balance,
                   ub.updated_at
            FROM currencies c
            LEFT JOIN user_balances ub ON (c.code = ub.currency_code AND ub.user_id = ?)
            WHERE c.is_active = 1
            ORDER BY c.is_fiat DESC, c.code
        """

        assets = db_manager.execute_query(query, (agent_user_id,))

        if not assets:
            return "📊 No asset data available"

        result = f"📊 ALL ASSET POSITIONS (agent_1)\n"
        result += "=" * 50 + "\n"

        fiat_assets = []
        crypto_assets = []
        total_portfolio_value = 0

        for asset in assets:
            currency = asset['code']
            name = asset['name']
            symbol = asset.get('symbol', currency)
            is_fiat = asset['is_fiat']
            total_balance = float(asset['total_balance'])
            available_balance = float(asset['available_balance'])
            locked_balance = float(asset['locked_balance'])
            updated_at = asset['updated_at']

            asset_info = {
                'currency': currency,
                'name': name,
                'symbol': symbol,
                'total_balance': total_balance,
                'available_balance': available_balance,
                'locked_balance': locked_balance,
                'updated_at': updated_at,
                'has_balance': total_balance > 0,
                'usd_value': 0
            }

            # Calculate USD value
            if is_fiat and currency == 'USD':
                asset_info['usd_value'] = total_balance
                total_portfolio_value += total_balance
            elif not is_fiat and total_balance > 0:
                price_data = get_market_price_data(f"{currency}USD")
                if price_data:
                    asset_info['usd_value'] = total_balance * price_data['price']
                    total_portfolio_value += asset_info['usd_value']

            if is_fiat:
                fiat_assets.append(asset_info)
            else:
                crypto_assets.append(asset_info)

        # Display fiat assets
        result += f"\n💵 FIAT CURRENCIES:\n"
        for asset in fiat_assets:
            status = "✅ HAS BALANCE" if asset['has_balance'] else "⭕ EMPTY"
            result += f"   {asset['currency']} ({asset['name']}) - {status}\n"
            if asset['has_balance']:
                result += f"      Balance: ${asset['total_balance']:,.2f}\n"
                result += f"      Available: ${asset['available_balance']:,.2f}\n"
                if asset['locked_balance'] > 0:
                    result += f"      Locked: ${asset['locked_balance']:,.2f}\n"

        # Display crypto assets
        result += f"\n₿ CRYPTO CURRENCIES:\n"
        for asset in crypto_assets:
            status = "✅ HAS BALANCE" if asset['has_balance'] else "⭕ EMPTY"
            result += f"   {asset['currency']} ({asset['name']}) - {status}\n"
            if asset['has_balance']:
                result += f"      Balance: {asset['total_balance']:,.8f} {asset['symbol']}\n"
                result += f"      Available: {asset['available_balance']:,.8f} {asset['symbol']}\n"
                if asset['locked_balance'] > 0:
                    result += f"      Locked: {asset['locked_balance']:,.8f} {asset['symbol']}\n"
                if asset['usd_value'] > 0:
                    result += f"      USD Value: ${asset['usd_value']:,.2f}\n"
                else:
                    result += f"      USD Value: Real-time data N/A\n"

        # Summary statistics
        total_assets = len(assets)
        assets_with_balance = sum(1 for a in assets if float(a['total_balance']) > 0)
        empty_assets = total_assets - assets_with_balance

        result += f"\n📊 PORTFOLIO STATISTICS:\n"
        result += f"   Total Assets Available: {total_assets}\n"
        result += f"   Assets with Balance:    {assets_with_balance}\n"
        result += f"   Empty Assets:           {empty_assets}\n"
        result += f"   Total Portfolio Value:  ${total_portfolio_value:,.2f}\n"

        result += f"\n⏰ Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

        return result

    except Exception as e:
        return f"❌ Error getting asset positions: {str(e)}"

@mcp.tool()
def debug_agent_info() -> str:
    """Debug information about agent_1 connection and data."""
    try:
        global agent_user_id

        result = f"🔍 AGENT_1 DEBUG INFO\n"
        result += "=" * 30 + "\n"

        result += f"Agent Username: {AGENT_USERNAME}\n"
        result += f"Agent User ID: {agent_user_id}\n"
        result += f"Database Connected: {db_manager is not None and db_manager.connection is not None}\n"

        if not agent_user_id:
            result += "\n❌ No agent user ID found!\n"
            return result

        # Check user exists
        user_query = "SELECT id, username, email FROM users WHERE id = ?"
        user_rows = db_manager.execute_query(user_query, (agent_user_id,))

        if user_rows:
            user = user_rows[0]
            result += f"\n✅ User Record Found:\n"
            result += f"   ID: {user['id']}\n"
            result += f"   Username: {user['username']}\n"
            result += f"   Email: {user['email']}\n"
        else:
            result += f"\n❌ No user record found for ID: {agent_user_id}\n"

        # Check balances
        balance_query = """
            SELECT ub.currency_code, ub.total_balance, ub.available_balance, ub.locked_balance
            FROM user_balances ub
            WHERE ub.user_id = ?
            ORDER BY ub.total_balance DESC
        """
        balance_rows = db_manager.execute_query(balance_query, (agent_user_id,))

        result += f"\n💰 Balance Records Found: {len(balance_rows)}\n"
        if balance_rows:
            for balance in balance_rows:
                result += f"   {balance['currency_code']}: {balance['total_balance']} (avail: {balance['available_balance']})\n"
        else:
            result += "   No balance records found!\n"

        # Check if there are balances for a different user ID
        other_balances_query = """
            SELECT ub.user_id, u.username, ub.currency_code, ub.total_balance
            FROM user_balances ub
            LEFT JOIN users u ON ub.user_id = u.id
            WHERE ub.total_balance > 0
            LIMIT 5
        """
        other_balances = db_manager.execute_query(other_balances_query)

        if other_balances:
            result += f"\n🔍 Other balance records in database:\n"
            for bal in other_balances:
                username = bal.get('username', 'Unknown')
                result += f"   User: {username} (ID: {bal['user_id']}) - {bal['currency_code']}: {bal['total_balance']}\n"

        return result

    except Exception as e:
        return f"❌ Debug error: {str(e)}"
    """Get a comprehensive portfolio summary with performance metrics."""
    try:
        if not db_manager or not agent_user_id:
            return "❌ Database or agent not initialized"

        # Get ALL balances (including zero balances)
        balance_query = """
            SELECT ub.currency_code, ub.total_balance, ub.available_balance, ub.locked_balance,
                   c.name, c.is_fiat, ub.updated_at
            FROM user_balances ub
            JOIN currencies c ON ub.currency_code = c.code
            WHERE ub.user_id = ?
            ORDER BY c.is_fiat DESC, ub.total_balance DESC
        """

        balances = db_manager.execute_query(balance_query, (agent_user_id,))

        if not balances:
            return "📊 No portfolio data available"

        result = f"📊 COMPLETE PORTFOLIO SUMMARY (agent_1)\n"
        result += "=" * 55 + "\n"

        total_value = 0
        crypto_value = 0
        fiat_value = 0
        assets_with_balance = 0
        zero_balance_assets = 0

        result += f"\n💰 ALL HOLDINGS:\n"

        for balance in balances:
            currency = balance['currency_code']
            amount = float(balance['total_balance'])
            available = float(balance['available_balance'])
            locked = float(balance['locked_balance'])
            name = balance['name']
            is_fiat = balance['is_fiat']
            updated_at = balance['updated_at']

            # Count assets
            if amount > 0:
                assets_with_balance += 1
            else:
                zero_balance_assets += 1

            if is_fiat:
                value = amount
                fiat_value += value
                if amount > 0:
                    result += f"   {currency}: ${amount:,.2f}\n"
                else:
                    result += f"   {currency}: $0.00 (empty)\n"
            else:
                if amount > 0:
                    price_data = get_market_price_data(f"{currency}USD")
                    if price_data:
                        value = amount * price_data['price']
                        crypto_value += value
                        result += f"   {currency}: {amount:.6f} (${value:,.2f} @ ${price_data['price']:,.2f})\n"
                    else:
                        result += f"   {currency}: {amount:.6f} (Real-time price N/A)\n"
                else:
                    result += f"   {currency}: 0.00000000 (empty)\n"

        total_value = fiat_value + crypto_value

        result += f"\n📈 PORTFOLIO STATISTICS:\n"
        result += f"   Total Assets Tracked: {len(balances)}\n"
        result += f"   Assets with Balance:  {assets_with_balance}\n"
        result += f"   Empty Asset Balances: {zero_balance_assets}\n"

        if total_value > 0:
            result += f"\n💵 VALUE ALLOCATION:\n"
            result += f"   Fiat (USD):    ${fiat_value:,.2f} ({fiat_value/total_value*100:.1f}%)\n"
            result += f"   Crypto:        ${crypto_value:,.2f} ({crypto_value/total_value*100:.1f}%)\n"
            result += f"   TOTAL VALUE:   ${total_value:,.2f}\n"
        else:
            result += f"\n💵 TOTAL PORTFOLIO VALUE: $0.00\n"

        # Get trade count
        trade_query = """
            SELECT COUNT(*) as trade_count,
                   SUM(CASE WHEN transaction_type = 'trade_buy' THEN 1 ELSE 0 END) as buys,
                   SUM(CASE WHEN transaction_type = 'trade_sell' THEN 1 ELSE 0 END) as sells,
                   MAX(created_at) as last_trade
            FROM transactions
            WHERE user_id = ? AND transaction_type IN ('trade_buy', 'trade_sell')
        """

        trade_stats = db_manager.execute_query(trade_query, (agent_user_id,))

        if trade_stats and trade_stats[0]['trade_count']:
            stats = trade_stats[0]
            result += f"\n📊 TRADING ACTIVITY:\n"
            result += f"   Total Trades:  {stats['trade_count']}\n"
            result += f"   Buys:          {stats['buys']}\n"
            result += f"   Sells:         {stats['sells']}\n"
            result += f"   Last Trade:    {stats['last_trade'] or 'None'}\n"
        else:
            result += f"\n📊 TRADING ACTIVITY: No trades recorded\n"

        result += f"\n⏰ Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

        return result

    except Exception as e:
        return f"❌ Error generating portfolio summary: {str(e)}"
    """Get a comprehensive portfolio summary with performance metrics."""
    try:
        if not db_manager or not agent_user_id:
            return "❌ Database or agent not initialized"

        # Get ALL balances (including zero balances)
        balance_query = """
            SELECT ub.currency_code, ub.total_balance, ub.available_balance, ub.locked_balance,
                   c.name, c.is_fiat, ub.updated_at
            FROM user_balances ub
            JOIN currencies c ON ub.currency_code = c.code
            WHERE ub.user_id = ?
            ORDER BY c.is_fiat DESC, ub.total_balance DESC
        """

        balances = db_manager.execute_query(balance_query, (agent_user_id,))

        if not balances:
            return "📊 No portfolio data available"

        result = f"📊 COMPLETE PORTFOLIO SUMMARY (agent_1)\n"
        result += "=" * 55 + "\n"

        total_value = 0
        crypto_value = 0
        fiat_value = 0
        assets_with_balance = 0
        zero_balance_assets = 0

        result += f"\n💰 ALL HOLDINGS:\n"

        for balance in balances:
            currency = balance['currency_code']
            amount = float(balance['total_balance'])
            available = float(balance['available_balance'])
            locked = float(balance['locked_balance'])
            name = balance['name']
            is_fiat = balance['is_fiat']
            updated_at = balance['updated_at']

            # Count assets
            if amount > 0:
                assets_with_balance += 1
            else:
                zero_balance_assets += 1

            if is_fiat:
                value = amount
                fiat_value += value
                if amount > 0:
                    result += f"   {currency}: ${amount:,.2f}\n"
                else:
                    result += f"   {currency}: $0.00 (empty)\n"
            else:
                if amount > 0:
                    price_data = get_market_price_data(f"{currency}USD")
                    if price_data:
                        value = amount * price_data['price']
                        crypto_value += value
                        result += f"   {currency}: {amount:.6f} (${value:,.2f} @ ${price_data['price']:,.2f})\n"
                    else:
                        result += f"   {currency}: {amount:.6f} (Real-time price N/A)\n"
                else:
                    result += f"   {currency}: 0.00000000 (empty)\n"

        total_value = fiat_value + crypto_value

        result += f"\n📈 PORTFOLIO STATISTICS:\n"
        result += f"   Total Assets Tracked: {len(balances)}\n"
        result += f"   Assets with Balance:  {assets_with_balance}\n"
        result += f"   Empty Asset Balances: {zero_balance_assets}\n"

        if total_value > 0:
            result += f"\n💵 VALUE ALLOCATION:\n"
            result += f"   Fiat (USD):    ${fiat_value:,.2f} ({fiat_value/total_value*100:.1f}%)\n"
            result += f"   Crypto:        ${crypto_value:,.2f} ({crypto_value/total_value*100:.1f}%)\n"
            result += f"   TOTAL VALUE:   ${total_value:,.2f}\n"
        else:
            result += f"\n💵 TOTAL PORTFOLIO VALUE: $0.00\n"

        # Get trade count
        trade_query = """
            SELECT COUNT(*) as trade_count,
                   SUM(CASE WHEN transaction_type = 'trade_buy' THEN 1 ELSE 0 END) as buys,
                   SUM(CASE WHEN transaction_type = 'trade_sell' THEN 1 ELSE 0 END) as sells,
                   MAX(created_at) as last_trade
            FROM transactions
            WHERE user_id = ? AND transaction_type IN ('trade_buy', 'trade_sell')
        """

        trade_stats = db_manager.execute_query(trade_query, (agent_user_id,))

        if trade_stats and trade_stats[0]['trade_count']:
            stats = trade_stats[0]
            result += f"\n📊 TRADING ACTIVITY:\n"
            result += f"   Total Trades:  {stats['trade_count']}\n"
            result += f"   Buys:          {stats['buys']}\n"
            result += f"   Sells:         {stats['sells']}\n"
            result += f"   Last Trade:    {stats['last_trade'] or 'None'}\n"
        else:
            result += f"\n📊 TRADING ACTIVITY: No trades recorded\n"

        result += f"\n⏰ Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

        return result

    except Exception as e:
        return f"❌ Error generating portfolio summary: {str(e)}"

# =============================================================================
# MCP TOOLS - MARKET DATA
# =============================================================================

@mcp.tool()
def get_market_price(symbol: str) -> str:
    """Get current market price for a trading pair (e.g., BTCUSD, ETHUSD)."""
    try:
        symbol = symbol.upper()

        # Try to get real market data
        price_data = get_market_price_data(symbol)

        if not price_data:
            return f"❌ Real-time price data not available for {symbol}\n💡 Please connect to a real trading system to get live prices"

        result = f"📊 MARKET DATA: {symbol}\n"
        result += "=" * 30 + "\n"
        result += f"💰 Current Price: ${price_data['price']:,.2f}\n"
        result += f"📈 Bid: ${price_data['bid']:,.2f}\n"
        result += f"📉 Ask: ${price_data['ask']:,.2f}\n"
        result += f"⬆️ 24h High: ${price_data['high_24h']:,.2f}\n"
        result += f"⬇️ 24h Low: ${price_data['low_24h']:,.2f}\n"
        result += f"📈 24h Change: {price_data['change_24h']}\n"
        result += f"📊 24h Volume: {price_data['volume_24h']}\n"
        result += f"⏰ Updated: {datetime.now().strftime('%H:%M:%S')}\n"

        return result

    except Exception as e:
        return f"❌ Error getting price: {str(e)}"

@mcp.tool()
def get_available_pairs() -> str:
    """Get list of available trading pairs."""
    try:
        if not db_manager:
            return "❌ Database not connected"

        query = """
            SELECT tp.symbol, tp.base_currency, tp.quote_currency, tp.min_trade_amount,
                   bc.name as base_name, qc.name as quote_name
            FROM trading_pairs tp
            JOIN currencies bc ON tp.base_currency = bc.code
            JOIN currencies qc ON tp.quote_currency = qc.code
            WHERE tp.is_active = 1
            ORDER BY tp.symbol
        """

        pairs = db_manager.execute_query(query)

        if not pairs:
            return "❌ No trading pairs available"

        result = f"📊 AVAILABLE TRADING PAIRS\n"
        result += "=" * 40 + "\n"

        for pair in pairs:
            symbol = pair['symbol']
            base_name = pair['base_name']
            quote_name = pair['quote_name']
            min_amount = float(pair['min_trade_amount'])

            # Try to get current price from real trading system
            price_data = get_market_price_data(symbol)
            price_str = f"${price_data['price']:,.2f}" if price_data else "Real-time data N/A"

            result += f"\n💱 {symbol}:\n"
            result += f"   {base_name} / {quote_name}\n"
            result += f"   Current Price: {price_str}\n"
            result += f"   Min Trade: {min_amount} {pair['base_currency']}\n"

        result += f"\n💡 Connect to real trading system for live prices"
        return result

    except Exception as e:
        return f"❌ Error getting trading pairs: {str(e)}"

# =============================================================================
# MCP TOOLS - TRADING EXECUTION
# =============================================================================

@mcp.tool()
def buy_asset(symbol: str, amount_usd: float) -> str:
    """Buy an asset using USD. Updates balances in database."""
    try:
        if not db_manager or not agent_user_id:
            return "❌ Database or agent not initialized"

        symbol = symbol.upper()

        # Validate amount
        if amount_usd <= 0:
            return f"❌ Invalid amount: ${amount_usd}"

        if amount_usd > 1000:  # Safety limit
            return f"❌ Amount too large: ${amount_usd} (max $1000 per trade)"

        # Get current price from real trading system
        price_data = get_market_price_data(symbol)
        if not price_data:
            return f"❌ Cannot execute trade: Real-time price data not available for {symbol}\n💡 Please connect to a real trading system to execute trades"

        current_price = price_data['price']
        asset_amount = amount_usd / current_price

        # Extract base currency from symbol (e.g., BTC from BTCUSD)
        base_currency = symbol.replace('USD', '')
        if base_currency == symbol:  # Handle other quote currencies
            base_currency = symbol[:3]

        # Check USD balance
        usd_balance_query = """
            SELECT available_balance FROM user_balances
            WHERE user_id = ? AND currency_code = 'USD'
        """
        usd_balance_rows = db_manager.execute_query(usd_balance_query, (agent_user_id,))

        if not usd_balance_rows:
            return "❌ No USD balance found"

        available_usd = float(usd_balance_rows[0]['available_balance'])
        if available_usd < amount_usd:
            return f"❌ Insufficient USD balance. Available: ${available_usd:.2f}, Required: ${amount_usd:.2f}"

        # Calculate fee (0.1%)
        fee_amount = amount_usd * 0.001
        net_amount_usd = amount_usd + fee_amount

        if available_usd < net_amount_usd:
            return f"❌ Insufficient USD for trade + fees. Available: ${available_usd:.2f}, Required: ${net_amount_usd:.2f}"

        # Execute the trade in database
        try:
            # 1. Deduct USD
            usd_update_query = """
                UPDATE user_balances
                SET available_balance = available_balance - ?,
                    total_balance = total_balance - ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND currency_code = 'USD'
            """
            db_manager.execute_update(usd_update_query, (net_amount_usd, net_amount_usd, agent_user_id))

            # 2. Add asset
            asset_update_query = """
                INSERT OR REPLACE INTO user_balances
                (user_id, currency_code, total_balance, available_balance, locked_balance, updated_at)
                VALUES (?, ?,
                    COALESCE((SELECT total_balance FROM user_balances WHERE user_id = ? AND currency_code = ?), 0) + ?,
                    COALESCE((SELECT available_balance FROM user_balances WHERE user_id = ? AND currency_code = ?), 0) + ?,
                    COALESCE((SELECT locked_balance FROM user_balances WHERE user_id = ? AND currency_code = ?), 0),
                    CURRENT_TIMESTAMP)
            """
            db_manager.execute_update(asset_update_query,
                (agent_user_id, base_currency, agent_user_id, base_currency, asset_amount,
                 agent_user_id, base_currency, asset_amount, agent_user_id, base_currency))

            # 3. Record transaction
            trade_id = str(uuid.uuid4()).replace('-', '')
            transaction_query = """
                INSERT INTO transactions
                (id, user_id, transaction_type, status, amount, currency_code, fee_amount, fee_currency_code,
                 description, created_at, processed_at)
                VALUES (?, ?, 'trade_buy', 'completed', ?, ?, ?, 'USD', ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """
            description = f"Buy {asset_amount:.8f} {base_currency} for ${amount_usd:.2f} @ ${current_price:.2f}"
            db_manager.execute_update(transaction_query,
                (trade_id, agent_user_id, asset_amount, base_currency, fee_amount, description))

            result = f"✅ BUY ORDER EXECUTED\n"
            result += "=" * 25 + "\n"
            result += f"💰 Purchased: {asset_amount:.8f} {base_currency}\n"
            result += f"💵 Cost: ${amount_usd:.2f}\n"
            result += f"📊 Price: ${current_price:.2f}\n"
            result += f"💸 Fee: ${fee_amount:.2f}\n"
            result += f"🆔 Transaction ID: {trade_id[:8]}...\n"
            result += f"⏰ Executed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"

            return result

        except Exception as e:
            return f"❌ Trade execution failed: {str(e)}"

    except Exception as e:
        return f"❌ Error processing buy order: {str(e)}"

@mcp.tool()
def sell_asset(symbol: str, amount: float) -> str:
    """Sell an asset for USD. Updates balances in database."""
    try:
        if not db_manager or not agent_user_id:
            return "❌ Database or agent not initialized"

        symbol = symbol.upper()

        # Validate amount
        if amount <= 0:
            return f"❌ Invalid amount: {amount}"

        # Get current price from real trading system
        price_data = get_market_price_data(symbol)
        if not price_data:
            return f"❌ Cannot execute trade: Real-time price data not available for {symbol}\n💡 Please connect to a real trading system to execute trades"

        current_price = price_data['price']
        usd_value = amount * current_price

        # Extract base currency from symbol
        base_currency = symbol.replace('USD', '')
        if base_currency == symbol:
            base_currency = symbol[:3]

        # Check asset balance
        asset_balance_query = """
            SELECT available_balance FROM user_balances
            WHERE user_id = ? AND currency_code = ?
        """
        asset_balance_rows = db_manager.execute_query(asset_balance_query, (agent_user_id, base_currency))

        if not asset_balance_rows:
            return f"❌ No {base_currency} balance found"

        available_amount = float(asset_balance_rows[0]['available_balance'])
        if available_amount < amount:
            return f"❌ Insufficient {base_currency} balance. Available: {available_amount:.8f}, Required: {amount:.8f}"

        # Calculate fee (0.1%)
        fee_amount = usd_value * 0.001
        net_usd_received = usd_value - fee_amount

        # Execute the trade
        try:
            # 1. Deduct asset
            asset_update_query = """
                UPDATE user_balances
                SET available_balance = available_balance - ?,
                    total_balance = total_balance - ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND currency_code = ?
            """
            db_manager.execute_update(asset_update_query, (amount, amount, agent_user_id, base_currency))

            # 2. Add USD
            usd_update_query = """
                INSERT OR REPLACE INTO user_balances
                (user_id, currency_code, total_balance, available_balance, locked_balance, updated_at)
                VALUES (?, 'USD',
                    COALESCE((SELECT total_balance FROM user_balances WHERE user_id = ? AND currency_code = 'USD'), 0) + ?,
                    COALESCE((SELECT available_balance FROM user_balances WHERE user_id = ? AND currency_code = 'USD'), 0) + ?,
                    COALESCE((SELECT locked_balance FROM user_balances WHERE user_id = ? AND currency_code = 'USD'), 0),
                    CURRENT_TIMESTAMP)
            """
            db_manager.execute_update(usd_update_query,
                (agent_user_id, agent_user_id, net_usd_received, agent_user_id, net_usd_received, agent_user_id))

            # 3. Record transaction
            trade_id = str(uuid.uuid4()).replace('-', '')
            transaction_query = """
                INSERT INTO transactions
                (id, user_id, transaction_type, status, amount, currency_code, fee_amount, fee_currency_code,
                 description, created_at, processed_at)
                VALUES (?, ?, 'trade_sell', 'completed', ?, ?, ?, 'USD', ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """
            description = f"Sell {amount:.8f} {base_currency} for ${usd_value:.2f} @ ${current_price:.2f}"
            db_manager.execute_update(transaction_query,
                (trade_id, agent_user_id, amount, base_currency, fee_amount, description))

            result = f"✅ SELL ORDER EXECUTED\n"
            result += "=" * 25 + "\n"
            result += f"📉 Sold: {amount:.8f} {base_currency}\n"
            result += f"💵 Received: ${net_usd_received:.2f}\n"
            result += f"📊 Price: ${current_price:.2f}\n"
            result += f"💸 Fee: ${fee_amount:.2f}\n"
            result += f"🆔 Transaction ID: {trade_id[:8]}...\n"
            result += f"⏰ Executed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"

            return result

        except Exception as e:
            return f"❌ Trade execution failed: {str(e)}"

    except Exception as e:
        return f"❌ Error processing sell order: {str(e)}"

# =============================================================================
# MCP TOOLS - TRADING HISTORY
# =============================================================================

@mcp.tool()
def get_my_trades() -> str:
    """Get recent trading history for agent_1."""
    try:
        if not db_manager or not agent_user_id:
            return "❌ Database or agent not initialized"

        query = """
            SELECT transaction_type, amount, currency_code, fee_amount, description,
                   created_at, id
            FROM transactions
            WHERE user_id = ? AND transaction_type IN ('trade_buy', 'trade_sell')
            ORDER BY created_at DESC
            LIMIT 10
        """

        trades = db_manager.execute_query(query, (agent_user_id,))

        if not trades:
            return "📋 No trading history found for agent_1"

        result = f"📋 MY RECENT TRADES (agent_1)\n"
        result += "=" * 40 + "\n"

        for i, trade in enumerate(trades, 1):
            trade_type = "🟢 BUY" if trade['transaction_type'] == 'trade_buy' else "🔴 SELL"
            amount = float(trade['amount'])
            currency = trade['currency_code']
            fee = float(trade['fee_amount'])
            description = trade['description']
            created_at = trade['created_at']
            trade_id = trade['id'][:8]

            result += f"\n{i:2d}. {trade_type} | {amount:.8f} {currency}\n"
            result += f"    {description}\n"
            result += f"    Fee: ${fee:.2f} | ID: {trade_id}... | {created_at}\n"

        return result

    except Exception as e:
        return f"❌ Error getting trade history: {str(e)}"

# =============================================================================
# MCP TOOLS - SMART TRADING
# =============================================================================

@mcp.tool()
def execute_smart_trade(command: str) -> str:
    """Execute a natural language trading command (e.g., 'buy $100 of bitcoin', 'sell half my ethereum')."""
    try:
        command = command.lower().strip()

        # Parse buy commands
        if 'buy' in command:
            # Extract amount and asset
            usd_match = re.search(r'\$(\d+(?:\.\d+)?)', command)

            if 'bitcoin' in command or 'btc' in command:
                symbol = 'BTCUSD'
            elif 'ethereum' in command or 'eth' in command:
                symbol = 'ETHUSD'
            elif 'solana' in command or 'sol' in command:
                symbol = 'SOLUSD'
            elif 'cardano' in command or 'ada' in command:
                symbol = 'ADAUSD'
            else:
                return "❓ Could not identify asset. Supported: bitcoin/btc, ethereum/eth, solana/sol, cardano/ada"

            if usd_match:
                amount_usd = float(usd_match.group(1))
                return buy_asset(symbol, amount_usd)
            else:
                return "❓ Could not parse USD amount. Try: 'buy $100 of bitcoin'"

        # Parse sell commands
        elif 'sell' in command:
            asset_amounts = {
                'bitcoin': ('BTCUSD', 'BTC'),
                'btc': ('BTCUSD', 'BTC'),
                'ethereum': ('ETHUSD', 'ETH'),
                'eth': ('ETHUSD', 'ETH'),
                'solana': ('SOLUSD', 'SOL'),
                'sol': ('SOLUSD', 'SOL'),
                'cardano': ('ADAUSD', 'ADA'),
                'ada': ('ADAUSD', 'ADA')
            }

            symbol = None
            currency = None

            for asset, (sym, curr) in asset_amounts.items():
                if asset in command:
                    symbol = sym
                    currency = curr
                    break

            if not symbol:
                return "❓ Could not identify asset to sell"

            # Parse amount
            if 'half' in command or '50%' in command:
                # Get current balance
                balance_query = """
                    SELECT available_balance FROM user_balances
                    WHERE user_id = ? AND currency_code = ?
                """
                balance_rows = db_manager.execute_query(balance_query, (agent_user_id, currency))
                if balance_rows:
                    amount = float(balance_rows[0]['available_balance']) * 0.5
                else:
                    return f"❌ No {currency} balance found"
            elif 'all' in command or '100%' in command:
                # Get current balance
                balance_query = """
                    SELECT available_balance FROM user_balances
                    WHERE user_id = ? AND currency_code = ?
                """
                balance_rows = db_manager.execute_query(balance_query, (agent_user_id, currency))
                if balance_rows:
                    amount = float(balance_rows[0]['available_balance'])
                else:
                    return f"❌ No {currency} balance found"
            else:
                # Extract specific amount
                amount_match = re.search(r'(\d+(?:\.\d+)?)', command)
                if amount_match:
                    amount = float(amount_match.group(1))
                else:
                    return "❓ Could not parse amount. Try: 'sell 0.1 bitcoin' or 'sell half my ethereum'"

            return sell_asset(symbol, amount)

        # Parse balance/portfolio commands
        elif any(word in command for word in ['balance', 'portfolio', 'holdings']):
            if 'summary' in command or 'portfolio' in command:
                return get_portfolio_summary()
            else:
                return get_my_balances()

        # Parse price commands
        elif 'price' in command:
            if 'bitcoin' in command or 'btc' in command:
                return get_market_price('BTCUSD')
            elif 'ethereum' in command or 'eth' in command:
                return get_market_price('ETHUSD')
            elif 'solana' in command or 'sol' in command:
                return get_market_price('SOLUSD')
            elif 'cardano' in command or 'ada' in command:
                return get_market_price('ADAUSD')
            else:
                return "❓ Which asset price? Try: 'bitcoin price' or 'ethereum price'"

        # Parse trade history
        elif 'trades' in command or 'history' in command:
            return get_my_trades()

        else:
            return "❓ Command not understood. Try: 'buy $100 bitcoin', 'sell half ethereum', 'show balance', 'bitcoin price'"

    except Exception as e:
        return f"❌ Error processing command: {str(e)}"

# =============================================================================
# MCP TOOLS - FILE ACCESS (kept for compatibility)
# =============================================================================

@mcp.tool()
def read_file(file_path: str) -> str:
    """Read contents of a file from the local repository."""
    try:
        path = Path(file_path)
        if not path.is_absolute():
            path = project_root / path

        try:
            path.resolve().relative_to(project_root.resolve())
        except ValueError:
            return f"❌ Error: Access denied - path outside project directory: {file_path}"

        if not path.exists():
            return f"❌ Error: File not found: {file_path}"

        if not path.is_file():
            return f"❌ Error: Path is not a file: {file_path}"

        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        return f"📄 File: {file_path}\n\n{content}"

    except Exception as e:
        return f"❌ Error reading file {file_path}: {str(e)}"

# =============================================================================
# MCP RESOURCES
# =============================================================================

@mcp.resource("agent://balances")
def agent_balances() -> str:
    """Current agent balances resource."""
    if not db_manager or not agent_user_id:
        return json.dumps({"error": "Agent not initialized"})

    try:
        query = """
            SELECT ub.currency_code, ub.total_balance, ub.available_balance, ub.locked_balance
            FROM user_balances ub
            WHERE ub.user_id = ? AND ub.total_balance > 0
        """
        balances = db_manager.execute_query(query, (agent_user_id,))
        return json.dumps({"agent": AGENT_USERNAME, "balances": balances}, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})

@mcp.resource("market://prices")
def market_prices() -> str:
    """Current market prices resource."""
    symbols = ['BTCUSD', 'ETHUSD', 'SOLUSD', 'ADAUSD']
    prices = {}

    for symbol in symbols:
        price_data = get_market_price_data(symbol)
        if price_data:
            prices[symbol] = price_data
        else:
            prices[symbol] = {"error": "Real-time data not available"}

    return json.dumps({
        "prices": prices,
        "timestamp": datetime.now().isoformat(),
        "note": "Connect to real trading system for live prices"
    })

# =============================================================================
# MAIN EXECUTION
# =============================================================================

async def main_async():
    """Async main entry point."""
    print("🤖 AGENT-FOCUSED TRADING SERVER")
    print("=" * 50)
    print("Features:")
    print("  🤖 Designed for AI agent trading")
    print("  💰 Real balance management in database")
    print("  📊 Live market data integration (when connected)")
    print("  💹 Execute buy/sell orders (with real prices)")
    print("  📈 Portfolio tracking & analytics")
    print("  🧠 Natural language trading commands")
    print("  ⚠️ No mock data - requires real trading system")
    print("=" * 50)

    # Initialize system (trading and database)
    await initialize_system()

    # Health check endpoint
    async def health_check(request):
        return JSONResponse({
            "status": "healthy",
            "server": "Agent-Focused Trading Server",
            "agent": AGENT_USERNAME,
            "features": ["agent_trading", "database", "market_data", "balance_management"],
            "database_connected": db_manager is not None and db_manager.connection is not None,
            "agent_authenticated": agent_user_id is not None,
            "timestamp": datetime.now().isoformat()
        })

    # Run with both stdio and HTTP support
    if len(sys.argv) > 1 and sys.argv[1] == "--http":
        print("🌐 Starting HTTP server mode...")

        routes = [
            Route("/health", health_check, methods=["GET"]),
            Route("/", health_check, methods=["GET"])
        ]

        # Add a simple MCP tool endpoint for debugging
        async def mcp_tool_handler(request):
            """Handle MCP tool calls directly via HTTP."""
            try:
                if request.method == "POST":
                    body = await request.json()

                    # Extract tool name and arguments
                    if "method" in body and body["method"] == "tools/call":
                        params = body.get("params", {})
                        tool_name = params.get("name")
                        arguments = params.get("arguments", {})

                        # Call the appropriate tool
                        if tool_name == "ping":
                            result = ping()
                        elif tool_name == "debug_agent_info":
                            result = debug_agent_info()
                        elif tool_name == "get_my_balances":
                            result = get_my_balances()
                        elif tool_name == "get_portfolio_summary":
                            result = get_portfolio_summary()
                        elif tool_name == "get_all_asset_positions":
                            result = get_all_asset_positions()
                        elif tool_name == "get_market_price":
                            symbol = arguments.get("symbol", "BTCUSD")
                            result = get_market_price(symbol)
                        elif tool_name == "get_available_pairs":
                            result = get_available_pairs()
                        elif tool_name == "buy_asset":
                            symbol = arguments.get("symbol", "BTCUSD")
                            amount_usd = arguments.get("amount_usd", 0)
                            result = buy_asset(symbol, amount_usd)
                        elif tool_name == "sell_asset":
                            symbol = arguments.get("symbol", "BTCUSD")
                            amount = arguments.get("amount", 0)
                            result = sell_asset(symbol, amount)
                        elif tool_name == "get_my_trades":
                            result = get_my_trades()
                        elif tool_name == "execute_smart_trade":
                            command = arguments.get("command", "")
                            result = execute_smart_trade(command)
                        elif tool_name == "get_server_status":
                            result = get_server_status()
                        else:
                            result = f"❌ Unknown tool: {tool_name}"

                        # Return MCP-formatted response
                        return JSONResponse({
                            "jsonrpc": "2.0",
                            "id": body.get("id", 1),
                            "result": {
                                "content": [{"type": "text", "text": result}]
                            }
                        })
                    else:
                        return JSONResponse({
                            "jsonrpc": "2.0",
                            "id": body.get("id", 1),
                            "error": {"code": -1, "message": "Invalid method"}
                        })
                else:
                    return JSONResponse({"error": "Only POST method supported"})

            except Exception as e:
                return JSONResponse({
                    "jsonrpc": "2.0",
                    "id": 1,
                    "error": {"code": -1, "message": str(e)}
                })

        # Add the MCP tool handler
        routes.append(Route("/mcp", mcp_tool_handler, methods=["POST"]))

        # Try to mount MCP SSE endpoint (optional)
        try:
            sse_app = mcp.sse_app()
            routes.append(Mount("/sse", app=sse_app))
            print("📡 MCP SSE endpoint: http://localhost:8000/sse")
        except Exception as e:
            print(f"⚠️ SSE mounting failed: {e}")
            print("💡 Using direct MCP endpoint instead: http://localhost:8000/mcp")

        app = Starlette(routes=routes)
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        print("🚀 Server starting on http://localhost:8000")
        print("📡 Direct MCP endpoint: http://localhost:8000/mcp")
        print(f"🤖 Agent {AGENT_USERNAME} ready for trading!")

        import uvicorn
        config = uvicorn.Config(app, host="127.0.0.1", port=8000, log_level="info")
        server = uvicorn.Server(config)

        try:
            await server.serve()
        except KeyboardInterrupt:
            print("\n🔄 Shutting down server...")
        finally:
            await shutdown_system()
    else:
        print("📱 Starting stdio mode...")
        print("💡 Use --http flag for HTTP server mode")
        try:
            await mcp.run_stdio_async()
        except KeyboardInterrupt:
            print("\n🔄 Shutting down server...")
        finally:
            await shutdown_system()

def main():
    """Main entry point."""
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        print(f"\n👋 {AGENT_USERNAME} trading server stopped")

if __name__ == "__main__":
    main()
