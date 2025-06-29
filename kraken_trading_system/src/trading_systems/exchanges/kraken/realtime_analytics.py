#!/usr/bin/env python3
"""
Task 3.3.B.2: Real-time Fill Analytics Engine

This module implements a comprehensive real-time analytics engine that provides
live performance tracking, PnL calculations, execution quality monitoring,
and risk analytics for trading operations.

File: src/trading_systems/exchanges/kraken/realtime_analytics.py
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Tuple, Union
from collections import deque, defaultdict
import statistics
import math

# Imports for integration
try:
    from .fill_processor import TradeFill, FillAnalytics, FillQuality, FillType
    from .order_models import EnhancedKrakenOrder, OrderState
    from ...utils.logger import get_logger
except ImportError:
    # Fallback for testing
    try:
        from trading_systems.exchanges.kraken.fill_processor import TradeFill, FillAnalytics, FillQuality, FillType
        from trading_systems.utils.logger import get_logger
    except ImportError:
        # Mock for testing
        class MockLogger:
            def info(self, msg, **kwargs): print(f"INFO: {msg} {kwargs}")
            def warning(self, msg, **kwargs): print(f"WARN: {msg} {kwargs}")
            def error(self, msg, **kwargs): print(f"ERROR: {msg} {kwargs}")
        def get_logger(name): return MockLogger()


class AlertLevel(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    URGENT = "urgent"


class PerformanceMetric(Enum):
    """Performance metric types."""
    SHARPE_RATIO = "sharpe_ratio"
    PROFIT_FACTOR = "profit_factor"
    WIN_RATE = "win_rate"
    MAX_DRAWDOWN = "max_drawdown"
    VWAP_PERFORMANCE = "vwap_performance"
    EXECUTION_SPEED = "execution_speed"
    SLIPPAGE_RATIO = "slippage_ratio"


@dataclass
class RealTimePnL:
    """Real-time profit and loss tracking."""
    
    # Core PnL metrics
    realized_pnl: Decimal = Decimal('0')
    unrealized_pnl: Decimal = Decimal('0')
    total_pnl: Decimal = Decimal('0')
    
    # Performance tracking
    gross_profit: Decimal = Decimal('0')
    gross_loss: Decimal = Decimal('0')
    total_fees: Decimal = Decimal('0')
    net_profit: Decimal = Decimal('0')
    
    # Trade statistics
    winning_trades: int = 0
    losing_trades: int = 0
    total_trades: int = 0
    win_rate: float = 0.0
    
    # Risk metrics
    max_profit: Decimal = Decimal('0')
    max_loss: Decimal = Decimal('0')
    max_drawdown: Decimal = Decimal('0')
    current_drawdown: Decimal = Decimal('0')
    
    # Volume and exposure
    total_volume_traded: Decimal = Decimal('0')
    current_exposure: Decimal = Decimal('0')
    average_trade_size: Decimal = Decimal('0')
    
    def update_from_fill(self, fill: TradeFill, current_price: Optional[Decimal] = None) -> None:
        """Update PnL from a new fill."""
        # Update volume
        self.total_volume_traded += fill.volume
        self.total_fees += fill.fee
        
        # Update exposure (simplified - assumes directional trading)
        if fill.side == 'buy':
            self.current_exposure += fill.volume
        else:
            self.current_exposure -= fill.volume
        
        # Calculate unrealized PnL if current price available
        if current_price and self.current_exposure != 0:
            # This is a simplified calculation - real implementation would need position tracking
            avg_entry_price = fill.price  # Simplified
            price_diff = current_price - avg_entry_price
            self.unrealized_pnl = self.current_exposure * price_diff
        
        # Update total PnL
        self.total_pnl = self.realized_pnl + self.unrealized_pnl - self.total_fees
        self.net_profit = self.total_pnl
        
        # Update trade statistics
        self.total_trades += 1
        if self.total_trades > 0:
            self.average_trade_size = self.total_volume_traded / self.total_trades
            self.win_rate = self.winning_trades / self.total_trades
        
        # Update drawdown tracking
        if self.total_pnl > self.max_profit:
            self.max_profit = self.total_pnl
            self.current_drawdown = Decimal('0')
        else:
            self.current_drawdown = self.max_profit - self.total_pnl
            if self.current_drawdown > self.max_drawdown:
                self.max_drawdown = self.current_drawdown


@dataclass
class ExecutionMetrics:
    """Real-time execution quality metrics."""
    
    # Speed metrics
    average_fill_time: Optional[timedelta] = None
    fastest_fill: Optional[timedelta] = None
    slowest_fill: Optional[timedelta] = None
    
    # Quality metrics
    average_slippage: Decimal = Decimal('0')
    average_price_improvement: Decimal = Decimal('0')
    implementation_shortfall: Decimal = Decimal('0')
    
    # Market impact
    market_impact_ratio: Decimal = Decimal('0')
    liquidity_consumption_rate: Decimal = Decimal('0')
    
    # Fill distribution
    maker_ratio: float = 0.0
    taker_ratio: float = 0.0
    aggressive_ratio: float = 0.0
    
    # VWAP performance
    vwap_outperformance: Decimal = Decimal('0')
    vwap_tracking_error: Decimal = Decimal('0')
    
    def update_from_fill(self, fill: TradeFill, benchmark_price: Optional[Decimal] = None) -> None:
        """Update execution metrics from a new fill."""
        # Update slippage and price improvement
        if fill.slippage:
            # Running average update (simplified)
            self.average_slippage = (self.average_slippage + fill.slippage) / 2
        
        if fill.price_improvement:
            self.average_price_improvement = (self.average_price_improvement + fill.price_improvement) / 2
        
        # Update VWAP performance if benchmark available
        if benchmark_price:
            performance = fill.price - benchmark_price if fill.side == 'sell' else benchmark_price - fill.price
            self.vwap_outperformance = (self.vwap_outperformance + performance) / 2


@dataclass
class RiskAlert:
    """Risk alert notification."""
    
    timestamp: datetime
    level: AlertLevel
    metric: str
    current_value: Union[Decimal, float]
    threshold: Union[Decimal, float]
    message: str
    order_id: Optional[str] = None
    trade_id: Optional[str] = None


class RealTimeAnalyticsEngine:
    """Comprehensive real-time analytics engine for trading operations."""
    
    def __init__(self, logger_name: str = "RealTimeAnalyticsEngine"):
        """Initialize the analytics engine."""
        self.logger = get_logger(logger_name)
        
        # Core analytics components
        self.pnl = RealTimePnL()
        self.execution_metrics = ExecutionMetrics()
        
        # Data storage
        self.fill_history: deque[TradeFill] = deque(maxlen=10000)  # Last 10k fills
        self.pnl_history: deque[Tuple[datetime, Decimal]] = deque(maxlen=1440)  # 24 hours at 1min intervals
        self.performance_snapshots: Dict[datetime, Dict[str, Any]] = {}
        
        # Real-time tracking
        self.active_positions: Dict[str, Decimal] = defaultdict(Decimal)  # pair -> net_position
        self.session_start: datetime = datetime.now()
        self.last_update: datetime = datetime.now()
        
        # Alert system
        self.alerts: deque[RiskAlert] = deque(maxlen=1000)
        self.alert_handlers: List[Callable[[RiskAlert], None]] = []
        
        # Risk thresholds
        self.risk_thresholds = {
            'max_drawdown_pct': Decimal('5.0'),  # 5%
            'max_position_size': Decimal('10.0'),  # 10 units
            'max_daily_loss': Decimal('1000.0'),  # $1000
            'min_win_rate': Decimal('0.4'),  # 40%
            'max_slippage_pct': Decimal('0.1'),  # 0.1%
        }
        
        # Performance benchmarks
        self.benchmarks: Dict[str, Decimal] = {
            'target_sharpe': Decimal('1.5'),
            'target_profit_factor': Decimal('1.2'),
            'target_vwap_outperformance': Decimal('0.01'),  # 1 basis point
        }
        
        # Analytics configuration
        self.enable_real_time_alerts = True
        self.enable_performance_tracking = True
        self.update_interval = timedelta(seconds=1)
        
        self.logger.info("RealTimeAnalyticsEngine initialized",
                        risk_thresholds=len(self.risk_thresholds),
                        benchmarks=len(self.benchmarks))

    async def process_fill(self, fill: TradeFill, market_data: Optional[Dict[str, Any]] = None) -> None:
        """Process a new fill and update all analytics."""
        try:
            # Store fill
            self.fill_history.append(fill)
            self.last_update = datetime.now()
            
            # Update core metrics
            current_price = market_data.get('current_price') if market_data else None
            benchmark_price = market_data.get('vwap_benchmark') if market_data else None
            
            self.pnl.update_from_fill(fill, current_price)
            self.execution_metrics.update_from_fill(fill, benchmark_price)
            
            # Update positions
            pair = fill.pair
            if fill.side == 'buy':
                self.active_positions[pair] += fill.volume
            else:
                self.active_positions[pair] -= fill.volume
            
            # Check for alerts
            if self.enable_real_time_alerts:
                await self._check_risk_alerts(fill)
            
            # Update performance snapshots
            if self.enable_performance_tracking:
                await self._update_performance_snapshot()
            
            self.logger.info("Fill processed in analytics engine",
                           trade_id=fill.trade_id,
                           order_id=fill.order_id,
                           total_pnl=str(self.pnl.total_pnl),
                           current_drawdown=str(self.pnl.current_drawdown))
            
        except Exception as e:
            self.logger.error("Error processing fill in analytics engine",
                            trade_id=fill.trade_id,
                            error=str(e))
            raise

    async def _check_risk_alerts(self, fill: TradeFill) -> None:
        """Check for risk threshold breaches and generate alerts."""
        alerts_generated = []
        
        # Check maximum drawdown
        if self.pnl.max_drawdown > 0 and self.pnl.max_profit > 0:
            drawdown_pct = (self.pnl.max_drawdown / self.pnl.max_profit) * 100
            if drawdown_pct > self.risk_thresholds['max_drawdown_pct']:
                alert = RiskAlert(
                    timestamp=datetime.now(),
                    level=AlertLevel.CRITICAL,
                    metric="max_drawdown",
                    current_value=drawdown_pct,
                    threshold=self.risk_thresholds['max_drawdown_pct'],
                    message=f"Maximum drawdown {drawdown_pct:.2f}% exceeds threshold {self.risk_thresholds['max_drawdown_pct']}%",
                    trade_id=fill.trade_id
                )
                alerts_generated.append(alert)
        
        # Check position size
        position_size = abs(self.active_positions.get(fill.pair, Decimal('0')))
        if position_size > self.risk_thresholds['max_position_size']:
            alert = RiskAlert(
                timestamp=datetime.now(),
                level=AlertLevel.WARNING,
                metric="position_size",
                current_value=position_size,
                threshold=self.risk_thresholds['max_position_size'],
                message=f"Position size {position_size} exceeds threshold {self.risk_thresholds['max_position_size']}",
                order_id=fill.order_id
            )
            alerts_generated.append(alert)
        
        # Check daily loss
        if self.pnl.total_pnl < -self.risk_thresholds['max_daily_loss']:
            alert = RiskAlert(
                timestamp=datetime.now(),
                level=AlertLevel.URGENT,
                metric="daily_loss",
                current_value=self.pnl.total_pnl,
                threshold=-self.risk_thresholds['max_daily_loss'],
                message=f"Daily loss {self.pnl.total_pnl} exceeds threshold {self.risk_thresholds['max_daily_loss']}",
                trade_id=fill.trade_id
            )
            alerts_generated.append(alert)
        
        # Check win rate (if enough trades)
        if self.pnl.total_trades >= 10 and self.pnl.win_rate < self.risk_thresholds['min_win_rate']:
            alert = RiskAlert(
                timestamp=datetime.now(),
                level=AlertLevel.WARNING,
                metric="win_rate",
                current_value=self.pnl.win_rate,
                threshold=float(self.risk_thresholds['min_win_rate']),
                message=f"Win rate {self.pnl.win_rate:.1%} below threshold {self.risk_thresholds['min_win_rate']:.1%}",
                trade_id=fill.trade_id
            )
            alerts_generated.append(alert)
        
        # Check slippage
        if fill.slippage and fill.reference_price and fill.reference_price > 0:
            slippage_pct = (fill.slippage / fill.reference_price) * 100
            if slippage_pct > self.risk_thresholds['max_slippage_pct']:
                alert = RiskAlert(
                    timestamp=datetime.now(),
                    level=AlertLevel.INFO,
                    metric="slippage",
                    current_value=slippage_pct,
                    threshold=self.risk_thresholds['max_slippage_pct'],
                    message=f"Fill slippage {slippage_pct:.3f}% exceeds threshold {self.risk_thresholds['max_slippage_pct']}%",
                    trade_id=fill.trade_id
                )
                alerts_generated.append(alert)
        
        # Store and trigger alerts
        for alert in alerts_generated:
            self.alerts.append(alert)
            await self._trigger_alert_handlers(alert)

    async def _trigger_alert_handlers(self, alert: RiskAlert) -> None:
        """Trigger all registered alert handlers."""
        for handler in self.alert_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(alert)
                else:
                    handler(alert)
            except Exception as e:
                self.logger.error("Alert handler error",
                                handler=handler.__name__,
                                alert_level=alert.level.value,
                                error=str(e))

    async def _update_performance_snapshot(self) -> None:
        """Update performance snapshot for historical tracking."""
        now = datetime.now()
        
        # Take snapshot every minute
        if not self.performance_snapshots or \
           (now - max(self.performance_snapshots.keys())).total_seconds() >= 60:
            
            snapshot = {
                'timestamp': now.isoformat(),
                'total_pnl': str(self.pnl.total_pnl),
                'realized_pnl': str(self.pnl.realized_pnl),
                'unrealized_pnl': str(self.pnl.unrealized_pnl),
                'current_drawdown': str(self.pnl.current_drawdown),
                'win_rate': self.pnl.win_rate,
                'total_trades': self.pnl.total_trades,
                'total_volume': str(self.pnl.total_volume_traded),
                'average_slippage': str(self.execution_metrics.average_slippage),
                'vwap_outperformance': str(self.execution_metrics.vwap_outperformance),
                'active_positions': {k: str(v) for k, v in self.active_positions.items()},
                'session_duration': str(now - self.session_start)
            }
            
            self.performance_snapshots[now] = snapshot
            self.pnl_history.append((now, self.pnl.total_pnl))

    def calculate_sharpe_ratio(self, lookback_minutes: int = 60) -> Optional[float]:
        """Calculate Sharpe ratio over specified lookback period."""
        if len(self.pnl_history) < 2:
            return None
        
        # Get recent PnL data
        cutoff_time = datetime.now() - timedelta(minutes=lookback_minutes)
        recent_pnl = [(ts, pnl) for ts, pnl in self.pnl_history if ts >= cutoff_time]
        
        if len(recent_pnl) < 2:
            return None
        
        # Calculate returns
        returns = []
        for i in range(1, len(recent_pnl)):
            prev_pnl = float(recent_pnl[i-1][1])
            curr_pnl = float(recent_pnl[i][1])
            if prev_pnl != 0:
                returns.append((curr_pnl - prev_pnl) / abs(prev_pnl))
        
        if len(returns) < 2:
            return None
        
        # Calculate Sharpe ratio (simplified - no risk-free rate)
        mean_return = statistics.mean(returns)
        std_return = statistics.stdev(returns) if len(returns) > 1 else 0
        
        if std_return == 0:
            return None
        
        # Annualized Sharpe ratio (approximate)
        sharpe = (mean_return / std_return) * math.sqrt(252 * 24 * 60)  # Assuming minute intervals
        return sharpe

    def calculate_profit_factor(self) -> Optional[float]:
        """Calculate profit factor (gross profit / gross loss)."""
        if self.pnl.gross_loss == 0:
            return None
        return float(self.pnl.gross_profit / abs(self.pnl.gross_loss))

    def get_real_time_dashboard(self) -> Dict[str, Any]:
        """Get comprehensive real-time analytics dashboard."""
        # Calculate derived metrics
        sharpe_ratio = self.calculate_sharpe_ratio()
        profit_factor = self.calculate_profit_factor()
        
        # Session duration
        session_duration = datetime.now() - self.session_start
        
        # Recent alerts
        recent_alerts = [
            {
                'timestamp': alert.timestamp.isoformat(),
                'level': alert.level.value,
                'metric': alert.metric,
                'message': alert.message
            }
            for alert in list(self.alerts)[-10:]  # Last 10 alerts
        ]
        
        dashboard = {
            'timestamp': datetime.now().isoformat(),
            'session_duration': str(session_duration),
            
            # PnL Summary
            'pnl_summary': {
                'total_pnl': str(self.pnl.total_pnl),
                'realized_pnl': str(self.pnl.realized_pnl),
                'unrealized_pnl': str(self.pnl.unrealized_pnl),
                'net_profit': str(self.pnl.net_profit),
                'total_fees': str(self.pnl.total_fees),
                'max_drawdown': str(self.pnl.max_drawdown),
                'current_drawdown': str(self.pnl.current_drawdown),
            },
            
            # Trading Statistics
            'trading_stats': {
                'total_trades': self.pnl.total_trades,
                'winning_trades': self.pnl.winning_trades,
                'losing_trades': self.pnl.losing_trades,
                'win_rate': f"{self.pnl.win_rate:.1%}",
                'total_volume': str(self.pnl.total_volume_traded),
                'average_trade_size': str(self.pnl.average_trade_size),
            },
            
            # Execution Quality
            'execution_quality': {
                'average_slippage': str(self.execution_metrics.average_slippage),
                'average_price_improvement': str(self.execution_metrics.average_price_improvement),
                'vwap_outperformance': str(self.execution_metrics.vwap_outperformance),
                'maker_ratio': f"{self.execution_metrics.maker_ratio:.1%}",
                'taker_ratio': f"{self.execution_metrics.taker_ratio:.1%}",
            },
            
            # Performance Metrics
            'performance_metrics': {
                'sharpe_ratio': f"{sharpe_ratio:.2f}" if sharpe_ratio else "N/A",
                'profit_factor': f"{profit_factor:.2f}" if profit_factor else "N/A",
                'total_fills_processed': len(self.fill_history),
            },
            
            # Risk Status
            'risk_status': {
                'active_positions': {k: str(v) for k, v in self.active_positions.items()},
                'total_alerts': len(self.alerts),
                'critical_alerts': len([a for a in self.alerts if a.level == AlertLevel.CRITICAL]),
                'urgent_alerts': len([a for a in self.alerts if a.level == AlertLevel.URGENT]),
            },
            
            # Recent Activity
            'recent_activity': {
                'recent_alerts': recent_alerts,
                'last_fill_time': self.fill_history[-1].timestamp.isoformat() if self.fill_history else None,
                'fills_last_hour': len([f for f in self.fill_history 
                                      if f.timestamp >= datetime.now() - timedelta(hours=1)]),
            }
        }
        
        return dashboard

    def get_performance_report(self, time_period: timedelta = timedelta(hours=24)) -> Dict[str, Any]:
        """Generate comprehensive performance report for specified period."""
        cutoff_time = datetime.now() - time_period
        
        # Filter data by time period
        period_fills = [f for f in self.fill_history if f.timestamp >= cutoff_time]
        period_snapshots = {k: v for k, v in self.performance_snapshots.items() if k >= cutoff_time}
        
        if not period_fills:
            return {"error": "No data available for specified time period"}
        
        # Calculate period statistics
        period_volume = sum(f.volume for f in period_fills)
        period_fees = sum(f.fee for f in period_fills)
        
        # Quality distribution
        quality_dist = defaultdict(int)
        for fill in period_fills:
            quality_dist[fill.fill_quality.value] += 1
        
        # Time-based analysis
        hourly_volume = defaultdict(Decimal)
        for fill in period_fills:
            hour = fill.timestamp.replace(minute=0, second=0, microsecond=0)
            hourly_volume[hour] += fill.volume
        
        report = {
            'report_period': {
                'start_time': cutoff_time.isoformat(),
                'end_time': datetime.now().isoformat(),
                'duration': str(time_period),
            },
            
            'summary_statistics': {
                'total_fills': len(period_fills),
                'total_volume': str(period_volume),
                'total_fees': str(period_fees),
                'average_fill_size': str(period_volume / len(period_fills)) if period_fills else "0",
                'fills_per_hour': len(period_fills) / (time_period.total_seconds() / 3600),
            },
            
            'quality_analysis': {
                'fill_quality_distribution': dict(quality_dist),
                'excellent_fills_pct': (quality_dist['excellent'] / len(period_fills) * 100) if period_fills else 0,
                'poor_bad_fills_pct': ((quality_dist['poor'] + quality_dist['bad']) / len(period_fills) * 100) if period_fills else 0,
            },
            
            'execution_performance': {
                'average_slippage': str(self.execution_metrics.average_slippage),
                'vwap_performance': str(self.execution_metrics.vwap_outperformance),
                'market_impact': str(self.execution_metrics.market_impact_ratio),
            },
            
            'time_analysis': {
                'hourly_volume_distribution': {k.isoformat(): str(v) for k, v in hourly_volume.items()},
                'peak_activity_hour': max(hourly_volume.items(), key=lambda x: x[1])[0].isoformat() if hourly_volume else None,
            },
            
            'alerts_summary': {
                'total_alerts': len([a for a in self.alerts if a.timestamp >= cutoff_time]),
                'critical_alerts': len([a for a in self.alerts if a.timestamp >= cutoff_time and a.level == AlertLevel.CRITICAL]),
                'alert_frequency': len([a for a in self.alerts if a.timestamp >= cutoff_time]) / (time_period.total_seconds() / 3600),
            }
        }
        
        return report

    # Public API methods
    
    def add_alert_handler(self, handler: Callable[[RiskAlert], None]) -> None:
        """Add a handler for risk alerts."""
        self.alert_handlers.append(handler)
        self.logger.info("Alert handler added", handler=handler.__name__)
    
    def update_risk_threshold(self, metric: str, threshold: Union[Decimal, float]) -> None:
        """Update a risk threshold."""
        self.risk_thresholds[metric] = Decimal(str(threshold))
        self.logger.info("Risk threshold updated", metric=metric, threshold=str(threshold))
    
    def reset_session_metrics(self) -> None:
        """Reset session-based metrics (e.g., for new trading day)."""
        self.session_start = datetime.now()
        self.pnl = RealTimePnL()
        self.execution_metrics = ExecutionMetrics()
        self.alerts.clear()
        self.performance_snapshots.clear()
        self.pnl_history.clear()
        self.active_positions.clear()
        
        self.logger.info("Session metrics reset")
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get system health and status information."""
        return {
            'status': 'active',
            'session_uptime': str(datetime.now() - self.session_start),
            'data_points': {
                'fills_stored': len(self.fill_history),
                'pnl_snapshots': len(self.pnl_history),
                'performance_snapshots': len(self.performance_snapshots),
                'active_alerts': len(self.alerts),
            },
            'configuration': {
                'real_time_alerts_enabled': self.enable_real_time_alerts,
                'performance_tracking_enabled': self.enable_performance_tracking,
                'update_interval': str(self.update_interval),
                'risk_thresholds_count': len(self.risk_thresholds),
            },
            'last_update': self.last_update.isoformat(),
        }


