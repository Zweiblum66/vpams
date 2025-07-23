"""
Security utilities for API Gateway

JWT token handling, password hashing, and security validation utilities.
"""

import hashlib
import hmac
import secrets
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from jose import JWTError, jwt
from passlib.context import CryptContext
from passlib.hash import bcrypt

from .config import get_settings
from .exceptions import InvalidTokenException, AuthenticationException

settings = get_settings()

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class TokenManager:
    """JWT token management"""
    
    def __init__(self):
        self.secret_key = settings.secret_key
        self.algorithm = settings.jwt_algorithm
        self.access_token_expire_minutes = settings.jwt_expiration_minutes
        self.refresh_token_expire_days = settings.refresh_token_expiration_days
    
    def create_access_token(
        self,
        subject: str,
        user_id: str,
        permissions: List[str] = None,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create a new access token
        
        Args:
            subject: Token subject (usually username or email)
            user_id: User ID
            permissions: List of user permissions
            expires_delta: Custom expiration time
            
        Returns:
            JWT token string
        """
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        
        to_encode = {
            "sub": subject,
            "user_id": user_id,
            "permissions": permissions or [],
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access"
        }
        
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
    
    def create_refresh_token(
        self,
        subject: str,
        user_id: str,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create a new refresh token
        
        Args:
            subject: Token subject
            user_id: User ID
            expires_delta: Custom expiration time
            
        Returns:
            JWT refresh token string
        """
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)
        
        to_encode = {
            "sub": subject,
            "user_id": user_id,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh"
        }
        
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
    
    def decode_token(self, token: str) -> Dict[str, Any]:
        """
        Decode and validate JWT token
        
        Args:
            token: JWT token string
            
        Returns:
            Token payload
            
        Raises:
            InvalidTokenException: If token is invalid or expired
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except JWTError as e:
            raise InvalidTokenException(f"Invalid token: {str(e)}")
    
    def verify_token(self, token: str, token_type: str = "access") -> Dict[str, Any]:
        """
        Verify token and check type
        
        Args:
            token: JWT token string
            token_type: Expected token type ('access' or 'refresh')
            
        Returns:
            Token payload
            
        Raises:
            InvalidTokenException: If token is invalid, expired, or wrong type
        """
        payload = self.decode_token(token)
        
        if payload.get("type") != token_type:
            raise InvalidTokenException(f"Invalid token type. Expected {token_type}")
        
        return payload
    
    def is_token_expired(self, token: str) -> bool:
        """
        Check if token is expired
        
        Args:
            token: JWT token string
            
        Returns:
            True if token is expired, False otherwise
        """
        try:
            payload = self.decode_token(token)
            exp = payload.get("exp")
            if exp is None:
                return True
            
            return datetime.utcnow() > datetime.fromtimestamp(exp)
        except InvalidTokenException:
            return True


class PasswordManager:
    """Password hashing and verification"""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash a password
        
        Args:
            password: Plain text password
            
        Returns:
            Hashed password
        """
        return pwd_context.hash(password)
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password against its hash
        
        Args:
            plain_password: Plain text password
            hashed_password: Hashed password
            
        Returns:
            True if password matches, False otherwise
        """
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def generate_password(length: int = 12) -> str:
        """
        Generate a secure random password
        
        Args:
            length: Password length
            
        Returns:
            Random password string
        """
        import string
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        return ''.join(secrets.choice(alphabet) for _ in range(length))


class APIKeyManager:
    """API key management and validation"""
    
    @staticmethod
    def generate_api_key() -> str:
        """
        Generate a new API key
        
        Returns:
            API key string
        """
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def hash_api_key(api_key: str) -> str:
        """
        Hash an API key for storage
        
        Args:
            api_key: API key string
            
        Returns:
            Hashed API key
        """
        return hashlib.sha256(api_key.encode()).hexdigest()
    
    @staticmethod
    def verify_api_key(api_key: str, hashed_key: str) -> bool:
        """
        Verify an API key against its hash
        
        Args:
            api_key: API key string
            hashed_key: Hashed API key
            
        Returns:
            True if API key matches, False otherwise
        """
        return hmac.compare_digest(
            hashlib.sha256(api_key.encode()).hexdigest(),
            hashed_key
        )


class SecurityValidator:
    """Security validation utilities"""
    
    @staticmethod
    def validate_password_strength(password: str) -> Dict[str, Any]:
        """
        Validate password strength
        
        Args:
            password: Password to validate
            
        Returns:
            Dictionary with validation results
        """
        result = {
            "is_valid": True,
            "errors": [],
            "strength": "weak"
        }
        
        # Check length
        if len(password) < 8:
            result["is_valid"] = False
            result["errors"].append("Password must be at least 8 characters long")
        
        # Check for uppercase letter
        if not any(c.isupper() for c in password):
            result["is_valid"] = False
            result["errors"].append("Password must contain at least one uppercase letter")
        
        # Check for lowercase letter
        if not any(c.islower() for c in password):
            result["is_valid"] = False
            result["errors"].append("Password must contain at least one lowercase letter")
        
        # Check for digit
        if not any(c.isdigit() for c in password):
            result["is_valid"] = False
            result["errors"].append("Password must contain at least one digit")
        
        # Check for special character
        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        if not any(c in special_chars for c in password):
            result["is_valid"] = False
            result["errors"].append("Password must contain at least one special character")
        
        # Determine strength
        if result["is_valid"]:
            if len(password) >= 12:
                result["strength"] = "strong"
            elif len(password) >= 10:
                result["strength"] = "medium"
            else:
                result["strength"] = "weak"
        
        return result
    
    @staticmethod
    def sanitize_input(input_string: str) -> str:
        """
        Sanitize input string to prevent XSS and injection attacks
        
        Args:
            input_string: String to sanitize
            
        Returns:
            Sanitized string
        """
        import html
        import re
        
        # HTML escape
        sanitized = html.escape(input_string)
        
        # Remove potentially dangerous patterns
        dangerous_patterns = [
            r'<script[^>]*>.*?</script>',
            r'javascript:',
            r'onload=',
            r'onerror=',
            r'onclick=',
            r'onmouseover=',
        ]
        
        for pattern in dangerous_patterns:
            sanitized = re.sub(pattern, '', sanitized, flags=re.IGNORECASE)
        
        return sanitized
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """
        Validate email address format
        
        Args:
            email: Email address to validate
            
        Returns:
            True if valid, False otherwise
        """
        import re
        
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    @staticmethod
    def check_rate_limit_key(key: str, max_requests: int, window_seconds: int) -> bool:
        """
        Check if rate limit key is within limits
        
        Args:
            key: Rate limit key
            max_requests: Maximum requests allowed
            window_seconds: Time window in seconds
            
        Returns:
            True if within limits, False otherwise
        """
        # This would typically use Redis for distributed rate limiting
        # For now, return True as a placeholder
        return True


# Global instances
token_manager = TokenManager()
password_manager = PasswordManager()
api_key_manager = APIKeyManager()
security_validator = SecurityValidator()