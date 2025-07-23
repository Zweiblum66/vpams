"""
Partner dashboard routes
"""

from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_
from datetime import datetime, timedelta

from ..core.logging import get_logger
from ..db.base import get_db
from ..db.models import (
    Partner, PartnerActivity, PartnerDeal, PartnerContact, 
    PartnerResource, PartnerCertification, PartnerApplication
)
from ..models.schemas import PartnerDashboardResponse, PartnerActivityResponse
from .dependencies import get_current_user

logger = get_logger(__name__)

router = APIRouter()


@router.get("/overview", response_model=Dict[str, Any])
async def get_dashboard_overview(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get overall dashboard statistics"""
    
    # Get basic counts
    total_partners = await db.execute(select(func.count(Partner.id)))
    active_partners = await db.execute(
        select(func.count(Partner.id)).where(Partner.status == "active")
    )
    pending_applications = await db.execute(
        select(func.count(PartnerApplication.id)).where(PartnerApplication.status == "submitted")
    )
    
    # Get recent activities (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    recent_activities = await db.execute(
        select(func.count(PartnerActivity.id))
        .where(PartnerActivity.created_at >= thirty_days_ago)
    )
    
    # Get deal statistics
    active_deals = await db.execute(
        select(func.count(PartnerDeal.id))
        .where(PartnerDeal.stage.in_(["prospecting", "qualification", "proposal", "negotiation"]))
    )
    
    total_deal_value = await db.execute(
        select(func.sum(PartnerDeal.deal_value))
        .where(PartnerDeal.stage.in_(["prospecting", "qualification", "proposal", "negotiation"]))
    )
    
    # Get partner type distribution
    partner_types = await db.execute(
        select(Partner.partner_type, func.count(Partner.id))
        .group_by(Partner.partner_type)
    )
    
    return {
        "summary": {
            "total_partners": total_partners.scalar() or 0,
            "active_partners": active_partners.scalar() or 0,
            "pending_applications": pending_applications.scalar() or 0,
            "recent_activities": recent_activities.scalar() or 0,
            "active_deals": active_deals.scalar() or 0,
            "total_deal_value": float(total_deal_value.scalar() or 0)
        },
        "partner_distribution": {
            row[0]: row[1] for row in partner_types.all()
        },
        "last_updated": datetime.utcnow().isoformat()
    }


@router.get("/partner/{partner_id}", response_model=PartnerDashboardResponse)
async def get_partner_dashboard(
    partner_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get dashboard data for a specific partner"""
    
    # Get partner
    partner_result = await db.execute(select(Partner).where(Partner.id == partner_id))
    partner = partner_result.scalar_one_or_none()
    
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    
    # Get partner statistics
    statistics = await get_partner_statistics(db, partner_id)
    
    # Get recent activities (last 30 activities)
    activities_result = await db.execute(
        select(PartnerActivity)
        .where(PartnerActivity.partner_id == partner_id)
        .order_by(desc(PartnerActivity.created_at))
        .limit(30)
    )
    activities = activities_result.scalars().all()
    
    # Get active deals
    deals_result = await db.execute(
        select(PartnerDeal)
        .where(
            and_(
                PartnerDeal.partner_id == partner_id,
                PartnerDeal.stage.in_(["prospecting", "qualification", "proposal", "negotiation"])
            )
        )
        .order_by(desc(PartnerDeal.created_at))
        .limit(10)
    )
    deals = deals_result.scalars().all()
    
    # Get certifications
    certifications_result = await db.execute(
        select(PartnerCertification)
        .where(PartnerCertification.partner_id == partner_id)
        .order_by(desc(PartnerCertification.completion_date))
    )
    certifications = certifications_result.scalars().all()
    
    # Get resources count
    resources_count = await db.execute(
        select(func.count(PartnerResource.id))
        .where(PartnerResource.partner_id == partner_id)
    )
    
    # Get contacts count
    contacts_count = await db.execute(
        select(func.count(PartnerContact.id))
        .where(PartnerContact.partner_id == partner_id)
    )
    
    from ..models.schemas import PartnerResponse, PartnerDealResponse
    
    return PartnerDashboardResponse(
        partner_info=PartnerResponse.from_orm(partner),
        statistics=statistics,
        recent_activities=[PartnerActivityResponse.from_orm(activity) for activity in activities],
        active_deals=[PartnerDealResponse.from_orm(deal) for deal in deals],
        certifications=[{
            "id": str(cert.id),
            "name": cert.certification_name,
            "type": cert.certification_type,
            "status": cert.status,
            "completion_date": cert.completion_date,
            "expiry_date": cert.expiry_date
        } for cert in certifications],
        resources_count=resources_count.scalar() or 0,
        contacts_count=contacts_count.scalar() or 0
    )


@router.get("/analytics/trends", response_model=Dict[str, Any])
async def get_analytics_trends(
    days: int = Query(30, ge=1, le=365),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get analytics trends over time"""
    
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    # Partner registration trends
    partner_registrations = await db.execute(
        select(
            func.date(Partner.created_at).label("date"),
            func.count(Partner.id).label("count")
        )
        .where(Partner.created_at >= start_date)
        .group_by(func.date(Partner.created_at))
        .order_by(func.date(Partner.created_at))
    )
    
    # Activity trends
    activity_trends = await db.execute(
        select(
            func.date(PartnerActivity.created_at).label("date"),
            PartnerActivity.activity_type,
            func.count(PartnerActivity.id).label("count")
        )
        .where(PartnerActivity.created_at >= start_date)
        .group_by(func.date(PartnerActivity.created_at), PartnerActivity.activity_type)
        .order_by(func.date(PartnerActivity.created_at))
    )
    
    # Deal value trends
    deal_trends = await db.execute(
        select(
            func.date(PartnerDeal.created_at).label("date"),
            func.sum(PartnerDeal.deal_value).label("total_value"),
            func.count(PartnerDeal.id).label("deal_count")
        )
        .where(PartnerDeal.created_at >= start_date)
        .group_by(func.date(PartnerDeal.created_at))
        .order_by(func.date(PartnerDeal.created_at))
    )
    
    return {
        "period": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "days": days
        },
        "partner_registrations": [
            {
                "date": row.date.isoformat(),
                "count": row.count
            }
            for row in partner_registrations.all()
        ],
        "activity_trends": [
            {
                "date": row.date.isoformat(),
                "activity_type": row.activity_type,
                "count": row.count
            }
            for row in activity_trends.all()
        ],
        "deal_trends": [
            {
                "date": row.date.isoformat(),
                "total_value": float(row.total_value or 0),
                "deal_count": row.deal_count
            }
            for row in deal_trends.all()
        ]
    }


@router.get("/partner/{partner_id}/performance", response_model=Dict[str, Any])
async def get_partner_performance(
    partner_id: str,
    days: int = Query(90, ge=1, le=365),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get partner performance metrics"""
    
    # Verify partner exists
    partner_result = await db.execute(select(Partner).where(Partner.id == partner_id))
    partner = partner_result.scalar_one_or_none()
    
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    # Deal performance
    deals_result = await db.execute(
        select(
            func.count(PartnerDeal.id).label("total_deals"),
            func.sum(PartnerDeal.deal_value).label("total_value"),
            func.avg(PartnerDeal.deal_value).label("avg_deal_value"),
            func.sum(PartnerDeal.partner_commission_amount).label("total_commission")
        )
        .where(
            and_(
                PartnerDeal.partner_id == partner_id,
                PartnerDeal.created_at >= start_date
            )
        )
    )
    deal_metrics = deals_result.first()
    
    # Deal stage distribution
    stage_distribution = await db.execute(
        select(PartnerDeal.stage, func.count(PartnerDeal.id))
        .where(
            and_(
                PartnerDeal.partner_id == partner_id,
                PartnerDeal.created_at >= start_date
            )
        )
        .group_by(PartnerDeal.stage)
    )
    
    # Activity performance
    activity_counts = await db.execute(
        select(
            PartnerActivity.activity_type,
            func.count(PartnerActivity.id)
        )
        .where(
            and_(
                PartnerActivity.partner_id == partner_id,
                PartnerActivity.created_at >= start_date
            )
        )
        .group_by(PartnerActivity.activity_type)
    )
    
    # Resource engagement
    resource_stats = await db.execute(
        select(
            func.sum(PartnerResource.download_count).label("total_downloads"),
            func.sum(PartnerResource.view_count).label("total_views"),
            func.count(PartnerResource.id).label("resource_count")
        )
        .where(PartnerResource.partner_id == partner_id)
    )
    resource_metrics = resource_stats.first()
    
    return {
        "period": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "days": days
        },
        "deal_performance": {
            "total_deals": deal_metrics.total_deals or 0,
            "total_value": float(deal_metrics.total_value or 0),
            "avg_deal_value": float(deal_metrics.avg_deal_value or 0),
            "total_commission": float(deal_metrics.total_commission or 0),
            "stage_distribution": {row[0]: row[1] for row in stage_distribution.all()}
        },
        "activity_performance": {
            row[0]: row[1] for row in activity_counts.all()
        },
        "resource_engagement": {
            "total_downloads": resource_metrics.total_downloads or 0,
            "total_views": resource_metrics.total_views or 0,
            "resource_count": resource_metrics.resource_count or 0
        }
    }


async def get_partner_statistics(db: AsyncSession, partner_id: str) -> Dict[str, Any]:
    """Get comprehensive partner statistics"""
    
    # Deal statistics
    total_deals = await db.execute(
        select(func.count(PartnerDeal.id))
        .where(PartnerDeal.partner_id == partner_id)
    )
    
    active_deals = await db.execute(
        select(func.count(PartnerDeal.id))
        .where(
            and_(
                PartnerDeal.partner_id == partner_id,
                PartnerDeal.stage.in_(["prospecting", "qualification", "proposal", "negotiation"])
            )
        )
    )
    
    won_deals = await db.execute(
        select(func.count(PartnerDeal.id))
        .where(
            and_(
                PartnerDeal.partner_id == partner_id,
                PartnerDeal.stage == "closed_won"
            )
        )
    )
    
    total_deal_value = await db.execute(
        select(func.sum(PartnerDeal.deal_value))
        .where(PartnerDeal.partner_id == partner_id)
    )
    
    total_commission = await db.execute(
        select(func.sum(PartnerDeal.partner_commission_amount))
        .where(PartnerDeal.partner_id == partner_id)
    )
    
    # Activity statistics (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    recent_activities = await db.execute(
        select(func.count(PartnerActivity.id))
        .where(
            and_(
                PartnerActivity.partner_id == partner_id,
                PartnerActivity.created_at >= thirty_days_ago
            )
        )
    )
    
    # Certification statistics
    active_certifications = await db.execute(
        select(func.count(PartnerCertification.id))
        .where(
            and_(
                PartnerCertification.partner_id == partner_id,
                PartnerCertification.status == "completed"
            )
        )
    )
    
    return {
        "deals": {
            "total": total_deals.scalar() or 0,
            "active": active_deals.scalar() or 0,
            "won": won_deals.scalar() or 0,
            "win_rate": (won_deals.scalar() or 0) / max(total_deals.scalar() or 1, 1) * 100,
            "total_value": float(total_deal_value.scalar() or 0),
            "total_commission": float(total_commission.scalar() or 0)
        },
        "activity": {
            "recent_count": recent_activities.scalar() or 0
        },
        "certifications": {
            "active": active_certifications.scalar() or 0
        }
    }