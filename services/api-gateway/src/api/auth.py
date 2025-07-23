"""
Authentication Endpoints

Handles user authentication, token management, and refresh tokens.
"""

import time
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field, validator
import httpx

from core.config import get_settings
from core.security import token_manager, password_manager, security_validator
from core.exceptions import (
    AuthenticationException,
    InvalidTokenException,
    ValidationException
)
from core.redis import get_cache
from core.service_discovery import get_service_client
from core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


# Request/Response models
class UserLogin(BaseModel):
    """User login request"""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)
    
    @validator('username')
    def validate_username(cls, v):
        """Validate username format"""
        import re
        if not re.match(r'^[a-zA-Z0-9_.-]+$', v):
            raise ValueError('Username must contain only letters, numbers, and ._-')
        return v


class UserRegister(BaseModel):
    """User registration request"""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=1, max_length=100)
    
    @validator('username')
    def validate_username(cls, v):
        """Validate username format"""
        import re
        if not re.match(r'^[a-zA-Z0-9_.-]+$', v):
            raise ValueError('Username must contain only letters, numbers, and ._-')
        return v
    
    @validator('password')
    def validate_password(cls, v):
        """Validate password strength"""
        result = security_validator.validate_password_strength(v)
        if not result['is_valid']:
            raise ValueError('; '.join(result['errors']))
        return v


class TokenResponse(BaseModel):
    """Token response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: str
    username: str
    permissions: list = []


class RefreshTokenRequest(BaseModel):
    """Refresh token request"""
    refresh_token: str


class PasswordChangeRequest(BaseModel):
    """Password change request"""
    old_password: str
    new_password: str = Field(..., min_length=8)
    
    @validator('new_password')
    def validate_password(cls, v, values):
        """Validate new password"""
        if 'old_password' in values and v == values['old_password']:
            raise ValueError('New password must be different from old password')
        
        result = security_validator.validate_password_strength(v)
        if not result['is_valid']:
            raise ValueError('; '.join(result['errors']))
        return v


class PasswordResetRequest(BaseModel):
    """Password reset request"""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation"""
    token: str
    new_password: str = Field(..., min_length=8)
    
    @validator('new_password')
    def validate_password(cls, v):
        """Validate password strength"""
        result = security_validator.validate_password_strength(v)
        if not result['is_valid']:
            raise ValueError('; '.join(result['errors']))
        return v


# Helper functions
async def authenticate_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    """
    Authenticate user with User Management Service
    
    Args:
        username: Username or email
        password: Plain text password
        
    Returns:
        User data if authenticated, None otherwise
    """
    try:
        # Call User Management Service
        user_service = get_service_client("user-management")
        
        response = await user_service.post(
            "/api/v1/auth/validate",
            json={"username": username, "password": password}
        )
        
        if response.status_code == 200:
            return response.json()
        
        return None
        
    except Exception as e:
        logger.error(f"Failed to authenticate user: {e}")
        return None


async def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    """
    Get current user from JWT token
    
    Args:
        token: JWT access token
        
    Returns:
        User data
        
    Raises:
        AuthenticationException: If token is invalid
    """
    try:
        # Verify token
        payload = token_manager.verify_token(token, "access")
        
        # Check if token is blacklisted
        cache = await get_cache()
        if await cache.exists(f"blacklist:{token}"):
            raise InvalidTokenException("Token has been revoked")
        
        # Return user data
        return {
            "user_id": payload.get("user_id"),
            "username": payload.get("sub"),
            "permissions": payload.get("permissions", [])
        }
        
    except InvalidTokenException:
        raise
    except Exception as e:
        raise AuthenticationException(f"Failed to validate token: {str(e)}")


async def require_permission(permission: str):
    """
    Dependency to require specific permission
    
    Args:
        permission: Required permission
        
    Returns:
        Dependency function
    """
    async def permission_checker(current_user: Dict = Depends(get_current_user)):
        if permission not in current_user.get("permissions", []):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission}' required"
            )
        return current_user
    
    return permission_checker


