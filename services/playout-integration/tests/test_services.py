"""Test service layer functionality"""

import pytest
from unittest.mock import Mock, AsyncMock
from uuid import uuid4

from src.services.playout_service import PlayoutService, GenericPlayoutAdapter
from src.db.models import PlayoutSystem, PlayoutSystemType, PlayoutProtocol, DeviceStatus
from src.models.schemas import PlayoutSystemCreate, DeviceCreate, DeviceCommand


class TestPlayoutService:
    """Test PlayoutService class"""
    
    @pytest.fixture
    def service(self):
        """Create service instance"""
        return PlayoutService()
    
    @pytest.mark.asyncio
    async def test_create_system_success(self, service, async_session):
        """Test successful system creation"""
        system_data = PlayoutSystemCreate(
            name="Test System",
            slug="test-system-unique",
            system_type=PlayoutSystemType.GENERIC,
            protocol=PlayoutProtocol.VDCP,
            host="localhost",
            port=8080,
            config={},
            channels=[],
            capabilities=[]
        )
        
        result = await service.create_system(async_session, system_data)
        
        assert result.name == system_data.name
        assert result.slug == system_data.slug
        assert result.system_type == system_data.system_type
        assert result.id is not None
    
    @pytest.mark.asyncio
    async def test_create_system_duplicate_slug(self, service, async_session, sample_playout_system):
        """Test system creation with duplicate slug"""
        system_data = PlayoutSystemCreate(
            name="Another System",
            slug=sample_playout_system.slug,  # Use existing slug
            system_type=PlayoutSystemType.GENERIC,
            protocol=PlayoutProtocol.VDCP,
            config={},
            channels=[],
            capabilities=[]
        )
        
        with pytest.raises(ValueError, match="already exists"):
            await service.create_system(async_session, system_data)
    
    @pytest.mark.asyncio
    async def test_get_system_success(self, service, async_session, sample_playout_system):
        """Test successful system retrieval"""
        result = await service.get_system(async_session, sample_playout_system.id)
        
        assert result is not None
        assert result.id == sample_playout_system.id
        assert result.name == sample_playout_system.name
    
    @pytest.mark.asyncio
    async def test_get_system_not_found(self, service, async_session):
        """Test system retrieval with invalid ID"""
        fake_id = uuid4()
        result = await service.get_system(async_session, fake_id)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_list_systems(self, service, async_session, sample_playout_system):
        """Test system listing"""
        result = await service.list_systems(async_session, skip=0, limit=10)
        
        assert isinstance(result, list)
        assert len(result) >= 1
        assert any(system.id == sample_playout_system.id for system in result)
    
    @pytest.mark.asyncio
    async def test_list_systems_filtered(self, service, async_session, sample_playout_system):
        """Test system listing with filters"""
        # Test active filter
        result = await service.list_systems(
            async_session, 
            skip=0, 
            limit=10, 
            is_active=True
        )
        assert all(system.is_active for system in result)
        
        # Test system type filter
        result = await service.list_systems(
            async_session,
            skip=0,
            limit=10,
            system_type=PlayoutSystemType.GENERIC
        )
        assert all(system.system_type == PlayoutSystemType.GENERIC for system in result)
    
    @pytest.mark.asyncio
    async def test_update_system(self, service, async_session, sample_playout_system):
        """Test system update"""
        from src.models.schemas import PlayoutSystemUpdate
        
        update_data = PlayoutSystemUpdate(
            name="Updated Name",
            host="updated-host"
        )
        
        result = await service.update_system(
            async_session, 
            sample_playout_system.id, 
            update_data
        )
        
        assert result is not None
        assert result.name == "Updated Name"
        assert result.host == "updated-host"
    
    @pytest.mark.asyncio
    async def test_delete_system(self, service, async_session, sample_playout_system):
        """Test system deletion"""
        system_id = sample_playout_system.id
        
        result = await service.delete_system(async_session, system_id)
        assert result is True
        
        # Verify it's deleted
        retrieved = await service.get_system(async_session, system_id)
        assert retrieved is None
    
    @pytest.mark.asyncio
    async def test_create_device_success(self, service, async_session, sample_playout_system):
        """Test successful device creation"""
        device_data = DeviceCreate(
            playout_system_id=sample_playout_system.id,
            name="Test Device",
            device_id="DEV123",
            device_type="server",
            channel=1,
            is_backup=False,
            supported_formats=[],
            metadata={}
        )
        
        result = await service.create_device(async_session, device_data)
        
        assert result.name == device_data.name
        assert result.device_id == device_data.device_id
        assert result.playout_system_id == device_data.playout_system_id
    
    @pytest.mark.asyncio
    async def test_create_device_invalid_system(self, service, async_session):
        """Test device creation with invalid system ID"""
        fake_system_id = uuid4()
        
        device_data = DeviceCreate(
            playout_system_id=fake_system_id,
            name="Test Device",
            device_id="DEV123",
            device_type="server",
            channel=1,
            is_backup=False,
            supported_formats=[],
            metadata={}
        )
        
        with pytest.raises(ValueError, match="not found"):
            await service.create_device(async_session, device_data)
    
    @pytest.mark.asyncio
    async def test_create_device_duplicate(self, service, async_session, sample_device):
        """Test device creation with duplicate device_id in same system"""
        device_data = DeviceCreate(
            playout_system_id=sample_device.playout_system_id,
            name="Another Device",
            device_id=sample_device.device_id,  # Same device_id
            device_type="server",
            channel=2,
            is_backup=False,
            supported_formats=[],
            metadata={}
        )
        
        with pytest.raises(ValueError, match="already exists"):
            await service.create_device(async_session, device_data)
    
    @pytest.mark.asyncio
    async def test_get_device_status(self, service, async_session, sample_device):
        """Test getting device status"""
        # Mock the adapter
        service._adapters[sample_device.playout_system.system_type] = Mock()
        mock_adapter = Mock()
        mock_adapter.get_device_status = AsyncMock(return_value={
            "status": "online",
            "storage_used_gb": 100.5,
            "uptime_seconds": 3600
        })
        
        service._get_adapter = Mock(return_value=mock_adapter)
        
        result = await service.get_device_status(async_session, sample_device.id)
        
        assert result is not None
        assert result.id == sample_device.id
        mock_adapter.get_device_status.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_control_device(self, service, async_session, sample_device):
        """Test device control"""
        # Mock the adapter
        mock_adapter = Mock()
        mock_adapter.send_command = AsyncMock(return_value={
            "acknowledged": True,
            "result": "success"
        })
        
        service._get_adapter = Mock(return_value=mock_adapter)
        
        command = DeviceCommand(
            command="play",
            parameters={"speed": 1.0}
        )
        
        result = await service.control_device(async_session, sample_device.id, command)
        
        assert result["status"] == "success"
        assert result["command"] == "play"
        mock_adapter.send_command.assert_called_once_with(
            sample_device.device_id,
            "play",
            {"speed": 1.0}
        )


