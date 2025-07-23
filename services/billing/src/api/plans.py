"""
Plan and pricing API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from typing import List, Optional
import logging

from src.db.base import get_db
from src.db.models import Plan, PlanAddon, BillingInterval, Currency
from src.models.schemas import (
    PlanResponse, PlanCreate, PlanUpdate,
    PlanAddonResponse, PlanAddonCreate
)
from src.core.auth import get_current_user, require_admin
from src.services.stripe_service import StripeService
from src.services.cache_service import CacheService

router = APIRouter()
logger = logging.getLogger(__name__)
stripe_service = StripeService()
cache_service = CacheService()


@router.get("/", response_model=List[PlanResponse])
async def list_plans(
    include_inactive: bool = False,
    billing_interval: Optional[BillingInterval] = None,
    currency: Optional[Currency] = None,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List available plans"""
    # Check cache
    cache_key = f"plans:list:{include_inactive}:{billing_interval}:{currency}"
    cached = await cache_service.get(cache_key)
    if cached:
        return cached
    
    # Build query
    query = select(Plan)
    
    if not include_inactive:
        query = query.where(Plan.is_active == True)
    
    if billing_interval:
        query = query.where(Plan.billing_interval == billing_interval)
    
    if currency:
        query = query.where(Plan.currency == currency)
    
    # Order by price
    query = query.order_by(Plan.base_price)
    
    result = await db.execute(query)
    plans = result.scalars().all()
    
    # Load addons for each plan
    for plan in plans:
        addons = await db.execute(
            select(PlanAddon)
            .where(
                and_(
                    PlanAddon.plan_id == plan.id,
                    PlanAddon.is_active == True
                )
            )
        )
        plan.addons = addons.scalars().all()
    
    # Cache results
    await cache_service.set(cache_key, plans, expire=3600)  # 1 hour
    
    return plans


@router.get("/{plan_id}", response_model=PlanResponse)
async def get_plan(
    plan_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get plan details"""
    plan = await db.get(Plan, plan_id)
    
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found"
        )
    
    # Load addons
    addons = await db.execute(
        select(PlanAddon)
        .where(
            and_(
                PlanAddon.plan_id == plan.id,
                PlanAddon.is_active == True
            )
        )
    )
    plan.addons = addons.scalars().all()
    
    return plan


@router.post("/", response_model=PlanResponse, status_code=status.HTTP_201_CREATED)
async def create_plan(
    plan_data: PlanCreate,
    current_user=Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Create a new plan (admin only)"""
    # Check if plan name exists
    existing = await db.execute(
        select(Plan).where(Plan.name == plan_data.name)
    )
    if existing.scalar():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Plan name already exists"
        )
    
    # Create in Stripe
    stripe_product = await stripe_service.create_product(
        name=plan_data.display_name,
        description=plan_data.description,
        metadata={
            "plan_name": plan_data.name,
            "features": str(plan_data.features)
        }
    )
    
    stripe_price = await stripe_service.create_price(
        product_id=stripe_product.id,
        unit_amount=int(plan_data.base_price * 100),  # Convert to cents
        currency=plan_data.currency.value.lower(),
        recurring_interval=plan_data.billing_interval.value
    )
    
    # Create plan
    plan = Plan(
        name=plan_data.name,
        display_name=plan_data.display_name,
        description=plan_data.description,
        base_price=plan_data.base_price,
        currency=plan_data.currency,
        billing_interval=plan_data.billing_interval,
        trial_days=plan_data.trial_days or 0,
        features=plan_data.features,
        metadata=plan_data.metadata or {},
        user_limit=plan_data.user_limit,
        storage_limit_gb=plan_data.storage_limit_gb,
        api_calls_limit=plan_data.api_calls_limit,
        stripe_product_id=stripe_product.id,
        stripe_price_id=stripe_price.id,
        is_visible=plan_data.is_visible
    )
    
    db.add(plan)
    await db.commit()
    await db.refresh(plan)
    
    # Clear cache
    await cache_service.delete_pattern("plans:*")
    
    logger.info(f"Plan created: {plan.id}")
    
    return plan


@router.put("/{plan_id}", response_model=PlanResponse)
async def update_plan(
    plan_id: str,
    update_data: PlanUpdate,
    current_user=Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Update plan details (admin only)"""
    plan = await db.get(Plan, plan_id)
    
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found"
        )
    
    # Update fields
    if update_data.display_name:
        plan.display_name = update_data.display_name
    
    if update_data.description:
        plan.description = update_data.description
    
    if update_data.features:
        plan.features.update(update_data.features)
    
    if update_data.metadata:
        plan.metadata.update(update_data.metadata)
    
    if update_data.user_limit is not None:
        plan.user_limit = update_data.user_limit
    
    if update_data.storage_limit_gb is not None:
        plan.storage_limit_gb = update_data.storage_limit_gb
    
    if update_data.api_calls_limit is not None:
        plan.api_calls_limit = update_data.api_calls_limit
    
    if update_data.is_visible is not None:
        plan.is_visible = update_data.is_visible
    
    # Update Stripe product
    if plan.stripe_product_id:
        await stripe_service.update_product(
            product_id=plan.stripe_product_id,
            name=plan.display_name,
            description=plan.description
        )
    
    await db.commit()
    await db.refresh(plan)
    
    # Clear cache
    await cache_service.delete_pattern("plans:*")
    
    logger.info(f"Plan updated: {plan.id}")
    
    return plan


@router.patch("/{plan_id}/deactivate", response_model=PlanResponse)
async def deactivate_plan(
    plan_id: str,
    current_user=Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Deactivate a plan (admin only)"""
    plan = await db.get(Plan, plan_id)
    
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found"
        )
    
    plan.is_active = False
    plan.is_visible = False
    
    # Archive in Stripe
    if plan.stripe_product_id:
        await stripe_service.archive_product(plan.stripe_product_id)
    
    await db.commit()
    await db.refresh(plan)
    
    # Clear cache
    await cache_service.delete_pattern("plans:*")
    
    logger.info(f"Plan deactivated: {plan.id}")
    
    return plan


