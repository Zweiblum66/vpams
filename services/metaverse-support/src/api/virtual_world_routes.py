"""API routes for virtual world management"""

import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..db.base import get_db
from ..models.schemas import (
    VirtualWorldDeploymentRequest,
    VirtualWorldDeploymentResponse,
    MultiPlatformDeploymentRequest,
    MultiPlatformDeploymentResponse,
    PlatformCapabilitiesResponse
)
from ..services.virtual_world_service import VirtualWorldService

logger = logging.getLogger(__name__)
router = APIRouter()

def get_virtual_world_service() -> VirtualWorldService:
    """Dependency to get virtual world service"""
    # This would be injected by the main app
    from ..main import virtual_world_service
    if not virtual_world_service:
        raise HTTPException(
            status_code=503, 
            detail="Virtual world service not available"
        )
    return virtual_world_service

@router.post("/deploy", response_model=VirtualWorldDeploymentResponse)
async def deploy_asset_to_world(
    deployment_request: VirtualWorldDeploymentRequest,
    db: AsyncSession = Depends(get_db),
    service: VirtualWorldService = Depends(get_virtual_world_service)
):
    """Deploy a media asset to a specific virtual world platform"""
    try:
        result = await service.deploy_asset(
            deployment_request.asset_id,
            deployment_request.platform,
            deployment_request.deployment_config
        )
        
        return VirtualWorldDeploymentResponse(
            success=True,
            asset_id=deployment_request.asset_id,
            platform=deployment_request.platform,
            deployment_result=result
        )
        
    except Exception as e:
        logger.error(f"Failed to deploy asset to virtual world: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Deployment failed: {str(e)}"
        )

@router.post("/deploy-multi", response_model=MultiPlatformDeploymentResponse)
async def deploy_asset_to_multiple_worlds(
    deployment_request: MultiPlatformDeploymentRequest,
    db: AsyncSession = Depends(get_db),
    service: VirtualWorldService = Depends(get_virtual_world_service)
):
    """Deploy a media asset to multiple virtual world platforms"""
    try:
        result = await service.deploy_to_multiple_platforms(
            deployment_request.asset_id,
            deployment_request.platforms,
            deployment_request.deployment_configs
        )
        
        return MultiPlatformDeploymentResponse(
            asset_id=deployment_request.asset_id,
            deployments=result["deployments"],
            total_platforms=result["total_platforms"],
            successful_deployments=result["successful_deployments"]
        )
        
    except Exception as e:
        logger.error(f"Failed to deploy asset to multiple virtual worlds: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Multi-platform deployment failed: {str(e)}"
        )

@router.get("/platforms", response_model=Dict[str, Any])
async def list_available_platforms(
    service: VirtualWorldService = Depends(get_virtual_world_service)
):
    """List all available virtual world platforms"""
    try:
        platforms = await service.get_all_platforms_status()
        return {
            "platforms": platforms,
            "total_count": len(platforms)
        }
        
    except Exception as e:
        logger.error(f"Failed to list platforms: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve platform information"
        )

@router.get("/platforms/{platform_name}", response_model=PlatformCapabilitiesResponse)
async def get_platform_capabilities(
    platform_name: str,
    service: VirtualWorldService = Depends(get_virtual_world_service)
):
    """Get capabilities and status of a specific virtual world platform"""
    try:
        capabilities = await service.get_platform_capabilities(platform_name)
        
        if not capabilities:
            raise HTTPException(
                status_code=404,
                detail=f"Platform {platform_name} not found"
            )
        
        return PlatformCapabilitiesResponse(**capabilities)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get platform capabilities: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve platform capabilities"
        )

@router.get("/health")
async def virtual_world_health_check(
    service: VirtualWorldService = Depends(get_virtual_world_service)
):
    """Health check for virtual world service"""
    try:
        health_status = await service.health_check()
        return health_status
        
    except Exception as e:
        logger.error(f"Virtual world health check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail="Virtual world service health check failed"
        )