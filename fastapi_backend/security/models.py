#!/usr/bin/env python3
"""
Enhanced Pydantic models with comprehensive input validation
Secure models for API endpoints with built-in security checks
"""

from pydantic import BaseModel, Field, validator, root_validator
from typing import Optional, List, Dict, Any, Union
from decimal import Decimal
from datetime import datetime
from enum import Enum
import re

from api.input_validation import validation_service


class SecureBaseModel(BaseModel):
    """
    Base model with enhanced security validation.
    All API models should inherit from this.
    """

    class Config:
        # Validate assignment to catch issues during runtime
        validate_assignment = True
        # Use enum values instead of names
        use_enum_values = True
        # Allow population by field name or alias
        allow_population_by_field_name = True
        # JSON encoders for special types
        json_encoders = {
            Decimal: str,
            datetime: lambda v: v.isoformat()
        }

    @root_validator(pre=True)
    def validate_object_structure(cls, values):
        """Validate the overall object structure."""
        if isinstance(values, dict):
            # Validate as JSON object
            validation_service.validate_json_object(values)
        return values


# =============================================================================
# Enhanced Transaction Models
# =============================================================================

class EnhancedTransactionRequest(SecureBaseModel):
    """Enhanced transaction request with comprehensive validation."""
    username: str = Field(..., min_length=3, max_length=50, description="Username")
    amount: Decimal = Field(..., gt=0, description="Transaction amount (must be positive)")
    currency_code: str = Field(..., min_length=3, max_length=4, description="Currency code")
    description: Optional[str] = Field(None, max_length=500, description="Transaction description")
    external_reference: Optional[str] = Field(None, max_length=255, description="External reference")

    @validator('username')
    def validate_username(cls, v):
        return validation_service.validate_username(v)

    @validator('currency_code')
    def validate_currency_code(cls, v):
        return validation_service.validate_currency_code(v)

    @validator('amount')
    def validate_amount(cls, v):
        return validation_service.validate_decimal_amount(
            v,
            field_name="amount",
            min_value=Decimal('0.00000001'),
            max_value=Decimal('999999999999.99')
        )

    @validator('description')
    def validate_description(cls, v):
        if v is not None:
            return validation_service.validate_and_sanitize_string(
                v,
                field_name="description",
                max_length=500,
                required=False
            )
        return v

    @validator('external_reference')
    def validate_external_reference(cls, v):
        if v is not None:
            return validation_service.validate_and_sanitize_string(
                v,
                field_name="external_reference",
                max_length=255,
                required=False
            )
        return v


class EnhancedDepositRequest(EnhancedTransactionRequest):
    """Enhanced deposit request with additional validation."""
    force_create_balance: bool = Field(False, description="Create balance if it doesn't exist")
    source_account: Optional[str] = Field(None, max_length=100, description="Source account identifier")

    @validator('source_account')
    def validate_source_account(cls, v):
        if v is not None:
            return validation_service.validate_and_sanitize_string(
                v,
                field_name="source_account",
                max_length=100,
                required=False
            )
        return v


class EnhancedWithdrawalRequest(EnhancedTransactionRequest):
    """Enhanced withdrawal request with additional validation."""
    allow_partial: bool = Field(False, description="Allow partial withdrawal if insufficient funds")
    destination_account: Optional[str] = Field(None, max_length=100, description="Destination account")
    withdrawal_address: Optional[str] = Field(None, max_length=255, description="Withdrawal address")

    @validator('destination_account')
    def validate_destination_account(cls, v):
        if v is not None:
            return validation_service.validate_and_sanitize_string(
                v,
                field_name="destination_account",
                max_length=100,
                required=False
            )
        return v

    @validator('withdrawal_address')
    def validate_withdrawal_address(cls, v):
        if v is not None:
            return validation_service.validate_and_sanitize_string(
                v,
                field_name="withdrawal_address",
                max_length=255,
                required=False
            )
        return v


# =============================================================================
# Enhanced User Models
# =============================================================================

