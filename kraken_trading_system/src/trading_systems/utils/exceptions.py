"""
Custom exceptions for the Kraken Trading System.
"""

from typing import Any, Dict, Optional


class TradingSystemError(Exception):
    """Base exception for all trading system errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}
    
    def __str__(self) -> str:
        if self.details:
            return f"{self.message} - Details: {self.details}"
        return self.message


class WebSocketError(TradingSystemError):
    """Exceptions related to WebSocket connections."""
    pass


class ConnectionError(WebSocketError):
    """WebSocket connection failures."""
    pass


class AuthenticationError(TradingSystemError):
    """Authentication failures."""
    pass


class InvalidCredentialsError(AuthenticationError):
    """Invalid API credentials."""
    pass


class OrderError(TradingSystemError):
    """Order-related errors."""
    pass


class InvalidOrderError(OrderError):
    """Invalid order parameters."""
    pass


class OrderRejectedError(OrderError):
    """Order rejected by exchange."""
    pass


class InsufficientFundsError(OrderError):
    """Insufficient funds for order."""
    pass


class RiskManagementError(TradingSystemError):
    """Risk management violations."""
    pass


class PositionLimitExceededError(RiskManagementError):
    """Position size limit exceeded."""
    pass


class OrderValueLimitExceededError(RiskManagementError):
    """Order value limit exceeded."""
    pass


class DailyLossLimitExceededError(RiskManagementError):
    """Daily loss limit exceeded."""
    pass


class MaxOrdersExceededError(RiskManagementError):
    """Maximum open orders limit exceeded."""
    pass


class MarketDataError(TradingSystemError):
    """Market data related errors."""
    pass


class SubscriptionError(MarketDataError):
    """Market data subscription failures."""
    pass


class ConfigurationError(TradingSystemError):
    """Configuration-related errors."""
    pass


class MissingConfigurationError(ConfigurationError):
    """Required configuration missing."""
    pass


class InvalidConfigurationError(ConfigurationError):
    """Invalid configuration values."""
    pass


class ExchangeError(TradingSystemError):
    """Exchange API errors."""
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, details)
        self.error_code = error_code


class RateLimitError(ExchangeError):
    """Rate limit exceeded."""
    pass


class MaintenanceError(ExchangeError):
    """Exchange maintenance mode."""
    pass


class InvalidSymbolError(ExchangeError):
    """Invalid trading symbol/pair."""
    pass


def handle_kraken_error(error_data: Dict[str, Any]) -> Exception:
    """
    Convert Kraken API error responses to appropriate exceptions.
    
    Args:
        error_data: Error data from Kraken API response
        
    Returns:
        Appropriate exception instance
    """
    error_message = error_data.get('error', 'Unknown error')
    
    # Handle array of error messages
    if isinstance(error_message, list):
        error_message = '; '.join(error_message)
    
    # Map common Kraken error codes to specific exceptions
    error_mappings = {
        'EGeneral:Invalid arguments': InvalidOrderError,
        'EService:Unavailable': MaintenanceError,
        'EGeneral:Permission denied': AuthenticationError,
        'EOrder:Insufficient funds': InsufficientFundsError,
        'EGeneral:Rate limit exceeded': RateLimitError,
        'EQuery:Unknown asset pair': InvalidSymbolError,
    }
    
    # Check for specific error patterns
    for error_pattern, exception_class in error_mappings.items():
        if error_pattern in error_message:
            return exception_class(error_message, details=error_data)
    
    # Default to generic exchange error
    return ExchangeError(error_message, details=error_data)