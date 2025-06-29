#!/usr/bin/env python3
"""
Task 3.3.B.1: Enhanced Fill Data Models and Processing System

This module implements comprehensive fill processing capabilities with advanced
analytics, detailed fill tracking, and sophisticated execution metrics.

File: src/trading_systems/exchanges/kraken/fill_processor.py
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Tuple
from pydantic import BaseModel, Field, validator
import statistics
from collections import defaultdict

# Imports for integration
try:
    from .order_models import EnhancedKrakenOrder, OrderState, OrderEvent
    from ...utils.logger import get_logger
except ImportError:
    # Fallback for testing
    try:
        from trading_systems.utils.logger import get_logger
    except ImportError:
        # Mock logger for testing
        class MockLogger:
            def info(self, msg, **kwargs): print(f"INFO: {msg} {kwargs}")
            def warning(self, msg, **kwargs): print(f"WARN: {msg} {kwargs}")
            def error(self, msg, **kwargs): print(f"ERROR: {msg} {kwargs}")
        def get_logger(name): return MockLogger()


class FillType(Enum):
    """Types of order fills."""
    MAKER = "maker"           # Fill that provided liquidity
    TAKER = "taker"          # Fill that removed liquidity
    AGGRESSIVE = "aggressive" # Aggressive market order fill
    PASSIVE = "passive"       # Passive limit order fill
    UNKNOWN = "unknown"       # Type not determined


class FillQuality(Enum):
    """Quality classification of fills."""
    EXCELLENT = "excellent"   # Price improvement > 0.05%
    GOOD = "good"            # Price improvement 0.01% - 0.05%
    FAIR = "fair"            # Price improvement 0% - 0.01%
    POOR = "poor"            # Slippage 0% - 0.05%
    BAD = "bad"              # Slippage > 0.05%


class TradeFill(BaseModel):
    """Detailed representation of a single trade fill."""

    # Core identification
    trade_id: str = Field(..., description="Unique trade identifier")
    order_id: str = Field(..., description="Associated order ID")

    # Execution details
    timestamp: datetime = Field(default_factory=datetime.now, description="Fill timestamp")
    volume: Decimal = Field(..., description="Volume filled")
    price: Decimal = Field(..., description="Fill price")
    fee: Decimal = Field(Decimal('0'), description="Trading fee")
    cost: Decimal = Field(..., description="Total cost (volume * price)")

    # Market context
    pair: str = Field(..., description="Trading pair")
    side: str = Field(..., description="Order side (buy/sell)")
    fill_type: FillType = Field(FillType.UNKNOWN, description="Type of fill")

    # Quality metrics
    reference_price: Optional[Decimal] = Field(None, description="Reference price at fill time")
    price_improvement: Optional[Decimal] = Field(None, description="Price improvement amount")
    slippage: Optional[Decimal] = Field(None, description="Slippage amount")
    fill_quality: FillQuality = Field(FillQuality.FAIR, description="Fill quality rating")

    # Additional context
    market_conditions: Dict[str, Any] = Field(default_factory=dict, description="Market conditions at fill")
    liquidity_consumed: Optional[Decimal] = Field(None, description="Liquidity consumed")

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {
            Decimal: str,
            datetime: lambda v: v.isoformat()
        }


@dataclass
class FillAnalytics:
    """Comprehensive fill analytics and metrics."""

    # Basic execution metrics
    total_fills: int = 0
    total_volume: Decimal = Decimal('0')
    total_cost: Decimal = Decimal('0')
    total_fees: Decimal = Decimal('0')

    # Price metrics
    volume_weighted_average_price: Optional[Decimal] = None
    best_fill_price: Optional[Decimal] = None
    worst_fill_price: Optional[Decimal] = None
    price_variance: Optional[Decimal] = None

    # Quality metrics
    total_price_improvement: Decimal = Decimal('0')
    total_slippage: Decimal = Decimal('0')
    implementation_shortfall: Optional[Decimal] = None

    # Timing metrics
    first_fill_time: Optional[datetime] = None
    last_fill_time: Optional[datetime] = None
    fill_duration: Optional[timedelta] = None
    average_fill_interval: Optional[timedelta] = None

    # Fill distribution
    fill_sizes: List[Decimal] = field(default_factory=list)
    fill_prices: List[Decimal] = field(default_factory=list)
    fill_types_distribution: Dict[FillType, int] = field(default_factory=lambda: defaultdict(int))

    def calculate_metrics(self) -> None:
        """Calculate derived metrics from fill data."""
        if self.total_fills == 0:
            return

        # Calculate VWAP
        if self.total_volume > 0:
            self.volume_weighted_average_price = self.total_cost / self.total_volume

        # Calculate timing metrics
        if self.first_fill_time and self.last_fill_time:
            self.fill_duration = self.last_fill_time - self.first_fill_time
            if self.total_fills > 1:
                total_seconds = self.fill_duration.total_seconds()
                self.average_fill_interval = timedelta(seconds=total_seconds / (self.total_fills - 1))

        # Calculate price variance
        if len(self.fill_prices) > 1:
            prices_float = [float(p) for p in self.fill_prices]
            self.price_variance = Decimal(str(statistics.variance(prices_float)))


class FillProcessor:
    """Enhanced fill processing system with advanced analytics."""

    def __init__(self, logger_name: str = "FillProcessor"):
        """Initialize the fill processor."""
        self.logger = get_logger(logger_name)

        # Fill storage and tracking
        self._fills: Dict[str, TradeFill] = {}  # trade_id -> TradeFill
        self._order_fills: Dict[str, List[str]] = defaultdict(list)  # order_id -> [trade_ids]

        # Analytics tracking
        self._order_analytics: Dict[str, FillAnalytics] = {}  # order_id -> FillAnalytics

        # Event handlers
        self._fill_handlers: List[Callable[[TradeFill], None]] = []
        self._analytics_handlers: List[Callable[[str, FillAnalytics], None]] = []

        # Configuration
        self.enable_quality_analysis = True
        self.enable_market_context = True
        self.price_precision = Decimal('0.01')

        self.logger.info("FillProcessor initialized",
                        quality_analysis=self.enable_quality_analysis,
                        market_context=self.enable_market_context)

    async def process_fill(self,
                          trade_id: str,
                          order_id: str,
                          volume: Decimal,
                          price: Decimal,
                          fee: Decimal = Decimal('0'),
                          timestamp: Optional[datetime] = None,
                          trade_info: Optional[Dict[str, Any]] = None) -> TradeFill:
        """
        Process a new fill with comprehensive analysis.

        Args:
            trade_id: Unique trade identifier
            order_id: Associated order ID
            volume: Volume filled
            price: Fill price
            fee: Trading fee
            timestamp: Fill timestamp
            trade_info: Additional trade information

        Returns:
            Processed TradeFill object
        """
        try:
            # Create basic fill object
            fill = TradeFill(
                trade_id=trade_id,
                order_id=order_id,
                timestamp=timestamp or datetime.now(),
                volume=volume,
                price=price,
                fee=fee,
                cost=volume * price,
                pair=trade_info.get('pair', 'UNKNOWN') if trade_info else 'UNKNOWN',
                side=trade_info.get('type', 'UNKNOWN') if trade_info else 'UNKNOWN'
            )

            # Enhanced analysis if enabled
            if self.enable_quality_analysis:
                await self._analyze_fill_quality(fill, trade_info)

            if self.enable_market_context:
                await self._capture_market_context(fill, trade_info)

            # Store fill
            self._fills[trade_id] = fill
            self._order_fills[order_id].append(trade_id)

            # Update analytics
            await self._update_order_analytics(order_id, fill)

            # Trigger event handlers
            await self._trigger_fill_handlers(fill)

            self.logger.info("Fill processed",
                           trade_id=trade_id,
                           order_id=order_id,
                           volume=str(volume),
                           price=str(price),
                           quality=fill.fill_quality.value)

            return fill

        except Exception as e:
            self.logger.error("Error processing fill",
                            trade_id=trade_id,
                            order_id=order_id,
                            error=str(e))
            raise

    async def _analyze_fill_quality(self, fill: TradeFill, trade_info: Optional[Dict[str, Any]]) -> None:
        """Analyze fill quality with price improvement/slippage calculation."""
        try:
            # Determine fill type
            fill.fill_type = self._determine_fill_type(trade_info)

            # Calculate price improvement/slippage if reference price available
            if trade_info and 'reference_price' in trade_info:
                fill.reference_price = Decimal(str(trade_info['reference_price']))

                if fill.side == 'buy':
                    # For buys, lower price is better
                    fill.price_improvement = fill.reference_price - fill.price
                else:
                    # For sells, higher price is better
                    fill.price_improvement = fill.price - fill.reference_price

                # Calculate slippage (always positive)
                fill.slippage = abs(fill.price_improvement) if fill.price_improvement < 0 else Decimal('0')

                # Determine fill quality
                fill.fill_quality = self._classify_fill_quality(fill.price_improvement, fill.reference_price)

        except Exception as e:
            self.logger.warning("Failed to analyze fill quality",
                              trade_id=fill.trade_id,
                              error=str(e))

    def _determine_fill_type(self, trade_info: Optional[Dict[str, Any]]) -> FillType:
        """Determine the type of fill based on trade information."""
        if not trade_info:
            return FillType.UNKNOWN

        # Check for maker/taker indicators
        if 'maker' in trade_info:
            return FillType.MAKER if trade_info['maker'] else FillType.TAKER

        # Check order type
        order_type = trade_info.get('ordertype', '').lower()
        if order_type == 'market':
            return FillType.AGGRESSIVE
        elif order_type in ['limit', 'stop-limit']:
            return FillType.PASSIVE

        return FillType.UNKNOWN

    def _classify_fill_quality(self, price_improvement: Decimal, reference_price: Decimal) -> FillQuality:
        """Classify fill quality based on price improvement."""
        if reference_price == 0:
            return FillQuality.FAIR

        improvement_pct = (price_improvement / reference_price) * 100

        if improvement_pct > Decimal('0.05'):
            return FillQuality.EXCELLENT
        elif improvement_pct > Decimal('0.01'):
            return FillQuality.GOOD
        elif improvement_pct >= Decimal('0'):
            return FillQuality.FAIR
        elif improvement_pct > Decimal('-0.05'):
            return FillQuality.POOR
        else:
            return FillQuality.BAD

    async def _capture_market_context(self, fill: TradeFill, trade_info: Optional[Dict[str, Any]]) -> None:
        """Capture market context at time of fill."""
        try:
            if trade_info:
                fill.market_conditions = {
                    'orderbook_spread': trade_info.get('spread'),
                    'market_impact': trade_info.get('market_impact'),
                    'volume_at_level': trade_info.get('volume_at_level'),
                    'timestamp': fill.timestamp.isoformat()
                }

                fill.liquidity_consumed = trade_info.get('liquidity_consumed')

        except Exception as e:
            self.logger.warning("Failed to capture market context",
                              trade_id=fill.trade_id,
                              error=str(e))

    async def _update_order_analytics(self, order_id: str, fill: TradeFill) -> None:
        """Update comprehensive analytics for an order."""
        try:
            if order_id not in self._order_analytics:
                self._order_analytics[order_id] = FillAnalytics()

            analytics = self._order_analytics[order_id]

            # Update basic metrics
            analytics.total_fills += 1
            analytics.total_volume += fill.volume
            analytics.total_cost += fill.cost
            analytics.total_fees += fill.fee

            # Update price tracking
            analytics.fill_sizes.append(fill.volume)
            analytics.fill_prices.append(fill.price)

            if analytics.best_fill_price is None or \
               (fill.side == 'buy' and fill.price < analytics.best_fill_price) or \
               (fill.side == 'sell' and fill.price > analytics.best_fill_price):
                analytics.best_fill_price = fill.price

            if analytics.worst_fill_price is None or \
               (fill.side == 'buy' and fill.price > analytics.worst_fill_price) or \
               (fill.side == 'sell' and fill.price < analytics.worst_fill_price):
                analytics.worst_fill_price = fill.price

            # Update quality metrics
            if fill.price_improvement:
                analytics.total_price_improvement += fill.price_improvement
            if fill.slippage:
                analytics.total_slippage += fill.slippage

            # Update timing
            if analytics.first_fill_time is None:
                analytics.first_fill_time = fill.timestamp
            analytics.last_fill_time = fill.timestamp

            # Update distribution
            analytics.fill_types_distribution[fill.fill_type] += 1

            # Recalculate derived metrics
            analytics.calculate_metrics()

            # Trigger analytics handlers
            await self._trigger_analytics_handlers(order_id, analytics)

        except Exception as e:
            self.logger.error("Error updating order analytics",
                            order_id=order_id,
                            error=str(e))

    async def _trigger_fill_handlers(self, fill: TradeFill) -> None:
        """Trigger all registered fill handlers."""
        for handler in self._fill_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(fill)
                else:
                    handler(fill)
            except Exception as e:
                self.logger.error("Fill handler error",
                                handler=handler.__name__,
                                trade_id=fill.trade_id,
                                error=str(e))

    async def _trigger_analytics_handlers(self, order_id: str, analytics: FillAnalytics) -> None:
        """Trigger all registered analytics handlers."""
        for handler in self._analytics_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(order_id, analytics)
                else:
                    handler(order_id, analytics)
            except Exception as e:
                self.logger.error("Analytics handler error",
                                handler=handler.__name__,
                                order_id=order_id,
                                error=str(e))

    # Public API methods

    def add_fill_handler(self, handler: Callable[[TradeFill], None]) -> None:
        """Add a handler for fill events."""
        self._fill_handlers.append(handler)
        self.logger.info("Fill handler added", handler=handler.__name__)

    def add_analytics_handler(self, handler: Callable[[str, FillAnalytics], None]) -> None:
        """Add a handler for analytics updates."""
        self._analytics_handlers.append(handler)
        self.logger.info("Analytics handler added", handler=handler.__name__)

    def get_fill(self, trade_id: str) -> Optional[TradeFill]:
        """Get a specific fill by trade ID."""
        return self._fills.get(trade_id)

    def get_order_fills(self, order_id: str) -> List[TradeFill]:
        """Get all fills for a specific order."""
        trade_ids = self._order_fills.get(order_id, [])
        return [self._fills[tid] for tid in trade_ids if tid in self._fills]

    def get_order_analytics(self, order_id: str) -> Optional[FillAnalytics]:
        """Get analytics for a specific order."""
        return self._order_analytics.get(order_id)

    def get_fill_summary(self, order_id: str) -> Dict[str, Any]:
        """Get comprehensive fill summary for an order."""
        fills = self.get_order_fills(order_id)
        analytics = self.get_order_analytics(order_id)

        if not fills:
            return {"order_id": order_id, "fill_count": 0}

        return {
            "order_id": order_id,
            "fill_count": len(fills),
            "total_volume": str(analytics.total_volume) if analytics else "0",
            "total_cost": str(analytics.total_cost) if analytics else "0",
            "total_fees": str(analytics.total_fees) if analytics else "0",
            "vwap": str(analytics.volume_weighted_average_price) if analytics and analytics.volume_weighted_average_price else None,
            "price_improvement": str(analytics.total_price_improvement) if analytics else "0",
            "total_slippage": str(analytics.total_slippage) if analytics else "0",
            "first_fill": fills[0].timestamp.isoformat() if fills else None,
            "last_fill": fills[-1].timestamp.isoformat() if fills else None,
            "fill_quality_distribution": {
                quality.value: sum(1 for f in fills if f.fill_quality == quality)
                for quality in FillQuality
            },
            "fill_type_distribution": {
                fill_type.value: analytics.fill_types_distribution.get(fill_type, 0)
                for fill_type in FillType
            } if analytics else {}
        }

    def get_performance_metrics(self, order_id: str) -> Dict[str, Any]:
        """Get performance metrics for an order."""
        analytics = self.get_order_analytics(order_id)
        if not analytics:
            return {}

        metrics = {
            "execution_quality": {
                "vwap": str(analytics.volume_weighted_average_price) if analytics.volume_weighted_average_price else None,
                "price_improvement_total": str(analytics.total_price_improvement),
                "slippage_total": str(analytics.total_slippage),
                "implementation_shortfall": str(analytics.implementation_shortfall) if analytics.implementation_shortfall else None
            },
            "execution_timing": {
                "first_fill": analytics.first_fill_time.isoformat() if analytics.first_fill_time else None,
                "last_fill": analytics.last_fill_time.isoformat() if analytics.last_fill_time else None,
                "total_duration": str(analytics.fill_duration) if analytics.fill_duration else None,
                "average_fill_interval": str(analytics.average_fill_interval) if analytics.average_fill_interval else None
            },
            "fill_distribution": {
                "total_fills": analytics.total_fills,
                "average_fill_size": str(analytics.total_volume / analytics.total_fills) if analytics.total_fills > 0 else "0",
                "largest_fill": str(max(analytics.fill_sizes)) if analytics.fill_sizes else "0",
                "smallest_fill": str(min(analytics.fill_sizes)) if analytics.fill_sizes else "0"
            }
        }

        return metrics

    def clear_order_data(self, order_id: str) -> None:
        """Clear all data for a specific order."""
        trade_ids = self._order_fills.get(order_id, [])
        for trade_id in trade_ids:
            self._fills.pop(trade_id, None)

        self._order_fills.pop(order_id, None)
        self._order_analytics.pop(order_id, None)

        self.logger.info("Order data cleared", order_id=order_id, fills_removed=len(trade_ids))

    def get_system_statistics(self) -> Dict[str, Any]:
        """Get system-wide fill processing statistics."""
        total_fills = len(self._fills)
        total_orders = len(self._order_fills)

        return {
            "total_fills_processed": total_fills,
            "total_orders_tracked": total_orders,
            "average_fills_per_order": total_fills / total_orders if total_orders > 0 else 0,
            "active_handlers": {
                "fill_handlers": len(self._fill_handlers),
                "analytics_handlers": len(self._analytics_handlers)
            },
            "configuration": {
                "quality_analysis_enabled": self.enable_quality_analysis,
                "market_context_enabled": self.enable_market_context,
                "price_precision": str(self.price_precision)
            }
        }


# Integration helper functions

async def integrate_fill_processor_with_order_manager(order_manager, fill_processor: FillProcessor) -> None:
    """Integrate FillProcessor with OrderManager for automatic fill processing."""

    async def handle_order_fill(order, fill_data: Dict[str, Any]) -> None:
        """Handle fills from OrderManager."""
        try:
            await fill_processor.process_fill(
                trade_id=fill_data.get('trade_id', f"fill_{datetime.now().timestamp()}"),
                order_id=order.order_id,
                volume=fill_data['volume'],
                price=fill_data['price'],
                fee=fill_data.get('fee', Decimal('0')),
                timestamp=fill_data.get('timestamp'),
                trade_info={
                    'pair': order.pair,
                    'type': order.side.value if hasattr(order.side, 'value') else str(order.side),
                    'ordertype': order.order_type.value if hasattr(order.order_type, 'value') else str(order.order_type),
                    **fill_data
                }
            )
        except Exception as e:
            fill_processor.logger.error("Error in OrderManager fill integration",
                                      order_id=order.order_id,
                                      error=str(e))

    # Add the handler to OrderManager
    if hasattr(order_manager, 'add_fill_handler'):
        order_manager.add_fill_handler(handle_order_fill)
        fill_processor.logger.info("FillProcessor integrated with OrderManager")
    else:
        fill_processor.logger.warning("OrderManager doesn't support fill handlers")


# Example usage and testing
if __name__ == "__main__":
    import asyncio

    async def demo_fill_processor():
        """Demonstrate FillProcessor capabilities."""
        processor = FillProcessor("DemoFillProcessor")

        # Add event handlers
        def on_fill(fill: TradeFill):
            print(f"Fill processed: {fill.trade_id} - {fill.volume} @ {fill.price}")

        def on_analytics(order_id: str, analytics: FillAnalytics):
            print(f"Analytics updated for {order_id}: VWAP = {analytics.volume_weighted_average_price}")

        processor.add_fill_handler(on_fill)
        processor.add_analytics_handler(on_analytics)

        # Process some demo fills
        order_id = "ORDER_DEMO_123"

        fills = [
            ("TRADE_1", Decimal("0.5"), Decimal("50000.00"), Decimal("5.00")),
            ("TRADE_2", Decimal("0.3"), Decimal("50100.00"), Decimal("3.01")),
            ("TRADE_3", Decimal("0.2"), Decimal("49950.00"), Decimal("2.00"))
        ]

        for trade_id, volume, price, fee in fills:
            await processor.process_fill(
                trade_id=trade_id,
                order_id=order_id,
                volume=volume,
                price=price,
                fee=fee,
                trade_info={'pair': 'XBT/USD', 'type': 'buy', 'ordertype': 'limit'}
            )

        # Get analytics
        summary = processor.get_fill_summary(order_id)
        print(f"\nFill Summary: {summary}")

        metrics = processor.get_performance_metrics(order_id)
        print(f"\nPerformance Metrics: {metrics}")

        stats = processor.get_system_statistics()
        print(f"\nSystem Statistics: {stats}")

    # Run demo
    asyncio.run(demo_fill_processor())
