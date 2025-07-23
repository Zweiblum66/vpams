"""Analytics API endpoints"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, text
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
import pandas as pd

from ..core.database import get_db
from ..core.auth import require_admin
from ..models import (
    BetaAnalytics, FeatureUsage, BetaUser, FeatureFlag, 
    Feedback, FeedbackCategory, FeedbackStatus
)
from ..schemas.analytics import (
    BetaAnalyticsResponse,
    FeatureUsageStats,
    UserEngagementMetrics,
    FeedbackAnalytics,
    AnalyticsExportRequest
)
from ..services.analytics_service import (
    calculate_engagement_metrics,
    generate_analytics_report,
    export_analytics_data
)

router = APIRouter(prefix="/beta/analytics", tags=["Analytics"])


@router.get("", response_model=BetaAnalyticsResponse)
async def get_beta_analytics(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    period: str = Query("daily", regex="^(daily|weekly|monthly)$"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Get beta program analytics (admin only)"""
    # Set default date range
    if not end_date:
        end_date = datetime.utcnow()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    # Get analytics data
    result = await db.execute(
        select(BetaAnalytics)
        .where(
            and_(
                BetaAnalytics.date >= start_date,
                BetaAnalytics.date <= end_date,
                BetaAnalytics.period_type == period
            )
        )
        .order_by(BetaAnalytics.date)
    )
    analytics = result.scalars().all()
    
    # Get current metrics
    current_metrics = await _get_current_metrics(db)
    
    # Calculate trends
    trends = _calculate_trends(analytics)
    
    return BetaAnalyticsResponse(
        period=period,
        start_date=start_date,
        end_date=end_date,
        current_metrics=current_metrics,
        trends=trends,
        time_series=[{
            "date": a.date,
            "total_users": a.total_users,
            "active_users": a.active_users,
            "new_users": a.new_users,
            "feedback_submitted": a.feedback_submitted,
            "features_used": a.features_used,
            "error_rate": a.error_rate
        } for a in analytics]
    )


