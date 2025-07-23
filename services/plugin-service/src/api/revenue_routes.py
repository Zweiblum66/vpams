"""
Revenue Sharing Routes for Plugin Service
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_, or_

from ..core.logging import get_logger
from ..core.exceptions import (
    PluginError,
    PluginNotFoundError,
    PluginPermissionError
)
from ..db.base import get_db
from ..models.schemas import (
    RevenueShareResponse,
    PayoutResponse,
    SalesReportResponse,
    PayoutRequestResponse
)
from .dependencies import get_current_user

logger = get_logger(__name__)

router = APIRouter(prefix="/revenue", tags=["revenue"])


@router.get("/dashboard", response_model=Dict[str, Any])
async def get_revenue_dashboard(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get revenue dashboard data for a developer"""
    from ..db.models import DeveloperAccount, PluginSale, Payout, Plugin
    
    # Get developer account
    developer_result = await db.execute(
        select(DeveloperAccount).where(
            DeveloperAccount.user_id == current_user.get("id")
        )
    )
    developer = developer_result.scalar_one_or_none()
    
    if not developer:
        raise HTTPException(status_code=404, detail="Developer account not found")
    
    # Get total revenue and statistics
    total_revenue_result = await db.execute(
        select(func.sum(PluginSale.revenue_share_amount))
        .join(Plugin, PluginSale.plugin_id == Plugin.id)
        .where(Plugin.developer_id == developer.id)
    )
    total_revenue = total_revenue_result.scalar() or Decimal('0.00')
    
    # Get current month revenue
    current_month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    current_month_revenue_result = await db.execute(
        select(func.sum(PluginSale.revenue_share_amount))
        .join(Plugin, PluginSale.plugin_id == Plugin.id)
        .where(
            and_(
                Plugin.developer_id == developer.id,
                PluginSale.created_at >= current_month_start
            )
        )
    )
    current_month_revenue = current_month_revenue_result.scalar() or Decimal('0.00')
    
    # Get pending payouts
    pending_payout_result = await db.execute(
        select(func.sum(Payout.amount))
        .where(
            and_(
                Payout.developer_id == developer.id,
                Payout.status == "pending"
            )
        )
    )
    pending_payout = pending_payout_result.scalar() or Decimal('0.00')
    
    # Get total sales count
    total_sales_result = await db.execute(
        select(func.count(PluginSale.id))
        .join(Plugin, PluginSale.plugin_id == Plugin.id)
        .where(Plugin.developer_id == developer.id)
    )
    total_sales = total_sales_result.scalar() or 0
    
    # Get recent sales (last 30 days by day)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    daily_sales_result = await db.execute(
        select(
            func.date(PluginSale.created_at).label("date"),
            func.sum(PluginSale.revenue_share_amount).label("revenue"),
            func.count(PluginSale.id).label("sales_count")
        )
        .join(Plugin, PluginSale.plugin_id == Plugin.id)
        .where(
            and_(
                Plugin.developer_id == developer.id,
                PluginSale.created_at >= thirty_days_ago
            )
        )
        .group_by(func.date(PluginSale.created_at))
        .order_by(func.date(PluginSale.created_at))
    )
    
    daily_sales = [
        {
            "date": row.date.isoformat(),
            "revenue": float(row.revenue) if row.revenue else 0,
            "sales_count": row.sales_count
        }
        for row in daily_sales_result
    ]
    
    # Get top performing plugins
    top_plugins_result = await db.execute(
        select(
            Plugin.id,
            Plugin.name,
            func.sum(PluginSale.revenue_share_amount).label("total_revenue"),
            func.count(PluginSale.id).label("sales_count")
        )
        .join(PluginSale, Plugin.id == PluginSale.plugin_id)
        .where(Plugin.developer_id == developer.id)
        .group_by(Plugin.id, Plugin.name)
        .order_by(desc(func.sum(PluginSale.revenue_share_amount)))
        .limit(5)
    )
    
    top_plugins = [
        {
            "plugin_id": row.id,
            "name": row.name,
            "total_revenue": float(row.total_revenue),
            "sales_count": row.sales_count
        }
        for row in top_plugins_result
    ]
    
    return {
        "developer_info": {
            "id": developer.id,
            "revenue_share_percent": float(developer.revenue_share_percent),
            "total_revenue": float(total_revenue),
            "pending_payout": float(pending_payout)
        },
        "overview": {
            "total_revenue": float(total_revenue),
            "current_month_revenue": float(current_month_revenue),
            "pending_payout": float(pending_payout),
            "total_sales": total_sales,
            "revenue_share_rate": float(developer.revenue_share_percent)
        },
        "daily_sales": daily_sales,
        "top_plugins": top_plugins,
        "payment_info": {
            "next_payout_date": get_next_payout_date().isoformat(),
            "minimum_payout": 50.0,  # Minimum payout threshold
            "payment_methods": ["PayPal", "Bank Transfer", "Stripe"]
        }
    }


