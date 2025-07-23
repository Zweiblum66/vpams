"""
API routes for the Monitoring Service
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
import httpx
import asyncio

from ..core.config import settings
from ..core.metrics import (
    MetricsCollector, users_total, projects_total, assets_total,
    asset_storage_bytes, processing_queue_size, workflow_active_instances,
    db_connections_active, cache_size_bytes, active_sessions
)
from ..db.base import get_db
from ..models.schemas import (
    ServiceHealth, SystemStatus, MetricsSummary,
    ServiceMetrics, AlertRule, AlertStatus
)

router = APIRouter(prefix="/monitoring", tags=["monitoring"])

# Initialize metrics collector for this module
metrics_collector = MetricsCollector(
    service_name="monitoring-api",
    version=settings.VERSION,
    environment=settings.ENVIRONMENT
)


@router.get("/status", response_model=SystemStatus)
async def get_system_status():
    """
    Get overall system status
    
    Returns the health status of all services and system components.
    """
    services = []
    
    # Check all services
    service_urls = {
        "api-gateway": f"{settings.API_GATEWAY_URL}/health",
        "user-management": f"{settings.USER_SERVICE_URL}/health",
        "asset-management": f"{settings.ASSET_SERVICE_URL}/health",
        "storage-abstraction": f"{settings.STORAGE_SERVICE_URL}/health",
        "metadata-service": f"{settings.METADATA_SERVICE_URL}/health",
        "search-engine": f"{settings.SEARCH_SERVICE_URL}/health",
        "ingest-service": f"{settings.INGEST_SERVICE_URL}/health",
        "proxy-generation": f"{settings.PROXY_SERVICE_URL}/health",
        "workflow-engine": f"{settings.WORKFLOW_SERVICE_URL}/health",
        "ai-ml-service": f"{settings.AI_SERVICE_URL}/health",
        "rights-management": f"{settings.RIGHTS_SERVICE_URL}/health",
        "integration-service": f"{settings.INTEGRATION_SERVICE_URL}/health",
    }
    
    async with httpx.AsyncClient(timeout=5.0) as client:
        tasks = []
        for service_name, url in service_urls.items():
            tasks.append(check_service_health(client, service_name, url))
        
        services = await asyncio.gather(*tasks)
    
    # Calculate overall status
    healthy_count = sum(1 for s in services if s["status"] == "healthy")
    total_count = len(services)
    
    if healthy_count == total_count:
        overall_status = "healthy"
    elif healthy_count >= total_count * 0.8:
        overall_status = "degraded"
    else:
        overall_status = "unhealthy"
    
    return SystemStatus(
        status=overall_status,
        timestamp=datetime.utcnow(),
        services=services,
        healthy_services=healthy_count,
        total_services=total_count
    )


async def check_service_health(client: httpx.AsyncClient, service_name: str, url: str) -> Dict[str, Any]:
    """Check health of a single service"""
    try:
        response = await client.get(url)
        if response.status_code == 200:
            data = response.json()
            return {
                "name": service_name,
                "status": "healthy",
                "version": data.get("version", "unknown"),
                "response_time_ms": response.elapsed.total_seconds() * 1000
            }
        else:
            return {
                "name": service_name,
                "status": "unhealthy",
                "error": f"HTTP {response.status_code}"
            }
    except Exception as e:
        return {
            "name": service_name,
            "status": "unhealthy",
            "error": str(e)
        }


@router.get("/metrics/summary", response_model=MetricsSummary)
async def get_metrics_summary(
    period: str = Query("1h", description="Time period (1h, 24h, 7d, 30d)"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get summary of key metrics
    
    Returns aggregated metrics for the specified time period.
    """
    # Parse period
    period_map = {
        "1h": timedelta(hours=1),
        "24h": timedelta(days=1),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30)
    }
    
    if period not in period_map:
        raise HTTPException(status_code=400, detail="Invalid period")
    
    # For now, return current metric values
    # In production, these would be fetched from TimescaleDB
    return MetricsSummary(
        period=period,
        timestamp=datetime.utcnow(),
        total_users=100,  # Placeholder
        active_users=25,  # Placeholder
        total_assets=5000,  # Placeholder
        storage_used_gb=2500,  # Placeholder
        api_requests_count=15000,  # Placeholder
        avg_response_time_ms=125,  # Placeholder
        error_rate=0.02,  # Placeholder
        active_workflows=15,  # Placeholder
        processing_queue_size=45  # Placeholder
    )


