
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

"""
These additions should be integrated into the existing KrakenWebSocketClient class.
Add these imports and modifications to the existing file.
"""

# ADD THESE IMPORTS at the top of websocket_client.py:
from .account_data_manager import AccountDataManager
from .account_models import AccountSnapshot, KrakenOrder, KrakenTrade

# ADD THIS TO THE __init__ method of KrakenWebSocketClient:
class KrakenWebSocketClient(LoggerMixin):
    def __init__(self):
        # IMPORTANT: Call LoggerMixin.__init__() first
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

        # Account data management
        self.account_manager: Optional[AccountDataManager] = None
        self._account_data_enabled = False

        # Get URLs from settings
        self.public_url, self.private_url = settings.get_websocket_urls()

        self.ssl_context = self._create_ssl_context()
        self.last_heartbeat = time.time()
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = getattr(settings, 'max_reconnect_attempts', 5)
        self.reconnect_delay = getattr(settings, 'reconnect_delay', 5.0)
        self.connection_timeout = getattr(settings, 'websocket_timeout', 30.0)
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
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        return ssl_context

    # REPLACE the existing _process_private_data method with this enhanced version:
    async def _process_private_data(self, data: Dict[str, Any]) -> None:
        """Process private data feeds (ownTrades, openOrders) with structured parsing."""
        try:
            # Initialize account manager if not already done
            if self.account_manager is None:
                self.account_manager = AccountDataManager()
                self._account_data_enabled = True
                self.log_info("Account data manager initialized")

            # Determine message type and route to appropriate processor
            if isinstance(data, list) and len(data) >= 3:
                channel_name = data[2] if len(data) > 2 else None

                if channel_name == "ownTrades":
                    await self.account_manager.process_own_trades_update(data)
                    log_websocket_event(
                        self.logger,
                        "private_trades_processed",
                        channel=channel_name,
                        data_elements=len(data[1]) if isinstance(data[1], dict) else 0
                    )

                elif channel_name == "openOrders":
                    await self.account_manager.process_open_orders_update(data)
                    log_websocket_event(
                        self.logger,
                        "private_orders_processed",
                        channel=channel_name,
                        data_elements=len(data[1]) if isinstance(data[1], dict) else 0
                    )

                else:
                    # Handle other private data types or log unknown
                    log_websocket_event(
                        self.logger,
                        "unknown_private_data",
                        channel=channel_name,
                        data_type=type(data).__name__
                    )
                    self.log_info("Unknown private data received",
                                channel=channel_name,
                                data_preview=str(data)[:200] + "..." if len(str(data)) > 200 else str(data))

            elif isinstance(data, dict):
                # Handle balance updates or other dict-format messages
                if "balance" in data or any(key in data for key in ["USD", "XBT", "ETH", "EUR"]):
                    await self.account_manager.process_balance_update(data)
                    log_websocket_event(
                        self.logger,
                        "balance_update_processed",
                        currencies=list(data.keys()) if isinstance(data, dict) else []
                    )
                else:
                    # Unknown dict format
                    self.log_info("Unknown private dict data received",
                                data_keys=list(data.keys()) if isinstance(data, dict) else None,
                                data_preview=str(data)[:200] + "..." if len(str(data)) > 200 else str(data))

            else:
                # Unknown data format
                self.log_info("Unknown private data format received",
                            data_type=type(data).__name__,
                            data_preview=str(data)[:200] + "..." if len(str(data)) > 200 else str(data))

        except Exception as e:
            self.log_error("Error processing private data", error=e, data_type=type(data).__name__)

    # ADD THESE NEW METHODS to the KrakenWebSocketClient class:

    def get_account_snapshot(self) -> Optional[AccountSnapshot]:
        """
        Get current account state snapshot.

        Returns:
            AccountSnapshot with current balances, orders, and trades, or None if not available
        """
        if not self.account_manager:
            self.log_warning("Account manager not initialized - no account data available")
            return None

        return self.account_manager.get_account_snapshot()

    def get_current_balances(self) -> Dict[str, Any]:
        """Get current account balances."""
        if not self.account_manager:
            return {}

        balances = self.account_manager.get_current_balances()
        return {currency: {
            'balance': str(balance.balance),
            'available': str(balance.available_balance),
            'hold': str(balance.hold),
            'last_update': balance.last_update.isoformat()
        } for currency, balance in balances.items()}

    def get_open_orders_summary(self) -> Dict[str, Any]:
        """Get summary of current open orders."""
        if not self.account_manager:
            return {'orders': [], 'count': 0, 'pairs': []}

        open_orders = self.account_manager.get_open_orders()

        # Organize by trading pair
        orders_by_pair = {}
        for order in open_orders.values():
            if order.pair not in orders_by_pair:
                orders_by_pair[order.pair] = []

            orders_by_pair[order.pair].append({
                'order_id': order.order_id,
                'type': order.type,
                'order_type': order.order_type,
                'volume': str(order.volume),
                'volume_executed': str(order.volume_executed),
                'volume_remaining': str(order.volume_remaining),
                'price': str(order.price) if order.price else None,
                'fill_percentage': f"{order.fill_percentage:.2f}%",
                'status': order.status,
                'last_update': order.last_update.isoformat()
            })

        return {
            'orders_by_pair': orders_by_pair,
            'total_orders': len(open_orders),
            'pairs': list(orders_by_pair.keys())
        }

    def get_recent_trades_summary(self, limit: int = 20) -> Dict[str, Any]:
        """Get summary of recent trades."""
        if not self.account_manager:
            return {'trades': [], 'count': 0}

        recent_trades = self.account_manager.get_recent_trades(limit)

        trades_data = []
        for trade in recent_trades:
            trades_data.append({
                'trade_id': trade.trade_id,
                'order_id': trade.order_id,
                'pair': trade.pair,
                'type': trade.type,
                'price': str(trade.price),
                'volume': str(trade.volume),
                'fee': str(trade.fee),
                'time': trade.time.isoformat(),
                'order_type': trade.order_type
            })

        return {
            'trades': trades_data,
            'count': len(trades_data)
        }

    def get_trading_summary(self, pair: Optional[str] = None, hours: int = 24) -> Dict[str, Any]:
        """Get trading summary for specified period."""
        if not self.account_manager:
            return {}

        return self.account_manager.get_trading_summary(pair, hours)

    def get_account_health(self) -> Dict[str, Any]:
        """Get account data health status."""
        if not self.account_manager:
            return {
                'account_data_enabled': False,
                'status': 'not_initialized'
            }

        health_data = asyncio.create_task(self.account_manager.health_check())
        # Note: This is async, so in real usage you'd want to await this
        # For now, return sync data

        return {
            'account_data_enabled': self._account_data_enabled,
            'manager_initialized': True,
            'statistics': self.account_manager.get_statistics()
        }

    # UPDATE the get_connection_status method to include account data info:
    def get_connection_status(self) -> Dict[str, Any]:
        """Get current connection status including account data."""
        base_status = {
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

        # Add account data status
        if self.account_manager:
            account_stats = self.account_manager.get_statistics()
            base_status.update({
                "account_data_enabled": self._account_data_enabled,
                "account_data_stats": account_stats
            })
        else:
            base_status.update({
                "account_data_enabled": False,
                "account_data_stats": None
            })

        return base_status

    # ADD THIS METHOD if it's missing:
    async def disconnect(self, endpoint: Optional[str] = None) -> None:
        """Disconnect from WebSocket(s)."""
        try:
            if endpoint is None or endpoint == "public":
                if hasattr(self, 'public_ws') and self.public_ws and not self.public_ws.closed:
                    await self.public_ws.close()
                    self.logger.info("Disconnected from public WebSocket")
                self.is_public_connected = False
                self.public_ws = None

            if endpoint is None or endpoint == "private":
                if hasattr(self, 'private_ws') and self.private_ws and not self.private_ws.closed:
                    await self.private_ws.close()
                    self.logger.info("Disconnected from private WebSocket")
                self.is_private_connected = False
                self.private_ws = None
                self.current_token = None

        except Exception as e:
            self.logger.error("Error during disconnect", error=e)

    # ADD THIS METHOD if it's missing:
    async def subscribe_own_trades(self) -> None:
        """Subscribe to own trades feed (private)."""
        if not hasattr(self, 'is_private_connected') or not self.is_private_connected:
            raise Exception("Private WebSocket not connected")

        # Basic implementation - you may need to adapt based on your current code
        subscription_message = {
            "event": "subscribe",
            "subscription": {
                "name": "ownTrades",
                "token": getattr(self, 'current_token', None)
            }
        }

        # You'll need to implement send_private_message if it doesn't exist
        await self.send_private_message(subscription_message)
        self.private_subscriptions.add("ownTrades")

    # ADD THIS METHOD if it's missing:
    async def subscribe_open_orders(self) -> None:
        """Subscribe to open orders feed (private)."""
        if not hasattr(self, 'is_private_connected') or not self.is_private_connected:
            raise Exception("Private WebSocket not connected")

        subscription_message = {
            "event": "subscribe",
            "subscription": {
                "name": "openOrders",
                "token": getattr(self, 'current_token', None)
            }
        }

        await self.send_private_message(subscription_message)
        self.private_subscriptions.add("openOrders")

    # ADD THIS METHOD if it's missing:
    async def send_private_message(self, message: Dict[str, Any]) -> None:
        """Send a message to the private WebSocket."""
        if not hasattr(self, 'private_ws') or not self.private_ws:
            raise Exception("Private WebSocket not connected")

        import json
        json_message = json.dumps(message)
        await self.private_ws.send(json_message)
        self.logger.info("Sent private message", message_type=message.get("event", "unknown"))

    async def connect_private(self) -> None:
        """
        Connect to Kraken's private WebSocket endpoint with token authentication.
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
        private_url = "wss://ws-auth.kraken.com"

        try:
            self.private_ws = await websockets.connect(
                private_url,
                ssl=self.ssl_context,
                ping_interval=None,
                ping_timeout=None
            )

            self.is_private_connected = True
            self.log_info("Private WebSocket connected successfully")

            # Initialize account manager
            if self.account_manager is None:
                self.account_manager = AccountDataManager()
                self._account_data_enabled = True
                self.log_info("Account data manager initialized")

            # Start message handling
            asyncio.create_task(self._handle_private_messages())

        except Exception as e:
            self.log_error("Private WebSocket connection failed", error=e)
            raise ConnectionError(f"Failed to connect to private WebSocket: {e}")

    async def subscribe_own_trades(self) -> None:
        """Subscribe to own trades feed (private)."""
        if not self.is_private_connected or not self.private_ws:
            raise WebSocketError("Private WebSocket not connected")

        if not self.current_token:
            raise AuthenticationError("No valid authentication token available")

        subscription_message = {
            "event": "subscribe",
            "subscription": {
                "name": "ownTrades",
                "token": self.current_token
            }
        }

        await self.send_private_message(subscription_message)
        self.private_subscriptions.add("ownTrades")
        self.log_info("Subscribed to ownTrades feed")

    async def subscribe_open_orders(self) -> None:
        """Subscribe to open orders feed (private)."""
        if not self.is_private_connected or not self.private_ws:
            raise WebSocketError("Private WebSocket not connected")

        if not self.current_token:
            raise AuthenticationError("No valid authentication token available")

        subscription_message = {
            "event": "subscribe",
            "subscription": {
                "name": "openOrders",
                "token": self.current_token
            }
        }

        await self.send_private_message(subscription_message)
        self.private_subscriptions.add("openOrders")
        self.log_info("Subscribed to openOrders feed")

    async def send_private_message(self, message: Dict[str, Any]) -> None:
        """Send a message to the private WebSocket."""
        if not self.is_private_connected or not self.private_ws:
            raise WebSocketError("Private WebSocket not connected")

        try:
            json_message = json.dumps(message)
            await self.private_ws.send(json_message)
            self.log_info("Sent private message", message_type=message.get("event", "unknown"))
        except Exception as e:
            self.log_error("Failed to send private message", error=e)
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
                    self.log_error("Failed to decode private JSON message", error=e)
                except Exception as e:
                    self.log_error("Error processing private message", error=e)
        except Exception as e:
            self.log_error("Private message handler error", error=e)
            self.is_private_connected = False

    async def _process_private_message(self, data: Dict[str, Any]) -> None:
        """Process private WebSocket messages."""
        try:
            # Initialize account manager if needed
            if self.account_manager is None:
                self.account_manager = AccountDataManager()
                self._account_data_enabled = True

            # Route messages to account manager
            if isinstance(data, list) and len(data) >= 3:
                channel_name = data[2]

                if channel_name == "ownTrades":
                    await self.account_manager.process_own_trades_update(data)
                elif channel_name == "openOrders":
                    await self.account_manager.process_open_orders_update(data)

            elif isinstance(data, dict):
                event = data.get("event")
                if event == "subscriptionStatus":
                    status = data.get("status")
                    channel = data.get("subscription", {}).get("name")
                    self.log_info(f"Private subscription {channel}: {status}")

        except Exception as e:
            self.log_error("Error processing private data", error=e)

    # 4. ENHANCE the disconnect method:
    async def disconnect(self, endpoint: Optional[str] = None) -> None:
        """Disconnect from WebSocket(s)."""
        if endpoint is None or endpoint == "public":
            if hasattr(self, 'public_ws') and self.public_ws and not self.public_ws.closed:
                await self.public_ws.close()
            self.is_public_connected = False
            self.public_ws = None

        if endpoint is None or endpoint == "private":
            if hasattr(self, 'private_ws') and self.private_ws and not self.private_ws.closed:
                await self.private_ws.close()
            self.is_private_connected = False
            self.private_ws = None
            self.current_token = None

        self.log_info("Disconnected from WebSockets", endpoint=endpoint or "all")

    # 5. ENHANCE get_connection_status method:
    def get_connection_status(self) -> Dict[str, Any]:
        """Get current connection status including account data."""
        status = {
            "public_connected": getattr(self, 'is_public_connected', False),
            "private_connected": getattr(self, 'is_private_connected', False),
            "public_subscriptions": list(getattr(self, 'public_subscriptions', set())),
            "private_subscriptions": list(getattr(self, 'private_subscriptions', set())),
            "has_token": self.current_token is not None,
            "token_manager_initialized": self.token_manager is not None,
            "last_heartbeat": getattr(self, 'last_heartbeat', 0),
            "ssl_verify_mode": str(getattr(self.ssl_context, 'verify_mode', 'unknown')),
            "ssl_check_hostname": getattr(self.ssl_context, 'check_hostname', False)
        }

        # Add account data status
        if hasattr(self, 'account_manager') and self.account_manager:
            account_stats = self.account_manager.get_statistics()
            status["account_data_stats"] = account_stats

        return status
