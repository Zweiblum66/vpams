"""API dependencies for playout integration service"""

from typing import Optional, AsyncGenerator
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
import jwt
import logging

from ..db.base import get_db
from ..core.config import settings
from ..services.playout_service import playout_service

logger = logging.getLogger(__name__)

# Security scheme
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """Get current user from JWT token"""
    if not credentials:
        if settings.development_mode:
            # Return mock user for development
            return {
                "id": "00000000-0000-0000-0000-000000000001",
                "username": "dev-user",
                "roles": ["admin"]
            }
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        # Decode JWT token
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )
        
        # TODO: Verify user exists in database
        # For now, return decoded user info
        return {
            "id": user_id,
            "username": payload.get("username"),
            "roles": payload.get("roles", [])
        }
        
    except jwt.PyJWTError as e:
        logger.error(f"JWT validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )


async def get_current_admin_user(
    current_user: dict = Depends(get_current_user)
):
    """Require admin role"""
    if "admin" not in current_user.get("roles", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required"
        )
    return current_user


def get_playout_service():
    """Get playout service instance"""
    return playout_service


class CommonQueryParams:
    """Common query parameters"""
    def __init__(
        self,
        skip: int = 0,
        limit: int = 100,
        sort_by: Optional[str] = None,
        sort_order: str = "asc"
    ):
        self.skip = max(0, skip)
        self.limit = min(1000, max(1, limit))
        self.sort_by = sort_by
        self.sort_order = sort_order.lower() if sort_order.lower() in ["asc", "desc"] else "asc"


# Request ID middleware helper
def get_request_id(request: Request) -> str:
    """Get request ID from header or generate one"""
    return request.headers.get("X-Request-ID", "unknown")


# Rate limiting helper (placeholder)
async def rate_limit_check(
    request: Request,
    calls_per_minute: int = 60
):
    """Basic rate limiting check (placeholder implementation)"""
    # TODO: Implement Redis-based rate limiting
    client_ip = request.client.host
    # For now, just log the request
    logger.debug(f"Request from {client_ip}")
    return True


# Health check dependencies
async def check_database_health(db: AsyncSession = Depends(get_db)):
    """Check database connectivity"""
    try:
        await db.execute("SELECT 1")
        return {"database": "healthy"}
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {"database": "unhealthy", "error": str(e)}


def validate_uuid(uuid_str: str, field_name: str = "ID") -> str:
    """Validate UUID format"""
    import uuid
    try:
        uuid.UUID(uuid_str)
        return uuid_str
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid {field_name} format"
        )


# Pagination helpers
def get_pagination_info(skip: int, limit: int, total: int):
    """Calculate pagination info"""
    total_pages = (total + limit - 1) // limit
    current_page = (skip // limit) + 1
    
    return {
        "page": current_page,
        "per_page": limit,
        "total": total,
        "pages": total_pages,
        "has_next": current_page < total_pages,
        "has_prev": current_page > 1
    }