class TestGenericPlayoutAdapter:
    """Test GenericPlayoutAdapter"""
    
    @pytest.fixture
    def mock_system(self):
        """Create mock playout system"""
        system = Mock()
        system.api_url = "http://localhost:8080"
        system.host = "localhost"
        system.port = 8080
        return system
    
    @pytest.fixture
    def adapter(self, mock_system):
        """Create adapter instance"""
        return GenericPlayoutAdapter(mock_system)
    
    @pytest.mark.asyncio
    async def test_test_connection_success(self, adapter, mock_system):
        """Test successful connection test"""
        # Would need to mock httpx.AsyncClient for real test
        # For now, test the structure
        assert hasattr(adapter, 'test_connection')
        assert callable(adapter.test_connection)
    
    @pytest.mark.asyncio  
    async def test_get_device_status(self, adapter):
        """Test device status retrieval"""
        result = await adapter.get_device_status("DEV001")
        
        assert result["status"] == "online"
        assert result["device_id"] == "DEV001"
    
    @pytest.mark.asyncio
    async def test_send_command(self, adapter):
        """Test sending command"""
        result = await adapter.send_command("DEV001", "play", {"speed": 1.0})
        
        assert result["acknowledged"] is True
        assert result["command"] == "play"
        assert result["device_id"] == "DEV001"
    
    @pytest.mark.asyncio
    async def test_transfer_content(self, adapter):
        """Test content transfer"""
        result = await adapter.transfer_content(
            "/path/to/content.mp4",
            "/playout/content.mp4", 
            {"title": "Test Content"}
        )
        
        # Should return a transfer ID
        assert isinstance(result, str)
        assert len(result) > 0
    
    @pytest.mark.asyncio
    async def test_get_schedule(self, adapter):
        """Test schedule retrieval"""
        from datetime import datetime
        
        result = await adapter.get_schedule(1, datetime.now())
        
        assert isinstance(result, list)
        # Generic implementation returns empty list
        assert len(result) == 0
    
    @pytest.mark.asyncio
    async def test_update_schedule(self, adapter):
        """Test schedule update"""
        result = await adapter.update_schedule(1, [])
        
        assert result is True


class TestAdapterRegistration:
    """Test adapter registration and retrieval"""
    
    @pytest.fixture
    def service(self):
        return PlayoutService()
    
    def test_get_adapter_generic_fallback(self, service):
        """Test fallback to generic adapter"""
        mock_system = Mock()
        mock_system.system_type = PlayoutSystemType.GENERIC
        
        adapter = service._get_adapter(mock_system)
        
        assert isinstance(adapter, GenericPlayoutAdapter)
        assert adapter.system == mock_system
    
    def test_get_adapter_unknown_type(self, service):
        """Test fallback for unknown system type"""
        mock_system = Mock()
        mock_system.system_type = PlayoutSystemType.GRASS_VALLEY  # Not registered
        
        adapter = service._get_adapter(mock_system)
        
        # Should fall back to generic
        assert isinstance(adapter, GenericPlayoutAdapter)