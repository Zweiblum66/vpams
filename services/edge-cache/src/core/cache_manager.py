"""
Cache Manager for Edge Cache Service

This module provides the core caching functionality including storage backends,
eviction policies, and cache operations.
"""

from typing import Any, Dict, List, Optional, Tuple, Union
from datetime import datetime, timedelta
import asyncio
import time
import hashlib
import json
import pickle
import aiofiles
import aioredis
from pathlib import Path
import structlog
from enum import Enum
from dataclasses import dataclass
from cachetools import LRUCache, LFUCache, TTLCache
import xxhash

from .config import CacheStrategy, StorageBackend, Settings, CACHE_PRIORITY


logger = structlog.get_logger()


@dataclass
class CacheEntry:
    """Represents a cache entry"""
    key: str
    value: bytes
    content_type: str
    size: int
    created_at: float
    accessed_at: float
    access_count: int
    ttl: int
    etag: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    priority: int = 5


class CacheStats:
    """Cache statistics tracking"""
    
    def __init__(self):
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        self.total_size = 0
        self.entry_count = 0
        self.start_time = time.time()
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate"""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0
    
    @property
    def uptime(self) -> float:
        """Get cache uptime in seconds"""
        return time.time() - self.start_time
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert stats to dictionary"""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": self.hit_rate,
            "evictions": self.evictions,
            "total_size": self.total_size,
            "entry_count": self.entry_count,
            "uptime_seconds": self.uptime
        }


class BaseCacheBackend:
    """Base class for cache backends"""
    
    async def get(self, key: str) -> Optional[CacheEntry]:
        """Get item from cache"""
        raise NotImplementedError
    
    async def set(self, key: str, entry: CacheEntry) -> bool:
        """Set item in cache"""
        raise NotImplementedError
    
    async def delete(self, key: str) -> bool:
        """Delete item from cache"""
        raise NotImplementedError
    
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        raise NotImplementedError
    
    async def clear(self) -> int:
        """Clear all cache entries"""
        raise NotImplementedError
    
    async def get_keys(self, pattern: str = "*") -> List[str]:
        """Get keys matching pattern"""
        raise NotImplementedError
    
    async def get_size(self) -> int:
        """Get total cache size in bytes"""
        raise NotImplementedError


class MemoryCacheBackend(BaseCacheBackend):
    """In-memory cache backend"""
    
    def __init__(self, max_size: int, strategy: CacheStrategy):
        self.max_size = max_size
        self.strategy = strategy
        
        if strategy == CacheStrategy.LRU:
            self.cache = LRUCache(maxsize=max_size)
        elif strategy == CacheStrategy.LFU:
            self.cache = LFUCache(maxsize=max_size)
        elif strategy == CacheStrategy.TTL:
            self.cache = TTLCache(maxsize=max_size, ttl=3600)
        else:
            self.cache = {}
        
        self.size_tracker = {}
    
    async def get(self, key: str) -> Optional[CacheEntry]:
        """Get item from memory cache"""
        entry = self.cache.get(key)
        if entry:
            entry.accessed_at = time.time()
            entry.access_count += 1
        return entry
    
    async def set(self, key: str, entry: CacheEntry) -> bool:
        """Set item in memory cache"""
        try:
            # Check if we need to evict entries
            if isinstance(self.cache, dict) and len(self.cache) >= self.max_size:
                await self._evict_entries()
            
            self.cache[key] = entry
            self.size_tracker[key] = entry.size
            return True
        except Exception as e:
            logger.error("memory_cache_set_error", key=key, error=str(e))
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete item from memory cache"""
        if key in self.cache:
            del self.cache[key]
            del self.size_tracker[key]
            return True
        return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in memory"""
        return key in self.cache
    
    async def clear(self) -> int:
        """Clear memory cache"""
        count = len(self.cache)
        self.cache.clear()
        self.size_tracker.clear()
        return count
    
    async def get_keys(self, pattern: str = "*") -> List[str]:
        """Get keys from memory cache"""
        if pattern == "*":
            return list(self.cache.keys())
        
        # Simple pattern matching
        import fnmatch
        return [k for k in self.cache.keys() if fnmatch.fnmatch(k, pattern)]
    
    async def get_size(self) -> int:
        """Get total size in bytes"""
        return sum(self.size_tracker.values())
    
    async def _evict_entries(self):
        """Evict entries based on strategy"""
        if self.strategy == CacheStrategy.FIFO:
            # Remove oldest entry
            if self.cache:
                oldest_key = next(iter(self.cache))
                await self.delete(oldest_key)
        elif self.strategy == CacheStrategy.ADAPTIVE:
            # Remove lowest priority entry with least access
            min_score = float('inf')
            evict_key = None
            
            for key, entry in self.cache.items():
                score = entry.priority * entry.access_count / (time.time() - entry.created_at)
                if score < min_score:
                    min_score = score
                    evict_key = key
            
            if evict_key:
                await self.delete(evict_key)


