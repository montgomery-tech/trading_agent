"""
Unit tests for the Kraken WebSocket Token Manager.
"""

import asyncio
import base64
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

import httpx

from src.trading_systems.exchanges.kraken.token_manager import (
    KrakenTokenManager,
    WebSocketToken,
    get_token_manager,
    cleanup_token_manager
)
from src.trading_systems.utils.exceptions import (
    AuthenticationError,
    InvalidCredentialsError
)


class TestWebSocketToken:
    """Test cases for WebSocketToken dataclass."""

    def test_token_creation(self):
        """Test creating a WebSocket token."""
        now = datetime.now()
        expires = now + timedelta(minutes=15)

        token = WebSocketToken(
            token="test_token_123",
            created_at=now,
            expires_at=expires
        )

        assert token.token == "test_token_123"
        assert token.created_at == now
        assert token.expires_at == expires
        assert token.is_valid is True
        assert token.is_expired is False

    def test_token_expiry_check(self):
        """Test token expiry checking."""
        now = datetime.now()

        # Create expired token
        expired_token = WebSocketToken(
            token="expired_token",
            created_at=now - timedelta(minutes=20),
            expires_at=now - timedelta(minutes=5)
        )

        assert expired_token.is_expired is True
        assert expired_token.time_until_expiry.total_seconds() < 0

    def test_token_refresh_check(self):
        """Test token refresh logic."""
        now = datetime.now()

        # Token that should be refreshed (expires in 1 minute)
        refresh_token = WebSocketToken(
            token="refresh_token",
            created_at=now - timedelta(minutes=14),
            expires_at=now + timedelta(minutes=1)
        )

        assert refresh_token.should_refresh is True
        assert refresh_token.is_expired is False


