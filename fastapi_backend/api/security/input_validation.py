#!/usr/bin/env python3
"""
Input Validation Service for the Balance Tracking API
Comprehensive input validation, sanitization, and security checks
"""

import re
import html
import logging
from typing import Any, Dict, List, Optional, Union
from decimal import Decimal, InvalidOperation
from datetime import datetime
from urllib.parse import urlparse
import bleach
import validators

from fastapi import HTTPException, status

logger = logging.getLogger(__name__)


class InputValidationService:
    """
    Comprehensive input validation and sanitization service.

    Provides protection against:
    - SQL injection attacks
    - XSS (Cross-Site Scripting) attacks
    - Path traversal attacks
    - Command injection
    - Input size attacks
    - Format string attacks
    - Invalid data types
    """

    def __init__(self):
        # XSS protection configuration
        self.allowed_html_tags = []  # No HTML tags allowed in our API
        self.allowed_html_attributes = {}

        # Size limits
        self.max_string_length = 10000
        self.max_description_length = 500
        self.max_username_length = 50
        self.max_email_length = 255

        # Regular expressions for validation
        self.username_pattern = re.compile(r'^[a-zA-Z0-9_]{3,50}$')
        self.currency_code_pattern = re.compile(r'^[A-Z]{3,4}$')
        self.transaction_id_pattern = re.compile(r'^[a-f0-9\-]{36}$')
        self.safe_filename_pattern = re.compile(r'^[a-zA-Z0-9._-]+$')

        # SQL injection patterns (common attack vectors)
        self.sql_injection_patterns = [
            re.compile(r'(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION|SCRIPT)\b)', re.IGNORECASE),
            re.compile(r'(--|#|\/\*|\*\/)', re.IGNORECASE),
            re.compile(r'(\b(OR|AND)\b\s+\w+\s*=\s*\w+)', re.IGNORECASE),
            re.compile(r'(\'\s*(OR|AND)\s*\'\w*\'\s*=\s*\'\w*)', re.IGNORECASE),
            re.compile(r'(\bunion\b.*\bselect\b)', re.IGNORECASE),
            re.compile(r'(\bexec\b.*\bxp_)', re.IGNORECASE),
        ]

        # Command injection patterns
        self.command_injection_patterns = [
            re.compile(r'[;&|`$(){}[\]<>]'),
            re.compile(r'(wget|curl|nc|netcat|python|perl|ruby|bash|sh|cmd|powershell)', re.IGNORECASE),
        ]

        # Path traversal patterns
        self.path_traversal_patterns = [
            re.compile(r'\.\.\/'),
            re.compile(r'\.\.\\'),
            re.compile(r'\/etc\/passwd'),
            re.compile(r'\/windows\/system32', re.IGNORECASE),
        ]

        logger.info("Input validation service initialized")

    def validate_and_sanitize_string(
        self,
        value: str,
        field_name: str,
        max_length: Optional[int] = None,
        allow_html: bool = False,
        required: bool = True
    ) -> str:
        """
        Validate and sanitize string input.

        Args:
            value: Input string to validate
            field_name: Name of the field (for error messages)
            max_length: Maximum allowed length
            allow_html: Whether to allow HTML content
            required: Whether the field is required

        Returns:
            Sanitized string value

        Raises:
            HTTPException: If validation fails
        """
        if value is None:
            if required:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"{field_name} is required"
                )
            return ""

        if not isinstance(value, str):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{field_name} must be a string"
            )

        # Strip whitespace
        value = value.strip()

        # Check if empty after stripping
        if not value and required:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{field_name} cannot be empty"
            )

        # Length validation
        max_len = max_length or self.max_string_length
        if len(value) > max_len:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{field_name} exceeds maximum length of {max_len} characters"
            )

        # Check for SQL injection patterns
        self._check_sql_injection(value, field_name)

        # Check for command injection patterns
        self._check_command_injection(value, field_name)

        # Check for path traversal patterns
        self._check_path_traversal(value, field_name)

        # XSS protection
        if not allow_html:
            # Remove all HTML tags and entities
            value = bleach.clean(value, tags=self.allowed_html_tags, attributes=self.allowed_html_attributes)
            value = html.escape(value)
        else:
            # Allow only safe HTML
            value = bleach.clean(value, tags=self.allowed_html_tags, attributes=self.allowed_html_attributes)

        # Remove null bytes and control characters
        value = value.replace('\x00', '')
        value = ''.join(char for char in value if ord(char) >= 32 or char in '\t\n\r')

        return value

    def validate_username(self, username: str) -> str:
        """Validate username format and content."""
        if not username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username is required"
            )

        username = username.strip().lower()

        # Length check
        if len(username) < 3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username must be at least 3 characters long"
            )

        if len(username) > self.max_username_length:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Username cannot exceed {self.max_username_length} characters"
            )

        # Format validation
        if not self.username_pattern.match(username):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username can only contain letters, numbers, and underscores"
            )

        # Check for reserved usernames
        reserved_usernames = {
            'admin', 'administrator', 'root', 'system', 'api', 'support',
            'help', 'info', 'contact', 'sales', 'marketing', 'security',
            'null', 'undefined', 'anonymous', 'guest', 'test', 'demo'
        }

        if username in reserved_usernames:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username is reserved and cannot be used"
            )

        return username

    def validate_email(self, email: str) -> str:
        """Validate email format and content."""
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is required"
            )

        email = email.strip().lower()

        # Length check
        if len(email) > self.max_email_length:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Email cannot exceed {self.max_email_length} characters"
            )

        # Format validation
        if not validators.email(email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid email format"
            )

        # Additional security checks
        self._check_sql_injection(email, "email")

        return email

    def validate_currency_code(self, currency_code: str) -> str:
        """Validate currency code format."""
        if not currency_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Currency code is required"
            )

        currency_code = currency_code.strip().upper()

        if not self.currency_code_pattern.match(currency_code):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Currency code must be 3-4 uppercase letters"
            )

        return currency_code

    def validate_decimal_amount(
        self,
        amount: Union[str, int, float, Decimal],
        field_name: str = "amount",
        min_value: Optional[Decimal] = None,
        max_value: Optional[Decimal] = None
    ) -> Decimal:
        """Validate and convert amount to Decimal."""
        if amount is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{field_name} is required"
            )

        try:
            # Convert to Decimal
            if isinstance(amount, str):
                # Remove any non-numeric characters except decimal point and minus
                amount = re.sub(r'[^\d.-]', '', amount)
                decimal_amount = Decimal(amount)
            else:
                decimal_amount = Decimal(str(amount))

            # Check for NaN or infinity
            if not decimal_amount.is_finite():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"{field_name} must be a valid number"
                )

            # Range validation
            if min_value is not None and decimal_amount < min_value:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"{field_name} must be at least {min_value}"
                )

            if max_value is not None and decimal_amount > max_value:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"{field_name} cannot exceed {max_value}"
                )

            return decimal_amount

        except (InvalidOperation, ValueError) as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{field_name} must be a valid number"
            )

    def validate_transaction_id(self, transaction_id: str) -> str:
        """Validate transaction ID format (UUID)."""
        if not transaction_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Transaction ID is required"
            )

        transaction_id = transaction_id.strip().lower()

        if not self.transaction_id_pattern.match(transaction_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid transaction ID format"
            )

        return transaction_id

    def validate_pagination_params(self, page: int, page_size: int) -> tuple[int, int]:
        """Validate pagination parameters."""
        if page < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Page number must be 1 or greater"
            )

        if page_size < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Page size must be 1 or greater"
            )

        if page_size > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Page size cannot exceed 100"
            )

        return page, page_size

    def validate_url(self, url: str, field_name: str = "URL") -> str:
        """Validate URL format and security."""
        if not url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{field_name} is required"
            )

        url = url.strip()

        # Basic URL validation
        if not validators.url(url):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid {field_name} format"
            )

        # Parse URL for security checks
        parsed = urlparse(url)

        # Check for dangerous schemes
        allowed_schemes = {'http', 'https'}
        if parsed.scheme not in allowed_schemes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{field_name} must use HTTP or HTTPS"
            )

        # Check for local addresses in production
        local_addresses = {'localhost', '127.0.0.1', '0.0.0.0', '::1'}
        if parsed.hostname in local_addresses:
            # Allow in development, warn in production
            logger.warning(f"Local address detected in {field_name}: {url}")

        return url

    def _check_sql_injection(self, value: str, field_name: str) -> None:
        """Check for SQL injection patterns."""
        for pattern in self.sql_injection_patterns:
            if pattern.search(value):
                logger.warning(f"SQL injection attempt detected in {field_name}: {value}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid characters detected in {field_name}"
                )

    def _check_command_injection(self, value: str, field_name: str) -> None:
        """Check for command injection patterns."""
        for pattern in self.command_injection_patterns:
            if pattern.search(value):
                logger.warning(f"Command injection attempt detected in {field_name}: {value}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid characters detected in {field_name}"
                )

    def _check_path_traversal(self, value: str, field_name: str) -> None:
        """Check for path traversal patterns."""
        for pattern in self.path_traversal_patterns:
            if pattern.search(value):
                logger.warning(f"Path traversal attempt detected in {field_name}: {value}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid path detected in {field_name}"
                )

    def validate_json_object(self, obj: Dict[str, Any], max_depth: int = 10) -> Dict[str, Any]:
        """Validate JSON object structure and content."""
        if not isinstance(obj, dict):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Request body must be a JSON object"
            )

        # Check nesting depth to prevent stack overflow
        def check_depth(data, current_depth=0):
            if current_depth > max_depth:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"JSON object exceeds maximum nesting depth of {max_depth}"
                )

            if isinstance(data, dict):
                for key, value in data.items():
                    if isinstance(key, str) and len(key) > 100:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="JSON key exceeds maximum length of 100 characters"
                        )
                    check_depth(value, current_depth + 1)
            elif isinstance(data, list):
                if len(data) > 1000:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="JSON array exceeds maximum length of 1000 items"
                    )
                for item in data:
                    check_depth(item, current_depth + 1)

        check_depth(obj)
        return obj

    def sanitize_log_message(self, message: str) -> str:
        """Sanitize message for safe logging."""
        if not message:
            return ""

        # Remove control characters and null bytes
        message = ''.join(char for char in message if ord(char) >= 32 or char in '\t\n\r')
        message = message.replace('\x00', '')

        # Limit length
        if len(message) > 1000:
            message = message[:1000] + "..."

        return message


# Global validation service instance
validation_service = InputValidationService()
