"""Main automation service for device control and macro execution"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from uuid import UUID
import json

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_, func
from sqlalchemy.orm import selectinload

from ..db.models import (
    Device, DevicePreset, Macro, MacroExecution,
    Show, ShowCue, CommandLog, ScheduledExecution,
    DeviceGroup, EmergencyOverride,
    DeviceType, DeviceStatus, ConnectionType,
    MacroStatus, CueStatus
)
from ..models.schemas import (
    DeviceCreate, DeviceUpdate, DeviceResponse,
    DevicePresetCreate, DevicePresetUpdate,
    MacroCreate, MacroUpdate, MacroExecuteRequest,
    ShowCreate, ShowUpdate, ShowCueCreate, ShowCueUpdate,
    DeviceCommand, CommandResponse,
    PTZControl, FocusControl, IrisControl,
    AudioFaderControl, SwitcherControl,
    ScheduledExecutionCreate, ScheduledExecutionUpdate,
    DeviceGroupCreate, DeviceGroupUpdate,
    EmergencyOverrideRequest,
    DiscoveryRequest, DiscoveredDevice,
)
from ..protocols import ProtocolRegistry, BaseProtocolAdapter
from ..core.config import settings

logger = logging.getLogger(__name__)


class AutomationService:
    """Main automation service for device control and workflow execution"""
    
    def __init__(self):
        """Initialize automation service"""
        self._device_adapters: Dict[UUID, BaseProtocolAdapter] = {}
        self._active_macros: Dict[str, MacroExecution] = {}
        self._active_shows: Dict[UUID, Dict[str, Any]] = {}
        self._emergency_override = False
        self._shutdown = False
        self._tasks: List[asyncio.Task] = []
        
    async def initialize(self) -> None:
        """Initialize service and connect to devices"""
        logger.info("Initializing automation service")
        
        # Start background tasks
        if settings.enable_auto_discovery:
            task = asyncio.create_task(self._discovery_loop())
            self._tasks.append(task)
            
        if settings.enable_device_monitoring:
            task = asyncio.create_task(self._monitoring_loop())
            self._tasks.append(task)
            
        # Start macro scheduler
        task = asyncio.create_task(self._scheduler_loop())
        self._tasks.append(task)
        
    async def shutdown(self) -> None:
        """Shutdown service and disconnect devices"""
        logger.info("Shutting down automation service")
        self._shutdown = True
        
        # Stop all macros and shows
        await self.emergency_stop("System shutdown")
        
        # Disconnect all devices
        for adapter in self._device_adapters.values():
            await adapter.shutdown()
            
        # Cancel background tasks
        for task in self._tasks:
            task.cancel()
            
        await asyncio.gather(*self._tasks, return_exceptions=True)
        
    # Device Management
    
    async def create_device(
        self,
        db: AsyncSession,
        device_data: DeviceCreate,
        user_id: UUID
    ) -> DeviceResponse:
        """Create new device"""
        # Check if slug already exists
        existing = await db.execute(
            select(Device).where(Device.slug == device_data.slug)
        )
        if existing.scalar():
            raise ValueError(f"Device with slug '{device_data.slug}' already exists")
            
        # Create device
        device = Device(
            **device_data.model_dump(exclude={"username", "password", "api_key"}),
            created_by=user_id
        )
        
        # Encrypt credentials if provided
        if device_data.username:
            device.username = device_data.username  # Should be encrypted in production
        if device_data.password:
            device.password = device_data.password  # Should be encrypted in production
        if device_data.api_key:
            device.api_key = device_data.api_key    # Should be encrypted in production
            
        db.add(device)
        await db.commit()
        await db.refresh(device)
        
        # Connect to device if active
        if device.is_active:
            await self.connect_device(db, device.id)
            
        return DeviceResponse.model_validate(device)
        
    async def update_device(
        self,
        db: AsyncSession,
        device_id: UUID,
        device_data: DeviceUpdate
    ) -> DeviceResponse:
        """Update device configuration"""
        # Get device
        result = await db.execute(
            select(Device).where(Device.id == device_id)
        )
        device = result.scalar_one_or_none()
        if not device:
            raise ValueError("Device not found")
            
        # Disconnect if connected
        if device_id in self._device_adapters:
            await self.disconnect_device(db, device_id)
            
        # Update device
        update_data = device_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(device, field, value)
            
        device.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(device)
        
        # Reconnect if active
        if device.is_active:
            await self.connect_device(db, device.id)
            
        return DeviceResponse.model_validate(device)
        
    async def delete_device(
        self,
        db: AsyncSession,
        device_id: UUID
    ) -> None:
        """Delete device"""
        # Disconnect first
        if device_id in self._device_adapters:
            await self.disconnect_device(db, device_id)
            
        # Delete device
        await db.execute(
            delete(Device).where(Device.id == device_id)
        )
        await db.commit()
        
    async def get_device(
        self,
        db: AsyncSession,
        device_id: UUID
    ) -> DeviceResponse:
        """Get device by ID"""
        result = await db.execute(
            select(Device).where(Device.id == device_id)
        )
        device = result.scalar_one_or_none()
        if not device:
            raise ValueError("Device not found")
            
        return DeviceResponse.model_validate(device)
        
    async def list_devices(
        self,
        db: AsyncSession,
        device_type: Optional[DeviceType] = None,
        is_active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[DeviceResponse]:
        """List devices with filters"""
        query = select(Device)
        
        # Apply filters
        if device_type:
            query = query.where(Device.device_type == device_type)
        if is_active is not None:
            query = query.where(Device.is_active == is_active)
            
        # Execute query
        result = await db.execute(
            query.offset(skip).limit(limit).order_by(Device.name)
        )
        devices = result.scalars().all()
        
        return [DeviceResponse.model_validate(device) for device in devices]
        
    async def connect_device(
        self,
        db: AsyncSession,
        device_id: UUID
    ) -> bool:
        """Connect to device"""
        # Get device
        result = await db.execute(
            select(Device).where(Device.id == device_id)
        )
        device = result.scalar_one_or_none()
        if not device:
            raise ValueError("Device not found")
            
        # Check if already connected
        if device_id in self._device_adapters:
            return True
            
        try:
            # Get protocol adapter
            adapter = ProtocolRegistry.get_adapter(device.protocol, device)
            
            # Initialize adapter
            await adapter.initialize()
            
            # Connect to device
            if await adapter.connect():
                self._device_adapters[device_id] = adapter
                
                # Update device status
                device.status = DeviceStatus.ONLINE
                device.last_seen = datetime.utcnow()
                device.last_error = None
                device.error_count = 0
                
                # Get capabilities
                device.capabilities = await adapter.get_capabilities()
                
                await db.commit()
                
                logger.info(f"Connected to device: {device.name}")
                return True
            else:
                raise Exception("Failed to connect")
                
        except Exception as e:
            # Update error status
            device.status = DeviceStatus.ERROR
            device.last_error = str(e)
            device.error_count += 1
            await db.commit()
            
            logger.error(f"Failed to connect to device {device.name}: {e}")
            return False
            
    async def disconnect_device(
        self,
        db: AsyncSession,
        device_id: UUID
    ) -> None:
        """Disconnect from device"""
        if device_id not in self._device_adapters:
            return
            
        try:
            # Get adapter
            adapter = self._device_adapters[device_id]
            
            # Shutdown adapter
            await adapter.shutdown()
            
            # Remove from active adapters
            del self._device_adapters[device_id]
            
            # Update device status
            result = await db.execute(
                select(Device).where(Device.id == device_id)
            )
            device = result.scalar_one_or_none()
            if device:
                device.status = DeviceStatus.OFFLINE
                await db.commit()
                
            logger.info(f"Disconnected from device: {device_id}")
            
        except Exception as e:
            logger.error(f"Error disconnecting device: {e}")
            
    async def get_device_status(
        self,
        device_id: UUID
    ) -> Dict[str, Any]:
        """Get device status"""
        if device_id not in self._device_adapters:
            return {
                "status": DeviceStatus.OFFLINE,
                "connected": False,
                "error": "Device not connected"
            }
            
        adapter = self._device_adapters[device_id]
        status = await adapter.get_status()
        connection_info = adapter.get_connection_info()
        
        return {
            "status": status.status,
            "connected": await adapter.is_connected(),
            "connection": connection_info,
            "last_seen": status.last_seen,
            "error": status.last_error,
        }
        
    # Device Control
    
    async def send_device_command(
        self,
        db: AsyncSession,
        command: DeviceCommand,
        user_id: UUID
    ) -> CommandResponse:
        """Send command to device"""
        # Check emergency override
        if self._emergency_override:
            raise Exception("Emergency override active - commands blocked")
            
        # Get adapter
        if command.device_id not in self._device_adapters:
            raise ValueError("Device not connected")
            
        adapter = self._device_adapters[command.device_id]
        
        # Validate command
        if not adapter.validate_command(command.command):
            raise ValueError(f"Unsupported command: {command.command}")
            
        # Validate parameters
        valid, error = adapter.validate_parameters(command.command, command.parameters)
        if not valid:
            raise ValueError(f"Invalid parameters: {error}")
            
        # Create command log
        log = CommandLog(
            device_id=command.device_id,
            command=command.command,
            parameters=command.parameters,
            status="sent",
            sent_at=datetime.utcnow(),
            source="manual",
            user_id=user_id,
        )
        db.add(log)
        await db.commit()
        
        try:
            # Send command
            response = await adapter.send_command(
                command.command,
                command.parameters,
                timeout=command.timeout
            )
            
            # Update log
            log.status = response.status
            log.acknowledged_at = response.acknowledged_at
            log.completed_at = response.completed_at
            log.response_data = response.response_data
            log.error_message = response.error_message
            await db.commit()
            
            return response
            
        except Exception as e:
            # Update log with error
            log.status = "failed"
            log.completed_at = datetime.utcnow()
            log.error_message = str(e)
            await db.commit()
            raise
            
    async def control_ptz(
        self,
        db: AsyncSession,
        device_id: UUID,
        control: PTZControl,
        user_id: UUID
    ) -> CommandResponse:
        """Control camera PTZ"""
        parameters = control.model_dump(exclude_unset=True)
        
        command = DeviceCommand(
            device_id=device_id,
            command="ptz",
            parameters=parameters
        )
        
        return await self.send_device_command(db, command, user_id)
        
    async def control_focus(
        self,
        db: AsyncSession,
        device_id: UUID,
        control: FocusControl,
        user_id: UUID
    ) -> CommandResponse:
        """Control camera focus"""
        parameters = control.model_dump(exclude_unset=True)
        
        command = DeviceCommand(
            device_id=device_id,
            command="focus",
            parameters=parameters
        )
        
        return await self.send_device_command(db, command, user_id)
        
    async def control_audio_fader(
        self,
        db: AsyncSession,
        device_id: UUID,
        control: AudioFaderControl,
        user_id: UUID
    ) -> CommandResponse:
        """Control audio fader"""
        parameters = control.model_dump()
        
        command = DeviceCommand(
            device_id=device_id,
            command="fader",
            parameters=parameters
        )
        
        return await self.send_device_command(db, command, user_id)
        
    async def control_switcher(
        self,
        db: AsyncSession,
        device_id: UUID,
        control: SwitcherControl,
        user_id: UUID
    ) -> CommandResponse:
        """Control switcher"""
        parameters = control.model_dump()
        
        command = DeviceCommand(
            device_id=device_id,
            command=control.transition_type,
            parameters=parameters
        )
        
        return await self.send_device_command(db, command, user_id)
        
    # Preset Management
    
    async def save_device_preset(
        self,
        db: AsyncSession,
        preset_data: DevicePresetCreate,
        user_id: UUID
    ) -> DevicePresetResponse:
        """Save device preset"""
        # Check if preset number already exists
        existing = await db.execute(
            select(DevicePreset).where(
                and_(
                    DevicePreset.device_id == preset_data.device_id,
                    DevicePreset.preset_number == preset_data.preset_number
                )
            )
        )
        if existing.scalar():
            raise ValueError(f"Preset {preset_data.preset_number} already exists")
            
        # Get current device state if connected
        if preset_data.device_id in self._device_adapters:
            adapter = self._device_adapters[preset_data.device_id]
            # Get current state from device
            # This would be device-specific implementation
            
        # Create preset
        preset = DevicePreset(**preset_data.model_dump())
        db.add(preset)
        await db.commit()
        await db.refresh(preset)
        
        return DevicePresetResponse.model_validate(preset)
        
    async def recall_device_preset(
        self,
        db: AsyncSession,
        device_id: UUID,
        preset_id: UUID,
        user_id: UUID
    ) -> CommandResponse:
        """Recall device preset"""
        # Get preset
        result = await db.execute(
            select(DevicePreset).where(
                and_(
                    DevicePreset.id == preset_id,
                    DevicePreset.device_id == device_id
                )
            )
        )
        preset = result.scalar_one_or_none()
        if not preset:
            raise ValueError("Preset not found")
            
        # Send preset data to device
        command = DeviceCommand(
            device_id=device_id,
            command="recall_preset",
            parameters={
                "preset_number": preset.preset_number,
                "preset_data": preset.preset_data
            }
        )
        
        response = await self.send_device_command(db, command, user_id)
        
        # Update preset usage
        preset.last_used = datetime.utcnow()
        preset.use_count += 1
        await db.commit()
        
        return response
        
    # Macro Management
    
    async def create_macro(
        self,
        db: AsyncSession,
        macro_data: MacroCreate,
        user_id: UUID
    ) -> MacroResponse:
        """Create new macro"""
        # Check if slug already exists
        existing = await db.execute(
            select(Macro).where(Macro.slug == macro_data.slug)
        )
        if existing.scalar():
            raise ValueError(f"Macro with slug '{macro_data.slug}' already exists")
            
        # Validate macro actions
        for action in macro_data.actions:
            if "device" in action:
                # Verify device exists
                device_result = await db.execute(
                    select(Device).where(Device.slug == action["device"])
                )
                if not device_result.scalar():
                    raise ValueError(f"Device '{action['device']}' not found")
                    
        # Create macro
        macro = Macro(
            **macro_data.model_dump(),
            created_by=user_id
        )
        db.add(macro)
        await db.commit()
        await db.refresh(macro)
        
        return MacroResponse.model_validate(macro)
        
    async def execute_macro(
        self,
        db: AsyncSession,
        macro_id: UUID,
        request: MacroExecuteRequest,
        user_id: UUID
    ) -> MacroExecutionResponse:
        """Execute macro"""
        # Check emergency override
        if self._emergency_override:
            raise Exception("Emergency override active - macro execution blocked")
            
        # Get macro
        result = await db.execute(
            select(Macro).where(
                and_(
                    Macro.id == macro_id,
                    Macro.is_active == True
                )
            )
        )
        macro = result.scalar_one_or_none()
        if not macro:
            raise ValueError("Macro not found or inactive")
            
        # Check permissions
        if macro.required_role:
            # Check user role here
            pass
            
        # Check concurrent execution
        execution_id = f"{macro.slug}_{datetime.utcnow().timestamp()}"
        if not macro.allow_concurrent and macro.slug in self._active_macros:
            raise Exception(f"Macro '{macro.name}' is already running")
            
        # Create execution record
        execution = MacroExecution(
            macro_id=macro_id,
            execution_id=execution_id,
            status=MacroStatus.RUNNING,
            trigger_type=request.trigger_type,
            trigger_source=request.trigger_source,
            trigger_data=request.trigger_data,
            started_at=datetime.utcnow(),
            executed_by=user_id,
        )
        db.add(execution)
        await db.commit()
        
        # Add to active macros
        self._active_macros[macro.slug] = execution
        
        try:
            # Execute macro
            await self._execute_macro_actions(
                db,
                macro,
                execution,
                request.override_timeout or macro.timeout_seconds
            )
            
            # Update execution
            execution.status = MacroStatus.COMPLETED
            execution.completed_at = datetime.utcnow()
            execution.duration_ms = int(
                (execution.completed_at - execution.started_at).total_seconds() * 1000
            )
            
        except Exception as e:
            # Update execution with error
            execution.status = MacroStatus.FAILED
            execution.completed_at = datetime.utcnow()
            execution.duration_ms = int(
                (execution.completed_at - execution.started_at).total_seconds() * 1000
            )
            execution.error_message = str(e)
            logger.error(f"Macro execution failed: {e}")
            
        finally:
            # Remove from active macros
            if macro.slug in self._active_macros:
                del self._active_macros[macro.slug]
                
        await db.commit()
        await db.refresh(execution)
        
        return MacroExecutionResponse.model_validate(execution)
        
    async def _execute_macro_actions(
        self,
        db: AsyncSession,
        macro: Macro,
        execution: MacroExecution,
        timeout: int
    ) -> None:
        """Execute macro actions"""
        start_time = datetime.utcnow()
        execution_log = []
        
        for i, action in enumerate(macro.actions):
            # Check timeout
            if (datetime.utcnow() - start_time).total_seconds() > timeout:
                raise Exception("Macro execution timeout")
                
            # Check emergency override
            if self._emergency_override:
                raise Exception("Emergency override activated")
                
            action_log = {
                "index": i,
                "action": action,
                "started_at": datetime.utcnow().isoformat(),
            }
            
            try:
                # Execute action based on type
                if action.get("type") == "wait":
                    # Wait action
                    await asyncio.sleep(action.get("duration", 1))
                    action_log["status"] = "completed"
                    
                elif action.get("type") == "device":
                    # Device command
                    device_slug = action.get("device")
                    command = action.get("command")
                    parameters = action.get("parameters", {})
                    
                    # Get device
                    device_result = await db.execute(
                        select(Device).where(Device.slug == device_slug)
                    )
                    device = device_result.scalar_one_or_none()
                    if not device:
                        raise ValueError(f"Device '{device_slug}' not found")
                        
                    # Send command
                    device_command = DeviceCommand(
                        device_id=device.id,
                        command=command,
                        parameters=parameters
                    )
                    response = await self.send_device_command(
                        db,
                        device_command,
                        execution.executed_by
                    )
                    
                    action_log["status"] = "completed"
                    action_log["response"] = {
                        "status": response.status,
                        "data": response.response_data
                    }
                    execution.actions_executed += 1
                    
                elif action.get("type") == "macro":
                    # Nested macro execution
                    nested_macro_slug = action.get("macro")
                    
                    # Get nested macro
                    nested_result = await db.execute(
                        select(Macro).where(Macro.slug == nested_macro_slug)
                    )
                    nested_macro = nested_result.scalar_one_or_none()
                    if not nested_macro:
                        raise ValueError(f"Nested macro '{nested_macro_slug}' not found")
                        
                    # Execute nested macro
                    nested_request = MacroExecuteRequest(
                        trigger_type="parent",
                        trigger_source=macro.slug,
                        trigger_data={"parent_execution": execution.execution_id}
                    )
                    nested_response = await self.execute_macro(
                        db,
                        nested_macro.id,
                        nested_request,
                        execution.executed_by
                    )
                    
                    action_log["status"] = "completed"
                    action_log["nested_execution"] = nested_response.execution_id
                    execution.actions_executed += 1
                    
                else:
                    raise ValueError(f"Unknown action type: {action.get('type')}")
                    
            except Exception as e:
                action_log["status"] = "failed"
                action_log["error"] = str(e)
                execution.actions_failed += 1
                
                # Check if should continue on error
                if not action.get("continue_on_error", False):
                    execution_log.append(action_log)
                    execution.execution_log = execution_log
                    raise
                    
            action_log["completed_at"] = datetime.utcnow().isoformat()
            execution_log.append(action_log)
            
        execution.execution_log = execution_log
        
    # Show Control
    
    async def create_show(
        self,
        db: AsyncSession,
        show_data: ShowCreate,
        user_id: UUID
    ) -> ShowResponse:
        """Create new show"""
        # Check if slug already exists
        existing = await db.execute(
            select(Show).where(Show.slug == show_data.slug)
        )
        if existing.scalar():
            raise ValueError(f"Show with slug '{show_data.slug}' already exists")
            
        # Create show
        show = Show(
            **show_data.model_dump(),
            created_by=user_id
        )
        db.add(show)
        await db.commit()
        await db.refresh(show)
        
        # Load with cue count
        result = await db.execute(
            select(Show, func.count(ShowCue.id).label("cue_count"))
            .outerjoin(ShowCue)
            .where(Show.id == show.id)
            .group_by(Show.id)
        )
        show, cue_count = result.first()
        
        response = ShowResponse.model_validate(show)
        response.cue_count = cue_count or 0
        
        return response
        
    async def run_show(
        self,
        db: AsyncSession,
        show_id: UUID,
        rehearsal: bool = False,
        user_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """Run show from beginning"""
        # Check emergency override
        if self._emergency_override:
            raise Exception("Emergency override active - show execution blocked")
            
        # Get show with cues
        result = await db.execute(
            select(Show)
            .options(selectinload(Show.cues))
            .where(
                and_(
                    Show.id == show_id,
                    Show.is_active == True,
                    Show.is_locked == False
                )
            )
        )
        show = result.scalar_one_or_none()
        if not show:
            raise ValueError("Show not found, inactive, or locked")
            
        # Check if already running
        if show_id in self._active_shows:
            raise Exception(f"Show '{show.name}' is already running")
            
        # Initialize show state
        show_state = {
            "show_id": show_id,
            "rehearsal": rehearsal or show.default_rehearsal_mode,
            "current_cue": 0,
            "started_at": datetime.utcnow(),
            "user_id": user_id,
            "paused": False,
            "cues": sorted(show.cues, key=lambda c: c.cue_number)
        }
        
        self._active_shows[show_id] = show_state
        
        # Start show execution
        asyncio.create_task(self._run_show_cues(db, show_state))
        
        return {
            "show_id": show_id,
            "status": "running",
            "rehearsal": show_state["rehearsal"],
            "current_cue": 0,
            "total_cues": len(show_state["cues"])
        }
        
    async def _run_show_cues(
        self,
        db: AsyncSession,
        show_state: Dict[str, Any]
    ) -> None:
        """Run show cues"""
        show_id = show_state["show_id"]
        
        try:
            while show_state["current_cue"] < len(show_state["cues"]):
                # Check if show stopped
                if show_id not in self._active_shows:
                    break
                    
                # Check if paused
                if show_state["paused"]:
                    await asyncio.sleep(0.1)
                    continue
                    
                # Get current cue
                cue = show_state["cues"][show_state["current_cue"]]
                
                # Update cue status
                await db.execute(
                    update(ShowCue)
                    .where(ShowCue.id == cue.id)
                    .values(status=CueStatus.ACTIVE)
                )
                await db.commit()
                
                # Pre-wait
                if cue.pre_wait > 0:
                    await asyncio.sleep(cue.pre_wait)
                    
                # Execute cue
                if cue.cue_type == "macro" and cue.target_id:
                    # Execute macro
                    if not show_state["rehearsal"]:
                        request = MacroExecuteRequest(
                            trigger_type="show",
                            trigger_source=str(show_id),
                            trigger_data={
                                "cue_number": cue.cue_number,
                                "cue_label": cue.cue_label
                            }
                        )
                        await self.execute_macro(
                            db,
                            cue.target_id,
                            request,
                            show_state["user_id"]
                        )
                        
                elif cue.cue_type == "wait":
                    # Just wait
                    pass
                    
                # Post-wait
                if cue.post_wait > 0:
                    await asyncio.sleep(cue.post_wait)
                    
                # Update cue status
                await db.execute(
                    update(ShowCue)
                    .where(ShowCue.id == cue.id)
                    .values(status=CueStatus.COMPLETE)
                )
                await db.commit()
                
                # Move to next cue
                show_state["current_cue"] += 1
                
                # Check auto-follow
                if cue.auto_follow and cue.auto_follow_time:
                    await asyncio.sleep(cue.auto_follow_time)
                elif cue.continue_mode == "manual":
                    # Wait for manual go
                    show_state["paused"] = True
                    
        except Exception as e:
            logger.error(f"Show execution error: {e}")
            
        finally:
            # Clean up
            if show_id in self._active_shows:
                del self._active_shows[show_id]
                
    async def show_go(
        self,
        show_id: UUID
    ) -> Dict[str, Any]:
        """Advance to next cue in show"""
        if show_id not in self._active_shows:
            raise ValueError("Show not running")
            
        show_state = self._active_shows[show_id]
        show_state["paused"] = False
        
        return {
            "show_id": show_id,
            "current_cue": show_state["current_cue"],
            "status": "running"
        }
        
    async def stop_show(
        self,
        show_id: UUID
    ) -> None:
        """Stop running show"""
        if show_id in self._active_shows:
            del self._active_shows[show_id]
            
    # Device Discovery
    
    async def discover_devices(
        self,
        request: DiscoveryRequest
    ) -> List[DiscoveredDevice]:
        """Discover devices on network"""
        discovered = []
        
        # Run discovery for each protocol
        protocols = request.protocols or settings.discovery_protocols
        
        for protocol in protocols:
            try:
                # Protocol-specific discovery
                # This would be implemented per protocol
                pass
            except Exception as e:
                logger.error(f"Discovery error for {protocol}: {e}")
                
        return discovered
        
    # Emergency Control
    
    async def emergency_stop(
        self,
        reason: str,
        user_id: Optional[UUID] = None
    ) -> EmergencyOverrideResponse:
        """Emergency stop all automation"""
        logger.warning(f"EMERGENCY STOP: {reason}")
        
        # Set override flag
        self._emergency_override = True
        
        # Stop all active macros
        for macro_slug in list(self._active_macros.keys()):
            execution = self._active_macros[macro_slug]
            execution.status = MacroStatus.CANCELLED
            execution.error_message = f"Emergency stop: {reason}"
            
        self._active_macros.clear()
        
        # Stop all active shows
        self._active_shows.clear()
        
        # Send stop commands to all devices
        affected_devices = []
        for device_id, adapter in self._device_adapters.items():
            try:
                await adapter.send_command("emergency_stop", {})
                affected_devices.append(device_id)
            except Exception as e:
                logger.error(f"Failed to stop device {device_id}: {e}")
                
        return EmergencyOverrideResponse(
            id=UUID("00000000-0000-0000-0000-000000000000"),  # Placeholder
            override_type="emergency_stop",
            reason=reason,
            initiated_by=user_id or UUID("00000000-0000-0000-0000-000000000000"),
            initiated_at=datetime.utcnow(),
            actions=["stopped_macros", "stopped_shows", "stopped_devices"],
            affected_devices=affected_devices
        )
        
    async def release_emergency_override(
        self,
        user_id: UUID
    ) -> None:
        """Release emergency override"""
        self._emergency_override = False
        logger.info(f"Emergency override released by user {user_id}")
        
    # Background Tasks
    
    async def _discovery_loop(self) -> None:
        """Background device discovery"""
        while not self._shutdown:
            try:
                # Run discovery
                request = DiscoveryRequest()
                devices = await self.discover_devices(request)
                
                # Process discovered devices
                for device in devices:
                    logger.info(f"Discovered device: {device.name} ({device.device_type})")
                    
            except Exception as e:
                logger.error(f"Discovery loop error: {e}")
                
            # Wait for next discovery
            await asyncio.sleep(settings.discovery_interval)
            
    async def _monitoring_loop(self) -> None:
        """Background device monitoring"""
        while not self._shutdown:
            try:
                # Check all connected devices
                for device_id, adapter in list(self._device_adapters.items()):
                    try:
                        if not await adapter.is_connected():
                            logger.warning(f"Device {device_id} disconnected")
                            # Attempt reconnection handled by adapter
                            
                    except Exception as e:
                        logger.error(f"Monitoring error for {device_id}: {e}")
                        
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                
            # Wait for next check
            await asyncio.sleep(settings.monitoring_interval)
            
    async def _scheduler_loop(self) -> None:
        """Background macro scheduler"""
        while not self._shutdown:
            try:
                # Check scheduled executions
                # This would query the database for due scheduled executions
                pass
                
            except Exception as e:
                logger.error(f"Scheduler loop error: {e}")
                
            # Wait for next check
            await asyncio.sleep(60)  # Check every minute


# Global service instance
automation_service = AutomationService()