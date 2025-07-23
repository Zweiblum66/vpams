"""Privacy Policy Management API Endpoints"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from uuid import UUID
from datetime import datetime

from ...db.models import PrivacyPolicy
from ...models.schemas import (
    PrivacyPolicyBase, PrivacyPolicyCreate,
    PrivacyPolicyResponse, PrivacyPolicyAcceptance
)
from ...services.audit_service import AuditService
from ..dependencies import get_db, get_current_user, require_admin, get_client_ip

router = APIRouter()


@router.post("/", response_model=PrivacyPolicyResponse, status_code=status.HTTP_201_CREATED)
async def create_privacy_policy(
    policy_data: PrivacyPolicyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Create a new privacy policy version (admin only)"""
    # Check if version already exists
    result = await db.execute(
        select(PrivacyPolicy).where(PrivacyPolicy.version == policy_data.version)
    )
    existing_policy = result.scalar_one_or_none()
    
    if existing_policy:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Privacy policy version {policy_data.version} already exists"
        )
    
    # Deactivate current active policy if new one requires re-consent
    if policy_data.requires_re_consent:
        result = await db.execute(
            select(PrivacyPolicy).where(PrivacyPolicy.is_active == True)
        )
        active_policies = result.scalars().all()
        
        for policy in active_policies:
            policy.is_active = False
    
    # Create new policy
    policy = PrivacyPolicy(
        version=policy_data.version,
        title=policy_data.title,
        content=policy_data.content,
        summary=policy_data.summary,
        language=policy_data.language,
        effective_date=policy_data.effective_date,
        change_summary=policy_data.change_summary,
        requires_re_consent=policy_data.requires_re_consent,
        created_by=policy_data.created_by
    )
    
    db.add(policy)
    await db.commit()
    await db.refresh(policy)
    
    return PrivacyPolicyResponse(
        id=policy.id,
        version=policy.version,
        title=policy.title,
        content=policy.content,
        summary=policy.summary,
        language=policy.language,
        effective_date=policy.effective_date,
        change_summary=policy.change_summary,
        requires_re_consent=policy.requires_re_consent,
        is_active=policy.is_active,
        created_at=policy.created_at,
        updated_at=policy.updated_at
    )


@router.get("/current", response_model=PrivacyPolicyResponse)
async def get_current_privacy_policy(
    language: str = "en",
    db: AsyncSession = Depends(get_db)
):
    """Get the current active privacy policy"""
    result = await db.execute(
        select(PrivacyPolicy).where(
            and_(
                PrivacyPolicy.is_active == True,
                PrivacyPolicy.language == language,
                PrivacyPolicy.effective_date <= datetime.utcnow()
            )
        ).order_by(PrivacyPolicy.effective_date.desc())
    )
    policy = result.scalar_one_or_none()
    
    if not policy:
        # Fall back to English if requested language not found
        if language != "en":
            result = await db.execute(
                select(PrivacyPolicy).where(
                    and_(
                        PrivacyPolicy.is_active == True,
                        PrivacyPolicy.language == "en",
                        PrivacyPolicy.effective_date <= datetime.utcnow()
                    )
                ).order_by(PrivacyPolicy.effective_date.desc())
            )
            policy = result.scalar_one_or_none()
    
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active privacy policy found"
        )
    
    return PrivacyPolicyResponse(
        id=policy.id,
        version=policy.version,
        title=policy.title,
        content=policy.content,
        summary=policy.summary,
        language=policy.language,
        effective_date=policy.effective_date,
        change_summary=policy.change_summary,
        requires_re_consent=policy.requires_re_consent,
        is_active=policy.is_active,
        created_at=policy.created_at,
        updated_at=policy.updated_at
    )


