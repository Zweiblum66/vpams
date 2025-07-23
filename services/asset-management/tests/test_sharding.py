"""
Tests for database sharding functionality
"""

import pytest
from uuid import UUID, uuid4
from unittest.mock import Mock, AsyncMock, patch
import hashlib

from src.db.sharding import (
    ShardingStrategy, ShardKey, ShardConfig, ShardRouter,
    ShardedSession, ShardedRepository, AssetShardedRepository
)
from src.core.sharding_config import (
    ShardingConfiguration, ShardDefinition, ShardingPolicy
)
from src.db.models import Asset, AssetStatus, AssetType


@pytest.fixture
def shard_config():
    """Create test shard configuration"""
    return ShardConfig(
        shard_id="test_shard1",
        database_url="postgresql+asyncpg://test:test@localhost:5432/test_shard1",
        weight=1.0,
        read_only=False
    )


@pytest.fixture
def shard_router():
    """Create test shard router"""
    router = ShardRouter(
        strategy=ShardingStrategy.HASH,
        shard_key=ShardKey.PROJECT_ID
    )
    
    # Add test shards
    for i in range(3):
        config = ShardConfig(
            shard_id=f"shard{i+1}",
            database_url=f"postgresql+asyncpg://test:test@localhost:5432/test_shard{i+1}",
            weight=1.0
        )
        router.add_shard(config)
    
    return router


@pytest.fixture
def sharding_configuration():
    """Create test sharding configuration"""
    return ShardingConfiguration(
        enabled=True,
        strategy="hash",
        shard_key="project_id",
        shards=[
            ShardDefinition(
                shard_id="shard1",
                database_url="postgresql+asyncpg://test:test@localhost:5432/test_shard1"
            ),
            ShardDefinition(
                shard_id="shard2",
                database_url="postgresql+asyncpg://test:test@localhost:5432/test_shard2"
            ),
            ShardDefinition(
                shard_id="shard3",
                database_url="postgresql+asyncpg://test:test@localhost:5432/test_shard3"
            )
        ]
    )


class TestShardConfig:
    """Test ShardConfig class"""
    
    def test_shard_config_creation(self, shard_config):
        """Test creating shard configuration"""
        assert shard_config.shard_id == "test_shard1"
        assert shard_config.weight == 1.0
        assert shard_config.read_only is False
        assert shard_config.regions == []
    
    def test_shard_config_with_regions(self):
        """Test shard config with regions"""
        config = ShardConfig(
            shard_id="regional_shard",
            database_url="postgresql+asyncpg://test:test@localhost:5432/test",
            regions=["us-east", "us-west"]
        )
        assert config.regions == ["us-east", "us-west"]


