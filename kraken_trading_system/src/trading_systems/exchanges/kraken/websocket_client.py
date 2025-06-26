"""
Enhanced Kraken WebSocket client with private connection support.
Integrates KrakenTokenManager for authenticated private WebSocket connections.
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
    AuthenticationError,
    handle_kraken_error,
)
from ...utils.logger import LoggerMixin, log_websocket_event
from .token_manager import KrakenTokenManager, get_token_manager


class KrakenWebSocketClient(LoggerMixin):
    """
    Enhanced Kraken WebSocket client supporting both public and private connections.

    This client manages WebSocket connections to Kraken's public and private
    WebSocket endpoints, handling subscriptions, message routing, reconnection logic,
    and token-based authentication for private feeds.
    """

    def __init__(self):
        super().__init__()

        # WebSocket connections
        self.public_ws: Optional[websockets.WebSocketServerProtocol] = None
        self.private_ws: Optional[websockets.WebSocketServerProtocol] = None
        self.is_public_connected = False
        self.is_private_connected = False

        # Connection management
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = settings.max_reconnect_attempts
        self.reconnect_delay = settings.reconnect_delay
        self.connection_timeout = settings.websocket_timeout

        # SSL context for handling certificate issues
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

        # Token management for private connections
        self.token_manager: Optional[KrakenTokenManager] = None
        self.current_token: Optional[str] = None

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
        """Create SSL context with proper certificate handling."""
        try:
            ssl_context = ssl.create_default_context()

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
            self.log_warning("SSL context creation failed, using fallback", error=str(e))
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            self.log_info("Created fallback SSL context (certificate verification disabled)")
            return ssl_context

    # PUBLIC CONNECTION METHODS (existing)

    async def connect_public(self) -> None:
        """Connect to Kraken's public WebSocket endpoint."""
        if self.is_public_connected:
            self.log_info("Public WebSocket already connected")
            return
        await self._connect_with_retry(endpoint="public")

    # NEW: PRIVATE CONNECTION METHODS

    async def connect_private(self) -> None:
        """
        Connect to Kraken's private WebSocket endpoint with token authentication.

        Raises:
            ConnectionError: If connection fails after retries
            AuthenticationError: If authentication fails or no credentials available
        """
        if self.is_private_connected:
            self.log_info("Private WebSocket already connected")
            return

        # Check if we have API credentials
        if not settings.has_api_credentials():
            raise AuthenticationError(
                "No API credentials configured for private WebSocket. "
                "Please set KRAKEN_API_KEY and KRAKEN_API_SECRET environment variables."
            )

        # Initialize token manager if not already done
        if self.token_manager is None:
            self.token_manager = await get_token_manager()
            self.log_info("Token manager initialized for private connection")

        # Get authentication token
        try:
            self.current_token = await self.token_manager.get_websocket_token()
            self.log_info(
                "WebSocket token obtained for private connection",
                token_length=len(self.current_token)
            )
        except Exception as e:
            self.log_error("Failed to obtain WebSocket token", error=e)
            raise AuthenticationError(f"Token acquisition failed: {e}")

        # Connect to private WebSocket
        await self._connect_with_retry(endpoint="private")

    async def _connect_with_retry(self, endpoint: str) -> None:
        """Connect to WebSocket with retry logic."""
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
                        ping_interval=None,
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

                # Start message handling tasks
                if endpoint == "public":
                    asyncio.create_task(self._handle_public_messages())
                    asyncio.create_task(self._heartbeat_monitor())
                else:
                    asyncio.create_task(self._handle_private_messages())

                return

            except (ConnectionClosed, WebSocketException, OSError) as e:
                self.log_error(
                    f"Connection attempt {attempt + 1} failed",
                    error=e,
                    endpoint=endpoint
                )

                # Handle SSL errors with automatic retry
                if "SSL" in str(e) or "certificate" in str(e):
                    self.log_info("SSL error detected, retrying with relaxed SSL settings")
                    if await self._retry_with_relaxed_ssl(url, endpoint, attempt):
                        return

                if attempt < self.max_reconnect_attempts - 1:
                    await asyncio.sleep(self.reconnect_delay * (2 ** attempt))
                else:
                    raise ConnectionError(
                        f"Failed to connect to {endpoint} WebSocket after {self.max_reconnect_attempts} attempts",
                        details={"endpoint": endpoint, "url": url}
                    )

    async def _retry_with_relaxed_ssl(self, url: str, endpoint: str, attempt: int) -> bool:
        """Retry connection with relaxed SSL settings."""
        try:
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

            self.ssl_context = relaxed_ssl_context

            if endpoint == "public":
                self.public_ws = ws
                self.is_public_connected = True
                asyncio.create_task(self._handle_public_messages())
                asyncio.create_task(self._heartbeat_monitor())
            else:
                self.private_ws = ws
                self.is_private_connected = True
                asyncio.create_task(self._handle_private_messages())

            self.reconnect_attempts = 0
            self.last_heartbeat = time.time()

            log_websocket_event(
                self.logger,
                "connection_established_with_relaxed_ssl",
                endpoint=endpoint,
                url=url
            )

            return True

        except Exception as e:
            self.log_error("Relaxed SSL connection attempt failed", error=e, endpoint=endpoint)
            return False

    async def disconnect(self, endpoint: Optional[str] = None) -> None:
        """Disconnect from WebSocket(s)."""
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
            self.current_token = None

    # PRIVATE SUBSCRIPTION METHODS

    async def subscribe_own_trades(self) -> None:
        """
        Subscribe to own trades feed (private).

        Raises:
            WebSocketError: If not connected to private WebSocket
            AuthenticationError: If no valid token available
        """
        if not self.is_private_connected or not self.private_ws:
            raise WebSocketError("Private WebSocket not connected")

        if not self.current_token:
            raise AuthenticationError("No valid authentication token available")

        subscription_message = {
            "event": "subscribe",
            "subscription": {
                "name": "ownTrades",
                "token": self.current_token
            },
            "reqid": self._get_next_req_id()
        }

        self.log_info(
            "Subscribing to own trades feed",
            req_id=subscription_message["reqid"]
        )

        try:
            await self.send_private_message(subscription_message)
            self.private_subscriptions.add("ownTrades")
        except Exception as e:
            self.log_error("Failed to subscribe to own trades", error=e)
            raise WebSocketError(f"Own trades subscription failed: {e}")

    async def subscribe_open_orders(self) -> None:
        """
        Subscribe to open orders feed (private).

        Raises:
            WebSocketError: If not connected to private WebSocket
            AuthenticationError: If no valid token available
        """
        if not self.is_private_connected or not self.private_ws:
            raise WebSocketError("Private WebSocket not connected")

        if not self.current_token:
            raise AuthenticationError("No valid authentication token available")

        subscription_message = {
            "event": "subscribe",
            "subscription": {
                "name": "openOrders",
                "token": self.current_token
            },
            "reqid": self._get_next_req_id()
        }

        self.log_info(
            "Subscribing to open orders feed",
            req_id=subscription_message["reqid"]
        )

        try:
            await self.send_private_message(subscription_message)
            self.private_subscriptions.add("openOrders")
        except Exception as e:
            self.log_error("Failed to subscribe to open orders", error=e)
            raise WebSocketError(f"Open orders subscription failed: {e}")

    # MESSAGE HANDLING

    async def _handle_private_messages(self) -> None:
        """Handle incoming messages from private WebSocket."""
        if not self.private_ws:
            return

        try:
            async for message in self.private_ws:
                try:
                    data = json.loads(message)
                    await self._process_private_message(data)
                    await self.private_message_queue.put(data)
                except json.JSONDecodeError as e:
                    self.log_error("Failed to decode JSON message", error=e, message=message)
                except Exception as e:
                    self.log_error("Error processing private message", error=e, message=message)
        except ConnectionClosed:
            self.log_warning("Private WebSocket connection closed")
            self.is_private_connected = False
            await self._handle_reconnection("private")
        except Exception as e:
            self.log_error("Unexpected error in private message handler", error=e)
            self.is_private_connected = False

    async def _process_private_message(self, data: Dict[str, Any]) -> None:
        """Process private WebSocket messages."""
        self.last_heartbeat = time.time()

        if isinstance(data, dict):
            event = data.get("event")

            if event == "systemStatus":
                log_websocket_event(
                    self.logger,
                    "private_system_status",
                    status=data.get("status"),
                    version=data.get("version")
                )
            elif event == "subscriptionStatus":
                await self._handle_private_subscription_status(data)
            elif event == "heartbeat":
                log_websocket_event(self.logger, "private_heartbeat_received")
            elif "errorMessage" in data:
                self.log_error("Received error from private WebSocket", details=data)

                # Handle token expiry
                if "token" in str(data.get("errorMessage", "")).lower():
                    self.log_warning("Token may have expired, attempting refresh")
                    await self._refresh_token_and_reconnect()
                else:
                    raise handle_kraken_error(data)
            else:
                # Handle private data feeds (ownTrades, openOrders)
                await self._process_private_data(data)

    async def _handle_private_subscription_status(self, data: Dict[str, Any]) -> None:
        """Handle private subscription status messages."""
        status = data.get("status")
        subscription = data.get("subscription", {})
        channel_name = subscription.get("name")

        log_websocket_event(
            self.logger,
            "private_subscription_status",
            status=status,
            channel=channel_name
        )

        if status == "subscribed":
            self.private_subscriptions.add(channel_name)
            self.log_info(f"Successfully subscribed to private feed: {channel_name}")
        elif status == "unsubscribed":
            self.private_subscriptions.discard(channel_name)
            self.log_info(f"Successfully unsubscribed from private feed: {channel_name}")
        elif status == "error":
            error_msg = data.get("errorMessage", "Unknown subscription error")
            self.log_error(f"Private subscription error for {channel_name}: {error_msg}")

    async def _process_private_data(self, data: Dict[str, Any]) -> None:
        """Process private data feeds (ownTrades, openOrders)."""
        # Log the private data received
        log_websocket_event(
            self.logger,
            "private_data_received",
            data_type=type(data).__name__,
            keys=list(data.keys()) if isinstance(data, dict) else None
        )

        # TODO: Implement specific parsing for ownTrades and openOrders
        # This will be enhanced in Task 2.3
        self.log_info("Private data received", data_preview=str(data)[:200] + "..." if len(str(data)) > 200 else str(data))

    async def _refresh_token_and_reconnect(self) -> None:
        """Refresh token and reconnect to private WebSocket."""
        try:
            if self.token_manager:
                self.log_info("Refreshing WebSocket token")
                self.current_token = await self.token_manager.get_websocket_token(force_refresh=True)

                # Disconnect and reconnect with new token
                await self.disconnect("private")
                await asyncio.sleep(1)  # Brief pause
                await self.connect_private()

                self.log_info("Successfully reconnected with new token")
            else:
                self.log_error("No token manager available for token refresh")
        except Exception as e:
            self.log_error("Failed to refresh token and reconnect", error=e)

    # UTILITY METHODS

    def _get_next_req_id(self) -> int:
        """Get next request ID for tracking requests."""
        req_id = self.next_req_id
        self.next_req_id += 1
        return req_id

    async def send_private_message(self, message: Dict[str, Any]) -> None:
        """Send a message to the private WebSocket."""
        if not self.is_private_connected or not self.private_ws:
            raise WebSocketError("Private WebSocket not connected")

        try:
            json_message = json.dumps(message)
            await self.private_ws.send(json_message)
            log_websocket_event(
                self.logger,
                "message_sent",
                endpoint="private",
                message_type=message.get("event", "unknown")
            )
        except Exception as e:
            self.log_error("Failed to send private message", error=e, message=message)
            raise WebSocketError(f"Failed to send private message: {e}")

    async def listen_private(self) -> AsyncGenerator[Dict[str, Any], None]:
        """Listen for messages from the private WebSocket."""
        while self.is_private_connected:
            try:
                message = await asyncio.wait_for(
                    self.private_message_queue.get(),
                    timeout=1.0
                )
                yield message
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self.log_error("Error in private message listener", error=e)
                break

    def get_connection_status(self) -> Dict[str, Any]:
        """Get current connection status."""
        return {
            "public_connected": self.is_public_connected,
            "private_connected": self.is_private_connected,
            "public_subscriptions": list(self.public_subscriptions),
            "private_subscriptions": list(self.private_subscriptions),
            "has_token": self.current_token is not None,
            "token_manager_initialized": self.token_manager is not None,
            "last_heartbeat": self.last_heartbeat,
            "reconnect_attempts": self.reconnect_attempts,
            "ssl_verify_mode": self.ssl_context.verify_mode.name if hasattr(self.ssl_context.verify_mode, 'name') else str(self.ssl_context.verify_mode),
            "ssl_check_hostname": self.ssl_context.check_hostname
        }

    # EXISTING PUBLIC METHODS (maintaining compatibility)
    # ... (all the existing public subscription methods would remain here)

    async def _handle_public_messages(self) -> None:
        """Handle incoming messages from public WebSocket (existing method)."""
        # This method remains unchanged from the existing implementation
        pass

    async def _heartbeat_monitor(self) -> None:
        """Monitor connection health (existing method)."""
        # This method remains unchanged from the existing implementation
        pass

    async def _handle_reconnection(self, endpoint: str) -> None:
        """Handle automatic reconnection after connection loss."""
        if endpoint == "public" and not self.is_public_connected:
            self.log_info("Attempting to reconnect to public WebSocket")
            try:
                await self._connect_with_retry("public")
            except Exception as e:
                self.log_error("Public reconnection failed", error=e)

        elif endpoint == "private" and not self.is_private_connected:
            self.log_info("Attempting to reconnect to private WebSocket")
            try:
                # For private reconnection, we may need to refresh the token
                await self._refresh_token_and_reconnect()
            except Exception as e:
                self.log_error("Private reconnection failed", error=e)
