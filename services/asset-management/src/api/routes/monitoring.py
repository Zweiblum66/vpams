"""
Monitoring endpoints for asset management service

Provides health checks, metrics, and shard monitoring.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any
import time
import psutil
import asyncio

from ...core.config import get_settings
from ...db.sharding import get_shard_router, get_replica_router
from ...core.sharding_config import load_sharding_config

router = APIRouter(prefix="/api/v1/monitoring", tags=["monitoring"])


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "service": "asset-management",
        "version": "1.0.0",
        "timestamp": time.time()
    }


@router.get("/metrics")
async def get_metrics() -> Dict[str, Any]:
    """Get service metrics"""
    # CPU and memory usage
    cpu_percent = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()
    
    # Process-specific metrics
    process = psutil.Process()
    process_memory = process.memory_info()
    
    return {
        "system": {
            "cpu_percent": cpu_percent,
            "memory": {
                "total": memory.total,
                "available": memory.available,
                "percent": memory.percent,
                "used": memory.used
            }
        },
        "process": {
            "memory_rss": process_memory.rss,
            "memory_vms": process_memory.vms,
            "cpu_percent": process.cpu_percent(),
            "num_threads": process.num_threads(),
            "connections": len(process.connections())
        },
        "timestamp": time.time()
    }


@router.get("/shards")
async def get_shard_status() -> Dict[str, Any]:
    """Get status of all database shards"""
    config = load_sharding_config()
    
    if not config.enabled:
        return {
            "enabled": False,
            "message": "Sharding is not enabled"
        }
    
    try:
        router = await get_shard_router()
        
        shard_status = {
            "enabled": True,
            "strategy": router.strategy.value,
            "shard_key": router.shard_key.value,
            "total_shards": len(router.shards),
            "write_shards": len(router.write_shards),
            "read_shards": len(router.read_shards),
            "shards": {}
        }
        
        # Check each shard
        for shard_id, shard in router.shards.items():
            try:
                engine = await shard.get_engine()
                async with engine.connect() as conn:
                    start_time = time.time()
                    result = await conn.execute("SELECT 1")
                    await result.fetchone()
                    response_time_ms = (time.time() - start_time) * 1000
                
                shard_status["shards"][shard_id] = {
                    "status": "healthy",
                    "read_only": shard.read_only,
                    "weight": shard.weight,
                    "regions": shard.regions,
                    "response_time_ms": round(response_time_ms, 2)
                }
                
            except Exception as e:
                shard_status["shards"][shard_id] = {
                    "status": "unhealthy",
                    "read_only": shard.read_only,
                    "error": str(e)
                }
        
        return shard_status
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get shard status: {str(e)}"
        )


@router.get("/shards/replicas")
async def get_replica_status() -> Dict[str, Any]:
    """Get status of read replicas"""
    config = load_sharding_config()
    
    if not config.enabled:
        return {
            "enabled": False,
            "message": "Sharding is not enabled"
        }
    
    try:
        replica_router = await get_replica_router()
        return replica_router.get_replica_status()
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get replica status: {str(e)}"
        )


@router.get("/shards/{shard_id}/stats")
async def get_shard_statistics(shard_id: str) -> Dict[str, Any]:
    """Get detailed statistics for a specific shard"""
    config = load_sharding_config()
    
    if not config.enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sharding is not enabled"
        )
    
    try:
        router = await get_shard_router()
        
        if shard_id not in router.shards:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Shard {shard_id} not found"
            )
        
        shard = router.shards[shard_id]
        engine = await shard.get_engine()
        
        stats = {}
        
        async with engine.connect() as conn:
            # Asset statistics
            result = await conn.execute("""
                SELECT 
                    COUNT(*) as total_assets,
                    COUNT(DISTINCT project_id) as total_projects,
                    COUNT(DISTINCT owner_id) as total_owners,
                    COALESCE(SUM(file_size), 0) as total_size,
                    MIN(created_at) as oldest_asset,
                    MAX(created_at) as newest_asset
                FROM assets 
                WHERE deleted_at IS NULL
            """)
            
            row = await result.fetchone()
            stats["assets"] = {
                "total": row.total_assets,
                "projects": row.total_projects,
                "owners": row.total_owners,
                "total_size_bytes": row.total_size,
                "total_size_gb": round(row.total_size / (1024**3), 2),
                "oldest": row.oldest_asset.isoformat() if row.oldest_asset else None,
                "newest": row.newest_asset.isoformat() if row.newest_asset else None
            }
            
            # Asset type distribution
            result = await conn.execute("""
                SELECT asset_type, COUNT(*) as count
                FROM assets
                WHERE deleted_at IS NULL
                GROUP BY asset_type
            """)
            
            stats["asset_types"] = {
                row.asset_type: row.count
                async for row in result
            }
            
            # Storage tier distribution
            result = await conn.execute("""
                SELECT storage_tier, COUNT(*) as count, COALESCE(SUM(file_size), 0) as size
                FROM assets
                WHERE deleted_at IS NULL
                GROUP BY storage_tier
            """)
            
            stats["storage_tiers"] = {
                row.storage_tier: {
                    "count": row.count,
                    "size_bytes": row.size,
                    "size_gb": round(row.size / (1024**3), 2)
                }
                async for row in result
            }
            
            # Database size
            result = await conn.execute("""
                SELECT pg_database_size(current_database()) as db_size
            """)
            row = await result.fetchone()
            stats["database"] = {
                "size_bytes": row.db_size,
                "size_gb": round(row.db_size / (1024**3), 2)
            }
            
            # For read replicas, check replication lag
            if shard.read_only:
                try:
                    result = await conn.execute("""
                        SELECT 
                            EXTRACT(EPOCH FROM (NOW() - pg_last_xact_replay_timestamp()))::INT AS lag_seconds,
                            pg_last_xact_replay_timestamp() AS last_replay
                    """)
                    row = await result.fetchone()
                    stats["replication"] = {
                        "lag_seconds": row.lag_seconds,
                        "last_replay": row.last_replay.isoformat() if row.last_replay else None
                    }
                except:
                    stats["replication"] = {"error": "Unable to get replication status"}
        
        return {
            "shard_id": shard_id,
            "read_only": shard.read_only,
            "statistics": stats
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get shard statistics: {str(e)}"
        )


@router.post("/shards/rebalance/check")
async def check_rebalance_needed() -> Dict[str, Any]:
    """Check if shard rebalancing is needed"""
    config = load_sharding_config()
    
    if not config.enabled:
        return {
            "rebalance_needed": False,
            "reason": "Sharding is not enabled"
        }
    
    try:
        router = await get_shard_router()
        threshold = config.policy.rebalance_threshold
        
        # Get asset count for each write shard
        shard_counts = {}
        total_count = 0
        
        for shard_id, shard in router.shards.items():
            if shard.read_only:
                continue
                
            try:
                engine = await shard.get_engine()
                async with engine.connect() as conn:
                    result = await conn.execute(
                        "SELECT COUNT(*) as count FROM assets WHERE deleted_at IS NULL"
                    )
                    row = await result.fetchone()
                    count = row.count
                    shard_counts[shard_id] = count
                    total_count += count
            except:
                shard_counts[shard_id] = 0
        
        if not shard_counts or total_count == 0:
            return {
                "rebalance_needed": False,
                "reason": "No data to rebalance"
            }
        
        # Calculate ideal distribution
        ideal_per_shard = total_count / len(shard_counts)
        max_deviation = 0
        
        details = []
        for shard_id, count in shard_counts.items():
            deviation = abs(count - ideal_per_shard) / ideal_per_shard if ideal_per_shard > 0 else 0
            max_deviation = max(max_deviation, deviation)
            
            details.append({
                "shard_id": shard_id,
                "asset_count": count,
                "ideal_count": round(ideal_per_shard),
                "deviation_percent": round(deviation * 100, 1)
            })
        
        return {
            "rebalance_needed": max_deviation > threshold,
            "threshold_percent": threshold * 100,
            "max_deviation_percent": round(max_deviation * 100, 1),
            "total_assets": total_count,
            "ideal_per_shard": round(ideal_per_shard),
            "shard_distribution": details
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check rebalance status: {str(e)}"
        )