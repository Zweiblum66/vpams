"""Business logic for customer management"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.orm import selectinload
from typing import List, Optional, Dict, Any
from uuid import UUID
import logging
from datetime import datetime, timedelta

from ..db.models import (
    Customer, CustomerActivity, Lead, Commission,
    CustomerStatusEnum
)
from ..models.schemas import (
    CustomerCreate, CustomerUpdate, CustomerResponse,
    CustomerActivityCreate, ActivityResponse,
    PaginationParams
)
from ..core.exceptions import NotFoundError, ValidationError

logger = logging.getLogger(__name__)


class CustomerService:
    """Service for customer management operations"""
    
    @staticmethod
    async def create_customer(
        db: AsyncSession,
        customer_data: CustomerCreate,
        current_user_id: UUID
    ) -> CustomerResponse:
        """Create a new customer"""
        try:
            # Check if customer already exists for this reseller
            stmt = select(Customer).where(
                and_(
                    Customer.reseller_id == customer_data.reseller_id,
                    Customer.email == customer_data.email
                )
            )
            existing = await db.execute(stmt)
            if existing.scalar_one_or_none():
                raise ValidationError("Customer with this email already exists for this reseller")
            
            # Create customer
            customer = Customer(**customer_data.model_dump())
            
            db.add(customer)
            await db.commit()
            await db.refresh(customer)
            
            # Create initial activity record
            activity = CustomerActivity(
                customer_id=customer.id,
                user_id=current_user_id,
                activity_type="customer_created",
                subject="Customer Created",
                description=f"Customer {customer.company_name} was added to the system"
            )
            db.add(activity)
            await db.commit()
            
            logger.info(f"Created customer {customer.id} for reseller {customer_data.reseller_id}")
            return CustomerResponse.model_validate(customer)
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating customer: {e}")
            raise
    
    @staticmethod
    async def get_customer(db: AsyncSession, customer_id: UUID) -> Optional[CustomerResponse]:
        """Get customer by ID"""
        stmt = select(Customer).where(Customer.id == customer_id)
        result = await db.execute(stmt)
        customer = result.scalar_one_or_none()
        
        if not customer:
            return None
            
        return CustomerResponse.model_validate(customer)
    
    @staticmethod
    async def list_customers(
        db: AsyncSession,
        reseller_id: UUID,
        pagination: PaginationParams,
        status: Optional[CustomerStatusEnum] = None,
        search: Optional[str] = None
    ) -> Dict[str, Any]:
        """List customers for a reseller with filtering and pagination"""
        
        # Build query
        stmt = select(Customer).where(Customer.reseller_id == reseller_id)
        
        # Apply filters
        filters = []
        if status:
            filters.append(Customer.status == status)
        if search:
            search_filter = or_(
                Customer.company_name.ilike(f"%{search}%"),
                Customer.contact_name.ilike(f"%{search}%"),
                Customer.email.ilike(f"%{search}%")
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
            sort_column = Customer.company_name
        elif pagination.sort_by == "status":
            sort_column = Customer.status
        elif pagination.sort_by == "contract_value":
            sort_column = Customer.contract_value
        else:
            sort_column = Customer.created_at
        
        if pagination.sort_order == "desc":
            stmt = stmt.order_by(sort_column.desc())
        else:
            stmt = stmt.order_by(sort_column.asc())
        
        # Apply pagination
        offset = (pagination.page - 1) * pagination.limit
        stmt = stmt.offset(offset).limit(pagination.limit)
        
        # Execute query
        result = await db.execute(stmt)
        customers = result.scalars().all()
        
        # Calculate pagination info
        pages = (total + pagination.limit - 1) // pagination.limit
        has_next = pagination.page < pages
        has_prev = pagination.page > 1
        
        return {
            "items": [CustomerResponse.model_validate(c) for c in customers],
            "total": total,
            "page": pagination.page,
            "pages": pages,
            "has_next": has_next,
            "has_prev": has_prev
        }
    
    @staticmethod
    async def update_customer(
        db: AsyncSession,
        customer_id: UUID,
        customer_data: CustomerUpdate,
        current_user_id: UUID
    ) -> Optional[CustomerResponse]:
        """Update customer"""
        try:
            # Get existing customer
            stmt = select(Customer).where(Customer.id == customer_id)
            result = await db.execute(stmt)
            customer = result.scalar_one_or_none()
            
            if not customer:
                return None
            
            # Track status changes for activity log
            old_status = customer.status
            
            # Update fields
            update_data = customer_data.model_dump(exclude_unset=True)
            if update_data:
                for field, value in update_data.items():
                    setattr(customer, field, value)
                
                customer.updated_at = datetime.utcnow()
                await db.commit()
                await db.refresh(customer)
                
                # Log status change if it occurred
                if old_status != customer.status:
                    activity = CustomerActivity(
                        customer_id=customer.id,
                        user_id=current_user_id,
                        activity_type="status_change",
                        subject="Status Changed",
                        description=f"Customer status changed from {old_status} to {customer.status}"
                    )
                    db.add(activity)
                    await db.commit()
            
            logger.info(f"Updated customer {customer_id}")
            return CustomerResponse.model_validate(customer)
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Error updating customer {customer_id}: {e}")
            raise
    
    @staticmethod
    async def delete_customer(db: AsyncSession, customer_id: UUID, current_user_id: UUID) -> bool:
        """Delete customer"""
        try:
            stmt = delete(Customer).where(Customer.id == customer_id)
            result = await db.execute(stmt)
            await db.commit()
            
            deleted = result.rowcount > 0
            if deleted:
                logger.info(f"Deleted customer {customer_id}")
            
            return deleted
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Error deleting customer {customer_id}: {e}")
            raise
    
    @staticmethod
    async def convert_lead_to_customer(
        db: AsyncSession,
        lead_id: UUID,
        customer_data: CustomerCreate,
        current_user_id: UUID
    ) -> CustomerResponse:
        """Convert a lead to a customer"""
        try:
            # Get the lead
            lead_stmt = select(Lead).where(Lead.id == lead_id)
            lead_result = await db.execute(lead_stmt)
            lead = lead_result.scalar_one_or_none()
            
            if not lead:
                raise NotFoundError("Lead not found")
            
            # Create customer from lead data
            customer_dict = customer_data.model_dump()
            
            # Use lead data if not provided in customer_data
            if not customer_dict.get("company_name"):
                customer_dict["company_name"] = lead.company_name
            if not customer_dict.get("contact_name"):
                customer_dict["contact_name"] = lead.contact_name
            if not customer_dict.get("email"):
                customer_dict["email"] = lead.email
            if not customer_dict.get("phone"):
                customer_dict["phone"] = lead.phone
            if not customer_dict.get("industry"):
                customer_dict["industry"] = lead.industry
            if not customer_dict.get("company_size"):
                customer_dict["company_size"] = lead.company_size
            if not customer_dict.get("annual_revenue"):
                customer_dict["annual_revenue"] = lead.annual_revenue
            if not customer_dict.get("lead_source"):
                customer_dict["lead_source"] = lead.source
            if not customer_dict.get("contract_value") and lead.estimated_value:
                customer_dict["contract_value"] = lead.estimated_value
            
            customer = Customer(**customer_dict)
            db.add(customer)
            
            # Update lead status to closed_won
            lead.status = "closed_won"
            lead.updated_at = datetime.utcnow()
            
            await db.commit()
            await db.refresh(customer)
            
            # Create activity records
            customer_activity = CustomerActivity(
                customer_id=customer.id,
                user_id=current_user_id,
                activity_type="lead_conversion",
                subject="Converted from Lead",
                description=f"Customer created from lead {lead.company_name}"
            )
            db.add(customer_activity)
            await db.commit()
            
            logger.info(f"Converted lead {lead_id} to customer {customer.id}")
            return CustomerResponse.model_validate(customer)
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Error converting lead {lead_id} to customer: {e}")
            raise
    
    @staticmethod
    async def add_customer_activity(
        db: AsyncSession,
        activity_data: CustomerActivityCreate,
        current_user_id: UUID
    ) -> ActivityResponse:
        """Add activity record for a customer"""
        try:
            # Verify customer exists
            customer_stmt = select(Customer).where(Customer.id == activity_data.customer_id)
            customer_result = await db.execute(customer_stmt)
            customer = customer_result.scalar_one_or_none()
            
            if not customer:
                raise NotFoundError("Customer not found")
            
            # Create activity
            activity = CustomerActivity(**activity_data.model_dump())
            db.add(activity)
            await db.commit()
            await db.refresh(activity)
            
            logger.info(f"Added activity {activity.id} for customer {activity_data.customer_id}")
            return ActivityResponse.model_validate(activity)
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Error adding customer activity: {e}")
            raise
    
    @staticmethod
    async def get_customer_activities(
        db: AsyncSession,
        customer_id: UUID,
        pagination: PaginationParams
    ) -> Dict[str, Any]:
        """Get activities for a customer"""
        
        # Build query
        stmt = select(CustomerActivity).where(CustomerActivity.customer_id == customer_id)
        
        # Get total count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await db.execute(count_stmt)
        total = total_result.scalar()
        
        # Apply sorting (always by created_at desc for activities)
        stmt = stmt.order_by(CustomerActivity.created_at.desc())
        
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
    async def get_customer_stats(db: AsyncSession, reseller_id: UUID) -> Dict[str, Any]:
        """Get customer statistics for a reseller"""
        try:
            # Total customers by status
            status_stats = {}
            for status in CustomerStatusEnum:
                stmt = select(func.count(Customer.id)).where(
                    and_(
                        Customer.reseller_id == reseller_id,
                        Customer.status == status
                    )
                )
                result = await db.execute(stmt)
                status_stats[status.value] = result.scalar() or 0
            
            # Revenue metrics
            total_revenue_stmt = select(func.sum(Customer.contract_value)).where(
                and_(
                    Customer.reseller_id == reseller_id,
                    Customer.contract_value > 0
                )
            )
            total_revenue_result = await db.execute(total_revenue_stmt)
            total_revenue = total_revenue_result.scalar() or 0.0
            
            monthly_revenue_stmt = select(func.sum(Customer.monthly_value)).where(
                and_(
                    Customer.reseller_id == reseller_id,
                    Customer.status == CustomerStatusEnum.ACTIVE
                )
            )
            monthly_revenue_result = await db.execute(monthly_revenue_stmt)
            monthly_revenue = monthly_revenue_result.scalar() or 0.0
            
            # Upcoming renewals (next 30 days)
            renewal_date_threshold = datetime.utcnow() + timedelta(days=30)
            upcoming_renewals_stmt = select(func.count(Customer.id)).where(
                and_(
                    Customer.reseller_id == reseller_id,
                    Customer.renewal_date <= renewal_date_threshold,
                    Customer.renewal_date >= datetime.utcnow(),
                    Customer.status == CustomerStatusEnum.ACTIVE
                )
            )
            upcoming_renewals_result = await db.execute(upcoming_renewals_stmt)
            upcoming_renewals = upcoming_renewals_result.scalar() or 0
            
            # Average contract value
            avg_contract_stmt = select(func.avg(Customer.contract_value)).where(
                and_(
                    Customer.reseller_id == reseller_id,
                    Customer.contract_value > 0
                )
            )
            avg_contract_result = await db.execute(avg_contract_stmt)
            avg_contract_value = avg_contract_result.scalar() or 0.0
            
            return {
                "status_breakdown": status_stats,
                "total_revenue": total_revenue,
                "monthly_recurring_revenue": monthly_revenue,
                "upcoming_renewals": upcoming_renewals,
                "average_contract_value": round(avg_contract_value, 2),
                "total_customers": sum(status_stats.values())
            }
            
        except Exception as e:
            logger.error(f"Error getting customer stats for reseller {reseller_id}: {e}")
            raise