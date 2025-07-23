"""
Subscription management API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from typing import List, Optional
from datetime import datetime, timedelta
import logging

from src.db.base import get_db
from src.db.models import (
    Subscription, Customer, Plan, SubscriptionStatus,
    SubscriptionItem, PlanAddon, Invoice
)
from src.models.schemas import (
    SubscriptionCreate, SubscriptionResponse, SubscriptionUpdate,
    SubscriptionChangePlan, SubscriptionCancel,
    SubscriptionUsage
)
from src.core.auth import get_current_user, require_api_key
from src.services.stripe_service import StripeService
from src.services.invoice_service import InvoiceService
from src.services.webhook_service import WebhookService
from src.services.usage_service import UsageService

router = APIRouter()
logger = logging.getLogger(__name__)
stripe_service = StripeService()
invoice_service = InvoiceService()
webhook_service = WebhookService()
usage_service = UsageService()


@router.post("/", response_model=SubscriptionResponse, status_code=status.HTTP_201_CREATED)
async def create_subscription(
    subscription_data: SubscriptionCreate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new subscription"""
    # Check if customer exists
    customer = await db.execute(
        select(Customer).where(Customer.organization_id == current_user.organization_id)
    )
    customer = customer.scalar()
    
    if not customer:
        # Create customer
        customer = Customer(
            organization_id=current_user.organization_id,
            email=current_user.email,
            name=current_user.name
        )
        db.add(customer)
        await db.commit()
        await db.refresh(customer)
    
    # Get plan
    plan = await db.get(Plan, subscription_data.plan_id)
    if not plan or not plan.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found or inactive"
        )
    
    # Check for existing active subscription
    existing = await db.execute(
        select(Subscription).where(
            and_(
                Subscription.customer_id == customer.id,
                Subscription.status.in_([
                    SubscriptionStatus.ACTIVE,
                    SubscriptionStatus.TRIALING
                ])
            )
        )
    )
    if existing.scalar():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Customer already has an active subscription"
        )
    
    # Create subscription in payment processor
    if customer.stripe_customer_id:
        stripe_subscription = await stripe_service.create_subscription(
            customer_id=customer.stripe_customer_id,
            price_id=plan.stripe_price_id,
            payment_method_id=subscription_data.payment_method_id,
            trial_days=plan.trial_days if subscription_data.enable_trial else 0
        )
        stripe_subscription_id = stripe_subscription.id
    else:
        # Create Stripe customer first
        stripe_customer = await stripe_service.create_customer(
            email=customer.email,
            name=customer.name,
            payment_method_id=subscription_data.payment_method_id
        )
        customer.stripe_customer_id = stripe_customer.id
        
        stripe_subscription = await stripe_service.create_subscription(
            customer_id=stripe_customer.id,
            price_id=plan.stripe_price_id,
            payment_method_id=subscription_data.payment_method_id,
            trial_days=plan.trial_days if subscription_data.enable_trial else 0
        )
        stripe_subscription_id = stripe_subscription.id
    
    # Calculate dates
    now = datetime.utcnow()
    trial_end = None
    if subscription_data.enable_trial and plan.trial_days > 0:
        trial_end = now + timedelta(days=plan.trial_days)
        status = SubscriptionStatus.TRIALING
    else:
        status = SubscriptionStatus.ACTIVE
    
    # Create subscription in database
    subscription = Subscription(
        customer_id=customer.id,
        plan_id=plan.id,
        status=status,
        start_date=now,
        current_period_start=now,
        current_period_end=now + timedelta(days=30),  # Will be updated by webhook
        trial_start=now if trial_end else None,
        trial_end=trial_end,
        quantity=subscription_data.quantity or 1,
        stripe_subscription_id=stripe_subscription_id,
        metadata=subscription_data.metadata or {}
    )
    
    db.add(subscription)
    
    # Add any add-ons
    if subscription_data.addon_ids:
        for addon_id in subscription_data.addon_ids:
            addon = await db.get(PlanAddon, addon_id)
            if addon and addon.plan_id == plan.id:
                item = SubscriptionItem(
                    subscription_id=subscription.id,
                    type="addon",
                    description=addon.display_name,
                    quantity=1,
                    unit_price=addon.price,
                    addon_id=addon.id
                )
                db.add(item)
    
    await db.commit()
    await db.refresh(subscription)
    
    # Send webhook
    await webhook_service.send_event(
        "subscription.created",
        {
            "subscription_id": str(subscription.id),
            "customer_id": str(customer.id),
            "plan_id": str(plan.id),
            "status": subscription.status.value
        }
    )
    
    logger.info(f"Subscription created: {subscription.id}")
    
    return subscription


