"""
Kraken WebSocket client for real-time market data and trading operations.
"""

import asyncio
import json
import ssl
import time
from typing import Any, AsyncGenerator, Dict, List, Optional, Set
from urllib.parse import urlparse

import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException

from ...config.settings import settings
from ...utils.exceptions import (
    ConnectionError,
    WebSocketError,
    handle_kraken_error,
)
from ...utils.logger import LoggerMixin, log_websocket_event


class KrakenWebSocketClient(LoggerMixin):
    """
    Kraken WebSocket client for handling public and private connections.

    This client manages WebSocket connections to Kraken's public and private
    WebSocket endpoints, handling subscriptions, message routing, and reconnection logic.
    """

    def __init__(self):
        super().__init__()
        self.public_ws: Optional[websockets.WebSocketServerProtocol] = None
        self.private_ws: Optional[websockets.WebSocketServerProtocol] = None
        self.is_public_connected = False
        self.is_private_connected = False

        # Connection management
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = settings.max_reconnect_attempts
        self.reconnect_delay = settings.reconnect_delay
        self.connection_timeout = settings.websocket_timeout

        # SSL context for handling certificate issues (especially on macOS)
        self.ssl_context = self._create_ssl_context()

        # Subscription management
        self.public_subscriptions: Set[str] = set()
        self.private_subscriptions: Set[str] = set()
        self.subscription_ids: Dict[str, int] = {}
        self.next_req_id = 1

        # Message queues for processing
        self.public_message_queue: asyncio.Queue = asyncio.Queue()
        self.private_message_queue: asyncio.Queue = asyncio.Queue()

        # Heartbeat management
        self.last_heartbeat = time.time()
        self.heartbeat_interval = 30  # seconds

        # Get URLs from settings
        self.public_url, self.private_url = settings.get_websocket_urls()

        log_websocket_event(
            self.logger,
            "client_initialized",
            public_url=self.public_url,
            private_url=self.private_url,
            ssl_context_type=type(self.ssl_context).__name__
        )

    def _create_ssl_context(self) -> ssl.SSLContext:
        """
        Create SSL context with proper certificate handling.

        This handles SSL certificate verification issues common on macOS
        by providing automatic fallback to relaxed SSL settings for development.

        Returns:
            SSL context configured for WebSocket connections
        """
        try:
            # Create SSL context based on settings
            ssl_context = ssl.create_default_context()

            # Apply SSL settings from configuration
            if not settings.ssl_verify_certificates:
                ssl_context.verify_mode = ssl.CERT_NONE
                self.log_info("SSL certificate verification disabled via settings")

            if not settings.ssl_check_hostname:
                ssl_context.check_hostname = False
                self.log_info("SSL hostname checking disabled via settings")

            self.log_info(
                "Created SSL context",
                verify_mode=ssl_context.verify_mode.name if hasattr(ssl_context.verify_mode, 'name') else str(ssl_context.verify_mode),
                check_hostname=ssl_context.check_hostname
            )
            return ssl_context

        except Exception as e:
            self.log_warning(
                "SSL context creation failed, using fallback",
                error=str(e)
            )

            # Fallback for certificate issues (common on macOS)
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

            self.log_info("Created fallback SSL context (certificate verification disabled)")
            return ssl_context

    async def connect_public(self) -> None:
        """
        Connect to Kraken's public WebSocket endpoint.

        Raises:
            ConnectionError: If connection fails after retries
        """
        if self.is_public_connected:
            self.log_info("Public WebSocket already connected")
            return

        await self._connect_with_retry(endpoint="public")

    async def connect_private(self) -> None:
        """
        Connect to Kraken's private WebSocket endpoint.

        Note: This requires API credentials and authentication.

        Raises:
            ConnectionError: If connection fails after retries
            AuthenticationError: If authentication fails
        """
        if self.is_private_connected:
            self.log_info("Private WebSocket already connected")
            return

        # TODO: Implement authentication in next task
        raise NotImplementedError("Private WebSocket connection requires authentication")

    async def _connect_with_retry(self, endpoint: str) -> None:
        """
        Connect to WebSocket with retry logic.

        Args:
            endpoint: Either "public" or "private"
        """
        url = self.public_url if endpoint == "public" else self.private_url

        for attempt in range(self.max_reconnect_attempts):
            try:
                log_websocket_event(
                    self.logger,
                    "connection_attempt",
                    endpoint=endpoint,
                    attempt=attempt + 1,
                    url=url
                )

                # Connect to WebSocket with SSL context
                ws = await asyncio.wait_for(
                    websockets.connect(
                        url,
                        ssl=self.ssl_context,
                        ping_interval=None,  # We'll handle heartbeat manually
                        ping_timeout=None
                    ),
                    timeout=self.connection_timeout
                )

                if endpoint == "public":
                    self.public_ws = ws
                    self.is_public_connected = True
                else:
                    self.private_ws = ws
                    self.is_private_connected = True

                self.reconnect_attempts = 0
                self.last_heartbeat = time.time()

                log_websocket_event(
                    self.logger,
                    "connection_established",
                    endpoint=endpoint,
                    url=url
                )

                # Start message handling task
                if endpoint == "public":
                    asyncio.create_task(self._handle_public_messages())
                    asyncio.create_task(self._heartbeat_monitor())

                return

            except (ConnectionClosed, WebSocketException, OSError) as e:
                self.log_error(
                    f"Connection attempt {attempt + 1} failed",
                    error=e,
                    endpoint=endpoint
                )

                # Handle SSL errors with automatic retry using relaxed settings
                if "SSL" in str(e) or "certificate" in str(e):
                    self.log_info("SSL error detected, retrying with relaxed SSL settings")
                    if await self._retry_with_relaxed_ssl(url, endpoint, attempt):
                        return

                if attempt < self.max_reconnect_attempts - 1:
                    await asyncio.sleep(self.reconnect_delay * (2 ** attempt))  # Exponential backoff
                else:
                    raise ConnectionError(
                        f"Failed to connect to {endpoint} WebSocket after {self.max_reconnect_attempts} attempts",
                        details={"endpoint": endpoint, "url": url}
                    )

    async def _retry_with_relaxed_ssl(self, url: str, endpoint: str, attempt: int) -> bool:
        """
        Retry connection with relaxed SSL settings if SSL verification fails.

        Args:
            url: WebSocket URL to connect to
            endpoint: Endpoint type ("public" or "private")
            attempt: Current attempt number

        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Create more permissive SSL context
            relaxed_ssl_context = ssl.create_default_context()
            relaxed_ssl_context.check_hostname = False
            relaxed_ssl_context.verify_mode = ssl.CERT_NONE

            log_websocket_event(
                self.logger,
                "ssl_retry_attempt",
                endpoint=endpoint,
                attempt=attempt + 1,
                url=url
            )

            ws = await asyncio.wait_for(
                websockets.connect(
                    url,
                    ssl=relaxed_ssl_context,
                    ping_interval=None,
                    ping_timeout=None
                ),
                timeout=self.connection_timeout
            )

            # Update SSL context for future connections
            self.ssl_context = relaxed_ssl_context

            if endpoint == "public":
                self.public_ws = ws
                self.is_public_connected = True
            else:
                self.private_ws = ws
                self.is_private_connected = True

            self.reconnect_attempts = 0
            self.last_heartbeat = time.time()

            log_websocket_event(
                self.logger,
                "connection_established_with_relaxed_ssl",
                endpoint=endpoint,
                url=url
            )

            # Start message handling task
            if endpoint == "public":
                asyncio.create_task(self._handle_public_messages())
                asyncio.create_task(self._heartbeat_monitor())

            return True

        except Exception as e:
            self.log_error(
                f"Relaxed SSL connection attempt failed",
                error=e,
                endpoint=endpoint
            )
            return False

    async def disconnect(self, endpoint: Optional[str] = None) -> None:
        """
        Disconnect from WebSocket(s).

        Args:
            endpoint: Specific endpoint to disconnect ("public" or "private").
                     If None, disconnect from all.
        """
        if endpoint is None or endpoint == "public":
            if self.public_ws and not self.public_ws.closed:
                await self.public_ws.close()
                log_websocket_event(self.logger, "disconnected", endpoint="public")
            self.is_public_connected = False
            self.public_ws = None

        if endpoint is None or endpoint == "private":
            if self.private_ws and not self.private_ws.closed:
                await self.private_ws.close()
                log_websocket_event(self.logger, "disconnected", endpoint="private")
            self.is_private_connected = False
            self.private_ws = None

    async def _handle_public_messages(self) -> None:
        """Handle incoming messages from public WebSocket."""
        if not self.public_ws:
            return

        try:
            async for message in self.public_ws:
                try:
                    data = json.loads(message)
                    await self._process_public_message(data)
                    await self.public_message_queue.put(data)
                except json.JSONDecodeError as e:
                    self.log_error("Failed to decode JSON message", error=e, message=message)
                except Exception as e:
                    self.log_error("Error processing message", error=e, message=message)
        except ConnectionClosed:
            self.log_warning("Public WebSocket connection closed")
            self.is_public_connected = False
            await self._handle_reconnection("public")
        except Exception as e:
            self.log_error("Unexpected error in message handler", error=e)
            self.is_public_connected = False

    async def _process_public_message(self, data: Dict[str, Any]) -> None:
        """
        Process incoming public WebSocket messages.

        Args:
            data: Parsed JSON message from WebSocket
        """
        # Update heartbeat timestamp
        self.last_heartbeat = time.time()

        # Handle different message types
        if isinstance(data, dict):
            event = data.get("event")

            if event == "systemStatus":
                log_websocket_event(
                    self.logger,
                    "system_status",
                    status=data.get("status"),
                    version=data.get("version")
                )
            elif event == "subscriptionStatus":
                await self._handle_subscription_status(data)
            elif event == "heartbeat":
                log_websocket_event(self.logger, "heartbeat_received")
            elif "errorMessage" in data:
                self.log_error("Received error from Kraken", details=data)
                raise handle_kraken_error(data)
            else:
                # Market data message
                log_websocket_event(
                    self.logger,
                    "market_data_received",
                    channel_id=data.get("channelID"),
                    channel_name=data.get("channelName")
                )

    async def _handle_subscription_status(self, data: Dict[str, Any]) -> None:
        """Handle subscription status messages."""
        status = data.get("status")
        subscription = data.get("subscription", {})
        pair = data.get("pair")
        channel_name = subscription.get("name")

        log_websocket_event(
            self.logger,
            "subscription_status",
            status=status,
            channel=channel_name,
            pair=pair,
            channel_id=data.get("channelID")
        )

        if status == "subscribed":
            # Store subscription info
            sub_key = f"{channel_name}:{pair}" if pair else channel_name
            self.public_subscriptions.add(sub_key)
            if "channelID" in data:
                self.subscription_ids[sub_key] = data["channelID"]
        elif status == "unsubscribed":
            # Remove subscription info
            sub_key = f"{channel_name}:{pair}" if pair else channel_name
            self.public_subscriptions.discard(sub_key)
            self.subscription_ids.pop(sub_key, None)

    async def _heartbeat_monitor(self) -> None:
        """Monitor connection health and send heartbeats if needed."""
        while self.is_public_connected:
            try:
                current_time = time.time()
                if current_time - self.last_heartbeat > self.heartbeat_interval:
                    # Send ping to check connection
                    await self.send_public_message({"event": "ping"})
                    log_websocket_event(self.logger, "heartbeat_sent")

                await asyncio.sleep(10)  # Check every 10 seconds
            except Exception as e:
                self.log_error("Error in heartbeat monitor", error=e)
                break

    async def _handle_reconnection(self, endpoint: str) -> None:
        """Handle automatic reconnection after connection loss."""
        if endpoint == "public" and not self.is_public_connected:
            self.log_info("Attempting to reconnect to public WebSocket")
            try:
                await self._connect_with_retry("public")
                # Resubscribe to previous subscriptions
                await self._resubscribe_public()
            except Exception as e:
                self.log_error("Reconnection failed", error=e)

    async def _resubscribe_public(self) -> None:
        """Resubscribe to previous public subscriptions after reconnection."""
        for subscription in self.public_subscriptions.copy():
            try:
                # Parse subscription key
                if ":" in subscription:
                    channel, pair = subscription.split(":", 1)
                    # TODO: Implement resubscription logic based on channel type
                    self.log_info(f"Resubscribing to {channel} for {pair}")
                else:
                    self.log_info(f"Resubscribing to {subscription}")
            except Exception as e:
                self.log_error("Failed to resubscribe", error=e, subscription=subscription)

    async def send_public_message(self, message: Dict[str, Any]) -> None:
        """
        Send a message to the public WebSocket.

        Args:
            message: Dictionary to send as JSON

        Raises:
            WebSocketError: If not connected or send fails
        """
        if not self.is_public_connected or not self.public_ws:
            raise WebSocketError("Public WebSocket not connected")

        try:
            json_message = json.dumps(message)
            await self.public_ws.send(json_message)
            log_websocket_event(
                self.logger,
                "message_sent",
                endpoint="public",
                message_type=message.get("event", "unknown")
            )
        except Exception as e:
            self.log_error("Failed to send message", error=e, message=message)
            raise WebSocketError(f"Failed to send message: {e}")

    async def send_private_message(self, message: Dict[str, Any]) -> None:
        """
        Send a message to the private WebSocket.

        Args:
            message: Dictionary to send as JSON

        Raises:
            WebSocketError: If not connected or send fails
        """
        if not self.is_private_connected or not self.private_ws:
            raise WebSocketError("Private WebSocket not connected")

        # TODO: Implement private message sending with authentication
        raise NotImplementedError("Private WebSocket messaging requires authentication")

    async def listen_public(self) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Listen for messages from the public WebSocket.

        Yields:
            Parsed JSON messages from the public WebSocket
        """
        while self.is_public_connected:
            try:
                message = await asyncio.wait_for(
                    self.public_message_queue.get(),
                    timeout=1.0
                )
                yield message
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self.log_error("Error in public message listener", error=e)
                break

    def get_connection_status(self) -> Dict[str, Any]:
        """
        Get current connection status.

        Returns:
            Dictionary with connection status information
        """
        return {
            "public_connected": self.is_public_connected,
            "private_connected": self.is_private_connected,
            "public_subscriptions": list(self.public_subscriptions),
            "private_subscriptions": list(self.private_subscriptions),
            "last_heartbeat": self.last_heartbeat,
            "reconnect_attempts": self.reconnect_attempts,
            "ssl_verify_mode": self.ssl_context.verify_mode.name if hasattr(self.ssl_context.verify_mode, 'name') else str(self.ssl_context.verify_mode),
            "ssl_check_hostname": self.ssl_context.check_hostname
        }
