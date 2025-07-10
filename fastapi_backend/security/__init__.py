"""
Security package for FastAPI Balance Tracking System
Provides input validation, middleware, and secure models
"""

from .input_validation import validation_service, InputValidationService
from .middleware import (
    create_security_middleware_stack,
    SecurityHeadersMiddleware,
    RequestSizeMiddleware,
    IPRateLimitMiddleware,
    security_exception_handler,
    security_metrics
)
from .models import (
    SecureBaseModel,
    EnhancedTransactionRequest,
    EnhancedDepositRequest,
    EnhancedWithdrawalRequest,
    EnhancedUserQuery,
    EnhancedUserUpdate,
    EnhancedBalanceQuery,
    EnhancedPaginationParams,
    EnhancedErrorResponse,
    EnhancedSuccessResponse,
    validate_model_with_security,
    create_secure_response,
    create_secure_error
)

__all__ = [
    # Validation Service
    'validation_service',
    'InputValidationService',

    # Middleware
    'create_security_middleware_stack',
    'SecurityHeadersMiddleware',
    'RequestSizeMiddleware',
    'IPRateLimitMiddleware',
    'security_exception_handler',
    'security_metrics',

    # Secure Models
    'SecureBaseModel',
    'EnhancedTransactionRequest',
    'EnhancedDepositRequest',
    'EnhancedWithdrawalRequest',
    'EnhancedUserQuery',
    'EnhancedUserUpdate',
    'EnhancedBalanceQuery',
    'EnhancedPaginationParams',
    'EnhancedErrorResponse',
    'EnhancedSuccessResponse',

    # Utility Functions
    'validate_model_with_security',
    'create_secure_response',
    'create_secure_error'
]
