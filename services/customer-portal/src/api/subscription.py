"""
Subscription management API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from typing import List, Optional
from datetime import datetime, timedelta
import logging

from src.db.base import get_db
from src.db.models import (
    Subscription, SubscriptionAddon, UsageMetric,
    SubscriptionTier, Organization
)
from src.models.schemas import (
    SubscriptionResponse,
    SubscriptionPlan,
    SubscriptionUpgrade,
    UsageResponse,
    AddonResponse
)
from src.core.auth import get_current_user, require_role
from src.services.billing_service import BillingService
from src.services.email import EmailService

router = APIRouter()
logger = logging.getLogger(__name__)
billing_service = BillingService()
email_service = EmailService()


# Available subscription plans
SUBSCRIPTION_PLANS = {
    "starter": SubscriptionPlan(
        tier=SubscriptionTier.STARTER,
        name="Starter Plan",
        description="Perfect for small teams",
        monthly_price=999,
        annual_price=9990,
        user_limit=10,
        storage_limit_gb=10000,  # 10TB
        api_calls_limit=100000,
        features=[
            "Core features",
            "Email support",
            "10TB storage",
            "Basic AI features"
        ]
    ),
    "professional": SubscriptionPlan(
        tier=SubscriptionTier.PROFESSIONAL,
        name="Professional Plan",
        description="For growing organizations",
        monthly_price=4999,
        annual_price=49990,
        user_limit=50,
        storage_limit_gb=100000,  # 100TB
        api_calls_limit=1000000,
        features=[
            "All features",
            "Priority support",
            "100TB storage",
            "Advanced AI features",
            "API access",
            "Custom workflows"
        ]
    ),
    "enterprise": SubscriptionPlan(
        tier=SubscriptionTier.ENTERPRISE,
        name="Enterprise Plan",
        description="For large organizations",
        monthly_price=0,  # Custom pricing
        annual_price=0,
        user_limit=None,  # Unlimited
        storage_limit_gb=None,  # Unlimited
        api_calls_limit=None,  # Unlimited
        features=[
            "All features",
            "Dedicated support",
            "Unlimited storage",
            "Custom AI models",
            "SLA guarantee",
            "Custom integrations",
            "On-premise option"
        ]
    )
}


@router.get("/", response_model=SubscriptionResponse)
async def get_subscription(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current subscription details"""
    subscription = await db.execute(
        select(Subscription).where(
            Subscription.organization_id == current_user.organization_id
        )
    )
    subscription = subscription.scalar()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscription found"
        )
    
    # Calculate days remaining
    if subscription.end_date:
        days_remaining = (subscription.end_date - datetime.utcnow()).days
    else:
        days_remaining = None
    
    # Get addon details
    addons = await db.execute(
        select(SubscriptionAddon).where(
            SubscriptionAddon.subscription_id == subscription.id,
            SubscriptionAddon.is_active == True
        )
    )
    addons = addons.scalars().all()
    
    return SubscriptionResponse(
        id=subscription.id,
        tier=subscription.tier,
        plan_name=subscription.plan_name,
        user_limit=subscription.user_limit,
        storage_limit_gb=subscription.storage_limit_gb,
        api_calls_limit=subscription.api_calls_limit,
        monthly_price=float(subscription.monthly_price),
        annual_price=float(subscription.annual_price) if subscription.annual_price else None,
        start_date=subscription.start_date,
        end_date=subscription.end_date,
        trial_end_date=subscription.trial_end_date,
        is_active=subscription.is_active,
        is_trial=subscription.is_trial,
        auto_renew=subscription.auto_renew,
        current_users=subscription.current_users,
        current_storage_gb=subscription.current_storage_gb,
        current_api_calls=subscription.current_api_calls,
        days_remaining=days_remaining,
        features=subscription.features or [],
        addons=[AddonResponse.from_orm(addon) for addon in addons]
    )


@router.get("/plans", response_model=List[SubscriptionPlan])
async def list_subscription_plans():
    """List available subscription plans"""
    return list(SUBSCRIPTION_PLANS.values())


