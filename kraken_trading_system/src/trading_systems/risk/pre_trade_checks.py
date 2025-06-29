"""
Pre-trade Risk Validation System for Kraken Trading System

This module provides comprehensive pre-trade risk checks to ensure safe order placement
and prevent unwanted trading scenarios.

Task 3.2.C: Implement Pre-trade Risk Validation

File Location: src/trading_systems/risk/pre_trade_checks.py
"""

from decimal import Decimal
from typing import Any, Dict, List, Optional, Union, Callable
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass

from pydantic import BaseModel, Field

# Import order models
from ..exchanges.kraken.order_requests import BaseOrderRequest
from ..exchanges.kraken.account_models import OrderSide, OrderType


class RiskLevel(str, Enum):
    """Risk levels for different checks."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskCheckResult(str, Enum):
    """Results of risk checks."""
    PASS = "pass"
    WARNING = "warning"
    FAIL = "fail"
    BLOCK = "block"


@dataclass
class RiskCheckResponse:
    """Response from a risk check."""
    result: RiskCheckResult
    message: str
    risk_level: RiskLevel
    details: Optional[Dict[str, Any]] = None
    suggested_action: Optional[str] = None


class AccountBalance(BaseModel):
    """Account balance information for risk checks."""
    currency: str = Field(..., description="Currency code")
    total_balance: Decimal = Field(..., description="Total balance")
    available_balance: Decimal = Field(..., description="Available balance for trading")
    reserved_balance: Decimal = Field(0, description="Reserved/locked balance")
    
    @property
    def utilization_percentage(self) -> float:
        """Calculate balance utilization percentage."""
        if self.total_balance == 0:
            return 0.0
        return float((self.total_balance - self.available_balance) / self.total_balance * 100)


class PositionInfo(BaseModel):
    """Position information for risk assessment."""
    pair: str = Field(..., description="Trading pair")
    size: Decimal = Field(..., description="Position size (positive for long, negative for short)")
    entry_price: Optional[Decimal] = Field(None, description="Average entry price")
    current_price: Optional[Decimal] = Field(None, description="Current market price")
    unrealized_pnl: Optional[Decimal] = Field(None, description="Unrealized P&L")
    
    @property
    def is_long(self) -> bool:
        """Check if position is long."""
        return self.size > 0
    
    @property
    def is_short(self) -> bool:
        """Check if position is short."""
        return self.size < 0
    
    @property
    def absolute_size(self) -> Decimal:
        """Get absolute position size."""
        return abs(self.size)


class RiskLimits(BaseModel):
    """Risk limits configuration."""
    
    # Balance limits
    max_balance_utilization: float = Field(0.95, description="Maximum balance utilization (95%)")
    min_available_balance: Decimal = Field(Decimal('100'), description="Minimum available balance")
    
    # Order size limits
    max_order_size_usd: Decimal = Field(Decimal('100000'), description="Maximum order size in USD")
    max_order_percentage: float = Field(0.10, description="Maximum order as % of balance (10%)")
    
    # Position limits
    max_position_size_usd: Decimal = Field(Decimal('500000'), description="Maximum position size in USD")
    max_concentration: float = Field(0.25, description="Maximum concentration in single asset (25%)")
    
    # Daily limits
    max_daily_trades: int = Field(100, description="Maximum trades per day")
    max_daily_volume_usd: Decimal = Field(Decimal('1000000'), description="Maximum daily volume in USD")
    
    # Risk ratios
    max_leverage: float = Field(1.0, description="Maximum leverage allowed")
    max_drawdown: float = Field(0.20, description="Maximum drawdown allowed (20%)")


class TradingStatistics(BaseModel):
    """Trading statistics for risk assessment."""
    daily_trade_count: int = Field(0, description="Number of trades today")
    daily_volume_usd: Decimal = Field(0, description="Total volume traded today")
    weekly_pnl: Decimal = Field(0, description="P&L for the week")
    current_drawdown: float = Field(0.0, description="Current drawdown percentage")
    consecutive_losses: int = Field(0, description="Consecutive losing trades")


class PreTradeRiskValidator:
    """Comprehensive pre-trade risk validation system."""
    
    def __init__(self, risk_limits: Optional[RiskLimits] = None):
        """
        Initialize the risk validator.
        
        Args:
            risk_limits: Risk limits configuration
        """
        self.risk_limits = risk_limits or RiskLimits()
        self.risk_checks: List[Callable] = []
        self._register_default_checks()
    
    def _register_default_checks(self):
        """Register default risk checks."""
        self.risk_checks = [
            self._check_balance_availability,
            self._check_order_size_limits,
            self._check_position_concentration,
            self._check_daily_limits,
            self._check_leverage_limits,
            self._check_market_conditions,
            self._check_order_frequency,
            self._check_drawdown_limits
        ]
    
    def validate_order(
        self,
        order_request: BaseOrderRequest,
        account_balances: List[AccountBalance],
        current_positions: List[PositionInfo],
        trading_stats: TradingStatistics,
        market_price: Optional[Decimal] = None
    ) -> List[RiskCheckResponse]:
        """
        Validate an order against all risk checks.
        
        Args:
            order_request: Order to validate
            account_balances: Current account balances
            current_positions: Current positions
            trading_stats: Trading statistics
            market_price: Current market price for the pair
            
        Returns:
            List of risk check responses
        """
        responses = []
        
        context = {
            'order_request': order_request,
            'account_balances': account_balances,
            'current_positions': current_positions,
            'trading_stats': trading_stats,
            'market_price': market_price,
            'estimated_order_value': self._estimate_order_value(order_request, market_price)
        }
        
        for check_func in self.risk_checks:
            try:
                response = check_func(context)
                responses.append(response)
            except Exception as e:
                responses.append(RiskCheckResponse(
                    result=RiskCheckResult.FAIL,
                    message=f"Risk check error: {str(e)}",
                    risk_level=RiskLevel.HIGH,
                    details={'error': str(e)}
                ))
        
        return responses
    
    def _estimate_order_value(self, order_request: BaseOrderRequest, market_price: Optional[Decimal]) -> Decimal:
        """Estimate the USD value of an order."""
        if hasattr(order_request, 'price') and order_request.price:
            # Limit order - use limit price
            price = order_request.price
        elif market_price:
            # Market order - use current market price
            price = market_price
        else:
            # No price available - use conservative estimate
            price = Decimal('50000')  # Default BTC price for estimation
        
        return order_request.volume * price
    
    def _check_balance_availability(self, context: Dict[str, Any]) -> RiskCheckResponse:
        """Check if sufficient balance is available for the order."""
        order_request = context['order_request']
        account_balances = context['account_balances']
        estimated_value = context['estimated_order_value']
        
        # Find relevant balance (assume USD for simplicity)
        usd_balance = None
        for balance in account_balances:
            if balance.currency.upper() in ['USD', 'ZUSD']:
                usd_balance = balance
                break
        
        if not usd_balance:
            return RiskCheckResponse(
                result=RiskCheckResult.WARNING,
                message="No USD balance found for validation",
                risk_level=RiskLevel.MEDIUM,
                suggested_action="Verify account balances"
            )
        
        # Check if sufficient balance for buy orders
        if order_request.side == OrderSide.BUY:
            required_balance = estimated_value * Decimal('1.01')  # Add 1% buffer for fees
            
            if usd_balance.available_balance < required_balance:
                return RiskCheckResponse(
                    result=RiskCheckResult.BLOCK,
                    message=f"Insufficient balance: need ${required_balance}, have ${usd_balance.available_balance}",
                    risk_level=RiskLevel.CRITICAL,
                    details={
                        'required': str(required_balance),
                        'available': str(usd_balance.available_balance),
                        'shortfall': str(required_balance - usd_balance.available_balance)
                    },
                    suggested_action="Reduce order size or add funds"
                )
        
        # Check balance utilization
        utilization = usd_balance.utilization_percentage
        if utilization > self.risk_limits.max_balance_utilization * 100:
            return RiskCheckResponse(
                result=RiskCheckResult.WARNING,
                message=f"High balance utilization: {utilization:.1f}%",
                risk_level=RiskLevel.MEDIUM,
                details={'utilization_percentage': utilization},
                suggested_action="Consider reducing position sizes"
            )
        
        return RiskCheckResponse(
            result=RiskCheckResult.PASS,
            message="Balance check passed",
            risk_level=RiskLevel.LOW
        )
    
    def _check_order_size_limits(self, context: Dict[str, Any]) -> RiskCheckResponse:
        """Check if order size is within limits."""
        order_request = context['order_request']
        estimated_value = context['estimated_order_value']
        account_balances = context['account_balances']
        
        # Check absolute size limit
        if estimated_value > self.risk_limits.max_order_size_usd:
            return RiskCheckResponse(
                result=RiskCheckResult.BLOCK,
                message=f"Order size ${estimated_value} exceeds limit of ${self.risk_limits.max_order_size_usd}",
                risk_level=RiskLevel.CRITICAL,
                details={
                    'order_value': str(estimated_value),
                    'limit': str(self.risk_limits.max_order_size_usd)
                },
                suggested_action="Reduce order size"
            )
        
        # Check percentage of balance
        total_balance = sum(balance.total_balance for balance in account_balances)
        if total_balance > 0:
            percentage = float(estimated_value / total_balance)
            if percentage > self.risk_limits.max_order_percentage:
                return RiskCheckResponse(
                    result=RiskCheckResult.WARNING,
                    message=f"Order is {percentage:.1%} of total balance (limit: {self.risk_limits.max_order_percentage:.1%})",
                    risk_level=RiskLevel.MEDIUM,
                    details={
                        'order_percentage': percentage,
                        'limit_percentage': self.risk_limits.max_order_percentage
                    },
                    suggested_action="Consider reducing order size"
                )
        
        return RiskCheckResponse(
            result=RiskCheckResult.PASS,
            message="Order size check passed",
            risk_level=RiskLevel.LOW
        )
    
    def _check_position_concentration(self, context: Dict[str, Any]) -> RiskCheckResponse:
        """Check position concentration risk."""
        order_request = context['order_request']
        current_positions = context['current_positions']
        estimated_value = context['estimated_order_value']
        
        # Find existing position in the same pair
        existing_position = None
        for position in current_positions:
            if position.pair == order_request.pair:
                existing_position = position
                break
        
        # Calculate total portfolio value
        total_portfolio_value = sum(
            abs(pos.size * (pos.current_price or Decimal('1'))) 
            for pos in current_positions
        )
        
        # Calculate concentration after this order
        if existing_position:
            new_position_value = abs(existing_position.size) * (existing_position.current_price or Decimal('1'))
            if order_request.side == OrderSide.BUY:
                new_position_value += estimated_value
            else:
                new_position_value = max(0, new_position_value - estimated_value)
        else:
            new_position_value = estimated_value
        
        if total_portfolio_value > 0:
            concentration = float(new_position_value / total_portfolio_value)
            if concentration > self.risk_limits.max_concentration:
                return RiskCheckResponse(
                    result=RiskCheckResult.WARNING,
                    message=f"High concentration in {order_request.pair}: {concentration:.1%}",
                    risk_level=RiskLevel.MEDIUM,
                    details={
                        'concentration': concentration,
                        'limit': self.risk_limits.max_concentration,
                        'pair': order_request.pair
                    },
                    suggested_action="Diversify portfolio or reduce position size"
                )
        
        return RiskCheckResponse(
            result=RiskCheckResult.PASS,
            message="Position concentration check passed",
            risk_level=RiskLevel.LOW
        )
    
    def _check_daily_limits(self, context: Dict[str, Any]) -> RiskCheckResponse:
        """Check daily trading limits."""
        trading_stats = context['trading_stats']
        estimated_value = context['estimated_order_value']
        
        # Check daily trade count
        if trading_stats.daily_trade_count >= self.risk_limits.max_daily_trades:
            return RiskCheckResponse(
                result=RiskCheckResult.BLOCK,
                message=f"Daily trade limit reached: {trading_stats.daily_trade_count}/{self.risk_limits.max_daily_trades}",
                risk_level=RiskLevel.HIGH,
                details={
                    'current_count': trading_stats.daily_trade_count,
                    'limit': self.risk_limits.max_daily_trades
                },
                suggested_action="Wait until next trading day"
            )
        
        # Check daily volume
        projected_volume = trading_stats.daily_volume_usd + estimated_value
        if projected_volume > self.risk_limits.max_daily_volume_usd:
            return RiskCheckResponse(
                result=RiskCheckResult.WARNING,
                message=f"Daily volume limit will be exceeded: ${projected_volume} > ${self.risk_limits.max_daily_volume_usd}",
                risk_level=RiskLevel.MEDIUM,
                details={
                    'current_volume': str(trading_stats.daily_volume_usd),
                    'order_value': str(estimated_value),
                    'projected_volume': str(projected_volume),
                    'limit': str(self.risk_limits.max_daily_volume_usd)
                },
                suggested_action="Reduce order size or wait until next day"
            )
        
        return RiskCheckResponse(
            result=RiskCheckResult.PASS,
            message="Daily limits check passed",
            risk_level=RiskLevel.LOW
        )
    
    def _check_leverage_limits(self, context: Dict[str, Any]) -> RiskCheckResponse:
        """Check leverage limits."""
        # For spot trading, leverage should be 1.0
        # This is a placeholder for future margin trading support
        return RiskCheckResponse(
            result=RiskCheckResult.PASS,
            message="Leverage check passed (spot trading)",
            risk_level=RiskLevel.LOW
        )
    
    def _check_market_conditions(self, context: Dict[str, Any]) -> RiskCheckResponse:
        """Check market conditions for risk assessment."""
        market_price = context.get('market_price')
        
        if not market_price:
            return RiskCheckResponse(
                result=RiskCheckResult.WARNING,
                message="No market price available for validation",
                risk_level=RiskLevel.MEDIUM,
                suggested_action="Verify market data connectivity"
            )
        
        # Placeholder for market condition checks
        # Could include volatility, spread, volume analysis
        
        return RiskCheckResponse(
            result=RiskCheckResult.PASS,
            message="Market conditions check passed",
            risk_level=RiskLevel.LOW
        )
    
    def _check_order_frequency(self, context: Dict[str, Any]) -> RiskCheckResponse:
        """Check for excessive order frequency."""
        trading_stats = context['trading_stats']
        
        # Simple check - more sophisticated logic could track timing
        if trading_stats.daily_trade_count > 50:
            return RiskCheckResponse(
                result=RiskCheckResult.WARNING,
                message=f"High trading frequency: {trading_stats.daily_trade_count} trades today",
                risk_level=RiskLevel.MEDIUM,
                suggested_action="Consider reducing trading frequency"
            )
        
        return RiskCheckResponse(
            result=RiskCheckResult.PASS,
            message="Order frequency check passed",
            risk_level=RiskLevel.LOW
        )
    
    def _check_drawdown_limits(self, context: Dict[str, Any]) -> RiskCheckResponse:
        """Check drawdown limits."""
        trading_stats = context['trading_stats']
        
        if trading_stats.current_drawdown > self.risk_limits.max_drawdown:
            return RiskCheckResponse(
                result=RiskCheckResult.WARNING,
                message=f"High drawdown: {trading_stats.current_drawdown:.1%} (limit: {self.risk_limits.max_drawdown:.1%})",
                risk_level=RiskLevel.HIGH,
                details={
                    'current_drawdown': trading_stats.current_drawdown,
                    'limit': self.risk_limits.max_drawdown
                },
                suggested_action="Consider reducing position sizes until drawdown recovers"
            )
        
        # Check consecutive losses
        if trading_stats.consecutive_losses >= 5:
            return RiskCheckResponse(
                result=RiskCheckResult.WARNING,
                message=f"Consecutive losses: {trading_stats.consecutive_losses}",
                risk_level=RiskLevel.MEDIUM,
                details={'consecutive_losses': trading_stats.consecutive_losses},
                suggested_action="Consider taking a break or reviewing strategy"
            )
        
        return RiskCheckResponse(
            result=RiskCheckResult.PASS,
            message="Drawdown limits check passed",
            risk_level=RiskLevel.LOW
        )


class RiskAnalyzer:
    """Analyzes and summarizes risk check results."""
    
    @staticmethod
    def analyze_results(responses: List[RiskCheckResponse]) -> Dict[str, Any]:
        """
        Analyze risk check responses and provide summary.
        
        Args:
            responses: List of risk check responses
            
        Returns:
            Analysis summary
        """
        # Count results by type
        result_counts = {result.value: 0 for result in RiskCheckResult}
        risk_levels = {level.value: 0 for level in RiskLevel}
        
        blocking_issues = []
        warnings = []
        
        for response in responses:
            result_counts[response.result.value] += 1
            risk_levels[response.risk_level.value] += 1
            
            if response.result == RiskCheckResult.BLOCK:
                blocking_issues.append(response.message)
            elif response.result in [RiskCheckResult.WARNING, RiskCheckResult.FAIL]:
                warnings.append(response.message)
        
        # Determine overall recommendation
        if result_counts[RiskCheckResult.BLOCK.value] > 0:
            recommendation = "BLOCK_ORDER"
            reason = f"{result_counts[RiskCheckResult.BLOCK.value]} blocking issue(s) found"
        elif result_counts[RiskCheckResult.FAIL.value] > 0:
            recommendation = "REJECT_ORDER"
            reason = f"{result_counts[RiskCheckResult.FAIL.value]} critical issue(s) found"
        elif result_counts[RiskCheckResult.WARNING.value] > 0:
            recommendation = "PROCEED_WITH_CAUTION"
            reason = f"{result_counts[RiskCheckResult.WARNING.value]} warning(s) found"
        else:
            recommendation = "APPROVE_ORDER"
            reason = "All risk checks passed"
        
        return {
            'recommendation': recommendation,
            'reason': reason,
            'total_checks': len(responses),
            'result_summary': result_counts,
            'risk_level_summary': risk_levels,
            'blocking_issues': blocking_issues,
            'warnings': warnings,
            'overall_risk_score': RiskAnalyzer._calculate_risk_score(responses)
        }
    
    @staticmethod
    def _calculate_risk_score(responses: List[RiskCheckResponse]) -> float:
        """Calculate overall risk score (0-100, higher = more risky)."""
        if not responses:
            return 0.0
        
        score_map = {
            RiskCheckResult.PASS: 0,
            RiskCheckResult.WARNING: 25,
            RiskCheckResult.FAIL: 75,
            RiskCheckResult.BLOCK: 100
        }
        
        total_score = sum(score_map.get(response.result, 50) for response in responses)
        return total_score / len(responses)


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def validate_order_with_defaults(
    order_request: BaseOrderRequest,
    account_balances: List[AccountBalance],
    current_positions: Optional[List[PositionInfo]] = None,
    trading_stats: Optional[TradingStatistics] = None,
    market_price: Optional[Decimal] = None,
    custom_limits: Optional[RiskLimits] = None
) -> Dict[str, Any]:
    """
    Convenience function to validate an order with default settings.
    
    Args:
        order_request: Order to validate
        account_balances: Current account balances
        current_positions: Current positions (optional)
        trading_stats: Trading statistics (optional)
        market_price: Current market price (optional)
        custom_limits: Custom risk limits (optional)
        
    Returns:
        Risk analysis results
    """
    validator = PreTradeRiskValidator(custom_limits)
    
    responses = validator.validate_order(
        order_request=order_request,
        account_balances=account_balances,
        current_positions=current_positions or [],
        trading_stats=trading_stats or TradingStatistics(),
        market_price=market_price
    )
    
    return RiskAnalyzer.analyze_results(responses)


def create_conservative_limits() -> RiskLimits:
    """Create conservative risk limits for cautious trading."""
    return RiskLimits(
        max_balance_utilization=0.80,  # 80% max utilization
        max_order_size_usd=Decimal('50000'),  # $50k max order
        max_order_percentage=0.05,  # 5% max of balance
        max_position_size_usd=Decimal('200000'),  # $200k max position
        max_concentration=0.15,  # 15% max concentration
        max_daily_trades=50,  # 50 trades per day
        max_daily_volume_usd=Decimal('500000'),  # $500k daily volume
        max_drawdown=0.10  # 10% max drawdown
    )


def create_aggressive_limits() -> RiskLimits:
    """Create aggressive risk limits for active trading."""
    return RiskLimits(
        max_balance_utilization=0.98,  # 98% max utilization
        max_order_size_usd=Decimal('500000'),  # $500k max order
        max_order_percentage=0.20,  # 20% max of balance
        max_position_size_usd=Decimal('2000000'),  # $2M max position
        max_concentration=0.40,  # 40% max concentration
        max_daily_trades=200,  # 200 trades per day
        max_daily_volume_usd=Decimal('5000000'),  # $5M daily volume
        max_drawdown=0.30  # 30% max drawdown
    )
