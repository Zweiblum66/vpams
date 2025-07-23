"""
Tests for Edge Computing API endpoints
"""

import pytest
from httpx import AsyncClient
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.main import app
from src.models.schemas import (
    EdgeNode, NodeStatus, NodeType, ProcessingTask,
    TaskStatus, TaskType, TaskPriority, CacheStats
)


@pytest.fixture
async def client():
    """Create test client"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def auth_headers():
    """Create auth headers"""
    return {"Authorization": "Bearer test-token"}


@pytest.fixture
def api_key_headers():
    """Create API key headers"""
    return {"X-API-Key": "test-api-key"}


@pytest.fixture
def mock_current_user(monkeypatch):
    """Mock current user"""
    user = Mock()
    user.id = "test-user"
    user.username = "testuser"
    
    async def mock_get_current_user():
        return user
    
    monkeypatch.setattr("src.core.deps.get_current_user", mock_get_current_user)
    return user


@pytest.fixture
def mock_verify_api_key(monkeypatch):
    """Mock API key verification"""
    async def mock_verify():
        return True
    
    monkeypatch.setattr("src.core.deps.verify_api_key", mock_verify)


class TestNodeEndpoints:
    """Test node management endpoints"""
    
    @pytest.mark.asyncio
    async def test_register_node(self, client, mock_verify_api_key, api_key_headers):
        """Test node registration"""
        node_data = {
            "node_id": "test-node",
            "node_type": "standard",
            "location": "us-west-2",
            "capabilities": ["transcode", "thumbnail"],
            "resources": {"cpu_count": 4}
        }
        
        with patch("src.api.routes.get_db") as mock_get_db:
            mock_db = AsyncMock()
            mock_db.get.return_value = None  # Node doesn't exist
            mock_db.commit = AsyncMock()
            mock_db.refresh = AsyncMock()
            mock_get_db.return_value.__aenter__.return_value = mock_db
            
            response = await client.post(
                "/api/v1/edge/nodes/register",
                json=node_data,
                headers=api_key_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["node_id"] == "test-node"
    
    @pytest.mark.asyncio
    async def test_list_nodes(self, client, mock_current_user, auth_headers):
        """Test listing nodes"""
        mock_nodes = [
            Mock(
                node_id="node-1",
                node_type=NodeType.STANDARD,
                location="us-west-2",
                status=NodeStatus.ONLINE,
                capabilities=["transcode"],
                resources={},
                performance_metrics={},
                last_heartbeat=datetime.utcnow(),
                metadata={}
            )
        ]
        
        with patch("src.api.routes.get_db") as mock_get_db:
            mock_db = AsyncMock()
            mock_result = Mock()
            mock_result.scalars.return_value.all.return_value = mock_nodes
            mock_db.execute = AsyncMock(return_value=mock_result)
            mock_get_db.return_value.__aenter__.return_value = mock_db
            
            response = await client.get(
                "/api/v1/edge/nodes",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["node_id"] == "node-1"
    
    @pytest.mark.asyncio
    async def test_update_node(self, client, mock_current_user, auth_headers):
        """Test updating node"""
        node_id = "test-node"
        update_data = {
            "status": "busy",
            "performance_metrics": {"cpu_usage": 50.0}
        }
        
        mock_node = Mock(
            node_id=node_id,
            node_type=NodeType.STANDARD,
            location="us-west-2",
            status=NodeStatus.ONLINE,
            capabilities=["transcode"],
            resources={},
            performance_metrics={},
            last_heartbeat=datetime.utcnow(),
            metadata={}
        )
        
        with patch("src.api.routes.get_db") as mock_get_db:
            mock_db = AsyncMock()
            mock_db.get.return_value = mock_node
            mock_db.commit = AsyncMock()
            mock_db.refresh = AsyncMock()
            mock_get_db.return_value.__aenter__.return_value = mock_db
            
            response = await client.patch(
                f"/api/v1/edge/nodes/{node_id}",
                json=update_data,
                headers=auth_headers
            )
            
            assert response.status_code == 200
            assert mock_node.status == "busy"


class TestTaskEndpoints:
    """Test task management endpoints"""
    
    @pytest.mark.asyncio
    async def test_create_task(self, client, mock_current_user, auth_headers):
        """Test creating task"""
        task_data = {
            "task_type": "video_transcode",
            "asset_id": "asset-123",
            "parameters": {"preset": "medium"},
            "priority": "normal"
        }
        
        with patch("src.api.routes.get_db") as mock_get_db:
            mock_db = AsyncMock()
            mock_db.commit = AsyncMock()
            mock_db.refresh = AsyncMock()
            mock_get_db.return_value.__aenter__.return_value = mock_db
            
            with patch("src.api.routes.get_edge_manager") as mock_get_manager:
                mock_manager = Mock()
                mock_manager.is_master = True
                mock_get_manager.return_value = mock_manager
                
                response = await client.post(
                    "/api/v1/edge/tasks",
                    json=task_data,
                    headers=auth_headers
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["task_type"] == "video_transcode"
                assert data["asset_id"] == "asset-123"
    
    @pytest.mark.asyncio
    async def test_get_task_progress(self, client, mock_current_user, auth_headers):
        """Test getting task progress"""
        task_id = "task-123"
        
        with patch("src.api.routes.get_task_processor") as mock_get_processor:
            mock_processor = Mock()
            mock_processor.get_task_progress = AsyncMock(return_value=75.5)
            mock_get_processor.return_value = mock_processor
            
            response = await client.get(
                f"/api/v1/edge/tasks/{task_id}/progress",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["task_id"] == task_id
            assert data["progress"] == 75.5


class TestCacheEndpoints:
    """Test cache management endpoints"""
    
    @pytest.mark.asyncio
    async def test_get_cache_stats(self, client, mock_current_user, auth_headers):
        """Test getting cache statistics"""
        mock_stats = CacheStats(
            node_id="test-node",
            total_size_gb=100.0,
            used_size_gb=50.0,
            available_size_gb=50.0,
            cache_hit_rate=0.85,
            total_entries=1000,
            active_entries=950,
            evicted_entries=50,
            avg_entry_size_mb=50.0
        )
        
        with patch("src.api.routes.get_cache_manager") as mock_get_cache:
            mock_cache = Mock()
            mock_cache.get_stats = AsyncMock(return_value=mock_stats)
            mock_get_cache.return_value = mock_cache
            
            response = await client.get(
                "/api/v1/edge/cache/stats",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["cache_hit_rate"] == 0.85
            assert data["used_size_gb"] == 50.0
    
    @pytest.mark.asyncio
    async def test_clear_cache(self, client, mock_current_user, auth_headers):
        """Test clearing cache"""
        with patch("src.api.routes.get_cache_manager") as mock_get_cache:
            mock_cache = Mock()
            mock_cache.clear = AsyncMock()
            mock_get_cache.return_value = mock_cache
            
            response = await client.post(
                "/api/v1/edge/cache/clear",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            assert response.json()["message"] == "Cache cleared"
            mock_cache.clear.assert_called_once()


class TestClusterEndpoints:
    """Test cluster management endpoints"""
    
    @pytest.mark.asyncio
    async def test_get_cluster_status(self, client, mock_current_user, auth_headers):
        """Test getting cluster status"""
        mock_status = Mock(
            total_nodes=5,
            online_nodes=4,
            total_capacity={"cpu_cores": 40},
            used_capacity={"cpu_percent": 60.0},
            active_tasks=10,
            completed_tasks_24h=100,
            failed_tasks_24h=5,
            average_task_duration=120.0,
            nodes=[]
        )
        
        with patch("src.api.routes.get_edge_manager") as mock_get_manager:
            mock_manager = Mock()
            mock_manager.get_cluster_status = AsyncMock(return_value=mock_status)
            mock_get_manager.return_value = mock_manager
            
            response = await client.get(
                "/api/v1/edge/cluster/status",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["total_nodes"] == 5
            assert data["online_nodes"] == 4


class TestHealthCheck:
    """Test health check endpoint"""
    
    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """Test health check"""
        with patch("src.api.routes.get_db") as mock_get_db:
            mock_db = AsyncMock()
            mock_db.execute = AsyncMock()
            mock_get_db.return_value.__aenter__.return_value = mock_db
            
            response = await client.get("/api/v1/edge/health")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["service"] == "edge-computing"