class RedisCacheBackend(BaseCacheBackend):
    """Redis cache backend"""
    
    def __init__(self, redis_url: str, max_connections: int = 50):
        self.redis_url = redis_url
        self.max_connections = max_connections
        self.redis = None
    
    async def connect(self):
        """Connect to Redis"""
        self.redis = await aioredis.from_url(
            self.redis_url,
            max_connections=self.max_connections,
            decode_responses=False
        )
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis:
            await self.redis.close()
    
    async def get(self, key: str) -> Optional[CacheEntry]:
        """Get item from Redis"""
        try:
            data = await self.redis.get(f"mams:edge:{key}")
            if data:
                entry = pickle.loads(data)
                entry.accessed_at = time.time()
                entry.access_count += 1
                
                # Update access metadata
                await self.redis.hincrby(f"mams:edge:stats:{key}", "access_count", 1)
                await self.redis.hset(f"mams:edge:stats:{key}", "accessed_at", time.time())
                
                return entry
        except Exception as e:
            logger.error("redis_cache_get_error", key=key, error=str(e))
        
        return None
    
    async def set(self, key: str, entry: CacheEntry) -> bool:
        """Set item in Redis"""
        try:
            data = pickle.dumps(entry)
            
            # Set main entry
            await self.redis.setex(
                f"mams:edge:{key}",
                entry.ttl,
                data
            )
            
            # Set metadata
            await self.redis.hset(
                f"mams:edge:stats:{key}",
                mapping={
                    "size": entry.size,
                    "created_at": entry.created_at,
                    "content_type": entry.content_type,
                    "priority": entry.priority
                }
            )
            
            # Set expiry on metadata
            await self.redis.expire(f"mams:edge:stats:{key}", entry.ttl)
            
            return True
        except Exception as e:
            logger.error("redis_cache_set_error", key=key, error=str(e))
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete item from Redis"""
        try:
            result = await self.redis.delete(
                f"mams:edge:{key}",
                f"mams:edge:stats:{key}"
            )
            return result > 0
        except Exception as e:
            logger.error("redis_cache_delete_error", key=key, error=str(e))
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis"""
        return await self.redis.exists(f"mams:edge:{key}") > 0
    
    async def clear(self) -> int:
        """Clear all cache entries"""
        try:
            keys = await self.redis.keys("mams:edge:*")
            if keys:
                return await self.redis.delete(*keys)
            return 0
        except Exception as e:
            logger.error("redis_cache_clear_error", error=str(e))
            return 0
    
    async def get_keys(self, pattern: str = "*") -> List[str]:
        """Get keys matching pattern"""
        try:
            keys = await self.redis.keys(f"mams:edge:{pattern}")
            return [k.decode().replace("mams:edge:", "") for k in keys if k.startswith(b"mams:edge:") and not k.startswith(b"mams:edge:stats:")]
        except Exception as e:
            logger.error("redis_cache_get_keys_error", error=str(e))
            return []
    
    async def get_size(self) -> int:
        """Get total cache size"""
        try:
            keys = await self.redis.keys("mams:edge:stats:*")
            total_size = 0
            
            for key in keys:
                size = await self.redis.hget(key, "size")
                if size:
                    total_size += int(size)
            
            return total_size
        except Exception as e:
            logger.error("redis_cache_get_size_error", error=str(e))
            return 0


