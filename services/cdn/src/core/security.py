"""
Security utilities for CDN service
"""

from typing import List, Optional
from fastapi import HTTPException, status
from passlib.context import CryptContext
import jwt
from datetime import datetime, timedelta

from ..core.config import settings
from ..models.database import User

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash password"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
    return encoded_jwt


async def require_permission(user: User, permission: str):
    """Check if user has required permission"""
    # In a real implementation, check user permissions from database
    # For now, allow all permissions for authenticated users
    user_permissions = [
        "cdn.read",
        "cdn.create",
        "cdn.update",
        "cdn.delete",
        "cdn.purge",
        "cdn.prefetch"
    ]
    
    if permission not in user_permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User does not have permission: {permission}"
        )


async def require_permissions(user: User, permissions: List[str]):
    """Check if user has all required permissions"""
    for permission in permissions:
        await require_permission(user, permission)


def validate_api_key(api_key: str) -> bool:
    """Validate API key"""
    # In a real implementation, validate against database
    # For now, simple check
    return api_key == settings.SECRET_KEY


def generate_cdn_token(
    distribution_id: str,
    expires_in: int = 3600,
    allowed_ips: Optional[List[str]] = None,
    allowed_paths: Optional[List[str]] = None
) -> str:
    """Generate CDN access token for signed URLs"""
    payload = {
        "distribution_id": distribution_id,
        "exp": datetime.utcnow().timestamp() + expires_in,
        "iat": datetime.utcnow().timestamp(),
    }
    
    if allowed_ips:
        payload["allowed_ips"] = allowed_ips
    
    if allowed_paths:
        payload["allowed_paths"] = allowed_paths
    
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return token


def verify_cdn_token(token: str, distribution_id: str, client_ip: str, path: str) -> bool:
    """Verify CDN access token"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        
        # Check distribution ID
        if payload.get("distribution_id") != distribution_id:
            return False
        
        # Check expiration
        if datetime.utcnow().timestamp() > payload.get("exp", 0):
            return False
        
        # Check allowed IPs
        allowed_ips = payload.get("allowed_ips")
        if allowed_ips and client_ip not in allowed_ips:
            return False
        
        # Check allowed paths
        allowed_paths = payload.get("allowed_paths")
        if allowed_paths:
            path_allowed = any(path.startswith(allowed_path) for allowed_path in allowed_paths)
            if not path_allowed:
                return False
        
        return True
        
    except jwt.PyJWTError:
        return False


def generate_signed_url(
    base_url: str,
    path: str,
    expires_in: int = 3600,
    allowed_ips: Optional[List[str]] = None
) -> str:
    """Generate signed URL for CDN content"""
    # Extract distribution ID from URL
    from urllib.parse import urlparse
    parsed = urlparse(base_url)
    distribution_id = parsed.hostname.split('.')[0]
    
    # Generate token
    token = generate_cdn_token(
        distribution_id=distribution_id,
        expires_in=expires_in,
        allowed_ips=allowed_ips,
        allowed_paths=[path]
    )
    
    # Build signed URL
    separator = "&" if "?" in path else "?"
    signed_url = f"{base_url}{path}{separator}token={token}"
    
    return signed_url