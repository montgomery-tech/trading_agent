"""
Dependency injection for FastAPI
"""

from fastapi import Depends, HTTPException, status, Request
from api.database import DatabaseManager
from api.config import settings
import logging

logger = logging.getLogger(__name__)


def get_database(request: Request) -> DatabaseManager:
    """Get database instance from app state"""
    if not hasattr(request.app.state, 'database'):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not available"
        )
    
    return request.app.state.database


def validate_user_exists(username: str, db: DatabaseManager = Depends(get_database)):
    """Validate that a user exists and is active"""
    query = "SELECT id, username, is_active FROM users WHERE username = ?"
    results = db.execute_query(query, (username,))
    
    if not results:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{username}' not found"
        )
    
    user = results[0]
    if not user['is_active']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User '{username}' is not active"
        )
    
    return user


def validate_currency_exists(currency_code: str, db: DatabaseManager = Depends(get_database)):
    """Validate that a currency exists and is active"""
    query = "SELECT code, name, is_active FROM currencies WHERE code = ?"
    results = db.execute_query(query, (currency_code.upper(),))
    
    if not results:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Currency '{currency_code}' not found"
        )
    
    currency = results[0]
    if not currency['is_active']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Currency '{currency_code}' is not active"
        )
    
    return currency


def get_pagination_params(page: int = 1, page_size: int = 20):
    """Get pagination parameters with validation"""
    if page < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Page number must be 1 or greater"
        )
    
    if page_size < 1 or page_size > settings.MAX_PAGE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Page size must be between 1 and {settings.MAX_PAGE_SIZE}"
        )
    
    offset = (page - 1) * page_size
    return {"page": page, "page_size": page_size, "offset": offset}