class TestKrakenTokenManager:
    """Test cases for KrakenTokenManager."""

    @pytest.fixture
    def token_manager(self):
        """Create a token manager instance for testing."""
        return KrakenTokenManager()

    @pytest.fixture
    def mock_settings(self):
        """Mock settings with test API credentials."""
        with patch('src.trading_systems.exchanges.kraken.token_manager.settings') as mock:
            mock.get_api_credentials.return_value = ("test_key", "dGVzdF9zZWNyZXQ=")  # base64 'test_secret'
            yield mock

    @pytest.mark.asyncio
    async def test_token_manager_initialization(self, token_manager):
        """Test token manager initialization."""
        assert token_manager._current_token is None
        assert token_manager._http_client is None
        assert token_manager.rest_api_base == "https://api.kraken.com"
        assert token_manager.token_endpoint == "/0/private/GetWebSocketsToken"

    @pytest.mark.asyncio
    async def test_context_manager(self, token_manager):
        """Test async context manager functionality."""
        async with token_manager as tm:
            assert tm._http_client is not None
            assert isinstance(tm._http_client, httpx.AsyncClient)

        # Client should be closed after exiting context
        assert token_manager._http_client is None

    @pytest.mark.asyncio
    async def test_signature_creation(self, token_manager):
        """Test API signature creation."""
        api_secret = base64.b64encode(b"test_secret").decode('utf-8')
        api_path = "/0/private/GetWebSocketsToken"
        nonce = "1234567890"
        post_data = "nonce=1234567890"

        signature = token_manager._create_signature(api_secret, api_path, nonce, post_data)

        assert isinstance(signature, str)
        assert len(signature) > 0
        # Signature should be base64 encoded
        try:
            base64.b64decode(signature)
        except Exception:
            pytest.fail("Signature should be valid base64")

    @pytest.mark.asyncio
    async def test_get_token_no_credentials(self, token_manager):
        """Test token request with no credentials."""
        with patch('src.trading_systems.exchanges.kraken.token_manager.settings') as mock_settings:
            mock_settings.get_api_credentials.return_value = (None, None)

            with pytest.raises(InvalidCredentialsError, match="API credentials not configured"):
                await token_manager.get_websocket_token()

    @pytest.mark.asyncio
    async def test_successful_token_request(self, token_manager, mock_settings):
        """Test successful token request."""
        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "error": [],
            "result": {
                "token": "WW91ciBhdXRoZW50aWNhdGlvbiB0b2tlbiBnb2VzIGhlcmUu"
            }
        }

        # Mock HTTP client
        mock_http_client = AsyncMock()
        mock_http_client.post.return_value = mock_response

        with patch.object(token_manager, '_http_client', mock_http_client):
            token = await token_manager.get_websocket_token()

            assert token == "WW91ciBhdXRoZW50aWNhdGlvbiB0b2tlbiBnb2VzIGhlcmUu"
            assert token_manager._current_token is not None
            assert token_manager._current_token.token == token
            assert not token_manager._current_token.is_expired

    @pytest.mark.asyncio
    async def test_token_request_api_error(self, token_manager, mock_settings):
        """Test token request with API error."""
        # Mock HTTP response with API error
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "error": ["EGeneral:Invalid arguments", "EGeneral:Permission denied"]
        }

        mock_http_client = AsyncMock()
        mock_http_client.post.return_value = mock_response

        with patch.object(token_manager, '_http_client', mock_http_client):
            with pytest.raises(InvalidCredentialsError, match="Invalid API credentials"):
                await token_manager.get_websocket_token()

    @pytest.mark.asyncio
    async def test_token_request_http_error(self, token_manager, mock_settings):
        """Test token request with HTTP error."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"

        mock_http_client = AsyncMock()
        mock_http_client.post.return_value = mock_response

        with patch.object(token_manager, '_http_client', mock_http_client):
            with pytest.raises(AuthenticationError, match="Token request failed with status 401"):
                await token_manager.get_websocket_token()

    @pytest.mark.asyncio
    async def test_token_request_network_error(self, token_manager, mock_settings):
        """Test token request with network error."""
        mock_http_client = AsyncMock()
        mock_http_client.post.side_effect = httpx.ConnectError("Connection failed")

        with patch.object(token_manager, '_http_client', mock_http_client):
            with pytest.raises(AuthenticationError, match="Network error during token request"):
                await token_manager.get_websocket_token()

    @pytest.mark.asyncio
    async def test_token_caching(self, token_manager, mock_settings):
        """Test that tokens are cached and reused."""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "error": [],
            "result": {"token": "cached_token_123"}
        }

        mock_http_client = AsyncMock()
        mock_http_client.post.return_value = mock_response

        with patch.object(token_manager, '_http_client', mock_http_client):
            # First request should make HTTP call
            token1 = await token_manager.get_websocket_token()
            assert mock_http_client.post.call_count == 1

            # Second request should use cached token
            token2 = await token_manager.get_websocket_token()
            assert mock_http_client.post.call_count == 1  # No additional calls
            assert token1 == token2

    @pytest.mark.asyncio
    async def test_force_refresh(self, token_manager, mock_settings):
        """Test forcing token refresh."""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "error": [],
            "result": {"token": "refreshed_token_456"}
        }

        mock_http_client = AsyncMock()
        mock_http_client.post.return_value = mock_response

        with patch.object(token_manager, '_http_client', mock_http_client):
            # Get initial token
            await token_manager.get_websocket_token()
            assert mock_http_client.post.call_count == 1

            # Force refresh should make new HTTP call
            await token_manager.get_websocket_token(force_refresh=True)
            assert mock_http_client.post.call_count == 2

    @pytest.mark.asyncio
    async def test_token_invalidation(self, token_manager):
        """Test token invalidation."""
        # Create a mock token
        now = datetime.now()
        token_manager._current_token = WebSocketToken(
            token="test_token",
            created_at=now,
            expires_at=now + timedelta(minutes=15)
        )

        assert token_manager._current_token.is_valid is True

        # Invalidate token
        await token_manager.invalidate_token()

        assert token_manager._current_token.is_valid is False

    def test_token_status_no_token(self, token_manager):
        """Test getting status when no token exists."""
        status = token_manager.get_token_status()

        assert status["has_token"] is False
        assert status["is_expired"] is None
        assert status["time_until_expiry"] is None
        assert status["should_refresh"] is None

    def test_token_status_with_token(self, token_manager):
        """Test getting status with active token."""
        now = datetime.now()
        token_manager._current_token = WebSocketToken(
            token="test_token",
            created_at=now,
            expires_at=now + timedelta(minutes=10)
        )

        status = token_manager.get_token_status()

        assert status["has_token"] is True
        assert status["is_expired"] is False
        assert status["time_until_expiry"] > 0
        assert status["should_refresh"] is False
        assert "created_at" in status
        assert "expires_at" in status
        assert status["is_valid"] is True


class TestGlobalTokenManager:
    """Test global token manager functionality."""

    @pytest.mark.asyncio
    async def test_get_global_token_manager(self):
        """Test getting global token manager instance."""
        # Clean up any existing instance
        await cleanup_token_manager()

        # Get instance
        manager1 = await get_token_manager()
        assert isinstance(manager1, KrakenTokenManager)

        # Should return same instance
        manager2 = await get_token_manager()
        assert manager1 is manager2

        # Clean up
        await cleanup_token_manager()

    @pytest.mark.asyncio
    async def test_cleanup_token_manager(self):
        """Test cleanup of global token manager."""
        # Get instance
        manager = await get_token_manager()
        assert manager._http_client is not None

        # Clean up
        await cleanup_token_manager()

        # Should be cleaned up
        # Note: We can't directly test the global variable,
        # but the next get_token_manager call should create a new instance
        new_manager = await get_token_manager()
        # This should be a fresh instance with fresh HTTP client
        assert new_manager._http_client is not None

        # Final cleanup
        await cleanup_token_manager()


# Integration test with mock Kraken API
@pytest.mark.asyncio
async def test_token_manager_integration():
    """Integration test with mocked Kraken API."""
    token_manager = KrakenTokenManager()

    # Mock settings
    with patch('src.trading_systems.exchanges.kraken.token_manager.settings') as mock_settings:
        mock_settings.get_api_credentials.return_value = ("test_key", "dGVzdF9zZWNyZXQ=")

        # Mock successful token response
        mock_response_data = {
            "error": [],
            "result": {
                "token": "integration_test_token_789"
            }
        }

        async with token_manager:
            with patch.object(token_manager._http_client, 'post') as mock_post:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = mock_response_data
                mock_post.return_value = mock_response

                # Test complete flow
                token = await token_manager.get_websocket_token()

                assert token == "integration_test_token_789"
                assert token_manager._current_token is not None

                # Verify request was made correctly
                mock_post.assert_called_once()
                call_args = mock_post.call_args

                # Check URL
                assert call_args[1]['url'] == "https://api.kraken.com/0/private/GetWebSocketsToken"

                # Check headers
                headers = call_args[1]['headers']
                assert 'API-Key' in headers
                assert 'API-Sign' in headers
                assert headers['Content-Type'] == 'application/x-www-form-urlencoded'

                # Check POST data
                post_data = call_args[1]['data']
                assert 'nonce=' in post_data

                # Test status
                status = token_manager.get_token_status()
                assert status['has_token'] is True
                assert status['is_valid'] is True
