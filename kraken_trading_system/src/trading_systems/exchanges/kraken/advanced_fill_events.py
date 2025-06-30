#!/usr/bin/env python3
"""
Task 3.3.B.3: Advanced Fill Event System

This module implements an advanced event-driven system for fill processing that provides
complex pattern recognition, multi-order correlation, and high-performance event handling.

File: src/trading_systems/exchanges/kraken/advanced_fill_events.py
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Set, Tuple, Union
from collections import deque, defaultdict
import statistics
import uuid
from concurrent.futures import ThreadPoolExecutor
import threading

# Imports for integration
try:
    from .fill_processor import TradeFill, FillAnalytics, FillQuality, FillType
    from .realtime_analytics import RealTimeAnalyticsEngine, RiskAlert, AlertLevel
    from .order_models import EnhancedKrakenOrder, OrderState
    from ...utils.logger import get_logger
except ImportError:
    # Fallback for testing
    class MockLogger:
        def info(self, msg, **kwargs): print(f"INFO: {msg} {kwargs}")
        def warning(self, msg, **kwargs): print(f"WARN: {msg} {kwargs}")
        def error(self, msg, **kwargs): print(f"ERROR: {msg} {kwargs}")
        def debug(self, msg, **kwargs): print(f"DEBUG: {msg} {kwargs}")
    def get_logger(name): return MockLogger()


class EventType(Enum):
    """Types of fill events."""
    FILL_RECEIVED = "fill_received"
    ORDER_COMPLETED = "order_completed"
    PATTERN_DETECTED = "pattern_detected"
    CORRELATION_FOUND = "correlation_found"
    ANOMALY_DETECTED = "anomaly_detected"
    PERFORMANCE_THRESHOLD = "performance_threshold"
    MARKET_IMPACT = "market_impact"
    EXECUTION_QUALITY = "execution_quality"


class PatternType(Enum):
    """Types of trading patterns."""
    ACCUMULATION = "accumulation"        # Gradual position building
    DISTRIBUTION = "distribution"        # Gradual position unwinding
    ICEBERG_DETECTED = "iceberg_detected" # Large hidden order detection
    MOMENTUM_BURST = "momentum_burst"     # Rapid execution cluster
    PRICE_IMPROVEMENT = "price_improvement" # Consistent price improvement
    SLIPPAGE_PATTERN = "slippage_pattern"  # Recurring slippage issues
    MARKET_MAKING = "market_making"       # Market making activity
    ARBITRAGE = "arbitrage"              # Cross-market arbitrage


class EventPriority(Enum):
    """Event priority levels."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4
    URGENT = 5


@dataclass
class FillEvent:
    """Represents a single fill event in the system."""
    
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: EventType = EventType.FILL_RECEIVED
    timestamp: datetime = field(default_factory=datetime.now)
    fill: Optional[TradeFill] = None
    
    # Event metadata
    priority: EventPriority = EventPriority.MEDIUM
    tags: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Processing status
    processed: bool = False
    processing_time: Optional[datetime] = None
    processing_duration: Optional[timedelta] = None
    
    # Correlation information
    related_events: List[str] = field(default_factory=list)  # Related event IDs
    correlation_group: Optional[str] = None
    pattern_match: Optional[PatternType] = None

    def mark_processed(self) -> None:
        """Mark event as processed and record timing."""
        self.processed = True
        self.processing_time = datetime.now()
        if self.processing_time and self.timestamp:
            self.processing_duration = self.processing_time - self.timestamp


@dataclass 
class TradingPattern:
    """Represents a detected trading pattern."""
    
    pattern_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    pattern_type: PatternType = PatternType.ACCUMULATION
    detected_at: datetime = field(default_factory=datetime.now)
    
    # Pattern characteristics
    events: List[str] = field(default_factory=list)  # Event IDs in pattern
    confidence: float = 0.0  # Confidence score 0-1
    strength: float = 0.0    # Pattern strength indicator
    
    # Trading metrics
    total_volume: Decimal = Decimal('0')
    average_price: Decimal = Decimal('0')
    price_range: Tuple[Decimal, Decimal] = field(default_factory=lambda: (Decimal('0'), Decimal('0')))
    duration: timedelta = field(default_factory=lambda: timedelta(0))
    
    # Market context
    pair: Optional[str] = None
    side: Optional[str] = None  # buy/sell tendency
    market_conditions: Dict[str, Any] = field(default_factory=dict)
    
    # Status
    active: bool = True
    completed_at: Optional[datetime] = None