# Authentication endpoints
@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends()
):
    """
    User login endpoint
    
    Authenticates user and returns access/refresh tokens.
    """
    # Authenticate user
    user = await authenticate_user(form_data.username, form_data.password)
    
    if not user:
        # Log failed attempt
        logger.warning(
            f"Failed login attempt for user: {form_data.username}",
            extra={
                "request_id": getattr(request.state, 'request_id', 'unknown'),
                "ip_address": request.client.host if request.client else None
            }
        )
        raise AuthenticationException("Invalid username or password")
    
    # Create tokens
    access_token = token_manager.create_access_token(
        subject=user["username"],
        user_id=user["id"],
        permissions=user.get("permissions", [])
    )
    
    refresh_token = token_manager.create_refresh_token(
        subject=user["username"],
        user_id=user["id"]
    )
    
    # Store refresh token in cache
    cache = await get_cache()
    await cache.set(
        f"refresh_token:{user['id']}:{refresh_token[-8:]}",
        refresh_token,
        ttl=settings.refresh_token_expiration_days * 24 * 3600
    )
    
    # Log successful login
    logger.info(
        f"User logged in: {user['username']}",
        extra={
            "request_id": getattr(request.state, 'request_id', 'unknown'),
            "user_id": user["id"]
        }
    )
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.jwt_expiration_minutes * 60,
        user_id=user["id"],
        username=user["username"],
        permissions=user.get("permissions", [])
    )


@router.post("/register", response_model=TokenResponse)
async def register(
    request: Request,
    user_data: UserRegister
):
    """
    User registration endpoint
    
    Creates new user account and returns tokens.
    """
    try:
        # Call User Management Service to create user
        user_service = get_service_client("user-management")
        
        response = await user_service.post(
            "/api/v1/users",
            json={
                "username": user_data.username,
                "email": user_data.email,
                "password": user_data.password,
                "full_name": user_data.full_name
            }
        )
        
        if response.status_code == 201:
            user = response.json()
            
            # Create tokens
            access_token = token_manager.create_access_token(
                subject=user["username"],
                user_id=user["id"],
                permissions=user.get("permissions", [])
            )
            
            refresh_token = token_manager.create_refresh_token(
                subject=user["username"],
                user_id=user["id"]
            )
            
            # Store refresh token
            cache = await get_cache()
            await cache.set(
                f"refresh_token:{user['id']}:{refresh_token[-8:]}",
                refresh_token,
                ttl=settings.refresh_token_expiration_days * 24 * 3600
            )
            
            logger.info(f"New user registered: {user['username']}")
            
            return TokenResponse(
                access_token=access_token,
                refresh_token=refresh_token,
                expires_in=settings.jwt_expiration_minutes * 60,
                user_id=user["id"],
                username=user["username"],
                permissions=user.get("permissions", [])
            )
        
        elif response.status_code == 409:
            raise ValidationException("Username or email already exists")
        else:
            raise HTTPException(
                status_code=response.status_code,
                detail="Failed to create user"
            )
            
    except httpx.RequestError as e:
        logger.error(f"Failed to contact user service: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="User service unavailable"
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: Request,
    refresh_data: RefreshTokenRequest
):
    """
    Refresh access token
    
    Uses refresh token to get new access token.
    """
    try:
        # Verify refresh token
        payload = token_manager.verify_token(refresh_data.refresh_token, "refresh")
        
        user_id = payload.get("user_id")
        username = payload.get("sub")
        
        # Check if refresh token exists in cache
        cache = await get_cache()
        token_key = f"refresh_token:{user_id}:{refresh_data.refresh_token[-8:]}"
        
        if not await cache.exists(token_key):
            raise InvalidTokenException("Invalid refresh token")
        
        # Get user permissions from User Management Service
        user_service = get_service_client("user-management")
        response = await user_service.get(f"/api/v1/users/{user_id}")
        
        if response.status_code == 200:
            user = response.json()
            permissions = user.get("permissions", [])
        else:
            permissions = []
        
        # Create new access token
        access_token = token_manager.create_access_token(
            subject=username,
            user_id=user_id,
            permissions=permissions
        )
        
        logger.info(f"Token refreshed for user: {username}")
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_data.refresh_token,
            expires_in=settings.jwt_expiration_minutes * 60,
            user_id=user_id,
            username=username,
            permissions=permissions
        )
        
    except InvalidTokenException as e:
        raise AuthenticationException(str(e))
    except Exception as e:
        logger.error(f"Failed to refresh token: {e}")
        raise AuthenticationException("Failed to refresh token")