@router.get("/usage", response_model=FeatureUsageStats)
async def get_feature_usage_stats(
    feature_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Get feature usage statistics (admin only)"""
    # Set default date range
    if not end_date:
        end_date = datetime.utcnow()
    if not start_date:
        start_date = end_date - timedelta(days=7)
    
    # Build query
    query = select(
        FeatureUsage.feature_id,
        func.count(func.distinct(FeatureUsage.beta_user_id)).label("unique_users"),
        func.count().label("total_usage"),
        func.avg(FeatureUsage.duration).label("avg_duration"),
        func.sum(FeatureUsage.success).label("success_count"),
        func.count().label("total_count")
    ).where(
        and_(
            FeatureUsage.timestamp >= start_date,
            FeatureUsage.timestamp <= end_date
        )
    )
    
    if feature_id:
        query = query.where(FeatureUsage.feature_id == feature_id)
    
    query = query.group_by(FeatureUsage.feature_id)
    
    # Execute query
    result = await db.execute(query)
    usage_data = result.all()
    
    # Get feature details
    feature_ids = [row.feature_id for row in usage_data]
    features_result = await db.execute(
        select(FeatureFlag).where(FeatureFlag.id.in_(feature_ids))
    )
    features = {str(f.id): f for f in features_result.scalars().all()}
    
    # Format response
    feature_stats = []
    for row in usage_data:
        feature = features.get(str(row.feature_id))
        if feature:
            success_rate = (row.success_count / row.total_count * 100) if row.total_count > 0 else 0
            feature_stats.append({
                "feature_id": str(row.feature_id),
                "feature_name": feature.name,
                "unique_users": row.unique_users,
                "total_usage": row.total_usage,
                "avg_duration": row.avg_duration or 0,
                "success_rate": success_rate,
                "error_count": row.total_count - row.success_count
            })
    
    return FeatureUsageStats(
        start_date=start_date,
        end_date=end_date,
        features=feature_stats,
        total_features=len(feature_stats)
    )


@router.get("/engagement", response_model=UserEngagementMetrics)
async def get_user_engagement_metrics(
    cohort: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Get user engagement metrics (admin only)"""
    # Build user query
    query = select(BetaUser)
    
    if cohort == "active":
        query = query.where(
            BetaUser.last_active >= datetime.utcnow() - timedelta(days=7)
        )
    elif cohort == "new":
        query = query.where(
            BetaUser.joined_at >= datetime.utcnow() - timedelta(days=30)
        )
    
    # Get users
    result = await db.execute(query)
    users = result.scalars().all()
    
    # Calculate metrics
    total_users = len(users)
    active_users = len([u for u in users if u.last_active and 
                       u.last_active >= datetime.utcnow() - timedelta(days=7)])
    
    # Calculate engagement distribution
    engagement_distribution = {
        "high": len([u for u in users if u.engagement_score >= 70]),
        "medium": len([u for u in users if 30 <= u.engagement_score < 70]),
        "low": len([u for u in users if u.engagement_score < 30])
    }
    
    # Calculate average metrics
    avg_feedback = sum(u.feedback_count for u in users) / total_users if total_users > 0 else 0
    avg_engagement = sum(u.engagement_score for u in users) / total_users if total_users > 0 else 0
    
    # User segments
    user_segments = {
        "by_role": {},
        "by_phase": {},
        "by_company_size": {}
    }
    
    for user in users:
        # By role
        if user.role:
            user_segments["by_role"][user.role] = user_segments["by_role"].get(user.role, 0) + 1
        
        # By phase
        user_segments["by_phase"][user.beta_phase] = user_segments["by_phase"].get(user.beta_phase, 0) + 1
    
    return UserEngagementMetrics(
        total_users=total_users,
        active_users=active_users,
        active_rate=(active_users / total_users * 100) if total_users > 0 else 0,
        avg_feedback_per_user=avg_feedback,
        avg_engagement_score=avg_engagement,
        engagement_distribution=engagement_distribution,
        user_segments=user_segments
    )


@router.get("/feedback", response_model=FeedbackAnalytics)
async def get_feedback_analytics(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Get feedback analytics (admin only)"""
    # Set default date range
    if not end_date:
        end_date = datetime.utcnow()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    # Get feedback stats
    result = await db.execute(
        select(
            Feedback.category,
            Feedback.status,
            func.count().label("count"),
            func.avg(
                func.extract('epoch', Feedback.resolved_at - Feedback.created_at) / 3600
            ).label("avg_resolution_hours")
        )
        .where(
            and_(
                Feedback.created_at >= start_date,
                Feedback.created_at <= end_date
            )
        )
        .group_by(Feedback.category, Feedback.status)
    )
    feedback_stats = result.all()
    
    # Organize by category
    by_category = {}
    by_status = {}
    
    for stat in feedback_stats:
        # By category
        if stat.category not in by_category:
            by_category[stat.category] = 0
        by_category[stat.category] += stat.count
        
        # By status
        if stat.status not in by_status:
            by_status[stat.status] = 0
        by_status[stat.status] += stat.count
    
    # Get top feedback items
    result = await db.execute(
        select(Feedback)
        .where(
            and_(
                Feedback.created_at >= start_date,
                Feedback.created_at <= end_date
            )
        )
        .order_by(Feedback.upvotes.desc())
        .limit(10)
    )
    top_feedback = result.scalars().all()
    
    # Calculate resolution metrics
    resolved_feedback = [s for s in feedback_stats if s.status == FeedbackStatus.RESOLVED]
    avg_resolution_time = sum(s.avg_resolution_hours or 0 for s in resolved_feedback) / len(resolved_feedback) if resolved_feedback else 0
    
    return FeedbackAnalytics(
        start_date=start_date,
        end_date=end_date,
        total_feedback=sum(by_category.values()),
        by_category=by_category,
        by_status=by_status,
        avg_resolution_time_hours=avg_resolution_time,
        top_feedback=[{
            "id": str(f.id),
            "title": f.title,
            "category": f.category,
            "upvotes": f.upvotes,
            "status": f.status
        } for f in top_feedback]
    )


@router.post("/export")
async def export_analytics(
    request: AnalyticsExportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Export analytics data (admin only)"""
    try:
        # Generate export data
        export_data = await export_analytics_data(
            db,
            request.export_type,
            request.start_date,
            request.end_date,
            request.format
        )
        
        return {
            "message": "Export generated successfully",
            "download_url": export_data["url"],
            "expires_at": export_data["expires_at"]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Export failed: {str(e)}"
        )


async def _get_current_metrics(db: AsyncSession) -> Dict[str, Any]:
    """Get current beta program metrics"""
    # Total users
    total_users = await db.scalar(select(func.count()).select_from(BetaUser))
    
    # Active users (last 7 days)
    active_users = await db.scalar(
        select(func.count()).select_from(BetaUser)
        .where(BetaUser.last_active >= datetime.utcnow() - timedelta(days=7))
    )
    
    # Total feedback
    total_feedback = await db.scalar(select(func.count()).select_from(Feedback))
    
    # Active features
    active_features = await db.scalar(
        select(func.count()).select_from(FeatureFlag)
        .where(FeatureFlag.is_enabled == True)
    )
    
    return {
        "total_users": total_users,
        "active_users": active_users,
        "total_feedback": total_feedback,
        "active_features": active_features,
        "active_rate": (active_users / total_users * 100) if total_users > 0 else 0
    }


def _calculate_trends(analytics: List[BetaAnalytics]) -> Dict[str, float]:
    """Calculate trends from analytics data"""
    if len(analytics) < 2:
        return {
            "users": 0,
            "engagement": 0,
            "feedback": 0,
            "features": 0
        }
    
    # Compare last period to previous
    latest = analytics[-1]
    previous = analytics[-2]
    
    def calc_change(new, old):
        if old == 0:
            return 100 if new > 0 else 0
        return ((new - old) / old) * 100
    
    return {
        "users": calc_change(latest.total_users, previous.total_users),
        "engagement": calc_change(latest.active_users, previous.active_users),
        "feedback": calc_change(latest.feedback_submitted, previous.feedback_submitted),
        "features": calc_change(latest.features_used, previous.features_used)
    }