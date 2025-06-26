"""
Configuration settings for the Kraken Trading System.
Updated to include API credential management for WebSocket authentication.
"""

from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="forbid"
    )

    # Kraken API Configuration
    kraken_api_key: Optional[str] = Field(None, description="Kraken API key")
    kraken_api_secret: Optional[str] = Field(None, description="Kraken API secret")

    # WebSocket Configuration
    kraken_ws_public_url: str = Field(
        "wss://ws.kraken.com",
        description="Kraken public WebSocket URL"
    )
    kraken_ws_private_url: str = Field(
        "wss://ws-auth.kraken.com",
        description="Kraken private WebSocket URL"
    )

    # Trading Configuration
    default_currency_pair: str = Field(
        "XBT/USD",
        description="Default trading pair"
    )
    max_position_size: float = Field(
        1.0,
        ge=0.0,
        description="Maximum position size"
    )
    max_order_value: float = Field(
        10000.0,
        ge=0.0,
        description="Maximum order value in USD"
    )

    # System Configuration
    log_level: str = Field(
        "INFO",
        description="Logging level",
        pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$"
    )
    log_format: str = Field(
        "json",
        description="Log format (json or text)",
        pattern="^(json|text)$"
    )
    environment: str = Field(
        "development",
        description="Environment (development, staging, production)"
    )

    # Risk Management
    enable_risk_checks: bool = Field(
        True,
        description="Enable risk management checks"
    )
    max_daily_loss: float = Field(
        1000.0,
        ge=0.0,
        description="Maximum daily loss limit"
    )
    max_open_orders: int = Field(
        10,
        ge=1,
        description="Maximum number of open orders"
    )

    # Testing Configuration
    use_sandbox: bool = Field(
        True,
        description="Use sandbox/testnet environment"
    )
    sandbox_api_key: Optional[str] = Field(
        None,
        description="Sandbox API key"
    )
    sandbox_api_secret: Optional[str] = Field(
        None,
        description="Sandbox API secret"
    )

    # Connection Settings
    websocket_timeout: float = Field(
        30.0,
        ge=1.0,
        description="WebSocket connection timeout in seconds"
    )
    reconnect_delay: float = Field(
        5.0,
        ge=0.1,
        description="Delay between reconnection attempts in seconds"
    )
    max_reconnect_attempts: int = Field(
        5,
        ge=1,
        description="Maximum number of reconnection attempts"
    )

    # SSL Configuration
    ssl_verify_certificates: bool = Field(
        True,
        description="Whether to verify SSL certificates (disable for development)"
    )
    ssl_check_hostname: bool = Field(
        True,
        description="Whether to check hostname in SSL certificates"
    )

    # WebSocket Token Management
    token_refresh_buffer: int = Field(
        120,
        ge=30,
        le=300,
        description="Seconds before expiry to refresh WebSocket token"
    )
    token_request_timeout: float = Field(
        30.0,
        ge=5.0,
        description="Timeout for WebSocket token requests in seconds"
    )

    def get_api_credentials(self) -> tuple[Optional[str], Optional[str]]:
        """Get the appropriate API credentials based on environment."""
        if self.use_sandbox:
            return self.sandbox_api_key, self.sandbox_api_secret
        return self.kraken_api_key, self.kraken_api_secret

    def get_websocket_urls(self) -> tuple[str, str]:
        """Get the WebSocket URLs for public and private connections."""
        return self.kraken_ws_public_url, self.kraken_ws_private_url

    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"

    def has_api_credentials(self) -> bool:
        """Check if API credentials are configured."""
        api_key, api_secret = self.get_api_credentials()
        return api_key is not None and api_secret is not None

    def validate_api_credentials(self) -> bool:
        """Validate that API credentials are properly formatted."""
        api_key, api_secret = self.get_api_credentials()

        if not api_key or not api_secret:
            return False

        # Basic validation - Kraken API keys are typically 56 chars
        # and secrets are base64 encoded
        if len(api_key) < 50:
            return False

        # Try to decode the secret to verify it's valid base64
        try:
            import base64
            base64.b64decode(api_secret)
            return True
        except Exception:
            return False


# Global settings instance
settings = Settings()
