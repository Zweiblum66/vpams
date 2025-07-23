"""
Read Replica Support for Database Sharding

This module extends the sharding implementation with read replica support
for improved read performance and availability.
"""

from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum
import random
import time
import asyncio
from contextlib import asynccontextmanager
import structlog

from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine
from sqlalchemy import text

from .sharding import ShardConfig, ShardRouter, ShardingStrategy, ShardKey

logger = structlog.get_logger()


class ReadPreference(Enum):
    """Read preference for replica selection"""
    PRIMARY = "primary"  # Always read from primary
    PRIMARY_PREFERRED = "primary_preferred"  # Try primary first, fallback to replica
    SECONDARY = "secondary"  # Always read from replica
    SECONDARY_PREFERRED = "secondary_preferred"  # Try replica first, fallback to primary
    NEAREST = "nearest"  # Read from nearest available node


class LoadBalancingStrategy(Enum):
    """Load balancing strategy for replicas"""
    ROUND_ROBIN = "round_robin"
    RANDOM = "random"
    LEAST_CONNECTIONS = "least_connections"
    RESPONSE_TIME = "response_time"
    WEIGHTED = "weighted"


@dataclass
class ReplicaStats:
    """Statistics for a replica"""
    shard_id: str
    total_queries: int = 0
    failed_queries: int = 0
    total_response_time_ms: float = 0
    active_connections: int = 0
    last_check_time: float = 0
    is_healthy: bool = True
    lag_seconds: Optional[float] = None
    
    @property
    def average_response_time_ms(self) -> float:
        """Calculate average response time"""
        if self.total_queries == 0:
            return 0
        return self.total_response_time_ms / self.total_queries
    
    @property
    def success_rate(self) -> float:
        """Calculate query success rate"""
        if self.total_queries == 0:
            return 1.0
        return (self.total_queries - self.failed_queries) / self.total_queries


