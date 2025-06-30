"""
Trading System Adapter for MCP Integration

This module provides the adapter layer between the MCP server and the existing
Kraken trading system infrastructure, managing connections and data flow.

File Location: src/trading_systems/mcp_server/trading_adapter.py
"""

import asyncio
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime
import json

from ..utils.logger import LoggerMixin
from ..utils.exceptions import TradingSystemError, ConnectionError
from ..config.settings import settings
from .config import MCPServerConfig


@dataclass
class TradingSystemStatus:
    """Status information for the trading system."""
    websocket_connected: bool
    order_manager_active: bool
    account_data_available: bool
    last_update: datetime
    connection_details: Dict[str, Any]


class TradingSystemAdapter(LoggerMixin):
    """
    Adapter layer between MCP server and Kraken trading system.
    
    This class:
    1. Manages connections to existing trading system components
    2. Provides a simplified interface for MCP operations
    3. Handles error translation and logging
    4. Manages connection lifecycle
    """
    
    def __init__(self, config: MCPServerConfig):
        super().__init__()
        self.config = config
        
        # Trading system components (will be initialized)
        self.websocket_client = None
        self.order_manager = None
        self.account_manager = None
        self.rest_client = None
        
        # Connection state
        self.is_initialized = False
        self.last_status_update = None
        
        # Mock/Demo mode data
        self.demo_mode = not config.enable_real_trading
        self.mock_data = self._initialize_mock_data()
        
        self.log_info("Trading system adapter created", demo_mode=self.demo_mode)
    
    def _initialize_mock_data(self) -> Dict[str, Any]:
        """Initialize mock data for demo mode."""
        return {
            "account_balance": {
                "USD": {"balance": "10000.00", "available": "8500.00"},
                "XBT": {"balance": "0.25", "available": "0.25"},
                "ETH": {"balance": "5.0", "available": "5.0"}
            },
            "market_status": {
                "status": "online",
                "timestamp": datetime.now().isoformat(),
                "trading_pairs": ["XBT/USD", "ETH/USD", "ADA/USD"]
            },
            "open_orders": [],
            "recent_trades": []
        }
    
    async def initialize(self) -> None:
        """Initialize the trading system adapter and connections."""
        try:
            self.log_info("Initializing trading system adapter...")
            
            if self.demo_mode:
                await self._initialize_demo_mode()
            else:
                await self._initialize_real_trading()
            
            self.is_initialized = True
            self.last_status_update = datetime.now()
            
            self.log_info("✅ Trading system adapter initialized successfully")
            
        except Exception as e:
            self.log_error("❌ Failed to initialize trading system adapter", error=e)
            raise TradingSystemError(f"Adapter initialization failed: {e}")
    
    async def _initialize_demo_mode(self) -> None:
        """Initialize adapter in demo mode with mock components."""
        self.log_info("🎭 Initializing in demo mode (no real trading)")
        
        # Simulate initialization delay
        await asyncio.sleep(0.5)
        
        # Mock successful initialization
        self.websocket_client = "mock_websocket"
        self.order_manager = "mock_order_manager"
        self.account_manager = "mock_account_manager"
        self.rest_client = "mock_rest_client"
        
        self.log_info("✅ Demo mode initialization complete")
    
    async def _initialize_real_trading(self) -> None:
        """Initialize adapter with real trading system components."""
        self.log_info("💰 Initializing real trading system components")
        
        try:
            # Import real trading system components
            from ..exchanges.kraken.websocket_client import KrakenWebSocketClient
            from ..exchanges.kraken.rest_client import EnhancedKrakenRestClient
            from ..exchanges.kraken.account_data_manager import AccountDataManager
            from ..exchanges.kraken.order_manager import OrderManager
            
            # Initialize REST client
            self.rest_client = EnhancedKrakenRestClient()
            self.log_info("✅ REST client initialized")
            
            # Initialize WebSocket client
            self.websocket_client = KrakenWebSocketClient()
            self.log_info("✅ WebSocket client initialized")
            
            # Initialize account data manager
            self.account_manager = AccountDataManager()
            self.log_info("✅ Account data manager initialized")
            
            # Initialize order manager
            self.order_manager = OrderManager(account_manager=self.account_manager)
            self.log_info("✅ Order manager initialized")
            
            # Test connections
            await self._test_connections()
            
        except ImportError as e:
            self.log_error("❌ Failed to import trading system components", error=e)
            raise TradingSystemError(f"Component import failed: {e}")
        except Exception as e:
            self.log_error("❌ Failed to initialize real trading components", error=e)
            raise TradingSystemError(f"Real trading initialization failed: {e}")
    
    async def _test_connections(self) -> None:
        """Test connections to trading system components."""
        self.log_info("🔍 Testing trading system connections...")
        
        try:
            # Test REST client connection
            if hasattr(self.rest_client, 'get_system_status'):
                status = await self.rest_client.get_system_status()
                self.log_info("✅ REST API connection successful")
            
            # Test WebSocket client (if implemented)
            if hasattr(self.websocket_client, 'get_connection_status'):
                ws_status = self.websocket_client.get_connection_status()
                self.log_info("✅ WebSocket client status checked")
            
        except Exception as e:
            self.log_warning("⚠️ Connection test failed (continuing in limited mode)", error=e)
    
    def get_status(self) -> TradingSystemStatus:
        """Get current status of the trading system."""
        
        if self.demo_mode:
            return TradingSystemStatus(
                websocket_connected=True,
                order_manager_active=True,
                account_data_available=True,
                last_update=self.last_status_update or datetime.now(),
                connection_details={
                    "mode": "demo",
                    "components": "mock",
                    "trading_enabled": False
                }
            )
        
        # Real trading status
        try:
            ws_connected = self.websocket_client is not None
            order_mgr_active = self.order_manager is not None
            account_available = self.account_manager is not None
            
            return TradingSystemStatus(
                websocket_connected=ws_connected,
                order_manager_active=order_mgr_active,
                account_data_available=account_available,
                last_update=self.last_status_update or datetime.now(),
                connection_details={
                    "mode": "real",
                    "components": "live",
                    "trading_enabled": self.config.enable_real_trading
                }
            )
            
        except Exception as e:
            self.log_error("Error getting system status", error=e)
            return TradingSystemStatus(
                websocket_connected=False,
                order_manager_active=False,
                account_data_available=False,
                last_update=datetime.now(),
                connection_details={"error": str(e)}
            )
    
    async def get_account_balance(self) -> Dict[str, Any]:
        """Get current account balance information."""
        try:
            if self.demo_mode:
                return self.mock_data["account_balance"]
            
            # Real trading implementation would call actual account manager
            if self.account_manager and hasattr(self.account_manager, 'get_balance'):
                return await self.account_manager.get_balance()
            else:
                # Fallback to REST API
                if self.rest_client:
                    balance = await self.rest_client.get_account_balance()
                    return balance
                
            raise TradingSystemError("No account data source available")
            
        except Exception as e:
            self.log_error("Failed to get account balance", error=e)
            raise TradingSystemError(f"Account balance error: {e}")
    
    def get_market_status(self) -> Dict[str, Any]:
        """Get current market status information."""
        try:
            if self.demo_mode:
                # Update timestamp for demo data
                self.mock_data["market_status"]["timestamp"] = datetime.now().isoformat()
                return self.mock_data["market_status"]
            
            # Real trading implementation would get actual market status
            # For now, return basic status
            return {
                "status": "connected" if self.websocket_client else "disconnected",
                "timestamp": datetime.now().isoformat(),
                "trading_pairs": list(self.config.get_allowed_trading_pairs())
            }
            
        except Exception as e:
            self.log_error("Failed to get market status", error=e)
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def shutdown(self) -> None:
        """Shutdown the trading system adapter and clean up connections."""
        try:
            self.log_info("🔄 Shutting down trading system adapter...")
            
            if not self.demo_mode:
                # Cleanup real trading system components
                if self.websocket_client and hasattr(self.websocket_client, 'disconnect'):
                    await self.websocket_client.disconnect()
                
                if self.order_manager and hasattr(self.order_manager, 'shutdown'):
                    await self.order_manager.shutdown()
            
            self.is_initialized = False
            self.log_info("✅ Trading system adapter shutdown complete")
            
        except Exception as e:
            self.log_error("Error during adapter shutdown", error=e)