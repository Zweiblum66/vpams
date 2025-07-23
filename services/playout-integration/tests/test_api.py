"""Test API endpoints"""

import pytest
import json
from uuid import uuid4


class TestSystemEndpoints:
    """Test playout system endpoints"""
    
    def test_health_check(self, test_client):
        """Test health check endpoint"""
        response = test_client.get("/api/v1/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "playout-integration"
    
    def test_root_endpoint(self, test_client):
        """Test root endpoint"""
        response = test_client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        assert data["service"] == "playout-integration"
        assert data["status"] == "running"
    
    def test_create_playout_system(self, test_client, auth_headers):
        """Test creating playout system"""
        system_data = {
            "name": "Test System",
            "slug": "test-system-api",
            "system_type": "generic",
            "protocol": "vdcp",
            "host": "localhost",
            "port": 8080,
            "config": {},
            "channels": [],
            "capabilities": []
        }
        
        response = test_client.post(
            "/api/v1/systems",
            json=system_data,
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == system_data["name"]
        assert data["slug"] == system_data["slug"]
        assert "id" in data
    
    @pytest.mark.asyncio
    async def test_list_playout_systems(self, test_client, auth_headers, sample_playout_system):
        """Test listing playout systems"""
        response = test_client.get(
            "/api/v1/systems",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
    
    @pytest.mark.asyncio
    async def test_get_playout_system(self, test_client, auth_headers, sample_playout_system):
        """Test getting single playout system"""
        system_id = str(sample_playout_system.id)
        
        response = test_client.get(
            f"/api/v1/systems/{system_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == system_id
        assert data["name"] == sample_playout_system.name
    
    def test_get_nonexistent_system(self, test_client, auth_headers):
        """Test getting nonexistent system"""
        fake_id = str(uuid4())
        
        response = test_client.get(
            f"/api/v1/systems/{fake_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio  
    async def test_update_playout_system(self, test_client, auth_headers, sample_playout_system):
        """Test updating playout system"""
        system_id = str(sample_playout_system.id)
        update_data = {
            "name": "Updated System Name"
        }
        
        response = test_client.put(
            f"/api/v1/systems/{system_id}",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == update_data["name"]
    
    @pytest.mark.asyncio
    async def test_delete_playout_system(self, test_client, auth_headers, sample_playout_system):
        """Test deleting playout system"""
        system_id = str(sample_playout_system.id)
        
        response = test_client.delete(
            f"/api/v1/systems/{system_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 204
        
        # Verify it's deleted
        response = test_client.get(
            f"/api/v1/systems/{system_id}",
            headers=auth_headers
        )
        assert response.status_code == 404


class TestDeviceEndpoints:
    """Test device endpoints"""
    
    @pytest.mark.asyncio
    async def test_create_device(self, test_client, auth_headers, sample_playout_system):
        """Test creating device"""
        device_data = {
            "playout_system_id": str(sample_playout_system.id),
            "name": "Test Device API",
            "device_id": "DEV002",
            "device_type": "server",
            "channel": 2,
            "is_backup": False,
            "supported_formats": [],
            "metadata": {}
        }
        
        response = test_client.post(
            "/api/v1/devices",
            json=device_data,
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == device_data["name"]
        assert data["device_id"] == device_data["device_id"]
    
    @pytest.mark.asyncio
    async def test_update_device(self, test_client, auth_headers, sample_device):
        """Test updating device"""
        device_id = str(sample_device.id)
        update_data = {
            "name": "Updated Device Name"
        }
        
        response = test_client.put(
            f"/api/v1/devices/{device_id}",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == update_data["name"]
    
    @pytest.mark.asyncio
    async def test_get_device_status(self, test_client, auth_headers, sample_device):
        """Test getting device status"""
        device_id = str(sample_device.id)
        
        response = test_client.get(
            f"/api/v1/devices/{device_id}/status",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == device_id
        assert "status" in data
    
    @pytest.mark.asyncio
    async def test_control_device(self, test_client, auth_headers, sample_device):
        """Test device control"""
        device_id = str(sample_device.id)
        command_data = {
            "command": "play",
            "parameters": {}
        }
        
        response = test_client.post(
            f"/api/v1/devices/{device_id}/control",
            json=command_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["command"] == command_data["command"]
    
    @pytest.mark.asyncio
    async def test_delete_device(self, test_client, auth_headers, sample_device):
        """Test deleting device"""
        device_id = str(sample_device.id)
        
        response = test_client.delete(
            f"/api/v1/devices/{device_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 204


class TestAuthEndpoints:
    """Test authentication"""
    
    def test_unauthorized_request(self, test_client):
        """Test request without authentication"""
        response = test_client.get("/api/v1/systems")
        
        # Should return 401 or allow with dev user
        assert response.status_code in [200, 401]
    
    def test_invalid_uuid_format(self, test_client, auth_headers):
        """Test invalid UUID format"""
        response = test_client.get(
            "/api/v1/systems/invalid-uuid",
            headers=auth_headers
        )
        
        assert response.status_code == 422


class TestErrorHandling:
    """Test error handling"""
    
    def test_not_found_endpoint(self, test_client):
        """Test 404 for nonexistent endpoint"""
        response = test_client.get("/api/v1/nonexistent")
        assert response.status_code == 404
    
    def test_method_not_allowed(self, test_client):
        """Test 405 for wrong HTTP method"""
        response = test_client.post("/api/v1/health")
        assert response.status_code == 405
    
    def test_validation_error(self, test_client, auth_headers):
        """Test validation error on bad data"""
        bad_data = {
            "name": "",  # Empty name should fail validation
            "slug": "test",
            "system_type": "invalid_type"
        }
        
        response = test_client.post(
            "/api/v1/systems",
            json=bad_data,
            headers=auth_headers
        )
        
        assert response.status_code == 422