class EnhancedUserQuery(SecureBaseModel):
    """Enhanced user query parameters with validation."""
    username: str = Field(..., min_length=3, max_length=50)

    @validator('username')
    def validate_username(cls, v):
        return validation_service.validate_username(v)


class EnhancedUserUpdate(SecureBaseModel):
    """Enhanced user update request with validation."""
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    email: Optional[str] = Field(None, max_length=255)

    @validator('first_name', 'last_name')
    def validate_names(cls, v):
        if v is not None:
            # Allow only letters, spaces, hyphens, and apostrophes
            if not re.match(r'^[a-zA-Z\s\'-]+$', v.strip()):
                raise ValueError('Names can only contain letters, spaces, hyphens, and apostrophes')
            return validation_service.validate_and_sanitize_string(
                v,
                field_name="name",
                max_length=100,
                required=False
            )
        return v

    @validator('email')
    def validate_email(cls, v):
        if v is not None:
            return validation_service.validate_email(v)
        return v


# =============================================================================
# Enhanced Balance Models
# =============================================================================

class EnhancedBalanceQuery(SecureBaseModel):
    """Enhanced balance query parameters with validation."""
    username: str = Field(..., min_length=3, max_length=50)
    currency: Optional[str] = Field(None, min_length=3, max_length=4)

    @validator('username')
    def validate_username(cls, v):
        return validation_service.validate_username(v)

    @validator('currency')
    def validate_currency(cls, v):
        if v is not None:
            return validation_service.validate_currency_code(v)
        return v


# =============================================================================
# Enhanced Pagination Models
# =============================================================================

class EnhancedPaginationParams(SecureBaseModel):
    """Enhanced pagination parameters with validation."""
    page: int = Field(1, ge=1, le=10000, description="Page number (1-based)")
    page_size: int = Field(20, ge=1, le=100, description="Items per page")
    sort_by: Optional[str] = Field(None, max_length=50, description="Sort field")
    sort_order: Optional[str] = Field("desc", regex="^(asc|desc)$", description="Sort order")

    @validator('page', 'page_size')
    def validate_pagination(cls, v, field):
        page, page_size = validation_service.validate_pagination_params(
            v if field.name == 'page' else 1,
            v if field.name == 'page_size' else 20
        )
        return v

    @validator('sort_by')
    def validate_sort_by(cls, v):
        if v is not None:
            # Only allow alphanumeric characters and underscores
            if not re.match(r'^[a-zA-Z0-9_]+$', v):
                raise ValueError('Sort field can only contain letters, numbers, and underscores')
            return validation_service.validate_and_sanitize_string(
                v,
                field_name="sort_by",
                max_length=50,
                required=False
            )
        return v


# =============================================================================
# Enhanced Search Models
# =============================================================================

class EnhancedSearchParams(SecureBaseModel):
    """Enhanced search parameters with validation."""
    query: str = Field(..., min_length=1, max_length=255, description="Search query")
    filters: Optional[Dict[str, Any]] = Field(None, description="Search filters")

    @validator('query')
    def validate_query(cls, v):
        return validation_service.validate_and_sanitize_string(
            v,
            field_name="search_query",
            max_length=255
        )

    @validator('filters')
    def validate_filters(cls, v):
        if v is not None:
            # Validate filter object structure
            validation_service.validate_json_object(v, max_depth=3)

            # Validate filter keys and values
            for key, value in v.items():
                if not re.match(r'^[a-zA-Z0-9_]+$', key):
                    raise ValueError(f'Filter key "{key}" contains invalid characters')

                if isinstance(value, str):
                    if len(value) > 255:
                        raise ValueError(f'Filter value for "{key}" is too long')

        return v


# =============================================================================
# Enhanced File Upload Models
# =============================================================================

