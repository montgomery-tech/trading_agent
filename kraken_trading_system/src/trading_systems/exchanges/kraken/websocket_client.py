"""
Kraken WebSocket client with enhanced market data message parsing.
"""

import asyncio
import json
import ssl
import time
from typing import Any, AsyncGenerator, Dict, List, Optional, Set, Union
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
from .models import (
    create_subscribe_message, 
    create_unsubscribe_message, 
    KrakenChannelName,
    KrakenTickerData,
    KrakenOrderBookData,
    KrakenTradeData
)


class KrakenWebSocketClient(LoggerMixin):
    """
    Kraken WebSocket client with enhanced market data parsing.

    This client manages WebSocket connections to Kraken's public and private
    WebSocket endpoints, handling subscriptions, message routing, reconnection logic,
    and real-time market data parsing and storage.
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

        # NEW: Market data storage
        self.latest_ticker: Dict[str, KrakenTickerData] = {}
        self.latest_orderbook: Dict[str, KrakenOrderBookData] = {}
        self.recent_trades: Dict[str, List[KrakenTradeData]] = {}
        self.max_trades_per_pair = 100  # Keep last 100 trades per pair

        # NEW: Channel ID to subscription mapping (reverse lookup)
        self.channel_id_to_subscription: Dict[int, str] = {}

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

    # CONNECTION METHODS (unchanged)
    
    async def connect_public(self) -> None:
        """Connect to Kraken's public WebSocket endpoint."""
        if self.is_public_connected:
            self.log_info("Public WebSocket already connected")
            return
        await self._connect_with_retry(endpoint="public")

    async def connect_private(self) -> None:
        """Connect to Kraken's private WebSocket endpoint."""
        if self.is_private_connected:
            self.log_info("Private WebSocket already connected")
            return
        raise NotImplementedError("Private WebSocket connection requires authentication")

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

    # SUBSCRIPTION METHODS (unchanged from 1.3.A)
    
    async def subscribe_ticker(self, pairs: List[str]) -> None:
        """Subscribe to ticker data for specified trading pairs."""
        if not self.is_public_connected:
            raise WebSocketError("Public WebSocket not connected")
        
        try:
            message = create_subscribe_message(
                channel=KrakenChannelName.TICKER,
                pairs=pairs,
                reqid=self.next_req_id
            )
            
            self.next_req_id += 1
            await self.send_public_message(message)
            
            log_websocket_event(
                self.logger,
                "subscription_requested",
                channel="ticker",
                pairs=pairs,
                req_id=message.get("reqid")
            )
            
        except Exception as e:
            self.log_error("Failed to subscribe to ticker", error=e, pairs=pairs)
            raise WebSocketError(f"Ticker subscription failed: {e}")

    async def subscribe_orderbook(self, pairs: List[str], depth: int = 10) -> None:
        """Subscribe to orderbook data for specified trading pairs."""
        if not self.is_public_connected:
            raise WebSocketError("Public WebSocket not connected")
        
        if depth <= 0 or depth > 1000:
            raise ValueError("Orderbook depth must be between 1 and 1000")
        
        try:
            message = create_subscribe_message(
                channel=KrakenChannelName.BOOK,
                pairs=pairs,
                depth=depth,
                reqid=self.next_req_id
            )
            
            self.next_req_id += 1
            await self.send_public_message(message)
            
            log_websocket_event(
                self.logger,
                "subscription_requested", 
                channel="book",
                pairs=pairs,
                depth=depth,
                req_id=message.get("reqid")
            )
            
        except Exception as e:
            self.log_error("Failed to subscribe to orderbook", error=e, pairs=pairs, depth=depth)
            raise WebSocketError(f"Orderbook subscription failed: {e}")

    async def subscribe_trades(self, pairs: List[str]) -> None:
        """Subscribe to trade data for specified trading pairs."""
        if not self.is_public_connected:
            raise WebSocketError("Public WebSocket not connected")
        
        try:
            message = create_subscribe_message(
                channel=KrakenChannelName.TRADE,
                pairs=pairs,
                reqid=self.next_req_id
            )
            
            self.next_req_id += 1
            await self.send_public_message(message)
            
            log_websocket_event(
                self.logger,
                "subscription_requested",
                channel="trade", 
                pairs=pairs,
                req_id=message.get("reqid")
            )
            
        except Exception as e:
            self.log_error("Failed to subscribe to trades", error=e, pairs=pairs)
            raise WebSocketError(f"Trade subscription failed: {e}")

    async def unsubscribe(self, subscription_id: str) -> None:
        """Unsubscribe from a specific subscription."""
        if not self.is_public_connected:
            raise WebSocketError("Public WebSocket not connected")
        
        try:
            if ":" in subscription_id:
                channel_name, pair = subscription_id.split(":", 1)
                pairs = [pair]
            else:
                channel_name = subscription_id
                pairs = None
                
            try:
                channel = KrakenChannelName(channel_name)
            except ValueError:
                raise ValueError(f"Invalid channel name: {channel_name}")
                
        except Exception as e:
            raise ValueError(f"Invalid subscription_id format '{subscription_id}': {e}")
        
        if subscription_id not in self.public_subscriptions:
            self.log_warning(f"Subscription '{subscription_id}' not found in active subscriptions")
            return
        
        try:
            message = create_unsubscribe_message(
                channel=channel,
                pairs=pairs,
                reqid=self.next_req_id
            )
            
            self.next_req_id += 1
            await self.send_public_message(message)
            
            log_websocket_event(
                self.logger,
                "unsubscription_requested",
                channel=channel_name,
                pairs=pairs,
                subscription_id=subscription_id,
                req_id=message.get("reqid")
            )
            
        except Exception as e:
            self.log_error("Failed to unsubscribe", error=e, subscription_id=subscription_id)
            raise WebSocketError(f"Unsubscription failed: {e}")

    def get_active_subscriptions(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all active subscriptions."""
        subscription_details = {}
        
        for sub_id in self.public_subscriptions:
            details = {
                "subscription_id": sub_id,
                "channel_id": self.subscription_ids.get(sub_id),
                "status": "subscribed"
            }
            
            if ":" in sub_id:
                channel, pair = sub_id.split(":", 1)
                details["channel"] = channel
                details["pair"] = pair
            else:
                details["channel"] = sub_id
                details["pair"] = None
                
            subscription_details[sub_id] = details
        
        return subscription_details

    # ENHANCED MESSAGE HANDLING WITH ARRAY PARSING

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

    async def _process_public_message(self, data: Union[Dict[str, Any], List[Any]]) -> None:
        """
        Enhanced message processing for both dict and array formats.

        Args:
            data: Parsed JSON message from WebSocket (dict or list)
        """
        self.last_heartbeat = time.time()

        # Handle dict messages (system messages, subscription status, etc.)
        if isinstance(data, dict):
            await self._process_dict_message(data)
        
        # Handle array messages (market data)
        elif isinstance(data, list) and len(data) >= 3:
            await self._process_array_message(data)
        
        else:
            self.log_warning("Received unknown message format", 
                           message_type=type(data).__name__, 
                           data_length=len(data) if hasattr(data, '__len__') else 'unknown')

    async def _process_dict_message(self, data: Dict[str, Any]) -> None:
        """Process dictionary format messages (system messages)."""
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
            log_websocket_event(
                self.logger,
                "unknown_dict_message",
                event=event,
                keys=list(data.keys())
            )

    async def _process_array_message(self, data: List[Any]) -> None:
        """
        Process array format messages (market data).
        
        Kraken array format: [channelID, data, channelName, pair]
        """
        try:
            channel_id = data[0]
            message_data = data[1]
            channel_name = data[2] if len(data) > 2 else None
            pair = data[3] if len(data) > 3 else None
            
            log_websocket_event(
                self.logger,
                "market_data_array_received",
                channel_id=channel_id,
                channel_name=channel_name,
                pair=pair,
                data_type=type(message_data).__name__
            )
            
            # Route to appropriate parser based on subscription lookup
            subscription_key = self._get_subscription_key_by_channel_id(channel_id)
            if subscription_key:
                channel_type = subscription_key.split(":")[0]
                
                if channel_type == "ticker":
                    await self._parse_ticker_data(message_data, pair, channel_id)
                elif channel_type == "book":
                    await self._parse_orderbook_data(message_data, pair, channel_id)
                elif channel_type == "trade":
                    await self._parse_trade_data(message_data, pair, channel_id)
                else:
                    self.log_warning("Unknown channel type for market data", 
                                   channel_type=channel_type, channel_id=channel_id)
            else:
                # Fallback: try to determine from channel name
                if channel_name:
                    if "ticker" in channel_name.lower():
                        await self._parse_ticker_data(message_data, pair, channel_id)
                    elif "book" in channel_name.lower():
                        await self._parse_orderbook_data(message_data, pair, channel_id)
                    elif "trade" in channel_name.lower():
                        await self._parse_trade_data(message_data, pair, channel_id)
                    else:
                        self.log_warning("Unknown channel name for market data", 
                                       channel_name=channel_name, channel_id=channel_id)
                else:
                    self.log_warning("Cannot determine message type for array data", 
                                   channel_id=channel_id)
        
        except (IndexError, TypeError) as e:
            self.log_error("Failed to parse array message", error=e, data_length=len(data))

    def _get_subscription_key_by_channel_id(self, channel_id: int) -> Optional[str]:
        """Get subscription key by channel ID (reverse lookup)."""
        return self.channel_id_to_subscription.get(channel_id)

    async def _parse_ticker_data(self, data: Any, pair: str, channel_id: int) -> None:
        """Parse ticker data into KrakenTickerData object."""
        try:
            if isinstance(data, dict):
                ticker = KrakenTickerData(**data)
                
                if pair:
                    self.latest_ticker[pair] = ticker
                    
                    log_websocket_event(
                        self.logger,
                        "ticker_data_parsed",
                        pair=pair,
                        channel_id=channel_id,
                        bid_price=ticker.b[0] if ticker.b else None,
                        ask_price=ticker.a[0] if ticker.a else None,
                        last_price=ticker.c[0] if ticker.c else None
                    )
            else:
                self.log_warning("Unexpected ticker data format", 
                               data_type=type(data).__name__, pair=pair)
        
        except Exception as e:
            self.log_error("Failed to parse ticker data", error=e, pair=pair, channel_id=channel_id)

    async def _parse_orderbook_data(self, data: Any, pair: str, channel_id: int) -> None:
        """Parse orderbook data into KrakenOrderBookData object."""
        try:
            if isinstance(data, dict):
                orderbook = KrakenOrderBookData(**data)
                
                if pair:
                    self.latest_orderbook[pair] = orderbook
                    
                    log_websocket_event(
                        self.logger,
                        "orderbook_data_parsed",
                        pair=pair,
                        channel_id=channel_id,
                        asks_count=len(orderbook.asks) if orderbook.asks else 0,
                        bids_count=len(orderbook.bids) if orderbook.bids else 0,
                        checksum=orderbook.checksum
                    )
            else:
                self.log_warning("Unexpected orderbook data format", 
                               data_type=type(data).__name__, pair=pair)
        
        except Exception as e:
            self.log_error("Failed to parse orderbook data", error=e, pair=pair, channel_id=channel_id)

    async def _parse_trade_data(self, data: Any, pair: str, channel_id: int) -> None:
        """Parse trade data into KrakenTradeData objects."""
        try:
            if isinstance(data, list):
                parsed_trades = []
                
                for trade_array in data:
                    if isinstance(trade_array, list) and len(trade_array) >= 6:
                        trade_dict = {
                            "price": trade_array[0],
                            "volume": trade_array[1],
                            "time": trade_array[2],
                            "side": trade_array[3],
                            "orderType": trade_array[4],
                            "misc": trade_array[5] if len(trade_array) > 5 else ""
                        }
                        
                        trade = KrakenTradeData(**trade_dict)
                        parsed_trades.append(trade)
                
                if pair and parsed_trades:
                    if pair not in self.recent_trades:
                        self.recent_trades[pair] = []
                    
                    self.recent_trades[pair].extend(parsed_trades)
                    self.recent_trades[pair] = self.recent_trades[pair][-self.max_trades_per_pair:]
                    
                    log_websocket_event(
                        self.logger,
                        "trade_data_parsed",
                        pair=pair,
                        channel_id=channel_id,
                        new_trades_count=len(parsed_trades),
                        total_stored_trades=len(self.recent_trades[pair])
                    )
            else:
                self.log_warning("Unexpected trade data format", 
                               data_type=type(data).__name__, pair=pair)
        
        except Exception as e:
            self.log_error("Failed to parse trade data", error=e, pair=pair, channel_id=channel_id)

    async def _handle_subscription_status(self, data: Dict[str, Any]) -> None:
        """Handle subscription status messages with enhanced channel mapping."""
        status = data.get("status")
        subscription = data.get("subscription", {})
        pair = data.get("pair")
        channel_name = subscription.get("name")
        channel_id = data.get("channelID")

        log_websocket_event(
            self.logger,
            "subscription_status",
            status=status,
            channel=channel_name,
            pair=pair,
            channel_id=channel_id
        )

        if status == "subscribed":
            sub_key = f"{channel_name}:{pair}" if pair else channel_name
            self.public_subscriptions.add(sub_key)
            
            if channel_id is not None:
                self.subscription_ids[sub_key] = channel_id
                # Add reverse mapping for array message routing
                self.channel_id_to_subscription[channel_id] = sub_key
                
        elif status == "unsubscribed":
            sub_key = f"{channel_name}:{pair}" if pair else channel_name
            self.public_subscriptions.discard(sub_key)
            
            # Remove from both mappings
            channel_id = self.subscription_ids.pop(sub_key, None)
            if channel_id is not None:
                self.channel_id_to_subscription.pop(channel_id, None)

    # DATA ACCESS METHODS

    def get_latest_ticker(self, pair: str) -> Optional[KrakenTickerData]:
        """Get the latest ticker data for a trading pair."""
        return self.latest_ticker.get(pair)

    def get_latest_orderbook(self, pair: str) -> Optional[KrakenOrderBookData]:
        """Get the latest orderbook data for a trading pair."""
        return self.latest_orderbook.get(pair)

    def get_recent_trades(self, pair: str, limit: Optional[int] = None) -> List[KrakenTradeData]:
        """Get recent trades for a trading pair."""
        trades = self.recent_trades.get(pair, [])
        if limit is not None:
            return trades[-limit:]
        return trades.copy()

    def get_market_data_summary(self) -> Dict[str, Dict[str, Any]]:
        """Get a summary of all available market data."""
        summary = {}
        
        all_pairs = set()
        all_pairs.update(self.latest_ticker.keys())
        all_pairs.update(self.latest_orderbook.keys())
        all_pairs.update(self.recent_trades.keys())
        
        for pair in all_pairs:
            pair_summary = {
                "pair": pair,
                "has_ticker": pair in self.latest_ticker,
                "has_orderbook": pair in self.latest_orderbook,
                "trades_count": len(self.recent_trades.get(pair, [])),
                "data_types": []
            }
            
            if pair_summary["has_ticker"]:
                pair_summary["data_types"].append("ticker")
                ticker = self.latest_ticker[pair]
                pair_summary["last_price"] = ticker.c[0] if ticker.c else None
                
            if pair_summary["has_orderbook"]:
                pair_summary["data_types"].append("orderbook")
                
            if pair_summary["trades_count"] > 0:
                pair_summary["data_types"].append("trades")
                
            summary[pair] = pair_summary
        
        return summary

    # REMAINING METHODS (unchanged)

    async def _heartbeat_monitor(self) -> None:
        """Monitor connection health and send heartbeats if needed."""
        while self.is_public_connected:
            try:
                current_time = time.time()
                if current_time - self.last_heartbeat > self.heartbeat_interval:
                    await self.send_public_message({"event": "ping"})
                    log_websocket_event(self.logger, "heartbeat_sent")

                await asyncio.sleep(10)
            except Exception as e:
                self.log_error("Error in heartbeat monitor", error=e)
                break

    async def _handle_reconnection(self, endpoint: str) -> None:
        """Handle automatic reconnection after connection loss."""
        if endpoint == "public" and not self.is_public_connected:
            self.log_info("Attempting to reconnect to public WebSocket")
            try:
                await self._connect_with_retry("public")
                await self._resubscribe_public()
            except Exception as e:
                self.log_error("Reconnection failed", error=e)

    async def _resubscribe_public(self) -> None:
        """Resubscribe to previous public subscriptions after reconnection."""
        for subscription in self.public_subscriptions.copy():
            try:
                if ":" in subscription:
                    channel, pair = subscription.split(":", 1)
                    self.log_info(f"Resubscribing to {channel} for {pair}")
                else:
                    self.log_info(f"Resubscribing to {subscription}")
            except Exception as e:
                self.log_error("Failed to resubscribe", error=e, subscription=subscription)

    async def send_public_message(self, message: Dict[str, Any]) -> None:
        """Send a message to the public WebSocket."""
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
        """Send a message to the private WebSocket."""
        if not self.is_private_connected or not self.private_ws:
            raise WebSocketError("Private WebSocket not connected")
        raise NotImplementedError("Private WebSocket messaging requires authentication")

    async def listen_public(self) -> AsyncGenerator[Dict[str, Any], None]:
        """Listen for messages from the public WebSocket."""
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

    async def listen_private(self) -> AsyncGenerator[Dict[str, Any], None]:
        """Listen for messages from the private WebSocket."""
        raise NotImplementedError("Private WebSocket listening requires authentication")
        yield

    def get_connection_status(self) -> Dict[str, Any]:
        """Get current connection status."""
        return {
            "public_connected": self.is_public_connected,
            "private_connected": self.is_private_connected,
            "public_subscriptions": list(self.public_subscriptions),
            "private_subscriptions": list(self.private_subscriptions),
            "last_heartbeat": self.last_heartbeat,
            "reconnect_attempts": self.reconnect_attempts,
            "ssl_verify_mode": self.ssl_context.verify_mode.name if hasattr(self.ssl_context.verify_mode, 'name') else str(self.ssl_context.verify_mode),
            "ssl_check_hostname": self.ssl_context.check_hostname,
            "active_subscription_details": self.get_active_subscriptions(),
            "market_data_summary": self.get_market_data_summary()
        }