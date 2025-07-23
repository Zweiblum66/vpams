"""
API routes for geo-replication service
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query, status
from typing import List, Optional, Dict, Any
from datetime import datetime

from ..services.replication_manager import GeoReplicationManager, ReplicationType
from ..models.schemas import (
    ReplicationStatus,
    ReplicationConfig,
    ReplicationJob,
    ReplicationMetrics,
    RegionInfo,
    DataSyncRequest,
    DataSyncResponse,
    CrossRegionLatency,
    ReplicationAlert,
    ConflictResolution,
    ReplicationTopology
)
from ..core.deps import get_current_user, get_replication_manager
from ..core.security import require_permission
from ..models.database import User

router = APIRouter(prefix="/api/v1/replication", tags=["geo-replication"])


@router.get("/status", response_model=ReplicationStatus)
async def get_replication_status(
    replication_manager: GeoReplicationManager = Depends(get_replication_manager),
    current_user: User = Depends(get_current_user)
):
    """Get current replication status across all regions"""
    await require_permission(current_user, "replication.read")
    
    try:
        status = await replication_manager.get_replication_status()
        return status
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get replication status: {str(e)}"
        )


@router.get("/config", response_model=ReplicationConfig)
async def get_replication_config(
    replication_manager: GeoReplicationManager = Depends(get_replication_manager),
    current_user: User = Depends(get_current_user)
):
    """Get current replication configuration"""
    await require_permission(current_user, "replication.read")
    
    return replication_manager.replication_config


@router.put("/config", response_model=ReplicationConfig)
async def update_replication_config(
    config: ReplicationConfig,
    replication_manager: GeoReplicationManager = Depends(get_replication_manager),
    current_user: User = Depends(get_current_user)
):
    """Update replication configuration"""
    await require_permission(current_user, "replication.manage")
    
    try:
        # Update configuration
        replication_manager.replication_config = config
        
        # Restart replication if needed
        if config.enabled:
            await replication_manager.initialize()
        else:
            await replication_manager.shutdown()
        
        return config
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update replication config: {str(e)}"
        )


@router.get("/regions", response_model=List[RegionInfo])
async def list_regions(
    include_inactive: bool = Query(False, description="Include inactive regions"),
    replication_manager: GeoReplicationManager = Depends(get_replication_manager),
    current_user: User = Depends(get_current_user)
):
    """List all configured regions"""
    await require_permission(current_user, "replication.read")
    
    regions = list(replication_manager.regions.values())
    
    if not include_inactive:
        regions = [r for r in regions if r.status == "active"]
    
    return regions


@router.get("/regions/{region_id}", response_model=RegionInfo)
async def get_region_info(
    region_id: str,
    replication_manager: GeoReplicationManager = Depends(get_replication_manager),
    current_user: User = Depends(get_current_user)
):
    """Get information about a specific region"""
    await require_permission(current_user, "replication.read")
    
    region = replication_manager.regions.get(region_id)
    if not region:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Region {region_id} not found"
        )
    
    return region


@router.post("/regions/{region_id}/health-check")
async def check_region_health(
    region_id: str,
    replication_manager: GeoReplicationManager = Depends(get_replication_manager),
    current_user: User = Depends(get_current_user)
):
    """Manually trigger health check for a region"""
    await require_permission(current_user, "replication.manage")
    
    if region_id not in replication_manager.regions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Region {region_id} not found"
        )
    
    health = await replication_manager._check_region_health(region_id)
    return health


@router.get("/jobs", response_model=List[ReplicationJob])
async def list_replication_jobs(
    status: Optional[str] = Query(None, description="Filter by job status"),
    region_id: Optional[str] = Query(None, description="Filter by region"),
    replication_type: Optional[ReplicationType] = Query(None, description="Filter by type"),
    limit: int = Query(100, ge=1, le=1000),
    replication_manager: GeoReplicationManager = Depends(get_replication_manager),
    current_user: User = Depends(get_current_user)
):
    """List replication jobs"""
    await require_permission(current_user, "replication.read")
    
    jobs = list(replication_manager.replication_jobs.values())
    
    # Apply filters
    if status:
        jobs = [j for j in jobs if j.status == status]
    
    if region_id:
        jobs = [j for j in jobs if j.source_region == region_id or j.target_region == region_id]
    
    if replication_type:
        jobs = [j for j in jobs if j.replication_type == replication_type]
    
    # Sort by started_at descending
    jobs.sort(key=lambda j: j.started_at or datetime.min, reverse=True)
    
    return jobs[:limit]


@router.get("/jobs/{job_id}", response_model=ReplicationJob)
async def get_replication_job(
    job_id: str,
    replication_manager: GeoReplicationManager = Depends(get_replication_manager),
    current_user: User = Depends(get_current_user)
):
    """Get details of a specific replication job"""
    await require_permission(current_user, "replication.read")
    
    job = replication_manager.replication_jobs.get(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Replication job {job_id} not found"
        )
    
    return job


@router.post("/sync", response_model=DataSyncResponse)
async def trigger_data_sync(
    sync_request: DataSyncRequest,
    background_tasks: BackgroundTasks,
    replication_manager: GeoReplicationManager = Depends(get_replication_manager),
    current_user: User = Depends(get_current_user)
):
    """Manually trigger data synchronization"""
    await require_permission(current_user, "replication.sync")
    
    # Validate regions
    if sync_request.source_region not in replication_manager.regions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Source region {sync_request.source_region} not found"
        )
    
    for target in sync_request.target_regions:
        if target not in replication_manager.regions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Target region {target} not found"
            )
    
    # Create sync job
    sync_id = f"manual-sync-{datetime.utcnow().timestamp()}"
    
    # Schedule sync in background
    for target_region in sync_request.target_regions:
        background_tasks.add_task(
            replication_manager.force_sync,
            target_region,
            sync_request.sync_type
        )
    
    return DataSyncResponse(
        sync_id=sync_id,
        status="initiated",
        source_region=sync_request.source_region,
        target_regions=sync_request.target_regions,
        sync_type=sync_request.sync_type
    )


@router.get("/metrics", response_model=List[ReplicationMetrics])
async def get_replication_metrics(
    region_id: Optional[str] = Query(None, description="Filter by region"),
    replication_type: Optional[ReplicationType] = Query(None, description="Filter by type"),
    start_time: Optional[datetime] = Query(None, description="Start time for metrics"),
    end_time: Optional[datetime] = Query(None, description="End time for metrics"),
    replication_manager: GeoReplicationManager = Depends(get_replication_manager),
    current_user: User = Depends(get_current_user)
):
    """Get replication metrics"""
    await require_permission(current_user, "replication.read")
    
    # In a real implementation, this would query a metrics store
    # For now, return sample metrics
    metrics = []
    
    for region in replication_manager.regions.values():
        if region_id and region.region_id != region_id:
            continue
        
        for rep_type in ReplicationType:
            if replication_type and rep_type != replication_type:
                continue
            
            if rep_type == ReplicationType.FULL:
                continue
            
            metric = ReplicationMetrics(
                region_id=region.region_id,
                replication_type=rep_type,
                items_pending=0,
                items_processed=1000,
                items_failed=0,
                bytes_transferred=1024 * 1024 * 100,  # 100MB
                lag_seconds=5.0,
                error_rate=0.0,
                throughput_mbps=10.0
            )
            metrics.append(metric)
    
    return metrics


@router.get("/latency", response_model=List[CrossRegionLatency])
async def get_cross_region_latency(
    source_region: Optional[str] = Query(None, description="Source region"),
    target_region: Optional[str] = Query(None, description="Target region"),
    replication_manager: GeoReplicationManager = Depends(get_replication_manager),
    current_user: User = Depends(get_current_user)
):
    """Get cross-region latency measurements"""
    await require_permission(current_user, "replication.read")
    
    latencies = []
    
    # In a real implementation, this would measure actual latency
    # For now, return sample data
    for source in replication_manager.regions:
        if source_region and source != source_region:
            continue
        
        for target in replication_manager.regions:
            if target == source:
                continue
            
            if target_region and target != target_region:
                continue
            
            latency = CrossRegionLatency(
                source_region=source,
                target_region=target,
                latency_ms=50.0 if source == replication_manager.replication_config.primary_region else 100.0,
                packet_loss_percentage=0.1,
                bandwidth_mbps=1000.0
            )
            latencies.append(latency)
    
    return latencies


@router.get("/alerts", response_model=List[ReplicationAlert])
async def get_replication_alerts(
    region_id: Optional[str] = Query(None, description="Filter by region"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    acknowledged: Optional[bool] = Query(None, description="Filter by acknowledgment status"),
    limit: int = Query(100, ge=1, le=1000),
    replication_manager: GeoReplicationManager = Depends(get_replication_manager),
    current_user: User = Depends(get_current_user)
):
    """Get replication alerts"""
    await require_permission(current_user, "replication.read")
    
    # In a real implementation, this would query an alert store
    alerts = []
    
    # Check for any inactive regions
    for region in replication_manager.regions.values():
        if region.status != "active":
            alert = ReplicationAlert(
                alert_id=f"alert-{region.region_id}-down",
                alert_type="region_down",
                severity="critical",
                region_id=region.region_id,
                message=f"Region {region.region_id} is {region.status}",
                details={"error": region.error_message}
            )
            alerts.append(alert)
    
    # Apply filters
    if region_id:
        alerts = [a for a in alerts if a.region_id == region_id]
    
    if severity:
        alerts = [a for a in alerts if a.severity == severity]
    
    if acknowledged is not None:
        alerts = [a for a in alerts if a.acknowledged == acknowledged]
    
    return alerts[:limit]


@router.put("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: str,
    replication_manager: GeoReplicationManager = Depends(get_replication_manager),
    current_user: User = Depends(get_current_user)
):
    """Acknowledge a replication alert"""
    await require_permission(current_user, "replication.manage")
    
    # In a real implementation, this would update the alert in storage
    return {
        "alert_id": alert_id,
        "acknowledged": True,
        "acknowledged_by": current_user.email,
        "acknowledged_at": datetime.utcnow()
    }


@router.get("/conflicts", response_model=List[ConflictResolution])
async def get_replication_conflicts(
    status: Optional[str] = Query(None, description="Filter by resolution status"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    limit: int = Query(100, ge=1, le=1000),
    replication_manager: GeoReplicationManager = Depends(get_replication_manager),
    current_user: User = Depends(get_current_user)
):
    """Get replication conflicts pending resolution"""
    await require_permission(current_user, "replication.read")
    
    # In a real implementation, this would query the conflict store
    # For now, return empty list
    return []


@router.post("/conflicts/{conflict_id}/resolve")
async def resolve_conflict(
    conflict_id: str,
    resolution: Dict[str, Any],
    replication_manager: GeoReplicationManager = Depends(get_replication_manager),
    current_user: User = Depends(get_current_user)
):
    """Manually resolve a replication conflict"""
    await require_permission(current_user, "replication.resolve_conflicts")
    
    # In a real implementation, this would update the conflict resolution
    return {
        "conflict_id": conflict_id,
        "resolved": True,
        "resolved_by": current_user.email,
        "resolved_at": datetime.utcnow(),
        "resolution": resolution
    }


@router.get("/topology", response_model=ReplicationTopology)
async def get_replication_topology(
    replication_manager: GeoReplicationManager = Depends(get_replication_manager),
    current_user: User = Depends(get_current_user)
):
    """Get current replication topology"""
    await require_permission(current_user, "replication.read")
    
    # Build topology from current configuration
    regions = list(replication_manager.regions.values())
    
    # Hub-spoke topology with primary as hub
    replication_paths = []
    primary = replication_manager.replication_config.primary_region
    
    for region in regions:
        if not region.is_primary:
            replication_paths.append({
                "source": primary,
                "target": region.region_id,
                "bidirectional": False
            })
    
    topology = ReplicationTopology(
        topology_type="hub_spoke",
        primary_region=primary,
        regions=regions,
        replication_paths=replication_paths
    )
    
    return topology


@router.post("/failover/{region_id}")
async def trigger_region_failover(
    region_id: str,
    force: bool = Query(False, description="Force failover even if region is healthy"),
    replication_manager: GeoReplicationManager = Depends(get_replication_manager),
    current_user: User = Depends(get_current_user)
):
    """Trigger failover for a specific region"""
    await require_permission(current_user, "replication.failover")
    
    if region_id not in replication_manager.regions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Region {region_id} not found"
        )
    
    region = replication_manager.regions[region_id]
    
    if region.is_primary:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot failover primary region"
        )
    
    if region.status == "active" and not force:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Region is healthy. Use force=true to failover anyway"
        )
    
    # In a real implementation, this would trigger actual failover
    return {
        "region_id": region_id,
        "failover_initiated": True,
        "initiated_by": current_user.email,
        "initiated_at": datetime.utcnow()
    }


# Health check endpoint
@router.get("/health")
async def health_check():
    """Health check endpoint for geo-replication service"""
    return {"status": "healthy", "service": "geo-replication"}