"""Business logic for lead management"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, or_
from typing import List, Optional, Dict, Any
from uuid import UUID
import logging
from datetime import datetime

from ..db.models import Lead, LeadActivity, LeadStatusEnum
from ..models.schemas import (
    LeadCreate, LeadUpdate, LeadResponse,
    LeadActivityCreate, ActivityResponse,
    PaginationParams
)
from ..core.exceptions import NotFoundError, ValidationError

logger = logging.getLogger(__name__)


class LeadService:
    """Service for lead management operations"""
    
    @staticmethod
    async def create_lead(
        db: AsyncSession,
        lead_data: LeadCreate,
        current_user_id: UUID
    ) -> LeadResponse:
        """Create a new lead"""
        try:
            # Check if lead already exists for this reseller
            stmt = select(Lead).where(
                and_(
                    Lead.reseller_id == lead_data.reseller_id,
                    Lead.email == lead_data.email
                )
            )
            existing = await db.execute(stmt)
            if existing.scalar_one_or_none():
                raise ValidationError("Lead with this email already exists for this reseller")
            
            # Create lead
            lead = Lead(**lead_data.model_dump())
            lead.score = LeadService._calculate_lead_score(lead_data)
            
            db.add(lead)
            await db.commit()
            await db.refresh(lead)
            
            # Create initial activity record
            activity = LeadActivity(
                lead_id=lead.id,
                user_id=current_user_id,
                activity_type="lead_created",
                subject="Lead Created",
                description=f"Lead {lead.company_name} was added to the system"
            )
            db.add(activity)
            await db.commit()
            
            logger.info(f"Created lead {lead.id} for reseller {lead_data.reseller_id}")
            return LeadResponse.model_validate(lead)
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating lead: {e}")
            raise
    
    @staticmethod
    async def get_lead(db: AsyncSession, lead_id: UUID) -> Optional[LeadResponse]:
        """Get lead by ID"""
        stmt = select(Lead).where(Lead.id == lead_id)
        result = await db.execute(stmt)
        lead = result.scalar_one_or_none()
        
        if not lead:
            return None
            
        return LeadResponse.model_validate(lead)
    
    @staticmethod
    async def list_leads(
        db: AsyncSession,
        reseller_id: UUID,
        pagination: PaginationParams,
        status: Optional[LeadStatusEnum] = None,
        search: Optional[str] = None
    ) -> Dict[str, Any]:
        """List leads for a reseller with filtering and pagination"""
        
        # Build query
        stmt = select(Lead).where(Lead.reseller_id == reseller_id)
        
        # Apply filters
        filters = []
        if status:
            filters.append(Lead.status == status)
        if search:
            search_filter = or_(
                Lead.company_name.ilike(f"%{search}%"),
                Lead.contact_name.ilike(f"%{search}%"),
                Lead.email.ilike(f"%{search}%")
            )
            filters.append(search_filter)
        
        if filters:
            stmt = stmt.where(and_(*filters))
        
        # Get total count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await db.execute(count_stmt)
        total = total_result.scalar()
        
        # Apply sorting
        if pagination.sort_by == "company_name":
            sort_column = Lead.company_name
        elif pagination.sort_by == "status":
            sort_column = Lead.status
        elif pagination.sort_by == "score":
            sort_column = Lead.score
        elif pagination.sort_by == "estimated_value":
            sort_column = Lead.estimated_value
        else:
            sort_column = Lead.created_at
        
        if pagination.sort_order == "desc":
            stmt = stmt.order_by(sort_column.desc())
        else:
            stmt = stmt.order_by(sort_column.asc())
        
        # Apply pagination
        offset = (pagination.page - 1) * pagination.limit
        stmt = stmt.offset(offset).limit(pagination.limit)
        
        # Execute query
        result = await db.execute(stmt)
        leads = result.scalars().all()
        
        # Calculate pagination info
        pages = (total + pagination.limit - 1) // pagination.limit
        has_next = pagination.page < pages
        has_prev = pagination.page > 1
        
        return {
            "items": [LeadResponse.model_validate(l) for l in leads],
            "total": total,
            "page": pagination.page,
            "pages": pages,
            "has_next": has_next,
            "has_prev": has_prev
        }
    
    @staticmethod
    async def update_lead(
        db: AsyncSession,
        lead_id: UUID,
        lead_data: LeadUpdate,
        current_user_id: UUID
    ) -> Optional[LeadResponse]:
        """Update lead"""
        try:
            # Get existing lead
            stmt = select(Lead).where(Lead.id == lead_id)
            result = await db.execute(stmt)
            lead = result.scalar_one_or_none()
            
            if not lead:
                return None
            
            # Track status changes for activity log
            old_status = lead.status
            
            # Update fields
            update_data = lead_data.model_dump(exclude_unset=True)
            if update_data:
                for field, value in update_data.items():
                    setattr(lead, field, value)
                
                # Recalculate score if relevant fields changed
                if any(field in update_data for field in ['estimated_value', 'probability', 'company_size', 'industry']):
                    lead.score = LeadService._calculate_lead_score_from_lead(lead)
                
                lead.updated_at = datetime.utcnow()
                await db.commit()
                await db.refresh(lead)
                
                # Log status change if it occurred
                if old_status != lead.status:
                    activity = LeadActivity(
                        lead_id=lead.id,
                        user_id=current_user_id,
                        activity_type="status_change",
                        subject="Status Changed",
                        description=f"Lead status changed from {old_status} to {lead.status}"
                    )
                    db.add(activity)
                    await db.commit()
            
            logger.info(f"Updated lead {lead_id}")
            return LeadResponse.model_validate(lead)
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Error updating lead {lead_id}: {e}")
            raise
    
    @staticmethod
    async def delete_lead(db: AsyncSession, lead_id: UUID, current_user_id: UUID) -> bool:
        """Delete lead"""
        try:
            stmt = delete(Lead).where(Lead.id == lead_id)
            result = await db.execute(stmt)
            await db.commit()
            
            deleted = result.rowcount > 0
            if deleted:
                logger.info(f"Deleted lead {lead_id}")
            
            return deleted
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Error deleting lead {lead_id}: {e}")
            raise
    
    @staticmethod
    async def add_lead_activity(
        db: AsyncSession,
        activity_data: LeadActivityCreate,
        current_user_id: UUID
    ) -> ActivityResponse:
        """Add activity record for a lead"""
        try:
            # Verify lead exists
            lead_stmt = select(Lead).where(Lead.id == activity_data.lead_id)
            lead_result = await db.execute(lead_stmt)
            lead = lead_result.scalar_one_or_none()
            
            if not lead:
                raise NotFoundError("Lead not found")
            
            # Create activity
            activity = LeadActivity(**activity_data.model_dump())
            db.add(activity)
            
            # Update last contact date
            lead.last_contact_date = datetime.utcnow()
            
            await db.commit()
            await db.refresh(activity)
            
            logger.info(f"Added activity {activity.id} for lead {activity_data.lead_id}")
            return ActivityResponse.model_validate(activity)
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Error adding lead activity: {e}")
            raise
    
    @staticmethod
    async def get_lead_activities(
        db: AsyncSession,
        lead_id: UUID,
        pagination: PaginationParams
    ) -> Dict[str, Any]:
        """Get activities for a lead"""
        
        # Build query
        stmt = select(LeadActivity).where(LeadActivity.lead_id == lead_id)
        
        # Get total count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await db.execute(count_stmt)
        total = total_result.scalar()
        
        # Apply sorting (always by created_at desc for activities)
        stmt = stmt.order_by(LeadActivity.created_at.desc())
        
        # Apply pagination
        offset = (pagination.page - 1) * pagination.limit
        stmt = stmt.offset(offset).limit(pagination.limit)
        
        # Execute query
        result = await db.execute(stmt)
        activities = result.scalars().all()
        
        # Calculate pagination info
        pages = (total + pagination.limit - 1) // pagination.limit
        has_next = pagination.page < pages
        has_prev = pagination.page > 1
        
        return {
            "items": [ActivityResponse.model_validate(a) for a in activities],
            "total": total,
            "page": pagination.page,
            "pages": pages,
            "has_next": has_next,
            "has_prev": has_prev
        }
    
    @staticmethod
    def _calculate_lead_score(lead_data) -> int:
        """Calculate lead score based on various factors"""
        score = 0
        
        # Base score
        score += 10
        
        # Company size scoring
        if hasattr(lead_data, 'company_size') and lead_data.company_size:
            size_scores = {
                "1-10": 5,
                "11-50": 15,
                "51-200": 25,
                "201-1000": 35,
                "1000+": 45
            }
            score += size_scores.get(lead_data.company_size, 0)
        
        # Estimated value scoring
        if hasattr(lead_data, 'estimated_value') and lead_data.estimated_value:
            if lead_data.estimated_value >= 100000:
                score += 30
            elif lead_data.estimated_value >= 50000:
                score += 20
            elif lead_data.estimated_value >= 10000:
                score += 15
            elif lead_data.estimated_value >= 5000:
                score += 10
            else:
                score += 5
        
        # Industry scoring (some industries are better fits)
        if hasattr(lead_data, 'industry') and lead_data.industry:
            high_value_industries = ["media", "broadcast", "production", "entertainment"]
            if any(industry in lead_data.industry.lower() for industry in high_value_industries):
                score += 15
        
        # Source scoring
        if hasattr(lead_data, 'source') and lead_data.source:
            source_scores = {
                "referral": 20,
                "website": 15,
                "event": 15,
                "cold_call": 5,
                "email": 8,
                "social": 10
            }
            score += source_scores.get(lead_data.source.lower(), 0)
        
        return min(score, 100)  # Cap at 100
    
    @staticmethod
    def _calculate_lead_score_from_lead(lead: Lead) -> int:
        """Calculate lead score from existing lead object"""
        score = 0
        
        # Base score
        score += 10
        
        # Company size scoring
        if lead.company_size:
            size_scores = {
                "1-10": 5,
                "11-50": 15,
                "51-200": 25,
                "201-1000": 35,
                "1000+": 45
            }
            score += size_scores.get(lead.company_size, 0)
        
        # Estimated value scoring
        if lead.estimated_value:
            if lead.estimated_value >= 100000:
                score += 30
            elif lead.estimated_value >= 50000:
                score += 20
            elif lead.estimated_value >= 10000:
                score += 15
            elif lead.estimated_value >= 5000:
                score += 10
            else:
                score += 5
        
        # Industry scoring
        if lead.industry:
            high_value_industries = ["media", "broadcast", "production", "entertainment"]
            if any(industry in lead.industry.lower() for industry in high_value_industries):
                score += 15
        
        # Source scoring
        if lead.source:
            source_scores = {
                "referral": 20,
                "website": 15,
                "event": 15,
                "cold_call": 5,
                "email": 8,
                "social": 10
            }
            score += source_scores.get(lead.source.lower(), 0)
        
        # Probability scoring
        if lead.probability:
            score += int(lead.probability * 20)  # 0-1 scale to 0-20 points
        
        return min(score, 100)  # Cap at 100