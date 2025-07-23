"""
API routes for CDN service
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, status
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from ..services.cdn_manager import GlobalCDNManager, OptimizationType
from ..models.schemas import (
    CDNProvider,
    CDNDistribution,
    CDNOrigin,
    CacheRule,
    PurgeRequest,
    PrefetchRequest,
    CDNMetrics,
    BandwidthUsage,
    EdgeLocation,
    ContentOptimization,
    ImageOptimizationSettings,
    VideoOptimizationSettings,
    CDNHealthCheck,
    CDNAlert,
    SecurityPolicy,
    CacheStatus,
    CDNCostEstimate
)
from ..core.deps import get_current_user, get_cdn_manager
from ..core.security import require_permission
from ..models.database import User

router = APIRouter(prefix="/api/v1/cdn", tags=["cdn"])


@router.get("/providers", response_model=List[CDNProvider])
async def list_cdn_providers(
    enabled_only: bool = Query(True, description="Only show enabled providers"),
    cdn_manager: GlobalCDNManager = Depends(get_cdn_manager),
    current_user: User = Depends(get_current_user)
):
    """List available CDN providers"""
    await require_permission(current_user, "cdn.read")
    
    providers = list(cdn_manager.providers.values())
    
    if enabled_only:
        providers = [p for p in providers if p.enabled]
    
    return providers


@router.get("/distributions", response_model=List[CDNDistribution])
async def list_distributions(
    provider_id: Optional[str] = Query(None, description="Filter by provider"),
    status: Optional[str] = Query(None, description="Filter by status"),
    enabled: Optional[bool] = Query(None, description="Filter by enabled status"),
    cdn_manager: GlobalCDNManager = Depends(get_cdn_manager),
    current_user: User = Depends(get_current_user)
):
    """List CDN distributions"""
    await require_permission(current_user, "cdn.read")
    
    distributions = list(cdn_manager.distributions.values())
    
    # Apply filters
    if provider_id:
        distributions = [d for d in distributions if d.provider_id == provider_id]
    
    if status:
        distributions = [d for d in distributions if d.status == status]
    
    if enabled is not None:
        distributions = [d for d in distributions if d.enabled == enabled]
    
    return distributions


@router.post("/distributions", response_model=CDNDistribution, status_code=status.HTTP_201_CREATED)
async def create_distribution(
    name: str,
    origins: List[CDNOrigin],
    cache_rules: List[CacheRule],
    provider_id: str = "cloudfront",
    custom_domain: Optional[str] = None,
    security_policy: Optional[SecurityPolicy] = None,
    cdn_manager: GlobalCDNManager = Depends(get_cdn_manager),
    current_user: User = Depends(get_current_user)
):
    """Create a new CDN distribution"""
    await require_permission(current_user, "cdn.create")
    
    try:
        distribution = await cdn_manager.create_distribution(
            name=name,
            origins=origins,
            cache_rules=cache_rules,
            provider_id=provider_id,
            custom_domain=custom_domain,
            security_policy=security_policy
        )
        
        return distribution
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create distribution: {str(e)}"
        )


@router.get("/distributions/{distribution_id}", response_model=CDNDistribution)
async def get_distribution(
    distribution_id: str,
    cdn_manager: GlobalCDNManager = Depends(get_cdn_manager),
    current_user: User = Depends(get_current_user)
):
    """Get CDN distribution details"""
    await require_permission(current_user, "cdn.read")
    
    distribution = cdn_manager.distributions.get(distribution_id)
    if not distribution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Distribution {distribution_id} not found"
        )
    
    return distribution


@router.put("/distributions/{distribution_id}", response_model=CDNDistribution)
async def update_distribution(
    distribution_id: str,
    cache_rules: Optional[List[CacheRule]] = None,
    security_policy: Optional[SecurityPolicy] = None,
    enabled: Optional[bool] = None,
    cdn_manager: GlobalCDNManager = Depends(get_cdn_manager),
    current_user: User = Depends(get_current_user)
):
    """Update CDN distribution configuration"""
    await require_permission(current_user, "cdn.update")
    
    try:
        distribution = await cdn_manager.update_distribution(
            distribution_id=distribution_id,
            cache_rules=cache_rules,
            security_policy=security_policy,
            enabled=enabled
        )
        
        return distribution
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update distribution: {str(e)}"
        )


@router.delete("/distributions/{distribution_id}")
async def delete_distribution(
    distribution_id: str,
    cdn_manager: GlobalCDNManager = Depends(get_cdn_manager),
    current_user: User = Depends(get_current_user)
):
    """Delete a CDN distribution"""
    await require_permission(current_user, "cdn.delete")
    
    distribution = cdn_manager.distributions.get(distribution_id)
    if not distribution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Distribution {distribution_id} not found"
        )
    
    # In a real implementation, this would delete the distribution
    # For now, just mark it as deleted
    distribution.status = "deleting"
    distribution.enabled = False
    
    return {"message": f"Distribution {distribution_id} deletion initiated"}


@router.post("/distributions/{distribution_id}/purge", response_model=PurgeRequest)
async def purge_cache(
    distribution_id: str,
    paths: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
    purge_all: bool = False,
    cdn_manager: GlobalCDNManager = Depends(get_cdn_manager),
    current_user: User = Depends(get_current_user)
):
    """Purge CDN cache"""
    await require_permission(current_user, "cdn.purge")
    
    if not paths and not tags and not purge_all:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must specify paths, tags, or purge_all=true"
        )
    
    try:
        purge_request = await cdn_manager.purge_cache(
            distribution_id=distribution_id,
            paths=paths,
            tags=tags,
            purge_all=purge_all
        )
        
        return purge_request
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to purge cache: {str(e)}"
        )


@router.post("/distributions/{distribution_id}/prefetch", response_model=PrefetchRequest)
async def prefetch_content(
    distribution_id: str,
    urls: List[str],
    priority: str = "normal",
    cdn_manager: GlobalCDNManager = Depends(get_cdn_manager),
    current_user: User = Depends(get_current_user)
):
    """Prefetch content to edge locations"""
    await require_permission(current_user, "cdn.prefetch")
    
    if not urls:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must specify URLs to prefetch"
        )
    
    try:
        prefetch_request = await cdn_manager.prefetch_content(
            distribution_id=distribution_id,
            urls=urls,
            priority=priority
        )
        
        return prefetch_request
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to prefetch content: {str(e)}"
        )


@router.get("/distributions/{distribution_id}/metrics", response_model=CDNMetrics)
async def get_cdn_metrics(
    distribution_id: str,
    start_time: datetime = Query(..., description="Start time for metrics"),
    end_time: datetime = Query(..., description="End time for metrics"),
    metric_type: str = Query("all", description="Type of metrics to retrieve"),
    cdn_manager: GlobalCDNManager = Depends(get_cdn_manager),
    current_user: User = Depends(get_current_user)
):
    """Get CDN metrics for a distribution"""
    await require_permission(current_user, "cdn.read")
    
    try:
        metrics = await cdn_manager.get_metrics(
            distribution_id=distribution_id,
            start_time=start_time,
            end_time=end_time,
            metric_type=metric_type
        )
        
        return metrics
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get metrics: {str(e)}"
        )


@router.get("/distributions/{distribution_id}/bandwidth", response_model=List[BandwidthUsage])
async def get_bandwidth_usage(
    distribution_id: str,
    start_time: datetime = Query(..., description="Start time"),
    end_time: datetime = Query(..., description="End time"),
    group_by: str = Query("hour", description="Grouping interval (hour, day)"),
    cdn_manager: GlobalCDNManager = Depends(get_cdn_manager),
    current_user: User = Depends(get_current_user)
):
    """Get bandwidth usage data"""
    await require_permission(current_user, "cdn.read")
    
    try:
        usage = await cdn_manager.get_bandwidth_usage(
            distribution_id=distribution_id,
            start_time=start_time,
            end_time=end_time,
            group_by=group_by
        )
        
        return usage
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get("/edge-locations", response_model=List[EdgeLocation])
async def list_edge_locations(
    distribution_id: Optional[str] = Query(None, description="Filter by distribution"),
    cdn_manager: GlobalCDNManager = Depends(get_cdn_manager),
    current_user: User = Depends(get_current_user)
):
    """List CDN edge locations"""
    await require_permission(current_user, "cdn.read")
    
    try:
        locations = await cdn_manager.get_edge_locations(distribution_id)
        return locations
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.post("/distributions/{distribution_id}/optimize", response_model=ContentOptimization)
async def configure_optimization(
    distribution_id: str,
    optimization_type: OptimizationType,
    settings: Dict[str, Any],
    cdn_manager: GlobalCDNManager = Depends(get_cdn_manager),
    current_user: User = Depends(get_current_user)
):
    """Configure content optimization"""
    await require_permission(current_user, "cdn.update")
    
    try:
        optimization = await cdn_manager.optimize_content(
            distribution_id=distribution_id,
            optimization_type=optimization_type,
            settings=settings
        )
        
        return optimization
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to configure optimization: {str(e)}"
        )


@router.post("/distributions/{distribution_id}/headers")
async def configure_custom_headers(
    distribution_id: str,
    headers: Dict[str, str],
    cdn_manager: GlobalCDNManager = Depends(get_cdn_manager),
    current_user: User = Depends(get_current_user)
):
    """Configure custom headers for a distribution"""
    await require_permission(current_user, "cdn.update")
    
    try:
        await cdn_manager.configure_custom_headers(distribution_id, headers)
        
        return {"message": "Custom headers configured successfully"}
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.post("/distributions/{distribution_id}/logs/realtime")
async def enable_realtime_logs(
    distribution_id: str,
    log_destination: str,
    cdn_manager: GlobalCDNManager = Depends(get_cdn_manager),
    current_user: User = Depends(get_current_user)
):
    """Enable real-time logging for a distribution"""
    await require_permission(current_user, "cdn.update")
    
    try:
        await cdn_manager.enable_real_time_logs(distribution_id, log_destination)
        
        return {"message": "Real-time logs enabled successfully"}
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get("/distributions/{distribution_id}/cache-status", response_model=CacheStatus)
async def get_cache_status(
    distribution_id: str,
    cdn_manager: GlobalCDNManager = Depends(get_cdn_manager),
    current_user: User = Depends(get_current_user)
):
    """Get cache status for a distribution"""
    await require_permission(current_user, "cdn.read")
    
    # In a real implementation, this would fetch actual cache status
    # For now, return sample data
    cache_status = CacheStatus(
        distribution_id=distribution_id,
        total_objects=1000000,
        total_size_bytes=1024 * 1024 * 1024 * 100,  # 100GB
        hot_objects=100000,
        warm_objects=300000,
        cold_objects=600000,
        eviction_rate=0.05,
        fill_rate=0.95
    )
    
    return cache_status


@router.get("/distributions/{distribution_id}/cost-estimate", response_model=CDNCostEstimate)
async def get_cost_estimate(
    distribution_id: str,
    start_date: datetime = Query(..., description="Start date for cost calculation"),
    end_date: datetime = Query(..., description="End date for cost calculation"),
    cdn_manager: GlobalCDNManager = Depends(get_cdn_manager),
    current_user: User = Depends(get_current_user)
):
    """Get cost estimate for CDN usage"""
    await require_permission(current_user, "cdn.read")
    
    # In a real implementation, this would calculate actual costs
    # For now, return sample estimate
    days = (end_date - start_date).days
    
    cost_estimate = CDNCostEstimate(
        distribution_id=distribution_id,
        period_start=start_date,
        period_end=end_date,
        data_transfer_gb=days * 100.0,  # 100GB per day
        data_transfer_cost=days * 8.5,  # $0.085 per GB
        requests_millions=days * 10.0,  # 10M requests per day
        requests_cost=days * 0.75,  # $0.0075 per 10K requests
        invalidation_requests=days * 2,
        invalidation_cost=0.0,  # First 1000 free
        field_level_encryption_requests=0,
        field_level_encryption_cost=0.0,
        total_cost=(days * 8.5) + (days * 0.75)
    )
    
    return cost_estimate


@router.post("/optimize/image-settings", response_model=ImageOptimizationSettings)
async def create_image_optimization_settings(
    settings: ImageOptimizationSettings,
    current_user: User = Depends(get_current_user)
):
    """Create image optimization settings template"""
    await require_permission(current_user, "cdn.update")
    
    # In a real implementation, this would save the settings
    return settings


@router.post("/optimize/video-settings", response_model=VideoOptimizationSettings)
async def create_video_optimization_settings(
    settings: VideoOptimizationSettings,
    current_user: User = Depends(get_current_user)
):
    """Create video optimization settings template"""
    await require_permission(current_user, "cdn.update")
    
    # In a real implementation, this would save the settings
    return settings


# Health check endpoint
@router.get("/health")
async def health_check():
    """Health check endpoint for CDN service"""
    return {"status": "healthy", "service": "cdn"}