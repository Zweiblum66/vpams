"""
API routes for User Management Service

This module defines all API endpoints for user management functionality.
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Dict, Any
from datetime import datetime, timezone, timedelta
from uuid import uuid4, UUID
import logging

from .dependencies import (
    get_db,
    get_current_user,
    get_current_active_user,
    require_permission,
    require_superuser,
    get_pagination_params,
    get_sort_params,
    get_filter_params
)
from models.schemas import (
    UserRegistrationRequest,
    UserRegistrationResponse,
    UserLoginRequest,
    UserLoginResponse,
    UserResponse,
    UserUpdateRequest,
    EmailVerificationRequest,
    PasswordResetRequest,
    PasswordResetConfirmRequest,
    ChangePasswordRequest,
    TokenResponse,
    ErrorResponse,
    BaseResponse,
    RoleCreateRequest,
    RoleUpdateRequest,
    PermissionCreateRequest,
    PermissionUpdateRequest,
    RoleAssignmentRequest,
    PermissionAssignmentRequest,
    RoleListResponse,
    PermissionListResponse,
    UserPermissionsResponse,
    RolePermissionsResponse,
    RoleResponse,
    PermissionResponse,
    PaginationParams,
    SortParams
)
from db.models import User, UserProfile, Role
from core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    generate_verification_token,
    verify_verification_token
)
from core.config import get_settings
from services.user_service import UserService
from services.email_service import EmailService
from services.auth_service import AuthService
from services.lockout_service import AccountLockoutService
from services.rbac_service import RBACService
from services.inheritance_service import InheritanceService
from .oauth2_routes import oauth2_router
from .saml_routes import saml_router

logger = logging.getLogger(__name__)
settings = get_settings()

# Create router
router = APIRouter(prefix="/api/v1/users", tags=["users"])
auth_router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])

# Initialize services
user_service = UserService()
email_service = EmailService()
lockout_service = AccountLockoutService()
rbac_service = RBACService()
inheritance_service = InheritanceService()


@router.post("/register", response_model=UserRegistrationResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserRegistrationRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new user account
    
    Creates a new user with the provided information and sends email verification.
    """
    try:
        # Check if user already exists
        existing_user = await user_service.get_user_by_email(db, user_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )
        
        # Check if username is taken (if provided)
        if user_data.username:
            existing_username = await user_service.get_user_by_username(db, user_data.username)
            if existing_username:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already taken"
                )
        
        # Create new user
        user_id = uuid4()
        password_hash = get_password_hash(user_data.password)
        
        # Create user object
        new_user = User(
            id=user_id,
            email=user_data.email,
            username=user_data.username,
            password_hash=password_hash,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            display_name=f"{user_data.first_name} {user_data.last_name}",
            is_active=True,
            is_verified=False,
            is_superuser=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        # Create user profile
        profile = UserProfile(
            id=uuid4(),
            user_id=user_id,
            phone=user_data.phone,
            department=user_data.department,
            job_title=user_data.job_title,
            organization=user_data.organization,
            timezone=user_data.timezone or "UTC",
            language=user_data.language or "en",
            preferences={},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        # Assign default role
        default_role = await user_service.get_default_role(db)
        if default_role:
            new_user.roles.append(default_role)
        
        # Save to database
        db.add(new_user)
        db.add(profile)
        await db.commit()
        await db.refresh(new_user)
        
        # Generate email verification token
        verification_token = generate_verification_token(str(user_id))
        
        # Send verification email in background
        background_tasks.add_task(
            email_service.send_verification_email,
            user_data.email,
            user_data.first_name,
            verification_token
        )
        
        # Prepare response data
        response_data = {
            "user_id": str(user_id),
            "email": user_data.email,
            "username": user_data.username,
            "first_name": user_data.first_name,
            "last_name": user_data.last_name,
            "is_active": True,
            "is_verified": False,
            "created_at": new_user.created_at.isoformat(),
            "verification_required": True
        }
        
        logger.info(f"User registered successfully: {user_data.email}")
        
        return UserRegistrationResponse(
            success=True,
            message="User registered successfully. Please check your email for verification.",
            data=response_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"User registration failed: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed. Please try again."
        )


@auth_router.post("/login", response_model=UserLoginResponse)
async def login_user(
    user_data: UserLoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Authenticate user and return access tokens
    """
    try:
        # Use auth service for authentication
        auth_service = AuthService()
        
        # Authenticate user
        user, lockout_info = await auth_service.authenticate_user(db, user_data.email, user_data.password)
        if not user:
            if lockout_info:
                if lockout_info.get("locked"):
                    raise HTTPException(
                        status_code=status.HTTP_423_LOCKED,
                        detail=lockout_info["message"]
                    )
                else:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail=lockout_info["message"]
                    )
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid credentials"
                )
        
        # Check if MFA is enabled
        if user.mfa_enabled:
            # Create a temporary token for MFA verification
            mfa_token = create_access_token(
                user_id=str(user.id),
                expires_delta=timedelta(minutes=5),  # Short-lived token for MFA
                additional_claims={"mfa_required": True, "mfa_pending": True}
            )
            
            return UserLoginResponse(
                success=True,
                message="MFA required",
                data={
                    "mfa_required": True,
                    "mfa_token": mfa_token,
                    "user": {
                        "user_id": str(user.id),
                        "email": user.email
                    }
                }
            )
        
        # Create user session with tokens
        tokens = await auth_service.create_user_session(
            db, user, user_data.device_info, user_data.remember_me
        )
        
        # Load user roles
        await db.refresh(user, ["roles"])
        user_roles = [role.name for role in user.roles]
        
        # Prepare response
        response_data = {
            "user": {
                "user_id": str(user.id),
                "email": user.email,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "display_name": user.display_name,
                "is_active": user.is_active,
                "is_verified": user.is_verified,
                "roles": user_roles
            },
            "tokens": tokens
        }
        
        logger.info(f"User logged in successfully: {user.email}")
        
        return UserLoginResponse(
            success=True,
            message="Login successful",
            data=response_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed. Please try again."
        )


@auth_router.post("/verify-email", response_model=BaseResponse)
async def verify_email(
    request: EmailVerificationRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Verify user email address using verification token
    """
    try:
        # Verify token and get user ID
        user_id = verify_verification_token(request.token)
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired verification token"
            )
        
        # Get user from database
        user = await user_service.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Check if already verified
        if user.is_verified:
            return BaseResponse(
                success=True,
                message="Email already verified"
            )
        
        # Update user verification status
        user.is_verified = True
        user.email_verified_at = datetime.now(timezone.utc)
        user.updated_at = datetime.now(timezone.utc)
        
        await db.commit()
        
        logger.info(f"Email verified successfully: {user.email}")
        
        return BaseResponse(
            success=True,
            message="Email verified successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Email verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Email verification failed. Please try again."
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current user information
    """
    await db.refresh(current_user, ["profile"])
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update current user information
    """
    try:
        # Update user fields
        if user_update.first_name is not None:
            current_user.first_name = user_update.first_name
        if user_update.last_name is not None:
            current_user.last_name = user_update.last_name
        if user_update.display_name is not None:
            current_user.display_name = user_update.display_name
        if user_update.username is not None:
            # Check if username is taken
            existing_user = await user_service.get_user_by_username(db, user_update.username)
            if existing_user and existing_user.id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already taken"
                )
            current_user.username = user_update.username
        
        # Update profile fields
        await db.refresh(current_user, ["profile"])
        profile = current_user.profile
        
        if user_update.phone is not None:
            profile.phone = user_update.phone
        if user_update.department is not None:
            profile.department = user_update.department
        if user_update.job_title is not None:
            profile.job_title = user_update.job_title
        if user_update.organization is not None:
            profile.organization = user_update.organization
        if user_update.location is not None:
            profile.location = user_update.location
        if user_update.timezone is not None:
            profile.timezone = user_update.timezone
        if user_update.language is not None:
            profile.language = user_update.language
        if user_update.bio is not None:
            profile.bio = user_update.bio
        if user_update.website is not None:
            profile.website = user_update.website
        if user_update.preferences is not None:
            profile.preferences = user_update.preferences
        
        # Update timestamps
        current_user.updated_at = datetime.now(timezone.utc)
        profile.updated_at = datetime.now(timezone.utc)
        
        await db.commit()
        await db.refresh(current_user)
        
        logger.info(f"User updated successfully: {current_user.email}")
        
        return current_user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"User update failed: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User update failed. Please try again."
        )


@auth_router.post("/change-password", response_model=BaseResponse)
async def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Change user password
    """
    try:
        # Verify current password
        if not verify_password(request.current_password, current_user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        # Update password
        current_user.password_hash = get_password_hash(request.new_password)
        current_user.updated_at = datetime.now(timezone.utc)
        
        await db.commit()
        
        logger.info(f"Password changed successfully: {current_user.email}")
        
        return BaseResponse(
            success=True,
            message="Password changed successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password change failed: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password change failed. Please try again."
        )


@auth_router.post("/logout", response_model=BaseResponse)
async def logout_user(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Logout user and invalidate all sessions
    """
    try:
        auth_service = AuthService()
        
        # Logout user (invalidate all sessions)
        success = await auth_service.logout_user(db, current_user.id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Logout failed"
            )
        
        logger.info(f"User logged out successfully: {current_user.email}")
        
        return BaseResponse(
            success=True,
            message="Logged out successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Logout failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed. Please try again."
        )


@auth_router.post("/logout-session", response_model=BaseResponse)
async def logout_session(
    refresh_token: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Logout specific session using refresh token
    """
    try:
        auth_service = AuthService()
        
        # Logout specific session
        success = await auth_service.logout_user(db, current_user.id, refresh_token)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Session logout failed"
            )
        
        logger.info(f"Session logged out successfully: {current_user.email}")
        
        return BaseResponse(
            success=True,
            message="Session logged out successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Session logout failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Session logout failed. Please try again."
        )


@auth_router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_token: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Refresh access token using refresh token
    """
    try:
        auth_service = AuthService()
        
        # Refresh access token
        tokens = await auth_service.refresh_access_token(db, refresh_token)
        
        if not tokens:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token"
            )
        
        return TokenResponse(**tokens)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed. Please try again."
        )