class DiskCacheBackend(BaseCacheBackend):
    """Disk-based cache backend"""
    
    def __init__(self, cache_dir: str, max_size: int):
        self.cache_dir = Path(cache_dir)
        self.max_size = max_size
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_file = self.cache_dir / ".metadata.json"
        self.metadata = {}
        self._load_metadata()
    
    def _load_metadata(self):
        """Load metadata from disk"""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r') as f:
                    self.metadata = json.load(f)
            except Exception as e:
                logger.error("disk_cache_metadata_load_error", error=str(e))
                self.metadata = {}
    
    def _save_metadata(self):
        """Save metadata to disk"""
        try:
            with open(self.metadata_file, 'w') as f:
                json.dump(self.metadata, f)
        except Exception as e:
            logger.error("disk_cache_metadata_save_error", error=str(e))
    
    def _get_file_path(self, key: str) -> Path:
        """Get file path for cache key"""
        # Use hash to avoid filesystem issues with special characters
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash[:2]}" / f"{key_hash}.cache"
    
    async def get(self, key: str) -> Optional[CacheEntry]:
        """Get item from disk cache"""
        file_path = self._get_file_path(key)
        
        if not file_path.exists():
            return None
        
        try:
            async with aiofiles.open(file_path, 'rb') as f:
                data = await f.read()
                entry = pickle.loads(data)
                
                # Check TTL
                if time.time() > entry.created_at + entry.ttl:
                    await self.delete(key)
                    return None
                
                entry.accessed_at = time.time()
                entry.access_count += 1
                
                # Update metadata
                if key in self.metadata:
                    self.metadata[key]["accessed_at"] = entry.accessed_at
                    self.metadata[key]["access_count"] = entry.access_count
                    self._save_metadata()
                
                return entry
        except Exception as e:
            logger.error("disk_cache_get_error", key=key, error=str(e))
            return None
    
    async def set(self, key: str, entry: CacheEntry) -> bool:
        """Set item in disk cache"""
        file_path = self._get_file_path(key)
        
        try:
            # Create directory if needed
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Check if we need to evict
            current_size = await self.get_size()
            if current_size + entry.size > self.max_size:
                await self._evict_entries(entry.size)
            
            # Write to disk
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(pickle.dumps(entry))
            
            # Update metadata
            self.metadata[key] = {
                "size": entry.size,
                "created_at": entry.created_at,
                "accessed_at": entry.accessed_at,
                "access_count": entry.access_count,
                "priority": entry.priority,
                "file_path": str(file_path)
            }
            self._save_metadata()
            
            return True
        except Exception as e:
            logger.error("disk_cache_set_error", key=key, error=str(e))
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete item from disk cache"""
        file_path = self._get_file_path(key)
        
        try:
            if file_path.exists():
                file_path.unlink()
            
            if key in self.metadata:
                del self.metadata[key]
                self._save_metadata()
            
            return True
        except Exception as e:
            logger.error("disk_cache_delete_error", key=key, error=str(e))
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists on disk"""
        return self._get_file_path(key).exists()
    
    async def clear(self) -> int:
        """Clear disk cache"""
        count = 0
        
        try:
            for key in list(self.metadata.keys()):
                if await self.delete(key):
                    count += 1
            
            # Clean up empty directories
            for subdir in self.cache_dir.iterdir():
                if subdir.is_dir() and not any(subdir.iterdir()):
                    subdir.rmdir()
            
            return count
        except Exception as e:
            logger.error("disk_cache_clear_error", error=str(e))
            return count
    
    async def get_keys(self, pattern: str = "*") -> List[str]:
        """Get keys from disk cache"""
        if pattern == "*":
            return list(self.metadata.keys())
        
        import fnmatch
        return [k for k in self.metadata.keys() if fnmatch.fnmatch(k, pattern)]
    
    async def get_size(self) -> int:
        """Get total cache size on disk"""
        return sum(meta["size"] for meta in self.metadata.values())
    
    async def _evict_entries(self, required_space: int):
        """Evict entries to make space"""
        # Sort by priority and access time
        entries = [
            (k, v) for k, v in self.metadata.items()
        ]
        entries.sort(
            key=lambda x: (x[1]["priority"], x[1]["accessed_at"])
        )
        
        freed_space = 0
        for key, meta in entries:
            if freed_space >= required_space:
                break
            
            await self.delete(key)
            freed_space += meta["size"]


