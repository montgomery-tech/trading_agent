#!/usr/bin/env python3
"""
Password Service for API Key Authentication System
Handles password hashing and verification for user accounts
"""

import bcrypt
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class PasswordService:
    """Service for password hashing and verification"""
    
    def __init__(self):
        """Initialize the password service"""
        self.rounds = 12  # bcrypt rounds for security
        logger.info("Password Service initialized")
    
    def hash_password(self, password: str) -> str:
        """
        Hash a password using bcrypt.
        
        Args:
            password: Plain text password to hash
            
        Returns:
            Hashed password string
        """
        try:
            # Convert password to bytes
            password_bytes = password.encode('utf-8')
            
            # Generate salt and hash
            salt = bcrypt.gensalt(rounds=self.rounds)
            hashed = bcrypt.hashpw(password_bytes, salt)
            
            # Return as string
            return hashed.decode('utf-8')
            
        except Exception as e:
            logger.error(f"Failed to hash password: {e}")
            raise ValueError("Password hashing failed")
    
    def verify_password(self, password: str, hashed_password: str) -> bool:
        """
        Verify a password against its hash.
        
        Args:
            password: Plain text password to verify
            hashed_password: Stored password hash
            
        Returns:
            True if password matches, False otherwise
        """
        try:
            # Convert to bytes
            password_bytes = password.encode('utf-8')
            hashed_bytes = hashed_password.encode('utf-8')
            
            # Verify password
            return bcrypt.checkpw(password_bytes, hashed_bytes)
            
        except Exception as e:
            logger.error(f"Password verification failed: {e}")
            return False
    
    def is_strong_password(self, password: str) -> tuple[bool, list[str]]:
        """
        Check if password meets strength requirements.
        
        Args:
            password: Password to check
            
        Returns:
            Tuple of (is_strong, list_of_issues)
        """
        issues = []
        
        # Length check
        if len(password) < 8:
            issues.append("Password must be at least 8 characters long")
        
        # Character type checks
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)
        
        if not has_upper:
            issues.append("Password must contain at least one uppercase letter")
        if not has_lower:
            issues.append("Password must contain at least one lowercase letter")
        if not has_digit:
            issues.append("Password must contain at least one number")
        if not has_special:
            issues.append("Password must contain at least one special character")
        
        # Common password checks
        common_passwords = [
            "password", "123456", "password123", "admin", "qwerty",
            "letmein", "welcome", "monkey", "dragon", "master"
        ]
        
        if password.lower() in common_passwords:
            issues.append("Password is too common")
        
        return len(issues) == 0, issues


# Global instance
password_service = PasswordService()


def get_password_service() -> PasswordService:
    """Get the global password service instance"""
    return password_service
