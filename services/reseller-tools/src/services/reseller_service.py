"""Business logic for reseller management"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.orm import selectinload
from typing import List, Optional, Dict, Any
from uuid import UUID
import logging
from datetime import datetime, timedelta

from ..db.models import (
    Reseller, Customer, Lead, PricingTier, Commission, 
    ResellerMetrics, ResellerNotification,
    ResellerStatusEnum, ResellerTierEnum
)
from ..models.schemas import (
    ResellerCreate, ResellerUpdate, ResellerResponse,
    PaginationParams
)
from ..core.exceptions import NotFoundError, ValidationError

logger = logging.getLogger(__name__)


class ResellerService:
    """Service for reseller management operations"""
    
    @staticmethod
    async def create_reseller(
        db: AsyncSession,
        reseller_data: ResellerCreate,
        current_user_id: UUID
    ) -> ResellerResponse:
        """Create a new reseller"""
        try:
            # Check if reseller already exists for this user
            stmt = select(Reseller).where(Reseller.user_id == reseller_data.user_id)
            existing = await db.execute(stmt)
            if existing.scalar_one_or_none():
                raise ValidationError("Reseller already exists for this user")
            
            # Create reseller
            reseller = Reseller(
                **reseller_data.model_dump(),
                status=ResellerStatusEnum.PENDING
            )
            
            db.add(reseller)
            await db.commit()
            await db.refresh(reseller)
            
            # Create default pricing tiers
            await ResellerService._create_default_pricing_tiers(db, reseller.id)
            
            # Send welcome notification
            await ResellerService._create_welcome_notification(db, reseller.id)
            
            logger.info(f"Created reseller {reseller.id} for user {reseller_data.user_id}")
            return ResellerResponse.model_validate(reseller)
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating reseller: {e}")
            raise
    
    @staticmethod
    async def get_reseller(db: AsyncSession, reseller_id: UUID) -> Optional[ResellerResponse]:
        """Get reseller by ID"""
        stmt = select(Reseller).where(Reseller.id == reseller_id)
        result = await db.execute(stmt)
        reseller = result.scalar_one_or_none()
        
        if not reseller:
            return None
            
        return ResellerResponse.model_validate(reseller)
    
    @staticmethod
    async def get_reseller_by_user(db: AsyncSession, user_id: UUID) -> Optional[ResellerResponse]:
        """Get reseller by user ID"""
        stmt = select(Reseller).where(Reseller.user_id == user_id)
        result = await db.execute(stmt)
        reseller = result.scalar_one_or_none()
        
        if not reseller:
            return None
            
        return ResellerResponse.model_validate(reseller)
    
    @staticmethod
    async def list_resellers(
        db: AsyncSession,
        pagination: PaginationParams,
        status: Optional[ResellerStatusEnum] = None,
        tier: Optional[ResellerTierEnum] = None,
        search: Optional[str] = None
    ) -> Dict[str, Any]:
        """List resellers with filtering and pagination"""
        
        # Build query
        stmt = select(Reseller)
        
        # Apply filters
        filters = []
        if status:
            filters.append(Reseller.status == status)
        if tier:
            filters.append(Reseller.tier == tier)
        if search:
            search_filter = or_(
                Reseller.company_name.ilike(f"%{search}%"),
                Reseller.contact_name.ilike(f"%{search}%"),
                Reseller.email.ilike(f"%{search}%")
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
            sort_column = Reseller.company_name
        elif pagination.sort_by == "status":
            sort_column = Reseller.status
        elif pagination.sort_by == "tier":
            sort_column = Reseller.tier
        else:
            sort_column = Reseller.created_at
        
        if pagination.sort_order == "desc":
            stmt = stmt.order_by(sort_column.desc())
        else:
            stmt = stmt.order_by(sort_column.asc())
        
        # Apply pagination
        offset = (pagination.page - 1) * pagination.limit
        stmt = stmt.offset(offset).limit(pagination.limit)
        
        # Execute query
        result = await db.execute(stmt)
        resellers = result.scalars().all()
        
        # Calculate pagination info
        pages = (total + pagination.limit - 1) // pagination.limit
        has_next = pagination.page < pages
        has_prev = pagination.page > 1
        
        return {
            "items": [ResellerResponse.model_validate(r) for r in resellers],
            "total": total,
            "page": pagination.page,
            "pages": pages,
            "has_next": has_next,
            "has_prev": has_prev
        }
    
    @staticmethod
    async def update_reseller(
        db: AsyncSession,
        reseller_id: UUID,
        reseller_data: ResellerUpdate,
        current_user_id: UUID
    ) -> Optional[ResellerResponse]:
        """Update reseller"""
        try:
            # Get existing reseller
            stmt = select(Reseller).where(Reseller.id == reseller_id)
            result = await db.execute(stmt)
            reseller = result.scalar_one_or_none()
            
            if not reseller:
                return None
            
            # Update fields
            update_data = reseller_data.model_dump(exclude_unset=True)
            if update_data:
                for field, value in update_data.items():
                    setattr(reseller, field, value)
                
                reseller.updated_at = datetime.utcnow()
                await db.commit()
                await db.refresh(reseller)
            
            logger.info(f"Updated reseller {reseller_id}")
            return ResellerResponse.model_validate(reseller)
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Error updating reseller {reseller_id}: {e}")
            raise
    
    @staticmethod
    async def delete_reseller(db: AsyncSession, reseller_id: UUID, current_user_id: UUID) -> bool:
        """Delete reseller"""
        try:
            stmt = delete(Reseller).where(Reseller.id == reseller_id)
            result = await db.execute(stmt)
            await db.commit()
            
            deleted = result.rowcount > 0
            if deleted:
                logger.info(f"Deleted reseller {reseller_id}")
            
            return deleted
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Error deleting reseller {reseller_id}: {e}")
            raise
    
    @staticmethod
    async def get_reseller_dashboard(db: AsyncSession, reseller_id: UUID) -> Dict[str, Any]:
        """Get dashboard data for reseller"""
        try:
            # Get basic counts
            lead_count_stmt = select(func.count(Lead.id)).where(Lead.reseller_id == reseller_id)
            customer_count_stmt = select(func.count(Customer.id)).where(Customer.reseller_id == reseller_id)
            
            lead_count = await db.execute(lead_count_stmt)
            customer_count = await db.execute(customer_count_stmt)
            
            total_leads = lead_count.scalar() or 0
            total_customers = customer_count.scalar() or 0
            
            # Get revenue metrics
            revenue_stmt = select(func.sum(Commission.commission_amount)).where(
                and_(
                    Commission.reseller_id == reseller_id,
                    Commission.payment_status == "paid"
                )
            )
            revenue_result = await db.execute(revenue_stmt)
            total_revenue = revenue_result.scalar() or 0.0
            
            # Get pending commissions
            pending_stmt = select(func.sum(Commission.commission_amount)).where(
                and_(
                    Commission.reseller_id == reseller_id,
                    Commission.payment_status == "pending"
                )
            )
            pending_result = await db.execute(pending_stmt)
            pending_commissions = pending_result.scalar() or 0.0
            
            # Get pipeline value
            pipeline_stmt = select(func.sum(Lead.estimated_value)).where(
                and_(
                    Lead.reseller_id == reseller_id,
                    Lead.status.in_(["qualified", "proposal", "negotiation"])
                )
            )
            pipeline_result = await db.execute(pipeline_stmt)
            pipeline_value = pipeline_result.scalar() or 0.0
            
            # Calculate conversion rate
            qualified_leads_stmt = select(func.count(Lead.id)).where(
                and_(
                    Lead.reseller_id == reseller_id,
                    Lead.status == "qualified"
                )
            )
            qualified_result = await db.execute(qualified_leads_stmt)
            qualified_leads = qualified_result.scalar() or 0
            
            conversion_rate = (total_customers / total_leads * 100) if total_leads > 0 else 0.0
            
            # Calculate average deal size
            avg_deal_stmt = select(func.avg(Customer.contract_value)).where(
                and_(
                    Customer.reseller_id == reseller_id,
                    Customer.contract_value > 0
                )
            )
            avg_deal_result = await db.execute(avg_deal_stmt)
            average_deal_size = avg_deal_result.scalar() or 0.0
            
            return {
                "total_leads": total_leads,
                "qualified_leads": qualified_leads,
                "active_customers": total_customers,
                "total_revenue": total_revenue,
                "pending_commissions": pending_commissions,
                "conversion_rate": round(conversion_rate, 2),
                "average_deal_size": round(average_deal_size, 2),
                "pipeline_value": pipeline_value
            }
            
        except Exception as e:
            logger.error(f"Error getting dashboard data for reseller {reseller_id}: {e}")
            raise
    
    @staticmethod
    async def approve_reseller(db: AsyncSession, reseller_id: UUID, admin_user_id: UUID) -> bool:
        """Approve a reseller application"""
        try:
            stmt = update(Reseller).where(
                Reseller.id == reseller_id
            ).values(
                status=ResellerStatusEnum.ACTIVE,
                onboarding_completed=True,
                contract_signed_date=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            result = await db.execute(stmt)
            await db.commit()
            
            if result.rowcount > 0:
                # Send approval notification
                await ResellerService._create_approval_notification(db, reseller_id)
                logger.info(f"Approved reseller {reseller_id}")
                return True
                
            return False
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Error approving reseller {reseller_id}: {e}")
            raise
    
    @staticmethod
    async def suspend_reseller(db: AsyncSession, reseller_id: UUID, admin_user_id: UUID, reason: str) -> bool:
        """Suspend a reseller"""
        try:
            stmt = update(Reseller).where(
                Reseller.id == reseller_id
            ).values(
                status=ResellerStatusEnum.SUSPENDED,
                notes=f"Suspended: {reason}",
                updated_at=datetime.utcnow()
            )
            
            result = await db.execute(stmt)
            await db.commit()
            
            if result.rowcount > 0:
                # Send suspension notification
                await ResellerService._create_suspension_notification(db, reseller_id, reason)
                logger.info(f"Suspended reseller {reseller_id}")
                return True
                
            return False
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Error suspending reseller {reseller_id}: {e}")
            raise
    
    @staticmethod
    async def _create_default_pricing_tiers(db: AsyncSession, reseller_id: UUID):
        """Create default pricing tiers for new reseller"""
        default_tiers = [
            {
                "name": "Starter",
                "description": "Perfect for small teams getting started",
                "tier_level": 1,
                "base_price": 99.0,
                "reseller_price": 75.0,
                "suggested_retail_price": 129.0,
                "minimum_retail_price": 99.0,
                "features": ["10 users", "100GB storage", "Basic support"],
                "user_limit": 10,
                "storage_limit_gb": 100,
                "billing_cycle": "monthly"
            },
            {
                "name": "Professional",
                "description": "For growing teams with advanced needs",
                "tier_level": 2,
                "base_price": 299.0,
                "reseller_price": 225.0,
                "suggested_retail_price": 399.0,
                "minimum_retail_price": 299.0,
                "features": ["50 users", "500GB storage", "Priority support", "Advanced workflows"],
                "user_limit": 50,
                "storage_limit_gb": 500,
                "billing_cycle": "monthly"
            },
            {
                "name": "Enterprise",
                "description": "For large organizations with custom requirements",
                "tier_level": 3,
                "base_price": 799.0,
                "reseller_price": 599.0,
                "suggested_retail_price": 999.0,
                "minimum_retail_price": 799.0,
                "features": ["Unlimited users", "2TB storage", "24/7 support", "Custom integrations"],
                "user_limit": None,
                "storage_limit_gb": 2048,
                "billing_cycle": "monthly"
            }
        ]
        
        for tier_data in default_tiers:
            tier = PricingTier(
                reseller_id=reseller_id,
                **tier_data
            )
            db.add(tier)
        
        await db.commit()
    
    @staticmethod
    async def _create_welcome_notification(db: AsyncSession, reseller_id: UUID):
        """Create welcome notification for new reseller"""
        notification = ResellerNotification(
            reseller_id=reseller_id,
            notification_type="onboarding",
            title="Welcome to the MAMS Partner Program!",
            message="Your reseller application has been received and is under review. You'll receive an email once your account is approved.",
            priority="normal"
        )
        db.add(notification)
        await db.commit()
    
    @staticmethod
    async def _create_approval_notification(db: AsyncSession, reseller_id: UUID):
        """Create approval notification"""
        notification = ResellerNotification(
            reseller_id=reseller_id,
            notification_type="approval",
            title="Congratulations! Your reseller account has been approved",
            message="You can now start selling MAMS solutions to your customers. Check out your dashboard to get started.",
            priority="high",
            action_required=True,
            action_url="/dashboard"
        )
        db.add(notification)
        await db.commit()
    
    @staticmethod
    async def _create_suspension_notification(db: AsyncSession, reseller_id: UUID, reason: str):
        """Create suspension notification"""
        notification = ResellerNotification(
            reseller_id=reseller_id,
            notification_type="suspension",
            title="Your reseller account has been suspended",
            message=f"Your account has been suspended for the following reason: {reason}. Please contact support for assistance.",
            priority="urgent",
            action_required=True,
            action_url="/support"
        )
        db.add(notification)
        await db.commit()