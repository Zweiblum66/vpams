"""Main playout system service"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import logging
import httpx
from abc import ABC, abstractmethod

from ..db.models import (
    PlayoutSystem, PlayoutDevice, PlayoutSystemType,
    PlayoutProtocol, DeviceStatus
)
from ..models.schemas import (
    PlayoutSystemCreate, PlayoutSystemUpdate, PlayoutSystemResponse,
    DeviceCreate, DeviceUpdate, DeviceResponse,
    SystemStatus, DeviceCommand
)
from ..core.config import settings

logger = logging.getLogger(__name__)


class PlayoutService:
    """Service for managing playout systems"""
    
    def __init__(self):
        self._adapters: Dict[PlayoutSystemType, 'PlayoutAdapter'] = {}
        self._register_adapters()
    
    def _register_adapters(self):
        """Register playout system adapters"""
        # Register adapters for different playout systems
        # These will be implemented in playout_systems/ directory
        pass
    
    async def create_system(
        self,
        db: AsyncSession,
        system_data: PlayoutSystemCreate
    ) -> PlayoutSystemResponse:
        """Create a new playout system"""
        # Check for duplicate slug
        existing = await db.execute(
            select(PlayoutSystem).where(PlayoutSystem.slug == system_data.slug)
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"Playout system with slug '{system_data.slug}' already exists")
        
        # Create system
        system_dict = system_data.model_dump()
        # Extract sensitive fields
        api_key = system_dict.pop('api_key', None)
        username = system_dict.pop('username', None) 
        password = system_dict.pop('password', None)
        
        system = PlayoutSystem(**system_dict)
        
        # Store credentials securely (should be encrypted)
        if api_key:
            system.api_key = api_key  # TODO: Encrypt
        if username:
            system.username = username
        if password:
            system.password = password  # TODO: Encrypt
        
        db.add(system)
        await db.commit()
        await db.refresh(system)
        
        logger.info(f"Created playout system: {system.id} - {system.name}")
        return PlayoutSystemResponse.model_validate(system)
    
    async def get_system(
        self,
        db: AsyncSession,
        system_id: UUID
    ) -> Optional[PlayoutSystemResponse]:
        """Get a playout system by ID"""
        result = await db.execute(
            select(PlayoutSystem).where(PlayoutSystem.id == system_id)
        )
        system = result.scalar_one_or_none()
        
        if not system:
            return None
        
        response = PlayoutSystemResponse.model_validate(system)
        
        # Get device count
        device_count = await db.execute(
            select(func.count(PlayoutDevice.id)).where(
                PlayoutDevice.playout_system_id == system_id
            )
        )
        response.device_count = device_count.scalar()
        
        return response
    
    async def list_systems(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        is_active: Optional[bool] = None,
        system_type: Optional[PlayoutSystemType] = None
    ) -> List[PlayoutSystemResponse]:
        """List playout systems"""
        query = select(PlayoutSystem)
        
        # Apply filters
        conditions = []
        if is_active is not None:
            conditions.append(PlayoutSystem.is_active == is_active)
        if system_type:
            conditions.append(PlayoutSystem.system_type == system_type)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        # Order by name
        query = query.order_by(PlayoutSystem.name)
        
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        result = await db.execute(query)
        systems = result.scalars().all()
        
        return [PlayoutSystemResponse.model_validate(system) for system in systems]
    
    async def update_system(
        self,
        db: AsyncSession,
        system_id: UUID,
        update_data: PlayoutSystemUpdate
    ) -> Optional[PlayoutSystemResponse]:
        """Update a playout system"""
        # Get system
        result = await db.execute(
            select(PlayoutSystem).where(PlayoutSystem.id == system_id)
        )
        system = result.scalar_one_or_none()
        
        if not system:
            return None
        
        # Update fields
        update_dict = update_data.model_dump(exclude_unset=True)
        
        # Handle sensitive fields
        if 'api_key' in update_dict:
            update_dict['api_key'] = update_dict['api_key']  # TODO: Encrypt
        if 'password' in update_dict:
            update_dict['password'] = update_dict['password']  # TODO: Encrypt
        
        for field, value in update_dict.items():
            setattr(system, field, value)
        
        system.updated_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(system)
        
        logger.info(f"Updated playout system: {system_id}")
        return PlayoutSystemResponse.model_validate(system)
    
    async def delete_system(
        self,
        db: AsyncSession,
        system_id: UUID
    ) -> bool:
        """Delete a playout system"""
        # Get system
        result = await db.execute(
            select(PlayoutSystem).where(PlayoutSystem.id == system_id)
        )
        system = result.scalar_one_or_none()
        
        if not system:
            return False
        
        # Delete system (cascade will handle related records)
        await db.delete(system)
        await db.commit()
        
        logger.info(f"Deleted playout system: {system_id}")
        return True
    
    async def test_connection(
        self,
        db: AsyncSession,
        system_id: UUID
    ) -> Dict[str, Any]:
        """Test connection to playout system"""
        # Get system
        result = await db.execute(
            select(PlayoutSystem).where(PlayoutSystem.id == system_id)
        )
        system = result.scalar_one_or_none()
        
        if not system:
            raise ValueError("Playout system not found")
        
        # Get appropriate adapter
        adapter = self._get_adapter(system)
        
        try:
            # Test connection
            result = await adapter.test_connection()
            
            # Update heartbeat
            system.last_heartbeat = datetime.utcnow()
            await db.commit()
            
            return {
                "status": "success",
                "connected": True,
                "message": "Connection successful",
                "details": result
            }
        except Exception as e:
            logger.error(f"Connection test failed for system {system_id}: {str(e)}")
            return {
                "status": "error",
                "connected": False,
                "message": str(e),
                "details": {}
            }
    
    async def get_system_status(
        self,
        db: AsyncSession,
        system_id: UUID
    ) -> SystemStatus:
        """Get detailed system status"""
        # Get system with devices
        result = await db.execute(
            select(PlayoutSystem)
            .options(selectinload(PlayoutSystem.devices))
            .where(PlayoutSystem.id == system_id)
        )
        system = result.scalar_one_or_none()
        
        if not system:
            raise ValueError("Playout system not found")
        
        # Determine overall status
        if not system.is_active:
            status = "inactive"
        elif not system.last_heartbeat:
            status = "unknown"
        elif system.last_heartbeat < datetime.utcnow() - timedelta(minutes=5):
            status = "offline"
        else:
            status = "online"
        
        # Get device statuses
        devices = []
        for device in system.devices:
            devices.append({
                "id": str(device.id),
                "name": device.name,
                "channel": device.channel,
                "status": device.status.value,
                "is_active": device.is_active,
                "is_backup": device.is_backup
            })
        
        # Get transfer counts
        # TODO: Query transfer counts
        
        return SystemStatus(
            id=system.id,
            name=system.name,
            system_type=system.system_type,
            status=status,
            is_active=system.is_active,
            last_heartbeat=system.last_heartbeat,
            devices=devices,
            active_transfers=0,  # TODO: Get actual count
            pending_transfers=0,  # TODO: Get actual count
            active_schedules=0   # TODO: Get actual count
        )
    
    async def create_device(
        self,
        db: AsyncSession,
        device_data: DeviceCreate
    ) -> DeviceResponse:
        """Create a new device"""
        # Check system exists
        system_result = await db.execute(
            select(PlayoutSystem).where(
                PlayoutSystem.id == device_data.playout_system_id
            )
        )
        if not system_result.scalar_one_or_none():
            raise ValueError("Playout system not found")
        
        # Check for duplicate device ID
        existing = await db.execute(
            select(PlayoutDevice).where(
                and_(
                    PlayoutDevice.playout_system_id == device_data.playout_system_id,
                    PlayoutDevice.device_id == device_data.device_id
                )
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"Device '{device_data.device_id}' already exists in this system")
        
        # Create device
        device = PlayoutDevice(**device_data.model_dump())
        device.status = DeviceStatus.UNKNOWN
        
        db.add(device)
        await db.commit()
        await db.refresh(device)
        
        logger.info(f"Created device: {device.id} - {device.name}")
        return DeviceResponse.model_validate(device)
    
    async def update_device(
        self,
        db: AsyncSession,
        device_id: UUID,
        update_data: DeviceUpdate
    ) -> Optional[DeviceResponse]:
        """Update a device"""
        # Get device
        result = await db.execute(
            select(PlayoutDevice).where(PlayoutDevice.id == device_id)
        )
        device = result.scalar_one_or_none()
        
        if not device:
            return None
        
        # Update fields
        update_dict = update_data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(device, field, value)
        
        device.updated_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(device)
        
        logger.info(f"Updated device: {device_id}")
        return DeviceResponse.model_validate(device)
    
    async def delete_device(
        self,
        db: AsyncSession,
        device_id: UUID
    ) -> bool:
        """Delete a device"""
        # Get device
        result = await db.execute(
            select(PlayoutDevice).where(PlayoutDevice.id == device_id)
        )
        device = result.scalar_one_or_none()
        
        if not device:
            return False
        
        # Delete device
        await db.delete(device)
        await db.commit()
        
        logger.info(f"Deleted device: {device_id}")
        return True
    
    async def get_device_status(
        self,
        db: AsyncSession,
        device_id: UUID
    ) -> Optional[DeviceResponse]:
        """Get device status"""
        # Get device with system
        result = await db.execute(
            select(PlayoutDevice)
            .options(selectinload(PlayoutDevice.playout_system))
            .where(PlayoutDevice.id == device_id)
        )
        device = result.scalar_one_or_none()
        
        if not device:
            return None
        
        # Get adapter and check device status
        adapter = self._get_adapter(device.playout_system)
        
        try:
            status_info = await adapter.get_device_status(device.device_id)
            
            # Update device status
            device.status = DeviceStatus(status_info.get('status', 'unknown'))
            device.last_status_check = datetime.utcnow()
            
            if 'storage_used_gb' in status_info:
                device.storage_used_gb = status_info['storage_used_gb']
            if 'uptime_seconds' in status_info:
                device.uptime_seconds = status_info['uptime_seconds']
            
            await db.commit()
            await db.refresh(device)
            
        except Exception as e:
            logger.error(f"Failed to get device status: {str(e)}")
            device.status = DeviceStatus.ERROR
            device.last_error = str(e)
            device.last_status_check = datetime.utcnow()
            await db.commit()
        
        return DeviceResponse.model_validate(device)
    
    async def control_device(
        self,
        db: AsyncSession,
        device_id: UUID,
        command: DeviceCommand
    ) -> Dict[str, Any]:
        """Send control command to device"""
        # Get device with system
        result = await db.execute(
            select(PlayoutDevice)
            .options(selectinload(PlayoutDevice.playout_system))
            .where(PlayoutDevice.id == device_id)
        )
        device = result.scalar_one_or_none()
        
        if not device:
            raise ValueError("Device not found")
        
        if not device.is_active:
            raise ValueError("Device is not active")
        
        if device.status == DeviceStatus.OFFLINE:
            raise ValueError("Device is offline")
        
        # Get adapter and send command
        adapter = self._get_adapter(device.playout_system)
        
        try:
            result = await adapter.send_command(
                device.device_id,
                command.command,
                command.parameters
            )
            
            return {
                "status": "success",
                "command": command.command,
                "result": result
            }
        except Exception as e:
            logger.error(f"Device control failed: {str(e)}")
            return {
                "status": "error",
                "command": command.command,
                "error": str(e)
            }
    
    def _get_adapter(self, system: PlayoutSystem) -> 'PlayoutAdapter':
        """Get adapter for playout system type"""
        adapter_class = self._adapters.get(system.system_type)
        if not adapter_class:
            # Use generic adapter as fallback
            adapter_class = GenericPlayoutAdapter
        
        return adapter_class(system)


class PlayoutAdapter(ABC):
    """Abstract base class for playout system adapters"""
    
    def __init__(self, system: PlayoutSystem):
        self.system = system
    
    @abstractmethod
    async def test_connection(self) -> Dict[str, Any]:
        """Test connection to playout system"""
        pass
    
    @abstractmethod
    async def get_device_status(self, device_id: str) -> Dict[str, Any]:
        """Get status of a specific device"""
        pass
    
    @abstractmethod
    async def send_command(
        self,
        device_id: str,
        command: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send command to device"""
        pass
    
    @abstractmethod
    async def transfer_content(
        self,
        content_path: str,
        destination: str,
        metadata: Dict[str, Any]
    ) -> str:
        """Transfer content to playout system"""
        pass
    
    @abstractmethod
    async def get_schedule(
        self,
        channel: int,
        date: datetime
    ) -> List[Dict[str, Any]]:
        """Get schedule from playout system"""
        pass
    
    @abstractmethod
    async def update_schedule(
        self,
        channel: int,
        schedule_items: List[Dict[str, Any]]
    ) -> bool:
        """Update schedule in playout system"""
        pass


