"""Beta users API endpoints"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from typing import List, Optional
from datetime import datetime
import uuid

from ..core.database import get_db
from ..core.auth import get_current_user, require_admin
from ..models import BetaUser, BetaInvitation
from ..schemas.beta_user import (
    BetaUserCreate,
    BetaUserUpdate,
    BetaUserResponse,
    BetaUserListResponse,
    BetaInvitationCreate,
    BetaInvitationResponse,
    BetaRegistrationRequest,
    BetaRegistrationResponse
)
from ..services.email_service import send_beta_welcome_email, send_beta_invitation_email
from ..core.config import get_settings

router = APIRouter(prefix="/beta", tags=["Beta Users"])


@router.post("/register", response_model=BetaRegistrationResponse)
async def register_for_beta(
    request: BetaRegistrationRequest,
    db: AsyncSession = Depends(get_db)
):
    """Register for beta program"""
    settings = get_settings()
    
    # Check if registration is open
    if not settings.beta_registration_open:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Beta registration is currently closed"
        )
    
    # Check for existing registration
    result = await db.execute(
        select(BetaUser).where(
            or_(
                BetaUser.user_id == request.user_id,
                BetaUser.email == request.email
            )
        )
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already registered for beta program"
        )
    
    # Check invitation if required
    invitation = None
    if settings.beta_invitation_required and request.invitation_code:
        result = await db.execute(
            select(BetaInvitation).where(
                and_(
                    BetaInvitation.code == request.invitation_code,
                    BetaInvitation.is_used == False
                )
            )
        )
        invitation = result.scalar_one_or_none()
        
        if not invitation:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or already used invitation code"
            )
    
    # Check max beta users
    user_count = await db.scalar(select(func.count()).select_from(BetaUser))
    if user_count >= settings.max_beta_users:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Beta program is full"
        )
    
    # Create beta user
    beta_user = BetaUser(
        user_id=request.user_id,
        email=request.email,
        full_name=request.full_name,
        company=request.company,
        role=request.role,
        use_case=request.use_case,
        interested_features=request.interested_features,
        technical_level=request.technical_level,
        beta_phase=settings.beta_phase,
        invitation_code=request.invitation_code
    )
    
    # Mark invitation as used
    if invitation:
        invitation.is_used = True
        invitation.used_by = beta_user.id
        invitation.used_at = datetime.utcnow()
        invitation.current_uses += 1
    
    db.add(beta_user)
    await db.commit()
    await db.refresh(beta_user)
    
    # Send welcome email
    await send_beta_welcome_email(beta_user.email, beta_user.full_name)
    
    return BetaRegistrationResponse(
        success=True,
        message="Successfully registered for beta program",
        beta_user_id=str(beta_user.id),
        beta_phase=beta_user.beta_phase,
        feature_access_level=beta_user.feature_access_level
    )


@router.post("/invite", response_model=BetaInvitationResponse)
async def send_beta_invitation(
    invitation: BetaInvitationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Send beta invitation"""
    # Check if user is beta user
    result = await db.execute(
        select(BetaUser).where(BetaUser.user_id == current_user["user_id"])
    )
    beta_user = result.scalar_one_or_none()
    
    if not beta_user and not current_user.get("is_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only beta users and admins can send invitations"
        )
    
    # Check for existing invitation
    result = await db.execute(
        select(BetaInvitation).where(BetaInvitation.email == invitation.email)
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation already sent to this email"
        )
    
    # Create invitation
    code = str(uuid.uuid4()).replace("-", "")[:8].upper()
    beta_invitation = BetaInvitation(
        code=code,
        email=invitation.email,
        invited_by=beta_user.id if beta_user else None,
        invitation_type=invitation.invitation_type,
        valid_until=invitation.valid_until,
        max_uses=invitation.max_uses,
        notes=invitation.notes
    )
    
    db.add(beta_invitation)
    await db.commit()
    await db.refresh(beta_invitation)
    
    # Send invitation email
    await send_beta_invitation_email(
        invitation.email,
        code,
        beta_user.full_name if beta_user else "MAMS Team"
    )
    
    return BetaInvitationResponse(
        id=str(beta_invitation.id),
        code=beta_invitation.code,
        email=beta_invitation.email,
        invitation_type=beta_invitation.invitation_type,
        valid_until=beta_invitation.valid_until,
        created_at=beta_invitation.created_at
    )


@router.get("/users", response_model=BetaUserListResponse)
async def list_beta_users(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    beta_phase: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """List beta users (admin only)"""
    # Build query
    query = select(BetaUser)
    
    # Apply filters
    if search:
        query = query.where(
            or_(
                BetaUser.email.ilike(f"%{search}%"),
                BetaUser.full_name.ilike(f"%{search}%"),
                BetaUser.company.ilike(f"%{search}%")
            )
        )
    
    if beta_phase:
        query = query.where(BetaUser.beta_phase == beta_phase)
    
    if is_active is not None:
        query = query.where(BetaUser.is_active == is_active)
    
    # Get total count
    count_query = select(func.count()).select_from(BetaUser)
    if search or beta_phase or is_active is not None:
        count_query = query.with_only_columns([func.count()])
    total = await db.scalar(count_query)
    
    # Apply pagination
    query = query.offset((page - 1) * limit).limit(limit)
    query = query.order_by(BetaUser.joined_at.desc())
    
    # Execute query
    result = await db.execute(query)
    users = result.scalars().all()
    
    return BetaUserListResponse(
        users=[BetaUserResponse.from_orm(user) for user in users],
        total=total,
        page=page,
        limit=limit,
        pages=(total + limit - 1) // limit
    )


@router.get("/users/{user_id}", response_model=BetaUserResponse)
async def get_beta_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get beta user details"""
    # Check permission
    if not current_user.get("is_admin") and str(current_user["user_id"]) != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only view own beta profile"
        )
    
    result = await db.execute(
        select(BetaUser).where(BetaUser.user_id == user_id)
    )
    beta_user = result.scalar_one_or_none()
    
    if not beta_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Beta user not found"
        )
    
    return BetaUserResponse.from_orm(beta_user)


@router.put("/users/{user_id}", response_model=BetaUserResponse)
async def update_beta_user(
    user_id: str,
    update: BetaUserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update beta user"""
    # Check permission
    is_self = str(current_user["user_id"]) == user_id
    is_admin = current_user.get("is_admin", False)
    
    if not is_admin and not is_self:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only update own beta profile"
        )
    
    # Get beta user
    result = await db.execute(
        select(BetaUser).where(BetaUser.user_id == user_id)
    )
    beta_user = result.scalar_one_or_none()
    
    if not beta_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Beta user not found"
        )
    
    # Update allowed fields
    update_data = update.dict(exclude_unset=True)
    
    # Restrict fields for non-admins
    if not is_admin:
        admin_only_fields = [
            "is_active", "feature_access_level", "beta_phase",
            "engagement_score", "notes", "tags"
        ]
        for field in admin_only_fields:
            update_data.pop(field, None)
    
    for field, value in update_data.items():
        setattr(beta_user, field, value)
    
    beta_user.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(beta_user)
    
    return BetaUserResponse.from_orm(beta_user)


@router.delete("/users/{user_id}")
async def remove_from_beta(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Remove user from beta program (admin only)"""
    result = await db.execute(
        select(BetaUser).where(BetaUser.user_id == user_id)
    )
    beta_user = result.scalar_one_or_none()
    
    if not beta_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Beta user not found"
        )
    
    await db.delete(beta_user)
    await db.commit()
    
    return {"message": "User removed from beta program"}