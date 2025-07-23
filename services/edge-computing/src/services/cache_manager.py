"""
Cache Manager Service

Manages local edge cache for frequently accessed content.
"""

import os
import shutil
import asyncio
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from pathlib import Path
import hashlib
import structlog
from aioredis import Redis
import aiofiles
from collections import OrderedDict
import json

from ..core.config import settings
from ..models.schemas import CacheEntry, CacheStatus, CacheStats
from ..utils.metrics import edge_metrics


logger = structlog.get_logger()


class CacheManager:
    """Manages edge node local cache"""
    
    def __init__(self, redis: Redis):
        self.redis = redis
        self.node_id = settings.NODE_ID
        self.cache_enabled = settings.ENABLE_LOCAL_CACHE
        self.cache_size_limit_bytes = settings.CACHE_SIZE_GB * 1024 * 1024 * 1024
        self.eviction_policy = settings.CACHE_EVICTION_POLICY
        
        # Cache directory
        self.cache_dir = Path(settings.CACHE_PATH) / self.node_id
        
        # In-memory cache index
        self.cache_index: OrderedDict[str, CacheEntry] = OrderedDict()
        self.cache_size_bytes = 0
        
        # Lock for cache operations
        self.cache_lock = asyncio.Lock()
        
        # Background tasks
        self._cleanup_task: Optional[asyncio.Task] = None
        self._sync_task: Optional[asyncio.Task] = None
    
    async def initialize(self):
        """Initialize cache manager"""
        if not self.cache_enabled:
            logger.info("Cache disabled for this node")
            return
        
        logger.info(
            "Initializing cache manager",
            node_id=self.node_id,
            cache_size_gb=settings.CACHE_SIZE_GB,
            eviction_policy=self.eviction_policy
        )
        
        # Create cache directory
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Load existing cache index
        await self._load_cache_index()
        
        # Start background tasks
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        self._sync_task = asyncio.create_task(self._sync_loop())
    
    async def shutdown(self):
        """Shutdown cache manager"""
        logger.info("Shutting down cache manager")
        
        # Cancel background tasks
        for task in [self._cleanup_task, self._sync_task]:
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        # Save cache index
        await self._save_cache_index()
    
    async def get(self, cache_key: str) -> Optional[Path]:
        """Get file from cache"""
        if not self.cache_enabled:
            return None
        
        async with self.cache_lock:
            entry = self.cache_index.get(cache_key)
            
            if not entry:
                edge_metrics.cache_misses.labels(node_id=self.node_id).inc()
                return None
            
            # Check if file exists
            file_path = Path(entry.file_path)
            if not file_path.exists():
                # Remove from index
                del self.cache_index[cache_key]
                self.cache_size_bytes -= entry.size_bytes
                edge_metrics.cache_misses.labels(node_id=self.node_id).inc()
                return None
            
            # Update access time and count
            entry.last_accessed = datetime.utcnow()
            entry.access_count += 1
            
            # Move to end for LRU
            if self.eviction_policy == "lru":
                self.cache_index.move_to_end(cache_key)
            
            edge_metrics.cache_hits.labels(node_id=self.node_id).inc()
            return file_path
    
    async def put(
        self,
        cache_key: str,
        source_path: Path,
        asset_id: str,
        content_type: str,
        ttl_seconds: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Put file into cache"""
        if not self.cache_enabled:
            return False
        
        try:
            # Get file size
            file_size = source_path.stat().st_size
            
            # Check if we need to evict items
            async with self.cache_lock:
                await self._ensure_space(file_size)
                
                # Generate cache file path
                cache_file = self.cache_dir / f"{cache_key}_{source_path.name}"
                
                # Copy file to cache
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    shutil.copy2,
                    str(source_path),
                    str(cache_file)
                )
                
                # Create cache entry
                entry = CacheEntry(
                    cache_key=cache_key,
                    asset_id=asset_id,
                    node_id=self.node_id,
                    file_path=str(cache_file),
                    size_bytes=file_size,
                    content_type=content_type,
                    ttl_seconds=ttl_seconds,
                    metadata=metadata or {}
                )
                
                # Add to index
                self.cache_index[cache_key] = entry
                self.cache_size_bytes += file_size
                
                # Store in Redis for cluster-wide visibility
                await self._store_cache_entry_redis(entry)
                
                edge_metrics.cache_puts.labels(node_id=self.node_id).inc()
                edge_metrics.cache_size_bytes.labels(node_id=self.node_id).set(self.cache_size_bytes)
                
                logger.info(
                    "Added to cache",
                    cache_key=cache_key,
                    size_mb=file_size / (1024 * 1024),
                    cache_utilization=self.cache_size_bytes / self.cache_size_limit_bytes
                )
                
                return True
                
        except Exception as e:
            logger.error("Failed to cache file", error=str(e), cache_key=cache_key)
            return False
    
    async def delete(self, cache_key: str) -> bool:
        """Delete file from cache"""
        if not self.cache_enabled:
            return False
        
        async with self.cache_lock:
            entry = self.cache_index.get(cache_key)
            
            if not entry:
                return False
            
            # Delete file
            file_path = Path(entry.file_path)
            if file_path.exists():
                file_path.unlink()
            
            # Remove from index
            del self.cache_index[cache_key]
            self.cache_size_bytes -= entry.size_bytes
            
            # Remove from Redis
            await self._remove_cache_entry_redis(cache_key)
            
            edge_metrics.cache_evictions.labels(
                node_id=self.node_id,
                reason="manual"
            ).inc()
            edge_metrics.cache_size_bytes.labels(node_id=self.node_id).set(self.cache_size_bytes)
            
            return True
    
    async def clear(self):
        """Clear entire cache"""
        if not self.cache_enabled:
            return
        
        async with self.cache_lock:
            # Delete all files
            for entry in self.cache_index.values():
                file_path = Path(entry.file_path)
                if file_path.exists():
                    file_path.unlink()
            
            # Clear index
            self.cache_index.clear()
            self.cache_size_bytes = 0
            
            # Clear Redis entries
            pattern = f"edge:cache:{self.node_id}:*"
            async for key in self.redis.scan_iter(match=pattern):
                await self.redis.delete(key)
            
            edge_metrics.cache_size_bytes.labels(node_id=self.node_id).set(0)
            
            logger.info("Cache cleared")
    
    async def get_stats(self) -> CacheStats:
        """Get cache statistics"""
        if not self.cache_enabled:
            return CacheStats(
                node_id=self.node_id,
                total_size_gb=0,
                used_size_gb=0,
                available_size_gb=0,
                cache_hit_rate=0,
                total_entries=0,
                active_entries=0,
                evicted_entries=0,
                avg_entry_size_mb=0
            )
        
        # Calculate statistics
        total_entries = len(self.cache_index)
        active_entries = sum(1 for e in self.cache_index.values() if e.status == CacheStatus.CACHED)
        evicted_entries = sum(1 for e in self.cache_index.values() if e.status == CacheStatus.EVICTED)
        
        avg_entry_size = (
            sum(e.size_bytes for e in self.cache_index.values()) / total_entries / (1024 * 1024)
            if total_entries > 0 else 0
        )
        
        # Get hit rate from Redis
        hits = await self.redis.get(f"edge:cache:hits:{self.node_id}") or 0
        misses = await self.redis.get(f"edge:cache:misses:{self.node_id}") or 0
        total_requests = int(hits) + int(misses)
        hit_rate = int(hits) / total_requests if total_requests > 0 else 0
        
        # Get most accessed items
        most_accessed = sorted(
            self.cache_index.values(),
            key=lambda e: e.access_count,
            reverse=True
        )[:10]
        
        return CacheStats(
            node_id=self.node_id,
            total_size_gb=self.cache_size_limit_bytes / (1024**3),
            used_size_gb=self.cache_size_bytes / (1024**3),
            available_size_gb=(self.cache_size_limit_bytes - self.cache_size_bytes) / (1024**3),
            cache_hit_rate=hit_rate,
            total_entries=total_entries,
            active_entries=active_entries,
            evicted_entries=evicted_entries,
            avg_entry_size_mb=avg_entry_size,
            most_accessed=[e.cache_key for e in most_accessed]
        )
    
    async def _ensure_space(self, required_bytes: int):
        """Ensure there's enough space for new cache entry"""
        if self.cache_size_bytes + required_bytes <= self.cache_size_limit_bytes:
            return
        
        # Need to evict items
        space_needed = (self.cache_size_bytes + required_bytes) - self.cache_size_limit_bytes
        evicted_bytes = 0
        
        if self.eviction_policy == "lru":
            # Evict least recently used
            for cache_key in list(self.cache_index.keys()):
                if evicted_bytes >= space_needed:
                    break
                
                entry = self.cache_index[cache_key]
                await self._evict_entry(cache_key, "lru")
                evicted_bytes += entry.size_bytes
        
        elif self.eviction_policy == "lfu":
            # Evict least frequently used
            sorted_entries = sorted(
                self.cache_index.items(),
                key=lambda x: x[1].access_count
            )
            
            for cache_key, entry in sorted_entries:
                if evicted_bytes >= space_needed:
                    break
                
                await self._evict_entry(cache_key, "lfu")
                evicted_bytes += entry.size_bytes
        
        elif self.eviction_policy == "fifo":
            # Evict first in first out
            for cache_key in list(self.cache_index.keys()):
                if evicted_bytes >= space_needed:
                    break
                
                entry = self.cache_index[cache_key]
                await self._evict_entry(cache_key, "fifo")
                evicted_bytes += entry.size_bytes
        
        elif self.eviction_policy == "ttl":
            # Evict expired items first, then oldest
            now = datetime.utcnow()
            
            # First pass: expired items
            for cache_key, entry in list(self.cache_index.items()):
                if evicted_bytes >= space_needed:
                    break
                
                if entry.ttl_seconds and (now - entry.created_at).total_seconds() > entry.ttl_seconds:
                    await self._evict_entry(cache_key, "ttl_expired")
                    evicted_bytes += entry.size_bytes
            
            # Second pass: oldest items
            if evicted_bytes < space_needed:
                sorted_entries = sorted(
                    self.cache_index.items(),
                    key=lambda x: x[1].created_at
                )
                
                for cache_key, entry in sorted_entries:
                    if evicted_bytes >= space_needed:
                        break
                    
                    await self._evict_entry(cache_key, "ttl_oldest")
                    evicted_bytes += entry.size_bytes
    
    async def _evict_entry(self, cache_key: str, reason: str):
        """Evict a cache entry"""
        entry = self.cache_index.get(cache_key)
        if not entry:
            return
        
        # Delete file
        file_path = Path(entry.file_path)
        if file_path.exists():
            file_path.unlink()
        
        # Update entry status
        entry.status = CacheStatus.EVICTED
        
        # Remove from index
        del self.cache_index[cache_key]
        self.cache_size_bytes -= entry.size_bytes
        
        # Remove from Redis
        await self._remove_cache_entry_redis(cache_key)
        
        edge_metrics.cache_evictions.labels(
            node_id=self.node_id,
            reason=reason
        ).inc()
        
        logger.info(
            "Evicted cache entry",
            cache_key=cache_key,
            reason=reason,
            size_mb=entry.size_bytes / (1024 * 1024)
        )
    
    async def _cleanup_loop(self):
        """Periodic cleanup of expired cache entries"""
        while True:
            try:
                await asyncio.sleep(300)  # Every 5 minutes
                
                now = datetime.utcnow()
                expired_keys = []
                
                async with self.cache_lock:
                    for cache_key, entry in self.cache_index.items():
                        if entry.ttl_seconds:
                            age_seconds = (now - entry.created_at).total_seconds()
                            if age_seconds > entry.ttl_seconds:
                                expired_keys.append(cache_key)
                    
                    # Evict expired entries
                    for cache_key in expired_keys:
                        await self._evict_entry(cache_key, "ttl_expired")
                
                if expired_keys:
                    logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")
                
            except Exception as e:
                logger.error("Error in cache cleanup", error=str(e))
    
    async def _sync_loop(self):
        """Sync cache state to Redis"""
        while True:
            try:
                await asyncio.sleep(60)  # Every minute
                
                # Update cache metrics in Redis
                await self.redis.hset(
                    f"edge:cache:stats:{self.node_id}",
                    mapping={
                        "size_bytes": self.cache_size_bytes,
                        "entry_count": len(self.cache_index),
                        "updated_at": datetime.utcnow().isoformat()
                    }
                )
                
                # Update hit/miss counters
                hits = edge_metrics.cache_hits._metrics.get(
                    (("node_id", self.node_id),), 0
                )
                misses = edge_metrics.cache_misses._metrics.get(
                    (("node_id", self.node_id),), 0
                )
                
                await self.redis.set(f"edge:cache:hits:{self.node_id}", hits)
                await self.redis.set(f"edge:cache:misses:{self.node_id}", misses)
                
            except Exception as e:
                logger.error("Error in cache sync", error=str(e))
    
    async def _load_cache_index(self):
        """Load cache index from disk"""
        index_file = self.cache_dir / "cache_index.json"
        
        if not index_file.exists():
            return
        
        try:
            async with aiofiles.open(index_file, "r") as f:
                data = await f.read()
                index_data = json.loads(data)
            
            # Rebuild index
            for entry_data in index_data:
                entry = CacheEntry(**entry_data)
                
                # Verify file exists
                if Path(entry.file_path).exists():
                    self.cache_index[entry.cache_key] = entry
                    self.cache_size_bytes += entry.size_bytes
            
            logger.info(f"Loaded {len(self.cache_index)} cache entries")
            
        except Exception as e:
            logger.error("Failed to load cache index", error=str(e))
    
    async def _save_cache_index(self):
        """Save cache index to disk"""
        index_file = self.cache_dir / "cache_index.json"
        
        try:
            # Convert entries to dict
            index_data = [entry.dict() for entry in self.cache_index.values()]
            
            async with aiofiles.open(index_file, "w") as f:
                await f.write(json.dumps(index_data, default=str))
            
        except Exception as e:
            logger.error("Failed to save cache index", error=str(e))
    
    async def _store_cache_entry_redis(self, entry: CacheEntry):
        """Store cache entry in Redis for cluster visibility"""
        key = f"edge:cache:{self.node_id}:{entry.cache_key}"
        await self.redis.setex(
            key,
            entry.ttl_seconds or 86400,  # Default 24h TTL
            entry.json()
        )
    
    async def _remove_cache_entry_redis(self, cache_key: str):
        """Remove cache entry from Redis"""
        key = f"edge:cache:{self.node_id}:{cache_key}"
        await self.redis.delete(key)
    
    def generate_cache_key(self, asset_id: str, variant: Optional[str] = None) -> str:
        """Generate cache key for an asset"""
        if variant:
            key_string = f"{asset_id}:{variant}"
        else:
            key_string = asset_id
        
        return hashlib.sha256(key_string.encode()).hexdigest()[:16]