"""
User Behavior Tracking API

This module provides REST API endpoints for user behavior tracking and analysis.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from shared.auth.dependencies import get_current_user
from shared.db.postgres import get_session
from shared.tracing.python_tracing import trace_async_function

from ...services.behavior_tracker import BehaviorTracker, UserSegment, ActivityLevel
from ...models.analytics import UserBehaviorResponse

router = APIRouter()

# Initialize behavior tracker
behavior_tracker = BehaviorTracker()


class UserActionRequest(BaseModel):
    """Request model for tracking user actions."""
    action: str = Field(..., description="Action name")
    context: Dict[str, Any] = Field(default_factory=dict, description="Action context")
    session_id: Optional[str] = Field(None, description="Session ID")


class BehaviorInsightsResponse(BaseModel):
    """Response model for user behavior insights."""
    user_id: str
    segment: Optional[str]
    activity_level: Optional[str]
    current_metrics: Dict[str, Any]
    trends: Dict[str, float]
    feature_usage: Dict[str, int]
    recent_activity: List[Dict[str, Any]]
    recommendations: List[str]


class EngagementMetricsResponse(BaseModel):
    """Response model for engagement metrics."""
    total_active_users: int
    avg_session_duration_minutes: float
    segments_distribution: Dict[str, int]
    feature_adoption_rates: Dict[str, float]
    retention_metrics: Dict[str, float]
    generated_at: str


class UserSegmentationResponse(BaseModel):
    """Response model for user segmentation."""
    segments: Dict[str, List[str]]
    total_users: int
    segmentation_timestamp: str


@router.post("/track")
async def track_user_action(
    request: UserActionRequest,
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    """Track a user action for behavior analysis."""
    
    # Add tracking to background tasks for performance
    background_tasks.add_task(
        behavior_tracker.track_user_action,
        str(current_user.id),
        request.session_id or "default",
        request.action,
        request.context,
        db
    )
    
    return {"status": "accepted", "message": "Action tracking queued"}


@router.get("/insights/{user_id}", response_model=BehaviorInsightsResponse)
async def get_user_insights(
    user_id: str,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    """Get detailed behavior insights for a specific user."""
    
    # Check permissions - users can only view their own insights unless admin
    if str(current_user.id) != user_id and not current_user.has_permission("analytics.view_all"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    insights = await behavior_tracker.get_user_insights(user_id, db)
    
    if "error" in insights:
        raise HTTPException(status_code=404, detail=insights["error"])
    
    return BehaviorInsightsResponse(**insights)


@router.get("/my-insights", response_model=BehaviorInsightsResponse)
async def get_my_insights(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    """Get behavior insights for the current user."""
    
    insights = await behavior_tracker.get_user_insights(str(current_user.id), db)
    
    if "error" in insights:
        raise HTTPException(status_code=404, detail=insights["error"])
    
    return BehaviorInsightsResponse(**insights)


@router.get("/segments", response_model=UserSegmentationResponse)
async def get_user_segmentation(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    """Get user segmentation data."""
    
    if not current_user.has_permission("analytics.view"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    segments = await behavior_tracker.segment_users(db)
    total_users = sum(len(users) for users in segments.values())
    
    return UserSegmentationResponse(
        segments=segments,
        total_users=total_users,
        segmentation_timestamp=datetime.utcnow().isoformat()
    )


@router.get("/patterns")
async def get_behavior_patterns(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    """Get discovered behavior patterns."""
    
    if not current_user.has_permission("analytics.view"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    patterns = await behavior_tracker.analyze_user_patterns(db)
    
    return {
        "patterns": [
            {
                "pattern_id": p.pattern_id,
                "pattern_name": p.pattern_name,
                "description": p.description,
                "metrics": p.metrics,
                "users_count": p.users_count,
                "confidence": p.confidence
            }
            for p in patterns
        ],
        "analysis_timestamp": datetime.utcnow().isoformat()
    }


@router.get("/engagement", response_model=EngagementMetricsResponse)
async def get_engagement_metrics(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    """Get overall user engagement metrics."""
    
    if not current_user.has_permission("analytics.view"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    metrics = await behavior_tracker.get_engagement_metrics(db)
    
    if not metrics:
        raise HTTPException(status_code=500, detail="Failed to generate engagement metrics")
    
    return EngagementMetricsResponse(**metrics)


@router.get("/cohort-analysis")
async def get_cohort_analysis(
    cohort_size: str = Query("weekly", description="Cohort size: daily, weekly, monthly"),
    periods: int = Query(12, ge=1, le=52, description="Number of periods to analyze"),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    """Get cohort analysis for user retention."""
    
    if not current_user.has_permission("analytics.view"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # This would implement cohort analysis logic
    # For now, return a placeholder response
    return {
        "cohort_analysis": {
            "cohort_size": cohort_size,
            "periods": periods,
            "cohorts": [],
            "message": "Cohort analysis implementation in progress"
        },
        "generated_at": datetime.utcnow().isoformat()
    }


@router.get("/funnel-analysis")
async def get_funnel_analysis(
    funnel_steps: List[str] = Query(..., description="Ordered list of funnel steps"),
    timeframe: str = Query("30d", description="Analysis timeframe"),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    """Get funnel analysis for user journey."""
    
    if not current_user.has_permission("analytics.view"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # This would implement funnel analysis logic
    # For now, return a placeholder response
    return {
        "funnel_analysis": {
            "steps": funnel_steps,
            "timeframe": timeframe,
            "conversion_rates": [],
            "drop_off_points": [],
            "message": "Funnel analysis implementation in progress"
        },
        "generated_at": datetime.utcnow().isoformat()
    }


@router.get("/feature-usage")
async def get_feature_usage_analytics(
    timeframe: str = Query("30d", description="Analysis timeframe"),
    segment: Optional[str] = Query(None, description="User segment filter"),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    """Get feature usage analytics."""
    
    if not current_user.has_permission("analytics.view"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # Parse timeframe
    end_time = datetime.utcnow()
    if timeframe == "7d":
        start_time = end_time - timedelta(days=7)
    elif timeframe == "30d":
        start_time = end_time - timedelta(days=30)
    elif timeframe == "90d":
        start_time = end_time - timedelta(days=90)
    else:
        start_time = end_time - timedelta(days=30)
    
    # This would implement feature usage analysis
    # For now, return a placeholder response
    return {
        "feature_usage": {
            "timeframe": timeframe,
            "segment_filter": segment,
            "features": [],
            "message": "Feature usage analysis implementation in progress"
        },
        "analysis_period": {
            "start": start_time.isoformat(),
            "end": end_time.isoformat()
        },
        "generated_at": datetime.utcnow().isoformat()
    }


@router.post("/segment-users")
async def trigger_user_segmentation(
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    """Trigger user segmentation analysis."""
    
    if not current_user.has_permission("analytics.admin"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # Add segmentation task to background
    background_tasks.add_task(behavior_tracker.segment_users, db)
    
    return {
        "status": "accepted",
        "message": "User segmentation analysis queued",
        "triggered_at": datetime.utcnow().isoformat()
    }


@router.post("/analyze-patterns")
async def trigger_pattern_analysis(
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    """Trigger behavior pattern analysis."""
    
    if not current_user.has_permission("analytics.admin"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # Add pattern analysis task to background
    background_tasks.add_task(behavior_tracker.analyze_user_patterns, db)
    
    return {
        "status": "accepted",
        "message": "Behavior pattern analysis queued",
        "triggered_at": datetime.utcnow().isoformat()
    }


@router.get("/health")
async def health_check():
    """Health check for behavior tracking service."""
    return {
        "status": "healthy",
        "service": "user_behavior_tracking",
        "timestamp": datetime.utcnow().isoformat()
    }