class EnhancedFileUpload(SecureBaseModel):
    """Enhanced file upload parameters with validation."""
    filename: str = Field(..., max_length=255, description="File name")
    content_type: str = Field(..., max_length=100, description="MIME content type")
    file_size: int = Field(..., ge=1, le=10485760, description="File size in bytes (max 10MB)")

    @validator('filename')
    def validate_filename(cls, v):
        # Remove any path components
        filename = v.split('/')[-1].split('\\')[-1]

        # Check for valid filename pattern
        if not re.match(r'^[a-zA-Z0-9._-]+$', filename):
            raise ValueError('Filename contains invalid characters')

        # Check for dangerous extensions
        dangerous_extensions = {
            '.exe', '.bat', '.cmd', '.com', '.pif', '.scr', '.vbs', '.js',
            '.jar', '.php', '.asp', '.aspx', '.jsp', '.py', '.rb', '.pl'
        }

        file_ext = '.' + filename.split('.')[-1].lower() if '.' in filename else ''
        if file_ext in dangerous_extensions:
            raise ValueError('File type not allowed')

        return validation_service.validate_and_sanitize_string(
            filename,
            field_name="filename",
            max_length=255
        )

    @validator('content_type')
    def validate_content_type(cls, v):
        # Allow only safe content types
        safe_content_types = {
            'text/plain', 'text/csv', 'application/json', 'application/pdf',
            'image/jpeg', 'image/png', 'image/gif', 'image/webp'
        }

        if v not in safe_content_types:
            raise ValueError('Content type not allowed')

        return v


# =============================================================================
# Enhanced API Response Models
# =============================================================================

class EnhancedErrorResponse(SecureBaseModel):
    """Enhanced error response with security considerations."""
    success: bool = Field(False, description="Operation success status")
    error: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(None, description="Error code")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")
    request_id: Optional[str] = Field(None, description="Request identifier")

    @validator('error')
    def sanitize_error_message(cls, v):
        # Sanitize error message to prevent information leakage
        return validation_service.sanitize_log_message(v)


class EnhancedSuccessResponse(SecureBaseModel):
    """Enhanced success response."""
    success: bool = Field(True, description="Operation success status")
    message: str = Field(..., description="Success message")
    data: Optional[Any] = Field(None, description="Response data")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")

    @validator('message')
    def sanitize_message(cls, v):
        return validation_service.sanitize_log_message(v)


# =============================================================================
# Enhanced Configuration Models
# =============================================================================

class EnhancedAPIConfigUpdate(SecureBaseModel):
    """Enhanced API configuration update with validation."""
    rate_limit_requests: Optional[int] = Field(None, ge=1, le=10000)
    rate_limit_window: Optional[int] = Field(None, ge=60, le=3600)
    max_request_size: Optional[int] = Field(None, ge=1024, le=104857600)  # 1KB to 100MB
    request_timeout: Optional[int] = Field(None, ge=1, le=300)  # 1 to 300 seconds

    @root_validator
    def validate_config_changes(cls, values):
        """Validate configuration changes don't break the system."""
        rate_limit = values.get('rate_limit_requests')
        window = values.get('rate_limit_window')

        if rate_limit and window:
            # Ensure rate limit isn't too restrictive
            requests_per_second = rate_limit / window * 60
            if requests_per_second < 0.1:  # Less than 1 request per 10 seconds
                raise ValueError('Rate limit configuration is too restrictive')

        return values


# =============================================================================
# Utility Functions for Model Validation
# =============================================================================

def validate_model_with_security(model_class: type, data: Dict[str, Any]) -> Any:
    """
    Validate model data with enhanced security checks.

    Args:
        model_class: Pydantic model class
        data: Data to validate

    Returns:
        Validated model instance

    Raises:
        HTTPException: If validation fails
    """
    try:
        # Pre-validation security checks
        validation_service.validate_json_object(data)

        # Create and validate model
        model_instance = model_class(**data)

        return model_instance

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Validation error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Model validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Data validation failed"
        )


def create_secure_response(data: Any, message: str = "Operation successful") -> EnhancedSuccessResponse:
    """Create a secure API response."""
    return EnhancedSuccessResponse(
        message=message,
        data=data
    )


def create_secure_error(error_message: str, error_code: Optional[str] = None) -> EnhancedErrorResponse:
    """Create a secure error response."""
    return EnhancedErrorResponse(
        error=error_message,
        error_code=error_code
    )
