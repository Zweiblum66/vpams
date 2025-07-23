"""
Security utilities for User Management Service

This module provides security-related functions including password hashing,
JWT token management, and cryptographic operations.
"""

import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from pydantic import BaseModel
import secrets
import hashlib
from uuid import UUID
import logging

from .config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class TokenData(BaseModel):
    """Token data model"""
    sub: str
    exp: datetime
    iat: datetime
    type: str = "access"


def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt
    
    Args:
        password: Plain text password
        
    Returns:
        Hashed password string
    """
    try:
        # Generate salt and hash password
        salt = bcrypt.gensalt(rounds=12)  # 12 rounds is secure and performant
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    except Exception as e:
        logger.error(f"Error hashing password: {e}")
        raise


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash
    
    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password to compare against
        
    Returns:
        True if password matches, False otherwise
    """
    try:
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )
    except Exception as e:
        logger.error(f"Error verifying password: {e}")
        return False


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT access token
    
    Args:
        data: Data to encode in token
        expires_delta: Token expiration time
        
    Returns:
        JWT token string
    """
    try:
        to_encode = data.copy()
        
        # Set expiration time
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(
                minutes=settings.jwt_expiration_minutes
            )
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "type": "access"
        })
        
        # Create token
        encoded_jwt = jwt.encode(
            to_encode,
            settings.secret_key,
            algorithm=settings.jwt_algorithm
        )
        
        return encoded_jwt
        
    except Exception as e:
        logger.error(f"Error creating access token: {e}")
        raise


def create_refresh_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT refresh token
    
    Args:
        data: Data to encode in token
        expires_delta: Token expiration time
        
    Returns:
        JWT refresh token string
    """
    try:
        to_encode = data.copy()
        
        # Set expiration time
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(
                days=settings.refresh_token_expiration_days
            )
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "type": "refresh"
        })
        
        # Create token
        encoded_jwt = jwt.encode(
            to_encode,
            settings.secret_key,
            algorithm=settings.jwt_algorithm
        )
        
        return encoded_jwt
        
    except Exception as e:
        logger.error(f"Error creating refresh token: {e}")
        raise


def verify_token(token: str) -> Optional[TokenData]:
    """
    Verify and decode JWT token
    
    Args:
        token: JWT token to verify
        
    Returns:
        TokenData if valid, None otherwise
    """
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        
        return TokenData(
            sub=payload.get("sub"),
            exp=datetime.fromtimestamp(payload.get("exp"), tz=timezone.utc),
            iat=datetime.fromtimestamp(payload.get("iat"), tz=timezone.utc),
            type=payload.get("type", "access")
        )
        
    except jwt.ExpiredSignatureError:
        logger.warning("Token has expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {e}")
        return None
    except Exception as e:
        logger.error(f"Error verifying token: {e}")
        return None


def generate_verification_token(user_id: str) -> str:
    """
    Generate email verification token
    
    Args:
        user_id: User ID to encode in token
        
    Returns:
        Verification token string
    """
    try:
        data = {
            "sub": user_id,
            "type": "email_verification"
        }
        
        expire = datetime.now(timezone.utc) + timedelta(
            hours=settings.email_verification_expires_hours
        )
        
        data.update({
            "exp": expire,
            "iat": datetime.now(timezone.utc)
        })
        
        token = jwt.encode(
            data,
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM
        )
        
        return token
        
    except Exception as e:
        logger.error(f"Error generating verification token: {e}")
        raise


def verify_verification_token(token: str) -> Optional[str]:
    """
    Verify email verification token
    
    Args:
        token: Verification token to verify
        
    Returns:
        User ID if valid, None otherwise
    """
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        
        # Check token type
        if payload.get("type") != "email_verification":
            return None
        
        return payload.get("sub")
        
    except jwt.ExpiredSignatureError:
        logger.warning("Verification token has expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid verification token: {e}")
        return None
    except Exception as e:
        logger.error(f"Error verifying verification token: {e}")
        return None


def generate_reset_token(user_id: str) -> str:
    """
    Generate password reset token
    
    Args:
        user_id: User ID to encode in token
        
    Returns:
        Reset token string
    """
    try:
        data = {
            "sub": user_id,
            "type": "password_reset"
        }
        
        expire = datetime.now(timezone.utc) + timedelta(
            hours=settings.password_reset_expires_hours
        )
        
        data.update({
            "exp": expire,
            "iat": datetime.now(timezone.utc)
        })
        
        token = jwt.encode(
            data,
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM
        )
        
        return token
        
    except Exception as e:
        logger.error(f"Error generating reset token: {e}")
        raise


