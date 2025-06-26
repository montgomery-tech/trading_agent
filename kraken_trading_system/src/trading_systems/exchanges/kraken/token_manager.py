"""
Kraken WebSocket Token Manager for handling authentication tokens.

This module handles:
1. Retrieving WebSocket authentication tokens from Kraken's REST API
2. Token lifecycle management (15-minute validity)
3. Automatic token refresh when needed
4. Secure credential handling
"""

import asyncio
import base64
import hashlib
import hmac
import time
from typing import Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta

import httpx

from ...config.settings import settings
from ...utils.exceptions import AuthenticationError, InvalidCredentialsError
from ...utils.logger import LoggerMixin


@dataclass
class WebSocketToken:
    """WebSocket authentication token with metadata."""
    token: str
    created_at: datetime
    expires_at: datetime
    is_valid: bool = True
    
    @property
    def is_expired(self) -> bool:
        """Check if token has expired (15-minute validity)."""
        return datetime.now() >= self.expires_at
    
    @property
    def time_until_expiry(self) -> timedelta:
        """Time remaining until token expires."""
        return self.expires_at - datetime.now()
    
    @property
    def should_refresh(self) -> bool:
        """Check if token should be refreshed (within 2 minutes of expiry)."""
        return self.time_until_expiry.total_seconds() < 120  # Refresh 2 minutes before expiry