# Integration helper functions

async def integrate_analytics_with_fill_processor(fill_processor, analytics_engine: RealTimeAnalyticsEngine) -> None:
    """Integrate RealTimeAnalyticsEngine with FillProcessor for automatic analytics updates."""
    
    async def handle_analytics_fill(fill: TradeFill) -> None:
        """Handle fills for analytics processing."""
        try:
            # Process fill in analytics engine
            await analytics_engine.process_fill(fill)
        except Exception as e:
            analytics_engine.logger.error("Error in analytics fill integration",
                                         trade_id=fill.trade_id,
                                         error=str(e))
    
    # Add the handler to FillProcessor
    if hasattr(fill_processor, 'add_fill_handler'):
        fill_processor.add_fill_handler(handle_analytics_fill)
        analytics_engine.logger.info("RealTimeAnalyticsEngine integrated with FillProcessor")
    else:
        analytics_engine.logger.warning("FillProcessor doesn't support fill handlers")


# Example usage and testing
if __name__ == "__main__":
    import asyncio
    from decimal import Decimal
    
    async def demo_analytics_engine():
        """Demonstrate RealTimeAnalyticsEngine capabilities."""
        engine = RealTimeAnalyticsEngine("DemoAnalyticsEngine")
        
        # Add alert handler
        def on_alert(alert: RiskAlert):
            print(f"🚨 ALERT [{alert.level.value.upper()}]: {alert.message}")
        
        engine.add_alert_handler(on_alert)
        
        # Simulate some fills
        from datetime import datetime
        
        # Mock TradeFill class for demo
        class MockTradeFill:
            def __init__(self, trade_id, order_id, volume, price, side, pair="XBT/USD", fee=Decimal('0')):
                self.trade_id = trade_id
                self.order_id = order_id
                self.volume = Decimal(str(volume))
                self.price = Decimal(str(price))
                self.side = side
                self.pair = pair
                self.fee = Decimal(str(fee))
                self.timestamp = datetime.now()
                self.cost = self.volume * self.price
                self.slippage = Decimal('0.5')  # Mock slippage
                self.price_improvement = None
                self.reference_price = self.price + Decimal('1.0')  # Mock reference
                self.fill_quality = type('FillQuality', (), {'value': 'fair'})()
        
        # Process demo fills
        fills = [
            MockTradeFill("DEMO_001", "ORDER_001", "0.5", "50000.00", "buy", fee="5.00"),
            MockTradeFill("DEMO_002", "ORDER_001", "0.3", "50100.00", "buy", fee="3.01"),
            MockTradeFill("DEMO_003", "ORDER_002", "0.2", "49950.00", "sell", fee="2.00"),
            MockTradeFill("DEMO_004", "ORDER_003", "1.0", "50200.00", "buy", fee="10.02"),
        ]
        
        print("📊 Processing demo fills...")
        for fill in fills:
            await engine.process_fill(fill, {'current_price': Decimal('50150.00')})
            await asyncio.sleep(0.1)  # Small delay between fills
        
        # Get real-time dashboard
        dashboard = engine.get_real_time_dashboard()
        print("\n📈 Real-time Dashboard:")
        print(f"Total PnL: {dashboard['pnl_summary']['total_pnl']}")
        print(f"Win Rate: {dashboard['trading_stats']['win_rate']}")
        print(f"Total Trades: {dashboard['trading_stats']['total_trades']}")
        
        # Get performance report
        report = engine.get_performance_report(timedelta(hours=1))
        print("\n📋 Performance Report:")
        print(f"Total Fills: {report['summary_statistics']['total_fills']}")
        print(f"Total Volume: {report['summary_statistics']['total_volume']}")
        
        # Get system health
        health = engine.get_system_health()
        print("\n🏥 System Health:")
        print(f"Status: {health['status']}")
        print(f"Fills Stored: {health['data_points']['fills_stored']}")
    
    # Run demo
    asyncio.run(demo_analytics_engine())
