"""
Analytics Data Models

This module defines the data models for analytics tracking and reporting.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum
import uuid

from sqlalchemy import Column, String, DateTime, Integer, Float, Boolean, Text, JSON, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel, Field

Base = declarative_base()


class EventType(str, Enum):
    """Types of events that can be tracked."""
    PAGE_VIEW = "page_view"
    USER_ACTION = "user_action"
    API_CALL = "api_call"
    ASSET_UPLOAD = "asset_upload"
    ASSET_DOWNLOAD = "asset_download"
    ASSET_VIEW = "asset_view"
    SEARCH_QUERY = "search_query"
    WORKFLOW_START = "workflow_start"
    WORKFLOW_COMPLETE = "workflow_complete"
    LOGIN = "login"
    LOGOUT = "logout"
    ERROR = "error"
    SYSTEM_EVENT = "system_event"


class UserSession(Base):
    """User session tracking."""
    __tablename__ = "user_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    session_id = Column(String(255), nullable=False, unique=True, index=True)
    
    # Session metadata
    started_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    last_activity_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    
    # Client information
    user_agent = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    device_type = Column(String(50), nullable=True)  # desktop, mobile, tablet
    browser = Column(String(100), nullable=True)
    os = Column(String(100), nullable=True)
    
    # Session metrics
    page_views = Column(Integer, default=0)
    actions_count = Column(Integer, default=0)
    assets_viewed = Column(Integer, default=0)
    searches_performed = Column(Integer, default=0)
    
    # Location data (if available)
    country = Column(String(2), nullable=True)  # ISO country code
    region = Column(String(100), nullable=True)
    city = Column(String(100), nullable=True)
    
    __table_args__ = (
        Index('idx_user_sessions_user_started', 'user_id', 'started_at'),
        Index('idx_user_sessions_activity', 'last_activity_at'),
    )


class Event(Base):
    """Generic event tracking."""
    __tablename__ = "events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Event identification
    event_type = Column(String(50), nullable=False, index=True)
    event_name = Column(String(255), nullable=False, index=True)
    category = Column(String(100), nullable=True, index=True)
    
    # Context
    user_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    session_id = Column(String(255), nullable=True, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, index=True)
    
    # Event data
    properties = Column(JSONB, nullable=True)
    metadata = Column(JSONB, nullable=True)
    
    # Performance tracking
    duration_ms = Column(Integer, nullable=True)
    
    # Request context
    request_id = Column(String(255), nullable=True)
    trace_id = Column(String(255), nullable=True)
    
    # Source information
    source_service = Column(String(100), nullable=True)
    source_component = Column(String(100), nullable=True)
    
    __table_args__ = (
        Index('idx_events_type_timestamp', 'event_type', 'timestamp'),
        Index('idx_events_user_timestamp', 'user_id', 'timestamp'),
        Index('idx_events_category_timestamp', 'category', 'timestamp'),
    )


class AssetInteraction(Base):
    """Asset-specific interaction tracking."""
    __tablename__ = "asset_interactions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Asset and user context
    asset_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    session_id = Column(String(255), nullable=True)
    
    # Interaction details
    interaction_type = Column(String(50), nullable=False)  # view, download, edit, share, etc.
    timestamp = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, index=True)
    duration_seconds = Column(Integer, nullable=True)
    
    # Asset context
    asset_type = Column(String(50), nullable=True)
    asset_size_bytes = Column(Integer, nullable=True)
    project_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    
    # Interaction metadata
    metadata = Column(JSONB, nullable=True)
    
    __table_args__ = (
        Index('idx_asset_interactions_asset_timestamp', 'asset_id', 'timestamp'),
        Index('idx_asset_interactions_user_timestamp', 'user_id', 'timestamp'),
        Index('idx_asset_interactions_type_timestamp', 'interaction_type', 'timestamp'),
    )


class SearchQuery(Base):
    """Search query tracking."""
    __tablename__ = "search_queries"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Query context
    user_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    session_id = Column(String(255), nullable=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, index=True)
    
    # Query details
    query_text = Column(Text, nullable=False)
    query_type = Column(String(50), nullable=True)  # basic, advanced, natural_language
    filters = Column(JSONB, nullable=True)
    sort_order = Column(String(100), nullable=True)
    
    # Results
    results_count = Column(Integer, nullable=True)
    response_time_ms = Column(Integer, nullable=True)
    clicked_results = Column(JSONB, nullable=True)  # Array of clicked result IDs
    
    # Context
    search_context = Column(String(100), nullable=True)  # browse, project, workflow
    project_id = Column(UUID(as_uuid=True), nullable=True)
    
    __table_args__ = (
        Index('idx_search_queries_user_timestamp', 'user_id', 'timestamp'),
        Index('idx_search_queries_text_timestamp', 'query_text', 'timestamp'),
    )


class UsageMetrics(Base):
    """Aggregated usage metrics (time-series data)."""
    __tablename__ = "usage_metrics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Time dimension
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    granularity = Column(String(20), nullable=False)  # minute, hour, day, week, month
    
    # Metric identification
    metric_name = Column(String(100), nullable=False, index=True)
    dimensions = Column(JSONB, nullable=True)  # Additional grouping dimensions
    
    # Metric values
    value = Column(Float, nullable=False)
    count = Column(Integer, nullable=True)
    min_value = Column(Float, nullable=True)
    max_value = Column(Float, nullable=True)
    avg_value = Column(Float, nullable=True)
    
    # Metadata
    metadata = Column(JSONB, nullable=True)
    
    __table_args__ = (
        Index('idx_usage_metrics_name_timestamp', 'metric_name', 'timestamp'),
        Index('idx_usage_metrics_granularity_timestamp', 'granularity', 'timestamp'),
    )


class UserBehavior(Base):
    """User behavior patterns and segments."""
    __tablename__ = "user_behavior"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # User identification
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Time period
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)
    period_type = Column(String(20), nullable=False)  # daily, weekly, monthly
    
    # Behavior metrics
    sessions_count = Column(Integer, default=0)
    total_time_minutes = Column(Integer, default=0)
    page_views = Column(Integer, default=0)
    actions_count = Column(Integer, default=0)
    
    # Feature usage
    features_used = Column(JSONB, nullable=True)  # Array of feature names
    most_used_feature = Column(String(100), nullable=True)
    
    # Content interaction
    assets_viewed = Column(Integer, default=0)
    assets_uploaded = Column(Integer, default=0)
    assets_downloaded = Column(Integer, default=0)
    searches_performed = Column(Integer, default=0)
    
    # Workflow usage
    workflows_created = Column(Integer, default=0)
    workflows_executed = Column(Integer, default=0)
    
    # Engagement metrics
    bounce_rate = Column(Float, nullable=True)  # % of single-page sessions
    avg_session_duration = Column(Float, nullable=True)  # minutes
    return_visitor = Column(Boolean, default=False)
    
    # Computed segments
    user_segment = Column(String(50), nullable=True)  # power_user, casual, new, etc.
    activity_level = Column(String(20), nullable=True)  # high, medium, low
    
    __table_args__ = (
        Index('idx_user_behavior_user_period', 'user_id', 'period_start'),
        Index('idx_user_behavior_segment', 'user_segment'),
    )


# Pydantic models for API
class EventCreate(BaseModel):
    """Event creation model."""
    event_type: EventType
    event_name: str
    category: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    properties: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    duration_ms: Optional[int] = None
    source_service: Optional[str] = None
    source_component: Optional[str] = None


class AssetInteractionCreate(BaseModel):
    """Asset interaction creation model."""
    asset_id: str
    user_id: str
    interaction_type: str
    session_id: Optional[str] = None
    duration_seconds: Optional[int] = None
    asset_type: Optional[str] = None
    asset_size_bytes: Optional[int] = None
    project_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class SearchQueryCreate(BaseModel):
    """Search query creation model."""
    query_text: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    query_type: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None
    sort_order: Optional[str] = None
    results_count: Optional[int] = None
    response_time_ms: Optional[int] = None
    clicked_results: Optional[List[str]] = None
    search_context: Optional[str] = None
    project_id: Optional[str] = None


class UsageMetricsResponse(BaseModel):
    """Usage metrics response model."""
    metric_name: str
    timestamp: datetime
    granularity: str
    value: float
    count: Optional[int] = None
    dimensions: Optional[Dict[str, Any]] = None


class UserBehaviorResponse(BaseModel):
    """User behavior response model."""
    user_id: str
    period_start: datetime
    period_end: datetime
    period_type: str
    sessions_count: int
    total_time_minutes: int
    page_views: int
    actions_count: int
    assets_viewed: int
    assets_uploaded: int
    assets_downloaded: int
    searches_performed: int
    user_segment: Optional[str] = None
    activity_level: Optional[str] = None


class AnalyticsOverview(BaseModel):
    """Analytics dashboard overview."""
    total_users: int
    active_users_24h: int
    total_sessions: int
    avg_session_duration: float
    total_page_views: int
    total_assets_uploaded: int
    total_assets_downloaded: int
    total_searches: int
    top_features: List[Dict[str, Any]]
    user_segments: Dict[str, int]
    growth_metrics: Dict[str, float]