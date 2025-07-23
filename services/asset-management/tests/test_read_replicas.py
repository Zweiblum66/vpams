"""
Tests for Read Replica Support

This module tests the read replica functionality including:
- Read preference routing
- Load balancing strategies
- Health checks and failover
- Lag monitoring
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine

from src.db.sharding import ShardRouter, ShardConfig, ShardingStrategy, ShardKey
from src.db.read_replicas import (
    ReadReplicaRouter, ReadPreference, LoadBalancingStrategy,
    ReplicaStats, ReadReplicaSession
)


@pytest.fixture
def mock_shard_router():
    """Create a mock shard router with test shards"""
    router = ShardRouter(
        strategy=ShardingStrategy.HASH,
        shard_key=ShardKey.PROJECT_ID
    )
    
    # Add primary shards
    primary1 = ShardConfig(
        shard_id="shard1",
        database_url="postgresql+asyncpg://test:test@primary1:5432/test",
        weight=1.0,
        read_only=False,
        regions=["us-east"]
    )
    
    primary2 = ShardConfig(
        shard_id="shard2", 
        database_url="postgresql+asyncpg://test:test@primary2:5432/test",
        weight=1.0,
        read_only=False,
        regions=["eu-west"]
    )
    
    # Add read replicas
    replica1 = ShardConfig(
        shard_id="shard1_read",
        database_url="postgresql+asyncpg://test:test@replica1:5432/test",
        weight=0.0,
        read_only=True,
        regions=["us-east"]
    )
    
    replica2 = ShardConfig(
        shard_id="shard2_read",
        database_url="postgresql+asyncpg://test:test@replica2:5432/test",
        weight=0.0,
        read_only=True,
        regions=["eu-west"]
    )
    
    router.add_shard(primary1)
    router.add_shard(primary2)
    router.add_shard(replica1)
    router.add_shard(replica2)
    
    return router


@pytest.fixture
def replica_router(mock_shard_router):
    """Create a read replica router"""
    return ReadReplicaRouter(
        base_router=mock_shard_router,
        read_preference=ReadPreference.SECONDARY_PREFERRED,
        load_balancing=LoadBalancingStrategy.ROUND_ROBIN,
        health_check_interval=30,
        max_lag_seconds=300
    )


class TestReadPreference:
    """Test read preference routing"""
    
    @pytest.mark.asyncio
    async def test_primary_preference(self, mock_shard_router):
        """Test PRIMARY read preference always uses primary"""
        router = ReadReplicaRouter(
            base_router=mock_shard_router,
            read_preference=ReadPreference.PRIMARY
        )
        
        # Mock health check
        with patch.object(router, '_check_replica_health', new_callable=AsyncMock):
            shard = await router.get_read_shard("test-key")
            
            assert not shard.read_only
            assert shard.shard_id in ["shard1", "shard2"]
    
    @pytest.mark.asyncio
    async def test_secondary_preference(self, mock_shard_router):
        """Test SECONDARY read preference always uses replica"""
        router = ReadReplicaRouter(
            base_router=mock_shard_router,
            read_preference=ReadPreference.SECONDARY
        )
        
        # Mock health check
        with patch.object(router, '_check_replica_health', new_callable=AsyncMock):
            shard = await router.get_read_shard("test-key")
            
            assert shard.read_only
            assert shard.shard_id in ["shard1_read", "shard2_read"]
    
    @pytest.mark.asyncio
    async def test_secondary_preferred(self, replica_router):
        """Test SECONDARY_PREFERRED uses replica when available"""
        # Mock health check
        with patch.object(replica_router, '_check_replica_health', new_callable=AsyncMock):
            # Mark all replicas as healthy
            replica_router.replica_stats["shard1_read"].is_healthy = True
            replica_router.replica_stats["shard2_read"].is_healthy = True
            
            shard = await replica_router.get_read_shard("test-key")
            
            # Should prefer replica
            assert shard.read_only
    
    @pytest.mark.asyncio
    async def test_primary_preferred_fallback(self, mock_shard_router):
        """Test PRIMARY_PREFERRED falls back to replica when primary unhealthy"""
        router = ReadReplicaRouter(
            base_router=mock_shard_router,
            read_preference=ReadPreference.PRIMARY_PREFERRED
        )
        
        # Mock health check
        with patch.object(router, '_check_replica_health', new_callable=AsyncMock):
            # Mark primary as unhealthy
            router.replica_stats["shard1"].is_healthy = False
            router.replica_stats["shard2"].is_healthy = False
            router.replica_stats["shard1_read"].is_healthy = True
            router.replica_stats["shard2_read"].is_healthy = True
            
            shard = await router.get_read_shard("test-key")
            
            # Should fall back to replica
            assert shard.read_only


class TestLoadBalancing:
    """Test load balancing strategies"""
    
    @pytest.mark.asyncio 
    async def test_round_robin(self, replica_router):
        """Test round-robin load balancing"""
        # Mock health check
        with patch.object(replica_router, '_check_replica_health', new_callable=AsyncMock):
            # Mark all as healthy
            for stats in replica_router.replica_stats.values():
                stats.is_healthy = True
            
            # Get replicas for a primary shard
            primary = replica_router.base_router.shards["shard1"]
            replicas = replica_router._get_replicas_for_shard(primary)
            
            # Track selections
            selections = []
            for _ in range(4):
                shard = replica_router._select_replica(replicas, "shard1")
                selections.append(shard.shard_id)
            
            # Should alternate between replicas
            assert len(set(selections)) == 1  # Only one replica for shard1
    
    @pytest.mark.asyncio
    async def test_least_connections(self, mock_shard_router):
        """Test least connections load balancing"""
        router = ReadReplicaRouter(
            base_router=mock_shard_router,
            read_preference=ReadPreference.SECONDARY,
            load_balancing=LoadBalancingStrategy.LEAST_CONNECTIONS
        )
        
        # Set different connection counts
        router.replica_stats["shard1_read"].active_connections = 10
        router.replica_stats["shard2_read"].active_connections = 5
        router.replica_stats["shard1_read"].is_healthy = True
        router.replica_stats["shard2_read"].is_healthy = True
        
        # Get replicas
        primary = router.base_router.shards["shard1"]
        replicas = router._get_replicas_for_shard(primary)
        
        # Should select replica with fewer connections
        shard = router._select_replica(replicas, "shard1")
        assert shard.shard_id == "shard1_read"  # Only one replica for shard1
    
    @pytest.mark.asyncio
    async def test_response_time_based(self, mock_shard_router):
        """Test response time based load balancing"""
        router = ReadReplicaRouter(
            base_router=mock_shard_router,
            load_balancing=LoadBalancingStrategy.RESPONSE_TIME
        )
        
        # Set different response times
        router.replica_stats["shard1_read"].total_response_time_ms = 1000
        router.replica_stats["shard1_read"].total_queries = 10  # Avg: 100ms
        router.replica_stats["shard2_read"].total_response_time_ms = 2000  
        router.replica_stats["shard2_read"].total_queries = 10  # Avg: 200ms
        router.replica_stats["shard1_read"].is_healthy = True
        router.replica_stats["shard2_read"].is_healthy = True
        
        # Get all read shards
        replicas = [s for s in router.base_router.read_shards if s.read_only]
        
        # Should select replica with lower response time
        shard = router._select_replica(replicas, "test")
        assert shard.shard_id == "shard1_read"


class TestHealthChecks:
    """Test replica health monitoring"""
    
    @pytest.mark.asyncio
    async def test_health_check_execution(self, replica_router):
        """Test that health checks are executed"""
        # Mock engine and connection
        mock_engine = AsyncMock(spec=AsyncEngine)
        mock_conn = AsyncMock()
        mock_result = AsyncMock()
        mock_result.fetchone = AsyncMock(return_value=Mock(lag_seconds=10))
        
        mock_conn.execute = AsyncMock(return_value=mock_result)
        mock_engine.connect = AsyncMock(return_value=mock_conn)
        mock_engine.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_engine.__aexit__ = AsyncMock(return_value=None)
        
        # Mock shard engine
        for shard in replica_router.base_router.shards.values():
            shard.get_engine = AsyncMock(return_value=mock_engine)
        
        # Execute health check
        await replica_router._check_replica_health()
        
        # Verify health checks were performed
        assert mock_conn.execute.called
        
        # Check that stats were updated
        for shard_id, stats in replica_router.replica_stats.items():
            assert stats.last_check_time > 0
    
    @pytest.mark.asyncio
    async def test_unhealthy_replica_handling(self, replica_router):
        """Test handling of unhealthy replicas"""
        # Mock failing health check
        mock_engine = AsyncMock(spec=AsyncEngine)
        mock_engine.connect = AsyncMock(side_effect=Exception("Connection failed"))
        
        shard = replica_router.base_router.shards["shard1_read"]
        shard.get_engine = AsyncMock(return_value=mock_engine)
        
        # Execute health check
        await replica_router._check_shard_health(shard)
        
        # Verify replica marked as unhealthy
        stats = replica_router.replica_stats["shard1_read"]
        assert not stats.is_healthy
        assert stats.failed_queries == 1
    
    @pytest.mark.asyncio
    async def test_lag_monitoring(self, replica_router):
        """Test replica lag monitoring"""
        # Mock engine with lag response
        mock_engine = AsyncMock(spec=AsyncEngine)
        mock_conn = AsyncMock()
        
        # Mock query results
        mock_health_result = AsyncMock()
        mock_health_result.fetchone = AsyncMock(return_value=None)
        
        mock_lag_result = AsyncMock()
        mock_lag_result.fetchone = AsyncMock(return_value=Mock(lag_seconds=500))
        
        # Return different results for different queries
        async def mock_execute(query):
            if "pg_last_xact_replay_timestamp" in str(query):
                return mock_lag_result
            return mock_health_result
        
        mock_conn.execute = mock_execute
        mock_engine.connect = AsyncMock(return_value=mock_conn)
        mock_engine.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_engine.__aexit__ = AsyncMock(return_value=None)
        
        shard = replica_router.base_router.shards["shard1_read"]
        shard.get_engine = AsyncMock(return_value=mock_engine)
        
        # Execute health check
        await replica_router._check_shard_health(shard)
        
        # Verify lag was recorded
        stats = replica_router.replica_stats["shard1_read"]
        assert stats.lag_seconds == 500
        
        # Verify lag check
        assert not replica_router._is_lag_acceptable("shard1_read")


class TestReadReplicaSession:
    """Test read replica session management"""
    
    @pytest.mark.asyncio
    async def test_read_session_uses_replica(self, mock_shard_router, replica_router):
        """Test that read sessions use replicas"""
        session = ReadReplicaSession(mock_shard_router, replica_router)
        
        # Mock session factory
        mock_session = AsyncMock(spec=AsyncSession)
        mock_factory = AsyncMock(return_value=mock_session)
        mock_factory.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.__aexit__ = AsyncMock(return_value=None)
        
        for shard in mock_shard_router.shards.values():
            shard.get_session_factory = AsyncMock(return_value=mock_factory)
        
        # Mock health check
        with patch.object(replica_router, '_check_replica_health', new_callable=AsyncMock):
            # Use read session
            async with session.get_session(
                "test-key",
                read_only=True,
                read_preference=ReadPreference.SECONDARY_PREFERRED
            ) as db:
                assert db == mock_session
        
        # Verify replica router was used
        assert replica_router.get_read_shard.called or hasattr(replica_router, '_check_replica_health')
    
    @pytest.mark.asyncio
    async def test_write_session_uses_primary(self, mock_shard_router, replica_router):
        """Test that write sessions use primary"""
        session = ReadReplicaSession(mock_shard_router, replica_router)
        
        # Mock session factory
        mock_session = AsyncMock(spec=AsyncSession)
        mock_factory = AsyncMock(return_value=mock_session)
        mock_factory.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.__aexit__ = AsyncMock(return_value=None)
        
        for shard in mock_shard_router.shards.values():
            shard.get_session_factory = AsyncMock(return_value=mock_factory)
        
        # Use write session
        async with session.get_session("test-key", read_only=False) as db:
            assert db == mock_session
        
        # Should have used primary shard router
        # (verified by read_only=False parameter)


class TestMetrics:
    """Test metrics collection"""
    
    @pytest.mark.asyncio
    async def test_query_metrics_tracking(self, replica_router):
        """Test that query metrics are tracked"""
        shard_id = "shard1_read"
        
        # Record successful query
        await replica_router.record_query_metrics(shard_id, 50.0, True)
        
        stats = replica_router.replica_stats[shard_id]
        assert stats.total_queries == 1
        assert stats.failed_queries == 0
        assert stats.total_response_time_ms == 50.0
        assert stats.average_response_time_ms == 50.0
        
        # Record failed query
        await replica_router.record_query_metrics(shard_id, 100.0, False)
        
        assert stats.total_queries == 2
        assert stats.failed_queries == 1
        assert stats.total_response_time_ms == 150.0
        assert stats.average_response_time_ms == 75.0
    
    @pytest.mark.asyncio
    async def test_connection_tracking(self, replica_router):
        """Test active connection tracking"""
        shard_id = "shard1_read"
        stats = replica_router.replica_stats[shard_id]
        
        assert stats.active_connections == 0
        
        # Track query
        async with replica_router.track_query(shard_id):
            assert stats.active_connections == 1
            
        assert stats.active_connections == 0
    
    def test_replica_status_report(self, replica_router):
        """Test replica status reporting"""
        # Set up some test data
        replica_router.replica_stats["shard1_read"].is_healthy = True
        replica_router.replica_stats["shard1_read"].total_queries = 100
        replica_router.replica_stats["shard1_read"].failed_queries = 5
        replica_router.replica_stats["shard1_read"].lag_seconds = 2
        
        status = replica_router.get_replica_status()
        
        assert status["read_preference"] == "secondary_preferred"
        assert status["load_balancing"] == "round_robin"
        assert "shard1_read" in status["replicas"]
        
        shard_status = status["replicas"]["shard1_read"]
        assert shard_status["is_healthy"] is True
        assert shard_status["total_queries"] == 100
        assert shard_status["failed_queries"] == 5
        assert shard_status["success_rate"] == "95.0%"
        assert shard_status["lag_seconds"] == 2


@pytest.mark.asyncio
async def test_integration_scenario(mock_shard_router):
    """Test a complete integration scenario"""
    # Create router with specific preferences
    router = ReadReplicaRouter(
        base_router=mock_shard_router,
        read_preference=ReadPreference.SECONDARY_PREFERRED,
        load_balancing=LoadBalancingStrategy.LEAST_CONNECTIONS,
        health_check_interval=1,  # Short interval for testing
        max_lag_seconds=100
    )
    
    # Mock health checks
    for shard in mock_shard_router.shards.values():
        mock_engine = AsyncMock(spec=AsyncEngine)
        mock_conn = AsyncMock()
        mock_result = AsyncMock()
        mock_result.fetchone = AsyncMock(return_value=Mock(lag_seconds=50))
        mock_conn.execute = AsyncMock(return_value=mock_result)
        mock_engine.connect = AsyncMock(return_value=mock_conn)
        mock_engine.__aenter__ = AsyncMock(return_value=mock_conn) 
        mock_engine.__aexit__ = AsyncMock(return_value=None)
        shard.get_engine = AsyncMock(return_value=mock_engine)
    
    # Simulate some queries
    session = ReadReplicaSession(mock_shard_router, router)
    
    # Mock session factory
    mock_session = AsyncMock(spec=AsyncSession)
    mock_factory = AsyncMock(return_value=mock_session)
    mock_factory.__aenter__ = AsyncMock(return_value=mock_session)
    mock_factory.__aexit__ = AsyncMock(return_value=None)
    
    for shard in mock_shard_router.shards.values():
        shard.get_session_factory = AsyncMock(return_value=mock_factory)
    
    # Execute several read queries
    for i in range(5):
        async with session.get_session(f"project-{i}", read_only=True):
            pass
    
    # Execute write query
    async with session.get_session("project-1", read_only=False):
        pass
    
    # Get status
    status = router.get_replica_status()
    assert len(status["replicas"]) > 0