@router.get("/services/{service_name}/metrics", response_model=ServiceMetrics)
async def get_service_metrics(
    service_name: str,
    period: str = Query("1h", description="Time period (1h, 24h, 7d, 30d)")
):
    """
    Get detailed metrics for a specific service
    
    Returns detailed performance and usage metrics for the specified service.
    """
    # Validate service name
    valid_services = [
        "api-gateway", "user-management", "asset-management",
        "storage-abstraction", "metadata-service", "search-engine",
        "ingest-service", "proxy-generation", "workflow-engine",
        "ai-ml-service", "rights-management", "integration-service"
    ]
    
    if service_name not in valid_services:
        raise HTTPException(status_code=404, detail="Service not found")
    
    # For now, return mock data
    # In production, fetch from TimescaleDB
    return ServiceMetrics(
        service_name=service_name,
        period=period,
        timestamp=datetime.utcnow(),
        cpu_usage_percent=45.2,
        memory_usage_mb=512,
        request_count=1500,
        error_count=15,
        avg_response_time_ms=85,
        p95_response_time_ms=150,
        p99_response_time_ms=250,
        active_connections=25,
        health_score=0.98
    )


@router.get("/alerts", response_model=List[AlertStatus])
async def get_active_alerts(
    severity: Optional[str] = Query(None, description="Filter by severity (critical, warning, info)"),
    service: Optional[str] = Query(None, description="Filter by service name"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get active alerts
    
    Returns all currently active alerts, optionally filtered by severity or service.
    """
    # For now, return empty list
    # In production, fetch from database
    alerts = []
    
    # Example alert structure
    if settings.DEBUG:
        alerts = [
            AlertStatus(
                id="alert-001",
                rule_name="High Error Rate",
                severity="warning",
                service="api-gateway",
                message="Error rate exceeded 5% threshold",
                triggered_at=datetime.utcnow() - timedelta(minutes=5),
                value=5.2,
                threshold=5.0,
                status="active"
            )
        ]
    
    # Apply filters
    if severity:
        alerts = [a for a in alerts if a.severity == severity]
    if service:
        alerts = [a for a in alerts if a.service == service]
    
    return alerts


@router.post("/alerts/rules", response_model=AlertRule)
async def create_alert_rule(
    rule: AlertRule,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new alert rule
    
    Defines a new rule for triggering alerts based on metric thresholds.
    """
    # TODO: Implement alert rule creation
    # Store in database and configure in alerting system
    
    return rule


@router.get("/alerts/rules", response_model=List[AlertRule])
async def get_alert_rules(
    service: Optional[str] = Query(None, description="Filter by service name"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get configured alert rules
    
    Returns all configured alert rules, optionally filtered by service.
    """
    # TODO: Implement fetching alert rules from database
    rules = []
    
    # Example rules
    if settings.DEBUG:
        rules = [
            AlertRule(
                id="rule-001",
                name="High Error Rate",
                description="Alert when error rate exceeds threshold",
                metric="error_rate",
                condition="greater_than",
                threshold=5.0,
                duration_seconds=300,
                severity="warning",
                service="all",
                enabled=True
            ),
            AlertRule(
                id="rule-002",
                name="Service Down",
                description="Alert when service health check fails",
                metric="health_status",
                condition="equals",
                threshold=0,
                duration_seconds=60,
                severity="critical",
                service="all",
                enabled=True
            )
        ]
    
    if service:
        rules = [r for r in rules if r.service == "all" or r.service == service]
    
    return rules


@router.post("/collect/system-metrics")
async def collect_system_metrics(
    metrics: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """
    Collect system-wide metrics
    
    This endpoint is called by other services to report their metrics.
    """
    try:
        # Update Prometheus metrics based on received data
        if "total_users" in metrics:
            users_total.labels(status="active", type="regular").set(metrics["total_users"])
        
        if "total_projects" in metrics:
            projects_total.labels(status="active").set(metrics["total_projects"])
        
        if "total_assets" in metrics:
            for asset_type, count in metrics["total_assets"].items():
                assets_total.labels(type=asset_type, status="active").set(count)
        
        if "storage_usage" in metrics:
            for tier, usage in metrics["storage_usage"].items():
                asset_storage_bytes.labels(
                    storage_tier=tier,
                    storage_type="s3"
                ).set(usage)
        
        if "queue_sizes" in metrics:
            for queue_name, size in metrics["queue_sizes"].items():
                processing_queue_size.labels(
                    queue_name=queue_name,
                    priority="normal"
                ).set(size)
        
        if "active_workflows" in metrics:
            for workflow_type, count in metrics["active_workflows"].items():
                workflow_active_instances.labels(
                    workflow_type=workflow_type
                ).set(count)
        
        # TODO: Store metrics in TimescaleDB for historical analysis
        
        return {"status": "success", "metrics_collected": len(metrics)}
    
    except Exception as e:
        metrics_collector.track_error("metrics_collection_error", "error")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboards")
async def get_dashboard_links():
    """
    Get links to monitoring dashboards
    
    Returns URLs for Grafana dashboards and other monitoring tools.
    """
    return {
        "grafana": {
            "system_overview": f"http://localhost:3001/d/system-overview",
            "service_metrics": f"http://localhost:3001/d/service-metrics",
            "business_metrics": f"http://localhost:3001/d/business-metrics",
            "alerts": f"http://localhost:3001/d/alerts"
        },
        "prometheus": {
            "targets": f"http://localhost:9090/targets",
            "graph": f"http://localhost:9090/graph",
            "alerts": f"http://localhost:9090/alerts"
        }
    }