# src/trading_systems/mcp_server/__init__.py
"""
MCP Server module for Kraken Trading System.

This module provides the Model Context Protocol server implementation
that exposes trading system capabilities to AI clients like Claude.
"""

from .main import main, mcp
from .config import MCPServerConfig, MCPSecurityConfig, MCPPerformanceConfig
from .trading_adapter import TradingSystemAdapter, TradingSystemStatus

__all__ = [
    "main",
    "mcp", 
    "MCPServerConfig",
    "MCPSecurityConfig",
    "MCPPerformanceConfig",
    "TradingSystemAdapter",
    "TradingSystemStatus"
]

__version__ = "0.1.0"