"""
Base classes for exchange implementations.
"""

from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Dict, List, Optional


class BaseExchangeClient(ABC):
    """
    Abstract base class for exchange WebSocket clients.
    
    This defines the interface that all exchange implementations should follow.
    """
    
    @abstractmethod
    async def connect_public(self) -> None:
        """Connect to the exchange's public WebSocket endpoint."""
        pass
    
    @abstractmethod
    async def connect_private(self) -> None:
        """Connect to the exchange's private WebSocket endpoint."""
        pass
    
    @abstractmethod
    async def disconnect(self, endpoint: Optional[str] = None) -> None:
        """Disconnect from WebSocket endpoint(s)."""
        pass
    
    @abstractmethod
    async def subscribe_ticker(self, pairs: List[str]) -> None:
        """Subscribe to ticker data for specified trading pairs."""
        pass
    
    @abstractmethod
    async def subscribe_orderbook(self, pairs: List[str], depth: int = 10) -> None:
        """Subscribe to orderbook data for specified trading pairs."""
        pass
    
    @abstractmethod
    async def subscribe_trades(self, pairs: List[str]) -> None:
        """Subscribe to trade data for specified trading pairs."""
        pass
    
    @abstractmethod
    async def unsubscribe(self, subscription_id: str) -> None:
        """Unsubscribe from a specific subscription."""
        pass
    
    @abstractmethod
    async def listen_public(self) -> AsyncGenerator[Dict[str, Any], None]:
        """Listen for messages from the public WebSocket."""
        pass
    
    @abstractmethod
    async def listen_private(self) -> AsyncGenerator[Dict[str, Any], None]:
        """Listen for messages from the private WebSocket."""
        pass
    
    @abstractmethod
    def get_connection_status(self) -> Dict[str, Any]:
        """Get current connection status."""
        pass


class BaseMarketDataProcessor(ABC):
    """
    Abstract base class for processing market data from exchanges.
    """
    
    @abstractmethod
    async def process_ticker(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process ticker data into standardized format."""
        pass
    
    @abstractmethod
    async def process_orderbook(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process orderbook data into standardized format."""
        pass
    
    @abstractmethod
    async def process_trade(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process trade data into standardized format."""
        pass


class BaseOrderManager(ABC):
    """
    Abstract base class for order management.
    """
    
    @abstractmethod
    async def place_order(
        self,
        pair: str,
        side: str,
        order_type: str,
        volume: str,
        price: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Place a new order."""
        pass
    
    @abstractmethod
    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """Cancel an existing order."""
        pass
    
    @abstractmethod
    async def modify_order(
        self,
        order_id: str,
        volume: Optional[str] = None,
        price: Optional[str] = None
    ) -> Dict[str, Any]:
        """Modify an existing order."""
        pass
    
    @abstractmethod
    async def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """Get the status of a specific order."""
        pass
    
    @abstractmethod
    async def get_open_orders(self) -> List[Dict[str, Any]]:
        """Get all open orders."""
        pass
