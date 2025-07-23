"""
MFA API routes

This module defines all Multi-Factor Authentication related endpoints.
"""

from typing import Dict, Any
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import get_settings
from ..core.exceptions import (
    MFANotEnabledError,
    InvalidMFACodeError,
    MFAAlreadyEnabledError,
    InvalidCredentialsError
)
from ..db.base import get_db
from ..db.models import User
from ..models.schemas import (
    BaseResponse,
    MFASetupRequest,
    MFASetupResponse,
    MFAVerifySetupRequest,
    MFALoginRequest,
    MFAStatusResponse,
    MFADisableRequest,
    MFARegenerateBackupCodesRequest,
    MFARegenerateBackupCodesResponse,
    SMSSendCodeRequest,
    SMSVerifyCodeRequest,
    ErrorResponse,
    UserLoginResponse
)
from ..services.mfa_service import mfa_service, sms_service
from .dependencies import get_current_user, get_current_active_user

settings = get_settings()
router = APIRouter(prefix="/api/v1/mfa", tags=["mfa"])


@router.post("/setup", response_model=MFASetupResponse)
async def setup_mfa(
    request: MFASetupRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> MFASetupResponse:
    """
    Setup MFA for the current user
    
    This endpoint initiates the MFA setup process by generating a secret key,
    QR code, and backup codes. The user must verify the setup with a valid
    TOTP code before MFA is fully enabled.
    """
    try:
        secret, qr_code, backup_codes = await mfa_service.setup_totp(db, current_user)
        
        return MFASetupResponse(
            success=True,
            message="MFA setup initiated. Please scan the QR code and verify with a code.",
            data={
                "secret": secret,
                "qr_code": qr_code,
                "backup_codes": backup_codes
            }
        )
    except MFAAlreadyEnabledError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to setup MFA"
        )