@router.post("/upgrade", response_model=dict)
async def upgrade_subscription(
    upgrade: SubscriptionUpgrade,
    current_user=Depends(require_role(["admin", "billing"])),
    db: AsyncSession = Depends(get_db)
):
    """Upgrade subscription plan"""
    # Get current subscription
    subscription = await db.execute(
        select(Subscription).where(
            Subscription.organization_id == current_user.organization_id
        )
    )
    subscription = subscription.scalar()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscription found"
        )
    
    # Validate upgrade
    if upgrade.tier == subscription.tier:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already on this plan"
        )
    
    # Check if downgrade
    tier_order = {
        SubscriptionTier.STARTER: 1,
        SubscriptionTier.PROFESSIONAL: 2,
        SubscriptionTier.ENTERPRISE: 3
    }
    
    if tier_order.get(upgrade.tier, 0) < tier_order.get(subscription.tier, 0):
        # Validate downgrade is possible
        if subscription.current_users > SUBSCRIPTION_PLANS[upgrade.tier].user_limit:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Current users ({subscription.current_users}) exceed new plan limit"
            )
        
        if subscription.current_storage_gb > SUBSCRIPTION_PLANS[upgrade.tier].storage_limit_gb:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Current storage ({subscription.current_storage_gb}GB) exceeds new plan limit"
            )
    
    # Process upgrade in billing service
    billing_result = await billing_service.process_subscription_change(
        subscription_id=str(subscription.id),
        new_tier=upgrade.tier,
        billing_period=upgrade.billing_period
    )
    
    # Update subscription
    new_plan = SUBSCRIPTION_PLANS[upgrade.tier]
    subscription.tier = upgrade.tier
    subscription.plan_name = new_plan.name
    subscription.user_limit = new_plan.user_limit
    subscription.storage_limit_gb = new_plan.storage_limit_gb
    subscription.api_calls_limit = new_plan.api_calls_limit
    subscription.features = new_plan.features
    
    if upgrade.billing_period == "annual":
        subscription.monthly_price = 0
        subscription.annual_price = new_plan.annual_price
    else:
        subscription.monthly_price = new_plan.monthly_price
        subscription.annual_price = 0
    
    subscription.updated_at = datetime.utcnow()
    
    await db.commit()
    
    # Send confirmation email
    org = await db.get(Organization, current_user.organization_id)
    await email_service.send_subscription_change_confirmation(
        to_email=org.billing_email or org.email,
        organization_name=org.name,
        old_plan=subscription.plan_name,
        new_plan=new_plan.name,
        effective_date=datetime.utcnow()
    )
    
    logger.info(f"Subscription upgraded for organization {current_user.organization_id} to {upgrade.tier}")
    
    return {
        "message": "Subscription upgraded successfully",
        "new_tier": upgrade.tier,
        "billing_reference": billing_result.get("reference")
    }