@router.get("/sales", response_model=List[Dict[str, Any]])
async def get_sales_history(
    plugin_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get sales history for developer's plugins"""
    from ..db.models import DeveloperAccount, PluginSale, Plugin
    
    # Get developer account
    developer_result = await db.execute(
        select(DeveloperAccount).where(
            DeveloperAccount.user_id == current_user.get("id")
        )
    )
    developer = developer_result.scalar_one_or_none()
    
    if not developer:
        raise HTTPException(status_code=404, detail="Developer account not found")
    
    # Build query
    query = select(PluginSale, Plugin).join(Plugin, PluginSale.plugin_id == Plugin.id).where(
        Plugin.developer_id == developer.id
    )
    
    if plugin_id:
        query = query.where(Plugin.id == plugin_id)
    
    if start_date:
        query = query.where(PluginSale.created_at >= start_date)
    
    if end_date:
        query = query.where(PluginSale.created_at <= end_date)
    
    # Add pagination
    offset = (page - 1) * limit
    query = query.order_by(desc(PluginSale.created_at)).offset(offset).limit(limit)
    
    result = await db.execute(query)
    sales = result.all()
    
    return [
        {
            "sale_id": sale.PluginSale.id,
            "plugin_id": sale.Plugin.id,
            "plugin_name": sale.Plugin.name,
            "sale_price": float(sale.PluginSale.sale_price),
            "revenue_share_amount": float(sale.PluginSale.revenue_share_amount),
            "revenue_share_percent": float(sale.PluginSale.revenue_share_percent),
            "customer_id": sale.PluginSale.customer_id,
            "sale_date": sale.PluginSale.created_at,
            "payment_method": sale.PluginSale.payment_method,
            "transaction_id": sale.PluginSale.transaction_id,
            "status": sale.PluginSale.status
        }
        for sale in sales
    ]


@router.get("/payouts", response_model=List[PayoutResponse])
async def get_payout_history(
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get payout history for developer"""
    from ..db.models import DeveloperAccount, Payout
    
    # Get developer account
    developer_result = await db.execute(
        select(DeveloperAccount).where(
            DeveloperAccount.user_id == current_user.get("id")
        )
    )
    developer = developer_result.scalar_one_or_none()
    
    if not developer:
        raise HTTPException(status_code=404, detail="Developer account not found")
    
    # Build query
    query = select(Payout).where(Payout.developer_id == developer.id)
    
    if status:
        query = query.where(Payout.status == status)
    
    # Add pagination
    offset = (page - 1) * limit
    query = query.order_by(desc(Payout.created_at)).offset(offset).limit(limit)
    
    result = await db.execute(query)
    payouts = result.scalars().all()
    
    return [PayoutResponse.from_orm(payout) for payout in payouts]


@router.post("/payouts/request", response_model=PayoutRequestResponse)
async def request_payout(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Request a payout of pending revenue"""
    from ..db.models import DeveloperAccount, Payout
    import uuid
    
    # Get developer account
    developer_result = await db.execute(
        select(DeveloperAccount).where(
            DeveloperAccount.user_id == current_user.get("id")
        )
    )
    developer = developer_result.scalar_one_or_none()
    
    if not developer:
        raise HTTPException(status_code=404, detail="Developer account not found")
    
    # Check minimum payout threshold
    minimum_payout = Decimal('50.00')
    if developer.pending_payout < minimum_payout:
        raise HTTPException(
            status_code=400,
            detail=f"Minimum payout amount is ${minimum_payout}. Current pending: ${developer.pending_payout}"
        )
    
    # Check if there's already a pending payout
    existing_payout = await db.execute(
        select(Payout).where(
            and_(
                Payout.developer_id == developer.id,
                Payout.status == "pending"
            )
        )
    )
    
    if existing_payout.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="You already have a pending payout request")
    
    # Create payout request
    payout = Payout(
        id=str(uuid.uuid4()),
        developer_id=developer.id,
        amount=developer.pending_payout,
        status="pending",
        payment_method="default",  # Use developer's preferred method
        notes="Payout requested by developer"
    )
    
    db.add(payout)
    
    # Reset pending payout (will be restored if payout fails)
    developer.pending_payout = Decimal('0.00')
    
    await db.commit()
    
    return PayoutRequestResponse(
        payout_id=payout.id,
        amount=float(payout.amount),
        status=payout.status,
        estimated_processing_time="3-5 business days",
        message="Payout request submitted successfully"
    )


@router.get("/analytics", response_model=Dict[str, Any])
async def get_revenue_analytics(
    days: int = Query(30, ge=1, le=365),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed revenue analytics"""
    from ..db.models import DeveloperAccount, PluginSale, Plugin
    
    # Get developer account
    developer_result = await db.execute(
        select(DeveloperAccount).where(
            DeveloperAccount.user_id == current_user.get("id")
        )
    )
    developer = developer_result.scalar_one_or_none()
    
    if not developer:
        raise HTTPException(status_code=404, detail="Developer account not found")
    
    # Date range for analytics
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    # Revenue by plugin
    plugin_revenue_result = await db.execute(
        select(
            Plugin.id,
            Plugin.name,
            Plugin.price,
            func.sum(PluginSale.revenue_share_amount).label("total_revenue"),
            func.count(PluginSale.id).label("sales_count"),
            func.avg(PluginSale.sale_price).label("avg_sale_price")
        )
        .join(PluginSale, Plugin.id == PluginSale.plugin_id)
        .where(
            and_(
                Plugin.developer_id == developer.id,
                PluginSale.created_at >= start_date
            )
        )
        .group_by(Plugin.id, Plugin.name, Plugin.price)
        .order_by(desc(func.sum(PluginSale.revenue_share_amount)))
    )
    
    plugin_revenue = [
        {
            "plugin_id": row.id,
            "plugin_name": row.name,
            "plugin_price": float(row.price),
            "total_revenue": float(row.total_revenue),
            "sales_count": row.sales_count,
            "avg_sale_price": float(row.avg_sale_price) if row.avg_sale_price else 0
        }
        for row in plugin_revenue_result
    ]
    
    # Revenue by payment method
    payment_method_result = await db.execute(
        select(
            PluginSale.payment_method,
            func.sum(PluginSale.revenue_share_amount).label("total_revenue"),
            func.count(PluginSale.id).label("sales_count")
        )
        .join(Plugin, PluginSale.plugin_id == Plugin.id)
        .where(
            and_(
                Plugin.developer_id == developer.id,
                PluginSale.created_at >= start_date
            )
        )
        .group_by(PluginSale.payment_method)
        .order_by(desc(func.sum(PluginSale.revenue_share_amount)))
    )
    
    payment_methods = [
        {
            "payment_method": row.payment_method,
            "total_revenue": float(row.total_revenue),
            "sales_count": row.sales_count
        }
        for row in payment_method_result
    ]
    
    # Weekly revenue trend
    weekly_revenue_result = await db.execute(
        select(
            func.date_trunc('week', PluginSale.created_at).label("week"),
            func.sum(PluginSale.revenue_share_amount).label("revenue"),
            func.count(PluginSale.id).label("sales_count")
        )
        .join(Plugin, PluginSale.plugin_id == Plugin.id)
        .where(
            and_(
                Plugin.developer_id == developer.id,
                PluginSale.created_at >= start_date
            )
        )
        .group_by(func.date_trunc('week', PluginSale.created_at))
        .order_by(func.date_trunc('week', PluginSale.created_at))
    )
    
    weekly_revenue = [
        {
            "week": row.week.isoformat(),
            "revenue": float(row.revenue),
            "sales_count": row.sales_count
        }
        for row in weekly_revenue_result
    ]
    
    return {
        "period": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "days": days
        },
        "plugin_revenue": plugin_revenue,
        "payment_methods": payment_methods,
        "weekly_revenue": weekly_revenue,
        "summary": {
            "total_plugins": len(plugin_revenue),
            "total_revenue": sum([p["total_revenue"] for p in plugin_revenue]),
            "total_sales": sum([p["sales_count"] for p in plugin_revenue]),
            "avg_revenue_per_plugin": sum([p["total_revenue"] for p in plugin_revenue]) / len(plugin_revenue) if plugin_revenue else 0
        }
    }


@router.get("/tax-report", response_model=Dict[str, Any])
async def get_tax_report(
    year: int = Query(..., ge=2020, le=2030),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Generate tax report for a specific year"""
    from ..db.models import DeveloperAccount, PluginSale, Plugin, Payout
    
    # Get developer account
    developer_result = await db.execute(
        select(DeveloperAccount).where(
            DeveloperAccount.user_id == current_user.get("id")
        )
    )
    developer = developer_result.scalar_one_or_none()
    
    if not developer:
        raise HTTPException(status_code=404, detail="Developer account not found")
    
    # Date range for the year
    start_date = datetime(year, 1, 1)
    end_date = datetime(year + 1, 1, 1)
    
    # Get total revenue for the year
    revenue_result = await db.execute(
        select(
            func.sum(PluginSale.revenue_share_amount).label("total_revenue"),
            func.count(PluginSale.id).label("total_sales")
        )
        .join(Plugin, PluginSale.plugin_id == Plugin.id)
        .where(
            and_(
                Plugin.developer_id == developer.id,
                PluginSale.created_at >= start_date,
                PluginSale.created_at < end_date
            )
        )
    )
    
    revenue_data = revenue_result.first()
    total_revenue = float(revenue_data.total_revenue) if revenue_data.total_revenue else 0
    total_sales = revenue_data.total_sales if revenue_data.total_sales else 0
    
    # Get monthly breakdown
    monthly_revenue_result = await db.execute(
        select(
            func.extract('month', PluginSale.created_at).label("month"),
            func.sum(PluginSale.revenue_share_amount).label("revenue"),
            func.count(PluginSale.id).label("sales_count")
        )
        .join(Plugin, PluginSale.plugin_id == Plugin.id)
        .where(
            and_(
                Plugin.developer_id == developer.id,
                PluginSale.created_at >= start_date,
                PluginSale.created_at < end_date
            )
        )
        .group_by(func.extract('month', PluginSale.created_at))
        .order_by(func.extract('month', PluginSale.created_at))
    )
    
    monthly_breakdown = [
        {
            "month": int(row.month),
            "month_name": datetime(year, int(row.month), 1).strftime("%B"),
            "revenue": float(row.revenue),
            "sales_count": row.sales_count
        }
        for row in monthly_revenue_result
    ]
    
    # Get payouts for the year
    payouts_result = await db.execute(
        select(
            func.sum(Payout.amount).label("total_payouts"),
            func.count(Payout.id).label("payout_count")
        )
        .where(
            and_(
                Payout.developer_id == developer.id,
                Payout.created_at >= start_date,
                Payout.created_at < end_date,
                Payout.status == "completed"
            )
        )
    )
    
    payout_data = payouts_result.first()
    total_payouts = float(payout_data.total_payouts) if payout_data.total_payouts else 0
    payout_count = payout_data.payout_count if payout_data.payout_count else 0
    
    return {
        "year": year,
        "developer_info": {
            "id": developer.id,
            "company_name": developer.company_name,
            "support_email": developer.support_email
        },
        "summary": {
            "total_revenue": total_revenue,
            "total_sales": total_sales,
            "total_payouts": total_payouts,
            "payout_count": payout_count,
            "net_pending": total_revenue - total_payouts
        },
        "monthly_breakdown": monthly_breakdown,
        "tax_info": {
            "currency": "USD",
            "tax_year": year,
            "generated_at": datetime.utcnow().isoformat(),
            "note": "This report is for tax reporting purposes. Consult with a tax professional for advice."
        }
    }


# Admin routes for revenue management
@router.get("/admin/overview", response_model=Dict[str, Any])
async def get_admin_revenue_overview(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get administrative overview of revenue system"""
    if not current_user.get("is_superuser"):
        raise HTTPException(status_code=403, detail="Admin privileges required")
    
    from ..db.models import PluginSale, Payout, DeveloperAccount
    
    # Total platform revenue
    total_platform_revenue_result = await db.execute(
        select(func.sum(PluginSale.platform_fee_amount))
    )
    total_platform_revenue = total_platform_revenue_result.scalar() or Decimal('0.00')
    
    # Total developer revenue
    total_developer_revenue_result = await db.execute(
        select(func.sum(PluginSale.revenue_share_amount))
    )
    total_developer_revenue = total_developer_revenue_result.scalar() or Decimal('0.00')
    
    # Pending payouts
    pending_payouts_result = await db.execute(
        select(
            func.sum(Payout.amount).label("total_amount"),
            func.count(Payout.id).label("payout_count")
        )
        .where(Payout.status == "pending")
    )
    pending_data = pending_payouts_result.first()
    
    # Active developers with revenue
    active_developers_result = await db.execute(
        select(func.count(func.distinct(DeveloperAccount.id)))
        .join(Plugin, DeveloperAccount.id == Plugin.developer_id)
        .join(PluginSale, Plugin.id == PluginSale.plugin_id)
    )
    active_developers = active_developers_result.scalar() or 0
    
    return {
        "platform_revenue": {
            "total": float(total_platform_revenue),
            "percentage": 30.0  # Platform fee percentage
        },
        "developer_revenue": {
            "total": float(total_developer_revenue),
            "percentage": 70.0  # Developer share percentage
        },
        "pending_payouts": {
            "total_amount": float(pending_data.total_amount) if pending_data.total_amount else 0,
            "payout_count": pending_data.payout_count if pending_data.payout_count else 0
        },
        "statistics": {
            "active_developers": active_developers,
            "total_transactions": float(total_platform_revenue + total_developer_revenue) / 1.0,  # Assuming $1 avg
            "average_transaction": 25.0  # Placeholder
        }
    }


def get_next_payout_date() -> datetime:
    """Calculate next payout date (typically first Friday of each month)"""
    now = datetime.utcnow()
    # Get first day of next month
    if now.month == 12:
        next_month = datetime(now.year + 1, 1, 1)
    else:
        next_month = datetime(now.year, now.month + 1, 1)
    
    # Find first Friday (weekday 4)
    days_ahead = 4 - next_month.weekday()
    if days_ahead < 0:  # Friday already happened this week
        days_ahead += 7
    
    return next_month + timedelta(days=days_ahead)