"""
FastAPI dependencies for Security Certification Service.
"""
from typing import Generator, Optional
import jwt
from datetime import datetime, timezone
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
import redis.asyncio as redis

from .config import settings
from ..db.models import User

# Database setup
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()

# Redis setup
redis_client = redis.from_url(settings.redis_url, decode_responses=True)

# Security setup
security = HTTPBearer()


async def get_db() -> Generator[AsyncSession, None, None]:
    """Get database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_redis() -> redis.Redis:
    """Get Redis client."""
    return redis_client


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current authenticated user."""
    try:
        # Decode JWT token
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # For demo purposes, create a mock user
        # In production, this would query the database
        user = User(
            id=user_id,
            email=payload.get("email", "user@example.com"),
            full_name=payload.get("name", "Security User"),
            is_active=True
        )
        
        return user
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current active user."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user


def check_permissions(required_permissions: list = None):
    """Check if user has required permissions."""
    def permission_checker(current_user: User = Depends(get_current_active_user)):
        # For demo purposes, assume all active users have all permissions
        # In production, this would check user roles and permissions
        if required_permissions and not current_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return current_user
    return permission_checker


class RateLimiter:
    """Rate limiting dependency."""
    
    def __init__(self, calls: int = 100, period: int = 60):
        self.calls = calls
        self.period = period
    
    async def __call__(
        self,
        request_ip: str,
        redis_client: redis.Redis = Depends(get_redis)
    ):
        """Check rate limit for IP address."""
        key = f"rate_limit:{request_ip}"
        
        # Get current count
        current = await redis_client.get(key)
        
        if current is None:
            # First request from this IP
            await redis_client.setex(key, self.period, 1)
            return
        
        if int(current) >= self.calls:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded"
            )
        
        # Increment counter
        await redis_client.incr(key)


# Pre-configured rate limiters
standard_rate_limit = RateLimiter(calls=100, period=60)
strict_rate_limit = RateLimiter(calls=10, period=60)


async def validate_audit_permissions(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """Validate user has audit permissions."""
    # In production, check specific audit permissions
    return current_user


async def validate_compliance_permissions(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """Validate user has compliance management permissions."""
    # In production, check specific compliance permissions
    return current_user


async def validate_admin_permissions(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """Validate user has admin permissions."""
    # In production, check admin role
    return current_user


class CacheManager:
    """Cache management dependency."""
    
    def __init__(self, ttl: int = 3600):
        self.ttl = ttl
    
    async def get(self, key: str, redis_client: redis.Redis = Depends(get_redis)):
        """Get cached value."""
        return await redis_client.get(key)
    
    async def set(self, key: str, value: str, redis_client: redis.Redis = Depends(get_redis)):
        """Set cached value."""
        await redis_client.setex(key, self.ttl, value)
    
    async def delete(self, key: str, redis_client: redis.Redis = Depends(get_redis)):
        """Delete cached value."""
        await redis_client.delete(key)


# Pre-configured cache managers
compliance_cache = CacheManager(ttl=settings.compliance_cache_ttl)
scan_cache = CacheManager(ttl=1800)  # 30 minutes