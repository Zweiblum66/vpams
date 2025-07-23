"""API routes for Broadcast Automation Service"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..services import automation_service
from ..models.schemas import (
    # Device schemas
    DeviceCreate, DeviceUpdate, DeviceResponse, DeviceStatus,
    DevicePresetCreate, DevicePresetUpdate, DevicePresetResponse,
    # Macro schemas
    MacroCreate, MacroUpdate, MacroResponse,
    MacroExecuteRequest, MacroExecutionResponse,
    # Show schemas
    ShowCreate, ShowUpdate, ShowResponse,
    ShowCueCreate, ShowCueUpdate, ShowCueResponse,
    # Command schemas
    DeviceCommand, CommandResponse,
    # Control schemas
    PTZControl, FocusControl, IrisControl,
    AudioFaderControl, SwitcherControl,
    # Schedule schemas
    ScheduledExecutionCreate, ScheduledExecutionUpdate, ScheduledExecutionResponse,
    # Device group schemas
    DeviceGroupCreate, DeviceGroupUpdate, DeviceGroupResponse,
    # Emergency schemas
    EmergencyOverrideRequest, EmergencyOverrideResponse,
    # Discovery schemas
    DiscoveryRequest, DiscoveredDevice,
    # WebSocket schemas
    WSMessage, WSResponse,
    # Pagination
    PaginationParams, PaginatedResponse,
)
from ..db.models import DeviceType
from ..core.config import settings

# Create routers
device_router = APIRouter(prefix="/api/v1/automation/devices", tags=["devices"])
camera_router = APIRouter(prefix="/api/v1/automation/cameras", tags=["cameras"])
switcher_router = APIRouter(prefix="/api/v1/automation/switchers", tags=["switchers"])
audio_router = APIRouter(prefix="/api/v1/automation/audio", tags=["audio"])
macro_router = APIRouter(prefix="/api/v1/automation/macros", tags=["macros"])
show_router = APIRouter(prefix="/api/v1/automation/shows", tags=["shows"])
control_router = APIRouter(prefix="/api/v1/automation/control", tags=["control"])


# Placeholder for current user dependency
async def get_current_user():
    """Get current user (placeholder)"""
    # This would be replaced with actual authentication
    return UUID("00000000-0000-0000-0000-000000000000")


# Device Management Routes

@device_router.post("/", response_model=DeviceResponse, status_code=status.HTTP_201_CREATED)
async def create_device(
    device: DeviceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: UUID = Depends(get_current_user)
):
    """Create new automation device"""
    try:
        return await automation_service.create_device(db, device, current_user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@device_router.get("/", response_model=List[DeviceResponse])
async def list_devices(
    device_type: Optional[DeviceType] = None,
    is_active: Optional[bool] = None,
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """List automation devices"""
    try:
        devices = await automation_service.list_devices(
            db,
            device_type=device_type,
            is_active=is_active,
            skip=pagination.offset,
            limit=pagination.limit
        )
        return devices
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@device_router.get("/{device_id}", response_model=DeviceResponse)
async def get_device(
    device_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get device by ID"""
    try:
        return await automation_service.get_device(db, device_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@device_router.put("/{device_id}", response_model=DeviceResponse)
async def update_device(
    device_id: UUID,
    device: DeviceUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update device configuration"""
    try:
        return await automation_service.update_device(db, device_id, device)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@device_router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_device(
    device_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Delete device"""
    try:
        await automation_service.delete_device(db, device_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@device_router.post("/{device_id}/connect")
async def connect_device(
    device_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Connect to device"""
    try:
        success = await automation_service.connect_device(db, device_id)
        return {"connected": success}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@device_router.post("/{device_id}/disconnect", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_device(
    device_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Disconnect from device"""
    try:
        await automation_service.disconnect_device(db, device_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@device_router.get("/{device_id}/status")
async def get_device_status(
    device_id: UUID
):
    """Get device status"""
    try:
        return await automation_service.get_device_status(device_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@device_router.post("/discover", response_model=List[DiscoveredDevice])
async def discover_devices(
    request: DiscoveryRequest
):
    """Discover devices on network"""
    try:
        return await automation_service.discover_devices(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Device Preset Routes

@device_router.post("/{device_id}/presets", response_model=DevicePresetResponse, status_code=status.HTTP_201_CREATED)
async def save_preset(
    device_id: UUID,
    preset: DevicePresetCreate,
    db: AsyncSession = Depends(get_db),
    current_user: UUID = Depends(get_current_user)
):
    """Save device preset"""
    try:
        preset.device_id = device_id
        return await automation_service.save_device_preset(db, preset, current_user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@device_router.post("/{device_id}/presets/{preset_id}/recall", response_model=CommandResponse)
async def recall_preset(
    device_id: UUID,
    preset_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: UUID = Depends(get_current_user)
):
    """Recall device preset"""
    try:
        return await automation_service.recall_device_preset(db, device_id, preset_id, current_user)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Camera Control Routes

@camera_router.get("/", response_model=List[DeviceResponse])
async def list_cameras(
    is_active: Optional[bool] = None,
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """List camera devices"""
    try:
        devices = await automation_service.list_devices(
            db,
            device_type=DeviceType.CAMERA,
            is_active=is_active,
            skip=pagination.offset,
            limit=pagination.limit
        )
        return devices
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@camera_router.post("/{camera_id}/ptz", response_model=CommandResponse)
async def control_ptz(
    camera_id: UUID,
    control: PTZControl,
    db: AsyncSession = Depends(get_db),
    current_user: UUID = Depends(get_current_user)
):
    """Control camera PTZ"""
    try:
        return await automation_service.control_ptz(db, camera_id, control, current_user)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@camera_router.post("/{camera_id}/focus", response_model=CommandResponse)
async def control_focus(
    camera_id: UUID,
    control: FocusControl,
    db: AsyncSession = Depends(get_db),
    current_user: UUID = Depends(get_current_user)
):
    """Control camera focus"""
    try:
        return await automation_service.control_focus(db, camera_id, control, current_user)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@camera_router.post("/{camera_id}/iris", response_model=CommandResponse)
async def control_iris(
    camera_id: UUID,
    control: IrisControl,
    db: AsyncSession = Depends(get_db),
    current_user: UUID = Depends(get_current_user)
):
    """Control camera iris"""
    try:
        command = DeviceCommand(
            device_id=camera_id,
            command="iris",
            parameters=control.model_dump(exclude_unset=True)
        )
        return await automation_service.send_device_command(db, command, current_user)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Switcher Control Routes

@switcher_router.get("/", response_model=List[DeviceResponse])
async def list_switchers(
    is_active: Optional[bool] = None,
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """List switcher devices"""
    try:
        devices = await automation_service.list_devices(
            db,
            device_type=DeviceType.SWITCHER,
            is_active=is_active,
            skip=pagination.offset,
            limit=pagination.limit
        )
        return devices
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@switcher_router.post("/{switcher_id}/take", response_model=CommandResponse)
async def switcher_take(
    switcher_id: UUID,
    control: SwitcherControl,
    db: AsyncSession = Depends(get_db),
    current_user: UUID = Depends(get_current_user)
):
    """Execute switcher take transition"""
    try:
        control.transition_type = "take"
        return await automation_service.control_switcher(db, switcher_id, control, current_user)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@switcher_router.post("/{switcher_id}/auto", response_model=CommandResponse)
async def switcher_auto(
    switcher_id: UUID,
    control: SwitcherControl,
    db: AsyncSession = Depends(get_db),
    current_user: UUID = Depends(get_current_user)
):
    """Execute switcher auto transition"""
    try:
        control.transition_type = "auto"
        return await automation_service.control_switcher(db, switcher_id, control, current_user)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@switcher_router.post("/{switcher_id}/cut", response_model=CommandResponse)
async def switcher_cut(
    switcher_id: UUID,
    control: SwitcherControl,
    db: AsyncSession = Depends(get_db),
    current_user: UUID = Depends(get_current_user)
):
    """Execute switcher cut"""
    try:
        control.transition_type = "cut"
        control.duration = 0
        return await automation_service.control_switcher(db, switcher_id, control, current_user)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Audio Control Routes

@audio_router.get("/mixers", response_model=List[DeviceResponse])
async def list_audio_mixers(
    is_active: Optional[bool] = None,
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """List audio mixer devices"""
    try:
        devices = await automation_service.list_devices(
            db,
            device_type=DeviceType.AUDIO_MIXER,
            is_active=is_active,
            skip=pagination.offset,
            limit=pagination.limit
        )
        return devices
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@audio_router.post("/mixers/{mixer_id}/fader", response_model=CommandResponse)
async def control_audio_fader(
    mixer_id: UUID,
    control: AudioFaderControl,
    db: AsyncSession = Depends(get_db),
    current_user: UUID = Depends(get_current_user)
):
    """Control audio fader"""
    try:
        return await automation_service.control_audio_fader(db, mixer_id, control, current_user)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@audio_router.post("/mixers/{mixer_id}/mute", response_model=CommandResponse)
async def mute_audio_channel(
    mixer_id: UUID,
    channel: str = Query(..., description="Channel to mute"),
    mute: bool = Query(True, description="Mute state"),
    db: AsyncSession = Depends(get_db),
    current_user: UUID = Depends(get_current_user)
):
    """Mute/unmute audio channel"""
    try:
        command = DeviceCommand(
            device_id=mixer_id,
            command="mute",
            parameters={"channel": channel, "mute": mute}
        )
        return await automation_service.send_device_command(db, command, current_user)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Macro Management Routes

@macro_router.post("/", response_model=MacroResponse, status_code=status.HTTP_201_CREATED)
async def create_macro(
    macro: MacroCreate,
    db: AsyncSession = Depends(get_db),
    current_user: UUID = Depends(get_current_user)
):
    """Create new automation macro"""
    try:
        return await automation_service.create_macro(db, macro, current_user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@macro_router.get("/", response_model=List[MacroResponse])
async def list_macros(
    category: Optional[str] = None,
    is_active: Optional[bool] = None,
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """List automation macros"""
    # Implementation would query macros with filters
    return []


@macro_router.get("/{macro_id}", response_model=MacroResponse)
async def get_macro(
    macro_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get macro by ID"""
    # Implementation would get macro details
    raise HTTPException(status_code=501, detail="Not implemented")


@macro_router.put("/{macro_id}", response_model=MacroResponse)
async def update_macro(
    macro_id: UUID,
    macro: MacroUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update macro"""
    # Implementation would update macro
    raise HTTPException(status_code=501, detail="Not implemented")


@macro_router.delete("/{macro_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_macro(
    macro_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Delete macro"""
    # Implementation would delete macro
    raise HTTPException(status_code=501, detail="Not implemented")


@macro_router.post("/{macro_id}/execute", response_model=MacroExecutionResponse)
async def execute_macro(
    macro_id: UUID,
    request: MacroExecuteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UUID = Depends(get_current_user)
):
    """Execute automation macro"""
    try:
        return await automation_service.execute_macro(db, macro_id, request, current_user)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@macro_router.get("/{macro_id}/history", response_model=List[MacroExecutionResponse])
async def get_macro_history(
    macro_id: UUID,
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """Get macro execution history"""
    # Implementation would query execution history
    return []


# Show Control Routes

@show_router.post("/", response_model=ShowResponse, status_code=status.HTTP_201_CREATED)
async def create_show(
    show: ShowCreate,
    db: AsyncSession = Depends(get_db),
    current_user: UUID = Depends(get_current_user)
):
    """Create new show"""
    try:
        return await automation_service.create_show(db, show, current_user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@show_router.get("/", response_model=List[ShowResponse])
async def list_shows(
    show_type: Optional[str] = None,
    is_active: Optional[bool] = None,
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """List shows"""
    # Implementation would query shows with filters
    return []


@show_router.get("/{show_id}", response_model=ShowResponse)
async def get_show(
    show_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get show by ID"""
    # Implementation would get show details
    raise HTTPException(status_code=501, detail="Not implemented")


@show_router.put("/{show_id}", response_model=ShowResponse)
async def update_show(
    show_id: UUID,
    show: ShowUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update show"""
    # Implementation would update show
    raise HTTPException(status_code=501, detail="Not implemented")


@show_router.post("/{show_id}/cues", response_model=ShowCueResponse, status_code=status.HTTP_201_CREATED)
async def add_show_cue(
    show_id: UUID,
    cue: ShowCueCreate,
    db: AsyncSession = Depends(get_db)
):
    """Add cue to show"""
    try:
        cue.show_id = show_id
        # Implementation would create cue
        raise HTTPException(status_code=501, detail="Not implemented")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@show_router.get("/{show_id}/cues", response_model=List[ShowCueResponse])
async def list_show_cues(
    show_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """List show cues"""
    # Implementation would query cues
    return []


@show_router.post("/{show_id}/go")
async def show_go(
    show_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: UUID = Depends(get_current_user)
):
    """Advance to next cue in show"""
    try:
        return await automation_service.show_go(show_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@show_router.post("/{show_id}/stop", status_code=status.HTTP_204_NO_CONTENT)
async def stop_show(
    show_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Stop running show"""
    try:
        await automation_service.stop_show(show_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@show_router.post("/{show_id}/rehearse")
async def rehearse_show(
    show_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: UUID = Depends(get_current_user)
):
    """Run show in rehearsal mode"""
    try:
        return await automation_service.run_show(db, show_id, rehearsal=True, user_id=current_user)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Control Routes

@control_router.post("/command", response_model=CommandResponse)
async def send_command(
    command: DeviceCommand,
    db: AsyncSession = Depends(get_db),
    current_user: UUID = Depends(get_current_user)
):
    """Send command to device"""
    try:
        return await automation_service.send_device_command(db, command, current_user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@control_router.post("/emergency/stop", response_model=EmergencyOverrideResponse)
async def emergency_stop(
    request: EmergencyOverrideRequest,
    current_user: UUID = Depends(get_current_user)
):
    """Emergency stop all automation"""
    try:
        # Verify emergency PIN if configured
        if settings.emergency_override_pin:
            if request.pin != settings.emergency_override_pin:
                raise HTTPException(status_code=403, detail="Invalid emergency PIN")
                
        return await automation_service.emergency_stop(request.reason, current_user)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@control_router.post("/emergency/release", status_code=status.HTTP_204_NO_CONTENT)
async def release_emergency(
    current_user: UUID = Depends(get_current_user)
):
    """Release emergency override"""
    try:
        await automation_service.release_emergency_override(current_user)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# WebSocket endpoint for real-time control
@control_router.websocket("/ws")
async def websocket_control(
    websocket: WebSocket,
    db: AsyncSession = Depends(get_db)
):
    """WebSocket endpoint for real-time device control"""
    await websocket.accept()
    
    try:
        while True:
            # Receive message
            data = await websocket.receive_json()
            message = WSMessage(**data)
            
            try:
                # Process message based on type
                if message.type == "control":
                    # Send device command
                    device = await automation_service.get_device_by_slug(db, message.device)
                    command = DeviceCommand(
                        device_id=device.id,
                        command=message.command,
                        parameters=message.params or {}
                    )
                    response = await automation_service.send_device_command(
                        db,
                        command,
                        UUID("00000000-0000-0000-0000-000000000000")  # WebSocket user
                    )
                    
                    # Send response
                    ws_response = WSResponse(
                        type="response",
                        request_id=message.request_id,
                        status="success",
                        data={
                            "command_id": str(response.command_id),
                            "status": response.status
                        }
                    )
                    await websocket.send_json(ws_response.model_dump())
                    
                elif message.type == "status":
                    # Get device status
                    device = await automation_service.get_device_by_slug(db, message.device)
                    status = await automation_service.get_device_status(device.id)
                    
                    # Send response
                    ws_response = WSResponse(
                        type="status",
                        request_id=message.request_id,
                        status="success",
                        data=status
                    )
                    await websocket.send_json(ws_response.model_dump())
                    
                else:
                    # Unknown message type
                    ws_response = WSResponse(
                        type="error",
                        request_id=message.request_id,
                        status="error",
                        error=f"Unknown message type: {message.type}"
                    )
                    await websocket.send_json(ws_response.model_dump())
                    
            except Exception as e:
                # Send error response
                ws_response = WSResponse(
                    type="error",
                    request_id=message.request_id,
                    status="error",
                    error=str(e)
                )
                await websocket.send_json(ws_response.model_dump())
                
    except Exception as e:
        await websocket.close(code=1000)