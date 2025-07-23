"""
Billing analytics API endpoints
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, case
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
import logging

from src.db.base import get_db
from src.db.models import (
    Subscription, Customer, Payment, Invoice, Plan,
    SubscriptionStatus, PaymentStatus, InvoiceStatus, Currency
)
from src.models.schemas import (
    MRRResponse, ChurnResponse, RevenueResponse,
    CustomerMetricsResponse, GrowthMetricsResponse
)
from src.core.auth import get_current_user, require_admin
from src.services.cache_service import CacheService

router = APIRouter()
logger = logging.getLogger(__name__)
cache_service = CacheService()


@router.get("/mrr", response_model=MRRResponse)
async def get_mrr_metrics(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user=Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get Monthly Recurring Revenue (MRR) metrics"""
    # Check cache
    cache_key = f"analytics:mrr:{start_date}:{end_date}"
    cached = await cache_service.get(cache_key)
    if cached:
        return cached
    
    # Default to last 12 months
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - relativedelta(months=12)
    
    # Get active subscriptions
    active_subs = await db.execute(
        select(
            Subscription,
            Plan
        )
        .join(Plan)
        .where(
            Subscription.status.in_([
                SubscriptionStatus.ACTIVE,
                SubscriptionStatus.TRIALING
            ])
        )
    )
    
    # Calculate current MRR
    current_mrr = 0
    for sub, plan in active_subs:
        monthly_amount = calculate_monthly_amount(
            plan.base_price,
            plan.billing_interval.value,
            sub.quantity
        )
        current_mrr += monthly_amount
    
    # Calculate MRR by month
    monthly_mrr = await calculate_monthly_mrr(
        db, start_date, end_date
    )
    
    # Calculate growth metrics
    if len(monthly_mrr) >= 2:
        last_month = monthly_mrr[-1]["mrr"]
        prev_month = monthly_mrr[-2]["mrr"]
        growth_rate = ((last_month - prev_month) / prev_month * 100) if prev_month > 0 else 0
    else:
        growth_rate = 0
    
    # Calculate MRR components
    components = await calculate_mrr_components(db, end_date)
    
    result = MRRResponse(
        current_mrr=current_mrr,
        growth_rate=growth_rate,
        monthly_data=monthly_mrr,
        new_mrr=components["new"],
        expansion_mrr=components["expansion"],
        contraction_mrr=components["contraction"],
        churned_mrr=components["churned"],
        net_new_mrr=components["net_new"]
    )
    
    # Cache for 1 hour
    await cache_service.set(cache_key, result, expire=3600)
    
    return result