@dataclass
class EventCorrelation:
    """Represents correlation between multiple events."""
    
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_ids: List[str] = field(default_factory=list)
    correlation_type: str = "temporal"  # temporal, price, volume, etc.
    strength: float = 0.0  # Correlation strength 0-1
    detected_at: datetime = field(default_factory=datetime.now)
    
    # Correlation metrics
    time_window: timedelta = field(default_factory=lambda: timedelta(0))
    statistical_significance: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class AdvancedFillEventSystem:
    """Advanced event system for sophisticated fill processing and pattern recognition."""
    
    def __init__(self, 
                 logger_name: str = "AdvancedFillEventSystem",
                 max_events: int = 50000,
                 max_patterns: int = 10000):
        """Initialize the advanced fill event system."""
        self.logger = get_logger(logger_name)
        
        # Event storage
        self.events: deque[FillEvent] = deque(maxlen=max_events)
        self.event_index: Dict[str, FillEvent] = {}  # event_id -> event
        self.patterns: deque[TradingPattern] = deque(maxlen=max_patterns)
        self.pattern_index: Dict[str, TradingPattern] = {}
        self.correlations: Dict[str, EventCorrelation] = {}
        
        # Event processing
        self.event_handlers: Dict[EventType, List[Callable]] = defaultdict(list)
        self.pattern_handlers: Dict[PatternType, List[Callable]] = defaultdict(list)
        self.correlation_handlers: List[Callable] = []
        
        # Configuration
        self.enable_pattern_detection = True
        self.enable_correlation_analysis = True
        self.enable_historical_replay = True
        self.pattern_detection_threshold = 0.7  # Confidence threshold
        self.correlation_threshold = 0.6
        
        # Performance optimization
        self.thread_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="FillEvent")
        self.processing_lock = threading.RLock()
        
        # Analytics integration
        self.analytics_engine: Optional[RealTimeAnalyticsEngine] = None
        
        # Pattern detection windows
        self.pattern_windows = {
            PatternType.ACCUMULATION: timedelta(minutes=30),
            PatternType.DISTRIBUTION: timedelta(minutes=30),
            PatternType.ICEBERG_DETECTED: timedelta(minutes=10),
            PatternType.MOMENTUM_BURST: timedelta(minutes=5),
            PatternType.PRICE_IMPROVEMENT: timedelta(minutes=15),
            PatternType.SLIPPAGE_PATTERN: timedelta(minutes=20),
            PatternType.MARKET_MAKING: timedelta(hours=1),
            PatternType.ARBITRAGE: timedelta(minutes=2),
        }
        
        self.logger.info("AdvancedFillEventSystem initialized",
                        max_events=max_events,
                        max_patterns=max_patterns,
                        pattern_detection=self.enable_pattern_detection,
                        correlation_analysis=self.enable_correlation_analysis)

    async def process_fill_event(self, fill: TradeFill, event_type: EventType = EventType.FILL_RECEIVED) -> FillEvent:
        """Process a new fill event through the advanced event system."""
        
        # Create event
        event = FillEvent(
            event_type=event_type,
            fill=fill,
            metadata={
                'pair': getattr(fill, 'pair', 'unknown'),
                'side': getattr(fill, 'side', 'unknown'),
                'volume': str(fill.volume),
                'price': str(fill.price),
                'cost': str(fill.cost),
            }
        )
        
        # Add tags based on fill characteristics
        await self._tag_event(event)
        
        # Store event
        with self.processing_lock:
            self.events.append(event)
            self.event_index[event.event_id] = event
        
        # Process event asynchronously
        await self._process_event_async(event)
        
        # Update analytics if available
        if self.analytics_engine:
            try:
                await self.analytics_engine.process_fill(fill)
            except Exception as e:
                self.logger.error("Error updating analytics", error=str(e))
        
        event.mark_processed()
        
        self.logger.debug("Fill event processed",
                         event_id=event.event_id,
                         trade_id=fill.trade_id,
                         processing_duration=str(event.processing_duration))
        
        return event

    async def _tag_event(self, event: FillEvent) -> None:
        """Add intelligent tags to an event based on its characteristics."""
        if not event.fill:
            return
            
        fill = event.fill
        
        # Volume-based tags
        if fill.volume > Decimal('10.0'):
            event.tags.add('large_volume')
        elif fill.volume < Decimal('0.1'):
            event.tags.add('small_volume')
        
        # Price-based tags
        if hasattr(fill, 'price_improvement') and fill.price_improvement > Decimal('0'):
            event.tags.add('price_improvement')
        
        # Quality-based tags
        if hasattr(fill, 'fill_quality'):
            event.tags.add(f'quality_{fill.fill_quality.value}')
        
        # Type-based tags
        if hasattr(fill, 'fill_type'):
            event.tags.add(f'type_{fill.fill_type.value}')
        
        # Time-based tags
        hour = event.timestamp.hour
        if 9 <= hour <= 16:
            event.tags.add('market_hours')
        else:
            event.tags.add('off_hours')

    async def _process_event_async(self, event: FillEvent) -> None:
        """Process event through pattern detection and correlation analysis."""
        
        tasks = []
        
        # Pattern detection
        if self.enable_pattern_detection:
            tasks.append(self._detect_patterns(event))
        
        # Correlation analysis  
        if self.enable_correlation_analysis:
            tasks.append(self._analyze_correlations(event))
        
        # Event handler notification
        tasks.append(self._notify_event_handlers(event))
        
        # Execute all tasks concurrently
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _detect_patterns(self, event: FillEvent) -> None:
        """Detect trading patterns involving this event."""
        
        try:
            current_time = event.timestamp
            
            # Check each pattern type
            for pattern_type, window in self.pattern_windows.items():
                # Get recent events in window
                recent_events = [
                    e for e in self.events 
                    if current_time - e.timestamp <= window
                ]
                
                if len(recent_events) < 3:  # Need minimum events for pattern
                    continue
                
                # Pattern-specific detection logic
                pattern = await self._detect_specific_pattern(pattern_type, recent_events, event)
                
                if pattern and pattern.confidence >= self.pattern_detection_threshold:
                    await self._register_pattern(pattern)
                    
        except Exception as e:
            self.logger.error("Error in pattern detection", error=str(e))

    async def _detect_specific_pattern(self, 
                                     pattern_type: PatternType, 
                                     events: List[FillEvent], 
                                     current_event: FillEvent) -> Optional[TradingPattern]:
        """Detect a specific type of trading pattern."""
        
        if pattern_type == PatternType.ACCUMULATION:
            return await self._detect_accumulation_pattern(events, current_event)
        elif pattern_type == PatternType.MOMENTUM_BURST:
            return await self._detect_momentum_burst(events, current_event)
        elif pattern_type == PatternType.ICEBERG_DETECTED:
            return await self._detect_iceberg_pattern(events, current_event)
        elif pattern_type == PatternType.PRICE_IMPROVEMENT:
            return await self._detect_price_improvement_pattern(events, current_event)
        elif pattern_type == PatternType.DISTRIBUTION:
            return await self._detect_distribution_pattern(events, current_event)
        elif pattern_type == PatternType.ARBITRAGE:
            return await self._detect_arbitrage_pattern(events, current_event)
        
        return None

    async def _detect_accumulation_pattern(self, 
                                         events: List[FillEvent], 
                                         current_event: FillEvent) -> Optional[TradingPattern]:
        """Detect accumulation pattern (gradual position building)."""
        
        if not current_event.fill:
            return None
            
        same_side_events = [
            e for e in events 
            if e.fill and hasattr(e.fill, 'side') and 
            e.fill.side == current_event.fill.side
        ]
        
        if len(same_side_events) < 5:  # Need multiple fills in same direction
            return None
        
        # Check for consistent volume and gradual price movement
        volumes = [e.fill.volume for e in same_side_events if e.fill]
        prices = [e.fill.price for e in same_side_events if e.fill]
        
        if not volumes or not prices:
            return None
        
        # Calculate metrics
        avg_volume = sum(volumes) / len(volumes)
        volume_consistency = 1.0 - (statistics.stdev(volumes) / avg_volume if avg_volume > 0 else 1.0)
        
        # Price trend analysis
        price_trend = (prices[-1] - prices[0]) / prices[0] if prices[0] > 0 else 0
        
        # Confidence calculation
        confidence = min(1.0, volume_consistency * 0.7 + abs(float(price_trend)) * 0.3)
        
        if confidence >= 0.6:  # Threshold for accumulation detection
            return TradingPattern(
                pattern_type=PatternType.ACCUMULATION,
                events=[e.event_id for e in same_side_events],
                confidence=confidence,
                strength=float(price_trend),
                total_volume=sum(volumes),
                average_price=sum(prices) / len(prices),
                price_range=(min(prices), max(prices)),
                duration=same_side_events[-1].timestamp - same_side_events[0].timestamp,
                pair=getattr(current_event.fill, 'pair', 'unknown'),
                side=getattr(current_event.fill, 'side', 'unknown')
            )
        
        return None

    async def _detect_momentum_burst(self, 
                                   events: List[FillEvent], 
                                   current_event: FillEvent) -> Optional[TradingPattern]:
        """Detect momentum burst pattern (rapid execution cluster)."""
        
        # Look for rapid succession of fills in short time window
        recent_window = timedelta(minutes=2)
        burst_events = [
            e for e in events 
            if current_event.timestamp - e.timestamp <= recent_window
        ]
        
        if len(burst_events) < 4:  # Need multiple rapid fills
            return None
        
        # Check execution frequency
        time_span = burst_events[-1].timestamp - burst_events[0].timestamp
        if time_span.total_seconds() == 0:
            return None
            
        execution_rate = len(burst_events) / time_span.total_seconds() * 60  # fills per minute
        
        # Calculate total volume and price impact
        total_volume = sum(e.fill.volume for e in burst_events if e.fill)
        
        if execution_rate > 5.0 and total_volume > Decimal('2.0'):  # High frequency + volume
            confidence = min(1.0, execution_rate / 20.0 + float(total_volume) / 10.0)
            
            return TradingPattern(
                pattern_type=PatternType.MOMENTUM_BURST,
                events=[e.event_id for e in burst_events],
                confidence=confidence,
                strength=execution_rate,
                total_volume=total_volume,
                duration=time_span,
                pair=getattr(current_event.fill, 'pair', 'unknown') if current_event.fill else 'unknown'
            )
        
        return None

    async def _detect_iceberg_pattern(self, 
                                    events: List[FillEvent], 
                                    current_event: FillEvent) -> Optional[TradingPattern]:
        """Detect iceberg order pattern (large hidden order)."""
        
        # Look for consistent small fills at similar price levels
        if not current_event.fill:
            return None
            
        current_price = current_event.fill.price
        price_tolerance = current_price * Decimal('0.001')  # 0.1% tolerance
        
        similar_price_events = [
            e for e in events 
            if e.fill and abs(e.fill.price - current_price) <= price_tolerance
        ]
        
        if len(similar_price_events) < 6:  # Need multiple fills at similar price
            return None
        
        # Check for consistent small volumes (iceberg characteristic)
        volumes = [e.fill.volume for e in similar_price_events]
        avg_volume = sum(volumes) / len(volumes)
        volume_consistency = 1.0 - (statistics.stdev(volumes) / avg_volume if avg_volume > 0 else 1.0)
        
        total_volume = sum(volumes)
        
        # Iceberg detected if many small consistent fills add up to large volume
        if volume_consistency > 0.8 and total_volume > avg_volume * 10:
            confidence = min(1.0, volume_consistency * 0.6 + min(1.0, float(total_volume) / 50.0) * 0.4)
            
            return TradingPattern(
                pattern_type=PatternType.ICEBERG_DETECTED,
                events=[e.event_id for e in similar_price_events],
                confidence=confidence,
                strength=float(total_volume / avg_volume),
                total_volume=total_volume,
                average_price=current_price,
                duration=similar_price_events[-1].timestamp - similar_price_events[0].timestamp,
                pair=getattr(current_event.fill, 'pair', 'unknown')
            )
        
        return None

    async def _detect_price_improvement_pattern(self, 
                                              events: List[FillEvent], 
                                              current_event: FillEvent) -> Optional[TradingPattern]:
        """Detect consistent price improvement pattern."""
        
        # Look for events with price improvement
        improvement_events = [
            e for e in events 
            if e.fill and hasattr(e.fill, 'price_improvement') and 
            e.fill.price_improvement > Decimal('0')
        ]
        
        if len(improvement_events) < 3:
            return None
        
        # Calculate average improvement and consistency
        improvements = [e.fill.price_improvement for e in improvement_events]
        avg_improvement = sum(improvements) / len(improvements)
        improvement_consistency = 1.0 - (statistics.stdev(improvements) / avg_improvement if avg_improvement > 0 else 1.0)
        
        if improvement_consistency > 0.7 and avg_improvement > Decimal('0.01'):
            confidence = min(1.0, improvement_consistency * 0.8 + min(1.0, float(avg_improvement) * 100) * 0.2)
            
            return TradingPattern(
                pattern_type=PatternType.PRICE_IMPROVEMENT,
                events=[e.event_id for e in improvement_events],
                confidence=confidence,
                strength=float(avg_improvement),
                total_volume=sum(e.fill.volume for e in improvement_events),
                duration=improvement_events[-1].timestamp - improvement_events[0].timestamp,
                pair=getattr(current_event.fill, 'pair', 'unknown') if current_event.fill else 'unknown'
            )
        
        return None

    async def _detect_distribution_pattern(self, 
                                         events: List[FillEvent], 
                                         current_event: FillEvent) -> Optional[TradingPattern]:
        """Detect distribution pattern (gradual position unwinding)."""
        
        if not current_event.fill:
            return None
            
        # Similar to accumulation but for selling
        same_side_events = [
            e for e in events 
            if e.fill and hasattr(e.fill, 'side') and 
            e.fill.side == 'sell'  # Focus on sell orders for distribution
        ]
        
        if len(same_side_events) < 5:
            return None
        
        volumes = [e.fill.volume for e in same_side_events if e.fill]
        prices = [e.fill.price for e in same_side_events if e.fill]
        
        if not volumes or not prices:
            return None
        
        # Check for consistent selling with gradual price decrease
        avg_volume = sum(volumes) / len(volumes)
        volume_consistency = 1.0 - (statistics.stdev(volumes) / avg_volume if avg_volume > 0 else 1.0)
        
        # Negative price trend indicates distribution
        price_trend = (prices[-1] - prices[0]) / prices[0] if prices[0] > 0 else 0
        
        confidence = min(1.0, volume_consistency * 0.7 + abs(float(price_trend)) * 0.3)
        
        if confidence >= 0.6 and price_trend < 0:  # Downward price movement
            return TradingPattern(
                pattern_type=PatternType.DISTRIBUTION,
                events=[e.event_id for e in same_side_events],
                confidence=confidence,
                strength=abs(float(price_trend)),
                total_volume=sum(volumes),
                average_price=sum(prices) / len(prices),
                duration=same_side_events[-1].timestamp - same_side_events[0].timestamp,
                pair=getattr(current_event.fill, 'pair', 'unknown'),
                side='sell'
            )
        
        return None

    async def _detect_arbitrage_pattern(self, 
                                      events: List[FillEvent], 
                                      current_event: FillEvent) -> Optional[TradingPattern]:
        """Detect arbitrage pattern (rapid buy-sell sequences)."""
        
        # Look for rapid buy-sell pairs in very short time window
        arb_window = timedelta(seconds=30)
        recent_events = [
            e for e in events 
            if current_event.timestamp - e.timestamp <= arb_window and e.fill
        ]
        
        if len(recent_events) < 4:
            return None
        
        # Check for alternating buy/sell pattern
        buy_events = [e for e in recent_events if getattr(e.fill, 'side', '') == 'buy']
        sell_events = [e for e in recent_events if getattr(e.fill, 'side', '') == 'sell']
        
        if len(buy_events) >= 2 and len(sell_events) >= 2:
            # Calculate profit potential
            buy_prices = [e.fill.price for e in buy_events]
            sell_prices = [e.fill.price for e in sell_events]
            
            avg_buy_price = sum(buy_prices) / len(buy_prices)
            avg_sell_price = sum(sell_prices) / len(sell_prices)
            
            profit_margin = (avg_sell_price - avg_buy_price) / avg_buy_price if avg_buy_price > 0 else 0
            
            if profit_margin > 0.001:  # At least 0.1% profit margin
                confidence = min(1.0, float(profit_margin) * 100)
                
                return TradingPattern(
                    pattern_type=PatternType.ARBITRAGE,
                    events=[e.event_id for e in recent_events],
                    confidence=confidence,
                    strength=float(profit_margin),
                    total_volume=sum(e.fill.volume for e in recent_events),
                    duration=recent_events[-1].timestamp - recent_events[0].timestamp,
                    pair=getattr(current_event.fill, 'pair', 'unknown')
                )
        
        return None

    async def _register_pattern(self, pattern: TradingPattern) -> None:
        """Register a detected pattern and notify handlers."""
        
        with self.processing_lock:
            self.patterns.append(pattern)
            self.pattern_index[pattern.pattern_id] = pattern
        
        # Notify pattern handlers
        handlers = self.pattern_handlers.get(pattern.pattern_type, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(pattern)
                else:
                    handler(pattern)
            except Exception as e:
                self.logger.error("Error in pattern handler", pattern_type=pattern.pattern_type.value, error=str(e))
        
        self.logger.info("Pattern detected",
                        pattern_type=pattern.pattern_type.value,
                        confidence=pattern.confidence,
                        events=len(pattern.events),
                        volume=str(pattern.total_volume))

    async def _analyze_correlations(self, event: FillEvent) -> None:
        """Analyze correlations between this event and recent events."""
        
        try:
            correlation_window = timedelta(minutes=10)
            recent_events = [
                e for e in self.events 
                if event.timestamp - e.timestamp <= correlation_window and e.event_id != event.event_id
            ]
            
            if len(recent_events) < 2:
                return
            
            # Temporal correlation analysis
            await self._analyze_temporal_correlation(event, recent_events)
            
            # Price correlation analysis
            await self._analyze_price_correlation(event, recent_events)
            
            # Volume correlation analysis
            await self._analyze_volume_correlation(event, recent_events)
            
        except Exception as e:
            self.logger.error("Error in correlation analysis", error=str(e))

    async def _analyze_temporal_correlation(self, event: FillEvent, recent_events: List[FillEvent]) -> None:
        """Analyze temporal correlations between events."""
        
        # Look for events that occurred at regular intervals
        time_diffs = []
        for i in range(1, len(recent_events)):
            diff = recent_events[i].timestamp - recent_events[i-1].timestamp
            time_diffs.append(diff.total_seconds())
        
        if len(time_diffs) < 3:
            return
        
        # Calculate temporal regularity
        avg_interval = statistics.mean(time_diffs)
        interval_stdev = statistics.stdev(time_diffs) if len(time_diffs) > 1 else 0
        
        if avg_interval > 0:
            regularity = 1.0 - (interval_stdev / avg_interval)
            
            if regularity > self.correlation_threshold:
                correlation = EventCorrelation(
                    event_ids=[e.event_id for e in recent_events] + [event.event_id],
                    correlation_type="temporal",
                    strength=regularity,
                    time_window=timedelta(seconds=avg_interval),
                    metadata={'average_interval': avg_interval, 'regularity': regularity}
                )
                
                await self._register_correlation(correlation)

    async def _analyze_price_correlation(self, event: FillEvent, recent_events: List[FillEvent]) -> None:
        """Analyze price correlations between events."""
        
        if not event.fill:
            return
        
        # Get events with price data
        price_events = [e for e in recent_events if e.fill and hasattr(e.fill, 'price')]
        
        if len(price_events) < 3:
            return
        
        prices = [float(e.fill.price) for e in price_events]
        current_price = float(event.fill.price)
        
        # Calculate price correlation strength
        price_variance = statistics.variance(prices) if len(prices) > 1 else 0
        price_mean = statistics.mean(prices)
        
        if price_variance > 0:
            price_deviation = abs(current_price - price_mean) / (price_variance ** 0.5)
            correlation_strength = max(0, 1.0 - price_deviation / 3.0)  # Normalize
            
            if correlation_strength > self.correlation_threshold:
                correlation = EventCorrelation(
                    event_ids=[e.event_id for e in price_events] + [event.event_id],
                    correlation_type="price",
                    strength=correlation_strength,
                    metadata={'price_mean': price_mean, 'price_variance': price_variance}
                )
                
                await self._register_correlation(correlation)

    async def _analyze_volume_correlation(self, event: FillEvent, recent_events: List[FillEvent]) -> None:
        """Analyze volume correlations between events."""
        
        if not event.fill:
            return
        
        # Get events with volume data
        volume_events = [e for e in recent_events if e.fill and hasattr(e.fill, 'volume')]
        
        if len(volume_events) < 3:
            return
        
        volumes = [float(e.fill.volume) for e in volume_events]
        current_volume = float(event.fill.volume)
        
        # Calculate volume correlation
        volume_variance = statistics.variance(volumes) if len(volumes) > 1 else 0
        volume_mean = statistics.mean(volumes)
        
        if volume_variance > 0:
            volume_deviation = abs(current_volume - volume_mean) / (volume_variance ** 0.5)
            correlation_strength = max(0, 1.0 - volume_deviation / 3.0)
            
            if correlation_strength > self.correlation_threshold:
                correlation = EventCorrelation(
                    event_ids=[e.event_id for e in volume_events] + [event.event_id],
                    correlation_type="volume",
                    strength=correlation_strength,
                    metadata={'volume_mean': volume_mean, 'volume_variance': volume_variance}
                )
                
                await self._register_correlation(correlation)

    async def _register_correlation(self, correlation: EventCorrelation) -> None:
        """Register a detected correlation and notify handlers."""
        
        with self.processing_lock:
            self.correlations[correlation.correlation_id] = correlation
        
        # Notify correlation handlers
        for handler in self.correlation_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(correlation)
                else:
                    handler(correlation)
            except Exception as e:
                self.logger.error("Error in correlation handler", correlation_type=correlation.correlation_type, error=str(e))
        
        self.logger.debug("Correlation detected",
                         correlation_type=correlation.correlation_type,
                         strength=correlation.strength,
                         events=len(correlation.event_ids))

    async def _notify_event_handlers(self, event: FillEvent) -> None:
        """Notify registered event handlers."""
        
        handlers = self.event_handlers.get(event.event_type, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                self.logger.error("Error in event handler", event_type=event.event_type.value, error=str(e))

    # Event Handler Registration Methods
    def add_event_handler(self, event_type: EventType, handler: Callable) -> None:
        """Add an event handler for specific event types."""
        self.event_handlers[event_type].append(handler)
        self.logger.info("Event handler added", event_type=event_type.value)

    def add_pattern_handler(self, pattern_type: PatternType, handler: Callable) -> None:
        """Add a pattern handler for specific pattern types."""
        self.pattern_handlers[pattern_type].append(handler)
        self.logger.info("Pattern handler added", pattern_type=pattern_type.value)

    def add_correlation_handler(self, handler: Callable) -> None:
        """Add a correlation handler."""
        self.correlation_handlers.append(handler)
        self.logger.info("Correlation handler added")

    # Query and Analysis Methods
    def get_events_by_pattern(self, pattern_type: PatternType, 
                             since: Optional[datetime] = None) -> List[FillEvent]:
        """Get events that match a specific pattern."""
        
        target_patterns = [
            p for p in self.patterns 
            if p.pattern_type == pattern_type and 
            (since is None or p.detected_at >= since)
        ]
        
        event_ids = set()
        for pattern in target_patterns:
            event_ids.update(pattern.events)
        
        return [self.event_index[eid] for eid in event_ids if eid in self.event_index]

    def get_pattern_statistics(self, 
                              since: Optional[datetime] = None) -> Dict[str, Any]:
        """Get comprehensive pattern detection statistics."""
        
        relevant_patterns = [
            p for p in self.patterns 
            if since is None or p.detected_at >= since
        ]
        
        if not relevant_patterns:
            return {'total_patterns': 0}
        
        # Pattern type distribution
        pattern_counts = defaultdict(int)
        confidence_scores = []
        total_volume = Decimal('0')
        
        for pattern in relevant_patterns:
            pattern_counts[pattern.pattern_type.value] += 1
            confidence_scores.append(pattern.confidence)
            total_volume += pattern.total_volume
        
        return {
            'total_patterns': len(relevant_patterns),
            'pattern_distribution': dict(pattern_counts),
            'average_confidence': statistics.mean(confidence_scores),
            'confidence_range': (min(confidence_scores), max(confidence_scores)),
            'total_pattern_volume': str(total_volume),
            'most_common_pattern': max(pattern_counts.items(), key=lambda x: x[1])[0] if pattern_counts else None
        }

    def get_correlation_analysis(self, 
                               correlation_type: Optional[str] = None,
                               since: Optional[datetime] = None) -> Dict[str, Any]:
        """Get comprehensive correlation analysis."""
        
        relevant_correlations = [
            c for c in self.correlations.values()
            if (correlation_type is None or c.correlation_type == correlation_type) and
            (since is None or c.detected_at >= since)
        ]
        
        if not relevant_correlations:
            return {'total_correlations': 0}
        
        # Correlation statistics
        type_counts = defaultdict(int)
        strength_scores = []
        
        for correlation in relevant_correlations:
            type_counts[correlation.correlation_type] += 1
            strength_scores.append(correlation.strength)
        
        return {
            'total_correlations': len(relevant_correlations),
            'correlation_types': dict(type_counts),
            'average_strength': statistics.mean(strength_scores),
            'strength_range': (min(strength_scores), max(strength_scores)),
            'strongest_correlation': max(relevant_correlations, key=lambda c: c.strength).correlation_type
        }

    async def replay_historical_events(self, 
                                     start_time: datetime, 
                                     end_time: datetime,
                                     event_filter: Optional[Callable] = None) -> Dict[str, Any]:
        """Replay historical events for analysis and strategy optimization."""
        
        self.logger.info("Starting historical event replay",
                        start_time=start_time.isoformat(),
                        end_time=end_time.isoformat())
        
        # Get events in time range
        historical_events = [
            e for e in self.events
            if start_time <= e.timestamp <= end_time and
            (event_filter is None or event_filter(e))
        ]
        
        if not historical_events:
            return {'events_replayed': 0, 'patterns_detected': 0}
        
        # Temporarily disable real-time processing
        original_pattern_detection = self.enable_pattern_detection
        original_correlation_analysis = self.enable_correlation_analysis
        
        self.enable_pattern_detection = True
        self.enable_correlation_analysis = True
        
        # Clear existing patterns and correlations for clean replay
        replay_patterns = []
        replay_correlations = []
        
        try:
            # Process events in chronological order
            sorted_events = sorted(historical_events, key=lambda e: e.timestamp)
            
            for event in sorted_events:
                if event.fill:
                    # Reprocess the event
                    await self._detect_patterns(event)
                    await self._analyze_correlations(event)
            
            # Collect replay results
            replay_patterns = [p for p in self.patterns if start_time <= p.detected_at <= end_time]
            replay_correlations = [
                c for c in self.correlations.values() 
                if start_time <= c.detected_at <= end_time
            ]
            
        finally:
            # Restore original settings
            self.enable_pattern_detection = original_pattern_detection
            self.enable_correlation_analysis = original_correlation_analysis
        
        replay_results = {
            'events_replayed': len(historical_events),
            'patterns_detected': len(replay_patterns),
            'correlations_found': len(replay_correlations),
            'pattern_types': list(set(p.pattern_type.value for p in replay_patterns)),
            'correlation_types': list(set(c.correlation_type for c in replay_correlations)),
            'time_span': str(end_time - start_time),
            'average_events_per_hour': len(historical_events) / max(1, (end_time - start_time).total_seconds() / 3600)
        }
        
        self.logger.info("Historical event replay completed", **replay_results)
        return replay_results

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get system performance metrics for high-frequency optimization."""
        
        if not self.events:
            return {'status': 'no_events'}
        
        # Processing latency analysis
        processed_events = [e for e in self.events if e.processed and e.processing_duration]
        
        if processed_events:
            processing_times = [e.processing_duration.total_seconds() * 1000 for e in processed_events]  # milliseconds
            
            latency_stats = {
                'average_latency_ms': statistics.mean(processing_times),
                'median_latency_ms': statistics.median(processing_times),
                'max_latency_ms': max(processing_times),
                'min_latency_ms': min(processing_times),
                'p99_latency_ms': sorted(processing_times)[int(0.99 * len(processing_times))] if len(processing_times) > 10 else max(processing_times)
            }
        else:
            latency_stats = {'status': 'no_processed_events'}
        
        # Throughput analysis
        recent_window = timedelta(minutes=10)
        recent_events = [
            e for e in self.events
            if datetime.now() - e.timestamp <= recent_window
        ]
        
        throughput_stats = {
            'events_last_10min': len(recent_events),
            'events_per_minute': len(recent_events) / 10,
            'total_events_stored': len(self.events),
            'total_patterns_detected': len(self.patterns),
            'total_correlations_found': len(self.correlations)
        }
        
        # Memory usage approximation
        memory_stats = {
            'events_in_memory': len(self.events),
            'patterns_in_memory': len(self.patterns),
            'correlations_in_memory': len(self.correlations),
            'memory_usage_estimate_mb': (len(self.events) * 2 + len(self.patterns) + len(self.correlations)) / 1000  # Rough estimate
        }
        
        return {
            'latency': latency_stats,
            'throughput': throughput_stats,
            'memory': memory_stats,
            'configuration': {
                'pattern_detection_enabled': self.enable_pattern_detection,
                'correlation_analysis_enabled': self.enable_correlation_analysis,
                'pattern_threshold': self.pattern_detection_threshold,
                'correlation_threshold': self.correlation_threshold
            }
        }

    def integrate_with_analytics_engine(self, analytics_engine: RealTimeAnalyticsEngine) -> None:
        """Integrate with the real-time analytics engine."""
        self.analytics_engine = analytics_engine
        self.logger.info("Integrated with RealTimeAnalyticsEngine")

    async def optimize_for_high_frequency(self) -> None:
        """Optimize system configuration for high-frequency trading scenarios."""
        
        # Reduce pattern detection windows for faster processing
        optimized_windows = {
            PatternType.MOMENTUM_BURST: timedelta(seconds=30),
            PatternType.ICEBERG_DETECTED: timedelta(minutes=2),
            PatternType.PRICE_IMPROVEMENT: timedelta(minutes=5),
            PatternType.ACCUMULATION: timedelta(minutes=10),
            PatternType.DISTRIBUTION: timedelta(minutes=10),
            PatternType.SLIPPAGE_PATTERN: timedelta(minutes=5),
            PatternType.MARKET_MAKING: timedelta(minutes=15),
            PatternType.ARBITRAGE: timedelta(seconds=30),
        }
        
        self.pattern_windows.update(optimized_windows)
        
        # Increase thresholds for more selective detection
        self.pattern_detection_threshold = 0.8
        self.correlation_threshold = 0.7
        
        # Optimize memory usage
        if len(self.events) > 25000:
            # Keep only most recent events
            recent_events = list(self.events)[-20000:]
            self.events.clear()
            self.events.extend(recent_events)
            
            # Rebuild index
            self.event_index = {e.event_id: e for e in self.events}
        
        self.logger.info("System optimized for high-frequency trading",
                        pattern_threshold=self.pattern_detection_threshold,
                        correlation_threshold=self.correlation_threshold,
                        events_retained=len(self.events))

    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status information."""
        
        return {
            'status': 'active',
            'configuration': {
                'pattern_detection': self.enable_pattern_detection,
                'correlation_analysis': self.enable_correlation_analysis,
                'historical_replay': self.enable_historical_replay,
                'pattern_threshold': self.pattern_detection_threshold,
                'correlation_threshold': self.correlation_threshold
            },
            'data_summary': {
                'total_events': len(self.events),
                'total_patterns': len(self.patterns),
                'total_correlations': len(self.correlations),
                'active_patterns': len([p for p in self.patterns if p.active]),
                'event_handlers': sum(len(handlers) for handlers in self.event_handlers.values()),
                'pattern_handlers': sum(len(handlers) for handlers in self.pattern_handlers.values()),
                'correlation_handlers': len(self.correlation_handlers)
            },
            'integration': {
                'analytics_engine_connected': self.analytics_engine is not None,
                'thread_pool_active': not self.thread_pool._shutdown
            }
        }

    async def shutdown(self) -> None:
        """Gracefully shutdown the event system."""
        
        self.logger.info("Shutting down AdvancedFillEventSystem")
        
        # Shutdown thread pool
        self.thread_pool.shutdown(wait=True)
        
        # Clear handlers to prevent memory leaks
        self.event_handlers.clear()
        self.pattern_handlers.clear()
        self.correlation_handlers.clear()
        
        self.logger.info("AdvancedFillEventSystem shutdown complete")


# Integration and Helper Functions

async def integrate_advanced_events_with_system(
    event_system: AdvancedFillEventSystem,
    fill_processor,
    analytics_engine: Optional[RealTimeAnalyticsEngine] = None
) -> None:
    """Integrate the advanced event system with existing components."""
    
    # Integrate with analytics engine if provided
    if analytics_engine:
        event_system.integrate_with_analytics_engine(analytics_engine)
    
    # Add fill processor integration
    if hasattr(fill_processor, 'add_fill_handler'):
        async def handle_fill_for_events(fill):
            await event_system.process_fill_event(fill)
        
        fill_processor.add_fill_handler(handle_fill_for_events)
        event_system.logger.info("Integrated with FillProcessor")


# Performance-optimized event processing for high-frequency scenarios
class HighFrequencyEventProcessor:
    """Specialized processor for high-frequency trading scenarios."""
    
    def __init__(self, event_system: AdvancedFillEventSystem):
        self.event_system = event_system
        self.batch_size = 100
        self.batch_timeout = timedelta(milliseconds=50)
        self.event_queue = asyncio.Queue(maxsize=10000)
        self.processing_task = None
        self.running = False
    
    async def start(self):
        """Start high-frequency processing."""
        self.running = True
        self.processing_task = asyncio.create_task(self._process_batch_events())
    
    async def stop(self):
        """Stop high-frequency processing."""
        self.running = False
        if self.processing_task:
            await self.processing_task
    
    async def queue_fill(self, fill):
        """Queue a fill for batch processing."""
        try:
            await asyncio.wait_for(self.event_queue.put(fill), timeout=0.001)
        except asyncio.TimeoutError:
            # Drop events if queue is full (backpressure)
            pass
    
    async def _process_batch_events(self):
        """Process events in optimized batches."""
        batch = []
        last_batch_time = datetime.now()
        
        while self.running:
            try:
                # Try to get an event with timeout
                fill = await asyncio.wait_for(self.event_queue.get(), timeout=0.01)
                batch.append(fill)
                
                # Process batch if size limit reached or timeout exceeded
                should_process = (
                    len(batch) >= self.batch_size or
                    datetime.now() - last_batch_time >= self.batch_timeout
                )
                
                if should_process and batch:
                    await self._process_batch(batch)
                    batch = []
                    last_batch_time = datetime.now()
                    
            except asyncio.TimeoutError:
                # Process any remaining events in batch
                if batch:
                    await self._process_batch(batch)
                    batch = []
                    last_batch_time = datetime.now()
    
    async def _process_batch(self, fills):
        """Process a batch of fills efficiently."""
        # Process fills concurrently
        tasks = [
            self.event_system.process_fill_event(fill)
            for fill in fills
        ]
        await asyncio.gather(*tasks, return_exceptions=True)


# Example usage and testing
if __name__ == "__main__":
    import asyncio
    
    async def demo_advanced_event_system():
        """Demonstrate AdvancedFillEventSystem capabilities."""
        
        print("🚀 ADVANCED FILL EVENT SYSTEM DEMO")
        print("=" * 60)
        
        # Initialize system
        event_system = AdvancedFillEventSystem("DemoEventSystem")
        
        # Add some example handlers
        def pattern_handler(pattern):
            print(f"🔍 Pattern detected: {pattern.pattern_type.value} (confidence: {pattern.confidence:.2f})")
        
        def correlation_handler(correlation):
            print(f"🔗 Correlation found: {correlation.correlation_type} (strength: {correlation.strength:.2f})")
        
        event_system.add_pattern_handler(PatternType.ACCUMULATION, pattern_handler)
        event_system.add_pattern_handler(PatternType.MOMENTUM_BURST, pattern_handler)
        event_system.add_correlation_handler(correlation_handler)
        
        # Create mock fills to demonstrate
        from decimal import Decimal
        from datetime import datetime, timedelta
        
        class MockFill:
            def __init__(self, trade_id, volume, price, side="buy"):
                self.trade_id = trade_id
                self.volume = Decimal(volume)
                self.price = Decimal(price)
                self.cost = self.volume * self.price
                self.side = side
                self.pair = "XBT/USD"
                self.fee = Decimal("5.0")
        
        print("\n📊 Processing demo fills...")
        
        # Simulate accumulation pattern
        base_price = Decimal("50000")
        for i in range(8):
            fill = MockFill(f"ACCUM_{i}", "1.0", str(base_price + i * 10), "buy")
            await event_system.process_fill_event(fill)
            await asyncio.sleep(0.1)  # Small delay to show timing
        
        # Simulate momentum burst
        print("\n🚀 Simulating momentum burst...")
        burst_time = datetime.now()
        for i in range(6):
            fill = MockFill(f"BURST_{i}", "0.5", str(base_price + 100 + i * 5), "buy")
            await event_system.process_fill_event(fill)
            await asyncio.sleep(0.05)  # Very rapid fills
        
        # Get system statistics
        print("\n📊 System Statistics:")
        stats = event_system.get_pattern_statistics()
        print(f"Total patterns detected: {stats.get('total_patterns', 0)}")
        print(f"Pattern distribution: {stats.get('pattern_distribution', {})}")
        
        performance = event_system.get_performance_metrics()
        print(f"\n⚡ Performance Metrics:")
        print(f"Events processed: {performance['throughput']['total_events_stored']}")
        print(f"Patterns detected: {performance['throughput']['total_patterns_detected']}")
        
        # System status
        status = event_system.get_system_status()
        print(f"\n🔧 System Status: {status['status']}")
        print(f"Active patterns: {status['data_summary']['active_patterns']}")
        
        # Cleanup
        await event_system.shutdown()
        print("\n✅ Demo completed successfully!")
    
    # Run the demo
    asyncio.run(demo_advanced_event_system())