class HybridCacheBackend(BaseCacheBackend):
    """Hybrid cache backend (Memory + Disk)"""
    
    def __init__(self, memory_size: int, disk_size: int, cache_dir: str, strategy: CacheStrategy):
        self.memory_cache = MemoryCacheBackend(memory_size, strategy)
        self.disk_cache = DiskCacheBackend(cache_dir, disk_size)
    
    async def get(self, key: str) -> Optional[CacheEntry]:
        """Get from memory first, then disk"""
        # Try memory first
        entry = await self.memory_cache.get(key)
        if entry:
            return entry
        
        # Try disk
        entry = await self.disk_cache.get(key)
        if entry:
            # Promote to memory if frequently accessed
            if entry.access_count > 5:
                await self.memory_cache.set(key, entry)
        
        return entry
    
    async def set(self, key: str, entry: CacheEntry) -> bool:
        """Set in both memory and disk based on priority"""
        # High priority items go to memory
        if entry.priority >= 7:
            memory_result = await self.memory_cache.set(key, entry)
            if not memory_result:
                # Fall back to disk if memory is full
                return await self.disk_cache.set(key, entry)
            return memory_result
        
        # Lower priority items go directly to disk
        return await self.disk_cache.set(key, entry)
    
    async def delete(self, key: str) -> bool:
        """Delete from both backends"""
        memory_result = await self.memory_cache.delete(key)
        disk_result = await self.disk_cache.delete(key)
        return memory_result or disk_result
    
    async def exists(self, key: str) -> bool:
        """Check both backends"""
        return await self.memory_cache.exists(key) or await self.disk_cache.exists(key)
    
    async def clear(self) -> int:
        """Clear both backends"""
        memory_count = await self.memory_cache.clear()
        disk_count = await self.disk_cache.clear()
        return memory_count + disk_count
    
    async def get_keys(self, pattern: str = "*") -> List[str]:
        """Get keys from both backends"""
        memory_keys = set(await self.memory_cache.get_keys(pattern))
        disk_keys = set(await self.disk_cache.get_keys(pattern))
        return list(memory_keys | disk_keys)
    
    async def get_size(self) -> int:
        """Get total size from both backends"""
        memory_size = await self.memory_cache.get_size()
        disk_size = await self.disk_cache.get_size()
        return memory_size + disk_size


