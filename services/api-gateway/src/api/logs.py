"""
Log Management API

Endpoints for viewing and managing logs, metrics, and log aggregations.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field

from core.config import get_settings
from core.enhanced_logging import performance_logger, log_aggregator
from api.dependencies import get_current_user, require_permissions

settings = get_settings()
router = APIRouter(prefix="/api/v1/logs", tags=["logs"])


class LogQuery(BaseModel):
    """Log query parameters"""
    start_time: Optional[datetime] = Field(None, description="Start time for log search")
    end_time: Optional[datetime] = Field(None, description="End time for log search")
    level: Optional[str] = Field(None, description="Log level filter")
    request_id: Optional[str] = Field(None, description="Filter by request ID")
    user_id: Optional[str] = Field(None, description="Filter by user ID")
    service: Optional[str] = Field(None, description="Filter by service name")
    limit: int = Field(100, le=1000, description="Maximum number of logs to return")


class MetricSummary(BaseModel):
    """Performance metric summary"""
    metric_name: str
    count: int
    min: float
    max: float
    avg: float
    p50: float
    p90: float
    p95: float
    p99: float


class AggregationSummary(BaseModel):
    """Log aggregation summary"""
    request_counts: Dict[str, int]
    error_counts: Dict[str, int]
    response_time_stats: Dict[str, Dict[str, float]]


@router.get("/search")
async def search_logs(
    query: LogQuery = Depends(),
    current_user: Dict = Depends(require_permissions("admin", "logs.read"))
):
    """
    Search logs based on query parameters
    
    This endpoint would typically query an external log storage system
    like Elasticsearch, CloudWatch, or similar.
    """
    # This is a placeholder implementation
    # In production, this would query your log storage backend
    
    return {
        "message": "Log search would be implemented based on your log storage backend",
        "query": query.dict(exclude_none=True),
        "note": "Integrate with Elasticsearch, CloudWatch, Datadog, etc."
    }


@router.get("/metrics", response_model=Dict[str, MetricSummary])
async def get_performance_metrics(
    metrics: List[str] = Query(default=["request_duration"]),
    current_user: Dict = Depends(get_current_user)
):
    """
    Get performance metrics summary
    
    Returns statistics for specified metrics.
    """
    results = {}
    
    for metric_name in metrics:
        stats = await performance_logger.get_stats(metric_name)
        if stats:
            results[metric_name] = MetricSummary(
                metric_name=metric_name,
                **stats
            )
    
    return results


@router.get("/aggregations", response_model=AggregationSummary)
async def get_log_aggregations(
    current_user: Dict = Depends(get_current_user)
):
    """
    Get aggregated log statistics
    
    Returns request counts, error counts, and response time statistics.
    """
    summary = await log_aggregator.get_summary()
    
    return AggregationSummary(**summary)


@router.post("/aggregations/reset")
async def reset_aggregations(
    current_user: Dict = Depends(require_permissions("admin", "logs.write"))
):
    """
    Reset log aggregations
    
    Clears all aggregated statistics. Requires admin permissions.
    """
    await log_aggregator.reset()
    
    return {
        "message": "Log aggregations reset successfully",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/tail")
async def tail_logs(
    lines: int = Query(default=100, le=1000),
    follow: bool = Query(default=False),
    current_user: Dict = Depends(require_permissions("admin", "logs.read"))
):
    """
    Tail recent logs
    
    Returns the most recent log entries. If follow=true, would establish
    a WebSocket connection for real-time log streaming.
    """
    if follow:
        return {
            "message": "Real-time log streaming would be implemented via WebSocket",
            "endpoint": "/ws/logs",
            "note": "Connect to WebSocket endpoint for real-time logs"
        }
    
    # This would read from your log files or log storage
    return {
        "message": f"Would return last {lines} log entries",
        "note": "Implement based on your log storage backend"
    }


@router.get("/errors")
async def get_recent_errors(
    hours: int = Query(default=24, le=168),  # Max 1 week
    current_user: Dict = Depends(require_permissions("admin", "logs.read"))
):
    """
    Get recent errors
    
    Returns errors from the specified time period.
    """
    since = datetime.utcnow() - timedelta(hours=hours)
    
    # This would query your log storage for errors
    return {
        "message": f"Would return errors from the last {hours} hours",
        "since": since.isoformat(),
        "note": "Implement based on your log storage backend"
    }


@router.get("/audit")
async def get_audit_logs(
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    user_id: Optional[str] = None,
    event_type: Optional[str] = None,
    limit: int = Query(default=100, le=1000),
    current_user: Dict = Depends(require_permissions("admin", "audit.read"))
):
    """
    Get audit logs
    
    Returns security and compliance audit events.
    """
    query_params = {
        "start_time": start_time.isoformat() if start_time else None,
        "end_time": end_time.isoformat() if end_time else None,
        "user_id": user_id,
        "event_type": event_type,
        "limit": limit
    }
    
    # This would query your audit log storage
    return {
        "message": "Would return audit logs based on query",
        "query": {k: v for k, v in query_params.items() if v is not None},
        "note": "Implement based on your audit log storage backend"
    }


@router.get("/export")
async def export_logs(
    format: str = Query(default="json", enum=["json", "csv", "txt"]),
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    current_user: Dict = Depends(require_permissions("admin", "logs.export"))
):
    """
    Export logs
    
    Exports logs in the specified format for the given time range.
    """
    # This would generate an export file
    return {
        "message": f"Would export logs in {format} format",
        "start_time": start_time.isoformat() if start_time else None,
        "end_time": end_time.isoformat() if end_time else None,
        "note": "Implement log export functionality"
    }


@router.get("/config")
async def get_logging_config(
    current_user: Dict = Depends(require_permissions("admin", "logs.read"))
):
    """
    Get current logging configuration
    
    Returns the current logging levels and configuration.
    """
    import logging
    
    # Get current logging configuration
    loggers = {}
    for name in logging.Logger.manager.loggerDict:
        logger = logging.getLogger(name)
        if logger.level != logging.NOTSET:
            loggers[name] = {
                "level": logging.getLevelName(logger.level),
                "handlers": [h.__class__.__name__ for h in logger.handlers]
            }
    
    return {
        "root_level": logging.getLevelName(logging.getLogger().level),
        "loggers": loggers,
        "log_format": settings.log_format,
        "environment": settings.environment
    }


@router.put("/config/level")
async def update_log_level(
    logger_name: str = Query(default="", description="Logger name (empty for root)"),
    level: str = Query(..., enum=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]),
    current_user: Dict = Depends(require_permissions("admin", "logs.write"))
):
    """
    Update log level for a logger
    
    Dynamically changes the log level for the specified logger.
    """
    import logging
    
    # Get logger
    logger = logging.getLogger(logger_name) if logger_name else logging.getLogger()
    
    # Set new level
    numeric_level = getattr(logging, level)
    logger.setLevel(numeric_level)
    
    return {
        "message": f"Log level updated for {'root' if not logger_name else logger_name} logger",
        "logger": logger_name or "root",
        "new_level": level,
        "numeric_level": numeric_level
    }