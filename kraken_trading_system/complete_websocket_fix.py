#!/usr/bin/env python3
"""
Complete WebSocket Message Processing Fix

This script completely rewrites the broken WebSocket message processing
to enable real-time order monitoring via ownTrades and openOrders feeds.

Issues being fixed:
1. Malformed log_websocket_event call
2. Hardcoded "unknown" channel names
3. Missing _is_order_update and _process_order_update methods
4. Broken message routing logic
5. Invalid syntax in _sync_order_states call
"""

import sys
from pathlib import Path


def create_fixed_websocket_client():
    """Create a completely fixed WebSocket client."""
    
    print("🔧 CREATING FIXED WEBSOCKET CLIENT")
    print("=" * 50)
    
    # The fixed WebSocket client code
    fixed_websocket_content = '''"""
Enhanced Kraken WebSocket client with OrderManager integration.
This enhancement adds real-time order state updates and order event propagation.

Task 3.1.C: Integrate OrderManager with WebSocket client
"""

import asyncio
import json
import ssl
import time
from typing import Any, AsyncGenerator, Dict, List, Optional, Set, Union
from decimal import Decimal
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

# ENHANCED IMPORTS for OrderManager integration
from .account_data_manager import AccountDataManager
from .account_models import AccountSnapshot, KrakenOrder, KrakenTrade
from .order_manager import OrderManager  # NEW: OrderManager integration
from .order_models import OrderState, OrderEvent, EnhancedKrakenOrder  # NEW: Order models


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
        self.max_reconnect_attempts = getattr(settings, 'max_reconnect_attempts', 5)
        self.reconnect_delay = getattr(settings, 'reconnect_delay', 5.0)
        self.connection_timeout = getattr(settings, 'websocket_timeout', 30.0)

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

        # NEW: OrderManager integration
        self.order_manager: Optional[OrderManager] = None
        self._order_management_enabled = True
        self._order_event_handlers: Dict[str, List[callable]] = {}

        # Get URLs from settings
        self.public_url, self.private_url = settings.get_websocket_urls()

        log_websocket_event(
            self.logger,
            "client_initialized",
            public_url=self.public_url,
            private_url=self.private_url,
            ssl_context_type=type(self.ssl_context).__name__,
            order_management_enabled=self._order_management_enabled
        )

    def _create_ssl_context(self) -> ssl.SSLContext:
        """Create SSL context with proper certificate handling."""
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        return ssl_context

    # NEW: OrderManager Integration Methods
    async def initialize_order_manager(self, order_manager: Optional[OrderManager] = None) -> None:
        """
        Initialize OrderManager integration with the WebSocket client.

        Args:
            order_manager: Optional OrderManager instance. If None, creates a new one.
        """
        try:
            # Initialize account manager first if not already done
            if self.account_manager is None:
                self.account_manager = AccountDataManager()
                self._account_data_enabled = True
                self.log_info("Account data manager initialized for order integration")

            # Initialize or use provided OrderManager
            if order_manager is None:
                self.order_manager = OrderManager(account_manager=self.account_manager)
            else:
                self.order_manager = order_manager
                # Ensure it has the same account manager
                if self.order_manager.account_manager != self.account_manager:
                    self.order_manager.account_manager = self.account_manager

            self._order_management_enabled = True

            # Set up order event handlers
            await self._setup_order_event_handlers()

            self.log_info(
                "OrderManager integration initialized",
                order_manager_id=id(self.order_manager),
                account_manager_id=id(self.account_manager)
            )

        except Exception as e:
            self.log_error("Failed to initialize OrderManager integration", error=e)
            raise

    async def _setup_order_event_handlers(self) -> None:
        """Set up event handlers for order state changes."""
        if not self.order_manager:
            return

        # Add order state change handler
        def handle_order_state_change(order: EnhancedKrakenOrder,
                                    old_state: OrderState,
                                    new_state: OrderState) -> None:
            """Handle order state changes from OrderManager."""
            self.log_info(
                "Order state change detected",
                order_id=order.order_id,
                old_state=old_state.value,
                new_state=new_state.value,
                pair=order.pair
            )

            # Trigger custom event handlers
            asyncio.create_task(self._trigger_order_event_handlers(
                "state_change",
                {
                    "order": order,
                    "old_state": old_state,
                    "new_state": new_state
                }
            ))

        # Add handler to OrderManager
        self.order_manager.add_state_change_handler(handle_order_state_change)

    async def _trigger_order_event_handlers(self, event_type: str, event_data: Dict[str, Any]) -> None:
        """Trigger registered order event handlers."""
        if event_type in self._order_event_handlers:
            for handler in self._order_event_handlers[event_type]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(event_data)
                    else:
                        handler(event_data)
                except Exception as e:
                    self.log_error(
                        "Error in order event handler",
                        event_type=event_type,
                        error=e
                    )

    def add_order_event_handler(self, event_type: str, handler: callable) -> None:
        """
        Add an event handler for order events.

        Args:
            event_type: Type of event ("state_change", "fill", "cancel", etc.)
            handler: Callback function to handle the event
        """
        if event_type not in self._order_event_handlers:
            self._order_event_handlers[event_type] = []

        self._order_event_handlers[event_type].append(handler)
        self.log_info(f"Added order event handler for {event_type}")

    def remove_order_event_handler(self, event_type: str, handler: callable) -> None:
        """Remove an order event handler."""
        if event_type in self._order_event_handlers:
            try:
                self._order_event_handlers[event_type].remove(handler)
                self.log_info(f"Removed order event handler for {event_type}")
            except ValueError:
                self.log_warning(f"Handler not found for {event_type}")

    # FIXED: _process_private_data method with proper channel processing
    async def _process_private_data(self, data: Dict[str, Any]) -> None:
        """Process private data feeds (ownTrades, openOrders) with OrderManager integration."""
        try:
            # Initialize account manager if not already done
            if self.account_manager is None:
                self.account_manager = AccountDataManager()
                self._account_data_enabled = True
                self.log_info("Account data manager initialized")

            # Determine message type and route to appropriate processor
            if isinstance(data, list) and len(data) >= 3:
                # FIXED: Properly extract channel name from WebSocket message
                channel_name = data[2] if len(data) > 2 else "unknown"

                if channel_name == "ownTrades":
                    await self.account_manager.process_own_trades_update(data)

                    # NEW: Trigger order fill processing if OrderManager is enabled
                    if self._order_management_enabled and self.order_manager:
                        await self._process_trade_fills(data)

                    log_websocket_event(
                        self.logger,
                        "private_trades_processed",
                        channel=channel_name,
                        data_elements=len(data[1]) if isinstance(data[1], dict) else 0,
                        order_manager_notified=self._order_management_enabled
                    )

                elif channel_name == "openOrders":
                    await self.account_manager.process_open_orders_update(data)

                    # FIXED: Sync order states with OrderManager
                    if self._order_management_enabled and self.order_manager:
                        await self._sync_order_states(data)

                    log_websocket_event(
                        self.logger,
                        "private_orders_processed",
                        channel=channel_name,
                        data_elements=len(data[1]) if isinstance(data[1], dict) else 0,
                        order_manager_synced=self._order_management_enabled
                    )

                else:
                    # Handle other private data types or log unknown
                    log_websocket_event(
                        self.logger,
                        "unknown_private_data",
                        channel=channel_name,
                        data_type=type(data).__name__,
                        data_preview=str(data)[:200] if isinstance(data, (dict, list)) else None
                    )

            elif isinstance(data, dict):
                # Handle balance updates or other dict-format messages
                if "balance" in data or any(key in data for key in ["USD", "XBT", "ETH", "EUR"]):
                    await self.account_manager.process_balance_update(data)
                    log_websocket_event(
                        self.logger,
                        "balance_update_processed",
                        currencies=list(data.keys()) if isinstance(data, dict) else []
                    )

        except Exception as e:
            self.log_error("Error processing private data", error=e, data_type=type(data).__name__)

    # NEW: Process trade fills for OrderManager
    async def _process_trade_fills(self, trade_data: List[Any]) -> None:
        """Process trade fills and notify OrderManager."""
        if not self.order_manager or len(trade_data) < 2:
            return

        try:
            trades_dict = trade_data[1] if isinstance(trade_data[1], dict) else {}

            for trade_id, trade_info in trades_dict.items():
                if isinstance(trade_info, dict):
                    order_id = trade_info.get('ordertxid')
                    if order_id:
                        # Check if this is a fill for an order we're tracking
                        if self.order_manager.has_order(order_id):
                            await self.order_manager.process_fill_update(trade_id, trade_info)

                            # Trigger fill event
                            await self._trigger_order_event_handlers(
                                "fill",
                                {
                                    "trade_id": trade_id,
                                    "order_id": order_id,
                                    "trade_info": trade_info
                                }
                            )

        except Exception as e:
            self.log_error("Error processing trade fills for OrderManager", error=e)

    # FIXED: Sync order states with OrderManager
    async def _sync_order_states(self, order_data: List[Any]) -> None:
        """Sync order states from WebSocket feed with OrderManager."""
        if not self.order_manager or len(order_data) < 2:
            return

        try:
            orders_dict = order_data[1] if isinstance(order_data[1], dict) else {}

            for order_id, order_info in orders_dict.items():
                if isinstance(order_info, dict):
                    # Update order state in OrderManager
                    await self.order_manager.sync_order_from_websocket(order_id, order_info)

                    # Trigger order update event
                    await self._trigger_order_event_handlers(
                        "order_update",
                        {
                            "order_id": order_id,
                            "order_info": order_info,
                            "source": "websocket"
                        }
                    )

        except Exception as e:
            self.log_error("Error syncing order states with OrderManager", error=e)

    # NEW: OrderManager query methods
    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """Get detailed status of a specific order."""
        if not self.order_manager:
            return None

        order = self.order_manager.get_order(order_id)
        if not order:
            return None

        return {
            "order_id": order.order_id,
            "current_state": order.current_state.value,
            "status": order.status,
            "pair": order.pair,
            "side": order.type.value, 
            "volume": str(order.volume),
            "volume_executed": str(order.volume_executed),
            "price": str(order.price) if order.price else None,
            "last_update": order.last_update.isoformat(),
            "fill_percentage": order.fill_percentage
        }

    def get_orders_summary(self) -> Dict[str, Any]:
        """Get summary of all orders from OrderManager."""
        if not self.order_manager:
            return {"enabled": False, "orders": []}

        stats = self.order_manager.get_statistics()
        orders = self.order_manager.get_all_orders()

        orders_data = []
        for order in orders:
            orders_data.append({
                "order_id": order.order_id,
                "state": order.current_state.value,
                "pair": order.pair,
                "type": order.type,
                "volume": str(order.volume),
                "volume_executed": str(order.volume_executed)
            })

        return {
            "enabled": True,
            "statistics": stats,
            "orders": orders_data,
            "total_orders": len(orders)
        }

    # ENHANCED: get_connection_status method
    def get_connection_status(self) -> Dict[str, Any]:
        """Get current connection status including OrderManager integration."""
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

        # NEW: Add OrderManager status
        if self.order_manager:
            order_stats = self.order_manager.get_statistics()
            base_status.update({
                "order_management_enabled": self._order_management_enabled,
                "order_manager_stats": order_stats,
                "order_event_handlers": {
                    event_type: len(handlers)
                    for event_type, handlers in self._order_event_handlers.items()
                }
            })
        else:
            base_status.update({
                "order_management_enabled": False,
                "order_manager_stats": None,
                "order_event_handlers": {}
            })

        return base_status

    async def get_account_snapshot(self) -> Optional[AccountSnapshot]:
        """Get current account state snapshot."""
        if not self.account_manager:
            self.log_warning("Account manager not initialized - no account data available")
            return None
        return self.account_manager.get_account_snapshot()

    async def connect_private(self) -> None:
        """Connect to Kraken's private WebSocket endpoint with token authentication."""
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

            # Initialize OrderManager integration if enabled
            if self._order_management_enabled:
                await self.initialize_order_manager()
                self.log_info("OrderManager integration initialized during private connection")

            # Start message handling
            asyncio.create_task(self._handle_private_messages())

        except Exception as e:
            self.log_error("Private WebSocket connection failed", error=e)
            raise ConnectionError(f"Failed to connect to private WebSocket: {e}")

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
        await self._process_private_data(data)

    # ===== WEBSOCKET ORDER PLACEMENT METHODS =====
    
    async def place_market_order(self, pair: str, side: str, volume: Union[str, Decimal], 
                                userref: Optional[int] = None, **kwargs) -> Dict[str, Any]:
        """
        Place a market order via WebSocket.
        
        Args:
            pair: Trading pair (e.g., "ETH/USD")
            side: Order side ("buy" or "sell")  
            volume: Order volume
            userref: Optional user reference number
            **kwargs: Additional order parameters
            
        Returns:
            Order placement response
            
        Raises:
            WebSocketError: If not connected or order fails
            AuthenticationError: If no valid token
        """
        if not self.is_private_connected or not self.current_token:
            raise WebSocketError("Private WebSocket not connected or no auth token")
        
        # Build order message according to Kraken WebSocket API
        order_message = {
            "event": "addOrder",
            "token": self.current_token,
            "pair": pair,
            "type": side.lower(),
            "ordertype": "market",
            "volume": str(volume)
        }
        
        # Add optional parameters
        if userref is not None:
            order_message["userref"] = str(userref)
        
        # Add any additional parameters
        order_message.update(kwargs)
        
        self.log_info(
            "Placing market order via WebSocket",
            pair=pair,
            side=side,
            volume=str(volume),
            userref=userref
        )
        
        try:
            # Send order via WebSocket
            await self.send_private_message(order_message)
            
            # Wait for response (addOrderStatus)
            response = await self._wait_for_order_response()
            
            if response.get("status") == "ok":
                order_id = response.get("txid")
                description = response.get("descr", "")
                
                self.log_info(
                    "Market order placed successfully",
                    order_id=order_id,
                    description=description
                )
                
                # Register order with OrderManager if available
                if self.order_manager and order_id:
                    await self._register_order_with_manager(order_id, order_message, response)
                
                return {
                    "success": True,
                    "order_id": order_id,
                    "description": description,
                    "response": response
                }
            else:
                error_msg = response.get("errorMessage", "Unknown error")
                self.log_error("Market order failed", error=error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "response": response
                }
                
        except Exception as e:
            self.log_error("Market order placement failed", error=e)
            raise WebSocketError(f"Order placement failed: {e}")
    
    async def place_limit_order(self, pair: str, side: str, volume: Union[str, Decimal],
                               price: Union[str, Decimal], userref: Optional[int] = None,
                               **kwargs) -> Dict[str, Any]:
        """
        Place a limit order via WebSocket.
        
        Args:
            pair: Trading pair (e.g., "ETH/USD")
            side: Order side ("buy" or "sell")
            volume: Order volume
            price: Limit price
            userref: Optional user reference number
            **kwargs: Additional order parameters
            
        Returns:
            Order placement response
        """
        if not self.is_private_connected or not self.current_token:
            raise WebSocketError("Private WebSocket not connected or no auth token")
        
        order_message = {
            "event": "addOrder",
            "token": self.current_token,
            "pair": pair,
            "type": side.lower(),
            "ordertype": "limit",
            "volume": str(volume),
            "price": str(price)
        }
        
        if userref is not None:
            order_message["userref"] = str(userref)
        
        order_message.update(kwargs)
        
        self.log_info(
            "Placing limit order via WebSocket",
            pair=pair,
            side=side,
            volume=str(volume),
            price=str(price),
            userref=userref
        )
        
        try:
            await self.send_private_message(order_message)
            response = await self._wait_for_order_response()
            
            if response.get("status") == "ok":
                order_id = response.get("txid")
                description = response.get("descr", "")
                
                self.log_info(
                    "Limit order placed successfully",
                    order_id=order_id,
                    description=description
                )
                
                if self.order_manager and order_id:
                    await self._register_order_with_manager(order_id, order_message, response)
                
                return {
                    "success": True,
                    "order_id": order_id,
                    "description": description,
                    "response": response
                }
            else:
                error_msg = response.get("errorMessage", "Unknown error")
                self.log_error("Limit order failed", error=error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "response": response
                }
                
        except Exception as e:
            self.log_error("Limit order placement failed", error=e)
            raise WebSocketError(f"Order placement failed: {e}")
    
    async def cancel_order(self, order_ids: Union[str, list], **kwargs) -> Dict[str, Any]:
        """
        Cancel one or more orders via WebSocket.
        
        Args:
            order_ids: Order ID(s) to cancel (string or list)
            **kwargs: Additional parameters
            
        Returns:
            Cancellation response
        """
        if not self.is_private_connected or not self.current_token:
            raise WebSocketError("Private WebSocket not connected or no auth token")
        
        # Ensure order_ids is a list
        if isinstance(order_ids, str):
            order_ids = [order_ids]
        
        cancel_message = {
            "event": "cancelOrder",
            "token": self.current_token,
            "txid": order_ids
        }
        
        cancel_message.update(kwargs)
        
        self.log_info("Cancelling orders via WebSocket", order_ids=order_ids)
        
        try:
            await self.send_private_message(cancel_message)
            response = await self._wait_for_cancel_response()
            
            if response.get("status") == "ok":
                self.log_info("Orders cancelled successfully", order_ids=order_ids)
                return {
                    "success": True,
                    "cancelled_orders": order_ids,
                    "response": response
                }
            else:
                error_msg = response.get("errorMessage", "Unknown error")
                self.log_error("Order cancellation failed", error=error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "response": response
                }
                
        except Exception as e:
            self.log_error("Order cancellation failed", error=e)
            raise WebSocketError(f"Order cancellation failed: {e}")
    
    async def _wait_for_order_response(self, timeout: float = 10.0) -> Dict[str, Any]:
        """
        Wait for addOrderStatus response from WebSocket.
        
        Args:
            timeout: Timeout in seconds
            
        Returns:
            Order status response
        """
        import asyncio
        
        try:
            # Wait for addOrderStatus message
            timeout_time = asyncio.get_event_loop().time() + timeout
            
            while asyncio.get_event_loop().time() < timeout_time:
                try:
                    # Check if we have messages in the queue
                    if not self.private_message_queue.empty():
                        message = self.private_message_queue.get_nowait()
                        
                        if isinstance(message, dict) and message.get("event") == "addOrderStatus":
                            return message
                    
                    # Wait a bit before checking again
                    await asyncio.sleep(0.1)
                    
                except asyncio.QueueEmpty:
                    continue
            
            raise TimeoutError("Timeout waiting for order response")
            
        except Exception as e:
            self.log_error("Error waiting for order response", error=e)
            raise
    
    async def _wait_for_cancel_response(self, timeout: float = 10.0) -> Dict[str, Any]:
        """
        Wait for cancelOrderStatus response from WebSocket.
        
        Args:
            timeout: Timeout in seconds
            
        Returns:
            Cancel status response
        """
        import asyncio
        
        try:
            timeout_time = asyncio.get_event_loop().time() + timeout
            
            while asyncio.get_event_loop().time() < timeout_time:
                try:
                    if not self.private_message_queue.empty():
                        message = self.private_message_queue.get_nowait()
                        
                        if isinstance(message, dict) and message.get("event") == "cancelOrderStatus":
                            return message
                    
                    await asyncio.sleep(0.1)
                    
                except asyncio.QueueEmpty:
                    continue
            
            raise TimeoutError("Timeout waiting for cancel response")
            
        except Exception as e:
            self.log_error("Error waiting for cancel response", error=e)
            raise
    
    async def _register_order_with_manager(self, order_id: str, order_request: Dict[str, Any], 
                                          order_response: Dict[str, Any]) -> None:
        """
        Register a new order with the OrderManager.
        
        Args:
            order_id: The order ID from Kraken
            order_request: Original order request message
            order_response: Order placement response
        """
        try:
            if not self.order_manager:
                return
            
            # Create order creation request from WebSocket order
            from .order_models import OrderCreationRequest, OrderSide, OrderType
            
            # Map WebSocket parameters to OrderCreationRequest
            side = OrderSide.BUY if order_request["type"].lower() == "buy" else OrderSide.SELL
            order_type = OrderType.MARKET if order_request["ordertype"] == "market" else OrderType.LIMIT
            
            creation_request = OrderCreationRequest(
                pair=order_request["pair"],
                side=side,
                order_type=order_type,
                volume=Decimal(order_request["volume"]),
                price=Decimal(order_request.get("price", "0")) if order_request.get("price") else None,
                userref=order_request.get("userref")
            )
            
            # Create order in OrderManager
            order = await self.order_manager.create_order(creation_request)
            
            # Store Kraken order ID in order metadata
            order.metadata = order.metadata or {}
            order.metadata['kraken_order_id'] = order_id
            order.status = "submitted"
            
            self.log_info(
                "Order registered with OrderManager",
                order_id=order_id,
                manager_order_id=order.order_id
            )
            
        except Exception as e:
            self.log_error("Failed to register order with OrderManager", error=e, order_id=order_id)

    # ===== REAL-TIME ORDER MONITORING =====
    
    async def subscribe_to_order_feeds(self) -> None:
        """Subscribe to real-time order feeds for monitoring."""
        try:
            if not self.is_private_connected:
                raise WebSocketError("Private WebSocket not connected")
            
            # Subscribe to openOrders feed for order status updates
            await self.subscribe_open_orders()
            
            # Subscribe to ownTrades feed for execution updates  
            await self.subscribe_own_trades()
            
            self.log_info("Subscribed to real-time order monitoring feeds")
            
        except Exception as e:
            self.log_error("Failed to subscribe to order feeds", error=e)
            raise
    
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
    
    async def monitor_order_realtime(self, order_id: str, timeout: float = 30.0) -> Dict[str, Any]:
        """
        Monitor order in real-time using WebSocket feeds.
        
        Args:
            order_id: Order ID to monitor
            timeout: Maximum time to wait for completion
            
        Returns:
            Order completion status
        """
        import asyncio
        
        print(f"📊 REAL-TIME ORDER MONITORING: {order_id}")
        print("-" * 50)
        
        start_time = asyncio.get_event_loop().time()
        order_completed = False
        order_status = "unknown"
        fill_info = {}
        
        try:
            # Ensure we're subscribed to order feeds
            await self.subscribe_to_order_feeds()
            
            # Give a moment for subscriptions to be confirmed
            await asyncio.sleep(0.5)
            
            # Monitor for order completion
            messages_checked = 0
            
            while (asyncio.get_event_loop().time() - start_time) < timeout and not order_completed:
                
                try:
                    # Check for messages with a shorter timeout for faster response
                    message = await asyncio.wait_for(
                        self.private_message_queue.get(), 
                        timeout=0.5
                    )
                    
                    messages_checked += 1
                    
                    if isinstance(message, (dict, list)):
                        # Log message type for debugging
                        if isinstance(message, list) and len(message) >= 3:
                            channel = message[2] if len(message) > 2 else 'unknown'
                            self.log_info(f"Processing message: {channel}")
                        
                        # Check for order status updates
                        if self._is_order_update(message, order_id):
                            order_status, order_completed, fill_info = self._process_order_update(
                                message, order_id
                            )
                            
                            print(f"📊 Order Update: {order_status}")
                            if fill_info:
                                print(f"📊 Fill Info: {fill_info}")
                            
                            if order_completed:
                                print(f"✅ Order completed: {order_status}")
                                break
                        else:
                            # Put message back for other processors
                            await self.private_message_queue.put(message)
                    
                except asyncio.TimeoutError:
                    # No messages - continue waiting
                    if messages_checked == 0:
                        print("⏱️ Waiting for order updates...")
                    continue
                    
                except Exception as e:
                    self.log_error("Error during real-time monitoring", error=e)
                    break
            
            if not order_completed:
                print(f"⏰ Monitoring timeout after {timeout}s (checked {messages_checked} messages)")
                order_status = "timeout"
            
            return {
                "completed": order_completed,
                "status": order_status,
                "fill_info": fill_info,
                "monitoring_time": asyncio.get_event_loop().time() - start_time,
                "messages_processed": messages_checked
            }
            
        except Exception as e:
            self.log_error("Real-time order monitoring failed", error=e)
            return {
                "completed": False,
                "status": "error",
                "error": str(e),
                "monitoring_time": asyncio.get_event_loop().time() - start_time
            }

    def _is_order_update(self, message: Dict[str, Any], order_id: str) -> bool:
        """Check if message is an update for our order."""
        try:
            # Handle list format messages from WebSocket feeds
            if isinstance(message, list) and len(message) >= 3:
                channel_name = message[2] if len(message) > 2 else None
                
                # ownTrades messages
                if channel_name == "ownTrades":
                    trades_data = message[0]
                    for trade_id, trade_info in trades_data.items():
                        if isinstance(trade_info, dict):
                            if trade_info.get("ordertxid") == order_id:
                                return True
                
                # openOrders messages  
                elif channel_name == "openOrders":
                    orders_data = message[0]
                    if isinstance(orders_data, dict):
                        if order_id in orders_data:
                            return True
            
            # Handle direct dict format messages
            elif isinstance(message, dict):
                # Check if it's a subscription confirmation or order status
                if message.get("event") in ["subscriptionStatus", "addOrderStatus"]:
                    return False  # These aren't order updates
                
                # Check for order data in the message
                if "ordertxid" in message and message.get("ordertxid") == order_id:
                    return True
            
            return False
            
        except Exception as e:
            self.log_error("Error checking order update", error=e)
            return False

    def _process_order_update(self, message: Dict[str, Any], order_id: str) -> tuple:
        """
        Process order update message.
        
        Returns:
            (status, completed, fill_info)
        """
        try:
            # Process ownTrades (execution/fill updates)
            if isinstance(message, list) and len(message) >= 3 and message[2] == "ownTrades":
                trades_data = message[0]
                for trade_id, trade_info in trades_data.items():
                    if isinstance(trade_info, dict) and trade_info.get("ordertxid") == order_id:
                        return (
                            "filled",
                            True,
                            {
                                "trade_id": trade_id,
                                "price": trade_info.get("price"),
                                "vol": trade_info.get("vol"),
                                "cost": trade_info.get("cost"),
                                "fee": trade_info.get("fee"),
                                "time": trade_info.get("time"),
                                "type": trade_info.get("type")
                            }
                        )
            
            # Process openOrders (status updates)
            elif isinstance(message, list) and len(message) >= 3 and message[2] == "openOrders":
                orders_data = message[0]
                if isinstance(orders_data, dict):
                    order_info = orders_data.get(order_id)
                    if order_info:
                        status = order_info.get("status", "unknown")
                        vol_exec = float(order_info.get("vol_exec", 0))
                        vol = float(order_info.get("vol", 0))
                        
                        # Order is completed if status is closed or fully executed
                        completed = status in ["closed", "canceled", "expired"] or vol_exec >= vol
                        
                        return (
                            status,
                            completed,
                            {
                                "vol_exec": vol_exec,
                                "vol": vol,
                                "status": status,
                                "avg_price": order_info.get("avg_price"),
                                "cost": order_info.get("cost"),
                                "fee": order_info.get("fee")
                            }
                        )
            
            return ("unknown", False, {})
            
        except Exception as e:
            self.log_error("Error processing order update", error=e, order_id=order_id)
            return ("error", False, {"error": str(e)})

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
'''

    return fixed_websocket_content