class CacheManager:
    """Main cache manager coordinating all cache operations"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.stats = CacheStats()
        self.backend = None
        self._lock = asyncio.Lock()
    
    async def initialize(self):
        """Initialize cache backend"""
        if self.settings.storage_backend == StorageBackend.MEMORY:
            self.backend = MemoryCacheBackend(
                max_size=self.settings.cache_size_mb * 1024 * 1024,
                strategy=self.settings.cache_strategy
            )
        elif self.settings.storage_backend == StorageBackend.REDIS:
            self.backend = RedisCacheBackend(
                redis_url=self.settings.redis_url,
                max_connections=self.settings.redis_max_connections
            )
            await self.backend.connect()
        elif self.settings.storage_backend == StorageBackend.DISK:
            self.backend = DiskCacheBackend(
                cache_dir=self.settings.disk_cache_path,
                max_size=self.settings.cache_size_mb * 1024 * 1024
            )
        elif self.settings.storage_backend == StorageBackend.HYBRID:
            self.backend = HybridCacheBackend(
                memory_size=self.settings.memory_cache_size_mb * 1024 * 1024,
                disk_size=self.settings.cache_size_mb * 1024 * 1024,
                cache_dir=self.settings.disk_cache_path,
                strategy=self.settings.cache_strategy
            )
        
        logger.info(
            "cache_manager_initialized",
            backend=self.settings.storage_backend,
            strategy=self.settings.cache_strategy,
            size_mb=self.settings.cache_size_mb
        )
    
    async def shutdown(self):
        """Shutdown cache backend"""
        if isinstance(self.backend, RedisCacheBackend):
            await self.backend.disconnect()
    
    def generate_cache_key(self, url: str, headers: Dict[str, str]) -> str:
        """Generate cache key from URL and headers"""
        # Include important headers in cache key
        key_parts = [url]
        
        for header in self.settings.cache_headers:
            if header in headers:
                key_parts.append(f"{header}:{headers[header]}")
        
        # Use xxhash for fast hashing
        key_string = "|".join(key_parts)
        return xxhash.xxh64(key_string.encode()).hexdigest()
    
    def is_cacheable(self, content_type: str, size: int) -> bool:
        """Check if content is cacheable"""
        # Check size limit
        if size > self.settings.max_object_size_mb * 1024 * 1024:
            return False
        
        # Check content type
        for pattern in self.settings.cacheable_content_types:
            if pattern.endswith("*"):
                if content_type.startswith(pattern[:-1]):
                    return True
            elif content_type == pattern:
                return True
        
        return False
    
    async def get(self, key: str) -> Optional[Tuple[bytes, Dict[str, str]]]:
        """Get item from cache"""
        async with self._lock:
            entry = await self.backend.get(key)
            
            if entry:
                self.stats.hits += 1
                logger.debug("cache_hit", key=key, size=entry.size)
                return entry.value, entry.headers or {}
            else:
                self.stats.misses += 1
                logger.debug("cache_miss", key=key)
                return None
    
    async def set(
        self,
        key: str,
        value: bytes,
        content_type: str,
        ttl: Optional[int] = None,
        headers: Optional[Dict[str, str]] = None,
        priority: Optional[int] = None
    ) -> bool:
        """Set item in cache"""
        if not self.is_cacheable(content_type, len(value)):
            return False
        
        # Determine priority if not provided
        if priority is None:
            priority = self._get_content_priority(content_type)
        
        entry = CacheEntry(
            key=key,
            value=value,
            content_type=content_type,
            size=len(value),
            created_at=time.time(),
            accessed_at=time.time(),
            access_count=0,
            ttl=ttl or self.settings.cache_ttl_seconds,
            etag=self._generate_etag(value),
            headers=headers,
            priority=priority
        )
        
        async with self._lock:
            result = await self.backend.set(key, entry)
            
            if result:
                self.stats.entry_count += 1
                self.stats.total_size += entry.size
                logger.debug(
                    "cache_set",
                    key=key,
                    size=entry.size,
                    ttl=entry.ttl,
                    priority=entry.priority
                )
            
            return result
    
    async def delete(self, key: str) -> bool:
        """Delete item from cache"""
        async with self._lock:
            result = await self.backend.delete(key)
            
            if result:
                self.stats.entry_count -= 1
                logger.debug("cache_delete", key=key)
            
            return result
    
    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all keys matching pattern"""
        count = 0
        
        async with self._lock:
            keys = await self.backend.get_keys(pattern)
            
            for batch_start in range(0, len(keys), self.settings.invalidation_batch_size):
                batch = keys[batch_start:batch_start + self.settings.invalidation_batch_size]
                
                for key in batch:
                    if await self.backend.delete(key):
                        count += 1
                
                # Small delay between batches
                if batch_start + self.settings.invalidation_batch_size < len(keys):
                    await asyncio.sleep(self.settings.invalidation_delay_ms / 1000)
        
        logger.info("cache_invalidate_pattern", pattern=pattern, count=count)
        return count
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        stats = self.stats.to_dict()
        stats["backend_size"] = await self.backend.get_size()
        stats["backend_type"] = self.settings.storage_backend.value
        return stats
    
    def _get_content_priority(self, content_type: str) -> int:
        """Determine content priority based on type"""
        if content_type.startswith("image/") and "thumbnail" in content_type:
            return CACHE_PRIORITY["thumbnail"]
        elif content_type == "application/json":
            return CACHE_PRIORITY["metadata"]
        elif content_type.startswith("video/"):
            return CACHE_PRIORITY["proxy_medium"]
        elif content_type.startswith("image/"):
            return CACHE_PRIORITY["proxy_low"]
        else:
            return 5  # Default priority
    
    def _generate_etag(self, content: bytes) -> str:
        """Generate ETag for content"""
        return f'"{xxhash.xxh64(content).hexdigest()}"'