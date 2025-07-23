"""
Database Sharding Implementation for Asset Management Service

This module provides horizontal database sharding capabilities for the MAMS platform,
enabling distribution of data across multiple database instances for improved
performance and scalability.
"""

from typing import Dict, List, Optional, Any, Callable, Union
from sqlalchemy import create_engine, MetaData, Table, select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, AsyncEngine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
import hashlib
import struct
from datetime import datetime
from enum import Enum
import asyncio
from contextlib import asynccontextmanager

from ..core.config import get_settings
from .models import Asset, AssetVersion, ProjectContainer, ShotItem


class ShardingStrategy(Enum):
    """Available sharding strategies"""
    HASH = "hash"
    RANGE = "range"
    GEOGRAPHY = "geography"
    CUSTOM = "custom"


class ShardKey(Enum):
    """Available shard keys"""
    ASSET_ID = "asset_id"
    PROJECT_ID = "project_id"
    OWNER_ID = "owner_id"
    CREATED_AT = "created_at"


class ShardConfig:
    """Configuration for a single shard"""
    
    def __init__(
        self,
        shard_id: str,
        database_url: str,
        weight: float = 1.0,
        read_only: bool = False,
        min_range: Optional[Any] = None,
        max_range: Optional[Any] = None,
        regions: Optional[List[str]] = None
    ):
        self.shard_id = shard_id
        self.database_url = database_url
        self.weight = weight
        self.read_only = read_only
        self.min_range = min_range
        self.max_range = max_range
        self.regions = regions or []
        self._engine: Optional[AsyncEngine] = None
        self._session_factory: Optional[sessionmaker] = None
    
    async def get_engine(self) -> AsyncEngine:
        """Get or create async engine for this shard"""
        if not self._engine:
            self._engine = create_async_engine(
                self.database_url,
                pool_pre_ping=True,
                pool_size=10,
                max_overflow=20,
                poolclass=NullPool if self.read_only else None
            )
        return self._engine
    
    async def get_session_factory(self) -> sessionmaker:
        """Get or create session factory for this shard"""
        if not self._session_factory:
            engine = await self.get_engine()
            self._session_factory = sessionmaker(
                engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
        return self._session_factory
    
    async def close(self):
        """Close database connections"""
        if self._engine:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None


class ShardRouter:
    """Routes database operations to appropriate shards"""
    
    def __init__(
        self,
        strategy: ShardingStrategy = ShardingStrategy.HASH,
        shard_key: ShardKey = ShardKey.ASSET_ID
    ):
        self.strategy = strategy
        self.shard_key = shard_key
        self.shards: Dict[str, ShardConfig] = {}
        self.write_shards: List[ShardConfig] = []
        self.read_shards: List[ShardConfig] = []
    
    def add_shard(self, config: ShardConfig):
        """Add a shard configuration"""
        self.shards[config.shard_id] = config
        
        if not config.read_only:
            self.write_shards.append(config)
        self.read_shards.append(config)
    
    def get_shard_for_key(self, key_value: Any) -> ShardConfig:
        """Determine which shard should handle a given key"""
        if self.strategy == ShardingStrategy.HASH:
            return self._hash_shard(key_value)
        elif self.strategy == ShardingStrategy.RANGE:
            return self._range_shard(key_value)
        elif self.strategy == ShardingStrategy.GEOGRAPHY:
            return self._geography_shard(key_value)
        else:
            raise ValueError(f"Unsupported sharding strategy: {self.strategy}")
    
    def _hash_shard(self, key_value: Any) -> ShardConfig:
        """Hash-based sharding"""
        if not self.write_shards:
            raise ValueError("No write shards available")
        
        # Convert key to bytes for hashing
        if isinstance(key_value, str):
            key_bytes = key_value.encode('utf-8')
        elif isinstance(key_value, int):
            key_bytes = struct.pack('q', key_value)
        elif isinstance(key_value, bytes):
            key_bytes = key_value
        else:
            key_bytes = str(key_value).encode('utf-8')
        
        # Calculate hash
        hash_value = int(hashlib.md5(key_bytes).hexdigest(), 16)
        
        # Weighted shard selection
        total_weight = sum(shard.weight for shard in self.write_shards)
        normalized_hash = (hash_value % 1000000) / 1000000.0
        
        cumulative_weight = 0.0
        for shard in self.write_shards:
            cumulative_weight += shard.weight / total_weight
            if normalized_hash <= cumulative_weight:
                return shard
        
        return self.write_shards[-1]
    
    def _range_shard(self, key_value: Any) -> ShardConfig:
        """Range-based sharding"""
        for shard in self.write_shards:
            if shard.min_range is not None and shard.max_range is not None:
                if shard.min_range <= key_value <= shard.max_range:
                    return shard
        
        # Default to first shard if no range matches
        if self.write_shards:
            return self.write_shards[0]
        raise ValueError("No suitable shard found for range")
    
    def _geography_shard(self, key_value: Any) -> ShardConfig:
        """Geography-based sharding (requires region info)"""
        # This would need additional context about user location
        # For now, return first available shard
        if self.write_shards:
            return self.write_shards[0]
        raise ValueError("No write shards available")
    
    def get_read_shard(self, key_value: Optional[Any] = None) -> ShardConfig:
        """Get a shard for read operations (can use read replicas)"""
        if key_value:
            # Try to use the same shard as write for consistency
            return self.get_shard_for_key(key_value)
        
        # Round-robin selection for load balancing
        if self.read_shards:
            import random
            return random.choice(self.read_shards)
        
        raise ValueError("No read shards available")


class ShardedSession:
    """Manages database sessions across shards"""
    
    def __init__(self, router: ShardRouter):
        self.router = router
        self._sessions: Dict[str, AsyncSession] = {}
    
    @asynccontextmanager
    async def get_session(self, shard_key_value: Any, read_only: bool = False):
        """Get a database session for the appropriate shard"""
        if read_only:
            shard = self.router.get_read_shard(shard_key_value)
        else:
            shard = self.router.get_shard_for_key(shard_key_value)
        
        session_factory = await shard.get_session_factory()
        async with session_factory() as session:
            yield session
    
    @asynccontextmanager
    async def get_all_shards_sessions(self):
        """Get sessions for all shards (for cross-shard queries)"""
        sessions = {}
        try:
            for shard_id, shard in self.router.shards.items():
                session_factory = await shard.get_session_factory()
                sessions[shard_id] = session_factory()
            
            yield sessions
        finally:
            for session in sessions.values():
                await session.close()


class ShardedRepository:
    """Base repository with sharding support"""
    
    def __init__(self, sharded_session: ShardedSession):
        self.sharded_session = sharded_session
    
    async def create_on_shard(
        self,
        model_class: type,
        shard_key_value: Any,
        **kwargs
    ) -> Any:
        """Create an entity on the appropriate shard"""
        async with self.sharded_session.get_session(shard_key_value) as session:
            instance = model_class(**kwargs)
            session.add(instance)
            await session.commit()
            await session.refresh(instance)
            return instance
    
    async def get_by_id_from_shard(
        self,
        model_class: type,
        entity_id: Any,
        shard_key_value: Any
    ) -> Optional[Any]:
        """Get an entity by ID from a specific shard"""
        async with self.sharded_session.get_session(shard_key_value, read_only=True) as session:
            result = await session.get(model_class, entity_id)
            return result
    
    async def query_shard(
        self,
        query_func: Callable,
        shard_key_value: Any,
        read_only: bool = True
    ) -> List[Any]:
        """Execute a query on a specific shard"""
        async with self.sharded_session.get_session(shard_key_value, read_only=read_only) as session:
            result = await query_func(session)
            return result
    
    async def query_all_shards(
        self,
        query_func: Callable,
        aggregate_func: Optional[Callable] = None
    ) -> Union[List[Any], Any]:
        """Execute a query across all shards"""
        results = []
        
        async with self.sharded_session.get_all_shards_sessions() as sessions:
            tasks = []
            for shard_id, session in sessions.items():
                task = query_func(session)
                tasks.append(task)
            
            shard_results = await asyncio.gather(*tasks)
            
            for result in shard_results:
                if isinstance(result, list):
                    results.extend(result)
                else:
                    results.append(result)
        
        if aggregate_func:
            return aggregate_func(results)
        return results


class AssetShardedRepository(ShardedRepository):
    """Asset-specific repository with sharding support"""
    
    async def create_asset(self, asset_data: dict) -> Asset:
        """Create an asset on the appropriate shard"""
        # Determine shard key value based on configuration
        if self.sharded_session.router.shard_key == ShardKey.PROJECT_ID:
            shard_key_value = asset_data.get('project_id')
        elif self.sharded_session.router.shard_key == ShardKey.OWNER_ID:
            shard_key_value = asset_data.get('owner_id')
        else:
            shard_key_value = asset_data.get('id')
        
        return await self.create_on_shard(Asset, shard_key_value, **asset_data)
    
    async def get_asset(self, asset_id: str, project_id: Optional[str] = None) -> Optional[Asset]:
        """Get an asset by ID"""
        # Use project_id as hint if available
        shard_key_value = project_id if project_id else asset_id
        
        # Try the most likely shard first
        result = await self.get_by_id_from_shard(Asset, asset_id, shard_key_value)
        if result:
            return result
        
        # If not found, search all shards
        async def search_query(session):
            result = await session.get(Asset, asset_id)
            return result
        
        results = await self.query_all_shards(search_query)
        return next((r for r in results if r), None)
    
    async def get_assets_by_project(self, project_id: str, limit: int = 100, offset: int = 0) -> List[Asset]:
        """Get assets for a specific project"""
        async def query(session):
            stmt = select(Asset).where(
                Asset.project_id == project_id
            ).limit(limit).offset(offset)
            result = await session.execute(stmt)
            return result.scalars().all()
        
        # If sharding by project_id, query only the relevant shard
        if self.sharded_session.router.shard_key == ShardKey.PROJECT_ID:
            return await self.query_shard(query, project_id)
        else:
            # Otherwise, query all shards
            return await self.query_all_shards(query)
    
    async def search_assets(self, search_params: dict) -> List[Asset]:
        """Search assets across all shards"""
        async def search_query(session):
            stmt = select(Asset)
            
            # Apply filters
            if 'name' in search_params:
                stmt = stmt.where(Asset.name.ilike(f"%{search_params['name']}%"))
            if 'asset_type' in search_params:
                stmt = stmt.where(Asset.asset_type == search_params['asset_type'])
            if 'status' in search_params:
                stmt = stmt.where(Asset.status == search_params['status'])
            if 'owner_id' in search_params:
                stmt = stmt.where(Asset.owner_id == search_params['owner_id'])
            
            result = await session.execute(stmt)
            return result.scalars().all()
        
        return await self.query_all_shards(search_query)


class ShardManager:
    """Manages shard configuration and migrations"""
    
    def __init__(self, router: ShardRouter):
        self.router = router
    
    async def init_shards(self, shard_configs: List[Dict[str, Any]]):
        """Initialize shards from configuration"""
        for config_dict in shard_configs:
            config = ShardConfig(**config_dict)
            self.router.add_shard(config)
    
    async def rebalance_shards(self, dry_run: bool = True) -> Dict[str, Any]:
        """Rebalance data across shards"""
        stats = {
            'total_assets': 0,
            'shard_distribution': {},
            'proposed_moves': []
        }
        
        # Analyze current distribution
        async def count_assets(session):
            result = await session.execute(select(func.count(Asset.id)))
            return result.scalar()
        
        async with self.router.sharded_session.get_all_shards_sessions() as sessions:
            for shard_id, session in sessions.items():
                count = await count_assets(session)
                stats['shard_distribution'][shard_id] = count
                stats['total_assets'] += count
        
        # Calculate ideal distribution
        if not dry_run:
            # Actual rebalancing logic would go here
            pass
        
        return stats
    
    async def add_shard(self, shard_config: ShardConfig, rebalance: bool = False):
        """Add a new shard to the cluster"""
        self.router.add_shard(shard_config)
        
        if rebalance:
            await self.rebalance_shards(dry_run=False)
    
    async def remove_shard(self, shard_id: str, target_shard_id: str):
        """Remove a shard and migrate its data"""
        if shard_id not in self.router.shards:
            raise ValueError(f"Shard {shard_id} not found")
        
        if target_shard_id not in self.router.shards:
            raise ValueError(f"Target shard {target_shard_id} not found")
        
        # Migration logic would go here
        # This is a complex operation that should be done carefully
        pass


# Default shard configuration loader
async def load_shard_configuration() -> List[Dict[str, Any]]:
    """Load shard configuration from settings or environment"""
    settings = get_settings()
    
    # Example configuration - in production this would come from config
    return [
        {
            "shard_id": "shard1",
            "database_url": settings.database_url.replace("mams_assets", "mams_assets_shard1"),
            "weight": 1.0,
            "regions": ["us-east", "us-west"]
        },
        {
            "shard_id": "shard2", 
            "database_url": settings.database_url.replace("mams_assets", "mams_assets_shard2"),
            "weight": 1.0,
            "regions": ["eu-west", "eu-central"]
        },
        {
            "shard_id": "shard3",
            "database_url": settings.database_url.replace("mams_assets", "mams_assets_shard3"),
            "weight": 1.0,
            "regions": ["asia-pacific"]
        }
    ]


# Global instances
_shard_router: Optional[ShardRouter] = None
_replica_router: Optional['ReadReplicaRouter'] = None


async def get_shard_router() -> ShardRouter:
    """Get or create the global shard router"""
    global _shard_router
    
    if not _shard_router:
        _shard_router = ShardRouter(
            strategy=ShardingStrategy.HASH,
            shard_key=ShardKey.PROJECT_ID
        )
        
        # Load configuration
        shard_configs = await load_shard_configuration()
        manager = ShardManager(_shard_router)
        await manager.init_shards(shard_configs)
    
    return _shard_router


async def get_replica_router() -> 'ReadReplicaRouter':
    """Get or create the global replica router"""
    global _replica_router
    
    if not _replica_router:
        from .read_replicas import ReadReplicaRouter, ReadPreference, LoadBalancingStrategy
        from ..core.sharding_config import load_sharding_config
        
        shard_router = await get_shard_router()
        config = load_sharding_config()
        
        # Map string values to enums
        read_pref = ReadPreference(config.policy.read_preference)
        load_balance = LoadBalancingStrategy(config.policy.load_balancing_strategy)
        
        _replica_router = ReadReplicaRouter(
            base_router=shard_router,
            read_preference=read_pref,
            load_balancing=load_balance,
            health_check_interval=config.policy.health_check_interval_seconds,
            max_lag_seconds=config.policy.max_replica_lag_seconds
        )
    
    return _replica_router


async def get_sharded_session() -> ShardedSession:
    """Get a sharded session instance"""
    router = await get_shard_router()
    return ShardedSession(router)


async def get_replica_aware_session() -> 'ReadReplicaSession':
    """Get a sharded session with read replica support"""
    from .read_replicas import ReadReplicaSession
    
    shard_router = await get_shard_router()
    replica_router = await get_replica_router()
    
    return ReadReplicaSession(shard_router, replica_router)