@router.get("/{subscription_id}", response_model=SubscriptionResponse)
async def get_subscription(
    subscription_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get subscription details"""
    subscription = await db.execute(
        select(Subscription)
        .join(Customer)
        .where(
            and_(
                Subscription.id == subscription_id,
                Customer.organization_id == current_user.organization_id
            )
        )
    )
    subscription = subscription.scalar()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )
    
    return subscription


@router.get("/", response_model=List[SubscriptionResponse])
async def list_subscriptions(
    status: Optional[SubscriptionStatus] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List subscriptions for organization"""
    # Get customer
    customer = await db.execute(
        select(Customer).where(Customer.organization_id == current_user.organization_id)
    )
    customer = customer.scalar()
    
    if not customer:
        return []
    
    # Build query
    query = select(Subscription).where(Subscription.customer_id == customer.id)
    
    if status:
        query = query.where(Subscription.status == status)
    
    # Pagination
    offset = (page - 1) * limit
    query = query.offset(offset).limit(limit).order_by(Subscription.created_at.desc())
    
    result = await db.execute(query)
    subscriptions = result.scalars().all()
    
    return subscriptions


@router.put("/{subscription_id}", response_model=SubscriptionResponse)
async def update_subscription(
    subscription_id: str,
    update_data: SubscriptionUpdate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update subscription (quantity, metadata)"""
    subscription = await db.execute(
        select(Subscription)
        .join(Customer)
        .where(
            and_(
                Subscription.id == subscription_id,
                Customer.organization_id == current_user.organization_id
            )
        )
    )
    subscription = subscription.scalar()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )
    
    # Update in payment processor
    if subscription.stripe_subscription_id and update_data.quantity:
        await stripe_service.update_subscription_quantity(
            subscription_id=subscription.stripe_subscription_id,
            quantity=update_data.quantity
        )
    
    # Update in database
    if update_data.quantity:
        subscription.quantity = update_data.quantity
    
    if update_data.metadata:
        subscription.metadata.update(update_data.metadata)
    
    subscription.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(subscription)
    
    # Send webhook
    await webhook_service.send_event(
        "subscription.updated",
        {
            "subscription_id": str(subscription.id),
            "changes": update_data.dict(exclude_unset=True)
        }
    )
    
    return subscription


@router.post("/{subscription_id}/change-plan", response_model=SubscriptionResponse)
async def change_subscription_plan(
    subscription_id: str,
    change_data: SubscriptionChangePlan,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Change subscription plan"""
    subscription = await db.execute(
        select(Subscription)
        .join(Customer)
        .where(
            and_(
                Subscription.id == subscription_id,
                Customer.organization_id == current_user.organization_id
            )
        )
    )
    subscription = subscription.scalar()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )
    
    if subscription.status not in [SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only change plan for active subscriptions"
        )
    
    # Get new plan
    new_plan = await db.get(Plan, change_data.new_plan_id)
    if not new_plan or not new_plan.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="New plan not found or inactive"
        )
    
    # Update in payment processor
    if subscription.stripe_subscription_id:
        await stripe_service.update_subscription_plan(
            subscription_id=subscription.stripe_subscription_id,
            new_price_id=new_plan.stripe_price_id,
            prorate=change_data.prorate
        )
    
    # Update in database
    old_plan_id = subscription.plan_id
    subscription.plan_id = new_plan.id
    subscription.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(subscription)
    
    # Create prorated invoice if needed
    if change_data.prorate:
        await invoice_service.create_prorated_invoice(
            subscription_id=subscription.id,
            old_plan_id=old_plan_id,
            new_plan_id=new_plan.id
        )
    
    # Send webhook
    await webhook_service.send_event(
        "subscription.plan_changed",
        {
            "subscription_id": str(subscription.id),
            "old_plan_id": str(old_plan_id),
            "new_plan_id": str(new_plan.id),
            "prorated": change_data.prorate
        }
    )
    
    logger.info(f"Subscription {subscription.id} plan changed from {old_plan_id} to {new_plan.id}")
    
    return subscription


