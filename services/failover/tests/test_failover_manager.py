"""
Tests for Failover Manager
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

from src.services.failover_manager import (
    FailoverManager,
    FailoverState,
    FailoverType,
    RegionStatus,
    ServiceStatus
)
from src.models.schemas import (
    RegionHealth,
    ServiceHealth,
    FailoverEvent,
    FailoverRequest,
    RecoveryPointStatus
)


@pytest.fixture
async def failover_manager():
    """Create failover manager instance for testing"""
    manager = FailoverManager()
    
    # Mock Redis client
    manager.redis_client = AsyncMock()
    manager.redis_client.get = AsyncMock(return_value=None)
    manager.redis_client.set = AsyncMock()
    
    # Mock HTTP client
    manager.http_client = AsyncMock()
    
    # Mock notifications
    manager.notifications = AsyncMock()
    
    # Set up regions
    manager.regions = ["us-east-1", "us-west-2", "eu-west-1"]
    manager.primary_region = "us-east-1"
    manager.current_active_region = "us-east-1"
    
    # Initialize region health
    for region in manager.regions:
        manager.region_health[region] = RegionHealth(
            region=region,
            status=RegionStatus.ACTIVE if region == "us-east-1" else RegionStatus.STANDBY
        )
    
    # Mark as initialized
    manager._initialized = True
    
    return manager


@pytest.fixture
def mock_healthy_region():
    """Create a mock healthy region"""
    return RegionHealth(
        region="us-west-2",
        status=RegionStatus.STANDBY,
        health_percentage=100.0,
        services={
            "api_gateway": ServiceStatus.HEALTHY,
            "storage": ServiceStatus.HEALTHY,
            "database": ServiceStatus.HEALTHY
        },
        database_status={
            "postgresql": True,
            "mongodb": True,
            "redis": True
        }
    )


@pytest.fixture
def mock_unhealthy_region():
    """Create a mock unhealthy region"""
    return RegionHealth(
        region="us-east-1",
        status=RegionStatus.FAILED,
        health_percentage=30.0,
        consecutive_failures=5,
        services={
            "api_gateway": ServiceStatus.UNHEALTHY,
            "storage": ServiceStatus.HEALTHY,
            "database": ServiceStatus.UNHEALTHY
        },
        database_status={
            "postgresql": False,
            "mongodb": True,
            "redis": False
        }
    )


class TestFailoverManager:
    """Test Failover Manager functionality"""
    
    @pytest.mark.asyncio
    async def test_initialize(self, failover_manager):
        """Test failover manager initialization"""
        # Reset initialization
        failover_manager._initialized = False
        
        with patch('src.services.failover_manager.aioredis.from_url') as mock_redis:
            mock_redis.return_value = AsyncMock()
            
            await failover_manager.initialize()
            
            assert failover_manager._initialized
            assert failover_manager.redis_client is not None
            assert failover_manager.http_client is not None
    
    @pytest.mark.asyncio
    async def test_check_service_health_healthy(self, failover_manager):
        """Test checking health of a healthy service"""
        failover_manager.http_client.get = AsyncMock(
            return_value=Mock(status_code=200)
        )
        
        health = await failover_manager._check_service_health(
            "api_gateway",
            "http://api-gateway:8000/health",
            "us-east-1"
        )
        
        assert health.status == ServiceStatus.HEALTHY
        assert health.response_time_ms is not None
        assert health.error_count == 0
    
    @pytest.mark.asyncio
    async def test_check_service_health_unhealthy(self, failover_manager):
        """Test checking health of an unhealthy service"""
        failover_manager.http_client.get = AsyncMock(
            side_effect=Exception("Connection error")
        )
        
        health = await failover_manager._check_service_health(
            "api_gateway",
            "http://api-gateway:8000/health",
            "us-east-1"
        )
        
        assert health.status == ServiceStatus.UNHEALTHY
        assert health.error_count == 1
    
    @pytest.mark.asyncio
    async def test_check_region_health(self, failover_manager):
        """Test checking health of a region"""
        # Mock service health checks
        failover_manager._check_service_health = AsyncMock(
            return_value=ServiceHealth(
                service_name="test",
                region="us-east-1",
                status=ServiceStatus.HEALTHY
            )
        )
        
        # Mock database health check
        failover_manager._check_database_health = AsyncMock(
            return_value={"postgresql": True, "mongodb": True, "redis": True}
        )
        
        health = await failover_manager._check_region_health("us-east-1")
        
        assert health.status == RegionStatus.ACTIVE
        assert health.consecutive_failures == 0
        assert health.health_percentage > 0
    
    @pytest.mark.asyncio
    async def test_automatic_failover_trigger(self, failover_manager, mock_unhealthy_region, mock_healthy_region):
        """Test automatic failover triggering"""
        # Set up unhealthy primary region
        failover_manager.region_health["us-east-1"] = mock_unhealthy_region
        failover_manager.region_health["us-west-2"] = mock_healthy_region
        
        # Mock failover execution
        failover_manager.execute_failover = AsyncMock()
        
        # Enable auto-failover
        with patch.object(failover_manager, 'settings', AUTO_FAILOVER_ENABLED=True):
            await failover_manager._trigger_automatic_failover("us-east-1")
        
        # Verify failover was triggered
        failover_manager.execute_failover.assert_called_once()
        event = failover_manager.execute_failover.call_args[0][0]
        assert event.event_type == FailoverType.AUTOMATIC
        assert event.from_region == "us-east-1"
        assert event.to_region == "us-west-2"
    
    @pytest.mark.asyncio
    async def test_select_failover_target(self, failover_manager, mock_healthy_region):
        """Test selecting best failover target"""
        # Set up healthy regions
        failover_manager.region_health["us-west-2"] = mock_healthy_region
        failover_manager.region_health["eu-west-1"] = RegionHealth(
            region="eu-west-1",
            status=RegionStatus.STANDBY,
            health_percentage=95.0,
            latency_ms=150.0
        )
        
        target = await failover_manager._select_failover_target("us-east-1")
        
        # Should select us-west-2 due to better health
        assert target == "us-west-2"
    
    @pytest.mark.asyncio
    async def test_execute_failover(self, failover_manager):
        """Test executing failover"""
        event = FailoverEvent(
            event_type=FailoverType.MANUAL,
            state=FailoverState.FAILING_OVER,
            from_region="us-east-1",
            to_region="us-west-2",
            reason="Test failover",
            triggered_by="test_user"
        )
        
        # Mock failover steps
        failover_manager._create_failover_plan = AsyncMock()
        failover_manager._execute_pre_checks = AsyncMock()
        failover_manager._execute_failover_step = AsyncMock()
        failover_manager._execute_post_checks = AsyncMock()
        failover_manager._save_state = AsyncMock()
        
        await failover_manager.execute_failover(event)
        
        assert event.success
        assert event.completed_at is not None
        assert failover_manager.current_active_region == "us-west-2"
        assert failover_manager.region_health["us-west-2"].status == RegionStatus.ACTIVE
    
    @pytest.mark.asyncio
    async def test_manual_failover(self, failover_manager, mock_healthy_region):
        """Test manual failover"""
        failover_manager.region_health["us-west-2"] = mock_healthy_region
        failover_manager.execute_failover = AsyncMock()
        
        event = await failover_manager.manual_failover(
            target_region="us-west-2",
            reason="Maintenance",
            triggered_by="admin",
            force=False
        )
        
        assert event.event_type == FailoverType.MANUAL
        assert event.from_region == "us-east-1"
        assert event.to_region == "us-west-2"
        failover_manager.execute_failover.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_manual_failover_unhealthy_target(self, failover_manager, mock_unhealthy_region):
        """Test manual failover to unhealthy region without force"""
        failover_manager.region_health["us-west-2"] = mock_unhealthy_region
        
        with pytest.raises(Exception) as exc_info:
            await failover_manager.manual_failover(
                target_region="us-west-2",
                reason="Test",
                triggered_by="admin",
                force=False
            )
        
        assert "not healthy" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_check_rpo_status(self, failover_manager):
        """Test checking RPO status"""
        rpo_status = await failover_manager.check_rpo_status("us-east-1", "us-west-2")
        
        assert isinstance(rpo_status, RecoveryPointStatus)
        assert rpo_status.region == "us-west-2"
        assert rpo_status.rpo_target_minutes > 0
        assert isinstance(rpo_status.is_within_rpo, bool)
    
    @pytest.mark.asyncio
    async def test_check_data_consistency(self, failover_manager):
        """Test data consistency check"""
        consistency = await failover_manager.check_data_consistency(["us-east-1", "us-west-2"])
        
        assert consistency.regions_compared == ["us-east-1", "us-west-2"]
        assert consistency.records_checked > 0
        assert consistency.consistency_percentage >= 0
        assert consistency.consistency_percentage <= 100
    
    @pytest.mark.asyncio
    async def test_failback_scheduling(self, failover_manager):
        """Test automatic failback scheduling"""
        # Create a failover event from primary
        original_event = FailoverEvent(
            event_type=FailoverType.AUTOMATIC,
            state=FailoverState.FAILED_OVER,
            from_region="us-east-1",  # Primary
            to_region="us-west-2",
            reason="Primary failure"
        )
        
        # Mock settings and methods
        with patch.object(failover_manager, 'settings', AUTO_FAILBACK_ENABLED=True, FAILBACK_DELAY_MINUTES=0):
            failover_manager._check_region_health = AsyncMock(
                return_value=RegionHealth(
                    region="us-east-1",
                    status=RegionStatus.STANDBY,
                    health_percentage=100.0
                )
            )
            failover_manager.execute_failover = AsyncMock()
            
            # Use shorter delay for testing
            with patch('asyncio.sleep', return_value=None):
                await failover_manager._schedule_failback(original_event)
            
            # Verify failback was scheduled
            failover_manager.execute_failover.assert_called_once()
            failback_event = failover_manager.execute_failover.call_args[0][0]
            assert failback_event.from_region == "us-west-2"
            assert failback_event.to_region == "us-east-1"
    
    @pytest.mark.asyncio
    async def test_get_failover_status(self, failover_manager):
        """Test getting failover status"""
        status = await failover_manager.get_failover_status()
        
        assert status.current_state == FailoverState.NORMAL
        assert status.primary_region == "us-east-1"
        assert status.active_region == "us-east-1"
        assert len(status.standby_regions) == 2
        assert len(status.region_health) == 3
    
    @pytest.mark.asyncio
    async def test_update_load_balancer(self, failover_manager):
        """Test updating load balancer configuration"""
        await failover_manager._update_load_balancer("us-west-2")
        
        if failover_manager.load_balancer.algorithm.value == "weighted":
            assert failover_manager.load_balancer.weights["us-west-2"] == 1.0
            assert failover_manager.load_balancer.weights["us-east-1"] == 0.0
    
    @pytest.mark.asyncio
    async def test_save_and_load_state(self, failover_manager):
        """Test saving and loading failover state"""
        # Save state
        await failover_manager._save_state()
        
        # Verify Redis was called
        failover_manager.redis_client.set.assert_called_once()
        
        # Test loading state
        state_json = '{"current_active_region": "us-west-2", "failover_state": "normal"}'
        failover_manager.redis_client.get = AsyncMock(return_value=state_json)
        
        await failover_manager._load_state()
        
        assert failover_manager.current_active_region == "us-west-2"
        assert failover_manager.failover_state == FailoverState.NORMAL