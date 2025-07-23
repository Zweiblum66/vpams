"""Authentication and authorization for Partner APIs"""

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import hashlib
import hmac
import time
from typing import Optional
import logging

from .config import settings
from .database import get_db
from ..db.models import APIKey as APIKeyModel, APIKeyStatusEnum

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)


class APIKey:
    """API key model for authentication"""
    def __init__(
        self,
        id: str,
        partner_id: str,
        key_id: str,
        name: str,
        status: str,
        tier: str,
        scopes: list,
        allowed_features: list,
        allowed_api_versions: list,
        rate_limit: str,
        burst_limit: int
    ):
        self.id = id
        self.partner_id = partner_id
        self.key_id = key_id
        self.name = name
        self.status = status
        self.tier = tier
        self.scopes = scopes
        self.allowed_features = allowed_features
        self.allowed_api_versions = allowed_api_versions
        self.rate_limit = rate_limit
        self.burst_limit = burst_limit


async def get_api_key(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> APIKey:
    """Get and validate API key from request"""
    
    # Extract API key from various sources
    api_key_value = None
    
    if credentials:
        api_key_value = credentials.credentials
    else:
        # Check X-API-Key header
        api_key_value = request.headers.get("X-API-Key")
        
        # Check query parameter
        if not api_key_value:
            api_key_value = request.query_params.get("api_key")
    
    if not api_key_value:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required"
        )
    
    # Parse key ID from API key
    if not api_key_value.startswith(settings.api_key_prefix):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key format"
        )
    
    try:
        # Extract key ID (part before the hash)
        key_parts = api_key_value[len(settings.api_key_prefix):].split("_")
        if len(key_parts) < 2:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key format"
            )
        
        key_id = f"{settings.api_key_prefix}{key_parts[0]}"
        
        # Look up API key in database
        stmt = select(APIKeyModel).where(APIKeyModel.key_id == key_id)
        result = await db.execute(stmt)
        api_key_record = result.scalar_one_or_none()
        
        if not api_key_record:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key"
            )
        
        # Verify API key hash
        if not verify_api_key(api_key_value, api_key_record.key_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key"
            )
        
        # Check API key status
        if api_key_record.status != APIKeyStatusEnum.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"API key is {api_key_record.status}"
            )
        
        # Check expiration
        if api_key_record.expires_at and api_key_record.expires_at < time.time():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key has expired"
            )
        
        # Update last used timestamp
        api_key_record.last_used_at = time.time()
        await db.commit()
        
        # Return API key object
        return APIKey(
            id=str(api_key_record.id),
            partner_id=str(api_key_record.partner_id),
            key_id=api_key_record.key_id,
            name=api_key_record.name,
            status=api_key_record.status,
            tier=api_key_record.tier,
            scopes=api_key_record.scopes or ["read"],
            allowed_features=api_key_record.allowed_features or ["assets"],
            allowed_api_versions=api_key_record.allowed_api_versions or ["v1"],
            rate_limit=api_key_record.rate_limit or settings.default_rate_limit,
            burst_limit=api_key_record.burst_limit or settings.default_burst_limit
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating API key: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )


async def get_admin_api_key(api_key: APIKey = Depends(get_api_key)) -> APIKey:
    """Require admin scope for API key"""
    if "admin" not in api_key.scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return api_key


async def get_write_api_key(api_key: APIKey = Depends(get_api_key)) -> APIKey:
    """Require write scope for API key"""
    if "write" not in api_key.scopes and "admin" not in api_key.scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Write access required"
        )
    return api_key


def generate_api_key(partner_id: str, key_name: str) -> tuple[str, str, str]:
    """Generate a new API key"""
    
    import secrets
    import uuid
    
    # Generate key ID
    key_id = f"{settings.api_key_prefix}{secrets.token_hex(8)}"
    
    # Generate secret part
    secret = secrets.token_hex(16)
    
    # Combine to create full API key
    api_key = f"{key_id}_{secret}"
    
    # Generate hash for storage
    key_hash = hash_api_key(api_key)
    
    return api_key, key_id, key_hash


def hash_api_key(api_key: str) -> str:
    """Hash an API key for secure storage"""
    return hashlib.sha256(api_key.encode()).hexdigest()


def verify_api_key(api_key: str, stored_hash: str) -> bool:
    """Verify an API key against stored hash"""
    return hmac.compare_digest(hash_api_key(api_key), stored_hash)


def check_ip_whitelist(request: Request, allowed_ips: Optional[list]) -> bool:
    """Check if request IP is in whitelist"""
    if not allowed_ips:
        return True
    
    client_ip = get_client_ip(request)
    return client_ip in allowed_ips


def check_domain_whitelist(request: Request, allowed_domains: Optional[list]) -> bool:
    """Check if request domain is in whitelist"""
    if not allowed_domains:
        return True
    
    origin = request.headers.get("Origin")
    referer = request.headers.get("Referer")
    
    if origin:
        domain = origin.replace("http://", "").replace("https://", "").split("/")[0]
        return domain in allowed_domains
    
    if referer:
        domain = referer.replace("http://", "").replace("https://", "").split("/")[0]
        return domain in allowed_domains
    
    return True


def get_client_ip(request: Request) -> str:
    """Get client IP address"""
    # Check for forwarded IP (behind proxy)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    
    # Check for real IP header
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Fall back to direct connection IP
    return request.client.host if request.client else "unknown"


def validate_api_version(api_key: APIKey, requested_version: str) -> bool:
    """Validate that API key has access to requested version"""
    return requested_version in api_key.allowed_api_versions


def validate_feature_access(api_key: APIKey, feature: str) -> bool:
    """Validate that API key has access to requested feature"""
    return feature in api_key.allowed_features or "*" in api_key.allowed_features


def validate_scope_access(api_key: APIKey, required_scope: str) -> bool:
    """Validate that API key has required scope"""
    return required_scope in api_key.scopes or "admin" in api_key.scopes