"""
Account Data Manager for Kraken Trading System.

Manages real-time account state including orders, trades, and balances.
Integrates with the WebSocket client to provide structured account data access.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from collections import defaultdict, deque

from ...utils.logger import LoggerMixin
from .account_models import (
    AccountBalance,
    AccountSnapshot,
    KrakenOrder,
    KrakenTrade,
    OrderStatus,
    parse_open_orders_message,
    parse_own_trades_message
)


class AccountDataManager(LoggerMixin):
    """
    Manages real-time account data from Kraken private WebSocket feeds.
    
    This class:
    - Processes real-time account data updates
    - Maintains current account state
    - Provides query interfaces for account data
    - Tracks order and trade history
    """
    
    def __init__(self, max_trade_history: int = 1000, max_order_history: int = 500):
        super().__init__()
        
        # Current account state
        self._current_balances: Dict[str, AccountBalance] = {}
        self._open_orders: Dict[str, KrakenOrder] = {}
        
        # Historical data
        self._trade_history: deque = deque(maxlen=max_trade_history)
        self._order_history: deque = deque(maxlen=max_order_history)
        
        # Data organization for quick queries
        self._trades_by_pair: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self._orders_by_pair: Dict[str, Set[str]] = defaultdict(set)
        
        # State tracking
        self._last_update = datetime.now()
        self._update_count = 0
        self._initialization_complete = False
        
        # Statistics
        self._stats = {
            'total_trades_processed': 0,
            'total_orders_processed': 0,
            'balance_updates': 0,
            'last_trade_time': None,
            'last_order_update': None
        }
        
        self.log_info("Account data manager initialized", 
                     max_trade_history=max_trade_history,
                     max_order_history=max_order_history)
    
    async def process_own_trades_update(self, message_data: Dict[str, Any]) -> None:
        """
        Process ownTrades WebSocket message and update trade history.
        
        Args:
            message_data: Raw ownTrades message from Kraken WebSocket
        """
        try:
            trades = parse_own_trades_message(message_data)
            
            if not trades:
                self.log_info("No trades found in ownTrades message")
                return
            
            for trade in trades:
                # Add to trade history
                self._trade_history.append(trade)
                self._trades_by_pair[trade.pair].append(trade)
                
                # Update statistics
                self._stats['total_trades_processed'] += 1
                self._stats['last_trade_time'] = trade.time
                
                self.log_info(
                    "Trade processed",
                    trade_id=trade.trade_id,
                    pair=trade.pair,
                    type=trade.type,
                    volume=str(trade.volume),
                    price=str(trade.price),
                    fee=str(trade.fee)
                )
            
            self._last_update = datetime.now()
            self._update_count += 1
            
            self.log_info(f"Processed {len(trades)} trades from ownTrades update")
            
        except Exception as e:
            self.log_error("Failed to process ownTrades update", error=e)
    
    async def process_open_orders_update(self, message_data: Dict[str, Any]) -> None:
        """
        Process openOrders WebSocket message and update order state.
        
        Args:
            message_data: Raw openOrders message from Kraken WebSocket
        """
        try:
            orders = parse_open_orders_message(message_data)
            
            if not orders:
                self.log_info("No orders found in openOrders message")
                return
            
            for order in orders:
                old_order = self._open_orders.get(order.order_id)
                
                # Update order state
                self._open_orders[order.order_id] = order
                self._orders_by_pair[order.pair].add(order.order_id)
                
                # Track order changes
                if old_order:
                    if old_order.volume_executed != order.volume_executed:
                        self.log_info(
                            "Order execution update",
                            order_id=order.order_id,
                            pair=order.pair,
                            old_executed=str(old_order.volume_executed),
                            new_executed=str(order.volume_executed),
                            fill_percentage=f"{order.fill_percentage:.2f}%"
                        )
                    
                    if old_order.status != order.status:
                        self.log_info(
                            "Order status change",
                            order_id=order.order_id,
                            pair=order.pair,
                            old_status=old_order.status,
                            new_status=order.status
                        )
                else:
                    self.log_info(
                        "New order detected",
                        order_id=order.order_id,
                        pair=order.pair,
                        type=order.type,
                        order_type=order.order_type,
                        volume=str(order.volume),
                        price=str(order.price) if order.price else "market"
                    )
                
                # Move completed orders to history
                if order.status in [OrderStatus.CLOSED, OrderStatus.CANCELED, OrderStatus.EXPIRED]:
                    if order.order_id in self._open_orders:
                        self._order_history.append(order)
                        del self._open_orders[order.order_id]
                        self._orders_by_pair[order.pair].discard(order.order_id)
                        
                        self.log_info(
                            "Order moved to history",
                            order_id=order.order_id,
                            final_status=order.status,
                            fill_percentage=f"{order.fill_percentage:.2f}%"
                        )
                
                # Update statistics
                self._stats['total_orders_processed'] += 1
                self._stats['last_order_update'] = datetime.now()
            
            self._last_update = datetime.now()
            self._update_count += 1
            
            self.log_info(f"Processed {len(orders)} orders from openOrders update")
            
        except Exception as e:
            self.log_error("Failed to process openOrders update", error=e)
    
    async def process_balance_update(self, balance_data: Dict[str, Any]) -> None:
        """
        Process account balance update.
        
        Args:
            balance_data: Balance update data
        """
        try:
            for currency, balance_info in balance_data.items():
                if isinstance(balance_info, dict):
                    balance = AccountBalance(
                        currency=currency,
                        balance=balance_info.get('balance', '0'),
                        hold=balance_info.get('hold', '0'),
                        available=balance_info.get('available')
                    )
                    
                    old_balance = self._current_balances.get(currency)
                    self._current_balances[currency] = balance
                    
                    if old_balance and old_balance.balance != balance.balance:
                        self.log_info(
                            "Balance change detected",
                            currency=currency,
                            old_balance=str(old_balance.balance),
                            new_balance=str(balance.balance),
                            change=str(balance.balance - old_balance.balance)
                        )
                    
                    self._stats['balance_updates'] += 1
            
            self._last_update = datetime.now()
            self.log_info(f"Processed balance update for {len(balance_data)} currencies")
            
        except Exception as e:
            self.log_error("Failed to process balance update", error=e)
    
    # QUERY INTERFACE METHODS
    
    def get_current_balances(self) -> Dict[str, AccountBalance]:
        """Get current account balances."""
        return self._current_balances.copy()
    
    def get_balance(self, currency: str) -> Optional[AccountBalance]:
        """Get balance for specific currency."""
        return self._current_balances.get(currency.upper())
    
    def get_open_orders(self) -> Dict[str, KrakenOrder]:
        """Get all current open orders."""
        return self._open_orders.copy()
    
    def get_order(self, order_id: str) -> Optional[KrakenOrder]:
        """Get specific order by ID."""
        return self._open_orders.get(order_id)
    
    def get_orders_for_pair(self, pair: str) -> List[KrakenOrder]:
        """Get all open orders for a specific trading pair."""
        order_ids = self._orders_by_pair.get(pair, set())
        return [self._open_orders[oid] for oid in order_ids if oid in self._open_orders]
    
    def get_recent_trades(self, limit: int = 50) -> List[KrakenTrade]:
        """Get recent trades, most recent first."""
        trades = list(self._trade_history)
        trades.sort(key=lambda t: t.time, reverse=True)
        return trades[:limit]
    
    def get_trades_for_pair(self, pair: str, limit: int = 50) -> List[KrakenTrade]:
        """Get recent trades for specific pair."""
        pair_trades = list(self._trades_by_pair.get(pair, []))
        pair_trades.sort(key=lambda t: t.time, reverse=True)
        return pair_trades[:limit]
    
    def get_order_history(self, limit: int = 100) -> List[KrakenOrder]:
        """Get historical orders (completed/canceled)."""
        history = list(self._order_history)
        history.sort(key=lambda o: o.last_update, reverse=True)
        return history[:limit]
    
    def get_account_snapshot(self) -> AccountSnapshot:
        """Get complete account state snapshot."""
        return AccountSnapshot(
            timestamp=datetime.now(),
            balances=self._current_balances.copy(),
            open_orders=self._open_orders.copy(),
            recent_trades=self.get_recent_trades(100)
        )
    
    def get_trading_summary(self, pair: Optional[str] = None, hours: int = 24) -> Dict[str, Any]:
        """
        Get trading summary for the specified time period.
        
        Args:
            pair: Trading pair to filter by (None for all pairs)
            hours: Number of hours to look back
            
        Returns:
            Dictionary with trading statistics
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        # Filter trades by time and pair
        if pair:
            recent_trades = [t for t in self._trades_by_pair.get(pair, []) if t.time >= cutoff_time]
        else:
            recent_trades = [t for t in self._trade_history if t.time >= cutoff_time]
        
        if not recent_trades:
            return {
                'pair': pair or 'ALL',
                'period_hours': hours,
                'total_trades': 0,
                'total_volume': '0',
                'total_fees': '0',
                'buy_trades': 0,
                'sell_trades': 0,
                'avg_price': None,
                'first_trade_time': None,
                'last_trade_time': None
            }
        
        # Calculate statistics
        from decimal import Decimal
        total_volume = sum(t.volume for t in recent_trades)
        total_fees = sum(t.fee for t in recent_trades)
        buy_trades = len([t for t in recent_trades if t.type == 'buy'])
        sell_trades = len([t for t in recent_trades if t.type == 'sell'])
        
        # Volume-weighted average price
        volume_price_sum = sum(t.volume * t.price for t in recent_trades)
        avg_price = volume_price_sum / total_volume if total_volume > 0 else Decimal('0')
        
        return {
            'pair': pair or 'ALL',
            'period_hours': hours,
            'total_trades': len(recent_trades),
            'total_volume': str(total_volume),
            'total_fees': str(total_fees),
            'buy_trades': buy_trades,
            'sell_trades': sell_trades,
            'avg_price': str(avg_price),
            'first_trade_time': min(t.time for t in recent_trades),
            'last_trade_time': max(t.time for t in recent_trades)
        }
    
    def get_position_summary(self) -> Dict[str, Any]:
        """
        Get current position summary based on balances and open orders.
        
        Returns:
            Dictionary with position information
        """
        positions = {}
        
        for currency, balance in self._current_balances.items():
            if balance.balance > 0 or balance.hold > 0:
                # Count open orders for this currency
                buy_orders = 0
                sell_orders = 0
                total_buy_volume = Decimal('0')
                total_sell_volume = Decimal('0')
                
                for order in self._open_orders.values():
                    # Check if this order involves the currency
                    base_currency = order.pair.split('/')[0] if '/' in order.pair else order.pair[:3]
                    quote_currency = order.pair.split('/')[1] if '/' in order.pair else order.pair[3:]
                    
                    if base_currency == currency:
                        if order.type == 'sell':
                            sell_orders += 1
                            total_sell_volume += order.volume_remaining
                        elif order.type == 'buy':
                            buy_orders += 1
                            total_buy_volume += order.volume_remaining
                
                positions[currency] = {
                    'balance': str(balance.balance),
                    'available': str(balance.available_balance),
                    'hold': str(balance.hold),
                    'open_buy_orders': buy_orders,
                    'open_sell_orders': sell_orders,
                    'buy_volume_pending': str(total_buy_volume),
                    'sell_volume_pending': str(total_sell_volume)
                }
        
        return positions
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get account data manager statistics."""
        return {
            **self._stats,
            'current_open_orders': len(self._open_orders),
            'total_currencies': len(self._current_balances),
            'trade_history_size': len(self._trade_history),
            'order_history_size': len(self._order_history),
            'last_update': self._last_update.isoformat(),
            'update_count': self._update_count,
            'initialization_complete': self._initialization_complete,
            'tracked_pairs': list(self._trades_by_pair.keys())
        }
    
    def mark_initialization_complete(self) -> None:
        """Mark account data initialization as complete."""
        self._initialization_complete = True
        self.log_info(
            "Account data initialization complete",
            open_orders=len(self._open_orders),
            currencies=len(self._current_balances),
            trade_history=len(self._trade_history)
        )
    
    def reset_data(self) -> None:
        """Reset all account data (for testing or reconnection scenarios)."""
        self.log_info("Resetting account data")
        
        self._current_balances.clear()
        self._open_orders.clear()
        self._trade_history.clear()
        self._order_history.clear()
        self._trades_by_pair.clear()
        self._orders_by_pair.clear()
        
        self._last_update = datetime.now()
        self._update_count = 0
        self._initialization_complete = False
        
        # Reset statistics
        self._stats = {
            'total_trades_processed': 0,
            'total_orders_processed': 0,
            'balance_updates': 0,
            'last_trade_time': None,
            'last_order_update': None
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on account data manager.
        
        Returns:
            Health status information
        """
        now = datetime.now()
        time_since_update = (now - self._last_update).total_seconds()
        
        # Determine health status
        if not self._initialization_complete:
            status = "initializing"
        elif time_since_update > 300:  # 5 minutes without update
            status = "stale"
        elif time_since_update > 60:   # 1 minute without update
            status = "warning"
        else:
            status = "healthy"
        
        return {
            'status': status,
            'last_update_seconds_ago': int(time_since_update),
            'initialization_complete': self._initialization_complete,
            'data_counts': {
                'open_orders': len(self._open_orders),
                'balances': len(self._current_balances),
                'trade_history': len(self._trade_history),
                'order_history': len(self._order_history)
            },
            'update_statistics': self._stats
        }