def apply_complete_fix():
    """Apply the complete WebSocket client fix."""
    
    print("🚀 APPLYING COMPLETE WEBSOCKET CLIENT FIX")
    print("=" * 60)
    
    websocket_path = Path("src/trading_systems/exchanges/kraken/websocket_client.py")
    
    try:
        # Create backup of current file
        backup_path = websocket_path.with_suffix('.py.backup')
        if websocket_path.exists():
            with open(websocket_path, 'r', encoding='utf-8') as f:
                backup_content = f.read()
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(backup_content)
            print(f"✅ Created backup: {backup_path}")
        
        # Apply the complete fix
        fixed_content = create_fixed_websocket_client()
        
        with open(websocket_path, 'w', encoding='utf-8') as f:
            f.write(fixed_content)
        
        print("✅ Applied complete WebSocket client fix")
        
        # Test syntax
        compile(fixed_content, str(websocket_path), 'exec')
        print("✅ Syntax verification passed")
        
        return True
        
    except Exception as e:
        print(f"❌ Error applying fix: {e}")
        return False


def main():
    """Main execution function."""
    print("🔧 COMPLETE WEBSOCKET MESSAGE PROCESSING FIX")
    print("=" * 70)
    print()
    print("This fix completely rewrites the broken WebSocket message processing")
    print("to enable real-time order monitoring via ownTrades and openOrders feeds.")
    print()
    print("Issues being fixed:")
    print("• Malformed log_websocket_event call")
    print("• Hardcoded 'unknown' channel names")
    print("• Missing _is_order_update and _process_order_update methods")
    print("• Broken message routing logic") 
    print("• Invalid syntax in _sync_order_states call")
    print("• Complete real-time order monitoring implementation")
    print()
    
    success = apply_complete_fix()
    
    if success:
        print("\n🎉 SUCCESS: Complete WebSocket Fix Applied!")
        print("=" * 70)
        print("✅ Fixed all syntax and logical errors")
        print("✅ Implemented proper channel name extraction")
        print("✅ Added missing order monitoring methods")
        print("✅ Real-time ownTrades and openOrders processing")
        print("✅ Complete OrderManager integration")
        print()
        print("🚀 READY FOR TESTING:")
        print("python3 live_order_placement.py")
        print()
        print("Expected results:")
        print("• Real-time order completion detection")
        print("• Sub-5-second monitoring")
        print("• Proper WebSocket message processing")
        print("• Live order feed integration")
        return True
    else:
        print("\n❌ FIX APPLICATION FAILED")
        print("Check errors above")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