@router.get("/usage", response_model=UsageResponse)
async def get_usage_statistics(
    period: str = Query("current", regex="^(current|last_30_days|last_90_days)$"),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get usage statistics for the organization"""
    # Get subscription for limits
    subscription = await db.execute(
        select(Subscription).where(
            Subscription.organization_id == current_user.organization_id
        )
    )
    subscription = subscription.scalar()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscription found"
        )
    
    # Determine date range
    end_date = datetime.utcnow()
    if period == "current":
        # Current billing period
        start_date = subscription.start_date
    elif period == "last_30_days":
        start_date = end_date - timedelta(days=30)
    else:  # last_90_days
        start_date = end_date - timedelta(days=90)
    
    # Get usage metrics
    metrics = await db.execute(
        select(
            func.sum(UsageMetric.storage_gb).label("total_storage"),
            func.sum(UsageMetric.bandwidth_gb).label("total_bandwidth"),
            func.sum(UsageMetric.api_calls).label("total_api_calls"),
            func.sum(UsageMetric.assets_uploaded).label("total_uploads"),
            func.sum(UsageMetric.assets_downloaded).label("total_downloads"),
            func.avg(UsageMetric.active_users).label("avg_active_users"),
            func.max(UsageMetric.assets_total).label("total_assets")
        ).where(
            and_(
                UsageMetric.organization_id == current_user.organization_id,
                UsageMetric.metric_date >= start_date,
                UsageMetric.metric_date <= end_date
            )
        )
    )
    metrics = metrics.first()
    
    # Calculate percentages
    storage_percentage = (
        (metrics.total_storage / subscription.storage_limit_gb * 100)
        if subscription.storage_limit_gb and metrics.total_storage
        else 0
    )
    
    users_percentage = (
        (subscription.current_users / subscription.user_limit * 100)
        if subscription.user_limit
        else 0
    )
    
    api_percentage = (
        (metrics.total_api_calls / subscription.api_calls_limit * 100)
        if subscription.api_calls_limit and metrics.total_api_calls
        else 0
    )
    
    return UsageResponse(
        period=period,
        start_date=start_date,
        end_date=end_date,
        storage={
            "used_gb": metrics.total_storage or 0,
            "limit_gb": subscription.storage_limit_gb,
            "percentage": storage_percentage
        },
        users={
            "active": subscription.current_users,
            "limit": subscription.user_limit,
            "percentage": users_percentage
        },
        api_calls={
            "used": metrics.total_api_calls or 0,
            "limit": subscription.api_calls_limit,
            "percentage": api_percentage
        },
        bandwidth_gb=metrics.total_bandwidth or 0,
        assets={
            "total": metrics.total_assets or 0,
            "uploaded": metrics.total_uploads or 0,
            "downloaded": metrics.total_downloads or 0
        }
    )


@router.get("/addons", response_model=List[AddonResponse])
async def list_subscription_addons(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List active subscription add-ons"""
    # Get subscription
    subscription = await db.execute(
        select(Subscription).where(
            Subscription.organization_id == current_user.organization_id
        )
    )
    subscription = subscription.scalar()
    
    if not subscription:
        return []
    
    # Get addons
    addons = await db.execute(
        select(SubscriptionAddon).where(
            SubscriptionAddon.subscription_id == subscription.id,
            SubscriptionAddon.is_active == True
        )
    )
    addons = addons.scalars().all()
    
    return [AddonResponse.from_orm(addon) for addon in addons]


@router.post("/cancel", response_model=dict)
async def cancel_subscription(
    reason: Optional[str] = None,
    current_user=Depends(require_role(["admin"])),
    db: AsyncSession = Depends(get_db)
):
    """Cancel subscription"""
    # Get subscription
    subscription = await db.execute(
        select(Subscription).where(
            Subscription.organization_id == current_user.organization_id
        )
    )
    subscription = subscription.scalar()
    
    if not subscription or not subscription.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscription found"
        )
    
    # Process cancellation
    billing_result = await billing_service.cancel_subscription(
        subscription_id=str(subscription.id),
        reason=reason
    )
    
    # Update subscription
    subscription.auto_renew = False
    subscription.updated_at = datetime.utcnow()
    
    # Set end date if not set
    if not subscription.end_date:
        # Calculate based on billing period
        if subscription.annual_price and subscription.annual_price > 0:
            # Annual billing - set to end of current year
            subscription.end_date = subscription.start_date.replace(
                year=subscription.start_date.year + 1
            )
        else:
            # Monthly billing - set to end of current month
            next_month = subscription.start_date.month + 1
            next_year = subscription.start_date.year
            if next_month > 12:
                next_month = 1
                next_year += 1
            subscription.end_date = subscription.start_date.replace(
                month=next_month,
                year=next_year
            )
    
    await db.commit()
    
    # Send cancellation email
    org = await db.get(Organization, current_user.organization_id)
    await email_service.send_subscription_cancellation(
        to_email=org.billing_email or org.email,
        organization_name=org.name,
        end_date=subscription.end_date
    )
    
    logger.info(f"Subscription cancelled for organization {current_user.organization_id}")
    
    return {
        "message": "Subscription cancelled successfully",
        "end_date": subscription.end_date.isoformat(),
        "refund_amount": billing_result.get("refund_amount", 0)
    }