@router.get("/{plan_id}/addons", response_model=List[PlanAddonResponse])
async def list_plan_addons(
    plan_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List available addons for a plan"""
    plan = await db.get(Plan, plan_id)
    
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found"
        )
    
    addons = await db.execute(
        select(PlanAddon)
        .where(
            and_(
                PlanAddon.plan_id == plan.id,
                PlanAddon.is_active == True
            )
        )
        .order_by(PlanAddon.price)
    )
    
    return addons.scalars().all()


@router.post("/{plan_id}/addons", response_model=PlanAddonResponse, status_code=status.HTTP_201_CREATED)
async def create_plan_addon(
    plan_id: str,
    addon_data: PlanAddonCreate,
    current_user=Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Create a new addon for a plan (admin only)"""
    plan = await db.get(Plan, plan_id)
    
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found"
        )
    
    # Create addon
    addon = PlanAddon(
        plan_id=plan.id,
        name=addon_data.name,
        display_name=addon_data.display_name,
        description=addon_data.description,
        price=addon_data.price,
        extra_users=addon_data.extra_users or 0,
        extra_storage_gb=addon_data.extra_storage_gb or 0,
        extra_api_calls=addon_data.extra_api_calls or 0,
        features=addon_data.features or {}
    )
    
    db.add(addon)
    await db.commit()
    await db.refresh(addon)
    
    # Clear cache
    await cache_service.delete_pattern("plans:*")
    
    logger.info(f"Plan addon created: {addon.id} for plan {plan.id}")
    
    return addon


@router.get("/compare", response_model=dict)
async def compare_plans(
    plan_ids: List[str] = Query(..., min_items=2, max_items=5),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Compare multiple plans"""
    plans = []
    
    for plan_id in plan_ids:
        plan = await db.get(Plan, plan_id)
        if plan and plan.is_active:
            plans.append(plan)
    
    if len(plans) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least 2 active plans required for comparison"
        )
    
    # Build comparison matrix
    all_features = set()
    for plan in plans:
        all_features.update(plan.features.keys())
    
    comparison = {
        "plans": [],
        "features": {},
        "limits": {}
    }
    
    for plan in plans:
        comparison["plans"].append({
            "id": str(plan.id),
            "name": plan.display_name,
            "price": float(plan.base_price),
            "interval": plan.billing_interval.value,
            "currency": plan.currency.value
        })
    
    # Compare features
    for feature in sorted(all_features):
        comparison["features"][feature] = [
            plan.features.get(feature, False) for plan in plans
        ]
    
    # Compare limits
    comparison["limits"]["users"] = [plan.user_limit for plan in plans]
    comparison["limits"]["storage_gb"] = [plan.storage_limit_gb for plan in plans]
    comparison["limits"]["api_calls"] = [plan.api_calls_limit for plan in plans]
    
    return comparison


@router.get("/recommended", response_model=PlanResponse)
async def get_recommended_plan(
    users: int = Query(..., ge=1),
    storage_gb: int = Query(..., ge=0),
    api_calls: int = Query(..., ge=0),
    currency: Currency = Currency.USD,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get recommended plan based on requirements"""
    # Find plans that meet requirements
    plans = await db.execute(
        select(Plan)
        .where(
            and_(
                Plan.is_active == True,
                Plan.is_visible == True,
                Plan.currency == currency,
                or_(
                    Plan.user_limit >= users,
                    Plan.user_limit == None
                ),
                or_(
                    Plan.storage_limit_gb >= storage_gb,
                    Plan.storage_limit_gb == None
                ),
                or_(
                    Plan.api_calls_limit >= api_calls,
                    Plan.api_calls_limit == None
                )
            )
        )
        .order_by(Plan.base_price)
    )
    
    plan = plans.scalar()
    
    if not plan:
        # Find the highest tier plan
        highest = await db.execute(
            select(Plan)
            .where(
                and_(
                    Plan.is_active == True,
                    Plan.is_visible == True,
                    Plan.currency == currency
                )
            )
            .order_by(Plan.base_price.desc())
            .limit(1)
        )
        plan = highest.scalar()
    
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No suitable plan found"
        )
    
    # Load addons
    addons = await db.execute(
        select(PlanAddon)
        .where(
            and_(
                PlanAddon.plan_id == plan.id,
                PlanAddon.is_active == True
            )
        )
    )
    plan.addons = addons.scalars().all()
    
    return plan