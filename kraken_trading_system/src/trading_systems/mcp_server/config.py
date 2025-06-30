"""
MCP Server Configuration for Kraken Trading System

This module provides configuration management for the MCP server,
including security settings, rate limiting, and integration options.

File Location: src/trading_systems/mcp_server/config.py
"""

from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from pydantic import BaseModel, Field
from pathlib import Path
import os

from ..config.settings import settings


class MCPSecurityConfig(BaseModel):
    """Security configuration for MCP server operations."""
    
    # Authentication settings
    require_authentication: bool = Field(default=True, description="Require authentication for trading operations")
    allowed_clients: Set[str] = Field(default_factory=set, description="Set of allowed client identifiers")
    
    # Rate limiting
    max_requests_per_minute: int = Field(default=60, description="Maximum requests per minute per client")
    max_trading_operations_per_hour: int = Field(default=10, description="Maximum trading operations per hour")
    
    # Operation restrictions
    allowed_trading_pairs: Set[str] = Field(default_factory=lambda: {"XBT/USD", "ETH/USD"}, description="Allowed trading pairs")
    max_order_value_usd: float = Field(default=1000.0, description="Maximum order value in USD")
    enable_market_orders: bool = Field(default=False, description="Allow market orders (higher risk)")
    
    # Audit and logging
    audit_all_operations: bool = Field(default=True, description="Audit all trading operations")
    log_level: str = Field(default="INFO", description="Logging level for MCP operations")


class MCPPerformanceConfig(BaseModel):
    """Performance configuration for MCP server."""
    
    # Connection settings
    max_concurrent_connections: int = Field(default=5, description="Maximum concurrent MCP connections")
    connection_timeout_seconds: int = Field(default=30, description="Connection timeout in seconds")
    
    # Resource caching
    cache_market_data_seconds: int = Field(default=5, description="Cache market data for N seconds")
    cache_account_data_seconds: int = Field(default=10, description="Cache account data for N seconds")
    
    # WebSocket settings
    websocket_reconnect_attempts: int = Field(default=3, description="Max WebSocket reconnection attempts")
    websocket_heartbeat_interval: int = Field(default=30, description="WebSocket heartbeat interval")


@dataclass
class MCPServerConfig:
    """Complete MCP server configuration."""
    
    # Basic server settings
    server_name: str = "Kraken Trading System"
    server_version: str = "0.1.0"
    description: str = "MCP server for Kraken cryptocurrency trading"
    
    # Security configuration
    security: MCPSecurityConfig = field(default_factory=MCPSecurityConfig)
    
    # Performance configuration  
    performance: MCPPerformanceConfig = field(default_factory=MCPPerformanceConfig)
    
    # Feature flags
    enable_real_trading: bool = field(default=False)  # Start in safe mode
    enable_advanced_orders: bool = field(default=False)  # Advanced order types
    enable_analytics: bool = field(default=True)  # Analytics and reporting
    enable_risk_management: bool = field(default=True)  # Risk checks
    
    # Integration settings
    kraken_api_enabled: bool = field(default=True)
    websocket_enabled: bool = field(default=True)
    order_management_enabled: bool = field(default=True)
    
    def __post_init__(self):
        """Post-initialization validation and setup."""
        
        # Load from environment variables if available
        self._load_from_environment()
        
        # Validate configuration
        self._validate_config()
    
    def _load_from_environment(self):
        """Load configuration from environment variables."""
        
        # Security settings from environment
        if os.getenv("MCP_REQUIRE_AUTH") is not None:
            self.security.require_authentication = os.getenv("MCP_REQUIRE_AUTH").lower() == "true"
        
        if os.getenv("MCP_MAX_ORDER_VALUE"):
            self.security.max_order_value_usd = float(os.getenv("MCP_MAX_ORDER_VALUE"))
        
        if os.getenv("MCP_ENABLE_MARKET_ORDERS"):
            self.security.enable_market_orders = os.getenv("MCP_ENABLE_MARKET_ORDERS").lower() == "true"
        
        # Feature flags from environment
        if os.getenv("MCP_ENABLE_REAL_TRADING"):
            self.enable_real_trading = os.getenv("MCP_ENABLE_REAL_TRADING").lower() == "true"
        
        if os.getenv("MCP_ENABLE_ADVANCED_ORDERS"):
            self.enable_advanced_orders = os.getenv("MCP_ENABLE_ADVANCED_ORDERS").lower() == "true"
    
    def _validate_config(self):
        """Validate configuration settings."""
        
        # Security validations
        if self.security.max_order_value_usd <= 0:
            raise ValueError("Maximum order value must be positive")
        
        if self.security.max_requests_per_minute <= 0:
            raise ValueError("Rate limit must be positive")
        
        # Performance validations
        if self.performance.max_concurrent_connections <= 0:
            raise ValueError("Max concurrent connections must be positive")
        
        # Feature flag validations
        if self.enable_real_trading and not self.enable_risk_management:
            raise ValueError("Real trading requires risk management to be enabled")
    
    def get_capabilities(self) -> Dict[str, Dict[str, bool]]:
        """Get MCP server capabilities based on configuration."""
        
        return {
            "resources": {
                "subscribe": True,
                "listChanged": True
            },
            "tools": {
                "listChanged": True
            },
            "prompts": {
                "listChanged": True
            },
            "logging": {}
        }
    
    def get_server_info(self) -> Dict[str, any]:
        """Get server information for MCP initialization."""
        
        return {
            "name": self.server_name,
            "version": self.server_version,
            "description": self.description,
            "capabilities": self.get_capabilities(),
            "features": {
                "real_trading": self.enable_real_trading,
                "advanced_orders": self.enable_advanced_orders,
                "analytics": self.enable_analytics,
                "risk_management": self.enable_risk_management
            }
        }
    
    def is_operation_allowed(self, operation: str, client_id: Optional[str] = None) -> bool:
        """Check if an operation is allowed based on security configuration."""
        
        # Check authentication requirements
        if self.security.require_authentication and not client_id:
            return False
        
        # Check client allowlist
        if client_id and self.security.allowed_clients and client_id not in self.security.allowed_clients:
            return False
        
        # Check feature flags
        trading_operations = {"place_order", "cancel_order", "modify_order"}
        if operation in trading_operations and not self.enable_real_trading:
            return False
        
        return True
    
    def get_allowed_trading_pairs(self) -> Set[str]:
        """Get the set of allowed trading pairs."""
        return self.security.allowed_trading_pairs
    
    def get_max_order_value(self) -> float:
        """Get maximum allowed order value in USD."""
        return self.security.max_order_value_usd


# Create default configuration instance
default_mcp_config = MCPServerConfig()