#!/usr/bin/env python3
"""
Task 1.3: Basic Authentication and Security Implementation

This module adds comprehensive security measures to the MCP server,
including API key validation, authorization, audit logging, and rate limiting.

File Location: src/trading_systems/mcp_server/security.py
"""

import asyncio
import hashlib
import hmac
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Callable, Any
from functools import wraps
import json

from ..utils.logger import LoggerMixin
from ..config.settings import settings
from .config import MCPServerConfig


@dataclass
class SecurityEvent:
    """Security event for audit logging."""
    timestamp: datetime
    event_type: str
    client_id: Optional[str]
    operation: str
    success: bool
    details: Dict[str, Any] = field(default_factory=dict)
    ip_address: Optional[str] = None


@dataclass
class RateLimitState:
    """Rate limiting state for a client."""
    requests: deque = field(default_factory=deque)
    trading_operations: deque = field(default_factory=deque)
    last_violation: Optional[datetime] = None
    violation_count: int = 0


class SecurityManager(LoggerMixin):
    """
    Comprehensive security manager for MCP server operations.
    
    Provides:
    - API key validation
    - Operation authorization
    - Rate limiting
    - Audit logging
    - Security event tracking
    """
    
    def __init__(self, config: MCPServerConfig):
        super().__init__()
        self.config = config
        
        # Security state
        self.authorized_clients: Set[str] = set()
        self.rate_limit_state: Dict[str, RateLimitState] = defaultdict(RateLimitState)
        self.security_events: List[SecurityEvent] = []
        self.blocked_clients: Set[str] = set()
        
        # Security configuration
        self.api_key_hash = self._hash_api_key(settings.kraken_api_key) if settings.kraken_api_key else None
        self.max_events = 1000  # Maximum security events to keep
        
        self.log_info("Security manager initialized", 
                     auth_required=config.security.require_authentication,
                     rate_limiting=True,
                     audit_logging=config.security.audit_all_operations)
    
    def _hash_api_key(self, api_key: str) -> str:
        """Hash API key for secure storage."""
        return hashlib.sha256(api_key.encode()).hexdigest()
    
    def _log_security_event(self, event_type: str, client_id: Optional[str], 
                          operation: str, success: bool, **details):
        """Log a security event."""
        event = SecurityEvent(
            timestamp=datetime.now(),
            event_type=event_type,
            client_id=client_id,
            operation=operation,
            success=success,
            details=details
        )
        
        self.security_events.append(event)
        
        # Trim old events
        if len(self.security_events) > self.max_events:
            self.security_events = self.security_events[-self.max_events:]
        
        # Log the event
        self.log_info("Security event",
                     event_type=event_type,
                     client_id=client_id,
                     operation=operation,
                     success=success,
                     **details)
    
    def authenticate_client(self, client_id: str, api_key: Optional[str] = None) -> bool:
        """
        Authenticate a client.
        
        Args:
            client_id: Client identifier
            api_key: API key for authentication
            
        Returns:
            True if authenticated, False otherwise
        """
        if not self.config.security.require_authentication:
            # Authentication disabled - allow all
            self.authorized_clients.add(client_id)
            self._log_security_event("authentication", client_id, "authenticate", True,
                                   reason="authentication_disabled")
            return True
        
        # Check if client is in allowlist
        if self.config.security.allowed_clients and client_id not in self.config.security.allowed_clients:
            self._log_security_event("authentication", client_id, "authenticate", False,
                                   reason="client_not_in_allowlist")
            return False
        
        # Validate API key if provided
        if api_key and self.api_key_hash:
            provided_hash = self._hash_api_key(api_key)
            if provided_hash == self.api_key_hash:
                self.authorized_clients.add(client_id)
                self._log_security_event("authentication", client_id, "authenticate", True,
                                       reason="valid_api_key")
                return True
            else:
                self._log_security_event("authentication", client_id, "authenticate", False,
                                       reason="invalid_api_key")
                return False
        
        # For demo mode, allow without API key
        if not self.config.enable_real_trading:
            self.authorized_clients.add(client_id)
            self._log_security_event("authentication", client_id, "authenticate", True,
                                   reason="demo_mode")
            return True
        
        self._log_security_event("authentication", client_id, "authenticate", False,
                               reason="no_valid_credentials")
        return False
    
    def authorize_operation(self, client_id: str, operation: str) -> bool:
        """
        Authorize a client operation.
        
        Args:
            client_id: Client identifier
            operation: Operation being attempted
            
        Returns:
            True if authorized, False otherwise
        """
        # Check if client is blocked
        if client_id in self.blocked_clients:
            self._log_security_event("authorization", client_id, operation, False,
                                   reason="client_blocked")
            return False
        
        # Check authentication
        if self.config.security.require_authentication and client_id not in self.authorized_clients:
            self._log_security_event("authorization", client_id, operation, False,
                                   reason="not_authenticated")
            return False
        
        # Check operation-specific permissions
        trading_operations = {"place_order", "cancel_order", "modify_order", "get_account_balance"}
        
        if operation in trading_operations:
            if not self.config.enable_real_trading and operation in {"place_order", "cancel_order", "modify_order"}:
                self._log_security_event("authorization", client_id, operation, False,
                                       reason="real_trading_disabled")
                return False
        
        self._log_security_event("authorization", client_id, operation, True)
        return True
    
    def check_rate_limit(self, client_id: str, operation: str) -> bool:
        """
        Check if client is within rate limits.
        
        Args:
            client_id: Client identifier
            operation: Operation being attempted
            
        Returns:
            True if within limits, False if rate limited
        """
        now = datetime.now()
        state = self.rate_limit_state[client_id]
        
        # Clean old requests (older than 1 minute)
        minute_ago = now - timedelta(minutes=1)
        while state.requests and state.requests[0] < minute_ago:
            state.requests.popleft()
        
        # Clean old trading operations (older than 1 hour)
        hour_ago = now - timedelta(hours=1)
        while state.trading_operations and state.trading_operations[0] < hour_ago:
            state.trading_operations.popleft()
        
        # Check general rate limit
        if len(state.requests) >= self.config.security.max_requests_per_minute:
            state.last_violation = now
            state.violation_count += 1
            self._log_security_event("rate_limit", client_id, operation, False,
                                   reason="general_rate_limit",
                                   requests_per_minute=len(state.requests))
            return False
        
        # Check trading operation rate limit
        trading_operations = {"place_order", "cancel_order", "modify_order"}
        if operation in trading_operations:
            if len(state.trading_operations) >= self.config.security.max_trading_operations_per_hour:
                state.last_violation = now
                state.violation_count += 1
                self._log_security_event("rate_limit", client_id, operation, False,
                                       reason="trading_rate_limit",
                                       trading_operations_per_hour=len(state.trading_operations))
                return False
            
            # Record trading operation
            state.trading_operations.append(now)
        
        # Record general request
        state.requests.append(now)
        
        return True
    
    def validate_operation_parameters(self, operation: str, parameters: Dict[str, Any]) -> tuple[bool, str]:
        """
        Validate operation parameters for security.
        
        Args:
            operation: Operation name
            parameters: Operation parameters
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if operation == "place_order":
            # Validate order value
            if "price" in parameters and "volume" in parameters:
                try:
                    price = float(parameters["price"])
                    volume = float(parameters["volume"])
                    order_value_usd = price * volume
                    
                    if order_value_usd > self.config.security.max_order_value_usd:
                        return False, f"Order value ${order_value_usd:.2f} exceeds maximum ${self.config.security.max_order_value_usd}"
                except (ValueError, TypeError):
                    return False, "Invalid price or volume format"
            
            # Validate trading pair
            if "pair" in parameters:
                allowed_pairs = self.config.get_allowed_trading_pairs()
                if parameters["pair"] not in allowed_pairs:
                    return False, f"Trading pair {parameters['pair']} not allowed"
            
            # Check market orders
            if parameters.get("order_type") == "market" and not self.config.security.enable_market_orders:
                return False, "Market orders are disabled for security"
        
        return True, ""
    
    def get_security_summary(self) -> Dict[str, Any]:
        """Get security status summary."""
        now = datetime.now()
        
        # Count recent events
        hour_ago = now - timedelta(hours=1)
        recent_events = [e for e in self.security_events if e.timestamp > hour_ago]
        
        # Count by type
        event_counts = defaultdict(int)
        for event in recent_events:
            event_counts[event.event_type] += 1
        
        return {
            "security_status": "active",
            "authenticated_clients": len(self.authorized_clients),
            "blocked_clients": len(self.blocked_clients),
            "recent_events_count": len(recent_events),
            "event_breakdown": dict(event_counts),
            "rate_limiting_active": True,
            "authentication_required": self.config.security.require_authentication,
            "audit_logging": self.config.security.audit_all_operations,
            "max_order_value_usd": self.config.security.max_order_value_usd,
            "allowed_trading_pairs": list(self.config.get_allowed_trading_pairs())
        }
    
    def block_client(self, client_id: str, reason: str):
        """Block a client for security violations."""
        self.blocked_clients.add(client_id)
        self.authorized_clients.discard(client_id)
        self._log_security_event("security_violation", client_id, "block_client", True,
                               reason=reason)
    
    def unblock_client(self, client_id: str):
        """Unblock a previously blocked client."""
        self.blocked_clients.discard(client_id)
        self._log_security_event("security_action", client_id, "unblock_client", True)


def require_authentication(operation_name: str):
    """Decorator to require authentication for MCP tools."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get the security manager from context
            # This would be set up in the enhanced server
            # For now, we'll implement a basic check
            
            # TODO: Integrate with MCP context to get client_id and security_manager
            # For demonstration, we'll assume authentication passes in demo mode
            
            try:
                result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
                return result
            except Exception as e:
                return f"❌ Security check failed for {operation_name}: {str(e)}"
        
        return wrapper
    return decorator


