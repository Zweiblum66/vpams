"""
API routes for failover service
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query, status
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from ..services.failover_manager import FailoverManager
from ..models.schemas import (
    FailoverStatus,
    FailoverRequest,
    FailoverEvent,
    RegionHealth,
    FailoverPlan,
    DataConsistencyCheck,
    RecoveryPointStatus,
    RegionConfiguration,
    LoadBalancerConfig,
    HealthCheckConfig,
    SystemTopology,
    FailoverMetrics
)
from ..core.deps import get_current_user, get_failover_manager
from ..core.security import require_permission
from ..models.database import User

router = APIRouter(prefix="/api/v1/failover", tags=["failover"])


@router.get("/status", response_model=FailoverStatus)
async def get_failover_status(
    failover_manager: FailoverManager = Depends(get_failover_manager),
    current_user: User = Depends(get_current_user)
):
    """Get current failover status"""
    await require_permission(current_user, "failover.read")
    
    status = await failover_manager.get_failover_status()
    return status


@router.get("/regions", response_model=List[RegionHealth])
async def get_region_health(
    region: Optional[str] = Query(None, description="Filter by specific region"),
    failover_manager: FailoverManager = Depends(get_failover_manager),
    current_user: User = Depends(get_current_user)
):
    """Get health status of all regions"""
    await require_permission(current_user, "failover.read")
    
    if region:
        health = failover_manager.region_health.get(region)
        if not health:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Region {region} not found"
            )
        return [health]
    
    return list(failover_manager.region_health.values())


@router.post("/failover", response_model=FailoverEvent)
async def trigger_manual_failover(
    request: FailoverRequest,
    background_tasks: BackgroundTasks,
    failover_manager: FailoverManager = Depends(get_failover_manager),
    current_user: User = Depends(get_current_user)
):
    """Trigger manual failover to specified region"""
    await require_permission(current_user, "failover.execute")
    
    try:
        # Validate target region
        if request.target_region not in failover_manager.regions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid target region: {request.target_region}"
            )
        
        # Check if target region is healthy
        if not request.skip_health_check:
            target_health = failover_manager.region_health.get(request.target_region)
            if not target_health or not target_health.is_healthy:
                if not request.force:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Target region {request.target_region} is not healthy. Use force=true to override."
                    )
        
        # Execute failover in background
        event = FailoverEvent(
            event_type="manual",
            state="failing_over",
            from_region=failover_manager.current_active_region,
            to_region=request.target_region,
            reason=request.reason,
            triggered_by=current_user.username
        )
        
        background_tasks.add_task(
            failover_manager.execute_failover,
            event
        )
        
        return event
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger failover: {str(e)}"
        )


@router.post("/failback")
async def trigger_failback(
    background_tasks: BackgroundTasks,
    failover_manager: FailoverManager = Depends(get_failover_manager),
    current_user: User = Depends(get_current_user)
):
    """Trigger failback to primary region"""
    await require_permission(current_user, "failover.execute")
    
    if failover_manager.current_active_region == failover_manager.primary_region:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already running in primary region"
        )
    
    # Check if primary region is healthy
    primary_health = failover_manager.region_health.get(failover_manager.primary_region)
    if not primary_health or not primary_health.is_healthy:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Primary region is not healthy"
        )
    
    # Create failback event
    event = FailoverEvent(
        event_type="manual",
        state="failing_back",
        from_region=failover_manager.current_active_region,
        to_region=failover_manager.primary_region,
        reason="Manual failback to primary region",
        triggered_by=current_user.username
    )
    
    background_tasks.add_task(
        failover_manager.execute_failover,
        event
    )
    
    return {"message": "Failback initiated", "event_id": event.event_id}


@router.get("/history", response_model=List[FailoverEvent])
async def get_failover_history(
    limit: int = Query(100, ge=1, le=1000),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    failover_manager: FailoverManager = Depends(get_failover_manager),
    current_user: User = Depends(get_current_user)
):
    """Get failover event history"""
    await require_permission(current_user, "failover.read")
    
    history = failover_manager.failover_history
    
    # Filter by date range
    if start_date:
        history = [e for e in history if e.started_at >= start_date]
    if end_date:
        history = [e for e in history if e.started_at <= end_date]
    
    # Sort by most recent first
    history.sort(key=lambda x: x.started_at, reverse=True)
    
    return history[:limit]


@router.get("/plans", response_model=List[FailoverPlan])
async def get_failover_plans(
    failover_manager: FailoverManager = Depends(get_failover_manager),
    current_user: User = Depends(get_current_user)
):
    """Get available failover plans"""
    await require_permission(current_user, "failover.read")
    
    plans = []
    
    # Generate plans for each healthy region
    for region, health in failover_manager.region_health.items():
        if region != failover_manager.current_active_region and health.is_healthy:
            plan = FailoverPlan(
                name=f"Failover to {region}",
                description=f"Standard failover plan from {failover_manager.current_active_region} to {region}",
                source_region=failover_manager.current_active_region,
                target_region=region,
                services=list(failover_manager.service_health.get(region, {}).keys()),
                estimated_downtime_minutes=15
            )
            plans.append(plan)
    
    return plans


@router.post("/test-failover")
async def test_failover(
    target_region: str,
    dry_run: bool = True,
    failover_manager: FailoverManager = Depends(get_failover_manager),
    current_user: User = Depends(get_current_user)
):
    """Test failover without actually executing it"""
    await require_permission(current_user, "failover.test")
    
    # Validate target region
    if target_region not in failover_manager.regions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid target region: {target_region}"
        )
    
    # Check health
    target_health = failover_manager.region_health.get(target_region)
    if not target_health:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No health data for region {target_region}"
        )
    
    # Check RPO
    rpo_status = await failover_manager.check_rpo_status(
        failover_manager.current_active_region,
        target_region
    )
    
    # Create test report
    test_report = {
        "target_region": target_region,
        "target_health": target_health.dict(),
        "rpo_status": rpo_status.dict(),
        "estimated_downtime_minutes": 15,
        "pre_checks_passed": target_health.is_healthy and rpo_status.is_within_rpo,
        "dry_run": dry_run,
        "recommendations": []
    }
    
    if not target_health.is_healthy:
        test_report["recommendations"].append(
            f"Target region {target_region} is not fully healthy. Address health issues before failover."
        )
    
    if not rpo_status.is_within_rpo:
        test_report["recommendations"].append(
            f"RPO exceeded. Current lag: {rpo_status.current_lag_minutes} minutes. Consider waiting for replication to catch up."
        )
    
    return test_report


@router.get("/rpo-status", response_model=List[RecoveryPointStatus])
async def get_rpo_status(
    failover_manager: FailoverManager = Depends(get_failover_manager),
    current_user: User = Depends(get_current_user)
):
    """Get Recovery Point Objective status for all regions"""
    await require_permission(current_user, "failover.read")
    
    rpo_statuses = []
    
    for region in failover_manager.regions:
        if region != failover_manager.current_active_region:
            rpo_status = await failover_manager.check_rpo_status(
                failover_manager.current_active_region,
                region
            )
            rpo_statuses.append(rpo_status)
    
    return rpo_statuses


@router.post("/consistency-check", response_model=DataConsistencyCheck)
async def check_data_consistency(
    regions: List[str],
    check_type: str = "sample",
    background_tasks: BackgroundTasks = None,
    failover_manager: FailoverManager = Depends(get_failover_manager),
    current_user: User = Depends(get_current_user)
):
    """Check data consistency between regions"""
    await require_permission(current_user, "failover.consistency")
    
    # Validate regions
    for region in regions:
        if region not in failover_manager.regions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid region: {region}"
            )
    
    if len(regions) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least 2 regions required for consistency check"
        )
    
    # Run consistency check
    consistency_check = await failover_manager.check_data_consistency(regions)
    
    return consistency_check


@router.get("/metrics", response_model=FailoverMetrics)
async def get_failover_metrics(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    failover_manager: FailoverManager = Depends(get_failover_manager),
    current_user: User = Depends(get_current_user)
):
    """Get failover metrics and statistics"""
    await require_permission(current_user, "failover.read")
    
    # Get metrics from metrics collector
    stats = failover_manager.metrics.get_failover_statistics()
    
    # Calculate additional metrics from history
    history = failover_manager.failover_history
    if start_date:
        history = [e for e in history if e.started_at >= start_date]
    if end_date:
        history = [e for e in history if e.started_at <= end_date]
    
    total = len(history)
    successful = len([e for e in history if e.success])
    failed = total - successful
    
    # Calculate average failover time
    failover_times = []
    for event in history:
        if event.completed_at and event.started_at:
            duration = (event.completed_at - event.started_at).total_seconds()
            failover_times.append(duration)
    
    avg_time = sum(failover_times) / len(failover_times) if failover_times else 0
    
    metrics = FailoverMetrics(
        total_failovers=total,
        successful_failovers=successful,
        failed_failovers=failed,
        average_failover_time_seconds=avg_time,
        last_failover=history[0].started_at if history else None,
        **stats
    )
    
    return metrics


@router.get("/topology", response_model=SystemTopology)
async def get_system_topology(
    failover_manager: FailoverManager = Depends(get_failover_manager),
    current_user: User = Depends(get_current_user)
):
    """Get system topology and region configuration"""
    await require_permission(current_user, "failover.read")
    
    # Build region configurations
    region_configs = []
    for region in failover_manager.regions:
        config = RegionConfiguration(
            region=region,
            is_primary=region == failover_manager.primary_region,
            auto_failover_enabled=True,
            failover_priority=failover_manager._get_region_priority(region)
        )
        region_configs.append(config)
    
    # Build active connections (simplified)
    active_connections = {}
    for region in failover_manager.regions:
        if region == failover_manager.current_active_region:
            active_connections[region] = [r for r in failover_manager.regions if r != region]
    
    topology = SystemTopology(
        regions=region_configs,
        active_connections=active_connections,
        load_distribution={failover_manager.current_active_region: 1.0}
    )
    
    return topology


@router.put("/configuration")
async def update_configuration(
    auto_failover: Optional[bool] = None,
    auto_failback: Optional[bool] = None,
    failover_threshold: Optional[int] = None,
    health_check_interval: Optional[int] = None,
    current_user: User = Depends(get_current_user)
):
    """Update failover configuration"""
    await require_permission(current_user, "failover.admin")
    
    updates = {}
    
    if auto_failover is not None:
        settings.AUTO_FAILOVER_ENABLED = auto_failover
        updates["auto_failover_enabled"] = auto_failover
    
    if auto_failback is not None:
        settings.AUTO_FAILBACK_ENABLED = auto_failback
        updates["auto_failback_enabled"] = auto_failback
    
    if failover_threshold is not None:
        settings.FAILOVER_THRESHOLD = failover_threshold
        updates["failover_threshold"] = failover_threshold
    
    if health_check_interval is not None:
        settings.HEALTH_CHECK_INTERVAL_SECONDS = health_check_interval
        updates["health_check_interval_seconds"] = health_check_interval
    
    return {
        "message": "Configuration updated",
        "updates": updates
    }


@router.post("/notifications/test")
async def test_notifications(
    failover_manager: FailoverManager = Depends(get_failover_manager),
    current_user: User = Depends(get_current_user)
):
    """Test notification channels"""
    await require_permission(current_user, "failover.admin")
    
    results = await failover_manager.notifications.test_notifications()
    
    return {
        "message": "Notification test completed",
        "results": results
    }


# Health check endpoint
@router.get("/health")
async def health_check():
    """Health check endpoint for failover service"""
    return {"status": "healthy", "service": "failover"}