@router.post("/{subscription_id}/cancel", response_model=SubscriptionResponse)
async def cancel_subscription(
    subscription_id: str,
    cancel_data: SubscriptionCancel,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Cancel subscription"""
    subscription = await db.execute(
        select(Subscription)
        .join(Customer)
        .where(
            and_(
                Subscription.id == subscription_id,
                Customer.organization_id == current_user.organization_id
            )
        )
    )
    subscription = subscription.scalar()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )
    
    if subscription.status == SubscriptionStatus.CANCELED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Subscription already canceled"
        )
    
    # Cancel in payment processor
    if subscription.stripe_subscription_id:
        await stripe_service.cancel_subscription(
            subscription_id=subscription.stripe_subscription_id,
            at_period_end=cancel_data.at_period_end
        )
    
    # Update in database
    subscription.canceled_at = datetime.utcnow()
    subscription.cancel_reason = cancel_data.reason
    
    if cancel_data.at_period_end:
        # Will be canceled at end of current period
        subscription.metadata["cancel_at_period_end"] = True
    else:
        # Cancel immediately
        subscription.status = SubscriptionStatus.CANCELED
        subscription.ended_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(subscription)
    
    # Send webhook
    await webhook_service.send_event(
        "subscription.canceled",
        {
            "subscription_id": str(subscription.id),
            "cancel_at_period_end": cancel_data.at_period_end,
            "reason": cancel_data.reason
        }
    )
    
    logger.info(f"Subscription {subscription.id} canceled")
    
    return subscription


@router.post("/{subscription_id}/reactivate", response_model=SubscriptionResponse)
async def reactivate_subscription(
    subscription_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Reactivate canceled subscription"""
    subscription = await db.execute(
        select(Subscription)
        .join(Customer)
        .where(
            and_(
                Subscription.id == subscription_id,
                Customer.organization_id == current_user.organization_id
            )
        )
    )
    subscription = subscription.scalar()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )
    
    if subscription.status != SubscriptionStatus.CANCELED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only reactivate canceled subscriptions"
        )
    
    # Check if within grace period (30 days)
    if subscription.ended_at and (datetime.utcnow() - subscription.ended_at).days > 30:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot reactivate subscription after 30 days"
        )
    
    # Reactivate in payment processor
    if subscription.stripe_subscription_id:
        # Create new subscription with same parameters
        plan = await db.get(Plan, subscription.plan_id)
        customer = await db.get(Customer, subscription.customer_id)
        
        stripe_subscription = await stripe_service.create_subscription(
            customer_id=customer.stripe_customer_id,
            price_id=plan.stripe_price_id,
            quantity=subscription.quantity
        )
        subscription.stripe_subscription_id = stripe_subscription.id
    
    # Update in database
    subscription.status = SubscriptionStatus.ACTIVE
    subscription.canceled_at = None
    subscription.ended_at = None
    subscription.cancel_reason = None
    subscription.metadata.pop("cancel_at_period_end", None)
    
    # Reset billing period
    now = datetime.utcnow()
    subscription.current_period_start = now
    subscription.current_period_end = now + timedelta(days=30)
    
    await db.commit()
    await db.refresh(subscription)
    
    # Send webhook
    await webhook_service.send_event(
        "subscription.reactivated",
        {
            "subscription_id": str(subscription.id)
        }
    )
    
    logger.info(f"Subscription {subscription.id} reactivated")
    
    return subscription


@router.get("/{subscription_id}/usage", response_model=SubscriptionUsage)
async def get_subscription_usage(
    subscription_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current usage for subscription"""
    subscription = await db.execute(
        select(Subscription)
        .join(Customer)
        .where(
            and_(
                Subscription.id == subscription_id,
                Customer.organization_id == current_user.organization_id
            )
        )
    )
    subscription = subscription.scalar()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )
    
    # Get usage data
    usage = await usage_service.get_subscription_usage(
        subscription_id=subscription.id,
        period_start=subscription.current_period_start,
        period_end=subscription.current_period_end
    )
    
    # Get plan limits
    plan = await db.get(Plan, subscription.plan_id)
    
    return SubscriptionUsage(
        subscription_id=subscription.id,
        period_start=subscription.current_period_start,
        period_end=subscription.current_period_end,
        usage=usage,
        limits={
            "users": plan.user_limit,
            "storage_gb": plan.storage_limit_gb,
            "api_calls": plan.api_calls_limit
        },
        overage_charges=await usage_service.calculate_overage_charges(
            subscription_id=subscription.id,
            usage=usage,
            plan=plan
        )
    )


@router.post("/{subscription_id}/pause")
async def pause_subscription(
    subscription_id: str,
    resume_date: Optional[datetime] = None,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Pause subscription (enterprise feature)"""
    subscription = await db.execute(
        select(Subscription)
        .join(Customer)
        .join(Plan)
        .where(
            and_(
                Subscription.id == subscription_id,
                Customer.organization_id == current_user.organization_id
            )
        )
    )
    subscription = subscription.scalar()
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )
    
    # Check if plan allows pausing
    if not subscription.plan.features.get("allow_pause", False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Subscription plan does not allow pausing"
        )
    
    # Pause in payment processor
    if subscription.stripe_subscription_id:
        await stripe_service.pause_subscription(
            subscription_id=subscription.stripe_subscription_id,
            resume_date=resume_date
        )
    
    # Update status
    subscription.status = SubscriptionStatus.PAUSED
    subscription.metadata["paused_at"] = datetime.utcnow().isoformat()
    if resume_date:
        subscription.metadata["resume_date"] = resume_date.isoformat()
    
    await db.commit()
    
    # Send webhook
    await webhook_service.send_event(
        "subscription.paused",
        {
            "subscription_id": str(subscription.id),
            "resume_date": resume_date.isoformat() if resume_date else None
        }
    )
    
    return {"message": "Subscription paused successfully"}