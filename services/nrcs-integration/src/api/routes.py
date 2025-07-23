"""Main API routes for NRCS Integration Service"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.base import get_db
from ..services.nrcs_service import NRCSService, nrcs_service
from ..models.schemas import (
    NRCSSystemCreate, NRCSSystemUpdate, NRCSSystemResponse,
    NRCSStoryCreate, NRCSStoryUpdate, NRCSStoryResponse,
    NRCSRundownCreate, NRCSRundownUpdate, NRCSRundownResponse,
    NRCSUserCreate, NRCSUserUpdate, NRCSUserResponse,
    NRCSAssignmentCreate, NRCSAssignmentUpdate, NRCSAssignmentResponse,
    SystemStatusResponse, ServiceHealthResponse,
    SearchRequest, SearchResponse, SyncRequest, SyncResponse
)
from ..db.models import NRCSType
from ..core.config import settings

# Create router
router = APIRouter(prefix="/api/v1", tags=["nrcs-integration"])


# Mock authentication for development
async def get_current_user():
    """Mock current user for development"""
    if settings.development_mode:
        return {
            "id": "00000000-0000-0000-0000-000000000001",
            "username": "dev-user",
            "roles": ["admin"]
        }
    # TODO: Implement proper JWT authentication
    return {"id": "user1", "username": "user", "roles": ["user"]}


# System Management Routes
@router.post("/systems", response_model=NRCSSystemResponse, status_code=status.HTTP_201_CREATED)
async def create_nrcs_system(
    system_data: NRCSSystemCreate,
    db: AsyncSession = Depends(get_db),
    service: NRCSService = Depends(lambda: nrcs_service),
    current_user: dict = Depends(get_current_user)
):
    """Create a new NRCS system"""
    try:
        return await service.create_system(db, system_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/systems", response_model=List[NRCSSystemResponse])
async def list_nrcs_systems(
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of items to return"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    system_type: Optional[NRCSType] = Query(None, description="Filter by system type"),
    db: AsyncSession = Depends(get_db),
    service: NRCSService = Depends(lambda: nrcs_service),
    current_user: dict = Depends(get_current_user)
):
    """List NRCS systems"""
    return await service.list_systems(
        db,
        skip=skip,
        limit=limit,
        is_active=is_active,
        system_type=system_type
    )


@router.get("/systems/{system_id}", response_model=NRCSSystemResponse)
async def get_nrcs_system(
    system_id: UUID,
    db: AsyncSession = Depends(get_db),
    service: NRCSService = Depends(lambda: nrcs_service),
    current_user: dict = Depends(get_current_user)
):
    """Get an NRCS system by ID"""
    system = await service.get_system(db, system_id)
    
    if not system:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="NRCS system not found"
        )
    
    return system


@router.put("/systems/{system_id}", response_model=NRCSSystemResponse)
async def update_nrcs_system(
    system_id: UUID,
    update_data: NRCSSystemUpdate,
    db: AsyncSession = Depends(get_db),
    service: NRCSService = Depends(lambda: nrcs_service),
    current_user: dict = Depends(get_current_user)
):
    """Update an NRCS system"""
    system = await service.update_system(db, system_id, update_data)
    
    if not system:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="NRCS system not found"
        )
    
    return system


@router.delete("/systems/{system_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_nrcs_system(
    system_id: UUID,
    db: AsyncSession = Depends(get_db),
    service: NRCSService = Depends(lambda: nrcs_service),
    current_user: dict = Depends(get_current_user)
):
    """Delete an NRCS system"""
    deleted = await service.delete_system(db, system_id)
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="NRCS system not found"
        )


# Connection Management Routes
@router.post("/systems/{system_id}/connect")
async def connect_nrcs_system(
    system_id: UUID,
    db: AsyncSession = Depends(get_db),
    service: NRCSService = Depends(lambda: nrcs_service),
    current_user: dict = Depends(get_current_user)
):
    """Connect to an NRCS system"""
    try:
        return await service.connect_system(db, system_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/systems/{system_id}/disconnect")
async def disconnect_nrcs_system(
    system_id: UUID,
    db: AsyncSession = Depends(get_db),
    service: NRCSService = Depends(lambda: nrcs_service),
    current_user: dict = Depends(get_current_user)
):
    """Disconnect from an NRCS system"""
    try:
        return await service.disconnect_system(db, system_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/systems/{system_id}/status", response_model=SystemStatusResponse)
async def get_nrcs_system_status(
    system_id: UUID,
    db: AsyncSession = Depends(get_db),
    service: NRCSService = Depends(lambda: nrcs_service),
    current_user: dict = Depends(get_current_user)
):
    """Get detailed system status"""
    try:
        return await service.get_system_status(db, system_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# Synchronization Routes
@router.post("/systems/{system_id}/sync/stories")
async def sync_stories(
    system_id: UUID,
    background_tasks: BackgroundTasks,
    force: bool = Query(False, description="Force full synchronization"),
    db: AsyncSession = Depends(get_db),
    service: NRCSService = Depends(lambda: nrcs_service),
    current_user: dict = Depends(get_current_user)
):
    """Sync stories from NRCS system"""
    try:
        # Run sync in background for large operations
        if force:
            background_tasks.add_task(service.sync_stories, db, system_id, force)
            return {
                "message": "Full story synchronization started in background",
                "system_id": system_id
            }
        else:
            # Quick sync
            result = await service.sync_stories(db, system_id, force)
            return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# Search Routes
@router.post("/search", response_model=SearchResponse)
async def search_content(
    search_request: SearchRequest,
    db: AsyncSession = Depends(get_db),
    service: NRCSService = Depends(lambda: nrcs_service),
    current_user: dict = Depends(get_current_user)
):
    """Search content across NRCS systems"""
    return await service.search_content(db, search_request)


# Placeholder routes for future implementation
@router.get("/stories", response_model=List[NRCSStoryResponse])
async def list_stories(
    system_id: Optional[UUID] = Query(None, description="Filter by system ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """List stories"""
    # TODO: Implement story listing
    return []


@router.get("/rundowns", response_model=List[NRCSRundownResponse])
async def list_rundowns(
    system_id: Optional[UUID] = Query(None, description="Filter by system ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """List rundowns"""
    # TODO: Implement rundown listing
    return []


@router.get("/users", response_model=List[NRCSUserResponse])
async def list_users(
    system_id: Optional[UUID] = Query(None, description="Filter by system ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """List users"""
    # TODO: Implement user listing
    return []


@router.get("/assignments", response_model=List[NRCSAssignmentResponse])
async def list_assignments(
    system_id: Optional[UUID] = Query(None, description="Filter by system ID"),
    assignee_id: Optional[UUID] = Query(None, description="Filter by assignee"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """List assignments"""
    # TODO: Implement assignment listing
    return []


# Health check routes
@router.get("/health", response_model=ServiceHealthResponse)
async def health_check(db: AsyncSession = Depends(get_db)):
    """Service health check"""
    # Test database connection
    try:
        await db.execute("SELECT 1")
        db_status = {"status": "healthy", "message": "Database connection OK"}
    except Exception as e:
        db_status = {"status": "unhealthy", "message": f"Database error: {str(e)}"}
    
    # TODO: Test Redis connection
    redis_status = {"status": "healthy", "message": "Redis not implemented"}
    
    # Overall status
    overall_status = "healthy"
    if db_status["status"] != "healthy":
        overall_status = "unhealthy"
    
    return ServiceHealthResponse(
        status=overall_status,
        service="nrcs-integration",
        version="1.0.0",
        uptime_seconds=0,  # TODO: Calculate actual uptime
        components={
            "database": db_status,
            "redis": redis_status
        },
        system_info={
            "environment": settings.environment,
            "debug": settings.debug
        }
    )


@router.get("/health/detailed")
async def detailed_health_check(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Detailed health check with system information"""
    health_data = {
        "service": "nrcs-integration",
        "version": "1.0.0",
        "status": "healthy",
        "timestamp": "2025-01-01T00:00:00Z",  # TODO: Use actual timestamp
        "checks": {}
    }
    
    # Database check
    try:
        await db.execute("SELECT 1")
        health_data["checks"]["database"] = {
            "status": "healthy",
            "response_time_ms": 5,  # TODO: Measure actual response time
            "message": "Database connection successful"
        }
    except Exception as e:
        health_data["status"] = "degraded"
        health_data["checks"]["database"] = {
            "status": "unhealthy",
            "error": str(e),
            "message": "Database connection failed"
        }
    
    # TODO: Add checks for:
    # - Redis connection
    # - NRCS system connections
    # - Background tasks status
    # - Memory usage
    # - Disk space
    
    return health_data