class GenericPlayoutAdapter(PlayoutAdapter):
    """Generic playout adapter for basic functionality"""
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test connection using basic HTTP"""
        if self.system.api_url:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        self.system.api_url,
                        timeout=10.0
                    )
                    return {
                        "status_code": response.status_code,
                        "reachable": response.status_code < 500
                    }
            except Exception as e:
                raise Exception(f"Connection failed: {str(e)}")
        
        raise Exception("No API URL configured")
    
    async def get_device_status(self, device_id: str) -> Dict[str, Any]:
        """Get device status - generic implementation"""
        return {
            "status": "online",
            "device_id": device_id
        }
    
    async def send_command(
        self,
        device_id: str,
        command: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send command - generic implementation"""
        logger.info(f"Sending command '{command}' to device {device_id}")
        return {
            "acknowledged": True,
            "command": command,
            "device_id": device_id
        }
    
    async def transfer_content(
        self,
        content_path: str,
        destination: str,
        metadata: Dict[str, Any]
    ) -> str:
        """Transfer content - generic implementation"""
        import uuid
        # This would be implemented based on the protocol
        transfer_id = str(uuid.uuid4())
        logger.info(f"Starting transfer {transfer_id}: {content_path} -> {destination}")
        return transfer_id
    
    async def get_schedule(
        self,
        channel: int,
        date: datetime
    ) -> List[Dict[str, Any]]:
        """Get schedule - generic implementation"""
        return []
    
    async def update_schedule(
        self,
        channel: int,
        schedule_items: List[Dict[str, Any]]
    ) -> bool:
        """Update schedule - generic implementation"""
        logger.info(f"Updating schedule for channel {channel} with {len(schedule_items)} items")
        return True


# Create service instance
playout_service = PlayoutService()