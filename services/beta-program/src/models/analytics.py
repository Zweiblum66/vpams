"""Analytics models"""

from sqlalchemy import Column, String, DateTime, Integer, Float, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime

from ..core.database import Base


class BetaAnalytics(Base):
    """Beta program analytics"""
    __tablename__ = "beta_analytics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Time period
    date = Column(DateTime(timezone=True), nullable=False, index=True)
    period_type = Column(String(20), default="daily")  # daily, weekly, monthly
    
    # User metrics
    total_users = Column(Integer, default=0)
    active_users = Column(Integer, default=0)
    new_users = Column(Integer, default=0)
    churned_users = Column(Integer, default=0)
    
    # Engagement metrics
    avg_session_duration = Column(Float, default=0.0)  # minutes
    avg_sessions_per_user = Column(Float, default=0.0)
    total_page_views = Column(Integer, default=0)
    total_actions = Column(Integer, default=0)
    
    # Feedback metrics
    feedback_submitted = Column(Integer, default=0)
    bug_reports = Column(Integer, default=0)
    feature_requests = Column(Integer, default=0)
    avg_feedback_response_time = Column(Float, default=0.0)  # hours
    
    # Feature adoption
    features_enabled = Column(Integer, default=0)
    features_used = Column(Integer, default=0)
    avg_features_per_user = Column(Float, default=0.0)
    
    # System metrics
    api_calls = Column(Integer, default=0)
    error_rate = Column(Float, default=0.0)  # percentage
    avg_response_time = Column(Float, default=0.0)  # milliseconds
    
    # User segmentation
    users_by_phase = Column(JSON)  # {closed_beta: 100, open_beta: 200}
    users_by_role = Column(JSON)  # {developer: 50, designer: 30}
    users_by_company_size = Column(JSON)  # {small: 100, medium: 50}
    
    # Top metrics
    top_features = Column(JSON)  # [{feature_id: usage_count}]
    top_pages = Column(JSON)  # [{page_url: view_count}]
    top_errors = Column(JSON)  # [{error_type: count}]
    
    # Metadata
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class FeatureUsage(Base):
    """Detailed feature usage tracking"""
    __tablename__ = "feature_usage"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    beta_user_id = Column(UUID(as_uuid=True), ForeignKey("beta_users.id"), nullable=False, index=True)
    feature_id = Column(UUID(as_uuid=True), ForeignKey("feature_flags.id"), nullable=False, index=True)
    
    # Usage details
    action = Column(String(100), nullable=False)  # view, click, submit, etc.
    context = Column(JSON)  # Additional context data
    
    # Performance
    duration = Column(Float)  # milliseconds
    success = Column(Integer, default=1)  # 1 for success, 0 for failure
    error_type = Column(String(100))
    
    # A/B testing
    variant = Column(String(50))
    
    # Session info
    session_id = Column(String(100), index=True)
    ip_address = Column(String(45))
    user_agent = Column(String(500))
    
    # Metadata
    timestamp = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)