def verify_reset_token(token: str) -> Optional[str]:
    """
    Verify password reset token
    
    Args:
        token: Reset token to verify
        
    Returns:
        User ID if valid, None otherwise
    """
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        
        # Check token type
        if payload.get("type") != "password_reset":
            return None
        
        return payload.get("sub")
        
    except jwt.ExpiredSignatureError:
        logger.warning("Reset token has expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid reset token: {e}")
        return None
    except Exception as e:
        logger.error(f"Error verifying reset token: {e}")
        return None


def generate_secure_token(length: int = 32) -> str:
    """
    Generate cryptographically secure random token
    
    Args:
        length: Token length in bytes
        
    Returns:
        Secure token string
    """
    try:
        return secrets.token_urlsafe(length)
    except Exception as e:
        logger.error(f"Error generating secure token: {e}")
        raise


def generate_api_key(user_id: UUID, name: str) -> str:
    """
    Generate API key for user
    
    Args:
        user_id: User ID
        name: API key name
        
    Returns:
        API key string
    """
    try:
        # Create unique identifier
        unique_data = f"{user_id}:{name}:{datetime.now(timezone.utc).isoformat()}"
        
        # Generate hash
        hash_object = hashlib.sha256(unique_data.encode())
        hash_hex = hash_object.hexdigest()
        
        # Create API key with prefix
        api_key = f"mams_{hash_hex[:32]}"
        
        return api_key
        
    except Exception as e:
        logger.error(f"Error generating API key: {e}")
        raise


def hash_api_key(api_key: str) -> str:
    """
    Hash API key for storage
    
    Args:
        api_key: API key to hash
        
    Returns:
        Hashed API key
    """
    try:
        return hashlib.sha256(api_key.encode()).hexdigest()
    except Exception as e:
        logger.error(f"Error hashing API key: {e}")
        raise


def verify_api_key(api_key: str, hashed_key: str) -> bool:
    """
    Verify API key against hash
    
    Args:
        api_key: API key to verify
        hashed_key: Hashed API key to compare against
        
    Returns:
        True if valid, False otherwise
    """
    try:
        return hashlib.sha256(api_key.encode()).hexdigest() == hashed_key
    except Exception as e:
        logger.error(f"Error verifying API key: {e}")
        return False


def check_password_strength(password: str) -> Dict[str, Any]:
    """
    Check password strength and return analysis
    
    Args:
        password: Password to analyze
        
    Returns:
        Dictionary with strength analysis
    """
    try:
        analysis = {
            "length": len(password),
            "has_upper": any(c.isupper() for c in password),
            "has_lower": any(c.islower() for c in password),
            "has_digit": any(c.isdigit() for c in password),
            "has_special": any(c in "!@#$%^&*(),.?\":{}|<>" for c in password),
            "strength": "weak"
        }
        
        # Calculate strength score
        score = 0
        if analysis["length"] >= 8:
            score += 1
        if analysis["length"] >= 12:
            score += 1
        if analysis["has_upper"]:
            score += 1
        if analysis["has_lower"]:
            score += 1
        if analysis["has_digit"]:
            score += 1
        if analysis["has_special"]:
            score += 1
        
        # Determine strength
        if score >= 5:
            analysis["strength"] = "strong"
        elif score >= 3:
            analysis["strength"] = "medium"
        else:
            analysis["strength"] = "weak"
        
        analysis["score"] = score
        return analysis
        
    except Exception as e:
        logger.error(f"Error checking password strength: {e}")
        return {"strength": "unknown", "score": 0}


def generate_session_id() -> str:
    """
    Generate unique session ID
    
    Returns:
        Session ID string
    """
    try:
        return secrets.token_urlsafe(32)
    except Exception as e:
        logger.error(f"Error generating session ID: {e}")
        raise


def constant_time_compare(val1: str, val2: str) -> bool:
    """
    Compare two strings in constant time to prevent timing attacks
    
    Args:
        val1: First string
        val2: Second string
        
    Returns:
        True if strings are equal, False otherwise
    """
    try:
        return secrets.compare_digest(val1, val2)
    except Exception as e:
        logger.error(f"Error in constant time compare: {e}")
        return False


def mask_sensitive_data(data: str, mask_char: str = "*", show_chars: int = 4) -> str:
    """
    Mask sensitive data for logging
    
    Args:
        data: Data to mask
        mask_char: Character to use for masking
        show_chars: Number of characters to show at end
        
    Returns:
        Masked string
    """
    try:
        if len(data) <= show_chars:
            return mask_char * len(data)
        
        return mask_char * (len(data) - show_chars) + data[-show_chars:]
        
    except Exception as e:
        logger.error(f"Error masking sensitive data: {e}")
        return mask_char * 8