"""Analytics service for beta program"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
import pandas as pd
import io
import json

from ..models import BetaUser, FeatureUsage, Feedback, BetaAnalytics
from ..core.config import get_settings

logger = logging.getLogger(__name__)


async def calculate_engagement_metrics(
    db: AsyncSession,
    user: BetaUser
) -> int:
    """Calculate user engagement score (0-100)"""
    score = 0
    
    # Activity score (0-30)
    if user.last_active:
        days_since_active = (datetime.utcnow() - user.last_active).days
        if days_since_active <= 1:
            score += 30
        elif days_since_active <= 7:
            score += 20
        elif days_since_active <= 30:
            score += 10
    
    # Feedback score (0-30)
    if user.feedback_count >= 10:
        score += 30
    elif user.feedback_count >= 5:
        score += 20
    elif user.feedback_count >= 1:
        score += 10
    
    # Feature usage score (0-20)
    result = await db.execute(
        select(func.count(func.distinct(FeatureUsage.feature_id)))
        .where(FeatureUsage.beta_user_id == user.id)
    )
    features_used = result.scalar() or 0
    
    if features_used >= 5:
        score += 20
    elif features_used >= 3:
        score += 15
    elif features_used >= 1:
        score += 10
    
    # Bug report score (0-20)
    if user.bug_reports_count >= 5:
        score += 20
    elif user.bug_reports_count >= 2:
        score += 15
    elif user.bug_reports_count >= 1:
        score += 10
    
    return min(score, 100)


async def generate_analytics_report(
    db: AsyncSession,
    report_type: str,
    start_date: datetime,
    end_date: datetime
) -> Dict[str, Any]:
    """Generate analytics report"""
    if report_type == "users":
        return await _generate_user_report(db, start_date, end_date)
    elif report_type == "features":
        return await _generate_feature_report(db, start_date, end_date)
    elif report_type == "feedback":
        return await _generate_feedback_report(db, start_date, end_date)
    elif report_type == "engagement":
        return await _generate_engagement_report(db, start_date, end_date)
    else:
        raise ValueError(f"Unknown report type: {report_type}")


async def _generate_user_report(
    db: AsyncSession,
    start_date: datetime,
    end_date: datetime
) -> Dict[str, Any]:
    """Generate user analytics report"""
    # Get users in date range
    result = await db.execute(
        select(BetaUser).where(
            and_(
                BetaUser.joined_at >= start_date,
                BetaUser.joined_at <= end_date
            )
        )
    )
    users = result.scalars().all()
    
    # User metrics
    total_users = len(users)
    active_users = len([u for u in users if u.last_active and 
                       u.last_active >= datetime.utcnow() - timedelta(days=7)])
    
    # User distribution
    by_phase = {}
    by_role = {}
    by_company_size = {}
    
    for user in users:
        # By phase
        by_phase[user.beta_phase] = by_phase.get(user.beta_phase, 0) + 1
        
        # By role
        if user.role:
            by_role[user.role] = by_role.get(user.role, 0) + 1
    
    return {
        "total_users": total_users,
        "active_users": active_users,
        "active_rate": (active_users / total_users * 100) if total_users > 0 else 0,
        "new_users": len([u for u in users if u.joined_at >= start_date]),
        "by_phase": by_phase,
        "by_role": by_role,
        "avg_engagement_score": sum(u.engagement_score for u in users) / total_users if total_users > 0 else 0
    }


async def _generate_feature_report(
    db: AsyncSession,
    start_date: datetime,
    end_date: datetime
) -> Dict[str, Any]:
    """Generate feature usage report"""
    # Get feature usage data
    result = await db.execute(
        select(
            FeatureUsage.feature_id,
            func.count(func.distinct(FeatureUsage.beta_user_id)).label("unique_users"),
            func.count().label("total_usage"),
            func.avg(FeatureUsage.duration).label("avg_duration"),
            func.sum(FeatureUsage.success).label("success_count")
        )
        .where(
            and_(
                FeatureUsage.timestamp >= start_date,
                FeatureUsage.timestamp <= end_date
            )
        )
        .group_by(FeatureUsage.feature_id)
    )
    usage_stats = result.all()
    
    feature_report = []
    for stat in usage_stats:
        success_rate = (stat.success_count / stat.total_usage * 100) if stat.total_usage > 0 else 0
        feature_report.append({
            "feature_id": str(stat.feature_id),
            "unique_users": stat.unique_users,
            "total_usage": stat.total_usage,
            "avg_duration": stat.avg_duration or 0,
            "success_rate": success_rate
        })
    
    return {
        "features": feature_report,
        "total_features_used": len(feature_report)
    }


async def _generate_feedback_report(
    db: AsyncSession,
    start_date: datetime,
    end_date: datetime
) -> Dict[str, Any]:
    """Generate feedback report"""
    # Get feedback data
    result = await db.execute(
        select(Feedback).where(
            and_(
                Feedback.created_at >= start_date,
                Feedback.created_at <= end_date
            )
        )
    )
    feedback_items = result.scalars().all()
    
    # Categorize feedback
    by_category = {}
    by_status = {}
    by_severity = {}
    
    for item in feedback_items:
        by_category[item.category.value] = by_category.get(item.category.value, 0) + 1
        by_status[item.status.value] = by_status.get(item.status.value, 0) + 1
        if item.severity:
            by_severity[item.severity] = by_severity.get(item.severity, 0) + 1
    
    # Calculate resolution time
    resolved_items = [f for f in feedback_items if f.resolved_at]
    avg_resolution_hours = 0
    if resolved_items:
        total_hours = sum((f.resolved_at - f.created_at).total_seconds() / 3600 
                         for f in resolved_items)
        avg_resolution_hours = total_hours / len(resolved_items)
    
    return {
        "total_feedback": len(feedback_items),
        "by_category": by_category,
        "by_status": by_status,
        "by_severity": by_severity,
        "avg_resolution_hours": avg_resolution_hours,
        "resolution_rate": (len(resolved_items) / len(feedback_items) * 100) if feedback_items else 0
    }


async def _generate_engagement_report(
    db: AsyncSession,
    start_date: datetime,
    end_date: datetime
) -> Dict[str, Any]:
    """Generate engagement report"""
    # Get all users
    result = await db.execute(select(BetaUser))
    all_users = result.scalars().all()
    
    # Calculate engagement metrics
    engagement_distribution = {
        "high": 0,
        "medium": 0,
        "low": 0,
        "inactive": 0
    }
    
    for user in all_users:
        if user.engagement_score >= 70:
            engagement_distribution["high"] += 1
        elif user.engagement_score >= 40:
            engagement_distribution["medium"] += 1
        elif user.engagement_score >= 10:
            engagement_distribution["low"] += 1
        else:
            engagement_distribution["inactive"] += 1
    
    # Feature adoption
    result = await db.execute(
        select(
            func.count(func.distinct(FeatureUsage.beta_user_id)).label("users"),
            func.count(func.distinct(FeatureUsage.feature_id)).label("features")
        ).where(
            and_(
                FeatureUsage.timestamp >= start_date,
                FeatureUsage.timestamp <= end_date
            )
        )
    )
    adoption = result.one()
    
    return {
        "engagement_distribution": engagement_distribution,
        "users_using_features": adoption.users,
        "features_being_used": adoption.features,
        "avg_features_per_user": (adoption.features / adoption.users) if adoption.users > 0 else 0
    }


async def export_analytics_data(
    db: AsyncSession,
    export_type: str,
    start_date: Optional[datetime],
    end_date: Optional[datetime],
    format: str
) -> Dict[str, Any]:
    """Export analytics data"""
    # Set default dates
    if not end_date:
        end_date = datetime.utcnow()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    # Generate report
    report = await generate_analytics_report(db, export_type, start_date, end_date)
    
    # Format data
    if format == "json":
        data = json.dumps(report, indent=2, default=str)
        content_type = "application/json"
        filename = f"beta_analytics_{export_type}_{datetime.utcnow().strftime('%Y%m%d')}.json"
    
    elif format == "csv":
        # Convert to DataFrame
        if export_type == "users":
            df = pd.DataFrame([report])
        elif export_type == "features":
            df = pd.DataFrame(report["features"])
        elif export_type == "feedback":
            df = pd.DataFrame([report])
        else:
            df = pd.DataFrame([report])
        
        # Convert to CSV
        buffer = io.StringIO()
        df.to_csv(buffer, index=False)
        data = buffer.getvalue()
        content_type = "text/csv"
        filename = f"beta_analytics_{export_type}_{datetime.utcnow().strftime('%Y%m%d')}.csv"
    
    elif format == "excel":
        # Convert to DataFrame
        if export_type == "users":
            df = pd.DataFrame([report])
        elif export_type == "features":
            df = pd.DataFrame(report["features"])
        elif export_type == "feedback":
            df = pd.DataFrame([report])
        else:
            df = pd.DataFrame([report])
        
        # Convert to Excel
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Analytics', index=False)
        data = buffer.getvalue()
        content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = f"beta_analytics_{export_type}_{datetime.utcnow().strftime('%Y%m%d')}.xlsx"
    
    else:
        raise ValueError(f"Unknown format: {format}")
    
    # In a real implementation, would upload to S3 or similar
    # For now, return mock URL
    return {
        "url": f"https://storage.mams.io/exports/{filename}",
        "expires_at": (datetime.utcnow() + timedelta(hours=24)).isoformat(),
        "content_type": content_type,
        "size": len(data)
    }


async def update_daily_analytics(db: AsyncSession):
    """Update daily analytics (would be run by scheduler)"""
    today = datetime.utcnow().date()
    
    # Get metrics
    total_users = await db.scalar(select(func.count()).select_from(BetaUser))
    active_users = await db.scalar(
        select(func.count()).select_from(BetaUser)
        .where(BetaUser.last_active >= datetime.utcnow() - timedelta(days=1))
    )
    new_users = await db.scalar(
        select(func.count()).select_from(BetaUser)
        .where(func.date(BetaUser.joined_at) == today)
    )
    
    # Create or update analytics record
    result = await db.execute(
        select(BetaAnalytics).where(
            and_(
                func.date(BetaAnalytics.date) == today,
                BetaAnalytics.period_type == "daily"
            )
        )
    )
    analytics = result.scalar_one_or_none()
    
    if not analytics:
        analytics = BetaAnalytics(
            date=datetime.utcnow(),
            period_type="daily"
        )
        db.add(analytics)
    
    analytics.total_users = total_users
    analytics.active_users = active_users
    analytics.new_users = new_users
    
    await db.commit()