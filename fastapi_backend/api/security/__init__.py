"""
Security package for FastAPI Balance Tracking System
Enhanced with comprehensive rate limiting and security features
"""

from .input_validation import validation_service, InputValidationService
from .middleware import (
    create_security_middleware_stack,
    SecurityHeadersMiddleware,
    RequestSizeMiddleware,
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

# Enhanced Rate Limiting (NEW)
ENHANCED_RATE_LIMITING_AVAILABLE = False
try:
    from .enhanced_rate_limiting_service import (
        rate_limiting_service,
        EnhancedRateLimitingService,
        RateLimitConfig,
        RateLimitResult,
        RateLimitType
    )
    from .enhanced_rate_limiting_middleware import (
        EnhancedRateLimitingMiddleware,
        RateLimitingConfigMiddleware,
        create_enhanced_rate_limiting_middleware
    )

    ENHANCED_RATE_LIMITING_AVAILABLE = True
    print("✅ Enhanced rate limiting imports successful")
except Exception as e:
    print(f"❌ Enhanced rate limiting import failed: {e}")
    ENHANCED_RATE_LIMITING_AVAILABLE = False

__all__ = [
    # Validation Service
    'validation_service',
    'InputValidationService',

    # Middleware
    'create_security_middleware_stack',
    'SecurityHeadersMiddleware',
    'RequestSizeMiddleware',
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
    'create_secure_error',

    # Enhanced Rate Limiting Status
    'ENHANCED_RATE_LIMITING_AVAILABLE',
]

# Add enhanced rate limiting exports if available
if ENHANCED_RATE_LIMITING_AVAILABLE:
    __all__.extend([
        'rate_limiting_service',
        'EnhancedRateLimitingService',
        'RateLimitConfig',
        'RateLimitResult',
        'RateLimitType',
        'EnhancedRateLimitingMiddleware',
        'RateLimitingConfigMiddleware',
        'create_enhanced_rate_limiting_middleware'
    ])
