"""Main API routes for playout integration service"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.base import get_db
from ..services.playout_service import PlayoutService
from ..models.schemas import (
    # System schemas
    PlayoutSystemCreate, PlayoutSystemUpdate, PlayoutSystemResponse,
    SystemStatus,
    
    # Device schemas  
    DeviceCreate, DeviceUpdate, DeviceResponse, DeviceCommand,
    
    # Schedule schemas
    ScheduleCreate, ScheduleUpdate, ScheduleResponse,
    ScheduleItemCreate, ScheduleItemUpdate, ScheduleItemResponse,
    ScheduleValidation,
    
    # Transfer schemas
    TransferCreate, TransferUpdate, TransferResponse, TransferProgress,
    
    # Alert schemas
    AlertCreate, AlertResponse,
    
    # Control schemas
    LoadCommand, PlayCommand,
    
    # Import/Export
    BXFImport, ScheduleExport,
    
    # As-Run
    AsRunEntry, AsRunResponse
)
from ..db.models import PlayoutSystemType, PlayoutProtocol
from .dependencies import (
    get_current_user, get_current_admin_user, get_playout_service,
    CommonQueryParams, validate_uuid
)

# Create router
router = APIRouter(prefix="/api/v1", tags=["playout-integration"])


# System Management Routes
@router.post("/systems", response_model=PlayoutSystemResponse, status_code=status.HTTP_201_CREATED)
async def create_playout_system(
    system_data: PlayoutSystemCreate,
    db: AsyncSession = Depends(get_db),
    service: PlayoutService = Depends(get_playout_service),
    current_user: dict = Depends(get_current_admin_user)
):
    """Create a new playout system"""
    try:
        return await service.create_system(db, system_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/systems", response_model=List[PlayoutSystemResponse])
async def list_playout_systems(
    params: CommonQueryParams = Depends(),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    system_type: Optional[PlayoutSystemType] = Query(None, description="Filter by system type"),
    db: AsyncSession = Depends(get_db),
    service: PlayoutService = Depends(get_playout_service),
    current_user: dict = Depends(get_current_user)
):
    """List playout systems"""
    return await service.list_systems(
        db, 
        skip=params.skip,
        limit=params.limit,
        is_active=is_active,
        system_type=system_type
    )


@router.get("/systems/{system_id}", response_model=PlayoutSystemResponse)
async def get_playout_system(
    system_id: str,
    db: AsyncSession = Depends(get_db),
    service: PlayoutService = Depends(get_playout_service),
    current_user: dict = Depends(get_current_user)
):
    """Get a playout system by ID"""
    system_uuid = validate_uuid(system_id, "system ID")
    system = await service.get_system(db, UUID(system_uuid))
    
    if not system:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Playout system not found"
        )
    
    return system


@router.put("/systems/{system_id}", response_model=PlayoutSystemResponse)
async def update_playout_system(
    system_id: str,
    update_data: PlayoutSystemUpdate,
    db: AsyncSession = Depends(get_db),
    service: PlayoutService = Depends(get_playout_service),
    current_user: dict = Depends(get_current_admin_user)
):
    """Update a playout system"""
    system_uuid = validate_uuid(system_id, "system ID")
    system = await service.update_system(db, UUID(system_uuid), update_data)
    
    if not system:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Playout system not found"
        )
    
    return system


@router.delete("/systems/{system_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_playout_system(
    system_id: str,
    db: AsyncSession = Depends(get_db),
    service: PlayoutService = Depends(get_playout_service),
    current_user: dict = Depends(get_current_admin_user)
):
    """Delete a playout system"""
    system_uuid = validate_uuid(system_id, "system ID")
    deleted = await service.delete_system(db, UUID(system_uuid))
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Playout system not found"
        )


@router.post("/systems/{system_id}/test-connection")
async def test_system_connection(
    system_id: str,
    db: AsyncSession = Depends(get_db),
    service: PlayoutService = Depends(get_playout_service),
    current_user: dict = Depends(get_current_user)
):
    """Test connection to playout system"""
    system_uuid = validate_uuid(system_id, "system ID")
    try:
        return await service.test_connection(db, UUID(system_uuid))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/systems/{system_id}/status", response_model=SystemStatus)
async def get_system_status(
    system_id: str,
    db: AsyncSession = Depends(get_db),
    service: PlayoutService = Depends(get_playout_service),
    current_user: dict = Depends(get_current_user)
):
    """Get detailed system status"""
    system_uuid = validate_uuid(system_id, "system ID")
    try:
        return await service.get_system_status(db, UUID(system_uuid))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# Device Management Routes
@router.post("/devices", response_model=DeviceResponse, status_code=status.HTTP_201_CREATED)
async def create_device(
    device_data: DeviceCreate,
    db: AsyncSession = Depends(get_db),
    service: PlayoutService = Depends(get_playout_service),
    current_user: dict = Depends(get_current_admin_user)
):
    """Create a new playout device"""
    try:
        return await service.create_device(db, device_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/devices/{device_id}", response_model=DeviceResponse)
async def update_device(
    device_id: str,
    update_data: DeviceUpdate,
    db: AsyncSession = Depends(get_db),
    service: PlayoutService = Depends(get_playout_service),
    current_user: dict = Depends(get_current_admin_user)
):
    """Update a device"""
    device_uuid = validate_uuid(device_id, "device ID")
    device = await service.update_device(db, UUID(device_uuid), update_data)
    
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    
    return device


@router.delete("/devices/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_device(
    device_id: str,
    db: AsyncSession = Depends(get_db),
    service: PlayoutService = Depends(get_playout_service),
    current_user: dict = Depends(get_current_admin_user)
):
    """Delete a device"""
    device_uuid = validate_uuid(device_id, "device ID")
    deleted = await service.delete_device(db, UUID(device_uuid))
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )


@router.get("/devices/{device_id}/status", response_model=DeviceResponse)
async def get_device_status(
    device_id: str,
    db: AsyncSession = Depends(get_db),
    service: PlayoutService = Depends(get_playout_service),
    current_user: dict = Depends(get_current_user)
):
    """Get device status"""
    device_uuid = validate_uuid(device_id, "device ID")
    device = await service.get_device_status(db, UUID(device_uuid))
    
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    
    return device


@router.post("/devices/{device_id}/control")
async def control_device(
    device_id: str,
    command: DeviceCommand,
    db: AsyncSession = Depends(get_db),
    service: PlayoutService = Depends(get_playout_service),
    current_user: dict = Depends(get_current_user)
):
    """Send control command to device"""
    device_uuid = validate_uuid(device_id, "device ID")
    try:
        return await service.control_device(db, UUID(device_uuid), command)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# Schedule Management Routes (placeholder implementations)
@router.post("/schedules", response_model=ScheduleResponse, status_code=status.HTTP_201_CREATED)
async def create_schedule(
    schedule_data: ScheduleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create a new schedule"""
    # TODO: Implement schedule creation
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Schedule management not yet implemented"
    )


