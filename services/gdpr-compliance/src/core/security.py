"""Security utilities for GDPR Compliance Service"""

from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from jose import jwt, JWTError
import secrets
import hashlib
import logging

from .config import settings

logger = logging.getLogger(__name__)


def create_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create JWT token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.jwt_expiration_minutes)
    
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm
    )
    
    return encoded_jwt


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify JWT token and return payload"""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        return payload
    except JWTError as e:
        logger.error(f"Token verification failed: {str(e)}")
        return None


def generate_verification_token() -> str:
    """Generate a secure random verification token"""
    return secrets.token_urlsafe(32)


def generate_request_id() -> str:
    """Generate a unique request ID"""
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    random_part = secrets.token_hex(8)
    return f"GDPR-{timestamp}-{random_part.upper()}"


def hash_password(password: str) -> str:
    """Hash password using SHA-256 (for demo purposes - use bcrypt in production)"""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return hash_password(plain_password) == hashed_password


def mask_email(email: str) -> str:
    """Mask email address for privacy"""
    if "@" not in email:
        return "***"
    
    local, domain = email.split("@", 1)
    if len(local) <= 2:
        masked_local = "*" * len(local)
    else:
        masked_local = local[0] + "*" * (len(local) - 2) + local[-1]
    
    return f"{masked_local}@{domain}"


def mask_ip_address(ip: str) -> str:
    """Mask IP address for privacy"""
    if "." in ip:  # IPv4
        parts = ip.split(".")
        if len(parts) == 4:
            return f"{parts[0]}.{parts[1]}.XXX.XXX"
    elif ":" in ip:  # IPv6
        parts = ip.split(":")
        if len(parts) >= 4:
            return f"{parts[0]}:{parts[1]}:XXXX:XXXX:XXXX:XXXX:XXXX:XXXX"
    
    return "XXX.XXX.XXX.XXX"


def sanitize_user_input(input_str: str, max_length: int = 1000) -> str:
    """Sanitize user input to prevent injection attacks"""
    if not input_str:
        return ""
    
    # Truncate to max length
    sanitized = input_str[:max_length]
    
    # Remove control characters
    sanitized = "".join(char for char in sanitized if ord(char) >= 32 or char in "\n\r\t")
    
    return sanitized.strip()


def is_valid_email(email: str) -> bool:
    """Basic email validation"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def is_strong_password(password: str) -> bool:
    """Check if password meets security requirements"""
    if len(password) < 8:
        return False
    
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)
    
    return has_upper and has_lower and has_digit and has_special


class SecurityHeaders:
    """Security headers for API responses"""
    
    @staticmethod
    def get_headers() -> Dict[str, str]:
        """Get security headers"""
        return {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'",
            "Referrer-Policy": "strict-origin-when-cross-origin"
        }


def encrypt_sensitive_data(data: str) -> str:
    """Encrypt sensitive data (placeholder - implement proper encryption)"""
    # In production, use proper encryption like AES
    # This is just a placeholder
    return hashlib.sha256(data.encode()).hexdigest()


def decrypt_sensitive_data(encrypted_data: str) -> str:
    """Decrypt sensitive data (placeholder - implement proper decryption)"""
    # In production, implement proper decryption
    # This is just a placeholder
    return encrypted_data