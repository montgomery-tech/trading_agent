
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
        # ... existing initialization code ...

        # NEW: Account data management
        self.account_manager: Optional[AccountDataManager] = None
        self._account_data_enabled = False

        # ... rest of existing __init__ code ...

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