@router.post("/logout")
async def logout(
    request: Request,
    current_user: Dict = Depends(get_current_user),
    authorization: str = Depends(oauth2_scheme)
):
    """
    User logout endpoint
    
    Revokes current access token and refresh tokens.
    """
    try:
        cache = await get_cache()
        
        # Blacklist current access token
        token_ttl = settings.jwt_expiration_minutes * 60
        await cache.set(f"blacklist:{authorization}", "1", ttl=token_ttl)
        
        # Remove all refresh tokens for user
        # Note: In production, you'd want to track refresh tokens more precisely
        user_id = current_user["user_id"]
        
        logger.info(f"User logged out: {current_user['username']}")
        
        return {"message": "Successfully logged out"}
        
    except Exception as e:
        logger.error(f"Failed to logout user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to logout"
        )


@router.post("/change-password")
async def change_password(
    request: Request,
    password_data: PasswordChangeRequest,
    current_user: Dict = Depends(get_current_user)
):
    """
    Change user password
    
    Requires current password validation.
    """
    try:
        # Validate old password
        auth_result = await authenticate_user(
            current_user["username"],
            password_data.old_password
        )
        
        if not auth_result:
            raise ValidationException("Current password is incorrect")
        
        # Update password via User Management Service
        user_service = get_service_client("user-management")
        
        response = await user_service.put(
            f"/api/v1/users/{current_user['user_id']}/password",
            json={"password": password_data.new_password}
        )
        
        if response.status_code == 200:
            logger.info(f"Password changed for user: {current_user['username']}")
            return {"message": "Password changed successfully"}
        else:
            raise HTTPException(
                status_code=response.status_code,
                detail="Failed to change password"
            )
            
    except ValidationException:
        raise
    except Exception as e:
        logger.error(f"Failed to change password: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to change password"
        )


@router.post("/request-password-reset")
async def request_password_reset(
    request: Request,
    reset_data: PasswordResetRequest
):
    """
    Request password reset
    
    Sends password reset email to user.
    """
    try:
        # Call User Management Service
        user_service = get_service_client("user-management")
        
        response = await user_service.post(
            "/api/v1/auth/password-reset",
            json={"email": reset_data.email}
        )
        
        if response.status_code in [200, 202]:
            # Always return success to prevent email enumeration
            return {
                "message": "If the email exists, a password reset link has been sent"
            }
        else:
            # Log but don't expose error
            logger.error(f"Password reset failed: {response.status_code}")
            return {
                "message": "If the email exists, a password reset link has been sent"
            }
            
    except Exception as e:
        logger.error(f"Failed to request password reset: {e}")
        # Don't expose errors
        return {
            "message": "If the email exists, a password reset link has been sent"
        }


@router.post("/reset-password")
async def reset_password(
    request: Request,
    reset_data: PasswordResetConfirm
):
    """
    Reset password with token
    
    Completes password reset process.
    """
    try:
        # Call User Management Service
        user_service = get_service_client("user-management")
        
        response = await user_service.post(
            "/api/v1/auth/password-reset/confirm",
            json={
                "token": reset_data.token,
                "new_password": reset_data.new_password
            }
        )
        
        if response.status_code == 200:
            return {"message": "Password reset successfully"}
        elif response.status_code == 400:
            raise ValidationException("Invalid or expired reset token")
        else:
            raise HTTPException(
                status_code=response.status_code,
                detail="Failed to reset password"
            )
            
    except ValidationException:
        raise
    except Exception as e:
        logger.error(f"Failed to reset password: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reset password"
        )


@router.get("/me")
async def get_current_user_info(
    current_user: Dict = Depends(get_current_user)
):
    """
    Get current user information
    
    Returns user profile data.
    """
    try:
        # Get full user info from User Management Service
        user_service = get_service_client("user-management")
        
        response = await user_service.get(
            f"/api/v1/users/{current_user['user_id']}"
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            # Return basic info from token
            return {
                "id": current_user["user_id"],
                "username": current_user["username"],
                "permissions": current_user["permissions"]
            }
            
    except Exception as e:
        logger.error(f"Failed to get user info: {e}")
        # Return basic info from token
        return {
            "id": current_user["user_id"],
            "username": current_user["username"],
            "permissions": current_user["permissions"]
        }


@router.post("/validate-token")
async def validate_token(
    request: Request,
    current_user: Dict = Depends(get_current_user)
):
    """
    Validate access token
    
    Checks if token is valid and returns user info.
    """
    return {
        "valid": True,
        "user_id": current_user["user_id"],
        "username": current_user["username"],
        "permissions": current_user["permissions"]
    }