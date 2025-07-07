"""
Configuration settings for the Balance Tracking API
"""

import os
from pathlib import Path


class Settings:
    """Application settings and configuration"""
    
    # Database configuration
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///balance_tracker.db")
    DATABASE_TYPE: str = "sqlite"
    
    # Security settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", "30"))
    
    # API settings
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "Balance Tracking System"
    VERSION: str = "1.0.0"
    
    # Rate limiting
    RATE_LIMIT_REQUESTS: int = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
    RATE_LIMIT_WINDOW: int = int(os.getenv("RATE_LIMIT_WINDOW", "60"))
    
    # Pagination defaults
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100
    
    # Transaction settings
    MIN_TRANSACTION_AMOUNT: float = 0.00000001
    MAX_TRANSACTION_AMOUNT: float = 999999999999.99
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"

# Global settings instance
settings = Settings()
