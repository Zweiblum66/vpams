"""API Dependencies for GDPR Compliance Service"""

from typing import Optional, Annotated
from fastapi import Depends, HTTPException, status, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession
from jose import JWTError, jwt
from datetime import datetime
import logging

from ..db.base import get_db_session
from ..core.config import settings
from ..core.security import verify_token

logger = logging.getLogger(__name__)


async def get_db() -> AsyncSession:
    """Get database session"""
    async with get_db_session() as session:
        yield session


async def get_current_user(
    authorization: Annotated[Optional[str], Header()] = None,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Get current authenticated user from JWT token"""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication scheme",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Verify token
        payload = verify_token(token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Check token expiration
        exp = payload.get("exp")
        if exp and datetime.fromtimestamp(exp) < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return {
            "user_id": payload.get("sub"),
            "email": payload.get("email"),
            "roles": payload.get("roles", []),
            "permissions": payload.get("permissions", [])
        }
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError as e:
        logger.error(f"JWT validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def require_admin(
    current_user: dict = Depends(get_current_user)
) -> dict:
    """Require admin role"""
    if "admin" not in current_user.get("roles", []) and \
       "gdpr_admin" not in current_user.get("roles", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


async def require_permission(permission: str):
    """Require specific permission"""
    async def permission_checker(
        current_user: dict = Depends(get_current_user)
    ) -> dict:
        user_permissions = current_user.get("permissions", [])
        if permission not in user_permissions and \
           "gdpr_admin" not in current_user.get("roles", []):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission}' required"
            )
        return current_user
    
    return permission_checker


def get_client_ip(request: Request) -> Optional[str]:
    """Extract client IP address from request"""
    # Check X-Forwarded-For header first (for proxied requests)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Take the first IP in the chain
        return forwarded_for.split(",")[0].strip()
    
    # Check X-Real-IP header
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Fall back to direct client IP
    if request.client:
        return request.client.host
    
    return None


def get_user_agent(request: Request) -> Optional[str]:
    """Extract user agent from request"""
    return request.headers.get("User-Agent")


class RateLimiter:
    """Simple in-memory rate limiter"""
    
    def __init__(self):
        self.requests = {}
    
    async def check_rate_limit(
        self,
        key: str,
        max_requests: int = 100,
        window_seconds: int = 60
    ) -> bool:
        """Check if rate limit is exceeded"""
        now = datetime.utcnow().timestamp()
        
        if key not in self.requests:
            self.requests[key] = []
        
        # Remove old requests outside the window
        self.requests[key] = [
            req_time for req_time in self.requests[key]
            if now - req_time < window_seconds
        ]
        
        # Check if limit exceeded
        if len(self.requests[key]) >= max_requests:
            return False
        
        # Add current request
        self.requests[key].append(now)
        return True


# Global rate limiter instance
rate_limiter = RateLimiter()


async def check_rate_limit(
    request: Request,
    current_user: dict = Depends(get_current_user)
) -> None:
    """Check rate limit for current user"""
    user_id = current_user.get("user_id", "anonymous")
    key = f"user:{user_id}"
    
    # Different limits for different roles
    if "admin" in current_user.get("roles", []):
        max_requests = 1000
    else:
        max_requests = 100
    
    allowed = await rate_limiter.check_rate_limit(key, max_requests=max_requests)
    
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later."
        )