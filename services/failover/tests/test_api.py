"""
Tests for Failover API endpoints
"""

import pytest
from httpx import AsyncClient
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock

from src.main import app
from src.services.failover_manager import FailoverManager, FailoverState, RegionStatus
from src.models.schemas import (
    FailoverStatus,
    RegionHealth,
    FailoverEvent,
    RecoveryPointStatus,
    DataConsistencyCheck
)


@pytest.fixture
async def client():
    """Create test client"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_failover_manager(monkeypatch):
    """Mock failover manager for testing"""
    manager = Mock(spec=FailoverManager)
    
    # Mock regions
    manager.regions = ["us-east-1", "us-west-2", "eu-west-1"]
    manager.primary_region = "us-east-1"
    manager.current_active_region = "us-east-1"
    
    # Mock region health
    manager.region_health = {
        "us-east-1": RegionHealth(
            region="us-east-1",
            status=RegionStatus.ACTIVE,
            health_percentage=100.0
        ),
        "us-west-2": RegionHealth(
            region="us-west-2",
            status=RegionStatus.STANDBY,
            health_percentage=100.0
        )
    }
    
    # Mock methods
    manager.get_failover_status = AsyncMock(
        return_value=FailoverStatus(
            current_state=FailoverState.NORMAL,
            primary_region="us-east-1",
            active_region="us-east-1",
            standby_regions=["us-west-2", "eu-west-1"],
            region_health=manager.region_health
        )
    )
    
    manager.manual_failover = AsyncMock()
    manager.execute_failover = AsyncMock()
    manager.check_rpo_status = AsyncMock()
    manager.check_data_consistency = AsyncMock()
    manager.metrics = Mock()
    manager.metrics.get_failover_statistics = Mock(return_value={})
    manager.notifications = Mock()
    manager.notifications.test_notifications = AsyncMock(return_value={})
    
    manager.failover_history = []
    manager.failover_state = FailoverState.NORMAL
    manager.active_failover = None
    
    # Mock service health
    manager.service_health = {}
    
    # Patch the dependency
    async def mock_get_failover_manager():
        return manager
    
    monkeypatch.setattr("src.api.routes.get_failover_manager", mock_get_failover_manager)
    monkeypatch.setattr("src.core.deps.get_failover_manager", mock_get_failover_manager)
    
    return manager


@pytest.fixture
def auth_headers():
    """Create authentication headers"""
    return {"Authorization": "Bearer test-token"}


@pytest.fixture
def mock_current_user(monkeypatch):
    """Mock current user for testing"""
    user = Mock()
    user.id = "user123"
    user.username = "testuser"
    
    async def mock_get_current_user():
        return user
    
    monkeypatch.setattr("src.api.routes.get_current_user", mock_get_current_user)
    monkeypatch.setattr("src.core.deps.get_current_user", mock_get_current_user)
    
    return user


class TestFailoverAPI:
    """Test Failover API endpoints"""
    
    @pytest.mark.asyncio
    async def test_get_failover_status(self, client, mock_failover_manager, mock_current_user, auth_headers):
        """Test getting failover status"""
        response = await client.get("/api/v1/failover/status", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["current_state"] == "normal"
        assert data["active_region"] == "us-east-1"
        assert len(data["standby_regions"]) == 2
    
    @pytest.mark.asyncio
    async def test_get_region_health(self, client, mock_failover_manager, mock_current_user, auth_headers):
        """Test getting region health"""
        response = await client.get("/api/v1/failover/regions", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["region"] in ["us-east-1", "us-west-2"]
    
    @pytest.mark.asyncio
    async def test_get_region_health_specific(self, client, mock_failover_manager, mock_current_user, auth_headers):
        """Test getting health of specific region"""
        response = await client.get("/api/v1/failover/regions?region=us-east-1", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["region"] == "us-east-1"
    
    @pytest.mark.asyncio
    async def test_trigger_manual_failover(self, client, mock_failover_manager, mock_current_user, auth_headers):
        """Test triggering manual failover"""
        mock_event = FailoverEvent(
            event_type="manual",
            state="failing_over",
            from_region="us-east-1",
            to_region="us-west-2",
            reason="Test failover",
            triggered_by="testuser"
        )
        
        mock_failover_manager.manual_failover.return_value = mock_event
        
        request_data = {
            "target_region": "us-west-2",
            "reason": "Test failover"
        }
        
        response = await client.post(
            "/api/v1/failover/failover",
            json=request_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["event_type"] == "manual"
        assert data["to_region"] == "us-west-2"
    
    @pytest.mark.asyncio
    async def test_trigger_failback(self, client, mock_failover_manager, mock_current_user, auth_headers):
        """Test triggering failback"""
        # Set current region to secondary
        mock_failover_manager.current_active_region = "us-west-2"
        
        response = await client.post("/api/v1/failover/failback", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "Failback initiated" in data["message"]
    
    @pytest.mark.asyncio
    async def test_get_failover_history(self, client, mock_failover_manager, mock_current_user, auth_headers):
        """Test getting failover history"""
        # Add some history
        mock_failover_manager.failover_history = [
            FailoverEvent(
                event_type="automatic",
                state="failed_over",
                from_region="us-east-1",
                to_region="us-west-2",
                reason="Health check failure",
                started_at=datetime.utcnow() - timedelta(hours=1),
                completed_at=datetime.utcnow() - timedelta(minutes=50),
                success=True
            )
        ]
        
        response = await client.get("/api/v1/failover/history", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["event_type"] == "automatic"
    
    @pytest.mark.asyncio
    async def test_get_failover_plans(self, client, mock_failover_manager, mock_current_user, auth_headers):
        """Test getting failover plans"""
        response = await client.get("/api/v1/failover/plans", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    @pytest.mark.asyncio
    async def test_test_failover(self, client, mock_failover_manager, mock_current_user, auth_headers):
        """Test failover simulation"""
        mock_failover_manager.check_rpo_status.return_value = RecoveryPointStatus(
            region="us-west-2",
            rpo_target_minutes=5,
            current_lag_minutes=3,
            is_within_rpo=True,
            last_sync_time=datetime.utcnow()
        )
        
        response = await client.post(
            "/api/v1/failover/test-failover?target_region=us-west-2",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["target_region"] == "us-west-2"
        assert "pre_checks_passed" in data
    
    @pytest.mark.asyncio
    async def test_get_rpo_status(self, client, mock_failover_manager, mock_current_user, auth_headers):
        """Test getting RPO status"""
        mock_failover_manager.check_rpo_status.return_value = RecoveryPointStatus(
            region="us-west-2",
            rpo_target_minutes=5,
            current_lag_minutes=3,
            is_within_rpo=True,
            last_sync_time=datetime.utcnow()
        )
        
        response = await client.get("/api/v1/failover/rpo-status", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    @pytest.mark.asyncio
    async def test_check_data_consistency(self, client, mock_failover_manager, mock_current_user, auth_headers):
        """Test data consistency check"""
        mock_failover_manager.check_data_consistency.return_value = DataConsistencyCheck(
            regions_compared=["us-east-1", "us-west-2"],
            check_type="sample",
            records_checked=10000,
            inconsistencies_found=5
        )
        
        request_data = {
            "regions": ["us-east-1", "us-west-2"],
            "check_type": "sample"
        }
        
        response = await client.post(
            "/api/v1/failover/consistency-check",
            json=request_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["records_checked"] == 10000
    
    @pytest.mark.asyncio
    async def test_get_failover_metrics(self, client, mock_failover_manager, mock_current_user, auth_headers):
        """Test getting failover metrics"""
        response = await client.get("/api/v1/failover/metrics", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "total_failovers" in data
        assert "successful_failovers" in data
    
    @pytest.mark.asyncio
    async def test_get_system_topology(self, client, mock_failover_manager, mock_current_user, auth_headers):
        """Test getting system topology"""
        mock_failover_manager._get_region_priority = Mock(return_value=100)
        
        response = await client.get("/api/v1/failover/topology", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "regions" in data
        assert "active_connections" in data
    
    @pytest.mark.asyncio
    async def test_update_configuration(self, client, mock_current_user, auth_headers):
        """Test updating failover configuration"""
        request_data = {
            "auto_failover": True,
            "auto_failback": False,
            "failover_threshold": 5
        }
        
        response = await client.put(
            "/api/v1/failover/configuration",
            json=request_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["updates"]["auto_failover_enabled"] is True
    
    @pytest.mark.asyncio
    async def test_test_notifications(self, client, mock_failover_manager, mock_current_user, auth_headers):
        """Test notification channels"""
        mock_failover_manager.notifications.test_notifications.return_value = {
            "email": True,
            "slack": False
        }
        
        response = await client.post("/api/v1/failover/notifications/test", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["results"]["email"] is True
    
    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """Test health check endpoint"""
        response = await client.get("/api/v1/failover/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "failover"
    
    @pytest.mark.asyncio
    async def test_invalid_region(self, client, mock_failover_manager, mock_current_user, auth_headers):
        """Test failover to invalid region"""
        request_data = {
            "target_region": "invalid-region",
            "reason": "Test"
        }
        
        response = await client.post(
            "/api/v1/failover/failover",
            json=request_data,
            headers=auth_headers
        )
        
        assert response.status_code == 400
        assert "Invalid target region" in response.json()["detail"]