"""
Partner management routes
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_, or_

from ..core.logging import get_logger
from ..core.exceptions import PartnerNotFoundError, PartnerPermissionError
from ..db.base import get_db
from ..db.models import Partner, PartnerContact, PartnerActivity, PartnerTypeEnum, PartnerStatusEnum, PartnerTierEnum
from ..models.schemas import (
    PartnerCreate, PartnerUpdate, PartnerResponse, PartnerListResponse,
    PartnerContactCreate, PartnerContactUpdate, PartnerContactResponse
)
from .dependencies import get_current_user

logger = get_logger(__name__)

router = APIRouter()


@router.post("/", response_model=PartnerResponse, status_code=status.HTTP_201_CREATED)
async def create_partner(
    partner_data: PartnerCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new partner"""
    import uuid
    
    # Generate partner code
    partner_code = f"PART-{str(uuid.uuid4())[:8].upper()}"
    
    # Create partner
    partner = Partner(
        id=str(uuid.uuid4()),
        partner_code=partner_code,
        **partner_data.dict(exclude_unset=True)
    )
    
    db.add(partner)
    await db.commit()
    await db.refresh(partner)
    
    # Log activity
    await log_partner_activity(
        db, partner.id, "partner_created", "management",
        title="Partner Created",
        description=f"Partner {partner.company_name} was created",
        user_id=current_user.get("id"),
        user_email=current_user.get("email")
    )
    
    logger.info(f"Partner created: {partner.id}")
    return PartnerResponse.from_orm(partner)