@router.get("/version/{version}", response_model=PrivacyPolicyResponse)
async def get_privacy_policy_by_version(
    version: str,
    language: str = "en",
    db: AsyncSession = Depends(get_db)
):
    """Get a specific privacy policy version"""
    result = await db.execute(
        select(PrivacyPolicy).where(
            and_(
                PrivacyPolicy.version == version,
                PrivacyPolicy.language == language
            )
        )
    )
    policy = result.scalar_one_or_none()
    
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Privacy policy version {version} not found"
        )
    
    return PrivacyPolicyResponse(
        id=policy.id,
        version=policy.version,
        title=policy.title,
        content=policy.content,
        summary=policy.summary,
        language=policy.language,
        effective_date=policy.effective_date,
        change_summary=policy.change_summary,
        requires_re_consent=policy.requires_re_consent,
        is_active=policy.is_active,
        created_at=policy.created_at,
        updated_at=policy.updated_at
    )


@router.get("/", response_model=List[PrivacyPolicyResponse])
async def list_privacy_policies(
    language: Optional[str] = None,
    active_only: bool = False,
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """List all privacy policy versions"""
    query = select(PrivacyPolicy)
    
    conditions = []
    if language:
        conditions.append(PrivacyPolicy.language == language)
    if active_only:
        conditions.append(PrivacyPolicy.is_active == True)
    
    if conditions:
        query = query.where(and_(*conditions))
    
    query = query.order_by(PrivacyPolicy.effective_date.desc())
    query = query.limit(limit).offset(offset)
    
    result = await db.execute(query)
    policies = result.scalars().all()
    
    return [
        PrivacyPolicyResponse(
            id=p.id,
            version=p.version,
            title=p.title,
            content=p.content,
            summary=p.summary,
            language=p.language,
            effective_date=p.effective_date,
            change_summary=p.change_summary,
            requires_re_consent=p.requires_re_consent,
            is_active=p.is_active,
            created_at=p.created_at,
            updated_at=p.updated_at
        )
        for p in policies
    ]


@router.post("/accept", status_code=status.HTTP_204_NO_CONTENT)
async def accept_privacy_policy(
    acceptance: PrivacyPolicyAcceptance,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Record user acceptance of privacy policy"""
    # Validate user can only accept for themselves
    if str(acceptance.user_id) != current_user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot accept privacy policy for another user"
        )
    
    # Verify policy version exists
    result = await db.execute(
        select(PrivacyPolicy).where(PrivacyPolicy.version == acceptance.policy_version)
    )
    policy = result.scalar_one_or_none()
    
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Privacy policy version {acceptance.policy_version} not found"
        )
    
    # Log acceptance
    audit_service = AuditService(db)
    await audit_service.log_policy_acceptance(
        user_id=acceptance.user_id,
        policy_version=acceptance.policy_version,
        accepted=acceptance.accepted,
        actor_ip=acceptance.ip_address or get_client_ip(request)
    )
    
    # Note: In a real implementation, you would also update a user_policy_acceptances table
    # to track which policies each user has accepted
    
    return None


@router.patch("/{policy_id}/activate", response_model=PrivacyPolicyResponse)
async def activate_privacy_policy(
    policy_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Activate a privacy policy version (admin only)"""
    # Get policy
    result = await db.execute(
        select(PrivacyPolicy).where(PrivacyPolicy.id == policy_id)
    )
    policy = result.scalar_one_or_none()
    
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Privacy policy not found"
        )
    
    if policy.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Policy is already active"
        )
    
    # Check if effective date has passed
    if policy.effective_date > datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Policy effective date ({policy.effective_date}) has not arrived yet"
        )
    
    # Deactivate other policies of same language
    result = await db.execute(
        select(PrivacyPolicy).where(
            and_(
                PrivacyPolicy.is_active == True,
                PrivacyPolicy.language == policy.language,
                PrivacyPolicy.id != policy_id
            )
        )
    )
    active_policies = result.scalars().all()
    
    for active_policy in active_policies:
        active_policy.is_active = False
    
    # Activate this policy
    policy.is_active = True
    await db.commit()
    await db.refresh(policy)
    
    return PrivacyPolicyResponse(
        id=policy.id,
        version=policy.version,
        title=policy.title,
        content=policy.content,
        summary=policy.summary,
        language=policy.language,
        effective_date=policy.effective_date,
        change_summary=policy.change_summary,
        requires_re_consent=policy.requires_re_consent,
        is_active=policy.is_active,
        created_at=policy.created_at,
        updated_at=policy.updated_at
    )