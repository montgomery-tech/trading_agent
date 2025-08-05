#!/usr/bin/env python3
"""
Entity Context Middleware
Task 2.4: Middleware for automatic entity context injection and logging

This middleware automatically adds entity context to requests and provides
audit logging for entity-scoped operations.
"""

import logging
import time
from typing import Optional, Dict, Any
from datetime import datetime, timezone

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


class EntityContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware for automatic entity context injection and audit logging.
    
    This middleware:
    1. Extracts entity context from authenticated requests
    2. Logs entity-scoped operations for audit trails
    3. Adds entity information to request state
    4. Tracks API usage by entity
    """
    
    def __init__(self, app, enable_audit_logging: bool = True, enable_performance_tracking: bool = True):
        super().__init__(app)
        self.enable_audit_logging = enable_audit_logging
        self.enable_performance_tracking = enable_performance_tracking
        logger.info("Entity Context Middleware initialized")
    
    async def dispatch(self, request: Request, call_next):
        """Main middleware dispatch method"""
        
        # Start timing for performance tracking
        start_time = time.time()
        
        # Extract entity context from request
        entity_context = await self._extract_entity_context(request)
        
        # Add entity context to request state
        request.state.entity_context = entity_context
        
        # Log request if audit logging is enabled
        if self.enable_audit_logging and entity_context:
            await self._log_entity_request(request, entity_context)
        
        # Process the request
        try:
            response = await call_next(request)
            
            # Log successful response if needed
            if self.enable_audit_logging and entity_context:
                await self._log_entity_response(request, response, entity_context, start_time)
            
            # Add entity context headers to response (for debugging)
            if entity_context and isinstance(response, Response):
                if entity_context.get('entity_id'):
                    response.headers["X-Entity-ID"] = entity_context['entity_id']
                if entity_context.get('entity_code'):
                    response.headers["X-Entity-Code"] = entity_context['entity_code']
            
            return response
            
        except Exception as e:
            # Log error with entity context
            if self.enable_audit_logging and entity_context:
                await self._log_entity_error(request, e, entity_context, start_time)
            
            # Re-raise the exception
            raise
    
    async def _extract_entity_context(self, request: Request) -> Optional[Dict[str, Any]]:
        """
        Extract entity context from the request.
        
        This looks for entity information in:
        1. Path parameters (entity_id)
        2. Query parameters 
        3. Authorization header (if API key contains entity info)
        """
        try:
            context = {}
            
            # Extract entity ID from path parameters
            entity_id = request.path_params.get('entity_id')
            if entity_id:
                context['entity_id'] = entity_id
                context['source'] = 'path_param'
            
            # Extract entity ID from query parameters as fallback
            if not entity_id:
                entity_id = request.query_params.get('entity_id')
                if entity_id:
                    context['entity_id'] = entity_id
                    context['source'] = 'query_param'
            
            # Extract user information from authorization header
            auth_header = request.headers.get('Authorization')
            if auth_header:
                context['has_auth'] = True
                
                # We could potentially decode the API key to get user info,
                # but that would require access to the API key service.
                # For now, we'll rely on the authentication dependencies
                # to populate this information.
            
            # Add request metadata
            context.update({
                'method': request.method,
                'path': str(request.url.path),
                'endpoint': request.url.path,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'client_ip': request.client.host if request.client else None,
                'user_agent': request.headers.get('User-Agent')
            })
            
            return context if context else None
            
        except Exception as e:
            logger.warning(f"Failed to extract entity context: {e}")
            return None
    
    async def _log_entity_request(self, request: Request, entity_context: Dict[str, Any]):
        """Log entity-scoped request for audit trail"""
        try:
            log_data = {
                'event': 'entity_request',
                'method': entity_context['method'],
                'endpoint': entity_context['endpoint'],
                'entity_id': entity_context.get('entity_id'),
                'client_ip': entity_context.get('client_ip'),
                'user_agent': entity_context.get('user_agent'),
                'timestamp': entity_context['timestamp']
            }
            
            # Log at INFO level for entity-scoped operations
            if entity_context.get('entity_id'):
                logger.info(f"Entity request: {log_data['method']} {log_data['endpoint']} "
                           f"[Entity: {log_data['entity_id']}] from {log_data['client_ip']}")
            
        except Exception as e:
            logger.warning(f"Failed to log entity request: {e}")
    
    async def _log_entity_response(self, request: Request, response: Response, 
                                  entity_context: Dict[str, Any], start_time: float):
        """Log entity-scoped response for audit trail"""
        try:
            duration = time.time() - start_time
            
            log_data = {
                'event': 'entity_response',
                'method': entity_context['method'],
                'endpoint': entity_context['endpoint'],
                'entity_id': entity_context.get('entity_id'),
                'status_code': response.status_code,
                'duration_ms': round(duration * 1000, 2),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            # Log performance warnings for slow requests
            if self.enable_performance_tracking and duration > 2.0:  # 2 second threshold
                logger.warning(f"Slow entity request: {log_data['method']} {log_data['endpoint']} "
                             f"[Entity: {log_data['entity_id']}] took {log_data['duration_ms']}ms")
            
            # Log successful entity operations
            if entity_context.get('entity_id') and 200 <= response.status_code < 300:
                logger.info(f"Entity response: {log_data['status_code']} {log_data['method']} "
                           f"{log_data['endpoint']} [Entity: {log_data['entity_id']}] "
                           f"in {log_data['duration_ms']}ms")
            
        except Exception as e:
            logger.warning(f"Failed to log entity response: {e}")
    
    async def _log_entity_error(self, request: Request, error: Exception, 
                               entity_context: Dict[str, Any], start_time: float):
        """Log entity-scoped errors for audit trail"""
        try:
            duration = time.time() - start_time
            
            log_data = {
                'event': 'entity_error',
                'method': entity_context['method'],
                'endpoint': entity_context['endpoint'],
                'entity_id': entity_context.get('entity_id'),
                'error_type': type(error).__name__,
                'error_message': str(error),
                'duration_ms': round(duration * 1000, 2),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            # Log entity-scoped errors
            if entity_context.get('entity_id'):
                logger.error(f"Entity error: {log_data['error_type']} in {log_data['method']} "
                           f"{log_data['endpoint']} [Entity: {log_data['entity_id']}]: "
                           f"{log_data['error_message']}")
            
        except Exception as e:
            logger.warning(f"Failed to log entity error: {e}")


class EntitySecurityMiddleware(BaseHTTPMiddleware):
    """
    Security middleware for entity-scoped operations.
    
    This middleware provides additional security checks:
    1. Rate limiting per entity
    2. Suspicious activity detection
    3. Entity access pattern analysis
    """
    
    def __init__(self, app, enable_rate_limiting: bool = True, enable_security_monitoring: bool = True):
        super().__init__(app)
        self.enable_rate_limiting = enable_rate_limiting
        self.enable_security_monitoring = enable_security_monitoring
        self.request_counts = {}  # Simple in-memory rate limiting (use Redis in production)
        logger.info("Entity Security Middleware initialized")
    
    async def dispatch(self, request: Request, call_next):
        """Main security middleware dispatch"""
        
        # Extract entity context
        entity_id = request.path_params.get('entity_id')
        client_ip = request.client.host if request.client else 'unknown'
        
        # Rate limiting check
        if self.enable_rate_limiting and entity_id:
            if await self._check_rate_limit(entity_id, client_ip, request):
                return JSONResponse(
                    status_code=429,
                    content={"error": "Rate limit exceeded for entity", "entity_id": entity_id}
                )
        
        # Security monitoring
        if self.enable_security_monitoring and entity_id:
            await self._monitor_security_patterns(entity_id, client_ip, request)
        
        # Process request
        response = await call_next(request)
        
        return response
    
    async def _check_rate_limit(self, entity_id: str, client_ip: str, request: Request) -> bool:
        """
        Check rate limits for entity operations.
        
        Returns True if rate limit exceeded, False otherwise.
        """
        try:
            # Simple rate limiting logic (implement proper rate limiting in production)
            current_time = time.time()
            key = f"{entity_id}:{client_ip}"
            
            if key not in self.request_counts:
                self.request_counts[key] = []
            
            # Remove old requests (keep only last minute)
            self.request_counts[key] = [
                timestamp for timestamp in self.request_counts[key]
                if current_time - timestamp < 60
            ]
            
            # Check if rate limit exceeded (60 requests per minute per entity per IP)
            if len(self.request_counts[key]) >= 60:
                logger.warning(f"Rate limit exceeded for entity {entity_id} from {client_ip}")
                return True
            
            # Add current request
            self.request_counts[key].append(current_time)
            return False
            
        except Exception as e:
            logger.warning(f"Rate limit check failed: {e}")
            return False
    
    async def _monitor_security_patterns(self, entity_id: str, client_ip: str, request: Request):
        """Monitor for suspicious security patterns"""
        try:
            # Example security monitoring (implement more sophisticated monitoring in production)
            
            # Check for suspicious endpoints
            suspicious_patterns = ['/admin/', '/internal/', '/../', '/.env']
            path = str(request.url.path).lower()
            
            for pattern in suspicious_patterns:
                if pattern in path:
                    logger.warning(f"Suspicious request pattern detected: {pattern} "
                                 f"for entity {entity_id} from {client_ip}")
            
            # Check for unusual user agents
            user_agent = request.headers.get('User-Agent', '').lower()
            suspicious_agents = ['bot', 'crawler', 'scanner', 'curl', 'wget']
            
            if any(agent in user_agent for agent in suspicious_agents):
                logger.info(f"Automated tool detected: {user_agent} "
                           f"for entity {entity_id} from {client_ip}")
            
        except Exception as e:
            logger.warning(f"Security monitoring failed: {e}")


# =============================================================================
# Middleware Integration Helpers
# =============================================================================

def add_entity_middleware(app, enable_audit_logging: bool = True, enable_security: bool = True):
    """
    Add entity middleware to FastAPI application.
    
    Args:
        app: FastAPI application instance
        enable_audit_logging: Enable audit logging middleware
        enable_security: Enable security middleware
    """
    
    if enable_security:
        app.add_middleware(
            EntitySecurityMiddleware,
            enable_rate_limiting=True,
            enable_security_monitoring=True
        )
        logger.info("Entity Security Middleware added to application")
    
    if enable_audit_logging:
        app.add_middleware(
            EntityContextMiddleware,
            enable_audit_logging=True,
            enable_performance_tracking=True
        )
        logger.info("Entity Context Middleware added to application")


# =============================================================================
# Utility Functions for Request Context
# =============================================================================

def get_entity_context_from_request(request: Request) -> Optional[Dict[str, Any]]:
    """
    Get entity context from request state.
    
    This can be used in route handlers to access entity context
    that was set by the middleware.
    """
    return getattr(request.state, 'entity_context', None)


def get_entity_id_from_request(request: Request) -> Optional[str]:
    """Get entity ID from request context"""
    context = get_entity_context_from_request(request)
    return context.get('entity_id') if context else None


# =============================================================================
# Example Usage Documentation
# =============================================================================

"""
Example usage of entity middleware:

# In your main.py file:
from api.entity_middleware import add_entity_middleware

# Add entity middleware to your FastAPI app
add_entity_middleware(app, enable_audit_logging=True, enable_security=True)

# In your route handlers:
from api.entity_middleware import get_entity_context_from_request

@router.get("/entities/{entity_id}/data")
async def get_entity_data(
    entity_id: str,
    request: Request,
    user: EntityAuthenticatedUser = Depends(require_entity_access())
):
    # Get entity context from middleware
    entity_context = get_entity_context_from_request(request)
    
    return {
        "entity_id": entity_id,
        "user": user.username,
        "context": entity_context,
        "data": "entity-specific data"
    }

The middleware will automatically:
1. Log entity-scoped operations: "Entity request: GET /entities/123/data [Entity: 123] from 192.168.1.1"
2. Track performance: "Entity response: 200 GET /entities/123/data [Entity: 123] in 45.2ms"
3. Monitor security: Rate limiting and suspicious activity detection
4. Add debug headers: X-Entity-ID and X-Entity-Code to responses
"""
