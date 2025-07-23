"""Tests for MOS API endpoints"""

import pytest
from httpx import AsyncClient
from datetime import datetime

from src.models.schemas import MOSStatus


class TestHealthEndpoints:
    """Test health and status endpoints"""
    
    @pytest.mark.asyncio
    async def test_health_check(self, client: AsyncClient):
        """Test health check endpoint"""
        response = await client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert "service" in data
        assert "version" in data
    
    @pytest.mark.asyncio
    async def test_mos_health_check(self, client: AsyncClient):
        """Test MOS-specific health check"""
        response = await client.get("/api/v1/mos/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert "database" in data
        assert "redis" in data
        assert "connections" in data
    
    @pytest.mark.asyncio
    async def test_server_info(self, client: AsyncClient):
        """Test server info endpoint"""
        response = await client.get("/server-info")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert "active_connections" in data
        assert "configuration" in data
        
        config = data["configuration"]
        assert "listen_port" in config
        assert "server_id" in config


class TestConnectionEndpoints:
    """Test connection management endpoints"""
    
    @pytest.mark.asyncio
    async def test_list_connections(self, client: AsyncClient):
        """Test listing connections"""
        response = await client.get("/api/v1/mos/connections")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
    
    @pytest.mark.asyncio
    async def test_list_connections_with_filters(self, client: AsyncClient):
        """Test listing connections with filters"""
        response = await client.get(
            "/api/v1/mos/connections?status=connected&limit=10&offset=0"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_connection(self, client: AsyncClient):
        """Test getting non-existent connection"""
        response = await client.get("/api/v1/mos/connections/nonexistent")
        assert response.status_code == 404


class TestObjectEndpoints:
    """Test MOS object endpoints"""
    
    @pytest.mark.asyncio
    async def test_list_objects(self, client: AsyncClient):
        """Test listing objects"""
        response = await client.get("/api/v1/mos/objects")
        assert response.status_code == 200
        
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data
        assert "has_next" in data
        assert "has_prev" in data
    
    @pytest.mark.asyncio
    async def test_list_objects_with_filters(self, client: AsyncClient):
        """Test listing objects with filters"""
        response = await client.get(
            "/api/v1/mos/objects?obj_type=video&status=NEW&limit=20"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "items" in data
        assert data["limit"] == 20
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_object(self, client: AsyncClient):
        """Test getting non-existent object"""
        response = await client.get("/api/v1/mos/objects/nonexistent")
        assert response.status_code == 404


class TestRunningOrderEndpoints:
    """Test running order endpoints"""
    
    @pytest.mark.asyncio
    async def test_list_running_orders(self, client: AsyncClient):
        """Test listing running orders"""
        response = await client.get("/api/v1/mos/running-orders")
        assert response.status_code == 200
        
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data
    
    @pytest.mark.asyncio
    async def test_list_running_orders_with_filters(self, client: AsyncClient):
        """Test listing running orders with filters"""
        response = await client.get(
            "/api/v1/mos/running-orders?status=READY&ready_to_air=true"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "items" in data
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_running_order(self, client: AsyncClient):
        """Test getting non-existent running order"""
        response = await client.get("/api/v1/mos/running-orders/nonexistent")
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_get_running_order_with_stories(self, client: AsyncClient):
        """Test getting running order with stories included"""
        response = await client.get(
            "/api/v1/mos/running-orders/nonexistent?include_stories=true"
        )
        assert response.status_code == 404  # Should still be 404 for non-existent


class TestMessageEndpoints:
    """Test message log endpoints"""
    
    @pytest.mark.asyncio
    async def test_list_messages(self, client: AsyncClient):
        """Test listing messages"""
        response = await client.get("/api/v1/mos/messages")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
    
    @pytest.mark.asyncio
    async def test_list_messages_with_filters(self, client: AsyncClient):
        """Test listing messages with filters"""
        response = await client.get(
            "/api/v1/mos/messages?direction=inbound&message_type=mosObj&limit=50"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)


class TestManagementEndpoints:
    """Test management endpoints"""
    
    @pytest.mark.asyncio
    async def test_get_stats(self, client: AsyncClient):
        """Test getting statistics"""
        response = await client.get("/api/v1/mos/stats")
        assert response.status_code == 200
        
        data = response.json()
        assert "total_connections" in data
        assert "active_connections" in data
        assert "total_objects" in data
        assert "total_running_orders" in data
        assert "total_messages" in data
        assert "last_24h_messages" in data
    
    @pytest.mark.asyncio
    async def test_send_message(self, client: AsyncClient):
        """Test sending manual message"""
        response = await client.post(
            "/api/v1/mos/send-message",
            params={
                "connection_id": "test_connection",
                "message_content": "<heartbeat><mosID>test</mosID></heartbeat>"
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "success"
    
    @pytest.mark.asyncio
    async def test_broadcast_message(self, client: AsyncClient):
        """Test broadcasting message"""
        response = await client.post(
            "/api/v1/mos/broadcast",
            params={
                "message_content": "<heartbeat><mosID>test</mosID></heartbeat>"
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "success"


class TestValidation:
    """Test input validation"""
    
    @pytest.mark.asyncio
    async def test_invalid_limit_parameter(self, client: AsyncClient):
        """Test invalid limit parameter"""
        response = await client.get("/api/v1/mos/objects?limit=2000")
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_invalid_offset_parameter(self, client: AsyncClient):
        """Test invalid offset parameter"""
        response = await client.get("/api/v1/mos/objects?offset=-1")
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_invalid_direction_parameter(self, client: AsyncClient):
        """Test invalid direction parameter"""
        response = await client.get("/api/v1/mos/messages?direction=invalid")
        assert response.status_code == 422  # Validation error