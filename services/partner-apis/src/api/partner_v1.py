"""Partner API v1 endpoints"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
from uuid import UUID
import httpx
import logging

from ..core.database import get_db
from ..core.auth import get_api_key, APIKey
from ..models.schemas import (
    AssetResponse, AssetListResponse, AssetCreate, AssetUpdate,
    ProjectResponse, ProjectListResponse, ProjectCreate, ProjectUpdate,
    SearchResponse, SearchRequest,
    WorkflowResponse, WorkflowListResponse, WorkflowTriggerRequest,
    UserResponse, UserListResponse,
    PaginationParams, StandardResponse
)
from ..services.proxy_service import ProxyService
from ..services.analytics_service import AnalyticsService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Partner API v1"])

# Initialize services
proxy_service = ProxyService()
analytics_service = AnalyticsService()


# Asset Management Endpoints
@router.get("/assets", response_model=AssetListResponse)
async def list_assets(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    project_id: Optional[UUID] = Query(None, description="Filter by project ID"),
    asset_type: Optional[str] = Query(None, description="Filter by asset type"),
    search: Optional[str] = Query(None, description="Search term"),
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(get_api_key)
):
    """List assets with filtering and pagination"""
    
    # Check feature access
    if "assets" not in api_key.allowed_features and "*" not in api_key.allowed_features:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access to assets feature not allowed"
        )
    
    try:
        # Log API usage
        await analytics_service.log_api_usage(
            api_key_id=api_key.id,
            endpoint="/assets",
            method="GET",
            status_code=200
        )
        
        # Proxy request to Asset Management Service
        params = {
            "page": page,
            "limit": limit,
            "project_id": str(project_id) if project_id else None,
            "asset_type": asset_type,
            "search": search
        }
        
        response = await proxy_service.proxy_request(
            service="asset-management",
            path="/api/v1/assets",
            method="GET",
            params={k: v for k, v in params.items() if v is not None}
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error listing assets: {e}")
        await analytics_service.log_api_usage(
            api_key_id=api_key.id,
            endpoint="/assets",
            method="GET",
            status_code=500,
            error_message=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve assets"
        )


@router.get("/assets/{asset_id}", response_model=AssetResponse)
async def get_asset(
    asset_id: UUID = Path(..., description="Asset ID"),
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(get_api_key)
):
    """Get asset by ID"""
    
    if "assets" not in api_key.allowed_features and "*" not in api_key.allowed_features:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access to assets feature not allowed"
        )
    
    try:
        await analytics_service.log_api_usage(
            api_key_id=api_key.id,
            endpoint=f"/assets/{asset_id}",
            method="GET",
            status_code=200
        )
        
        response = await proxy_service.proxy_request(
            service="asset-management",
            path=f"/api/v1/assets/{asset_id}",
            method="GET"
        )
        
        return response
        
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Asset not found"
            )
        raise
    except Exception as e:
        logger.error(f"Error getting asset {asset_id}: {e}")
        await analytics_service.log_api_usage(
            api_key_id=api_key.id,
            endpoint=f"/assets/{asset_id}",
            method="GET",
            status_code=500,
            error_message=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve asset"
        )


@router.post("/assets", response_model=AssetResponse, status_code=status.HTTP_201_CREATED)
async def create_asset(
    asset_data: AssetCreate,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(get_api_key)
):
    """Create a new asset"""
    
    # Check write permissions
    if "write" not in api_key.scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Write access required"
        )
    
    if "assets" not in api_key.allowed_features and "*" not in api_key.allowed_features:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access to assets feature not allowed"
        )
    
    try:
        await analytics_service.log_api_usage(
            api_key_id=api_key.id,
            endpoint="/assets",
            method="POST",
            status_code=201
        )
        
        response = await proxy_service.proxy_request(
            service="asset-management",
            path="/api/v1/assets",
            method="POST",
            json=asset_data.model_dump()
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error creating asset: {e}")
        await analytics_service.log_api_usage(
            api_key_id=api_key.id,
            endpoint="/assets",
            method="POST",
            status_code=500,
            error_message=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create asset"
        )


@router.put("/assets/{asset_id}", response_model=AssetResponse)
async def update_asset(
    asset_id: UUID = Path(..., description="Asset ID"),
    asset_data: AssetUpdate = None,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(get_api_key)
):
    """Update an asset"""
    
    if "write" not in api_key.scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Write access required"
        )
    
    if "assets" not in api_key.allowed_features and "*" not in api_key.allowed_features:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access to assets feature not allowed"
        )
    
    try:
        await analytics_service.log_api_usage(
            api_key_id=api_key.id,
            endpoint=f"/assets/{asset_id}",
            method="PUT",
            status_code=200
        )
        
        response = await proxy_service.proxy_request(
            service="asset-management",
            path=f"/api/v1/assets/{asset_id}",
            method="PUT",
            json=asset_data.model_dump() if asset_data else {}
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error updating asset {asset_id}: {e}")
        await analytics_service.log_api_usage(
            api_key_id=api_key.id,
            endpoint=f"/assets/{asset_id}",
            method="PUT",
            status_code=500,
            error_message=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update asset"
        )


@router.delete("/assets/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_asset(
    asset_id: UUID = Path(..., description="Asset ID"),
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(get_api_key)
):
    """Delete an asset"""
    
    if "write" not in api_key.scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Write access required"
        )
    
    if "assets" not in api_key.allowed_features and "*" not in api_key.allowed_features:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access to assets feature not allowed"
        )
    
    try:
        await analytics_service.log_api_usage(
            api_key_id=api_key.id,
            endpoint=f"/assets/{asset_id}",
            method="DELETE",
            status_code=204
        )
        
        await proxy_service.proxy_request(
            service="asset-management",
            path=f"/api/v1/assets/{asset_id}",
            method="DELETE"
        )
        
    except Exception as e:
        logger.error(f"Error deleting asset {asset_id}: {e}")
        await analytics_service.log_api_usage(
            api_key_id=api_key.id,
            endpoint=f"/assets/{asset_id}",
            method="DELETE",
            status_code=500,
            error_message=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete asset"
        )


# Search Endpoints
@router.post("/search", response_model=SearchResponse)
async def search_assets(
    search_request: SearchRequest,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(get_api_key)
):
    """Search assets using various criteria"""
    
    if "search" not in api_key.allowed_features and "*" not in api_key.allowed_features:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access to search feature not allowed"
        )
    
    try:
        await analytics_service.log_api_usage(
            api_key_id=api_key.id,
            endpoint="/search",
            method="POST",
            status_code=200
        )
        
        response = await proxy_service.proxy_request(
            service="search-engine",
            path="/api/v1/search",
            method="POST",
            json=search_request.model_dump()
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error performing search: {e}")
        await analytics_service.log_api_usage(
            api_key_id=api_key.id,
            endpoint="/search",
            method="POST",
            status_code=500,
            error_message=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Search request failed"
        )


# Project Management Endpoints
@router.get("/projects", response_model=ProjectListResponse)
async def list_projects(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search term"),
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(get_api_key)
):
    """List projects with filtering and pagination"""
    
    if "projects" not in api_key.allowed_features and "*" not in api_key.allowed_features:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access to projects feature not allowed"
        )
    
    try:
        await analytics_service.log_api_usage(
            api_key_id=api_key.id,
            endpoint="/projects",
            method="GET",
            status_code=200
        )
        
        params = {
            "page": page,
            "limit": limit,
            "search": search
        }
        
        response = await proxy_service.proxy_request(
            service="asset-management",
            path="/api/v1/projects",
            method="GET",
            params={k: v for k, v in params.items() if v is not None}
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error listing projects: {e}")
        await analytics_service.log_api_usage(
            api_key_id=api_key.id,
            endpoint="/projects",
            method="GET",
            status_code=500,
            error_message=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve projects"
        )


# Workflow Management Endpoints
@router.get("/workflows", response_model=WorkflowListResponse)
async def list_workflows(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query(None, description="Filter by status"),
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(get_api_key)
):
    """List workflows with filtering and pagination"""
    
    if "workflows" not in api_key.allowed_features and "*" not in api_key.allowed_features:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access to workflows feature not allowed"
        )
    
    try:
        await analytics_service.log_api_usage(
            api_key_id=api_key.id,
            endpoint="/workflows",
            method="GET",
            status_code=200
        )
        
        params = {
            "page": page,
            "limit": limit,
            "status": status
        }
        
        response = await proxy_service.proxy_request(
            service="workflow-engine",
            path="/api/v1/workflows",
            method="GET",
            params={k: v for k, v in params.items() if v is not None}
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error listing workflows: {e}")
        await analytics_service.log_api_usage(
            api_key_id=api_key.id,
            endpoint="/workflows",
            method="GET",
            status_code=500,
            error_message=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve workflows"
        )


@router.post("/workflows/{workflow_id}/trigger", response_model=StandardResponse)
async def trigger_workflow(
    workflow_id: UUID = Path(..., description="Workflow ID"),
    trigger_data: WorkflowTriggerRequest = None,
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(get_api_key)
):
    """Trigger a workflow execution"""
    
    if "write" not in api_key.scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Write access required"
        )
    
    if "workflows" not in api_key.allowed_features and "*" not in api_key.allowed_features:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access to workflows feature not allowed"
        )
    
    try:
        await analytics_service.log_api_usage(
            api_key_id=api_key.id,
            endpoint=f"/workflows/{workflow_id}/trigger",
            method="POST",
            status_code=200
        )
        
        response = await proxy_service.proxy_request(
            service="workflow-engine",
            path=f"/api/v1/workflows/{workflow_id}/trigger",
            method="POST",
            json=trigger_data.model_dump() if trigger_data else {}
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error triggering workflow {workflow_id}: {e}")
        await analytics_service.log_api_usage(
            api_key_id=api_key.id,
            endpoint=f"/workflows/{workflow_id}/trigger",
            method="POST",
            status_code=500,
            error_message=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to trigger workflow"
        )


# User Management Endpoints
@router.get("/users", response_model=UserListResponse)
async def list_users(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search term"),
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(get_api_key)
):
    """List users with filtering and pagination"""
    
    if "users" not in api_key.allowed_features and "*" not in api_key.allowed_features:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access to users feature not allowed"
        )
    
    try:
        await analytics_service.log_api_usage(
            api_key_id=api_key.id,
            endpoint="/users",
            method="GET",
            status_code=200
        )
        
        params = {
            "page": page,
            "limit": limit,
            "search": search
        }
        
        response = await proxy_service.proxy_request(
            service="user-management",
            path="/api/v1/users",
            method="GET",
            params={k: v for k, v in params.items() if v is not None}
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error listing users: {e}")
        await analytics_service.log_api_usage(
            api_key_id=api_key.id,
            endpoint="/users",
            method="GET",
            status_code=500,
            error_message=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve users"
        )


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID = Path(..., description="User ID"),
    db: AsyncSession = Depends(get_db),
    api_key: APIKey = Depends(get_api_key)
):
    """Get user by ID"""
    
    if "users" not in api_key.allowed_features and "*" not in api_key.allowed_features:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access to users feature not allowed"
        )
    
    try:
        await analytics_service.log_api_usage(
            api_key_id=api_key.id,
            endpoint=f"/users/{user_id}",
            method="GET",
            status_code=200
        )
        
        response = await proxy_service.proxy_request(
            service="user-management",
            path=f"/api/v1/users/{user_id}",
            method="GET"
        )
        
        return response
        
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        raise
    except Exception as e:
        logger.error(f"Error getting user {user_id}: {e}")
        await analytics_service.log_api_usage(
            api_key_id=api_key.id,
            endpoint=f"/users/{user_id}",
            method="GET",
            status_code=500,
            error_message=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user"
        )