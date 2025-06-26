"""
Kraken REST API client with authentication support.

This client handles authenticated REST API calls to Kraken,
including the GetWebSocketsToken endpoint needed for WebSocket authentication.
"""

import asyncio
from typing import Any, Dict, Optional, Union
from urllib.parse import urljoin

import httpx

from ...config.settings import settings
from ...utils.exceptions import (
    AuthenticationError,
    ExchangeError,
    InvalidCredentialsError,
    RateLimitError,
    handle_kraken_error,
)
from ...utils.logger import LoggerMixin
from .auth import KrakenAuthenticator, create_authenticator_from_settings


class KrakenRestClient(LoggerMixin):
    """
    Kraken REST API client with authentication support.
    
    Provides methods for making authenticated calls to Kraken's REST API,
    with special focus on endpoints needed for WebSocket authentication.
    """
    
    def __init__(self, authenticator: Optional[KrakenAuthenticator] = None):
        """
        Initialize the REST API client.
        
        Args:
            authenticator: KrakenAuthenticator instance. If None, will try
                          to create one from application settings.
        """
        super().__init__()
        
        # Set up authenticator
        if authenticator is None:
            authenticator = create_authenticator_from_settings(settings)
        
        self.authenticator = authenticator
        
        # API configuration
        self.base_url = "https://api.kraken.com"
        self.timeout = httpx.Timeout(30.0)  # 30 second timeout
        
        # Create HTTP client
        self.client = httpx.AsyncClient(
            timeout=self.timeout,
            verify=True  # Always verify SSL for REST API
        )
        
        self.log_info(
            "Kraken REST client initialized", 
            has_authenticator=self.authenticator is not None,
            base_url=self.base_url
        )
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
        self.log_info("REST client closed")
    
    def _check_authentication(self):
        """Check if client is properly authenticated."""
        if not self.authenticator:
            raise AuthenticationError("No API credentials available. Set API key and secret in settings.")
    
    async def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict[str, Any]] = None,
        authenticated: bool = True
    ) -> Dict[str, Any]:
        """
        Make a request to the Kraken API.
        
        Args:
            method: HTTP method (GET, POST)
            endpoint: API endpoint (e.g., "/0/private/Balance")
            data: Request data (for POST requests)
            authenticated: Whether request requires authentication
            
        Returns:
            Parsed JSON response
            
        Raises:
            AuthenticationError: If authentication is required but not available
            ExchangeError: If API returns an error
            RateLimitError: If rate limit is exceeded
        """
        if authenticated:
            self._check_authentication()
        
        url = urljoin(self.base_url, endpoint)
        headers = {}
        
        if data is None:
            data = {}
        
        try:
            if authenticated:
                # Create authentication headers
                auth_headers = self.authenticator.create_headers(endpoint, data)
                headers.update(auth_headers)
                
                # For POST requests, add nonce to data
                if 'nonce' not in data:
                    data['nonce'] = self.authenticator.generate_nonce()
            
            self.log_info(
                "Making API request",
                method=method,
                endpoint=endpoint,
                authenticated=authenticated,
                data_keys=list(data.keys()) if data else []
            )
            
            # Make the request
            if method.upper() == "GET":
                response = await self.client.get(url, headers=headers, params=data)
            else:  # POST
                response = await self.client.post(url, headers=headers, data=data)
            
            # Check HTTP status
            response.raise_for_status()
            
            # Parse JSON response
            json_response = response.json()
            
            # Check for Kraken API errors
            if "error" in json_response and json_response["error"]:
                error_messages = json_response["error"]
                if isinstance(error_messages, list):
                    error_message = "; ".join(error_messages)
                else:
                    error_message = str(error_messages)
                
                self.log_error("Kraken API error", error_message=error_message)
                
                # Handle specific error types
                if "EAPI:Rate limit exceeded" in error_message:
                    raise RateLimitError(error_message)
                elif any(auth_error in error_message for auth_error in 
                        ["EAPI:Invalid key", "EAPI:Invalid signature", "EAPI:Permission denied"]):
                    raise AuthenticationError(error_message)
                else:
                    raise ExchangeError(error_message, details=json_response)
            
            self.log_info(
                "API request successful",
                endpoint=endpoint,
                has_result=bool(json_response.get("result"))
            )
            
            return json_response
            
        except httpx.HTTPStatusError as e:
            self.log_error("HTTP error in API request", status_code=e.response.status_code, error=e)
            
            if e.response.status_code == 429:
                raise RateLimitError("Rate limit exceeded")
            elif e.response.status_code in [401, 403]:
                raise AuthenticationError(f"Authentication failed: {e.response.status_code}")
            else:
                raise ExchangeError(f"HTTP {e.response.status_code}: {e}")
                
        except httpx.RequestError as e:
            self.log_error("Request error in API call", error=e)
            raise ExchangeError(f"Request failed: {e}")
        
        except Exception as e:
            self.log_error("Unexpected error in API call", error=e)
            raise ExchangeError(f"Unexpected error: {e}")
    
    # Public API methods (no authentication required)
    
    async def get_server_time(self) -> Dict[str, Any]:
        """
        Get server time from Kraken.
        
        Returns:
            Dictionary with server time information
        """
        return await self._make_request("GET", "/0/public/Time", authenticated=False)
    
    async def get_system_status(self) -> Dict[str, Any]:
        """
        Get system status from Kraken.
        
        Returns:
            Dictionary with system status information
        """
        return await self._make_request("GET", "/0/public/SystemStatus", authenticated=False)
    
    # Private API methods (authentication required)
    
    async def get_account_balance(self) -> Dict[str, Any]:
        """
        Get account balance.
        
        Returns:
            Dictionary with account balances
            
        Raises:
            AuthenticationError: If not authenticated
        """
        return await self._make_request("POST", "/0/private/Balance")
    
    async def get_trade_balance(self, asset: str = "ZUSD") -> Dict[str, Any]:
        """
        Get trade balance information.
        
        Args:
            asset: Base asset for balance calculation (default: ZUSD)
            
        Returns:
            Dictionary with trade balance information
        """
        data = {"asset": asset}
        return await self._make_request("POST", "/0/private/TradeBalance", data)
    
    async def get_websockets_token(self) -> str:
        """
        Get WebSocket authentication token.
        
        This is the key method for WebSocket authentication. The token
        returned can be used to authenticate WebSocket connections.
        
        Returns:
            WebSocket authentication token string
            
        Raises:
            AuthenticationError: If authentication fails
            ExchangeError: If API call fails
        """
        response = await self._make_request("POST", "/0/private/GetWebSocketsToken")
        
        if "result" not in response:
            raise ExchangeError("No result in GetWebSocketsToken response")
        
        result = response["result"]
        if "token" not in result:
            raise ExchangeError("No token in GetWebSocketsToken result")
        
        token = result["token"]
        
        self.log_info(
            "WebSocket token obtained",
            token_length=len(token),
            expires_in_minutes=15  # Kraken tokens expire in 15 minutes
        )
        
        return token
    
    # Convenience methods
    
    async def test_authentication(self) -> bool:
        """
        Test if authentication is working by making a simple API call.
        
        Returns:
            True if authentication successful, False otherwise
        """
        try:
            await self.get_account_balance()
            self.log_info("Authentication test successful")
            return True
        except AuthenticationError as e:
            self.log_error("Authentication test failed", error=e)
            return False
        except Exception as e:
            self.log_error("Authentication test error", error=e)
            return False
    
    def is_authenticated(self) -> bool:
        """
        Check if client has authentication credentials.
        
        Returns:
            True if credentials are available, False otherwise
        """
        return self.authenticator is not None
    
    async def validate_connection(self) -> Dict[str, Any]:
        """
        Validate connection by testing both public and private endpoints.
        
        Returns:
            Dictionary with validation results
        """
        results = {
            "public_api": False,
            "private_api": False,
            "authentication": False,
            "errors": []
        }
        
        # Test public API
        try:
            await self.get_system_status()
            results["public_api"] = True
        except Exception as e:
            results["errors"].append(f"Public API error: {e}")
        
        # Test private API if authenticated
        if self.is_authenticated():
            try:
                await self.get_account_balance()
                results["private_api"] = True
                results["authentication"] = True
            except AuthenticationError as e:
                results["errors"].append(f"Authentication error: {e}")
            except Exception as e:
                results["errors"].append(f"Private API error: {e}")
        else:
            results["errors"].append("No authentication credentials available")
        
        self.log_info("Connection validation completed", **results)
        return results


# Convenience function for creating client
async def create_rest_client() -> KrakenRestClient:
    """
    Create a KrakenRestClient with settings from configuration.
    
    Returns:
        Configured KrakenRestClient instance
    """
    return KrakenRestClient()


# Example usage and testing
async def test_rest_client():
    """Test the REST client functionality."""
    async with KrakenRestClient() as client:
        print("Testing Kraken REST client...")
        
        # Test public API
        try:
            time_response = await client.get_server_time()
            print(f"✅ Server time: {time_response}")
        except Exception as e:
            print(f"❌ Server time error: {e}")
        
        # Test private API (if authenticated)
        if client.is_authenticated():
            try:
                balance = await client.get_account_balance()
                print(f"✅ Account balance retrieved")
            except Exception as e:
                print(f"❌ Balance error: {e}")
            
            try:
                token = await client.get_websockets_token()
                print(f"✅ WebSocket token: {token[:20]}...")
            except Exception as e:
                print(f"❌ Token error: {e}")
        else:
            print("⚠️ No authentication - skipping private API tests")


if __name__ == "__main__":
    asyncio.run(test_rest_client())