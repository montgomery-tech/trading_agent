#!/usr/bin/env python3
"""
Password Service for API Key System
Creates the missing password_service module that API key service depends on
"""

import logging
from passlib.context import CryptContext
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)


class PasswordService:
    """Password hashing and verification service using bcrypt"""
    
    def __init__(self):
        # Configure bcrypt context
        self.pwd_context = CryptContext(
            schemes=["bcrypt"],
            deprecated="auto",
            bcrypt__rounds=12  # Good balance of security and performance
        )
        logger.info("Password service initialized with bcrypt")

    def hash_password(self, password: str) -> str:
        """
        Hash a password using bcrypt.

        Args:
            password: Plain text password

        Returns:
            Hashed password string
        """
        try:
            return self.pwd_context.hash(password)
        except Exception as e:
            logger.error(f"Failed to hash password: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Password processing failed"
            )

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password against its hash.

        Args:
            plain_password: Plain text password
            hashed_password: Hashed password from database

        Returns:
            True if password matches, False otherwise
        """
        try:
            return self.pwd_context.verify(plain_password, hashed_password)
        except Exception as e:
            logger.error(f"Failed to verify password: {e}")
            return False

    def needs_update(self, hashed_password: str) -> bool:
        """
        Check if a password hash needs to be updated (rehashed).

        Args:
            hashed_password: Hashed password from database

        Returns:
            True if hash needs update, False otherwise
        """
        try:
            return self.pwd_context.needs_update(hashed_password)
        except Exception:
            return False


# Global service instance
password_service = PasswordService()
