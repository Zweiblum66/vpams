"""
FastAPI dependencies for SLA Management Service.
"""
from typing import Generator
import jwt
from datetime import datetime, timezone
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
import redis.asyncio as redis

from .config import settings
from ..db.models import Customer

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
) -> Customer:
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
        
        # For demo purposes, create a mock customer
        # In production, this would query the database
        customer = Customer(
            id=user_id,
            customer_id=payload.get("customer_id", "demo_customer"),
            company_name=payload.get("company", "Demo Company"),
            contact_email=payload.get("email", "user@example.com"),
            contact_name=payload.get("name", "Demo User"),
            is_active=True
        )
        
        return customer
        
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


async def get_current_active_customer(
    current_customer: Customer = Depends(get_current_user)
) -> Customer:
    """Get current active customer."""
    if not current_customer.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive customer"
        )
    return current_customer


def check_sla_permissions(required_permissions: list = None):
    """Check if customer has required SLA permissions."""
    def permission_checker(current_customer: Customer = Depends(get_current_active_customer)):
        # For demo purposes, assume all active customers have all permissions
        # In production, this would check customer roles and permissions
        if required_permissions and not current_customer.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return current_customer
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
        key = f"sla_rate_limit:{request_ip}"
        
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


class CacheManager:
    """Cache management dependency."""
    
    def __init__(self, ttl: int = 300):
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


# Pre-configured dependencies
standard_rate_limit = RateLimiter(calls=settings.rate_limit_per_minute, period=60)
strict_rate_limit = RateLimiter(calls=10, period=60)
sla_cache = CacheManager(ttl=settings.cache_ttl_seconds)
compliance_cache = CacheManager(ttl=settings.compliance_cache_ttl_seconds)


async def validate_sla_admin_permissions(
    current_customer: Customer = Depends(get_current_active_customer)
) -> Customer:
    """Validate customer has SLA admin permissions."""
    # In production, check specific SLA admin permissions
    return current_customer


async def validate_sla_read_permissions(
    current_customer: Customer = Depends(get_current_active_customer)
) -> Customer:
    """Validate customer has SLA read permissions."""
    # In production, check specific SLA read permissions
    return current_customer


async def validate_compliance_permissions(
    current_customer: Customer = Depends(get_current_active_customer)
) -> Customer:
    """Validate customer has compliance management permissions."""
    # In production, check specific compliance permissions
    return current_customer