class KrakenTokenManager(LoggerMixin):
    """
    Manages WebSocket authentication tokens for Kraken API.
    
    Handles token retrieval, caching, and automatic refresh to ensure
    continuous WebSocket authentication capability.
    """
    
    def __init__(self):
        super().__init__()
        self._current_token: Optional[WebSocketToken] = None
        self._token_lock = asyncio.Lock()
        self._http_client: Optional[httpx.AsyncClient] = None
        
        # Kraken REST API configuration
        self.rest_api_base = "https://api.kraken.com"
        self.token_endpoint = "/0/private/GetWebSocketsToken"
        
        self.log_info("Token manager initialized")
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_http_client()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self._close_http_client()
    
    async def _ensure_http_client(self):
        """Ensure HTTP client is initialized."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=30.0)
    
    async def _close_http_client(self):
        """Close HTTP client if initialized."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
    
    async def get_websocket_token(self, force_refresh: bool = False) -> str:
        """
        Get a valid WebSocket authentication token.
        
        Args:
            force_refresh: Force token refresh even if current token is valid
            
        Returns:
            Valid WebSocket authentication token
            
        Raises:
            AuthenticationError: If token retrieval fails
            InvalidCredentialsError: If API credentials are invalid
        """
        async with self._token_lock:
            # Check if we need a new token
            if (self._current_token is None or 
                self._current_token.is_expired or 
                self._current_token.should_refresh or 
                force_refresh):
                
                self.log_info(
                    "Requesting new WebSocket token",
                    force_refresh=force_refresh,
                    has_current_token=self._current_token is not None,
                    current_expired=self._current_token.is_expired if self._current_token else None
                )
                
                await self._refresh_token()
            
            if self._current_token is None:
                raise AuthenticationError("Failed to obtain WebSocket token")
            
            return self._current_token.token
    
    async def _refresh_token(self):
        """Refresh the WebSocket authentication token."""
        try:
            # Get API credentials
            api_key, api_secret = settings.get_api_credentials()
            
            if not api_key or not api_secret:
                raise InvalidCredentialsError(
                    "Kraken API credentials not configured. "
                    "Please set KRAKEN_API_KEY and KRAKEN_API_SECRET environment variables."
                )
            
            # Prepare API request
            nonce = str(int(time.time() * 1000))
            post_data = f"nonce={nonce}"
            
            # Create authentication signature
            signature = self._create_signature(api_secret, self.token_endpoint, nonce, post_data)
            
            # Prepare headers
            headers = {
                "API-Key": api_key,
                "API-Sign": signature,
                "Content-Type": "application/x-www-form-urlencoded"
            }
            
            # Ensure HTTP client is available
            await self._ensure_http_client()
            
            # Make REST API request
            url = f"{self.rest_api_base}{self.token_endpoint}"
            
            self.log_info("Requesting WebSocket token from Kraken API", url=url)
            
            response = await self._http_client.post(
                url,
                headers=headers,
                data=post_data
            )
            
            # Handle response
            if response.status_code != 200:
                raise AuthenticationError(
                    f"Token request failed with status {response.status_code}: {response.text}"
                )
            
            response_data = response.json()
            
            # Check for API errors
            if response_data.get("error"):
                error_messages = response_data["error"]
                if isinstance(error_messages, list):
                    error_text = "; ".join(error_messages)
                else:
                    error_text = str(error_messages)
                
                # Handle specific error types
                if "Invalid key" in error_text or "Permission denied" in error_text:
                    raise InvalidCredentialsError(f"Invalid API credentials: {error_text}")
                else:
                    raise AuthenticationError(f"API error: {error_text}")
            
            # Extract token from response
            token_data = response_data.get("result")
            if not token_data or "token" not in token_data:
                raise AuthenticationError("Invalid token response format")
            
            token_string = token_data["token"]
            
            # Create token object with metadata
            now = datetime.now()
            self._current_token = WebSocketToken(
                token=token_string,
                created_at=now,
                expires_at=now + timedelta(minutes=15)  # 15-minute validity
            )
            
            self.log_info(
                "WebSocket token obtained successfully",
                token_length=len(token_string),
                expires_at=self._current_token.expires_at.isoformat()
            )
            
        except (httpx.RequestError, httpx.HTTPStatusError) as e:
            self.log_error("HTTP error during token request", error=e)
            raise AuthenticationError(f"Network error during token request: {e}")
        
        except Exception as e:
            self.log_error("Unexpected error during token refresh", error=e)
            raise AuthenticationError(f"Token refresh failed: {e}")
    
    def _create_signature(self, api_secret: str, api_path: str, nonce: str, post_data: str) -> str:
        """
        Create HMAC-SHA512 signature for Kraken API authentication.
        
        Args:
            api_secret: Base64-encoded API secret key
            api_path: API endpoint path
            nonce: Unique nonce value
            post_data: POST data string
            
        Returns:
            Base64-encoded signature string
        """
        try:
            # Decode the API secret
            api_secret_decoded = base64.b64decode(api_secret)
            
            # Create SHA256 hash of nonce and post data
            sha256_hash = hashlib.sha256((nonce + post_data).encode('utf-8'))
            
            # Create HMAC-SHA512 signature
            hmac_signature = hmac.new(
                api_secret_decoded,
                api_path.encode('utf-8') + sha256_hash.digest(),
                hashlib.sha512
            )
            
            # Return base64-encoded signature
            return base64.b64encode(hmac_signature.digest()).decode('utf-8')
            
        except Exception as e:
            self.log_error("Error creating API signature", error=e)
            raise AuthenticationError(f"Failed to create API signature: {e}")
    
    async def invalidate_token(self):
        """Invalidate the current token (forces refresh on next request)."""
        async with self._token_lock:
            if self._current_token:
                self._current_token.is_valid = False
                self.log_info("WebSocket token invalidated")
    
    def get_token_status(self) -> dict:
        """
        Get current token status information.
        
        Returns:
            Dictionary with token status details
        """
        if self._current_token is None:
            return {
                "has_token": False,
                "is_expired": None,
                "time_until_expiry": None,
                "should_refresh": None
            }
        
        return {
            "has_token": True,
            "is_expired": self._current_token.is_expired,
            "time_until_expiry": self._current_token.time_until_expiry.total_seconds(),
            "should_refresh": self._current_token.should_refresh,
            "created_at": self._current_token.created_at.isoformat(),
            "expires_at": self._current_token.expires_at.isoformat(),
            "is_valid": self._current_token.is_valid
        }


# Global token manager instance for shared use
_token_manager: Optional[KrakenTokenManager] = None


async def get_token_manager() -> KrakenTokenManager:
    """
    Get the global token manager instance.
    
    Returns:
        Initialized KrakenTokenManager instance
    """
    global _token_manager
    
    if _token_manager is None:
        _token_manager = KrakenTokenManager()
        await _token_manager._ensure_http_client()
    
    return _token_manager


async def cleanup_token_manager():
    """Clean up the global token manager."""
    global _token_manager
    
    if _token_manager:
        await _token_manager._close_http_client()
        _token_manager = None