@auth_router.get("/sessions", response_model=Dict[str, Any])
async def get_user_sessions(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get active sessions for current user
    """
    try:
        auth_service = AuthService()
        
        # Get active sessions
        sessions = await auth_service.get_active_sessions(db, current_user.id)
        
        # Format session data
        session_data = []
        for session in sessions:
            session_data.append({
                "session_id": str(session.id),
                "device_info": session.device_info,
                "created_at": session.created_at.isoformat(),
                "last_used_at": session.last_used_at.isoformat() if session.last_used_at else None,
                "expires_at": session.expires_at.isoformat(),
                "is_current": False  # Could be enhanced to detect current session
            })
        
        return {
            "success": True,
            "message": "Sessions retrieved successfully",
            "data": {
                "sessions": session_data,
                "total": len(session_data)
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get user sessions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve sessions"
        )


@auth_router.post("/password-reset", response_model=BaseResponse)
async def request_password_reset(
    request: PasswordResetRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Request password reset - send reset email
    """
    try:
        # Get user by email
        user = await user_service.get_user_by_email(db, request.email)
        
        # Always return success to prevent email enumeration
        if not user:
            return BaseResponse(
                success=True,
                message="If an account with this email exists, you will receive password reset instructions."
            )
        
        # Generate reset token
        auth_service = AuthService()
        reset_token = await auth_service.generate_password_reset_token(user.id)
        
        # Send reset email in background
        background_tasks.add_task(
            email_service.send_password_reset_email,
            user.email,
            user.first_name,
            reset_token
        )
        
        logger.info(f"Password reset requested for: {user.email}")
        
        return BaseResponse(
            success=True,
            message="If an account with this email exists, you will receive password reset instructions."
        )
        
    except Exception as e:
        logger.error(f"Password reset request failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password reset request failed. Please try again."
        )


@auth_router.post("/password-reset/confirm", response_model=BaseResponse)
async def confirm_password_reset(
    request: PasswordResetConfirmRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Confirm password reset with token and new password
    """
    try:
        auth_service = AuthService()
        
        # Verify reset token and get user
        user = await auth_service.verify_password_reset_token(db, request.token)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token"
            )
        
        # Reset password
        success = await auth_service.reset_user_password(db, user, request.new_password)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Password reset failed"
            )
        
        logger.info(f"Password reset confirmed for: {user.email}")
        
        return BaseResponse(
            success=True,
            message="Password reset successfully. Please log in with your new password."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password reset confirmation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password reset confirmation failed. Please try again."
        )


@router.get("/lockout-info/{user_id}", response_model=Dict[str, Any])
async def get_user_lockout_info(
    user_id: UUID,
    current_user: User = Depends(require_superuser),
    db: AsyncSession = Depends(get_db)
):
    """
    Get lockout information for a specific user (admin only)
    """
    try:
        # Get user
        user = await user_service.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Get lockout info
        lockout_info = await lockout_service.get_lockout_info(user)
        
        return {
            "success": True,
            "data": {
                "user_id": str(user.id),
                "email": user.email,
                "lockout_info": lockout_info
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get lockout info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve lockout information"
        )


@router.post("/unlock/{user_id}", response_model=BaseResponse)
async def unlock_user_account(
    user_id: UUID,
    current_user: User = Depends(require_superuser),
    db: AsyncSession = Depends(get_db)
):
    """
    Manually unlock a user account (admin only)
    """
    try:
        # Get user
        user = await user_service.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Unlock account
        success = await lockout_service.unlock_account(db, user)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to unlock account"
            )
        
        logger.info(f"Account unlocked by admin {current_user.email} for user: {user.email}")
        
        return BaseResponse(
            success=True,
            message="Account unlocked successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to unlock account: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to unlock account"
        )


@router.get("/lockout-stats", response_model=Dict[str, Any])
async def get_lockout_stats(
    current_user: User = Depends(require_superuser),
    db: AsyncSession = Depends(get_db)
):
    """
    Get system lockout statistics (admin only)
    """
    try:
        stats = await lockout_service.get_lockout_stats(db)
        
        return {
            "success": True,
            "data": stats
        }
        
    except Exception as e:
        logger.error(f"Failed to get lockout stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve lockout statistics"
        )


@router.get("/locked-users", response_model=Dict[str, Any])
async def get_locked_users(
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(require_superuser),
    db: AsyncSession = Depends(get_db)
):
    """
    Get list of currently locked users (admin only)
    """
    try:
        locked_users = await lockout_service.get_locked_users(db, limit)
        
        users_data = []
        for user in locked_users:
            lockout_info = await lockout_service.get_lockout_info(user)
            users_data.append({
                "user_id": str(user.id),
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "lockout_info": lockout_info
            })
        
        return {
            "success": True,
            "data": {
                "locked_users": users_data,
                "total": len(users_data)
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get locked users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve locked users"
        )


@router.post("/cleanup-lockouts", response_model=BaseResponse)
async def cleanup_expired_lockouts(
    current_user: User = Depends(require_superuser),
    db: AsyncSession = Depends(get_db)
):
    """
    Clean up expired account lockouts (admin only)
    """
    try:
        count = await lockout_service.cleanup_expired_lockouts(db)
        
        return BaseResponse(
            success=True,
            message=f"Cleaned up {count} expired lockouts"
        )
        
    except Exception as e:
        logger.error(f"Failed to cleanup lockouts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cleanup expired lockouts"
        )


@auth_router.get("/lockout-status", response_model=Dict[str, Any])
async def get_current_user_lockout_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current user's lockout status
    """
    try:
        lockout_info = await lockout_service.get_lockout_info(current_user)
        
        return {
            "success": True,
            "data": lockout_info
        }
        
    except Exception as e:
        logger.error(f"Failed to get user lockout status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve lockout status"
        )


# RBAC Routes
rbac_router = APIRouter(prefix="/api/v1/rbac", tags=["rbac"])

# Role Management
@rbac_router.post("/roles", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    role_data: RoleCreateRequest,
    current_user: User = Depends(require_superuser),
    db: AsyncSession = Depends(get_db)
):
    """Create a new role (admin only)"""
    try:
        role = await rbac_service.create_role(
            db=db,
            name=role_data.name,
            display_name=role_data.display_name,
            description=role_data.description,
            role_type=role_data.role_type,
            parent_role_id=role_data.parent_role_id,
            creator_id=current_user.id
        )
        return role
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create role: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create role")


@rbac_router.get("/roles", response_model=RoleListResponse)
async def get_roles(
    pagination: PaginationParams = Depends(get_pagination_params),
    sort: SortParams = Depends(get_sort_params),
    is_active: Optional[bool] = Query(None),
    role_type: Optional[str] = Query(None),
    is_system: Optional[bool] = Query(None),
    current_user: User = Depends(require_superuser),
    db: AsyncSession = Depends(get_db)
):
    """Get list of roles (admin only)"""
    try:
        filters = {
            "is_active": is_active,
            "role_type": role_type,
            "is_system": is_system
        }
        roles, total = await rbac_service.get_roles(db, pagination, sort, filters)
        
        return RoleListResponse(
            success=True,
            message="Roles retrieved successfully",
            data=roles,
            meta={
                "page": pagination.page,
                "limit": pagination.limit,
                "total": total,
                "pages": (total + pagination.limit - 1) // pagination.limit
            }
        )
    except Exception as e:
        logger.error(f"Failed to get roles: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve roles")


@rbac_router.get("/roles/{role_id}", response_model=RoleResponse)
async def get_role(
    role_id: UUID,
    current_user: User = Depends(require_superuser),
    db: AsyncSession = Depends(get_db)
):
    """Get role by ID (admin only)"""
    try:
        role = await rbac_service.get_role_by_id(db, role_id)
        if not role:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
        return role
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get role: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve role")


@rbac_router.put("/roles/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: UUID,
    role_data: RoleUpdateRequest,
    current_user: User = Depends(require_superuser),
    db: AsyncSession = Depends(get_db)
):
    """Update role (admin only)"""
    try:
        updates = role_data.dict(exclude_unset=True)
        role = await rbac_service.update_role(db, role_id, updates, current_user.id)
        if not role:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
        return role
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update role: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update role")


@rbac_router.delete("/roles/{role_id}", response_model=BaseResponse)
async def delete_role(
    role_id: UUID,
    current_user: User = Depends(require_superuser),
    db: AsyncSession = Depends(get_db)
):
    """Delete role (admin only)"""
    try:
        success = await rbac_service.delete_role(db, role_id)
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
        return BaseResponse(success=True, message="Role deleted successfully")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete role: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete role")


# Permission Management
@rbac_router.post("/permissions", response_model=PermissionResponse, status_code=status.HTTP_201_CREATED)
async def create_permission(
    permission_data: PermissionCreateRequest,
    current_user: User = Depends(require_superuser),
    db: AsyncSession = Depends(get_db)
):
    """Create a new permission (admin only)"""
    try:
        permission = await rbac_service.create_permission(
            db=db,
            name=permission_data.name,
            display_name=permission_data.display_name,
            description=permission_data.description,
            resource=permission_data.resource,
            action=permission_data.action,
            category=permission_data.category,
            scope=permission_data.scope,
            creator_id=current_user.id
        )
        return permission
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create permission: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create permission")


@rbac_router.get("/permissions", response_model=PermissionListResponse)
async def get_permissions(
    pagination: PaginationParams = Depends(get_pagination_params),
    sort: SortParams = Depends(get_sort_params),
    is_active: Optional[bool] = Query(None),
    resource: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    scope: Optional[str] = Query(None),
    current_user: User = Depends(require_superuser),
    db: AsyncSession = Depends(get_db)
):
    """Get list of permissions (admin only)"""
    try:
        filters = {
            "is_active": is_active,
            "resource": resource,
            "action": action,
            "category": category,
            "scope": scope
        }
        permissions, total = await rbac_service.get_permissions(db, pagination, sort, filters)
        
        return PermissionListResponse(
            success=True,
            message="Permissions retrieved successfully",
            data=permissions,
            meta={
                "page": pagination.page,
                "limit": pagination.limit,
                "total": total,
                "pages": (total + pagination.limit - 1) // pagination.limit
            }
        )
    except Exception as e:
        logger.error(f"Failed to get permissions: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve permissions")


@rbac_router.get("/permissions/{permission_id}", response_model=PermissionResponse)
async def get_permission(
    permission_id: UUID,
    current_user: User = Depends(require_superuser),
    db: AsyncSession = Depends(get_db)
):
    """Get permission by ID (admin only)"""
    try:
        permission = await rbac_service.get_permission_by_id(db, permission_id)
        if not permission:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found")
        return permission
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get permission: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve permission")


# Role-Permission Assignment
@rbac_router.post("/roles/{role_id}/permissions", response_model=BaseResponse)
async def assign_permission_to_role(
    role_id: UUID,
    assignment: PermissionAssignmentRequest,
    current_user: User = Depends(require_superuser),
    db: AsyncSession = Depends(get_db)
):
    """Assign permission to role (admin only)"""
    try:
        success = await rbac_service.assign_permission_to_role(
            db, role_id, assignment.permission_id, current_user.id
        )
        if not success:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Assignment failed")
        return BaseResponse(success=True, message="Permission assigned to role successfully")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to assign permission to role: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to assign permission")


@rbac_router.delete("/roles/{role_id}/permissions/{permission_id}", response_model=BaseResponse)
async def revoke_permission_from_role(
    role_id: UUID,
    permission_id: UUID,
    current_user: User = Depends(require_superuser),
    db: AsyncSession = Depends(get_db)
):
    """Revoke permission from role (admin only)"""
    try:
        success = await rbac_service.revoke_permission_from_role(db, role_id, permission_id)
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission assignment not found")
        return BaseResponse(success=True, message="Permission revoked from role successfully")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to revoke permission from role: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to revoke permission")


# User-Role Assignment
@rbac_router.post("/users/{user_id}/roles", response_model=BaseResponse)
async def assign_role_to_user(
    user_id: UUID,
    assignment: RoleAssignmentRequest,
    current_user: User = Depends(require_superuser),
    db: AsyncSession = Depends(get_db)
):
    """Assign role to user (admin only)"""
    try:
        success = await rbac_service.assign_role_to_user(
            db, user_id, assignment.role_id, current_user.id
        )
        if not success:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Assignment failed")
        return BaseResponse(success=True, message="Role assigned to user successfully")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to assign role to user: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to assign role")


@rbac_router.delete("/users/{user_id}/roles/{role_id}", response_model=BaseResponse)
async def revoke_role_from_user(
    user_id: UUID,
    role_id: UUID,
    current_user: User = Depends(require_superuser),
    db: AsyncSession = Depends(get_db)
):
    """Revoke role from user (admin only)"""
    try:
        success = await rbac_service.revoke_role_from_user(db, user_id, role_id)
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role assignment not found")
        return BaseResponse(success=True, message="Role revoked from user successfully")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to revoke role from user: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to revoke role")


# Permission Queries
@rbac_router.get("/users/{user_id}/permissions", response_model=UserPermissionsResponse)
async def get_user_permissions(
    user_id: UUID,
    include_inherited: bool = Query(True),
    current_user: User = Depends(require_superuser),
    db: AsyncSession = Depends(get_db)
):
    """Get user permissions (admin only)"""
    try:
        permissions = await rbac_service.get_user_permissions(db, user_id, include_inherited)
        
        # Get user with roles
        user = await user_service.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        
        return UserPermissionsResponse(
            user_id=user_id,
            permissions=list(permissions),
            roles=user.roles
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user permissions: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve permissions")


@rbac_router.get("/roles/{role_id}/permissions", response_model=RolePermissionsResponse)
async def get_role_permissions(
    role_id: UUID,
    include_inherited: bool = Query(True),
    current_user: User = Depends(require_superuser),
    db: AsyncSession = Depends(get_db)
):
    """Get role permissions (admin only)"""
    try:
        role = await rbac_service.get_role_by_id(db, role_id)
        if not role:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
        
        permissions = await rbac_service.get_role_permissions(db, role_id, include_inherited)
        
        # Separate direct and inherited permissions
        direct_permissions = [p for p in role.permissions if p.is_active]
        inherited_permissions = list(permissions - {p.name for p in direct_permissions})
        
        return RolePermissionsResponse(
            role_id=role_id,
            role_name=role.name,
            permissions=direct_permissions,
            inherited_permissions=inherited_permissions
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get role permissions: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve permissions")


@rbac_router.get("/stats", response_model=Dict[str, Any])
async def get_rbac_stats(
    current_user: User = Depends(require_superuser),
    db: AsyncSession = Depends(get_db)
):
    """Get RBAC statistics (admin only)"""
    try:
        stats = await rbac_service.get_rbac_stats(db)
        return {
            "success": True,
            "data": stats
        }
    except Exception as e:
        logger.error(f"Failed to get RBAC stats: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve statistics")


# Permission Inheritance Routes
inheritance_router = APIRouter(prefix="/api/v1/inheritance", tags=["inheritance"])

@inheritance_router.get("/users/{user_id}/effective-permissions", response_model=Dict[str, Any])
async def get_user_effective_permissions(
    user_id: UUID,
    include_sources: bool = Query(False, description="Include source information"),
    current_user: User = Depends(require_superuser),
    db: AsyncSession = Depends(get_db)
):
    """Get effective permissions for a user with inheritance analysis"""
    try:
        result = await inheritance_service.get_effective_permissions(
            db, user_id, include_sources
        )
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        logger.error(f"Failed to get effective permissions: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve effective permissions")


@inheritance_router.get("/users/{user_id}/inheritance-tree", response_model=Dict[str, Any])
async def get_user_inheritance_tree(
    user_id: UUID,
    current_user: User = Depends(require_superuser),
    db: AsyncSession = Depends(get_db)
):
    """Get the full inheritance tree for a user"""
    try:
        result = await inheritance_service.get_permission_inheritance_tree(db, user_id)
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        logger.error(f"Failed to get inheritance tree: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve inheritance tree")


@inheritance_router.get("/users/{user_id}/permission-conflicts", response_model=Dict[str, Any])
async def get_user_permission_conflicts(
    user_id: UUID,
    current_user: User = Depends(require_superuser),
    db: AsyncSession = Depends(get_db)
):
    """Check for permission conflicts in user's assignments"""
    try:
        result = await inheritance_service.check_permission_conflicts(db, user_id)
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        logger.error(f"Failed to check permission conflicts: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to check permission conflicts")


@inheritance_router.get("/users/{user_id}/inheritance-statistics", response_model=Dict[str, Any])
async def get_user_inheritance_statistics(
    user_id: UUID,
    current_user: User = Depends(require_superuser),
    db: AsyncSession = Depends(get_db)
):
    """Get statistics about permission inheritance for a user"""
    try:
        result = await inheritance_service.get_inheritance_statistics(db, user_id)
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        logger.error(f"Failed to get inheritance statistics: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve inheritance statistics")


@inheritance_router.get("/users/{user_id}/optimization-recommendations", response_model=Dict[str, Any])
async def get_user_optimization_recommendations(
    user_id: UUID,
    current_user: User = Depends(require_superuser),
    db: AsyncSession = Depends(get_db)
):
    """Get recommendations for optimizing user permission assignments"""
    try:
        result = await inheritance_service.optimize_user_permissions(db, user_id)
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        logger.error(f"Failed to get optimization recommendations: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to generate optimization recommendations")


@inheritance_router.get("/users/{user_id}/permissions/summary", response_model=Dict[str, Any])
async def get_user_permissions_summary(
    user_id: UUID,
    current_user: User = Depends(require_superuser),
    db: AsyncSession = Depends(get_db)
):
    """Get a comprehensive summary of user's permissions"""
    try:
        # Get all relevant information
        effective_permissions = await inheritance_service.get_effective_permissions(
            db, user_id, include_sources=True
        )
        conflicts = await inheritance_service.check_permission_conflicts(db, user_id)
        statistics = await inheritance_service.get_inheritance_statistics(db, user_id)
        recommendations = await inheritance_service.optimize_user_permissions(db, user_id)
        
        return {
            "success": True,
            "data": {
                "user_id": str(user_id),
                "permissions": effective_permissions,
                "conflicts": conflicts,
                "statistics": statistics,
                "recommendations": recommendations
            }
        }
    except Exception as e:
        logger.error(f"Failed to get permissions summary: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to generate permissions summary")


# LDAP Management endpoints
ldap_router = APIRouter(prefix="/ldap", tags=["LDAP Management"])

@ldap_router.get("/test", response_model=Dict[str, Any])
async def test_ldap_connection(
    current_user: User = Depends(require_superuser),
    db: AsyncSession = Depends(get_db)
):
    """Test LDAP connection and configuration"""
    try:
        from services.ldap_service import LDAPService
        from core.config import get_settings
        
        settings = get_settings()
        if not settings.enable_ldap:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="LDAP authentication is disabled"
            )
        
        ldap_service = LDAPService()
        result = await ldap_service.test_connection()
        
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        logger.error(f"LDAP connection test failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"LDAP connection test failed: {str(e)}"
        )

@ldap_router.post("/sync", response_model=Dict[str, Any])
async def sync_ldap_users(
    current_user: User = Depends(require_superuser),
    db: AsyncSession = Depends(get_db)
):
    """Synchronize users from LDAP directory"""
    try:
        from services.ldap_service import LDAPService
        from core.config import get_settings
        
        settings = get_settings()
        if not settings.enable_ldap:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="LDAP authentication is disabled"
            )
        
        ldap_service = LDAPService()
        result = await ldap_service.sync_users(db)
        
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        logger.error(f"LDAP user sync failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"LDAP user sync failed: {str(e)}"
        )

@ldap_router.get("/config", response_model=Dict[str, Any])
async def get_ldap_config(
    current_user: User = Depends(require_superuser)
):
    """Get LDAP configuration (without sensitive data)"""
    try:
        from core.config import get_settings
        settings = get_settings()
        
        if not settings.enable_ldap:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="LDAP authentication is disabled"
            )
        
        config = {
            "enabled": settings.enable_ldap,
            "server": settings.ldap_server,
            "port": settings.ldap_port,
            "use_ssl": settings.ldap_use_ssl,
            "use_tls": settings.ldap_use_tls,
            "base_dn": settings.ldap_base_dn,
            "user_search_base": settings.ldap_user_search_base,
            "user_search_filter": settings.ldap_user_search_filter,
            "user_object_class": settings.ldap_user_object_class,
            "group_search_base": settings.ldap_group_search_base,
            "group_search_filter": settings.ldap_group_search_filter,
            "group_object_class": settings.ldap_group_object_class,
            "auto_create_user": settings.ldap_auto_create_user,
            "auto_update_user": settings.ldap_auto_update_user,
            "default_role": settings.ldap_default_role,
            "admin_groups": settings.ldap_admin_groups,
            "editor_groups": settings.ldap_editor_groups,
            "viewer_groups": settings.ldap_viewer_groups,
            "attribute_mappings": {
                "username": settings.ldap_username_attr,
                "email": settings.ldap_email_attr,
                "first_name": settings.ldap_first_name_attr,
                "last_name": settings.ldap_last_name_attr,
                "display_name": settings.ldap_display_name_attr,
                "phone": settings.ldap_phone_attr,
                "department": settings.ldap_department_attr,
                "organization": settings.ldap_organization_attr,
                "groups": settings.ldap_groups_attr
            }
        }
        
        return {
            "success": True,
            "data": config
        }
    except Exception as e:
        logger.error(f"Failed to get LDAP config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get LDAP configuration"
        )

@ldap_router.post("/authenticate", response_model=Dict[str, Any])
async def test_ldap_authentication(
    username: str,
    password: str,
    current_user: User = Depends(require_superuser)
):
    """Test LDAP authentication for a specific user"""
    try:
        from services.ldap_service import LDAPService
        from core.config import get_settings
        
        settings = get_settings()
        if not settings.enable_ldap:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="LDAP authentication is disabled"
            )
        
        ldap_service = LDAPService()
        user_info = await ldap_service.authenticate_user(username, password)
        
        if user_info:
            # Remove sensitive information before returning
            safe_user_info = {k: v for k, v in user_info.items() if k not in ['password']}
            return {
                "success": True,
                "authenticated": True,
                "user_info": safe_user_info
            }
        else:
            return {
                "success": True,
                "authenticated": False,
                "message": "Authentication failed"
            }
    except Exception as e:
        logger.error(f"LDAP authentication test failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"LDAP authentication test failed: {str(e)}"
        )


# Include all routers in main router
router.include_router(auth_router)
router.include_router(rbac_router)
router.include_router(inheritance_router)
router.include_router(ldap_router)
router.include_router(oauth2_router)
router.include_router(saml_router)