@router.get("/churn", response_model=ChurnResponse)
async def get_churn_metrics(
    period_months: int = Query(3, ge=1, le=12),
    current_user=Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get customer and revenue churn metrics"""
    end_date = date.today()
    start_date = end_date - relativedelta(months=period_months)
    
    # Get subscriptions at start of period
    start_subs = await db.execute(
        select(func.count(Subscription.id))
        .where(
            and_(
                Subscription.start_date <= start_date,
                or_(
                    Subscription.ended_at == None,
                    Subscription.ended_at > start_date
                )
            )
        )
    )
    start_count = start_subs.scalar() or 0
    
    # Get churned subscriptions
    churned_subs = await db.execute(
        select(func.count(Subscription.id))
        .where(
            and_(
                Subscription.canceled_at >= start_date,
                Subscription.canceled_at <= end_date,
                Subscription.status == SubscriptionStatus.CANCELED
            )
        )
    )
    churned_count = churned_subs.scalar() or 0
    
    # Calculate churn rate
    customer_churn_rate = (churned_count / start_count * 100) if start_count > 0 else 0
    
    # Calculate revenue churn
    revenue_churn = await calculate_revenue_churn(
        db, start_date, end_date
    )
    
    # Get churn reasons
    churn_reasons = await get_churn_reasons(db, start_date, end_date)
    
    # Calculate average customer lifetime
    avg_lifetime = await calculate_average_customer_lifetime(db)
    
    return ChurnResponse(
        customer_churn_rate=customer_churn_rate,
        revenue_churn_rate=revenue_churn["rate"],
        gross_revenue_churn=revenue_churn["gross"],
        net_revenue_churn=revenue_churn["net"],
        churned_customers=churned_count,
        churn_reasons=churn_reasons,
        average_customer_lifetime_months=avg_lifetime,
        period_months=period_months
    )


@router.get("/revenue", response_model=RevenueResponse)
async def get_revenue_analytics(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    group_by: str = Query("month", enum=["day", "week", "month", "quarter"]),
    current_user=Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed revenue analytics"""
    # Default to last 12 months
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - relativedelta(months=12)
    
    # Get revenue data
    revenue_data = await calculate_revenue_by_period(
        db, start_date, end_date, group_by
    )
    
    # Calculate totals
    total_revenue = sum(item["revenue"] for item in revenue_data)
    total_recurring = sum(item["recurring"] for item in revenue_data)
    total_one_time = sum(item["one_time"] for item in revenue_data)
    
    # Get revenue by plan
    revenue_by_plan = await calculate_revenue_by_plan(
        db, start_date, end_date
    )
    
    # Get revenue by currency
    revenue_by_currency = await calculate_revenue_by_currency(
        db, start_date, end_date
    )
    
    # Calculate ARPU (Average Revenue Per User)
    arpu = await calculate_arpu(db, end_date)
    
    # Calculate LTV (Customer Lifetime Value)
    ltv = await calculate_ltv(db)
    
    return RevenueResponse(
        total_revenue=total_revenue,
        recurring_revenue=total_recurring,
        one_time_revenue=total_one_time,
        revenue_data=revenue_data,
        revenue_by_plan=revenue_by_plan,
        revenue_by_currency=revenue_by_currency,
        arpu=arpu,
        ltv=ltv,
        period={
            "start": start_date,
            "end": end_date,
            "group_by": group_by
        }
    )


@router.get("/customers", response_model=CustomerMetricsResponse)
async def get_customer_metrics(
    current_user=Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get customer-related metrics"""
    # Total customers
    total_customers = await db.scalar(
        select(func.count(Customer.id))
    )
    
    # Active customers (with active subscriptions)
    active_customers = await db.scalar(
        select(func.count(func.distinct(Subscription.customer_id)))
        .where(
            Subscription.status.in_([
                SubscriptionStatus.ACTIVE,
                SubscriptionStatus.TRIALING
            ])
        )
    )
    
    # New customers this month
    month_start = date.today().replace(day=1)
    new_customers = await db.scalar(
        select(func.count(Customer.id))
        .where(Customer.created_at >= month_start)
    )
    
    # Customer distribution by plan
    customer_by_plan = await calculate_customers_by_plan(db)
    
    # Customer value distribution
    value_distribution = await calculate_customer_value_distribution(db)
    
    # Geographic distribution
    geographic_distribution = await calculate_geographic_distribution(db)
    
    return CustomerMetricsResponse(
        total_customers=total_customers,
        active_customers=active_customers,
        new_customers_this_month=new_customers,
        trial_customers=await count_trial_customers(db),
        customer_by_plan=customer_by_plan,
        value_distribution=value_distribution,
        geographic_distribution=geographic_distribution,
        average_customers_per_month=await calculate_average_new_customers(db)
    )


@router.get("/growth", response_model=GrowthMetricsResponse)
async def get_growth_metrics(
    months: int = Query(12, ge=1, le=24),
    current_user=Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get growth and expansion metrics"""
    end_date = date.today()
    start_date = end_date - relativedelta(months=months)
    
    # Monthly growth data
    growth_data = await calculate_monthly_growth(
        db, start_date, end_date
    )
    
    # Calculate compound monthly growth rate
    if growth_data and len(growth_data) > 1:
        first_mrr = growth_data[0]["mrr"]
        last_mrr = growth_data[-1]["mrr"]
        months_diff = len(growth_data) - 1
        
        if first_mrr > 0 and months_diff > 0:
            cmgr = ((last_mrr / first_mrr) ** (1 / months_diff) - 1) * 100
        else:
            cmgr = 0
    else:
        cmgr = 0
    
    # Net revenue retention
    nrr = await calculate_net_revenue_retention(db, months)
    
    # Expansion revenue
    expansion_revenue = await calculate_expansion_revenue(
        db, start_date, end_date
    )
    
    # Quick ratio (growth efficiency)
    quick_ratio = await calculate_quick_ratio(db, end_date)
    
    return GrowthMetricsResponse(
        compound_monthly_growth_rate=cmgr,
        net_revenue_retention=nrr,
        expansion_revenue=expansion_revenue,
        quick_ratio=quick_ratio,
        monthly_growth_data=growth_data,
        cohort_retention=await calculate_cohort_retention(db, months)
    )


# Helper functions

def calculate_monthly_amount(base_price: float, interval: str, quantity: int) -> float:
    """Convert any billing interval to monthly amount"""
    multipliers = {
        "monthly": 1,
        "quarterly": 1/3,
        "semi_annual": 1/6,
        "annual": 1/12
    }
    return float(base_price) * multipliers.get(interval, 1) * quantity


async def calculate_monthly_mrr(
    db: AsyncSession,
    start_date: date,
    end_date: date
) -> List[Dict[str, Any]]:
    """Calculate MRR for each month in the period"""
    monthly_data = []
    current_date = start_date.replace(day=1)
    
    while current_date <= end_date:
        # Get active subscriptions for this month
        month_end = (current_date + relativedelta(months=1)) - timedelta(days=1)
        
        result = await db.execute(
            select(
                func.sum(
                    case(
                        (Plan.billing_interval == "monthly", Plan.base_price * Subscription.quantity),
                        (Plan.billing_interval == "quarterly", Plan.base_price * Subscription.quantity / 3),
                        (Plan.billing_interval == "semi_annual", Plan.base_price * Subscription.quantity / 6),
                        (Plan.billing_interval == "annual", Plan.base_price * Subscription.quantity / 12),
                        else_=0
                    )
                )
            )
            .select_from(Subscription)
            .join(Plan)
            .where(
                and_(
                    Subscription.start_date <= month_end,
                    or_(
                        Subscription.ended_at == None,
                        Subscription.ended_at > current_date
                    ),
                    Subscription.status.in_([
                        SubscriptionStatus.ACTIVE,
                        SubscriptionStatus.TRIALING
                    ])
                )
            )
        )
        
        mrr = result.scalar() or 0
        
        monthly_data.append({
            "month": current_date.isoformat(),
            "mrr": float(mrr)
        })
        
        current_date += relativedelta(months=1)
    
    return monthly_data


async def calculate_mrr_components(
    db: AsyncSession,
    as_of_date: date
) -> Dict[str, float]:
    """Calculate MRR movement components for the current month"""
    month_start = as_of_date.replace(day=1)
    prev_month_start = month_start - relativedelta(months=1)
    
    # New MRR (from new customers)
    new_mrr_result = await db.execute(
        select(
            func.sum(
                case(
                    (Plan.billing_interval == "monthly", Plan.base_price * Subscription.quantity),
                    (Plan.billing_interval == "quarterly", Plan.base_price * Subscription.quantity / 3),
                    (Plan.billing_interval == "semi_annual", Plan.base_price * Subscription.quantity / 6),
                    (Plan.billing_interval == "annual", Plan.base_price * Subscription.quantity / 12),
                    else_=0
                )
            )
        )
        .select_from(Subscription)
        .join(Plan)
        .join(Customer)
        .where(
            and_(
                Customer.created_at >= month_start,
                Subscription.status.in_([
                    SubscriptionStatus.ACTIVE,
                    SubscriptionStatus.TRIALING
                ])
            )
        )
    )
    new_mrr = new_mrr_result.scalar() or 0
    
    # Calculate other components (simplified)
    # In production, these would be more detailed calculations
    expansion_mrr = new_mrr * 0.2  # Placeholder
    contraction_mrr = new_mrr * 0.1  # Placeholder
    churned_mrr = new_mrr * 0.15  # Placeholder
    
    net_new_mrr = new_mrr + expansion_mrr - contraction_mrr - churned_mrr
    
    return {
        "new": float(new_mrr),
        "expansion": float(expansion_mrr),
        "contraction": float(contraction_mrr),
        "churned": float(churned_mrr),
        "net_new": float(net_new_mrr)
    }


async def calculate_revenue_churn(
    db: AsyncSession,
    start_date: date,
    end_date: date
) -> Dict[str, float]:
    """Calculate revenue churn metrics"""
    # This is a simplified calculation
    # In production, this would track actual revenue changes
    
    # Get MRR at start of period
    start_mrr = await get_mrr_at_date(db, start_date)
    
    # Get churned MRR
    churned_mrr = await get_churned_mrr(db, start_date, end_date)
    
    # Get expansion MRR
    expansion_mrr = await get_expansion_mrr(db, start_date, end_date)
    
    gross_churn_rate = (churned_mrr / start_mrr * 100) if start_mrr > 0 else 0
    net_churn_rate = ((churned_mrr - expansion_mrr) / start_mrr * 100) if start_mrr > 0 else 0
    
    return {
        "rate": net_churn_rate,
        "gross": gross_churn_rate,
        "net": net_churn_rate
    }


async def get_churn_reasons(
    db: AsyncSession,
    start_date: date,
    end_date: date
) -> Dict[str, int]:
    """Get breakdown of churn reasons"""
    result = await db.execute(
        select(
            Subscription.cancel_reason,
            func.count(Subscription.id)
        )
        .where(
            and_(
                Subscription.canceled_at >= start_date,
                Subscription.canceled_at <= end_date,
                Subscription.status == SubscriptionStatus.CANCELED
            )
        )
        .group_by(Subscription.cancel_reason)
    )
    
    reasons = {}
    for reason, count in result:
        reason_key = reason or "unspecified"
        reasons[reason_key] = count
    
    return reasons


async def calculate_average_customer_lifetime(db: AsyncSession) -> float:
    """Calculate average customer lifetime in months"""
    # Get completed subscriptions
    result = await db.execute(
        select(
            func.avg(
                func.extract(
                    "epoch",
                    Subscription.ended_at - Subscription.start_date
                ) / 86400 / 30  # Convert to months
            )
        )
        .where(
            and_(
                Subscription.status == SubscriptionStatus.CANCELED,
                Subscription.ended_at != None
            )
        )
    )
    
    avg_lifetime = result.scalar() or 0
    return float(avg_lifetime)


# Additional helper functions would continue here...
# Including calculate_revenue_by_period, calculate_arpu, calculate_ltv, etc.