"""
Enhanced Kraken REST API client with order placement functionality.

This enhancement adds comprehensive order operations to the existing REST client,
supporting market orders, limit orders, error handling, and retry logic.

Task 3.2.A: Extend REST Client for Order Operations
"""

import asyncio
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urljoin
from decimal import Decimal
from datetime import datetime

import httpx

from ...config.settings import settings
from ...utils.exceptions import (
    AuthenticationError,
    ExchangeError,
    InvalidCredentialsError,
    RateLimitError,
    OrderError,
    handle_kraken_error,
)
from ...utils.logger import LoggerMixin
from .auth import KrakenAuthenticator, create_authenticator_from_settings


class EnhancedKrakenRestClient(LoggerMixin):
    """
    Enhanced Kraken REST API client with comprehensive order operations.

    Extends the basic REST client to support:
    - Market and limit order placement
    - Order cancellation and modification
    - Order status queries
    - Comprehensive error handling and retry logic
    - Parameter validation and sanitization
    """

    def __init__(self, authenticator: Optional[KrakenAuthenticator] = None, max_retries: int = 3):
        """
        Initialize the enhanced REST API client.

        Args:
            authenticator: KrakenAuthenticator instance. If None, creates from settings.
            max_retries: Maximum number of retries for failed requests
        """
        super().__init__()

        # Set up authenticator
        if authenticator is None:
            authenticator = create_authenticator_from_settings(settings)

        self.authenticator = authenticator
        self.max_retries = max_retries

        # API configuration
        self.base_url = "https://api.kraken.com"
        self.timeout = httpx.Timeout(30.0)

        # Create HTTP client
        self.client = httpx.AsyncClient(
            timeout=self.timeout,
            verify=True
        )

        # Rate limiting
        self.rate_limit_delay = 1.0  # seconds between requests
        self.last_request_time = 0.0

        self.log_info(
            "Enhanced Kraken REST client initialized",
            has_authenticator=self.authenticator is not None,
            base_url=self.base_url,
            max_retries=self.max_retries
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
        self.log_info("Enhanced REST client closed")

    def _check_authentication(self):
        """Check if client is properly authenticated."""
        if not self.authenticator:
            raise AuthenticationError("No API credentials available. Set API key and secret in settings.")

    async def _apply_rate_limiting(self):
        """Apply rate limiting to prevent API abuse."""
        import time
        current_time = time.time()
        time_since_last = current_time - self.last_request_time

        if time_since_last < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - time_since_last
            await asyncio.sleep(sleep_time)

        self.last_request_time = time.time()

    async def _make_request_with_retry(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        authenticated: bool = True,
        retry_count: int = 0
    ) -> Dict[str, Any]:
        """
        Make a request with retry logic for handling temporary failures.

        Args:
            method: HTTP method (GET, POST)
            endpoint: API endpoint
            data: Request data
            authenticated: Whether request requires authentication
            retry_count: Current retry attempt

        Returns:
            Parsed JSON response
        """
        try:
            # Apply rate limiting
            await self._apply_rate_limiting()

            # Make the request
            return await self._make_request(method, endpoint, data, authenticated)

        except RateLimitError as e:
            if retry_count < self.max_retries:
                # Exponential backoff for rate limit errors
                delay = (2 ** retry_count) * 2  # 2, 4, 8 seconds
                self.log_warning(
                    f"Rate limit exceeded, retrying in {delay}s",
                    retry_count=retry_count + 1,
                    max_retries=self.max_retries
                )
                await asyncio.sleep(delay)
                return await self._make_request_with_retry(method, endpoint, data, authenticated, retry_count + 1)
            else:
                self.log_error("Max retries exceeded for rate limit")
                raise

        except (httpx.RequestError, httpx.ConnectError) as e:
            if retry_count < self.max_retries:
                # Network errors with linear backoff
                delay = (retry_count + 1) * 1  # 1, 2, 3 seconds
                self.log_warning(
                    f"Network error, retrying in {delay}s",
                    error=str(e),
                    retry_count=retry_count + 1,
                    max_retries=self.max_retries
                )
                await asyncio.sleep(delay)
                return await self._make_request_with_retry(method, endpoint, data, authenticated, retry_count + 1)
            else:
                self.log_error("Max retries exceeded for network error", error=e)
                raise ExchangeError(f"Network error after {self.max_retries} retries: {e}")

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
            endpoint: API endpoint
            data: Request data
            authenticated: Whether request requires authentication

        Returns:
            Parsed JSON response
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

                # Add nonce for POST requests
                if 'nonce' not in data:
                    data['nonce'] = self.authenticator.generate_nonce()

            self.log_info(
                "Making API request",
                method=method,
                endpoint=endpoint,
                authenticated=authenticated
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

            return json_response

        except httpx.HTTPStatusError as e:
            self.log_error("HTTP error in API request", status_code=e.response.status_code)

            if e.response.status_code == 429:
                raise RateLimitError("Rate limit exceeded")
            elif e.response.status_code in [401, 403]:
                raise AuthenticationError(f"Authentication failed: {e.response.status_code}")
            else:
                raise ExchangeError(f"HTTP {e.response.status_code}: {e}")

        except httpx.RequestError as e:
            self.log_error("Request error in API call", error=e)
            raise ExchangeError(f"Request failed: {e}")

    # ORDER PLACEMENT METHODS

    def _validate_order_parameters(self, pair: str, side: str, order_type: str,
                                 volume: Union[str, Decimal], price: Optional[Union[str, Decimal]] = None) -> Dict[str, str]:
        """
        Validate and sanitize order parameters.

        Args:
            pair: Trading pair (e.g., "XBTUSD")
            side: Order side ("buy" or "sell")
            order_type: Order type ("market" or "limit")
            volume: Order volume
            price: Order price (required for limit orders)

        Returns:
            Dictionary of validated parameters

        Raises:
            OrderError: If parameters are invalid
        """
        # Validate pair
        if not pair or not isinstance(pair, str):
            raise OrderError("Invalid trading pair")

        # Validate side
        if side.lower() not in ["buy", "sell"]:
            raise OrderError("Invalid order side. Must be 'buy' or 'sell'")

        # Validate order type
        if order_type.lower() not in ["market", "limit"]:
            raise OrderError("Invalid order type. Must be 'market' or 'limit'")

        # Validate volume
        try:
            volume_decimal = Decimal(str(volume))
            if volume_decimal <= 0:
                raise OrderError("Order volume must be greater than 0")
        except (ValueError, TypeError):
            raise OrderError("Invalid order volume")

        # Validate price for limit orders
        if order_type.lower() == "limit":
            if price is None:
                raise OrderError("Price is required for limit orders")
            try:
                price_decimal = Decimal(str(price))
                if price_decimal <= 0:
                    raise OrderError("Order price must be greater than 0")
            except (ValueError, TypeError):
                raise OrderError("Invalid order price")

        # Return validated parameters
        validated = {
            "pair": pair.upper(),
            "type": side.lower(),
            "ordertype": order_type.lower(),
            "volume": str(volume)
        }

        if price is not None:
            validated["price"] = str(price)

        return validated

    async def place_market_order(self, pair: str, side: str, volume: Union[str, Decimal],
                               **kwargs) -> Dict[str, Any]:
        """
        Place a market order.

        Args:
            pair: Trading pair (e.g., "XBTUSD")
            side: Order side ("buy" or "sell")
            volume: Order volume
            **kwargs: Additional order parameters

        Returns:
            Order placement response from Kraken

        Raises:
            OrderError: If order parameters are invalid
            ExchangeError: If API call fails
        """
        try:
            # Validate parameters
            order_data = self._validate_order_parameters(pair, side, "market", volume)

            # Add additional parameters
            order_data.update(kwargs)

            self.log_info(
                "Placing market order",
                pair=pair,
                side=side,
                volume=str(volume)
            )

            # Make API request with retry
            response = await self._make_request_with_retry(
                "POST",
                "/0/private/AddOrder",
                order_data
            )

            if "result" in response and response["result"]:
                result = response["result"]
                self.log_info(
                    "Market order placed successfully",
                    order_ids=result.get("txid", []),
                    description=result.get("descr", {})
                )

            return response

        except Exception as e:
            self.log_error("Failed to place market order", error=e, pair=pair, side=side)
            raise

    async def place_limit_order(self, pair: str, side: str, volume: Union[str, Decimal],
                              price: Union[str, Decimal], **kwargs) -> Dict[str, Any]:
        """
        Place a limit order.

        Args:
            pair: Trading pair (e.g., "XBTUSD")
            side: Order side ("buy" or "sell")
            volume: Order volume
            price: Order price
            **kwargs: Additional order parameters

        Returns:
            Order placement response from Kraken

        Raises:
            OrderError: If order parameters are invalid
            ExchangeError: If API call fails
        """
        try:
            # Validate parameters
            order_data = self._validate_order_parameters(pair, side, "limit", volume, price)

            # Add additional parameters
            order_data.update(kwargs)

            self.log_info(
                "Placing limit order",
                pair=pair,
                side=side,
                volume=str(volume),
                price=str(price)
            )

            # Make API request with retry
            response = await self._make_request_with_retry(
                "POST",
                "/0/private/AddOrder",
                order_data
            )

            if "result" in response and response["result"]:
                result = response["result"]
                self.log_info(
                    "Limit order placed successfully",
                    order_ids=result.get("txid", []),
                    description=result.get("descr", {})
                )

            return response

        except Exception as e:
            self.log_error("Failed to place limit order", error=e, pair=pair, side=side)
            raise

    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """
        Cancel an existing order.

        Args:
            order_id: Order ID to cancel

        Returns:
            Cancellation response from Kraken

        Raises:
            OrderError: If order ID is invalid
            ExchangeError: If API call fails
        """
        try:
            if not order_id or not isinstance(order_id, str):
                raise OrderError("Invalid order ID")

            cancel_data = {"txid": order_id}

            self.log_info("Canceling order", order_id=order_id)

            response = await self._make_request_with_retry(
                "POST",
                "/0/private/CancelOrder",
                cancel_data
            )

            if "result" in response and response["result"]:
                self.log_info("Order canceled successfully", order_id=order_id)

            return response

        except Exception as e:
            self.log_error("Failed to cancel order", error=e, order_id=order_id)
            raise

    async def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """
        Get the status of a specific order.

        Args:
            order_id: Order ID to query

        Returns:
            Order status response from Kraken

        Raises:
            OrderError: If order ID is invalid
            ExchangeError: If API call fails
        """
        try:
            if not order_id or not isinstance(order_id, str):
                raise OrderError("Invalid order ID")

            query_data = {"txid": order_id}

            response = await self._make_request_with_retry(
                "POST",
                "/0/private/QueryOrders",
                query_data
            )

            return response

        except Exception as e:
            self.log_error("Failed to get order status", error=e, order_id=order_id)
            raise

    async def get_open_orders(self) -> Dict[str, Any]:
        """
        Get all open orders.

        Returns:
            Open orders response from Kraken

        Raises:
            ExchangeError: If API call fails
        """
        try:
            response = await self._make_request_with_retry(
                "POST",
                "/0/private/OpenOrders",
                {}
            )

            return response

        except Exception as e:
            self.log_error("Failed to get open orders", error=e)
            raise

    async def get_closed_orders(self, **kwargs) -> Dict[str, Any]:
        """
        Get closed orders history.

        Args:
            **kwargs: Query parameters (start, end, ofs, closetime)

        Returns:
            Closed orders response from Kraken

        Raises:
            ExchangeError: If API call fails
        """
        try:
            response = await self._make_request_with_retry(
                "POST",
                "/0/private/ClosedOrders",
                kwargs
            )

            return response

        except Exception as e:
            self.log_error("Failed to get closed orders", error=e)
            raise

    # EXISTING METHODS (from base REST client)

    async def get_server_time(self) -> Dict[str, Any]:
        """Get server time from Kraken."""
        return await self._make_request_with_retry("GET", "/0/public/Time", authenticated=False)

    async def get_system_status(self) -> Dict[str, Any]:
        """Get system status from Kraken."""
        return await self._make_request_with_retry("GET", "/0/public/SystemStatus", authenticated=False)

    async def get_account_balance(self) -> Dict[str, Any]:
        """Get account balance."""
        return await self._make_request_with_retry("POST", "/0/private/Balance")

    async def get_websocket_token(self) -> str:
        """
        Get WebSocket authentication token.

        Returns:
            Authentication token for WebSocket connections
        """
        response = await self._make_request_with_retry("POST", "/0/private/GetWebSocketsToken")

        if "result" in response and "token" in response["result"]:
            token = response["result"]["token"]
            self.log_info("WebSocket token obtained successfully")
            return token
        else:
            raise ExchangeError("Failed to obtain WebSocket token", details=response)

    async def test_authentication(self) -> bool:
        """
        Test authentication by making a simple API call.

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
            "order_operations": False,
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

                # Test order operations (just query, don't place orders)
                await self.get_open_orders()
                results["order_operations"] = True

            except AuthenticationError as e:
                results["errors"].append(f"Authentication error: {e}")
            except Exception as e:
                results["errors"].append(f"Private API error: {e}")
        else:
            results["errors"].append("No authentication credentials available")

        self.log_info("Enhanced connection validation completed", **results)
        return results


# Convenience function for creating enhanced client
async def create_enhanced_rest_client(max_retries: int = 3) -> EnhancedKrakenRestClient:
    """
    Create an EnhancedKrakenRestClient with settings from configuration.

    Args:
        max_retries: Maximum number of retries for failed requests

    Returns:
        Configured EnhancedKrakenRestClient instance
    """
    return EnhancedKrakenRestClient(max_retries=max_retries)


# Export the enhanced client as the main client
KrakenRestClient = EnhancedKrakenRestClient
