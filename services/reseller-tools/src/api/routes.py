"""API routes for the Reseller Tools Service"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID

from ..core.database import get_db
from ..core.auth import get_current_user
from ..models.schemas import (
    ResellerCreate, ResellerUpdate, ResellerResponse,
    CustomerCreate, CustomerUpdate, CustomerResponse,
    LeadCreate, LeadUpdate, LeadResponse,
    PricingTierCreate, PricingTierUpdate, PricingTierResponse,
    CommissionCreate, CommissionUpdate, CommissionResponse,
    CustomerActivityCreate, LeadActivityCreate, ActivityResponse,
    NotificationResponse, DashboardSummary,
    PaginationParams, PaginatedResponse
)
from ..services.reseller_service import ResellerService
from ..services.customer_service import CustomerService
from ..services.lead_service import LeadService
from ..services.pricing_service import PricingService
from ..services.commission_service import CommissionService
from ..services.analytics_service import AnalyticsService
from ..services.notification_service import NotificationService
from ..db.models import (
    ResellerStatusEnum, ResellerTierEnum, CustomerStatusEnum,
    LeadStatusEnum, PaymentStatusEnum
)

router = APIRouter()

# Reseller endpoints
@router.post("/resellers", response_model=ResellerResponse, status_code=status.HTTP_201_CREATED)
async def create_reseller(
    reseller_data: ResellerCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Create a new reseller"""
    try:
        return await ResellerService.create_reseller(db, reseller_data, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/resellers", response_model=PaginatedResponse)
async def list_resellers(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    status: Optional[ResellerStatusEnum] = Query(None),
    tier: Optional[ResellerTierEnum] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """List resellers with filtering and pagination"""
    pagination = PaginationParams(
        page=page, limit=limit, sort_by=sort_by, sort_order=sort_order
    )
    return await ResellerService.list_resellers(db, pagination, status, tier, search)


@router.get("/resellers/{reseller_id}", response_model=ResellerResponse)
async def get_reseller(
    reseller_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get reseller by ID"""
    reseller = await ResellerService.get_reseller(db, reseller_id)
    if not reseller:
        raise HTTPException(status_code=404, detail="Reseller not found")
    return reseller


@router.get("/resellers/user/{user_id}", response_model=ResellerResponse)
async def get_reseller_by_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get reseller by user ID"""
    reseller = await ResellerService.get_reseller_by_user(db, user_id)
    if not reseller:
        raise HTTPException(status_code=404, detail="Reseller not found")
    return reseller


@router.put("/resellers/{reseller_id}", response_model=ResellerResponse)
async def update_reseller(
    reseller_id: UUID,
    reseller_data: ResellerUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Update reseller"""
    reseller = await ResellerService.update_reseller(db, reseller_id, reseller_data, current_user.id)
    if not reseller:
        raise HTTPException(status_code=404, detail="Reseller not found")
    return reseller


@router.delete("/resellers/{reseller_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reseller(
    reseller_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Delete reseller"""
    deleted = await ResellerService.delete_reseller(db, reseller_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Reseller not found")


@router.get("/resellers/{reseller_id}/dashboard", response_model=DashboardSummary)
async def get_reseller_dashboard(
    reseller_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get dashboard data for reseller"""
    return await ResellerService.get_reseller_dashboard(db, reseller_id)


@router.post("/resellers/{reseller_id}/approve", status_code=status.HTTP_204_NO_CONTENT)
async def approve_reseller(
    reseller_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Approve a reseller application"""
    success = await ResellerService.approve_reseller(db, reseller_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Reseller not found")


@router.post("/resellers/{reseller_id}/suspend", status_code=status.HTTP_204_NO_CONTENT)
async def suspend_reseller(
    reseller_id: UUID,
    reason: str = Query(..., description="Reason for suspension"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Suspend a reseller"""
    success = await ResellerService.suspend_reseller(db, reseller_id, current_user.id, reason)
    if not success:
        raise HTTPException(status_code=404, detail="Reseller not found")


# Customer endpoints
@router.post("/customers", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
async def create_customer(
    customer_data: CustomerCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Create a new customer"""
    try:
        return await CustomerService.create_customer(db, customer_data, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/customers", response_model=PaginatedResponse)
async def list_customers(
    reseller_id: UUID,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    status: Optional[CustomerStatusEnum] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """List customers for a reseller"""
    pagination = PaginationParams(
        page=page, limit=limit, sort_by=sort_by, sort_order=sort_order
    )
    return await CustomerService.list_customers(db, reseller_id, pagination, status, search)


@router.get("/customers/{customer_id}", response_model=CustomerResponse)
async def get_customer(
    customer_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get customer by ID"""
    customer = await CustomerService.get_customer(db, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@router.put("/customers/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    customer_id: UUID,
    customer_data: CustomerUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Update customer"""
    customer = await CustomerService.update_customer(db, customer_id, customer_data, current_user.id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@router.delete("/customers/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_customer(
    customer_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Delete customer"""
    deleted = await CustomerService.delete_customer(db, customer_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Customer not found")


@router.post("/customers/convert-lead/{lead_id}", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
async def convert_lead_to_customer(
    lead_id: UUID,
    customer_data: CustomerCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Convert a lead to a customer"""
    try:
        return await CustomerService.convert_lead_to_customer(db, lead_id, customer_data, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


# Customer activities
@router.post("/customers/{customer_id}/activities", response_model=ActivityResponse, status_code=status.HTTP_201_CREATED)
async def add_customer_activity(
    customer_id: UUID,
    activity_data: CustomerActivityCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Add activity record for a customer"""
    activity_data.customer_id = customer_id
    activity_data.user_id = current_user.id
    return await CustomerService.add_customer_activity(db, activity_data, current_user.id)


@router.get("/customers/{customer_id}/activities", response_model=PaginatedResponse)
async def get_customer_activities(
    customer_id: UUID,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get activities for a customer"""
    pagination = PaginationParams(page=page, limit=limit)
    return await CustomerService.get_customer_activities(db, customer_id, pagination)


@router.get("/customers/stats/{reseller_id}")
async def get_customer_stats(
    reseller_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get customer statistics for a reseller"""
    return await CustomerService.get_customer_stats(db, reseller_id)


# Lead endpoints
@router.post("/leads", response_model=LeadResponse, status_code=status.HTTP_201_CREATED)
async def create_lead(
    lead_data: LeadCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Create a new lead"""
    try:
        return await LeadService.create_lead(db, lead_data, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/leads", response_model=PaginatedResponse)
async def list_leads(
    reseller_id: UUID,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    status: Optional[LeadStatusEnum] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """List leads for a reseller"""
    pagination = PaginationParams(
        page=page, limit=limit, sort_by=sort_by, sort_order=sort_order
    )
    return await LeadService.list_leads(db, reseller_id, pagination, status, search)


@router.get("/leads/{lead_id}", response_model=LeadResponse)
async def get_lead(
    lead_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get lead by ID"""
    lead = await LeadService.get_lead(db, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


@router.put("/leads/{lead_id}", response_model=LeadResponse)
async def update_lead(
    lead_id: UUID,
    lead_data: LeadUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Update lead"""
    lead = await LeadService.update_lead(db, lead_id, lead_data, current_user.id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


@router.delete("/leads/{lead_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lead(
    lead_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Delete lead"""
    deleted = await LeadService.delete_lead(db, lead_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Lead not found")


# Lead activities
@router.post("/leads/{lead_id}/activities", response_model=ActivityResponse, status_code=status.HTTP_201_CREATED)
async def add_lead_activity(
    lead_id: UUID,
    activity_data: LeadActivityCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Add activity record for a lead"""
    activity_data.lead_id = lead_id
    activity_data.user_id = current_user.id
    return await LeadService.add_lead_activity(db, activity_data, current_user.id)


@router.get("/leads/{lead_id}/activities", response_model=PaginatedResponse)
async def get_lead_activities(
    lead_id: UUID,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get activities for a lead"""
    pagination = PaginationParams(page=page, limit=limit)
    return await LeadService.get_lead_activities(db, lead_id, pagination)


# Pricing endpoints
@router.post("/pricing-tiers", response_model=PricingTierResponse, status_code=status.HTTP_201_CREATED)
async def create_pricing_tier(
    pricing_data: PricingTierCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Create a new pricing tier"""
    try:
        return await PricingService.create_pricing_tier(db, pricing_data, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/pricing-tiers", response_model=List[PricingTierResponse])
async def list_pricing_tiers(
    reseller_id: UUID,
    active_only: bool = Query(True),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """List pricing tiers for a reseller"""
    return await PricingService.list_pricing_tiers(db, reseller_id, active_only)


@router.get("/pricing-tiers/{tier_id}", response_model=PricingTierResponse)
async def get_pricing_tier(
    tier_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get pricing tier by ID"""
    tier = await PricingService.get_pricing_tier(db, tier_id)
    if not tier:
        raise HTTPException(status_code=404, detail="Pricing tier not found")
    return tier


@router.put("/pricing-tiers/{tier_id}", response_model=PricingTierResponse)
async def update_pricing_tier(
    tier_id: UUID,
    pricing_data: PricingTierUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Update pricing tier"""
    tier = await PricingService.update_pricing_tier(db, tier_id, pricing_data, current_user.id)
    if not tier:
        raise HTTPException(status_code=404, detail="Pricing tier not found")
    return tier


@router.delete("/pricing-tiers/{tier_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pricing_tier(
    tier_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Delete pricing tier"""
    deleted = await PricingService.delete_pricing_tier(db, tier_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Pricing tier not found")


# Commission endpoints
@router.post("/commissions", response_model=CommissionResponse, status_code=status.HTTP_201_CREATED)
async def create_commission(
    commission_data: CommissionCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Create a new commission record"""
    try:
        return await CommissionService.create_commission(db, commission_data, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/commissions", response_model=PaginatedResponse)
async def list_commissions(
    reseller_id: UUID,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    payment_status: Optional[PaymentStatusEnum] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """List commissions for a reseller"""
    pagination = PaginationParams(
        page=page, limit=limit, sort_by=sort_by, sort_order=sort_order
    )
    return await CommissionService.list_commissions(db, reseller_id, pagination, payment_status)


@router.get("/commissions/{commission_id}", response_model=CommissionResponse)
async def get_commission(
    commission_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get commission by ID"""
    commission = await CommissionService.get_commission(db, commission_id)
    if not commission:
        raise HTTPException(status_code=404, detail="Commission not found")
    return commission


@router.put("/commissions/{commission_id}", response_model=CommissionResponse)
async def update_commission(
    commission_id: UUID,
    commission_data: CommissionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Update commission"""
    commission = await CommissionService.update_commission(db, commission_id, commission_data, current_user.id)
    if not commission:
        raise HTTPException(status_code=404, detail="Commission not found")
    return commission


@router.post("/commissions/{commission_id}/mark-paid", status_code=status.HTTP_204_NO_CONTENT)
async def mark_commission_paid(
    commission_id: UUID,
    payment_reference: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Mark commission as paid"""
    success = await CommissionService.mark_commission_paid(db, commission_id, payment_reference, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Commission not found")


# Analytics endpoints
@router.get("/analytics/reseller/{reseller_id}/metrics")
async def get_reseller_metrics(
    reseller_id: UUID,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get reseller performance metrics"""
    return await AnalyticsService.get_reseller_metrics(db, reseller_id, start_date, end_date)


@router.get("/analytics/reseller/{reseller_id}/pipeline")
async def get_pipeline_analysis(
    reseller_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get sales pipeline analysis"""
    return await AnalyticsService.get_pipeline_analysis(db, reseller_id)


# Notification endpoints
@router.get("/notifications/{reseller_id}", response_model=List[NotificationResponse])
async def get_notifications(
    reseller_id: UUID,
    unread_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get notifications for a reseller"""
    return await NotificationService.get_notifications(db, reseller_id, unread_only, limit)


@router.post("/notifications/{notification_id}/mark-read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_notification_read(
    notification_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Mark notification as read"""
    success = await NotificationService.mark_notification_read(db, notification_id)
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found")


@router.post("/notifications/{notification_id}/acknowledge", status_code=status.HTTP_204_NO_CONTENT)
async def acknowledge_notification(
    notification_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Acknowledge notification"""
    success = await NotificationService.acknowledge_notification(db, notification_id)
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found")