class ReadReplicaRouter:
    """Routes read queries to appropriate replicas"""
    
    def __init__(
        self,
        base_router: ShardRouter,
        read_preference: ReadPreference = ReadPreference.SECONDARY_PREFERRED,
        load_balancing: LoadBalancingStrategy = LoadBalancingStrategy.ROUND_ROBIN,
        health_check_interval: int = 30,
        max_lag_seconds: int = 300
    ):
        self.base_router = base_router
        self.read_preference = read_preference
        self.load_balancing = load_balancing
        self.health_check_interval = health_check_interval
        self.max_lag_seconds = max_lag_seconds
        
        # Track replica statistics
        self.replica_stats: Dict[str, ReplicaStats] = {}
        self._round_robin_index: Dict[str, int] = {}
        self._last_health_check = 0
        
        # Initialize stats for all shards
        for shard_id, shard in base_router.shards.items():
            self.replica_stats[shard_id] = ReplicaStats(shard_id=shard_id)
    
    async def get_read_shard(
        self,
        shard_key_value: Any,
        read_preference: Optional[ReadPreference] = None
    ) -> ShardConfig:
        """Get appropriate shard for read operation"""
        preference = read_preference or self.read_preference
        
        # Get the primary shard for this key
        primary_shard = self.base_router.get_shard_for_key(shard_key_value)
        
        # Check if we need to perform health check
        await self._check_replica_health()
        
        # Handle read preference
        if preference == ReadPreference.PRIMARY:
            return primary_shard
        
        # Get available replicas for this shard's data
        replicas = self._get_replicas_for_shard(primary_shard)
        
        if preference == ReadPreference.SECONDARY:
            if not replicas:
                raise ValueError(f"No read replicas available for shard {primary_shard.shard_id}")
            return self._select_replica(replicas, primary_shard.shard_id)
        
        if preference == ReadPreference.PRIMARY_PREFERRED:
            if self._is_shard_healthy(primary_shard.shard_id):
                return primary_shard
            if replicas:
                return self._select_replica(replicas, primary_shard.shard_id)
            return primary_shard  # Fallback even if unhealthy
        
        if preference == ReadPreference.SECONDARY_PREFERRED:
            if replicas:
                selected = self._select_replica(replicas, primary_shard.shard_id)
                if self._is_shard_healthy(selected.shard_id):
                    return selected
            return primary_shard
        
        if preference == ReadPreference.NEAREST:
            all_shards = [primary_shard] + replicas
            return self._select_nearest(all_shards)
        
        return primary_shard
    
    def _get_replicas_for_shard(self, primary_shard: ShardConfig) -> List[ShardConfig]:
        """Get read replicas that can serve data for a primary shard"""
        replicas = []
        
        # Find replicas by naming convention (e.g., shard1 -> shard1_read)
        for shard_id, shard in self.base_router.shards.items():
            if shard.read_only and (
                shard_id.startswith(f"{primary_shard.shard_id}_") or
                shard_id.endswith("_read") and shard_id.startswith(primary_shard.shard_id.split("_")[0])
            ):
                replicas.append(shard)
        
        # Also check by regions
        if primary_shard.regions:
            for shard in self.base_router.read_shards:
                if shard.read_only and shard.regions:
                    if any(region in primary_shard.regions for region in shard.regions):
                        if shard not in replicas:
                            replicas.append(shard)
        
        return replicas
    
    def _select_replica(self, replicas: List[ShardConfig], primary_shard_id: str) -> ShardConfig:
        """Select a replica based on load balancing strategy"""
        if not replicas:
            raise ValueError("No replicas available")
        
        # Filter healthy replicas
        healthy_replicas = [
            r for r in replicas 
            if self._is_shard_healthy(r.shard_id) and self._is_lag_acceptable(r.shard_id)
        ]
        
        if not healthy_replicas:
            # Fallback to any replica if none are healthy
            healthy_replicas = replicas
        
        if self.load_balancing == LoadBalancingStrategy.RANDOM:
            return random.choice(healthy_replicas)
        
        elif self.load_balancing == LoadBalancingStrategy.ROUND_ROBIN:
            if primary_shard_id not in self._round_robin_index:
                self._round_robin_index[primary_shard_id] = 0
            
            index = self._round_robin_index[primary_shard_id] % len(healthy_replicas)
            self._round_robin_index[primary_shard_id] += 1
            return healthy_replicas[index]
        
        elif self.load_balancing == LoadBalancingStrategy.LEAST_CONNECTIONS:
            return min(
                healthy_replicas,
                key=lambda r: self.replica_stats[r.shard_id].active_connections
            )
        
        elif self.load_balancing == LoadBalancingStrategy.RESPONSE_TIME:
            return min(
                healthy_replicas,
                key=lambda r: self.replica_stats[r.shard_id].average_response_time_ms
            )
        
        elif self.load_balancing == LoadBalancingStrategy.WEIGHTED:
            # Use shard weights for selection
            total_weight = sum(r.weight for r in healthy_replicas)
            if total_weight == 0:
                return random.choice(healthy_replicas)
            
            rand = random.uniform(0, total_weight)
            cumulative = 0
            
            for replica in healthy_replicas:
                cumulative += replica.weight
                if rand <= cumulative:
                    return replica
            
            return healthy_replicas[-1]
        
        # Default to random
        return random.choice(healthy_replicas)
    
    def _select_nearest(self, shards: List[ShardConfig]) -> ShardConfig:
        """Select nearest shard based on response time"""
        healthy_shards = [
            s for s in shards 
            if self._is_shard_healthy(s.shard_id)
        ]
        
        if not healthy_shards:
            healthy_shards = shards
        
        return min(
            healthy_shards,
            key=lambda s: self.replica_stats[s.shard_id].average_response_time_ms
        )
    
    def _is_shard_healthy(self, shard_id: str) -> bool:
        """Check if a shard is healthy"""
        stats = self.replica_stats.get(shard_id)
        if not stats:
            return True
        
        return stats.is_healthy and stats.success_rate > 0.5
    
    def _is_lag_acceptable(self, shard_id: str) -> bool:
        """Check if replica lag is within acceptable limits"""
        stats = self.replica_stats.get(shard_id)
        if not stats or stats.lag_seconds is None:
            return True
        
        return stats.lag_seconds <= self.max_lag_seconds
    
    async def _check_replica_health(self):
        """Periodically check replica health"""
        current_time = time.time()
        
        if current_time - self._last_health_check < self.health_check_interval:
            return
        
        self._last_health_check = current_time
        
        # Check each shard's health
        tasks = []
        for shard_id, shard in self.base_router.shards.items():
            tasks.append(self._check_shard_health(shard))
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _check_shard_health(self, shard: ShardConfig):
        """Check health of a specific shard"""
        stats = self.replica_stats[shard.shard_id]
        start_time = time.time()
        
        try:
            engine = await shard.get_engine()
            async with engine.connect() as conn:
                # Basic connectivity check
                result = await conn.execute(text("SELECT 1"))
                await result.fetchone()
                
                # Check replication lag for read replicas
                if shard.read_only:
                    lag_result = await conn.execute(
                        text("""
                            SELECT EXTRACT(EPOCH FROM (NOW() - pg_last_xact_replay_timestamp()))::INT 
                            AS lag_seconds
                        """)
                    )
                    lag_row = await lag_result.fetchone()
                    if lag_row and lag_row.lag_seconds is not None:
                        stats.lag_seconds = lag_row.lag_seconds
                
                stats.is_healthy = True
                response_time_ms = (time.time() - start_time) * 1000
                
                # Update stats
                stats.total_response_time_ms += response_time_ms
                stats.total_queries += 1
                
        except Exception as e:
            logger.warning(
                "shard_health_check_failed",
                shard_id=shard.shard_id,
                error=str(e)
            )
            stats.is_healthy = False
            stats.failed_queries += 1
        
        stats.last_check_time = time.time()
    
    async def record_query_metrics(
        self,
        shard_id: str,
        response_time_ms: float,
        success: bool
    ):
        """Record metrics for a completed query"""
        stats = self.replica_stats.get(shard_id)
        if not stats:
            return
        
        stats.total_queries += 1
        stats.total_response_time_ms += response_time_ms
        
        if not success:
            stats.failed_queries += 1
    
    @asynccontextmanager
    async def track_query(self, shard_id: str):
        """Context manager to track query metrics"""
        stats = self.replica_stats.get(shard_id)
        if stats:
            stats.active_connections += 1
        
        start_time = time.time()
        success = True
        
        try:
            yield
        except Exception:
            success = False
            raise
        finally:
            response_time_ms = (time.time() - start_time) * 1000
            
            if stats:
                stats.active_connections -= 1
            
            await self.record_query_metrics(shard_id, response_time_ms, success)
    
    def get_replica_status(self) -> Dict[str, Any]:
        """Get current status of all replicas"""
        status = {
            "read_preference": self.read_preference.value,
            "load_balancing": self.load_balancing.value,
            "replicas": {}
        }
        
        for shard_id, stats in self.replica_stats.items():
            shard = self.base_router.shards.get(shard_id)
            if not shard:
                continue
            
            status["replicas"][shard_id] = {
                "is_primary": not shard.read_only,
                "is_healthy": stats.is_healthy,
                "total_queries": stats.total_queries,
                "failed_queries": stats.failed_queries,
                "success_rate": f"{stats.success_rate * 100:.1f}%",
                "avg_response_time_ms": f"{stats.average_response_time_ms:.2f}",
                "active_connections": stats.active_connections,
                "lag_seconds": stats.lag_seconds,
                "last_check": time.strftime(
                    "%Y-%m-%d %H:%M:%S",
                    time.localtime(stats.last_check_time)
                ) if stats.last_check_time else "Never"
            }
        
        return status


class ReadReplicaSession:
    """Session manager with read replica support"""
    
    def __init__(
        self,
        router: ShardRouter,
        replica_router: ReadReplicaRouter
    ):
        self.router = router
        self.replica_router = replica_router
    
    @asynccontextmanager
    async def get_session(
        self,
        shard_key_value: Any,
        read_only: bool = False,
        read_preference: Optional[ReadPreference] = None
    ):
        """Get a database session with read replica support"""
        if read_only:
            # Use replica router for read operations
            shard = await self.replica_router.get_read_shard(
                shard_key_value,
                read_preference
            )
        else:
            # Use primary shard for write operations
            shard = self.router.get_shard_for_key(shard_key_value)
        
        # Track query metrics
        async with self.replica_router.track_query(shard.shard_id):
            session_factory = await shard.get_session_factory()
            async with session_factory() as session:
                yield session