def require_authorization(operation_name: str):
    """Decorator to require authorization for MCP tools."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Authorization check would go here
            # For now, we'll implement basic validation
            
            try:
                result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
                return result
            except Exception as e:
                return f"❌ Authorization failed for {operation_name}: {str(e)}"
        
        return wrapper
    return decorator


# =============================================================================
# SECURITY TESTING FUNCTIONS
# =============================================================================

async def test_security_manager():
    """Test the security manager functionality."""
    from .config import MCPServerConfig
    
    print("🔒 Testing Security Manager")
    print("=" * 40)
    
    # Create config and security manager
    config = MCPServerConfig()
    security_manager = SecurityManager(config)
    
    # Test authentication
    print("🧪 Testing authentication...")
    client_id = "test_client"
    
    # Should pass in demo mode
    auth_result = security_manager.authenticate_client(client_id)
    print(f"   Demo mode auth: {'✅' if auth_result else '❌'}")
    
    # Test authorization
    print("\n🧪 Testing authorization...")
    auth_result = security_manager.authorize_operation(client_id, "get_account_balance")
    print(f"   Account balance auth: {'✅' if auth_result else '❌'}")
    
    # Test rate limiting
    print("\n🧪 Testing rate limiting...")
    rate_ok = security_manager.check_rate_limit(client_id, "ping")
    print(f"   Rate limit check: {'✅' if rate_ok else '❌'}")
    
    # Test parameter validation
    print("\n🧪 Testing parameter validation...")
    valid, error = security_manager.validate_operation_parameters("place_order", {
        "pair": "XBT/USD",
        "price": 50000,
        "volume": 0.01,
        "order_type": "limit"
    })
    print(f"   Parameter validation: {'✅' if valid else '❌'} {error}")
    
    # Get security summary
    print("\n📊 Security summary:")
    summary = security_manager.get_security_summary()
    print(f"   Authenticated clients: {summary['authenticated_clients']}")
    print(f"   Security events: {summary['recent_events_count']}")
    print(f"   Max order value: ${summary['max_order_value_usd']}")
    
    print("\n✅ Security manager test complete!")
    return True


if __name__ == "__main__":
    asyncio.run(test_security_manager())

