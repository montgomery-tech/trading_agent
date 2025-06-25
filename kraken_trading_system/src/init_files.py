# src/__init__.py
"""Kraken Trading System - Root package."""

# src/trading_system/__init__.py
"""
Kraken Trading System

A Python-based MCP server for Kraken exchange WebSocket integration.
"""

__version__ = "0.1.0"
__author__ = "Trading System Team"

from .config.settings import settings
from .utils.logger import get_logger, setup_logging

# Initialize logging on package import
setup_logging()

__all__ = ["settings", "get_logger", "setup_logging"]


# src/trading_system/config/__init__.py
"""Configuration module."""

from .settings import settings, Settings

__all__ = ["settings", "Settings"]


# src/trading_system/exchanges/__init__.py
"""Exchange integrations."""

# src/trading_system/exchanges/kraken/__init__.py
"""Kraken exchange integration."""

# src/trading_system/market_data/__init__.py
"""Market data processing."""

# src/trading_system/orders/__init__.py
"""Order management."""

# src/trading_system/risk/__init__.py
"""Risk management."""

# src/trading_system/utils/__init__.py
"""Utility functions and classes."""

from .logger import get_logger, LoggerMixin, setup_logging
from .exceptions import (
    TradingSystemError,
    WebSocketError,
    ConnectionError,
    AuthenticationError,
    OrderError,
    RiskManagementError,
    MarketDataError,
    ConfigurationError,
    ExchangeError,
    handle_kraken_error,
)

__all__ = [
    "get_logger",
    "LoggerMixin", 
    "setup_logging",
    "TradingSystemError",
    "WebSocketError",
    "ConnectionError",
    "AuthenticationError",
    "OrderError",
    "RiskManagementError",
    "MarketDataError",
    "ConfigurationError",
    "ExchangeError",
    "handle_kraken_error",
]


# tests/__init__.py
"""Test package."""

# tests/unit/__init__.py
"""Unit tests."""

# tests/integration/__init__.py
"""Integration tests."""

# examples/__init__.py
"""Usage examples."""