@router.post("/verify-setup", response_model=BaseResponse)
async def verify_mfa_setup(
    request: MFAVerifySetupRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> BaseResponse:
    """
    Verify MFA setup with TOTP code
    
    This endpoint completes the MFA setup process by verifying the user
    can generate valid TOTP codes. Once verified, MFA is enabled for the account.
    """
    try:
        await mfa_service.verify_totp_setup(db, current_user, request.code)
        
        return BaseResponse(
            success=True,
            message="MFA has been successfully enabled for your account"
        )
    except (MFANotEnabledError, InvalidMFACodeError, MFAAlreadyEnabledError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify MFA setup"
        )


@router.post("/verify", response_model=BaseResponse)
async def verify_mfa(
    request: MFALoginRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> BaseResponse:
    """
    Verify MFA code during login
    
    This endpoint is used during the login process when MFA is enabled.
    It supports TOTP codes, backup codes, and SMS codes (if configured).
    """
    try:
        if request.code_type == "totp":
            await mfa_service.verify_totp(current_user, request.code)
        elif request.code_type == "backup":
            await mfa_service.verify_backup_code(db, current_user, request.code)
        elif request.code_type == "sms":
            await sms_service.verify_sms_code(current_user, request.code)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid code type"
            )
        
        return BaseResponse(
            success=True,
            message="MFA verification successful"
        )
    except (MFANotEnabledError, InvalidMFACodeError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify MFA code"
        )


@router.post("/complete-login", response_model=UserLoginResponse)
async def complete_mfa_login(
    request: MFALoginRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> UserLoginResponse:
    """
    Complete login with MFA verification
    
    This endpoint completes the login process after successful MFA verification.
    It returns the full authentication tokens.
    """
    from ..models.schemas import UserLoginResponse, TokenResponse
    from ..services.auth_service import AuthService
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        # Verify MFA code
        if request.code_type == "totp":
            await mfa_service.verify_totp(current_user, request.code)
        elif request.code_type == "backup":
            await mfa_service.verify_backup_code(db, current_user, request.code)
        elif request.code_type == "sms":
            await sms_service.verify_sms_code(current_user, request.code)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid code type"
            )
        
        # Create full session after successful MFA
        auth_service = AuthService()
        tokens = await auth_service.create_user_session(
            db, current_user, None, False
        )
        
        # Load user roles
        await db.refresh(current_user, ["roles"])
        user_roles = [role.name for role in current_user.roles]
        
        # Update last login time
        current_user.last_login_at = datetime.now(timezone.utc)
        await db.commit()
        
        # Prepare response
        response_data = {
            "user": {
                "user_id": str(current_user.id),
                "email": current_user.email,
                "username": current_user.username,
                "first_name": current_user.first_name,
                "last_name": current_user.last_name,
                "display_name": current_user.display_name,
                "is_active": current_user.is_active,
                "is_verified": current_user.is_verified,
                "roles": user_roles
            },
            "tokens": tokens
        }
        
        logger.info(f"User completed MFA login: {current_user.email}")
        
        return UserLoginResponse(
            success=True,
            message="Login successful",
            data=response_data
        )
        
    except (MFANotEnabledError, InvalidMFACodeError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"MFA login completion failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete login"
        )


@router.get("/status", response_model=MFAStatusResponse)
async def get_mfa_status(
    current_user: User = Depends(get_current_active_user)
) -> MFAStatusResponse:
    """
    Get MFA status for the current user
    
    Returns information about MFA configuration including enabled status,
    available methods, and remaining backup codes count.
    """
    try:
        status_data = await mfa_service.get_mfa_status(current_user)
        
        return MFAStatusResponse(
            success=True,
            message="MFA status retrieved",
            data=status_data
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get MFA status"
        )


@router.post("/disable", response_model=BaseResponse)
async def disable_mfa(
    request: MFADisableRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> BaseResponse:
    """
    Disable MFA for the current user
    
    Requires the user's password for verification. This will remove all
    MFA settings including the secret and backup codes.
    """
    try:
        await mfa_service.disable_mfa(db, current_user, request.password)
        
        return BaseResponse(
            success=True,
            message="MFA has been disabled for your account"
        )
    except (MFANotEnabledError, InvalidCredentialsError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to disable MFA"
        )


@router.post("/regenerate-backup-codes", response_model=MFARegenerateBackupCodesResponse)
async def regenerate_backup_codes(
    request: MFARegenerateBackupCodesRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> MFARegenerateBackupCodesResponse:
    """
    Regenerate backup codes
    
    Requires the user's password for verification. This will replace all
    existing backup codes with new ones.
    """
    try:
        # Verify password
        from ..services.auth_service import auth_service
        if not auth_service.verify_password(request.password, current_user.password_hash):
            raise InvalidCredentialsError("Invalid password")
        
        backup_codes = await mfa_service.regenerate_backup_codes(db, current_user)
        
        return MFARegenerateBackupCodesResponse(
            success=True,
            message="Backup codes regenerated successfully",
            data={
                "backup_codes": backup_codes
            }
        )
    except (MFANotEnabledError, InvalidCredentialsError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to regenerate backup codes"
        )


@router.post("/sms/send", response_model=BaseResponse)
async def send_sms_code(
    request: SMSSendCodeRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
) -> BaseResponse:
    """
    Send SMS verification code
    
    Sends a 6-digit verification code to the specified phone number.
    The code expires after 10 minutes.
    """
    try:
        await sms_service.send_sms_code(db, current_user, request.phone_number)
        
        return BaseResponse(
            success=True,
            message=f"SMS code sent to {request.phone_number}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send SMS code"
        )


@router.post("/sms/verify", response_model=BaseResponse)
async def verify_sms_code(
    request: SMSVerifyCodeRequest,
    current_user: User = Depends(get_current_active_user)
) -> BaseResponse:
    """
    Verify SMS code
    
    Verifies the SMS code sent to the user's phone number.
    """
    try:
        await sms_service.verify_sms_code(current_user, request.code)
        
        return BaseResponse(
            success=True,
            message="SMS code verified successfully"
        )
    except InvalidMFACodeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify SMS code"
        )