@router.get("/schedules", response_model=List[ScheduleResponse])
async def list_schedules(
    params: CommonQueryParams = Depends(),
    system_id: Optional[str] = Query(None, description="Filter by system ID"),
    channel: Optional[int] = Query(None, description="Filter by channel"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """List schedules"""
    # TODO: Implement schedule listing
    return []


# Transfer Management Routes (placeholder implementations)
@router.post("/transfers", response_model=TransferResponse, status_code=status.HTTP_201_CREATED)
async def create_transfer(
    transfer_data: TransferCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create a new content transfer"""
    # TODO: Implement transfer creation
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Transfer management not yet implemented"
    )


@router.get("/transfers", response_model=List[TransferResponse])
async def list_transfers(
    params: CommonQueryParams = Depends(),
    system_id: Optional[str] = Query(None, description="Filter by system ID"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """List transfers"""
    # TODO: Implement transfer listing
    return []


@router.get("/transfers/{transfer_id}/progress", response_model=TransferProgress)
async def get_transfer_progress(
    transfer_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get transfer progress"""
    # TODO: Implement transfer progress
    transfer_uuid = validate_uuid(transfer_id, "transfer ID")
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Transfer progress not yet implemented"
    )


# Alert Management Routes (placeholder implementations)
@router.get("/alerts", response_model=List[AlertResponse])
async def list_alerts(
    params: CommonQueryParams = Depends(),
    system_id: Optional[str] = Query(None, description="Filter by system ID"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    is_resolved: Optional[bool] = Query(None, description="Filter by resolution status"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """List system alerts"""
    # TODO: Implement alert listing
    return []


@router.post("/alerts/{alert_id}/acknowledge", status_code=status.HTTP_204_NO_CONTENT)
async def acknowledge_alert(
    alert_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Acknowledge an alert"""
    alert_uuid = validate_uuid(alert_id, "alert ID")
    # TODO: Implement alert acknowledgment
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Alert management not yet implemented"
    )


# As-Run Log Routes (placeholder implementations)
@router.get("/systems/{system_id}/asrun", response_model=List[AsRunResponse])
async def get_asrun_logs(
    system_id: str,
    params: CommonQueryParams = Depends(),
    channel: Optional[int] = Query(None, description="Filter by channel"),
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get as-run logs for a system"""
    system_uuid = validate_uuid(system_id, "system ID")
    # TODO: Implement as-run log retrieval
    return []


# Import/Export Routes (placeholder implementations)
@router.post("/import/bxf")
async def import_bxf_schedule(
    import_data: BXFImport,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Import BXF schedule"""
    # TODO: Implement BXF import
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="BXF import not yet implemented"
    )


@router.post("/schedules/{schedule_id}/export")
async def export_schedule(
    schedule_id: str,
    export_data: ScheduleExport,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Export schedule in various formats"""
    schedule_uuid = validate_uuid(schedule_id, "schedule ID")
    # TODO: Implement schedule export
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Schedule export not yet implemented"
    )


# Health check routes
@router.get("/health")
async def health_check():
    """Service health check"""
    return {
        "status": "healthy",
        "service": "playout-integration",
        "version": "1.0.0"
    }


@router.get("/health/detailed")
async def detailed_health_check(
    db: AsyncSession = Depends(get_db)
):
    """Detailed health check with dependencies"""
    health_status = {
        "status": "healthy",
        "service": "playout-integration",
        "version": "1.0.0",
        "checks": {}
    }
    
    # Database check
    try:
        await db.execute("SELECT 1")
        health_status["checks"]["database"] = "healthy"
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["checks"]["database"] = {"status": "unhealthy", "error": str(e)}
    
    return health_status