class TestShardRouter:
    """Test ShardRouter class"""
    
    def test_add_shard(self, shard_router):
        """Test adding shards to router"""
        assert len(shard_router.shards) == 3
        assert len(shard_router.write_shards) == 3
        assert len(shard_router.read_shards) == 3
    
    def test_add_read_only_shard(self):
        """Test adding read-only shard"""
        router = ShardRouter()
        
        # Add write shard
        write_shard = ShardConfig(
            shard_id="write_shard",
            database_url="postgresql+asyncpg://test:test@localhost:5432/write",
            read_only=False
        )
        router.add_shard(write_shard)
        
        # Add read-only shard
        read_shard = ShardConfig(
            shard_id="read_shard",
            database_url="postgresql+asyncpg://test:test@localhost:5432/read",
            read_only=True
        )
        router.add_shard(read_shard)
        
        assert len(router.write_shards) == 1
        assert len(router.read_shards) == 2
    
    def test_hash_sharding_distribution(self, shard_router):
        """Test that hash sharding distributes keys across shards"""
        # Generate test keys
        keys = [f"project_{i}" for i in range(100)]
        shard_counts = {f"shard{i+1}": 0 for i in range(3)}
        
        # Route each key
        for key in keys:
            shard = shard_router.get_shard_for_key(key)
            shard_counts[shard.shard_id] += 1
        
        # Check distribution (should be roughly equal)
        for count in shard_counts.values():
            assert 20 < count < 50  # Allow for some variance
    
    def test_consistent_hash_routing(self, shard_router):
        """Test that same key always routes to same shard"""
        test_key = "project_123"
        
        # Route same key multiple times
        shard1 = shard_router.get_shard_for_key(test_key)
        shard2 = shard_router.get_shard_for_key(test_key)
        shard3 = shard_router.get_shard_for_key(test_key)
        
        assert shard1.shard_id == shard2.shard_id == shard3.shard_id
    
    def test_range_sharding(self):
        """Test range-based sharding"""
        router = ShardRouter(strategy=ShardingStrategy.RANGE)
        
        # Add shards with ranges
        shard1 = ShardConfig(
            shard_id="range1",
            database_url="postgresql+asyncpg://test:test@localhost:5432/range1",
            min_range="a",
            max_range="m"
        )
        shard2 = ShardConfig(
            shard_id="range2", 
            database_url="postgresql+asyncpg://test:test@localhost:5432/range2",
            min_range="n",
            max_range="z"
        )
        
        router.add_shard(shard1)
        router.add_shard(shard2)
        
        # Test routing
        assert router.get_shard_for_key("apple").shard_id == "range1"
        assert router.get_shard_for_key("zebra").shard_id == "range2"
    
    def test_weighted_sharding(self):
        """Test weighted shard selection"""
        router = ShardRouter(strategy=ShardingStrategy.HASH)
        
        # Add shards with different weights
        light_shard = ShardConfig(
            shard_id="light",
            database_url="postgresql+asyncpg://test:test@localhost:5432/light",
            weight=1.0
        )
        heavy_shard = ShardConfig(
            shard_id="heavy",
            database_url="postgresql+asyncpg://test:test@localhost:5432/heavy",
            weight=3.0
        )
        
        router.add_shard(light_shard)
        router.add_shard(heavy_shard)
        
        # Route many keys and check distribution
        shard_counts = {"light": 0, "heavy": 0}
        for i in range(1000):
            shard = router.get_shard_for_key(f"key_{i}")
            shard_counts[shard.shard_id] += 1
        
        # Heavy shard should get roughly 3x more keys
        ratio = shard_counts["heavy"] / shard_counts["light"]
        assert 2.5 < ratio < 3.5


class TestShardedSession:
    """Test ShardedSession class"""
    
    @pytest.mark.asyncio
    async def test_get_session_for_write(self, shard_router):
        """Test getting session for write operations"""
        sharded_session = ShardedSession(shard_router)
        
        # Mock the session factory
        mock_session = AsyncMock()
        mock_factory = AsyncMock(return_value=mock_session)
        
        with patch.object(ShardConfig, 'get_session_factory', return_value=mock_factory):
            async with sharded_session.get_session("test_key", read_only=False) as session:
                assert session == mock_session
    
    @pytest.mark.asyncio
    async def test_get_session_for_read(self, shard_router):
        """Test getting session for read operations"""
        sharded_session = ShardedSession(shard_router)
        
        # Add a read replica
        read_shard = ShardConfig(
            shard_id="read_replica",
            database_url="postgresql+asyncpg://test:test@localhost:5432/read",
            read_only=True
        )
        shard_router.add_shard(read_shard)
        
        mock_session = AsyncMock()
        mock_factory = AsyncMock(return_value=mock_session)
        
        with patch.object(ShardConfig, 'get_session_factory', return_value=mock_factory):
            async with sharded_session.get_session("test_key", read_only=True) as session:
                assert session == mock_session


class TestShardedRepository:
    """Test ShardedRepository base class"""
    
    @pytest.mark.asyncio
    async def test_create_on_shard(self, shard_router):
        """Test creating entity on specific shard"""
        sharded_session = ShardedSession(shard_router)
        repo = ShardedRepository(sharded_session)
        
        # Mock the session and model
        mock_session = AsyncMock()
        mock_instance = Mock(id=uuid4())
        
        with patch.object(sharded_session, 'get_session') as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session
            
            # Create test entity
            class TestModel:
                def __init__(self, **kwargs):
                    for k, v in kwargs.items():
                        setattr(self, k, v)
            
            result = await repo.create_on_shard(
                TestModel,
                "test_shard_key",
                name="test",
                value=123
            )
            
            mock_session.add.assert_called_once()
            mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_query_all_shards(self, shard_router):
        """Test querying across all shards"""
        sharded_session = ShardedSession(shard_router)
        repo = ShardedRepository(sharded_session)
        
        # Mock query results from different shards
        shard_results = [
            [{"id": 1, "name": "asset1"}],
            [{"id": 2, "name": "asset2"}],
            [{"id": 3, "name": "asset3"}]
        ]
        
        async def mock_query(session):
            # Return different results for each shard
            return shard_results.pop(0)
        
        with patch.object(sharded_session, 'get_all_shards_sessions') as mock_get_sessions:
            mock_sessions = {
                f"shard{i+1}": AsyncMock() for i in range(3)
            }
            mock_get_sessions.return_value.__aenter__.return_value = mock_sessions
            
            with patch('asyncio.gather', return_value=shard_results):
                results = await repo.query_all_shards(mock_query)
                
                assert len(results) == 3


