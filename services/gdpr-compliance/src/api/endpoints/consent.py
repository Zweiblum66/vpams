"""Consent Management API Endpoints"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from uuid import UUID

from ...db.models import UserConsent, ConsentType
from ...models.schemas import (
    ConsentCreate, ConsentUpdate, ConsentResponse,
    UserConsentsResponse
)
from ...services.audit_service import AuditService
from ..dependencies import get_db, get_current_user, get_client_ip, get_user_agent

router = APIRouter()


@router.post("/", response_model=ConsentResponse, status_code=status.HTTP_201_CREATED)
async def give_consent(
    consent_data: ConsentCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Give consent for specific data processing"""
    # Validate user can only give consent for themselves
    if str(consent_data.user_id) != current_user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot give consent for another user"
        )
    
    # Check if consent already exists
    result = await db.execute(
        select(UserConsent).where(
            and_(
                UserConsent.user_id == consent_data.user_id,
                UserConsent.consent_type == consent_data.consent_type,
                UserConsent.withdrawn == False
            )
        )
    )
    existing_consent = result.scalar_one_or_none()
    
    if existing_consent:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Active consent already exists for this type"
        )
    
    # Create new consent
    consent = UserConsent(
        user_id=consent_data.user_id,
        consent_type=consent_data.consent_type,
        consent_given=consent_data.consent_given,
        policy_version=consent_data.policy_version,
        consent_text=consent_data.consent_text,
        ip_address=consent_data.ip_address or get_client_ip(request),
        user_agent=consent_data.user_agent or get_user_agent(request)
    )
    
    db.add(consent)
    await db.commit()
    await db.refresh(consent)
    
    # Log audit event
    audit_service = AuditService(db)
    await audit_service.log_consent_given(
        user_id=consent.user_id,
        consent_type=consent.consent_type.value,
        policy_version=consent.policy_version,
        actor_id=UUID(current_user["user_id"]),
        actor_ip=get_client_ip(request)
    )
    
    return ConsentResponse(
        id=consent.id,
        user_id=consent.user_id,
        consent_type=consent.consent_type,
        consent_given=consent.consent_given,
        policy_version=consent.policy_version,
        consent_text=consent.consent_text,
        consent_date=consent.consent_date,
        withdrawn=consent.withdrawn,
        withdrawal_date=consent.withdrawal_date,
        created_at=consent.created_at,
        updated_at=consent.updated_at
    )


@router.patch("/{consent_id}", response_model=ConsentResponse)
async def withdraw_consent(
    consent_id: UUID,
    update_data: ConsentUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Withdraw previously given consent"""
    # Get consent
    result = await db.execute(
        select(UserConsent).where(UserConsent.id == consent_id)
    )
    consent = result.scalar_one_or_none()
    
    if not consent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Consent not found"
        )
    
    # Validate user can only withdraw their own consent
    if str(consent.user_id) != current_user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot withdraw consent for another user"
        )
    
    if consent.withdrawn:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Consent already withdrawn"
        )
    
    # Update consent
    consent.consent_given = update_data.consent_given
    consent.withdrawn = not update_data.consent_given
    if consent.withdrawn:
        from datetime import datetime
        consent.withdrawal_date = datetime.utcnow()
        consent.withdrawal_reason = update_data.withdrawal_reason
    
    await db.commit()
    await db.refresh(consent)
    
    # Log audit event
    audit_service = AuditService(db)
    if consent.withdrawn:
        await audit_service.log_consent_withdrawn(
            user_id=consent.user_id,
            consent_type=consent.consent_type.value,
            reason=update_data.withdrawal_reason,
            actor_id=UUID(current_user["user_id"]),
            actor_ip=get_client_ip(request)
        )
    
    return ConsentResponse(
        id=consent.id,
        user_id=consent.user_id,
        consent_type=consent.consent_type,
        consent_given=consent.consent_given,
        policy_version=consent.policy_version,
        consent_text=consent.consent_text,
        consent_date=consent.consent_date,
        withdrawn=consent.withdrawn,
        withdrawal_date=consent.withdrawal_date,
        created_at=consent.created_at,
        updated_at=consent.updated_at
    )


@router.get("/user/{user_id}", response_model=UserConsentsResponse)
async def get_user_consents(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all consents for a user"""
    # Validate user can only view their own consents (unless admin)
    if str(user_id) != current_user["user_id"] and "admin" not in current_user.get("roles", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot view consents for another user"
        )
    
    # Get all consents
    result = await db.execute(
        select(UserConsent)
        .where(UserConsent.user_id == user_id)
        .order_by(UserConsent.consent_date.desc())
    )
    consents = result.scalars().all()
    
    # Check if all required consents are given
    required_types = [ConsentType.ESSENTIAL]
    active_consent_types = {
        c.consent_type for c in consents 
        if c.consent_given and not c.withdrawn
    }
    all_required_given = all(rt in active_consent_types for rt in required_types)
    
    # Get last update time
    from datetime import datetime
    last_updated = max(
        (c.updated_at or c.created_at for c in consents),
        default=datetime.utcnow()
    )
    
    return UserConsentsResponse(
        user_id=user_id,
        consents=[
            ConsentResponse(
                id=c.id,
                user_id=c.user_id,
                consent_type=c.consent_type,
                consent_given=c.consent_given,
                policy_version=c.policy_version,
                consent_text=c.consent_text,
                consent_date=c.consent_date,
                withdrawn=c.withdrawn,
                withdrawal_date=c.withdrawal_date,
                created_at=c.created_at,
                updated_at=c.updated_at
            )
            for c in consents
        ],
        all_required_consents_given=all_required_given,
        last_updated=last_updated
    )


@router.get("/types", response_model=List[str])
async def get_consent_types():
    """Get all available consent types"""
    return [ct.value for ct in ConsentType]