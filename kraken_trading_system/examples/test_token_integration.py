#!/usr/bin/env python3
"""
Integration test script for Kraken WebSocket Token Manager.
This script tests the token management functionality without making real API calls.
"""

import asyncio
import sys
import os
from pathlib import Path
from unittest.mock import patch

# Add src to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from trading_systems.exchanges.kraken.token_manager import (
    KrakenTokenManager,
    WebSocketToken,
    get_token_manager,
    cleanup_token_manager
)
from trading_systems.config.settings import settings
from trading_systems.utils.logger import get_logger
from datetime import datetime, timedelta


class MockKrakenAPI:
    """Mock Kraken API for testing without real credentials."""

    def __init__(self):
        self.call_count = 0
        self.should_fail = False
        self.error_type = None

    async def mock_token_request(self, *args, **kwargs):
        """Mock token request that simulates Kraken API response."""
        self.call_count += 1

        if self.should_fail:
            if self.error_type == "auth":
                response_data = {
                    "error": ["EGeneral:Permission denied"]
                }
            elif self.error_type == "network":
                raise Exception("Network error")
            else:
                response_data = {
                    "error": ["EGeneral:Invalid arguments"]
                }
        else:
            response_data = {
                "error": [],
                "result": {
                    "token": f"mock_token_{self.call_count}_{int(datetime.now().timestamp())}"
                }
            }

        # Create mock response object
        class MockResponse:
            def __init__(self, data):
                self.status_code = 200
                self._data = data

            def json(self):
                return self._data

        return MockResponse(response_data)


async def test_token_creation_and_expiry():
    """Test WebSocket token creation and expiry logic."""
    logger = get_logger("TokenTest")
    logger.info("Testing WebSocket token creation and expiry...")

    # Test token creation
    now = datetime.now()
    token = WebSocketToken(
        token="test_token_123",
        created_at=now,
        expires_at=now + timedelta(minutes=15)
    )

    assert token.token == "test_token_123"
    assert not token.is_expired
    assert not token.should_refresh
    logger.info("✅ Token creation test passed")

    # Test expiry logic
    expired_token = WebSocketToken(
        token="expired_token",
        created_at=now - timedelta(minutes=20),
        expires_at=now - timedelta(minutes=5)
    )

    assert expired_token.is_expired
    logger.info("✅ Token expiry test passed")

    # Test refresh logic
    refresh_token = WebSocketToken(
        token="refresh_token",
        created_at=now - timedelta(minutes=14),
        expires_at=now + timedelta(minutes=1)
    )

    assert refresh_token.should_refresh
    assert not refresh_token.is_expired
    logger.info("✅ Token refresh logic test passed")


async def test_token_manager_basic():
    """Test basic token manager functionality."""
    logger = get_logger("TokenManagerTest")
    logger.info("Testing token manager basic functionality...")

    # Create token manager
    token_manager = KrakenTokenManager()

    # Test initialization
    assert token_manager._current_token is None
    logger.info("✅ Token manager initialization test passed")

    # Test status with no token
    status = token_manager.get_token_status()
    assert not status["has_token"]
    logger.info("✅ Token status (no token) test passed")

    # Test signature creation
    try:
        import base64
        api_secret = base64.b64encode(b"test_secret").decode('utf-8')
        signature = token_manager._create_signature(
            api_secret, "/0/private/GetWebSocketsToken", "12345", "nonce=12345"
        )
        assert isinstance(signature, str)
        assert len(signature) > 0
        logger.info("✅ Signature creation test passed")
    except Exception as e:
        logger.error(f"❌ Signature creation test failed: {e}")
        raise


async def test_token_manager_with_mock_api():
    """Test token manager with mocked API calls."""
    logger = get_logger("TokenManagerMockTest")
    logger.info("Testing token manager with mocked API...")

    # Create mock API
    mock_api = MockKrakenAPI()

    # Create token manager and mock the HTTP client
    token_manager = KrakenTokenManager()

    # Mock settings to provide test credentials
    import base64
    from unittest.mock import patch
    test_credentials = ("test_api_key", base64.b64encode(b"test_secret").decode('utf-8'))

    # Use proper patching for Pydantic v2
    with patch.object(settings, 'get_api_credentials', return_value=test_credentials):
        async with token_manager:
            # Mock the HTTP client's post method
            original_post = token_manager._http_client.post
            token_manager._http_client.post = mock_api.mock_token_request

            # Test successful token request
            token = await token_manager.get_websocket_token()
            assert token.startswith("mock_token_1_")
            assert mock_api.call_count == 1
            logger.info("✅ Successful token request test passed")

            # Test token caching (should not make another API call)
            token2 = await token_manager.get_websocket_token()
            assert token == token2
            assert mock_api.call_count == 1  # No additional calls
            logger.info("✅ Token caching test passed")

            # Test force refresh
            token3 = await token_manager.get_websocket_token(force_refresh=True)
            assert token3.startswith("mock_token_2_")
            assert mock_api.call_count == 2
            logger.info("✅ Force refresh test passed")

            # Test token status with active token
            status = token_manager.get_token_status()
            assert status["has_token"]
            assert not status["is_expired"]
            assert status["is_valid"]
            logger.info("✅ Token status (with token) test passed")

            # Test token invalidation
            await token_manager.invalidate_token()
            status = token_manager.get_token_status()
            assert not status["is_valid"]
            logger.info("✅ Token invalidation test passed")

            # Restore original post method
            token_manager._http_client.post = original_post


async def test_error_handling():
    """Test error handling in token manager."""
    logger = get_logger("TokenErrorTest")
    logger.info("Testing error handling...")

    # Test with no credentials
    token_manager = KrakenTokenManager()

    # Mock settings to return no credentials using proper patching
    from unittest.mock import patch

    with patch.object(settings, 'get_api_credentials', return_value=(None, None)):
        from trading_systems.utils.exceptions import InvalidCredentialsError

        try:
            await token_manager.get_websocket_token()
            assert False, "Should have raised InvalidCredentialsError"
        except InvalidCredentialsError:
            logger.info("✅ No credentials error handling test passed")


async def test_global_token_manager():
    """Test global token manager functionality."""
    logger = get_logger("GlobalTokenManagerTest")
    logger.info("Testing global token manager...")

    # Clean up any existing instance
    await cleanup_token_manager()

    # Get global instance
    manager1 = await get_token_manager()
    assert isinstance(manager1, KrakenTokenManager)
    logger.info("✅ Global token manager creation test passed")

    # Should return same instance
    manager2 = await get_token_manager()
    assert manager1 is manager2
    logger.info("✅ Global token manager singleton test passed")

    # Test cleanup
    await cleanup_token_manager()
    logger.info("✅ Global token manager cleanup test passed")


async def main():
    """Run all token manager tests."""
    logger = get_logger("TokenManagerIntegrationTest")

    print("=" * 70)
    print("🧪 Kraken WebSocket Token Manager Integration Tests")
    print("=" * 70)
    print()

    try:
        # Run all tests
        await test_token_creation_and_expiry()
        await test_token_manager_basic()
        await test_token_manager_with_mock_api()
        await test_error_handling()
        await test_global_token_manager()

        print()
        print("🎉 ALL TOKEN MANAGER TESTS PASSED!")
        print("✅ Token creation and expiry logic working")
        print("✅ Token manager basic functionality working")
        print("✅ Mocked API integration working")
        print("✅ Error handling working")
        print("✅ Global token manager working")

    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)

    print("\n" + "=" * 70)
    print("🔧 Token Manager is ready for Subtask 2.1.B implementation!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