@router.get("/", response_model=PartnerListResponse)
async def list_partners(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    partner_type: Optional[PartnerTypeEnum] = Query(None),
    status: Optional[PartnerStatusEnum] = Query(None),
    tier: Optional[PartnerTierEnum] = Query(None),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List partners with filtering and pagination"""
    
    # Build query
    query = select(Partner)
    
    # Apply filters
    if search:
        query = query.where(
            or_(
                Partner.company_name.ilike(f"%{search}%"),
                Partner.display_name.ilike(f"%{search}%"),
                Partner.partner_code.ilike(f"%{search}%")
            )
        )
    
    if partner_type:
        query = query.where(Partner.partner_type == partner_type)
    
    if status:
        query = query.where(Partner.status == status)
    
    if tier:
        query = query.where(Partner.partner_tier == tier)
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Apply pagination and ordering
    offset = (page - 1) * limit
    query = query.order_by(desc(Partner.created_at)).offset(offset).limit(limit)
    
    # Execute query
    result = await db.execute(query)
    partners = result.scalars().all()
    
    return PartnerListResponse(
        partners=[PartnerResponse.from_orm(partner) for partner in partners],
        total=total,
        page=page,
        limit=limit
    )


@router.get("/{partner_id}", response_model=PartnerResponse)
async def get_partner(
    partner_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific partner"""
    result = await db.execute(select(Partner).where(Partner.id == partner_id))
    partner = result.scalar_one_or_none()
    
    if not partner:
        raise PartnerNotFoundError(partner_id)
    
    return PartnerResponse.from_orm(partner)


@router.put("/{partner_id}", response_model=PartnerResponse)
async def update_partner(
    partner_id: str,
    partner_data: PartnerUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a partner"""
    result = await db.execute(select(Partner).where(Partner.id == partner_id))
    partner = result.scalar_one_or_none()
    
    if not partner:
        raise PartnerNotFoundError(partner_id)
    
    # Update partner fields
    update_data = partner_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(partner, field, value)
    
    await db.commit()
    await db.refresh(partner)
    
    # Log activity
    await log_partner_activity(
        db, partner.id, "partner_updated", "management",
        title="Partner Updated",
        description=f"Partner {partner.company_name} was updated",
        user_id=current_user.get("id"),
        user_email=current_user.get("email")
    )
    
    logger.info(f"Partner updated: {partner.id}")
    return PartnerResponse.from_orm(partner)


@router.delete("/{partner_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_partner(
    partner_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a partner"""
    result = await db.execute(select(Partner).where(Partner.id == partner_id))
    partner = result.scalar_one_or_none()
    
    if not partner:
        raise PartnerNotFoundError(partner_id)
    
    # Log activity before deletion
    await log_partner_activity(
        db, partner.id, "partner_deleted", "management",
        title="Partner Deleted",
        description=f"Partner {partner.company_name} was deleted",
        user_id=current_user.get("id"),
        user_email=current_user.get("email")
    )
    
    await db.delete(partner)
    await db.commit()
    
    logger.info(f"Partner deleted: {partner.id}")


@router.post("/{partner_id}/contacts", response_model=PartnerContactResponse, status_code=status.HTTP_201_CREATED)
async def create_partner_contact(
    partner_id: str,
    contact_data: PartnerContactCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new partner contact"""
    import uuid
    
    # Verify partner exists
    partner_result = await db.execute(select(Partner).where(Partner.id == partner_id))
    partner = partner_result.scalar_one_or_none()
    
    if not partner:
        raise PartnerNotFoundError(partner_id)
    
    # If this is set as primary, remove primary from other contacts
    if contact_data.is_primary:
        await db.execute(
            db.update(PartnerContact)
            .where(PartnerContact.partner_id == partner_id)
            .values(is_primary=False)
        )
    
    # Create contact
    contact = PartnerContact(
        id=str(uuid.uuid4()),
        partner_id=partner_id,
        **contact_data.dict()
    )
    
    db.add(contact)
    await db.commit()
    await db.refresh(contact)
    
    # Log activity
    await log_partner_activity(
        db, partner_id, "contact_created", "management",
        title="Contact Added",
        description=f"Contact {contact.first_name} {contact.last_name} was added",
        user_id=current_user.get("id"),
        user_email=current_user.get("email")
    )
    
    logger.info(f"Partner contact created: {contact.id}")
    return PartnerContactResponse.from_orm(contact)


@router.get("/{partner_id}/contacts", response_model=List[PartnerContactResponse])
async def list_partner_contacts(
    partner_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List partner contacts"""
    # Verify partner exists
    partner_result = await db.execute(select(Partner).where(Partner.id == partner_id))
    partner = partner_result.scalar_one_or_none()
    
    if not partner:
        raise PartnerNotFoundError(partner_id)
    
    # Get contacts
    result = await db.execute(
        select(PartnerContact)
        .where(PartnerContact.partner_id == partner_id)
        .order_by(PartnerContact.is_primary.desc(), PartnerContact.created_at)
    )
    contacts = result.scalars().all()
    
    return [PartnerContactResponse.from_orm(contact) for contact in contacts]


@router.put("/{partner_id}/contacts/{contact_id}", response_model=PartnerContactResponse)
async def update_partner_contact(
    partner_id: str,
    contact_id: str,
    contact_data: PartnerContactUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a partner contact"""
    # Verify partner exists
    partner_result = await db.execute(select(Partner).where(Partner.id == partner_id))
    partner = partner_result.scalar_one_or_none()
    
    if not partner:
        raise PartnerNotFoundError(partner_id)
    
    # Get contact
    contact_result = await db.execute(
        select(PartnerContact).where(
            and_(PartnerContact.id == contact_id, PartnerContact.partner_id == partner_id)
        )
    )
    contact = contact_result.scalar_one_or_none()
    
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    # If setting as primary, remove primary from other contacts
    if contact_data.is_primary:
        await db.execute(
            db.update(PartnerContact)
            .where(
                and_(
                    PartnerContact.partner_id == partner_id,
                    PartnerContact.id != contact_id
                )
            )
            .values(is_primary=False)
        )
    
    # Update contact
    update_data = contact_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(contact, field, value)
    
    await db.commit()
    await db.refresh(contact)
    
    # Log activity
    await log_partner_activity(
        db, partner_id, "contact_updated", "management",
        title="Contact Updated",
        description=f"Contact {contact.first_name} {contact.last_name} was updated",
        user_id=current_user.get("id"),
        user_email=current_user.get("email")
    )
    
    logger.info(f"Partner contact updated: {contact.id}")
    return PartnerContactResponse.from_orm(contact)


@router.delete("/{partner_id}/contacts/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_partner_contact(
    partner_id: str,
    contact_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a partner contact"""
    # Verify partner exists
    partner_result = await db.execute(select(Partner).where(Partner.id == partner_id))
    partner = partner_result.scalar_one_or_none()
    
    if not partner:
        raise PartnerNotFoundError(partner_id)
    
    # Get contact
    contact_result = await db.execute(
        select(PartnerContact).where(
            and_(PartnerContact.id == contact_id, PartnerContact.partner_id == partner_id)
        )
    )
    contact = contact_result.scalar_one_or_none()
    
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    # Log activity before deletion
    await log_partner_activity(
        db, partner_id, "contact_deleted", "management",
        title="Contact Deleted",
        description=f"Contact {contact.first_name} {contact.last_name} was deleted",
        user_id=current_user.get("id"),
        user_email=current_user.get("email")
    )
    
    await db.delete(contact)
    await db.commit()
    
    logger.info(f"Partner contact deleted: {contact.id}")


async def log_partner_activity(
    db: AsyncSession,
    partner_id: str,
    activity_type: str,
    activity_category: str,
    title: str = None,
    description: str = None,
    user_id: str = None,
    user_email: str = None,
    metadata: dict = None
):
    """Log partner activity"""
    import uuid
    
    activity = PartnerActivity(
        id=str(uuid.uuid4()),
        partner_id=partner_id,
        activity_type=activity_type,
        activity_category=activity_category,
        title=title,
        description=description,
        user_id=user_id,
        user_email=user_email,
        metadata=metadata or {}
    )
    
    db.add(activity)
    await db.commit()