class TestAssetShardedRepository:
    """Test AssetShardedRepository class"""
    
    @pytest.mark.asyncio
    async def test_create_asset_with_project_sharding(self, shard_router):
        """Test creating asset with project-based sharding"""
        sharded_session = ShardedSession(shard_router)
        repo = AssetShardedRepository(sharded_session)
        
        # Test asset data
        project_id = uuid4()
        asset_data = {
            "id": uuid4(),
            "name": "test_video.mp4",
            "project_id": project_id,
            "owner_id": uuid4(),
            "file_size": 1000000
        }
        
        with patch.object(repo, 'create_on_shard') as mock_create:
            mock_create.return_value = Asset(**asset_data)
            
            result = await repo.create_asset(asset_data)
            
            # Should use project_id as shard key
            mock_create.assert_called_once()
            call_args = mock_create.call_args
            assert call_args[0][1] == project_id  # shard_key_value
    
    @pytest.mark.asyncio
    async def test_get_asset_with_hint(self, shard_router):
        """Test getting asset with project hint"""
        sharded_session = ShardedSession(shard_router)
        repo = AssetShardedRepository(sharded_session)
        
        asset_id = uuid4()
        project_id = uuid4()
        
        mock_asset = Mock(id=asset_id, project_id=project_id)
        
        with patch.object(repo, 'get_by_id_from_shard') as mock_get:
            mock_get.return_value = mock_asset
            
            result = await repo.get_asset(asset_id, project_id)
            
            assert result == mock_asset
            mock_get.assert_called_once_with(Asset, asset_id, project_id)
    
    @pytest.mark.asyncio
    async def test_get_assets_by_project(self, shard_router):
        """Test getting assets for specific project"""
        sharded_session = ShardedSession(shard_router)
        repo = AssetShardedRepository(sharded_session)
        
        project_id = uuid4()
        mock_assets = [
            Mock(id=uuid4(), project_id=project_id),
            Mock(id=uuid4(), project_id=project_id)
        ]
        
        with patch.object(repo, 'query_shard') as mock_query:
            mock_query.return_value = mock_assets
            
            results = await repo.get_assets_by_project(project_id, limit=10, offset=0)
            
            assert len(results) == 2
            assert results == mock_assets
            
            # Should query only the project's shard
            mock_query.assert_called_once()
            assert mock_query.call_args[0][1] == project_id


class TestShardingConfiguration:
    """Test sharding configuration"""
    
    def test_configuration_validation(self, sharding_configuration):
        """Test configuration validation"""
        assert sharding_configuration.enabled is True
        assert sharding_configuration.strategy == "hash"
        assert sharding_configuration.shard_key == "project_id"
        assert len(sharding_configuration.shards) == 3
    
    def test_configuration_with_read_replicas(self):
        """Test configuration with read replicas"""
        config = ShardingConfiguration(
            enabled=True,
            strategy="hash",
            shard_key="asset_id",
            shards=[
                ShardDefinition(
                    shard_id="primary",
                    database_url="postgresql+asyncpg://test:test@localhost:5432/primary"
                ),
                ShardDefinition(
                    shard_id="replica",
                    database_url="postgresql+asyncpg://test:test@localhost:5432/replica",
                    read_only=True
                )
            ]
        )
        
        write_shards = [s for s in config.shards if not s.read_only]
        read_shards = [s for s in config.shards if s.read_only]
        
        assert len(write_shards) == 1
        assert len(read_shards) == 1
    
    def test_invalid_configuration(self):
        """Test invalid configuration raises error"""
        with pytest.raises(ValueError):
            # No write shards
            ShardingConfiguration(
                enabled=True,
                strategy="hash",
                shard_key="asset_id",
                shards=[
                    ShardDefinition(
                        shard_id="read_only",
                        database_url="postgresql+asyncpg://test:test@localhost:5432/ro",
                        read_only=True
                    )
                ]
            )