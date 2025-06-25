"""
Pytest configuration and fixtures for the trading system tests.
"""

import asyncio
import os
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from dotenv import load_dotenv

# Load test environment variables
load_dotenv(".env.test", override=True)


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_websocket():
    """Mock WebSocket connection for testing."""
    mock_ws = AsyncMock()
    mock_ws.send = AsyncMock()
    mock_ws.recv = AsyncMock()
    mock_ws.close = AsyncMock()
    mock_ws.closed = False
    return mock_ws


@pytest.fixture
def mock_kraken_response():
    """Mock Kraken API response data."""
    return {
        "connectionID": 12345,
        "event": "systemStatus",
        "status": "online",
        "version": "1.9.0"
    }


@pytest.fixture
def mock_ticker_data():
    """Mock ticker data from Kraken."""
    return {
        "channelID": 1001,
        "channelName": "ticker",
        "event": "subscriptionStatus",
        "pair": "XBT/USD",
        "status": "subscribed",
        "subscription": {"name": "ticker"}
    }


@pytest.fixture
def mock_order_data():
    """Mock order data for testing."""
    return {
        "pair": "XBT/USD",
        "type": "buy",
        "ordertype": "limit",
        "volume": "0.01",
        "price": "50000.00",
        "oflags": "fciq"
    }


@pytest.fixture
def test_settings():
    """Test settings with safe defaults."""
    from src.trading_system.config.settings import Settings
    
    return Settings(
        kraken_api_key="test_api_key",
        kraken_api_secret="test_api_secret",
        use_sandbox=True,
        max_position_size=0.1,
        max_order_value=1000.0,
        log_level="DEBUG",
        environment="test"
    )


@pytest.fixture
def mock_logger():
    """Mock logger for testing."""
    return MagicMock()


@pytest_asyncio.fixture
async def mock_websocket_client():
    """Mock WebSocket client for testing."""
    from unittest.mock import AsyncMock
    
    client = AsyncMock()
    client.connect = AsyncMock()
    client.disconnect = AsyncMock()
    client.send_message = AsyncMock()
    client.subscribe = AsyncMock()
    client.unsubscribe = AsyncMock()
    client.is_connected = True
    
    return client


@pytest.fixture(autouse=True)
def reset_settings():
    """Reset settings before each test."""
    # Set test environment variables
    test_env = {
        "KRAKEN_API_KEY": "test_key",
        "KRAKEN_API_SECRET": "test_secret",
        "USE_SANDBOX": "true",
        "LOG_LEVEL": "DEBUG",
        "ENVIRONMENT": "test"
    }
    
    for key, value in test_env.items():
        os.environ[key] = value
    
    yield
    
    # Cleanup
    for key in test_env.keys():
        os.environ.pop(key, None)


# Async test markers
pytestmark = pytest.mark.asyncio


class AsyncContextManagerMock:
    """Mock async context manager for testing."""
    
    def __init__(self, return_value=None):
        self.return_value = return_value
    
    async def __aenter__(self):
        return self.return_value
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


@pytest.fixture
def async_context_mock():
    """Create an async context manager mock."""
    return AsyncContextManagerMock
