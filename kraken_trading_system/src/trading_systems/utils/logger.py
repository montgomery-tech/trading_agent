"""
Logging configuration for the Kraken Trading System.
"""

import logging
import sys
from typing import Any, Dict

import structlog
from structlog.types import Processor

from ..config.settings import settings


def setup_logging() -> None:
    """Set up structured logging with appropriate configuration."""
    
    # Configure structlog processors
    processors: list[Processor] = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    
    # Add appropriate renderer based on format setting
    if settings.log_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        context_class=dict,
        cache_logger_on_first_use=True,
    )
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level.upper()),
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a structured logger instance."""
    return structlog.get_logger(name)


def log_websocket_event(
    logger: structlog.BoundLogger,
    event: str,
    **kwargs: Any
) -> None:
    """Log WebSocket events with standardized format."""
    logger.info(
        "websocket_event",
        websocket_event=event,
        component="websocket",
        **kwargs
    )


def log_trading_event(
    logger: structlog.BoundLogger,
    event: str,
    order_id: str = None,
    pair: str = None,
    **kwargs: Any
) -> None:
    """Log trading events with standardized format."""
    log_data = {
        "event": event,
        "component": "trading",
        **kwargs
    }
    
    if order_id:
        log_data["order_id"] = order_id
    if pair:
        log_data["pair"] = pair
    
    logger.info("trading_event", **log_data)


def log_risk_event(
    logger: structlog.BoundLogger,
    event: str,
    risk_type: str,
    **kwargs: Any
) -> None:
    """Log risk management events with standardized format."""
    logger.warning(
        "risk_event",
        event=event,
        risk_type=risk_type,
        component="risk_management",
        **kwargs
    )


def log_error(
    logger: structlog.BoundLogger,
    error: Exception,
    context: Dict[str, Any] = None,
    **kwargs: Any
) -> None:
    """Log errors with standardized format and context."""
    log_data = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        **kwargs
    }
    
    if context:
        log_data.update(context)
    
    logger.error("error_occurred", **log_data, exc_info=True)


class LoggerMixin:
    """Mixin class to add logging capabilities to other classes."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = get_logger(self.__class__.__name__)
    
    def log_info(self, message: str, **kwargs: Any) -> None:
        """Log info message with class context."""
        self.logger.info(message, class_name=self.__class__.__name__, **kwargs)
    
    def log_warning(self, message: str, **kwargs: Any) -> None:
        """Log warning message with class context."""
        self.logger.warning(message, class_name=self.__class__.__name__, **kwargs)
    
    def log_error(self, message: str, error: Exception = None, **kwargs: Any) -> None:
        """Log error message with class context."""
        log_data = {"class_name": self.__class__.__name__, **kwargs}
        if error:
            log_data.update({
                "error_type": type(error).__name__,
                "error_message": str(error)
            })
            self.logger.error(message, **log_data, exc_info=True)
        else:
            self.logger.error(message, **log_data)


# Initialize logging on import
setup_logging()
