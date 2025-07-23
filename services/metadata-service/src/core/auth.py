"""
Authentication and authorization utilities
"""

from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from uuid import UUID
import structlog

from .config import settings
from .exceptions import AuthenticationError, AuthorizationError

logger = structlog.get_logger()

# Security scheme
security = HTTPBearer()


class JWTHandler:
    """JWT token handler"""
    
    def __init__(self):
        self.secret_key = settings.JWT_SECRET_KEY
        self.algorithm = settings.JWT_ALGORITHM
        self.expiration_minutes = settings.JWT_EXPIRATION_MINUTES
    
    def encode_token(self, user_id: UUID, additional_claims: Dict[str, Any] = None) -> str:
        """Encode JWT token"""
        payload = {
            "user_id": str(user_id),
            "exp": datetime.utcnow() + timedelta(minutes=self.expiration_minutes),
            "iat": datetime.utcnow(),
            "type": "access"
        }
        
        if additional_claims:
            payload.update(additional_claims)
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def decode_token(self, token: str) -> Dict[str, Any]:
        """Decode JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Check if token has expired
            if datetime.utcnow() > datetime.fromtimestamp(payload.get("exp", 0)):
                raise AuthenticationError("Token has expired")
            
            return payload
            
        except JWTError as e:
            raise AuthenticationError(f"Invalid token: {str(e)}")
    
    def verify_token(self, token: str) -> bool:
        """Verify if token is valid"""
        try:
            self.decode_token(token)
            return True
        except AuthenticationError:
            return False


# Global JWT handler instance
jwt_handler = JWTHandler()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """
    Get current user from JWT token
    
    This is a simplified version for development.
    In production, this should validate against the User Management Service.
    """
    try:
        token = credentials.credentials
        payload = jwt_handler.decode_token(token)
        
        # Extract user information from token
        user_id = payload.get("user_id")
        if not user_id:
            raise AuthenticationError("Invalid token: missing user_id")
        
        # For now, return a mock user object
        # In production, this would query the User Management Service
        user = {
            "user_id": UUID(user_id),
            "username": payload.get("username", "user"),
            "email": payload.get("email", "user@example.com"),
            "roles": payload.get("roles", ["user"]),
            "permissions": payload.get("permissions", [])
        }
        
        return user
        
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"}
        )
    except Exception as e:
        logger.error("Authentication error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )


async def get_current_admin_user(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Get current user with admin privileges"""
    if "admin" not in current_user.get("roles", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user


def require_permission(permission: str):
    """Decorator to require specific permission"""
    def decorator(current_user: Dict[str, Any] = Depends(get_current_user)):
        if permission not in current_user.get("permissions", []):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission required: {permission}"
            )
        return current_user
    return decorator


async def verify_api_key(api_key: str) -> bool:
    """
    Verify API key
    
    This is a placeholder implementation.
    In production, this should validate against a secure API key store.
    """
    # TODO: Implement proper API key validation
    return api_key == "dev-api-key"


class APIKeyAuth:
    """API Key authentication"""
    
    def __init__(self, api_key_header: str = "X-API-Key"):
        self.api_key_header = api_key_header
    
    async def __call__(self, request) -> Dict[str, Any]:
        """Validate API key from request headers"""
        api_key = request.headers.get(self.api_key_header)
        
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key required"
            )
        
        if not await verify_api_key(api_key):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key"
            )
        
        # Return a service user for API key authentication
        return {
            "user_id": UUID("00000000-0000-0000-0000-000000000000"),
            "username": "api_service",
            "email": "api@service.local",
            "roles": ["service"],
            "permissions": ["*"]
        }


# API key authentication instance
api_key_auth = APIKeyAuth()


async def get_current_user_or_service(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    request=None
) -> Dict[str, Any]:
    """
    Get current user from JWT token or API key
    
    This allows both JWT and API key authentication.
    """
    # Try JWT authentication first
    if credentials:
        return await get_current_user(credentials)
    
    # Try API key authentication
    if request:
        return await api_key_auth(request)
    
    # No authentication provided
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required"
    )


def create_access_token(user_id: UUID, additional_claims: Dict[str, Any] = None) -> str:
    """Create access token for user"""
    return jwt_handler.encode_token(user_id, additional_claims)


def verify_token(token: str) -> bool:
    """Verify if token is valid"""
    return jwt_handler.verify_token(token)


def decode_token(token: str) -> Dict[str, Any]:
    """Decode token and return payload"""
    return jwt_handler.decode_token(token)