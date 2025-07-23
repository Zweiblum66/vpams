"""
Account management API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from typing import List, Optional
from datetime import datetime
import logging

from src.db.base import get_db
from src.db.models import Organization, OrganizationUser
from src.models.schemas import (
    OrganizationResponse,
    OrganizationUpdate,
    OrganizationUserResponse,
    UserInvite,
    UserRole
)
from src.core.auth import get_current_user, require_role
from src.services.email import EmailService
from src.services.user_service import UserService

router = APIRouter()
logger = logging.getLogger(__name__)
email_service = EmailService()
user_service = UserService()


@router.get("/", response_model=OrganizationResponse)
async def get_organization(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get organization details"""
    org = await db.get(Organization, current_user.organization_id)
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    return org


@router.put("/", response_model=OrganizationResponse)
async def update_organization(
    update_data: OrganizationUpdate,
    current_user=Depends(require_role(["admin", "billing"])),
    db: AsyncSession = Depends(get_db)
):
    """Update organization details"""
    org = await db.get(Organization, current_user.organization_id)
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    # Update fields
    for field, value in update_data.dict(exclude_unset=True).items():
        setattr(org, field, value)
    
    org.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(org)
    
    logger.info(f"Organization {org.id} updated by user {current_user.id}")
    return org


@router.get("/users", response_model=List[OrganizationUserResponse])
async def list_organization_users(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    role: Optional[str] = None,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List organization users"""
    query = select(OrganizationUser).where(
        OrganizationUser.organization_id == current_user.organization_id
    )
    
    if role:
        query = query.where(OrganizationUser.role == role)
    
    # Pagination
    offset = (page - 1) * limit
    query = query.offset(offset).limit(limit)
    
    result = await db.execute(query)
    org_users = result.scalars().all()
    
    # Fetch user details from user service
    user_ids = [ou.user_id for ou in org_users]
    user_details = await user_service.get_users_by_ids(user_ids)
    
    # Combine organization user data with user details
    response = []
    for org_user in org_users:
        user_detail = user_details.get(str(org_user.user_id), {})
        response.append(OrganizationUserResponse(
            id=org_user.id,
            user_id=org_user.user_id,
            email=user_detail.get("email", ""),
            name=user_detail.get("name", ""),
            role=org_user.role,
            is_primary=org_user.is_primary,
            joined_at=org_user.joined_at,
            last_login=user_detail.get("last_login")
        ))
    
    return response


@router.post("/users/invite", status_code=status.HTTP_201_CREATED)
async def invite_user(
    invite: UserInvite,
    current_user=Depends(require_role(["admin"])),
    db: AsyncSession = Depends(get_db)
):
    """Invite new user to organization"""
    # Check if user already exists in organization
    existing = await db.execute(
        select(OrganizationUser).where(
            OrganizationUser.organization_id == current_user.organization_id,
            OrganizationUser.user_id == invite.user_id
        )
    )
    if existing.scalar():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already in organization"
        )
    
    # Get organization details
    org = await db.get(Organization, current_user.organization_id)
    
    # Check user limit
    if org.subscription and org.subscription.user_limit:
        current_count = await db.execute(
            select(func.count()).select_from(OrganizationUser).where(
                OrganizationUser.organization_id == current_user.organization_id
            )
        )
        if current_count.scalar() >= org.subscription.user_limit:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Organization user limit reached"
            )
    
    # Create invitation in user service
    invitation_result = await user_service.create_invitation(
        email=invite.email,
        organization_id=current_user.organization_id,
        role=invite.role,
        invited_by=current_user.id
    )
    
    # Send invitation email
    await email_service.send_invitation(
        to_email=invite.email,
        inviter_name=current_user.name,
        organization_name=org.name,
        invitation_link=invitation_result["invitation_link"]
    )
    
    logger.info(f"User {invite.email} invited to organization {org.id}")
    
    return {
        "message": "Invitation sent successfully",
        "invitation_id": invitation_result["id"]
    }


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_user(
    user_id: str,
    current_user=Depends(require_role(["admin"])),
    db: AsyncSession = Depends(get_db)
):
    """Remove user from organization"""
    # Check if user exists in organization
    org_user = await db.execute(
        select(OrganizationUser).where(
            OrganizationUser.organization_id == current_user.organization_id,
            OrganizationUser.user_id == user_id
        )
    )
    org_user = org_user.scalar()
    
    if not org_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in organization"
        )
    
    # Prevent removing primary admin
    if org_user.is_primary:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove primary administrator"
        )
    
    # Remove user
    await db.delete(org_user)
    await db.commit()
    
    # Update subscription user count
    await db.execute(
        update(Subscription).where(
            Subscription.organization_id == current_user.organization_id
        ).values(current_users=Subscription.current_users - 1)
    )
    await db.commit()
    
    logger.info(f"User {user_id} removed from organization {current_user.organization_id}")


@router.put("/users/{user_id}/role", response_model=OrganizationUserResponse)
async def update_user_role(
    user_id: str,
    role: UserRole,
    current_user=Depends(require_role(["admin"])),
    db: AsyncSession = Depends(get_db)
):
    """Update user role in organization"""
    # Get organization user
    org_user = await db.execute(
        select(OrganizationUser).where(
            OrganizationUser.organization_id == current_user.organization_id,
            OrganizationUser.user_id == user_id
        )
    )
    org_user = org_user.scalar()
    
    if not org_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in organization"
        )
    
    # Update role
    org_user.role = role.value
    await db.commit()
    await db.refresh(org_user)
    
    # Get user details
    user_detail = await user_service.get_user_by_id(user_id)
    
    logger.info(f"User {user_id} role updated to {role.value} in organization {current_user.organization_id}")
    
    return OrganizationUserResponse(
        id=org_user.id,
        user_id=org_user.user_id,
        email=user_detail.get("email", ""),
        name=user_detail.get("name", ""),
        role=org_user.role,
        is_primary=org_user.is_primary,
        joined_at=org_user.joined_at,
        last_login=user_detail.get("last_login")
    )