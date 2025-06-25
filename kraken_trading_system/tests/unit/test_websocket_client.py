"""
Unit tests for the Kraken WebSocket client.
"""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from websockets.exceptions import ConnectionClosed

from src.trading_system.exchanges.kraken.websocket_client import KrakenWebSocketClient
from src.trading_system.utils.exceptions import ConnectionError, WebSocketError


class TestKrakenWebSocketClient:
    """Test cases for KrakenWebSocketClient."""

    @pytest.fixture
    def client(self):
        """Create a WebSocket client instance for testing."""
        return KrakenWebSocketClient()

    @pytest.fixture
    def mock_websocket(self):
        """Mock WebSocket connection."""
        mock_ws = AsyncMock()
        mock_ws.closed = False
        mock_ws.send = AsyncMock()
        mock_ws.close = AsyncMock()
        return mock_ws

    def test_client_initialization(self, client):
        """Test client initializes with correct default values."""
        assert not client.is_public_connected
        assert not client.is_private_connected
        assert client.public_ws is None
        assert client.private_ws is None
        assert len(client.public_subscriptions) == 0
        assert len(client.private_subscriptions) == 0
        assert client.reconnect_attempts == 0
        assert client.next_req_id == 1
        assert client.ssl_context is not None

    @pytest.mark.asyncio
    async def test_connect_public_success(self, client, mock_websocket):
        """Test successful public WebSocket connection."""
        with patch('websockets.connect', return_value=mock_websocket) as mock_connect:
            # Mock the message handler task
            with patch.object(client, '_handle_public_messages'):
                with patch.object(client, '_heartbeat_monitor'):
                    await client.connect_public()

        assert client.is_public_connected
        assert client.public_ws == mock_websocket
        assert client.reconnect_attempts == 0
        mock_connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_public_already_connected(self, client):
        """Test connecting when already connected."""
        client.is_public_connected = True

        with patch('websockets.connect') as mock_connect:
            await client.connect_public()

        mock_connect.assert_not_called()

    @pytest.mark.asyncio
    async def test_connect_public_retry_on_failure(self, client):
        """Test retry logic on connection failure."""
        # First attempt fails, second succeeds
        mock_websocket = AsyncMock()

        with patch('websockets.connect') as mock_connect:
            mock_connect.side_effect = [ConnectionError("Connection failed"), mock_websocket]

            with patch.object(client, '_handle_public_messages'):
                with patch.object(client, '_heartbeat_monitor'):
                    with patch('asyncio.sleep'):  # Speed up the test
                        await client.connect_public()

        assert client.is_public_connected
        assert mock_connect.call_count == 2

    @pytest.mark.asyncio
    async def test_connect_public_max_retries_exceeded(self, client):
        """Test failure after max retries exceeded."""
        with patch('websockets.connect', side_effect=ConnectionError("Connection failed")):
            with patch('asyncio.sleep'):  # Speed up the test
                with pytest.raises(ConnectionError, match="Failed to connect"):
                    await client.connect_public()

        assert not client.is_public_connected

    @pytest.mark.asyncio
    async def test_connect_private_not_implemented(self, client):
        """Test that private connection raises NotImplementedError."""
        with pytest.raises(NotImplementedError):
            await client.connect_private()

    @pytest.mark.asyncio
    async def test_disconnect_public(self, client, mock_websocket):
        """Test disconnecting from public WebSocket."""
        client.public_ws = mock_websocket
        client.is_public_connected = True

        await client.disconnect("public")

        assert not client.is_public_connected
        assert client.public_ws is None
        mock_websocket.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect_all(self, client, mock_websocket):
        """Test disconnecting from all WebSockets."""
        client.public_ws = mock_websocket
        client.is_public_connected = True

        await client.disconnect()

        assert not client.is_public_connected
        assert not client.is_private_connected
        assert client.public_ws is None
        mock_websocket.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_public_message_success(self, client, mock_websocket):
        """Test sending message to public WebSocket."""
        client.public_ws = mock_websocket
        client.is_public_connected = True

        message = {"event": "subscribe", "subscription": {"name": "ticker"}}
        await client.send_public_message(message)

        expected_json = json.dumps(message)
        mock_websocket.send.assert_called_once_with(expected_json)

    @pytest.mark.asyncio
    async def test_send_public_message_not_connected(self, client):
        """Test sending message when not connected raises error."""
        with pytest.raises(WebSocketError, match="Public WebSocket not connected"):
            await client.send_public_message({"event": "test"})

    @pytest.mark.asyncio
    async def test_send_private_message_not_implemented(self, client):
        """Test that private message sending raises NotImplementedError."""
        with pytest.raises(NotImplementedError):
            await client.send_private_message({"event": "test"})

    @pytest.mark.asyncio
    async def test_process_system_status_message(self, client):
        """Test processing system status message."""
        message = {
            "event": "systemStatus",
            "connectionID": 12345,
            "status": "online",
            "version": "1.9.0"
        }

        # This should not raise any exceptions
        await client._process_public_message(message)

        # Verify heartbeat was updated
        assert client.last_heartbeat > 0

    @pytest.mark.asyncio
    async def test_process_subscription_status_message(self, client):
        """Test processing subscription status message."""
        message = {
            "event": "subscriptionStatus",
            "channelID": 1001,
            "channelName": "ticker",
            "pair": "XBT/USD",
            "status": "subscribed",
            "subscription": {"name": "ticker"}
        }

        await client._process_public_message(message)

        # Verify subscription was added
        assert "ticker:XBT/USD" in client.public_subscriptions
        assert client.subscription_ids["ticker:XBT/USD"] == 1001

    @pytest.mark.asyncio
    async def test_process_unsubscription_status_message(self, client):
        """Test processing unsubscription status message."""
        # First add a subscription
        client.public_subscriptions.add("ticker:XBT/USD")
        client.subscription_ids["ticker:XBT/USD"] = 1001

        message = {
            "event": "subscriptionStatus",
            "channelID": 1001,
            "channelName": "ticker",
            "pair": "XBT/USD",
            "status": "unsubscribed",
            "subscription": {"name": "ticker"}
        }

        await client._process_public_message(message)

        # Verify subscription was removed
        assert "ticker:XBT/USD" not in client.public_subscriptions
        assert "ticker:XBT/USD" not in client.subscription_ids

    @pytest.mark.asyncio
    async def test_process_heartbeat_message(self, client):
        """Test processing heartbeat message."""
        old_heartbeat = client.last_heartbeat

        message = {"event": "heartbeat"}
        await client._process_public_message(message)

        # Verify heartbeat was updated
        assert client.last_heartbeat > old_heartbeat

    @pytest.mark.asyncio
    async def test_process_error_message(self, client):
        """Test processing error message raises appropriate exception."""
        message = {
            "errorMessage": "Invalid subscription",
            "error": ["EQuery:Unknown asset pair"]
        }

        with pytest.raises(Exception):  # Should raise a Kraken-specific error
            await client._process_public_message(message)

    def test_get_connection_status(self, client):
        """Test getting connection status."""
        client.is_public_connected = True
        client.public_subscriptions.add("ticker:XBT/USD")
        client.last_heartbeat = 1234567890

        status = client.get_connection_status()

        assert status["public_connected"] is True
        assert status["private_connected"] is False
        assert "ticker:XBT/USD" in status["public_subscriptions"]
        assert status["last_heartbeat"] == 1234567890
        assert status["reconnect_attempts"] == 0
        assert "ssl_verify_mode" in status
        assert "ssl_check_hostname" in status

    @pytest.mark.asyncio
    async def test_handle_connection_closed(self, client):
        """Test handling connection closed during message processing."""
        mock_websocket = AsyncMock()
        mock_websocket.__aiter__.side_effect = ConnectionClosed(None, None)

        client.public_ws = mock_websocket
        client.is_public_connected = True

        with patch.object(client, '_handle_reconnection') as mock_reconnect:
            await client._handle_public_messages()

        assert not client.is_public_connected
        mock_reconnect.assert_called_once_with("public")

    @pytest.mark.asyncio
    async def test_listen_public_yields_messages(self, client):
        """Test listening for public messages yields queued messages."""
        client.is_public_connected = True

        # Add messages to queue
        test_message = {"event": "test", "data": "test_data"}
        await client.public_message_queue.put(test_message)

        # Listen for one message
        messages = []
        async for message in client.listen_public():
            messages.append(message)
            break  # Only get one message for test

        assert len(messages) == 1
        assert messages[0] == test_message

    @pytest.mark.asyncio
    async def test_listen_public_timeout_handling(self, client):
        """Test listening handles timeout gracefully."""
        client.is_public_connected = True

        # Start listening (should timeout since no messages)
        timeout_task = asyncio.create_task(self._collect_messages_with_timeout(client))

        # Let it run briefly then stop
        await asyncio.sleep(0.1)
        client.is_public_connected = False

        messages = await timeout_task
        assert len(messages) == 0  # No messages should be collected

    async def _collect_messages_with_timeout(self, client):
        """Helper to collect messages with timeout."""
        messages = []
        try:
            async for message in client.listen_public():
                messages.append(message)
                if len(messages) >= 5:  # Limit collection
                    break
        except Exception:
            pass
        return messages
