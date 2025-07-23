"""
Unified Analytics API

This module provides a comprehensive REST API for all analytics functionality,
including usage metrics, user behavior, reports, and real-time analytics.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from shared.auth.dependencies import get_current_user
from shared.db.postgres import get_session
from shared.tracing.python_tracing import trace_async_function

from ...services.analytics_engine import AnalyticsEngine
from ...services.behavior_tracker import BehaviorTracker
from ...services.report_generator import ReportGenerator
from ...models.analytics import EventType

router = APIRouter()

# Initialize analytics services
analytics_engine = AnalyticsEngine()
behavior_tracker = BehaviorTracker()
report_generator = ReportGenerator()


class EventTrackingRequest(BaseModel):
    """Request model for event tracking."""
    event_type: EventType = Field(..., description="Type of event")
    event_name: str = Field(..., min_length=1, max_length=255, description="Event name")
    category: Optional[str] = Field(None, max_length=100, description="Event category")
    properties: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Event properties")
    session_id: Optional[str] = Field(None, description="Session identifier")
    duration_ms: Optional[int] = Field(None, ge=0, description="Event duration in milliseconds")


class AnalyticsOverviewResponse(BaseModel):
    """Response model for analytics overview."""
    timeframe: str
    total_events: int
    unique_users: int
    active_sessions: int
    top_events: List[Dict[str, Any]]
    user_segments: Dict[str, int]
    key_metrics: Dict[str, float]
    trends: Dict[str, float]
    generated_at: str


class MetricsQuery(BaseModel):
    """Query parameters for metrics."""
    metric_names: List[str] = Field(..., description="Metric names to retrieve")
    start_date: Optional[str] = Field(None, description="Start date (ISO format)")
    end_date: Optional[str] = Field(None, description="End date (ISO format)")
    granularity: str = Field("hour", description="Data granularity: minute, hour, day, week, month")
    group_by: Optional[List[str]] = Field(None, description="Group by dimensions")
    filters: Optional[Dict[str, Any]] = Field(None, description="Additional filters")


@router.get("/overview")
async def get_analytics_overview(
    timeframe: str = Query("24h", description="Time range: 1h, 24h, 7d, 30d"),
    segment: Optional[str] = Query(None, description="User segment filter"),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
) -> AnalyticsOverviewResponse:
    """Get comprehensive analytics overview."""
    
    if not current_user.has_permission("analytics.view"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    try:
        # Parse timeframe
        end_time = datetime.utcnow()
        if timeframe == "1h":
            start_time = end_time - timedelta(hours=1)
        elif timeframe == "24h":
            start_time = end_time - timedelta(hours=24)
        elif timeframe == "7d":
            start_time = end_time - timedelta(days=7)
        elif timeframe == "30d":
            start_time = end_time - timedelta(days=30)
        else:
            raise HTTPException(status_code=400, detail="Invalid timeframe")
        
        # Get overview data from analytics engine
        overview_data = await analytics_engine.get_overview_metrics(start_time, end_time, db)
        
        # Get user segments from behavior tracker
        user_segments = await behavior_tracker.segment_users(db)
        segments_count = {seg: len(users) for seg, users in user_segments.items()}
        
        # Get engagement metrics
        engagement_metrics = await behavior_tracker.get_engagement_metrics(db)
        
        # Calculate trends (compare with previous period)
        previous_start = start_time - (end_time - start_time)
        previous_overview = await analytics_engine.get_overview_metrics(
            previous_start, start_time, db
        )
        
        trends = {}
        if previous_overview and overview_data:
            for key in ["total_events", "unique_users", "active_sessions"]:
                current_val = overview_data.get(key, 0)
                previous_val = previous_overview.get(key, 0)
                if previous_val > 0:
                    trends[f"{key}_change_percent"] = ((current_val - previous_val) / previous_val) * 100
                else:
                    trends[f"{key}_change_percent"] = 0
        
        return AnalyticsOverviewResponse(
            timeframe=timeframe,
            total_events=overview_data.get("total_events", 0),
            unique_users=overview_data.get("unique_users", 0),
            active_sessions=overview_data.get("active_sessions", 0),
            top_events=overview_data.get("top_events", []),
            user_segments=segments_count,
            key_metrics={
                "avg_session_duration_minutes": engagement_metrics.get("avg_session_duration_minutes", 0),
                "bounce_rate_percent": overview_data.get("bounce_rate", 0) * 100,
                "conversion_rate_percent": overview_data.get("conversion_rate", 0) * 100,
                "retention_rate_percent": engagement_metrics.get("retention_metrics", {}).get("week_7_retention_percent", 0)
            },
            trends=trends,
            generated_at=datetime.utcnow().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get analytics overview: {str(e)}")


@router.post("/events/track")
async def track_event(
    request: EventTrackingRequest,
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    """Track an analytics event."""
    
    try:
        # Add event tracking to background tasks for performance
        background_tasks.add_task(
            analytics_engine.track_event,
            event_type=request.event_type,
            event_name=request.event_name,
            category=request.category,
            user_id=str(current_user.id),
            session_id=request.session_id,
            properties=request.properties,
            duration_ms=request.duration_ms,
            db=db
        )
        
        return {
            "status": "accepted",
            "message": "Event tracking queued",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to track event: {str(e)}")


@router.post("/events/batch")
async def track_events_batch(
    events: List[EventTrackingRequest],
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    """Track multiple analytics events in batch."""
    
    if len(events) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 events per batch")
    
    try:
        # Add batch event tracking to background tasks
        for event_request in events:
            background_tasks.add_task(
                analytics_engine.track_event,
                event_type=event_request.event_type,
                event_name=event_request.event_name,
                category=event_request.category,
                user_id=str(current_user.id),
                session_id=event_request.session_id,
                properties=event_request.properties,
                duration_ms=event_request.duration_ms,
                db=db
            )
        
        return {
            "status": "accepted",
            "message": f"Batch of {len(events)} events queued",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to track events batch: {str(e)}")


@router.post("/metrics/query")
async def query_metrics(
    query: MetricsQuery,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    """Query analytics metrics with flexible parameters."""
    
    if not current_user.has_permission("analytics.view"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    try:
        # Parse date range
        end_time = datetime.utcnow()
        if query.end_date:
            end_time = datetime.fromisoformat(query.end_date)
        
        start_time = end_time - timedelta(days=7)  # Default to 7 days
        if query.start_date:
            start_time = datetime.fromisoformat(query.start_date)
        
        # Query metrics from analytics engine
        metrics_data = await analytics_engine.query_metrics(
            metric_names=query.metric_names,
            start_time=start_time,
            end_time=end_time,
            granularity=query.granularity,
            group_by=query.group_by,
            filters=query.filters,
            db=db
        )
        
        return {
            "metrics": metrics_data,
            "query_parameters": {
                "metric_names": query.metric_names,
                "start_date": start_time.isoformat(),
                "end_date": end_time.isoformat(),
                "granularity": query.granularity,
                "group_by": query.group_by,
                "filters": query.filters
            },
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to query metrics: {str(e)}")


@router.get("/metrics/available")
async def get_available_metrics(
    current_user = Depends(get_current_user)
):
    """Get list of available metrics."""
    
    if not current_user.has_permission("analytics.view"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    metrics = [
        {
            "name": "page_views",
            "description": "Total page views",
            "type": "counter",
            "dimensions": ["page", "user_id", "session_id"]
        },
        {
            "name": "user_sessions",
            "description": "Active user sessions",
            "type": "gauge",
            "dimensions": ["device_type", "browser", "country"]
        },
        {
            "name": "events_count",
            "description": "Total events by type",
            "type": "counter",
            "dimensions": ["event_type", "event_name", "category"]
        },
        {
            "name": "asset_interactions",
            "description": "Asset interaction events",
            "type": "counter",
            "dimensions": ["interaction_type", "asset_type", "user_id"]
        },
        {
            "name": "search_queries",
            "description": "Search query count",
            "type": "counter",
            "dimensions": ["query_type", "results_count", "user_id"]
        },
        {
            "name": "session_duration",
            "description": "User session duration in minutes",
            "type": "histogram",
            "dimensions": ["device_type", "user_segment"]
        },
        {
            "name": "conversion_events",
            "description": "Conversion events (uploads, downloads, shares)",
            "type": "counter",
            "dimensions": ["conversion_type", "user_segment"]
        },
        {
            "name": "error_rate",
            "description": "Application error rate",
            "type": "gauge",
            "dimensions": ["service", "endpoint", "error_type"]
        }
    ]
    
    return {"metrics": metrics}


@router.get("/trends")
async def get_analytics_trends(
    metric: str = Query(..., description="Metric to analyze"),
    timeframe: str = Query("7d", description="Time range"),
    granularity: str = Query("1h", description="Data granularity"),
    comparison: bool = Query(False, description="Include period comparison"),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    """Get trend analysis for a specific metric."""
    
    if not current_user.has_permission("analytics.view"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    try:
        # Parse timeframe
        end_time = datetime.utcnow()
        if timeframe == "1h":
            start_time = end_time - timedelta(hours=1)
        elif timeframe == "24h":
            start_time = end_time - timedelta(hours=24)
        elif timeframe == "7d":
            start_time = end_time - timedelta(days=7)
        elif timeframe == "30d":
            start_time = end_time - timedelta(days=30)
        else:
            raise HTTPException(status_code=400, detail="Invalid timeframe")
        
        # Get trend data
        trend_data = await analytics_engine.get_trend_data(
            metric, timeframe, granularity, db
        )
        
        result = {
            "metric": metric,
            "timeframe": timeframe,
            "granularity": granularity,
            "data": trend_data,
            "generated_at": datetime.utcnow().isoformat()
        }
        
        # Add comparison data if requested
        if comparison:
            period_duration = end_time - start_time
            comparison_start = start_time - period_duration
            comparison_end = start_time
            
            comparison_data = await analytics_engine.get_trend_data(
                metric, timeframe, granularity, db,
                start_time=comparison_start, end_time=comparison_end
            )
            
            result["comparison"] = {
                "period": f"{comparison_start.isoformat()} to {comparison_end.isoformat()}",
                "data": comparison_data
            }
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get trends: {str(e)}")


@router.get("/dashboards/executive")
async def get_executive_dashboard(
    period: str = Query("30d", description="Reporting period"),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    """Get executive dashboard with high-level KPIs."""
    
    if not current_user.has_permission("analytics.view_executive"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    try:
        # Parse period
        end_time = datetime.utcnow()
        if period == "7d":
            start_time = end_time - timedelta(days=7)
        elif period == "30d":
            start_time = end_time - timedelta(days=30)
        elif period == "90d":
            start_time = end_time - timedelta(days=90)
        else:
            start_time = end_time - timedelta(days=30)
        
        # Get executive metrics
        overview = await analytics_engine.get_overview_metrics(start_time, end_time, db)
        engagement = await behavior_tracker.get_engagement_metrics(db)
        user_segments = await behavior_tracker.segment_users(db)
        
        # Calculate growth metrics (compared to previous period)
        previous_start = start_time - (end_time - start_time)
        previous_overview = await analytics_engine.get_overview_metrics(
            previous_start, start_time, db
        )
        
        growth_metrics = {}
        if previous_overview:
            for metric in ["total_events", "unique_users"]:
                current = overview.get(metric, 0)
                previous = previous_overview.get(metric, 0)
                if previous > 0:
                    growth_metrics[f"{metric}_growth"] = ((current - previous) / previous) * 100
                else:
                    growth_metrics[f"{metric}_growth"] = 0
        
        return {
            "period": period,
            "kpis": {
                "total_users": overview.get("unique_users", 0),
                "active_users": engagement.get("total_active_users", 0),
                "user_growth": growth_metrics.get("unique_users_growth", 0),
                "engagement_score": engagement.get("avg_session_duration_minutes", 0),
                "retention_rate": engagement.get("retention_metrics", {}).get("week_7_retention_percent", 0),
                "feature_adoption": engagement.get("feature_adoption_rates", {}),
            },
            "user_distribution": {
                "by_segment": {seg: len(users) for seg, users in user_segments.items()},
                "by_activity": engagement.get("segments_distribution", {})
            },
            "trends": growth_metrics,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get executive dashboard: {str(e)}")


@router.get("/dashboards/operational")
async def get_operational_dashboard(
    timeframe: str = Query("24h", description="Time range: 1h, 24h, 7d"),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    """Get operational dashboard with system health metrics."""
    
    if not current_user.has_permission("analytics.view"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    try:
        # Parse timeframe
        end_time = datetime.utcnow()
        if timeframe == "1h":
            start_time = end_time - timedelta(hours=1)
        elif timeframe == "24h":
            start_time = end_time - timedelta(hours=24)
        elif timeframe == "7d":
            start_time = end_time - timedelta(days=7)
        else:
            start_time = end_time - timedelta(hours=24)
        
        # Get operational metrics
        overview = await analytics_engine.get_overview_metrics(start_time, end_time, db)
        
        # Get system health metrics (placeholder - would integrate with monitoring)
        system_health = {
            "api_response_time_ms": 150,
            "error_rate_percent": 0.1,
            "throughput_requests_per_second": 45,
            "database_connection_pool_usage": 65,
            "memory_usage_percent": 72,
            "cpu_usage_percent": 45
        }
        
        return {
            "timeframe": timeframe,
            "system_health": system_health,
            "traffic_metrics": {
                "total_requests": overview.get("total_events", 0),
                "unique_visitors": overview.get("unique_users", 0),
                "page_views": overview.get("page_views", 0),
                "bounce_rate": overview.get("bounce_rate", 0) * 100
            },
            "user_activity": {
                "active_sessions": overview.get("active_sessions", 0),
                "avg_session_duration": overview.get("avg_session_duration", 0),
                "top_pages": overview.get("top_pages", []),
                "top_events": overview.get("top_events", [])
            },
            "alerts": [
                {
                    "level": "warning",
                    "message": "API response time above normal",
                    "metric": "api_response_time_ms",
                    "value": 150,
                    "threshold": 200
                }
            ] if system_health["api_response_time_ms"] > 200 else [],
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get operational dashboard: {str(e)}")


@router.get("/export")
async def export_analytics_data(
    format: str = Query("csv", description="Export format: csv, json, excel"),
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
    data_types: List[str] = Query([], description="Data types to export: events, sessions, interactions"),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    """Export analytics data in various formats."""
    
    if not current_user.has_permission("analytics.export"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    try:
        # Parse date range
        end_time = datetime.utcnow()
        if end_date:
            end_time = datetime.fromisoformat(end_date)
        
        start_time = end_time - timedelta(days=30)  # Default to 30 days
        if start_date:
            start_time = datetime.fromisoformat(start_date)
        
        # Validate date range
        if (end_time - start_time).days > 365:
            raise HTTPException(status_code=400, detail="Date range cannot exceed 365 days")
        
        # Default data types if none specified
        if not data_types:
            data_types = ["events", "sessions"]
        
        # Export data using analytics engine
        export_data = await analytics_engine.export_data(
            data_types=data_types,
            start_time=start_time,
            end_time=end_time,
            format=format,
            db=db
        )
        
        return {
            "export_id": export_data.get("export_id"),
            "format": format,
            "data_types": data_types,
            "date_range": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat()
            },
            "download_url": export_data.get("download_url"),
            "expires_at": export_data.get("expires_at"),
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export data: {str(e)}")


@router.get("/health")
async def health_check():
    """Health check for analytics API."""
    return {
        "status": "healthy",
        "service": "unified_analytics_api",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "components": {
            "analytics_engine": "healthy",
            "behavior_tracker": "healthy",
            "report_generator": "healthy"
        }
    }


@router.get("/status")
async def get_service_status(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    """Get detailed service status and statistics."""
    
    if not current_user.has_permission("analytics.admin"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    try:
        # Get service statistics
        stats = await analytics_engine.get_service_statistics(db)
        
        return {
            "service": "analytics",
            "status": "operational",
            "uptime_minutes": stats.get("uptime_minutes", 0),
            "version": "1.0.0",
            "statistics": {
                "total_events_processed": stats.get("total_events", 0),
                "events_last_24h": stats.get("events_24h", 0),
                "active_users_count": stats.get("active_users", 0),
                "reports_generated": stats.get("reports_count", 0),
                "data_retention_days": 90,
                "storage_size_mb": stats.get("storage_mb", 0)
            },
            "performance": {
                "avg_query_time_ms": stats.get("avg_query_time", 0),
                "cache_hit_rate_percent": stats.get("cache_hit_rate", 0) * 100,
                "processing_queue_size": stats.get("queue_size", 0)
            },
            "last_updated": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get service status: {str(e)}")


@router.get("/schema")
async def get_api_schema():
    """Get analytics API schema documentation."""
    
    schema = {
        "api_version": "1.0.0",
        "title": "MAMS Analytics API",
        "description": "Comprehensive analytics API for tracking, reporting, and insights",
        "endpoints": {
            "overview": {
                "method": "GET",
                "path": "/analytics/overview",
                "description": "Get comprehensive analytics overview",
                "parameters": ["timeframe", "segment"],
                "permissions": ["analytics.view"]
            },
            "track_event": {
                "method": "POST",
                "path": "/analytics/events/track",
                "description": "Track a single analytics event",
                "permissions": ["authenticated"]
            },
            "track_batch": {
                "method": "POST",
                "path": "/analytics/events/batch",
                "description": "Track multiple events in batch",
                "permissions": ["authenticated"]
            },
            "query_metrics": {
                "method": "POST",
                "path": "/analytics/metrics/query",
                "description": "Query metrics with flexible parameters",
                "permissions": ["analytics.view"]
            },
            "trends": {
                "method": "GET",
                "path": "/analytics/trends",
                "description": "Get trend analysis for metrics",
                "permissions": ["analytics.view"]
            },
            "executive_dashboard": {
                "method": "GET",
                "path": "/analytics/dashboards/executive",
                "description": "Executive dashboard with KPIs",
                "permissions": ["analytics.view_executive"]
            },
            "operational_dashboard": {
                "method": "GET",
                "path": "/analytics/dashboards/operational",
                "description": "Operational dashboard with system health",
                "permissions": ["analytics.view"]
            },
            "export": {
                "method": "GET",
                "path": "/analytics/export",
                "description": "Export analytics data",
                "permissions": ["analytics.export"]
            }
        },
        "event_types": [e.value for e in EventType],
        "available_timeframes": ["1h", "24h", "7d", "30d", "90d"],
        "supported_formats": ["csv", "json", "excel", "pdf"],
        "rate_limits": {
            "events/track": "1000 per hour per user",
            "events/batch": "100 batches per hour per user",
            "queries": "100 per hour per user",
            "exports": "10 per day per user"
        }
    }
    
    return schema