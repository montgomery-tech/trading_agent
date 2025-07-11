#!/usr/bin/env python3
"""
JWT Service for the Balance Tracking API
Handles JWT token generation, validation, and management
"""

import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Union
import logging

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status

from api.config import settings
from api.auth_models import TokenData, Token, TokenType, UserRole

logger = logging.getLogger(__name__)


class JWTService:
    """
    JWT token service for authentication and authorization.

    Provides secure token generation, validation, and management
    with support for access tokens, refresh tokens, and special-purpose tokens.
    """

    def __init__(self):
        self.secret_key = settings.SECRET_KEY
        self.algorithm = settings.JWT_ALGORITHM
        self.access_token_expire_minutes = settings.JWT_EXPIRE_MINUTES
        self.refresh_token_expire_days = getattr(settings, 'JWT_REFRESH_EXPIRE_DAYS', 7)

        # Validate JWT configuration
        if not self.secret_key or len(self.secret_key) < 32:
            raise ValueError("JWT secret key must be at least 32 characters long")

        if self.algorithm not in ['HS256', 'HS384', 'HS512', 'RS256', 'RS384', 'RS512']:
            raise ValueError(f"Unsupported JWT algorithm: {self.algorithm}")

        logger.info(f"JWT Service initialized with {self.algorithm} algorithm")

    def create_access_token(
        self,
        user_id: str,
        username: str,
        email: str,
        role: UserRole = UserRole.USER,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create a JWT access token for user authentication.

        Args:
            user_id: Unique user identifier
            username: Username
            email: User email address
            role: User role for authorization
            expires_delta: Custom expiration time (optional)

        Returns:
            JWT access token string
        """
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=self.access_token_expire_minutes)

        # Create unique token ID
        jti = str(uuid.uuid4())
        issued_at = datetime.now(timezone.utc)

        # Token payload
        payload = {
            "sub": user_id,  # Subject (user ID)
            "username": username,
            "email": email,
            "role": role.value,
            "token_type": TokenType.ACCESS.value,
            "iat": int(issued_at.timestamp()),  # Issued at
            "exp": int(expire.timestamp()),  # Expiration time
            "jti": jti,  # JWT ID
            "iss": "balance-tracking-api",  # Issuer
            "aud": "balance-tracking-users"  # Audience
        }

        try:
            token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
            logger.debug(f"Created access token for user {username} (expires: {expire})")
            return token
        except Exception as e:
            logger.error(f"Failed to create access token: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create authentication token"
            )

    def create_refresh_token(
        self,
        user_id: str,
        username: str,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create a JWT refresh token for token renewal.

        Args:
            user_id: Unique user identifier
            username: Username
            expires_delta: Custom expiration time (optional)

        Returns:
            JWT refresh token string
        """
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(days=self.refresh_token_expire_days)

        jti = str(uuid.uuid4())
        issued_at = datetime.now(timezone.utc)

        payload = {
            "sub": user_id,
            "username": username,
            "token_type": TokenType.REFRESH.value,
            "iat": int(issued_at.timestamp()),
            "exp": int(expire.timestamp()),
            "jti": jti,
            "iss": "balance-tracking-api",
            "aud": "balance-tracking-users"
        }

        try:
            token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
            logger.debug(f"Created refresh token for user {username} (expires: {expire})")
            return token
        except Exception as e:
            logger.error(f"Failed to create refresh token: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create refresh token"
            )

    def create_special_token(
        self,
        user_id: str,
        username: str,
        email: str,
        token_type: TokenType,
        expires_hours: int = 24,
        additional_claims: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create special-purpose tokens (email verification, password reset, etc.).

        Args:
            user_id: Unique user identifier
            username: Username
            email: User email address
            token_type: Type of special token
            expires_hours: Expiration time in hours
            additional_claims: Additional claims to include

        Returns:
            JWT special token string
        """
        expire = datetime.now(timezone.utc) + timedelta(hours=expires_hours)
        jti = str(uuid.uuid4())
        issued_at = datetime.now(timezone.utc)

        payload = {
            "sub": user_id,
            "username": username,
            "email": email,
            "token_type": token_type.value,
            "iat": int(issued_at.timestamp()),
            "exp": int(expire.timestamp()),
            "jti": jti,
            "iss": "balance-tracking-api",
            "aud": "balance-tracking-users"
        }

        # Add additional claims if provided
        if additional_claims:
            payload.update(additional_claims)

        try:
            token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
            logger.debug(f"Created {token_type.value} token for user {username}")
            return token
        except Exception as e:
            logger.error(f"Failed to create {token_type.value} token: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create {token_type.value} token"
            )

    def validate_token(self, token: str, expected_type: Optional[TokenType] = None) -> TokenData:
        """
        Validate and decode a JWT token.

        Args:
            token: JWT token string
            expected_type: Expected token type for validation

        Returns:
            TokenData object with decoded token information

        Raises:
            HTTPException: If token is invalid, expired, or wrong type
        """
        try:
            # Decode token
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                audience="balance-tracking-users",
                issuer="balance-tracking-api"
            )

            # Extract required fields
            user_id = payload.get("sub")
            username = payload.get("username")
            email = payload.get("email")
            role_str = payload.get("role", UserRole.USER.value)
            token_type_str = payload.get("token_type")
            issued_at_timestamp = payload.get("iat")
            expires_at_timestamp = payload.get("exp")
            jti = payload.get("jti")

            # Validate required fields
            if not all([user_id, username, token_type_str, issued_at_timestamp, expires_at_timestamp, jti]):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token: missing required fields"
                )

            # Convert timestamps to datetime objects
            issued_at = datetime.fromtimestamp(issued_at_timestamp, tz=timezone.utc)
            expires_at = datetime.fromtimestamp(expires_at_timestamp, tz=timezone.utc)

            # Validate token type
            try:
                token_type = TokenType(token_type_str)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Invalid token type: {token_type_str}"
                )

            # Check expected token type
            if expected_type and token_type != expected_type:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Expected {expected_type.value} token, got {token_type.value}"
                )

            # Validate user role
            try:
                role = UserRole(role_str)
            except ValueError:
                role = UserRole.USER  # Default role if invalid

            # Check if token is expired
            if datetime.now(timezone.utc) > expires_at:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has expired"
                )

            # Create TokenData object
            token_data = TokenData(
                user_id=user_id,
                username=username,
                email=email or "",
                role=role,
                token_type=token_type,
                issued_at=issued_at,
                expires_at=expires_at,
                jti=jti
            )

            logger.debug(f"Successfully validated {token_type.value} token for user {username}")
            return token_data

        except JWTError as e:
            logger.warning(f"JWT validation error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token"
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error validating token: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Token validation failed"
            )

    def get_token_payload(self, token: str) -> Dict[str, Any]:
        """
        Get token payload without validation (for debugging/inspection).

        Args:
            token: JWT token string

        Returns:
            Token payload dictionary

        Note: This method does not validate the token signature or expiration!
        """
        try:
            # Decode without verification (for inspection only)
            payload = jwt.decode(token, options={"verify_signature": False})
            return payload
        except Exception as e:
            logger.error(f"Failed to decode token payload: {e}")
            return {}

    def is_token_expired(self, token: str) -> bool:
        """
        Check if a token is expired without full validation.

        Args:
            token: JWT token string

        Returns:
            True if token is expired, False otherwise
        """
        try:
            payload = self.get_token_payload(token)
            exp_timestamp = payload.get("exp")
            if not exp_timestamp:
                return True

            expires_at = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
            return datetime.now(timezone.utc) > expires_at
        except Exception:
            return True

    def create_token_response(
        self,
        user_id: str,
        username: str,
        email: str,
        role: UserRole = UserRole.USER,
        include_refresh_token: bool = True
    ) -> Token:
        """
        Create a complete token response with access and refresh tokens.

        Args:
            user_id: Unique user identifier
            username: Username
            email: User email address
            role: User role
            include_refresh_token: Whether to include refresh token

        Returns:
            Token response object
        """
        # Create access token
        access_token = self.create_access_token(user_id, username, email, role)

        # Create refresh token if requested
        refresh_token = None
        if include_refresh_token:
            refresh_token = self.create_refresh_token(user_id, username)

        return Token(
            access_token=access_token,
            token_type="bearer",
            expires_in=self.access_token_expire_minutes * 60,  # Convert to seconds
            refresh_token=refresh_token,
            scope="read write"
        )


class PasswordService:
    """
    Password hashing and verification service using bcrypt.
    """

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


# Global service instances
jwt_service = JWTService()
password_service = PasswordService()
