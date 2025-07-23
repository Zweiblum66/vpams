"""Analytics schemas"""

from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional
from datetime import datetime


class BetaAnalyticsResponse(BaseModel):
    """Beta analytics response"""
    period: str
    start_date: datetime
    end_date: datetime
    current_metrics: Dict[str, Any]
    trends: Dict[str, float]
    time_series: List[Dict[str, Any]]


class FeatureUsageStats(BaseModel):
    """Feature usage statistics"""
    start_date: datetime
    end_date: datetime
    features: List[Dict[str, Any]]
    total_features: int


class UserEngagementMetrics(BaseModel):
    """User engagement metrics"""
    total_users: int
    active_users: int
    active_rate: float
    avg_feedback_per_user: float
    avg_engagement_score: float
    engagement_distribution: Dict[str, int]
    user_segments: Dict[str, Dict[str, int]]


class FeedbackAnalytics(BaseModel):
    """Feedback analytics"""
    start_date: datetime
    end_date: datetime
    total_feedback: int
    by_category: Dict[str, int]
    by_status: Dict[str, int]
    avg_resolution_time_hours: float
    top_feedback: List[Dict[str, Any]]


class AnalyticsExportRequest(BaseModel):
    """Analytics export request"""
    export_type: str = Field(..., regex="^(users|features|feedback|engagement|full)$")
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    format: str = Field("csv", regex="^(csv|excel|json)$")