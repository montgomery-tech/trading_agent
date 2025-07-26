from pydantic import Field
#!/usr/bin/env python3
#api/config.py
"""
Enhanced Configuration settings for the Balance Tracking API
Production-ready configuration with security, validation, and environment management
"""

import os
import sys
import secrets
from pathlib import Path
from typing import Optional, List, Union
from enum import Enum
import logging

# Try to import python-decouple for enhanced .env support
try:
    from decouple import config, Csv
    HAS_DECOUPLE = True
except ImportError:
    HAS_DECOUPLE = False
    # Fallback to os.getenv
    def config(key: str, default=None, cast=None):
        value = os.getenv(key, default)
        if cast and value is not None:
            try:
                return cast(value)
            except (ValueError, TypeError):
                return default
        return value

    def Csv(cast=str):
        def csv_cast(value):
            if isinstance(value, str):
                return [cast(item.strip()) for item in value.split(',') if item.strip()]
            return value
        return csv_cast


class Environment(str, Enum):
    """Environment types"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class DatabaseType(str, Enum):
    """Supported database types"""
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"


class Settings:
    """
    Enhanced application settings and configuration with validation

    Features:
    - Environment-specific configurations
    - Security validation
    - Required environment variable checking
    - Production-ready defaults
    """

    def __init__(self):
        """Initialize settings with validation"""
        self._load_settings()
        self._validate_settings()

    def _load_settings(self):
        """Load all configuration settings"""


        # Load Redis settings from environment
        self.RATE_LIMIT_REDIS_URL = os.getenv('RATE_LIMIT_REDIS_URL', 'redis://localhost:6379/1')
        self.RATE_LIMIT_FALLBACK_TO_MEMORY = os.getenv('RATE_LIMIT_FALLBACK_TO_MEMORY', 'true').lower() == 'true'
        self.RATE_LIMIT_AUTH_REQUESTS = int(os.getenv('RATE_LIMIT_AUTH_REQUESTS', '10'))
        self.RATE_LIMIT_TRADING_REQUESTS = int(os.getenv('RATE_LIMIT_TRADING_REQUESTS', '100'))
        self.RATE_LIMIT_INFO_REQUESTS = int(os.getenv('RATE_LIMIT_INFO_REQUESTS', '200'))
        self.RATE_LIMIT_ADMIN_REQUESTS = int(os.getenv('RATE_LIMIT_ADMIN_REQUESTS', '5'))
        self.RATE_LIMIT_REQUESTS_PER_MINUTE = int(os.getenv('RATE_LIMIT_REQUESTS_PER_MINUTE', '60'))
        # =================================================================
        # ENVIRONMENT CONFIGURATION
        # =================================================================
        self.ENVIRONMENT: Environment = Environment(
            config("ENVIRONMENT", default="development").lower()
        )
        self.DEBUG: bool = config("DEBUG", default=self.ENVIRONMENT == Environment.DEVELOPMENT, cast=bool)

        # =================================================================
        # SECURITY SETTINGS - CRITICAL FOR PRODUCTION
        # =================================================================
        self.SECRET_KEY: str = config("SECRET_KEY", default="")
        self.JWT_ALGORITHM: str = config("JWT_ALGORITHM", default="HS256")
        self.JWT_EXPIRE_MINUTES: int = config("JWT_EXPIRE_MINUTES", default=30, cast=int)
        self.JWT_REFRESH_EXPIRE_DAYS: int = config("JWT_REFRESH_EXPIRE_DAYS", default=7, cast=int)

        # Password requirements
        self.PASSWORD_MIN_LENGTH: int = config("PASSWORD_MIN_LENGTH", default=8, cast=int)
        self.PASSWORD_REQUIRE_UPPERCASE: bool = config("PASSWORD_REQUIRE_UPPERCASE", default=True, cast=bool)
        self.PASSWORD_REQUIRE_LOWERCASE: bool = config("PASSWORD_REQUIRE_LOWERCASE", default=True, cast=bool)
        self.PASSWORD_REQUIRE_NUMBERS: bool = config("PASSWORD_REQUIRE_NUMBERS", default=True, cast=bool)
        self.PASSWORD_REQUIRE_SPECIAL: bool = config("PASSWORD_REQUIRE_SPECIAL", default=True, cast=bool)

        # =================================================================
        # DATABASE CONFIGURATION
        # =================================================================
        self.DATABASE_URL: str = config("DATABASE_URL", default="sqlite:///balance_tracker.db")
        self.DATABASE_SSL_MODE: str = config("DATABASE_SSL_MODE", default="prefer")
        self.DATABASE_POOL_SIZE: int = config("DATABASE_POOL_SIZE", default=20, cast=int)
        self.DATABASE_MAX_OVERFLOW: int = config("DATABASE_MAX_OVERFLOW", default=30, cast=int)
        self.DATABASE_POOL_TIMEOUT: int = config("DATABASE_POOL_TIMEOUT", default=30, cast=int)

        # Determine database type from URL
        if "postgresql://" in self.DATABASE_URL or "postgres://" in self.DATABASE_URL:
            self.DATABASE_TYPE = DatabaseType.POSTGRESQL
        elif "mysql://" in self.DATABASE_URL:
            self.DATABASE_TYPE = DatabaseType.MYSQL
        else:
            self.DATABASE_TYPE = DatabaseType.SQLITE

        # =================================================================
        # API CONFIGURATION
        # =================================================================
        self.API_V1_PREFIX: str = config("API_V1_PREFIX", default="/api/v1")
        self.PROJECT_NAME: str = config("PROJECT_NAME", default="Balance Tracking System")
        self.VERSION: str = config("VERSION", default="1.0.0")

        # CORS settings
        self.CORS_ORIGINS: List[str] = config(
            "CORS_ORIGINS",
            default="http://localhost:3000,http://localhost:8080" if self.DEBUG else "",
            cast=Csv()
        )
        self.CORS_ALLOW_CREDENTIALS: bool = config("CORS_ALLOW_CREDENTIALS", default=True, cast=bool)

        # =================================================================
        # RATE LIMITING
        # =================================================================
        self.RATE_LIMIT_ENABLED: bool = config("RATE_LIMIT_ENABLED", default=True, cast=bool)

        # Redis Rate Limiting Settings
        RATE_LIMIT_REDIS_URL: Optional[str] = Field(
            default="redis://localhost:6379/1",
            env="RATE_LIMIT_REDIS_URL"
        )
        RATE_LIMIT_FALLBACK_TO_MEMORY: bool = Field(
            default=True,
            env="RATE_LIMIT_FALLBACK_TO_MEMORY"
        )
        RATE_LIMIT_AUTH_REQUESTS: int = Field(
            default=10,
            env="RATE_LIMIT_AUTH_REQUESTS"
        )
        RATE_LIMIT_TRADING_REQUESTS: int = Field(
            default=100,
            env="RATE_LIMIT_TRADING_REQUESTS"
        )
        RATE_LIMIT_INFO_REQUESTS: int = Field(
            default=200,
            env="RATE_LIMIT_INFO_REQUESTS"
        )
        RATE_LIMIT_ADMIN_REQUESTS: int = Field(
            default=5,
            env="RATE_LIMIT_ADMIN_REQUESTS"
        )
        RATE_LIMIT_REQUESTS_PER_MINUTE: int = Field(
            default=60,
            env="RATE_LIMIT_REQUESTS_PER_MINUTE"
        )
        self.RATE_LIMIT_REQUESTS_PER_MINUTE: int = config("RATE_LIMIT_REQUESTS_PER_MINUTE", default=60, cast=int)
        self.RATE_LIMIT_BURST: int = config("RATE_LIMIT_BURST", default=10, cast=int)

        # Different limits for different endpoint types
        self.RATE_LIMIT_AUTH_REQUESTS: int = config("RATE_LIMIT_AUTH_REQUESTS", default=5, cast=int)  # Per minute
        self.RATE_LIMIT_TRADING_REQUESTS: int = config("RATE_LIMIT_TRADING_REQUESTS", default=30, cast=int)  # Per minute
        self.RATE_LIMIT_ADMIN_REQUESTS: int = config("RATE_LIMIT_ADMIN_REQUESTS", default=100, cast=int)  # Per minute

        # =================================================================
        # EMAIL CONFIGURATION (Amazon SES)
        # =================================================================
        self.EMAIL_ENABLED: bool = config("EMAIL_ENABLED", default=True, cast=bool)
        self.AWS_ACCESS_KEY_ID: str = config("AWS_ACCESS_KEY_ID", default="")
        self.AWS_SECRET_ACCESS_KEY: str = config("AWS_SECRET_ACCESS_KEY", default="")
        self.AWS_REGION: str = config("AWS_REGION", default="us-east-1")
        self.SES_FROM_EMAIL: str = config("SES_FROM_EMAIL", default="noreply@yourdomain.com")
        self.SES_FROM_NAME: str = config("SES_FROM_NAME", default="Trading System")

        # Email verification settings
        self.EMAIL_VERIFICATION_EXPIRE_HOURS: int = config("EMAIL_VERIFICATION_EXPIRE_HOURS", default=24, cast=int)
        self.PASSWORD_RESET_EXPIRE_HOURS: int = config("PASSWORD_RESET_EXPIRE_HOURS", default=2, cast=int)

        # =================================================================
        # SECURITY HEADERS AND FEATURES
        # =================================================================
        self.SECURITY_HEADERS_ENABLED: bool = config("SECURITY_HEADERS_ENABLED", default=True, cast=bool)
        self.HTTPS_ONLY: bool = config("HTTPS_ONLY", default=self.ENVIRONMENT == Environment.PRODUCTION, cast=bool)
        self.HSTS_MAX_AGE: int = config("HSTS_MAX_AGE", default=31536000, cast=int)  # 1 year

        # =================================================================
        # PAGINATION AND LIMITS
        # =================================================================
        self.DEFAULT_PAGE_SIZE: int = config("DEFAULT_PAGE_SIZE", default=20, cast=int)
        self.MAX_PAGE_SIZE: int = config("MAX_PAGE_SIZE", default=100, cast=int)

        # =================================================================
        # TRANSACTION SETTINGS
        # =================================================================
        self.MIN_TRANSACTION_AMOUNT: float = config("MIN_TRANSACTION_AMOUNT", default=0.00000001, cast=float)
        self.MAX_TRANSACTION_AMOUNT: float = config("MAX_TRANSACTION_AMOUNT", default=999999999999.99, cast=float)
        self.TRANSACTION_FEE_RATE: float = config("TRANSACTION_FEE_RATE", default=0.0025, cast=float)  # 0.25%

        # =================================================================
        # LOGGING
        # =================================================================
        self.LOG_LEVEL: str = config("LOG_LEVEL", default="INFO")
        self.LOG_FORMAT: str = config("LOG_FORMAT", default="detailed")
        self.LOG_FILE_ENABLED: bool = config("LOG_FILE_ENABLED", default=self.ENVIRONMENT == Environment.PRODUCTION, cast=bool)
        self.LOG_FILE_PATH: str = config("LOG_FILE_PATH", default="logs/app.log")

        # =================================================================
        # MONITORING AND HEALTH CHECKS
        # =================================================================
        self.HEALTH_CHECK_ENABLED: bool = config("HEALTH_CHECK_ENABLED", default=True, cast=bool)
        self.METRICS_ENABLED: bool = config("METRICS_ENABLED", default=True, cast=bool)

        # =================================================================
        # TESTING CONFIGURATION
        # =================================================================
        if self.ENVIRONMENT == Environment.TESTING:
            self.DATABASE_URL = config("TEST_DATABASE_URL", default="sqlite:///test_balance_tracker.db")
            self.EMAIL_ENABLED = False
            self.RATE_LIMIT_ENABLED = False

    def _validate_settings(self):
        """Validate critical settings, especially for production"""
        errors = []
        warnings = []

        # Critical security validation
        if not self.SECRET_KEY:
            errors.append("SECRET_KEY is required and cannot be empty")
        elif self.SECRET_KEY == "your-secret-key-change-in-production":
            errors.append("SECRET_KEY must be changed from default value for production")
        elif len(self.SECRET_KEY) < 32:
            errors.append("SECRET_KEY must be at least 32 characters long")

        # Production-specific validations
        if self.ENVIRONMENT == Environment.PRODUCTION:
            if self.DEBUG:
                warnings.append("DEBUG should be False in production")

            if not self.DATABASE_URL.startswith(("postgresql://", "postgres://")):
                warnings.append("PostgreSQL is recommended for production instead of SQLite")

            if not self.CORS_ORIGINS:
                warnings.append("CORS_ORIGINS should be configured for production")
            elif "*" in self.CORS_ORIGINS:
                errors.append("CORS_ORIGINS should not contain '*' in production")

            if not self.HTTPS_ONLY:
                warnings.append("HTTPS_ONLY should be True in production")

            if self.EMAIL_ENABLED and not self.AWS_ACCESS_KEY_ID:
                errors.append("AWS_ACCESS_KEY_ID required when EMAIL_ENABLED=True")

            if self.EMAIL_ENABLED and not self.AWS_SECRET_ACCESS_KEY:
                errors.append("AWS_SECRET_ACCESS_KEY required when EMAIL_ENABLED=True")

        # Database validation
        if self.DATABASE_TYPE == DatabaseType.POSTGRESQL:
            if "localhost" in self.DATABASE_URL and self.ENVIRONMENT == Environment.PRODUCTION:
                warnings.append("Using localhost for PostgreSQL in production - consider managed database")

        # Rate limiting validation
        if self.RATE_LIMIT_ENABLED:
            if self.RATE_LIMIT_REQUESTS_PER_MINUTE <= 0:
                errors.append("RATE_LIMIT_REQUESTS_PER_MINUTE must be positive")

        # JWT validation
        if self.JWT_EXPIRE_MINUTES <= 0:
            errors.append("JWT_EXPIRE_MINUTES must be positive")
        if self.JWT_REFRESH_EXPIRE_DAYS <= 0:
            errors.append("JWT_REFRESH_EXPIRE_DAYS must be positive")

        # Log validation results
        if errors:
            error_msg = "Configuration validation failed:\n" + "\n".join(f"  ❌ {error}" for error in errors)
            print(error_msg, file=sys.stderr)
            if self.ENVIRONMENT == Environment.PRODUCTION:
                sys.exit(1)  # Fail fast in production

        if warnings:
            warning_msg = "Configuration warnings:\n" + "\n".join(f"  ⚠️  {warning}" for warning in warnings)
            print(warning_msg, file=sys.stderr)

    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.ENVIRONMENT == Environment.PRODUCTION

    def is_development(self) -> bool:
        """Check if running in development environment"""
        return self.ENVIRONMENT == Environment.DEVELOPMENT

    def is_testing(self) -> bool:
        """Check if running in testing environment"""
        return self.ENVIRONMENT == Environment.TESTING

    def get_database_url(self, async_url: bool = False) -> str:
        """Get database URL, optionally with async driver"""
        if async_url and self.DATABASE_TYPE == DatabaseType.POSTGRESQL:
            return self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
        return self.DATABASE_URL

    def generate_secret_key(self) -> str:
        """Generate a new cryptographically secure secret key"""
        return secrets.token_hex(32)  # 256 bits

    def get_cors_config(self) -> dict:
        """Get CORS configuration for FastAPI"""
        return {
            "allow_origins": self.CORS_ORIGINS,
            "allow_credentials": self.CORS_ALLOW_CREDENTIALS,
            "allow_methods": ["GET", "POST", "PUT", "DELETE", "PATCH"],
            "allow_headers": ["*"],
        }

    def get_security_headers(self) -> dict:
        """Get security headers configuration"""
        if not self.SECURITY_HEADERS_ENABLED:
            return {}

        headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin",
        }

        if self.HTTPS_ONLY:
            headers["Strict-Transport-Security"] = f"max-age={self.HSTS_MAX_AGE}; includeSubDomains"

        return headers

    def __repr__(self) -> str:
        """String representation of settings (without sensitive data)"""
        safe_attrs = {
            "ENVIRONMENT": self.ENVIRONMENT,
            "DEBUG": self.DEBUG,
            "DATABASE_TYPE": self.DATABASE_TYPE,
            "PROJECT_NAME": self.PROJECT_NAME,
            "VERSION": self.VERSION,
            "RATE_LIMIT_ENABLED": self.RATE_LIMIT_ENABLED,
            "EMAIL_ENABLED": self.EMAIL_ENABLED,
        }
        return f"Settings({safe_attrs})"


# Global settings instance
settings = Settings()

# Configure logging based on settings
def configure_logging():
    """Configure logging based on settings"""
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    if settings.LOG_FORMAT == "json":
        # JSON logging for production
        format_str = '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "name": "%(name)s", "message": "%(message)s"}'
    elif settings.LOG_FORMAT == "detailed":
        # Detailed logging for development
        format_str = "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
    else:
        # Simple logging
        format_str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format=format_str,
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Create logs directory if file logging is enabled
    if settings.LOG_FILE_ENABLED:
        log_path = Path(settings.LOG_FILE_PATH)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # Add file handler
        file_handler = logging.FileHandler(log_path)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(logging.Formatter(format_str, datefmt="%Y-%m-%d %H:%M:%S"))
        logging.getLogger().addHandler(file_handler)

# Initialize logging
configure_logging()

# Create a logger for this module
logger = logging.getLogger(__name__)
logger.info(f"Configuration loaded: {settings}")
