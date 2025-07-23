"""
Tests for cache manager
"""

import pytest
import time
from unittest.mock import Mock, patch

from src.core.cache_manager import (
    CacheManager, CacheEntry, CacheStats,
    MemoryCacheBackend, RedisCacheBackend, DiskCacheBackend, HybridCacheBackend
)
from src.core.config import CacheStrategy, StorageBackend, CACHE_PRIORITY


class TestCacheStats:
    """Test cache statistics"""
    
    def test_init(self):
        """Test stats initialization"""
        stats = CacheStats()
        
        assert stats.hits == 0
        assert stats.misses == 0
        assert stats.evictions == 0
        assert stats.total_size == 0
        assert stats.entry_count == 0
        assert stats.start_time > 0
    
    def test_hit_rate(self):
        """Test hit rate calculation"""
        stats = CacheStats()
        
        # No requests
        assert stats.hit_rate == 0.0
        
        # Some hits and misses
        stats.hits = 75
        stats.misses = 25
        assert stats.hit_rate == 0.75
        
        # All hits
        stats.hits = 100
        stats.misses = 0
        assert stats.hit_rate == 1.0
    
    def test_to_dict(self):
        """Test stats serialization"""
        stats = CacheStats()
        stats.hits = 10
        stats.misses = 5
        
        data = stats.to_dict()
        
        assert data["hits"] == 10
        assert data["misses"] == 5
        assert data["hit_rate"] == 10 / 15
        assert "uptime_seconds" in data


class TestCacheEntry:
    """Test cache entry"""
    
    def test_creation(self):
        """Test cache entry creation"""
        entry = CacheEntry(
            key="test_key",
            value=b"test_value",
            content_type="text/plain",
            size=10,
            created_at=time.time(),
            accessed_at=time.time(),
            access_count=0,
            ttl=300,
            etag='"abc123"',
            headers={"x-custom": "value"},
            priority=5
        )
        
        assert entry.key == "test_key"
        assert entry.value == b"test_value"
        assert entry.content_type == "text/plain"
        assert entry.size == 10
        assert entry.ttl == 300
        assert entry.etag == '"abc123"'
        assert entry.headers == {"x-custom": "value"}
        assert entry.priority == 5


class TestMemoryCacheBackend:
    """Test memory cache backend"""
    
    @pytest.mark.asyncio
    async def test_basic_operations(self):
        """Test basic cache operations"""
        backend = MemoryCacheBackend(max_size=100, strategy=CacheStrategy.LRU)
        
        # Create entry
        entry = CacheEntry(
            key="test",
            value=b"value",
            content_type="text/plain",
            size=5,
            created_at=time.time(),
            accessed_at=time.time(),
            access_count=0,
            ttl=300,
            priority=5
        )
        
        # Set
        assert await backend.set("test", entry) is True
        assert await backend.exists("test") is True
        
        # Get
        retrieved = await backend.get("test")
        assert retrieved is not None
        assert retrieved.value == b"value"
        assert retrieved.access_count == 1
        
        # Delete
        assert await backend.delete("test") is True
        assert await backend.exists("test") is False
        assert await backend.get("test") is None
    
    @pytest.mark.asyncio
    async def test_clear(self):
        """Test clearing cache"""
        backend = MemoryCacheBackend(max_size=100, strategy=CacheStrategy.LRU)
        
        # Add multiple entries
        for i in range(5):
            entry = CacheEntry(
                key=f"test{i}",
                value=f"value{i}".encode(),
                content_type="text/plain",
                size=10,
                created_at=time.time(),
                accessed_at=time.time(),
                access_count=0,
                ttl=300,
                priority=5
            )
            await backend.set(f"test{i}", entry)
        
        # Clear
        count = await backend.clear()
        assert count == 5
        assert await backend.get_size() == 0
    
    @pytest.mark.asyncio
    async def test_get_keys(self):
        """Test getting keys"""
        backend = MemoryCacheBackend(max_size=100, strategy=CacheStrategy.LRU)
        
        # Add entries
        for i in range(3):
            entry = CacheEntry(
                key=f"asset:{i}",
                value=b"value",
                content_type="text/plain",
                size=5,
                created_at=time.time(),
                accessed_at=time.time(),
                access_count=0,
                ttl=300,
                priority=5
            )
            await backend.set(f"asset:{i}", entry)
        
        # Get all keys
        keys = await backend.get_keys("*")
        assert len(keys) == 3
        
        # Get matching keys
        keys = await backend.get_keys("asset:*")
        assert len(keys) == 3
    
    @pytest.mark.asyncio
    async def test_eviction(self):
        """Test cache eviction"""
        backend = MemoryCacheBackend(max_size=2, strategy=CacheStrategy.FIFO)
        
        # Fill cache
        for i in range(3):
            entry = CacheEntry(
                key=f"test{i}",
                value=b"value",
                content_type="text/plain",
                size=5,
                created_at=time.time() + i,
                accessed_at=time.time(),
                access_count=0,
                ttl=300,
                priority=5
            )
            await backend.set(f"test{i}", entry)
        
        # First entry should be evicted
        assert await backend.exists("test0") is False
        assert await backend.exists("test1") is True
        assert await backend.exists("test2") is True


class TestDiskCacheBackend:
    """Test disk cache backend"""
    
    @pytest.mark.asyncio
    async def test_basic_operations(self, tmp_path):
        """Test basic disk cache operations"""
        backend = DiskCacheBackend(
            cache_dir=str(tmp_path / "cache"),
            max_size=1024 * 1024  # 1MB
        )
        
        # Create entry
        entry = CacheEntry(
            key="test",
            value=b"test value on disk",
            content_type="text/plain",
            size=18,
            created_at=time.time(),
            accessed_at=time.time(),
            access_count=0,
            ttl=300,
            priority=5
        )
        
        # Set
        assert await backend.set("test", entry) is True
        assert await backend.exists("test") is True
        
        # Get
        retrieved = await backend.get("test")
        assert retrieved is not None
        assert retrieved.value == b"test value on disk"
        
        # Delete
        assert await backend.delete("test") is True
        assert await backend.exists("test") is False
    
    @pytest.mark.asyncio
    async def test_ttl_expiry(self, tmp_path):
        """Test TTL expiry on disk"""
        backend = DiskCacheBackend(
            cache_dir=str(tmp_path / "cache"),
            max_size=1024 * 1024
        )
        
        # Create expired entry
        entry = CacheEntry(
            key="expired",
            value=b"old data",
            content_type="text/plain",
            size=8,
            created_at=time.time() - 400,  # Created 400s ago
            accessed_at=time.time() - 400,
            access_count=0,
            ttl=300,  # 300s TTL
            priority=5
        )
        
        await backend.set("expired", entry)
        
        # Should return None due to expiry
        retrieved = await backend.get("expired")
        assert retrieved is None
        assert await backend.exists("expired") is False


class TestHybridCacheBackend:
    """Test hybrid cache backend"""
    
    @pytest.mark.asyncio
    async def test_priority_routing(self, tmp_path):
        """Test priority-based routing"""
        backend = HybridCacheBackend(
            memory_size=100,
            disk_size=1000,
            cache_dir=str(tmp_path / "cache"),
            strategy=CacheStrategy.LRU
        )
        
        # High priority - should go to memory
        high_priority = CacheEntry(
            key="high",
            value=b"important",
            content_type="text/plain",
            size=9,
            created_at=time.time(),
            accessed_at=time.time(),
            access_count=0,
            ttl=300,
            priority=8
        )
        
        # Low priority - should go to disk
        low_priority = CacheEntry(
            key="low",
            value=b"less important",
            content_type="text/plain",
            size=14,
            created_at=time.time(),
            accessed_at=time.time(),
            access_count=0,
            ttl=300,
            priority=3
        )
        
        await backend.set("high", high_priority)
        await backend.set("low", low_priority)
        
        # Check both are retrievable
        assert await backend.get("high") is not None
        assert await backend.get("low") is not None
        
        # High priority should be in memory
        assert await backend.memory_cache.exists("high") is True
        assert await backend.memory_cache.exists("low") is False


class TestCacheManager:
    """Test cache manager"""
    
    @pytest.mark.asyncio
    async def test_initialization(self, test_settings):
        """Test cache manager initialization"""
        manager = CacheManager(test_settings)
        await manager.initialize()
        
        assert manager.backend is not None
        assert manager.stats is not None
        
        await manager.shutdown()
    
    @pytest.mark.asyncio
    async def test_cache_key_generation(self, cache_manager):
        """Test cache key generation"""
        url = "/api/v1/assets/123"
        headers = {
            "Accept": "application/json",
            "Authorization": "Bearer token123"
        }
        
        key1 = cache_manager.generate_cache_key(url, headers)
        key2 = cache_manager.generate_cache_key(url, headers)
        
        # Same inputs should generate same key
        assert key1 == key2
        
        # Different headers should generate different key
        headers2 = headers.copy()
        headers2["Accept"] = "text/html"
        key3 = cache_manager.generate_cache_key(url, headers2)
        
        assert key1 != key3
    
    @pytest.mark.asyncio
    async def test_is_cacheable(self, cache_manager):
        """Test cacheability checks"""
        # Cacheable content types
        assert cache_manager.is_cacheable("image/png", 1000) is True
        assert cache_manager.is_cacheable("video/mp4", 1000) is True
        assert cache_manager.is_cacheable("application/json", 1000) is True
        
        # Non-cacheable
        assert cache_manager.is_cacheable("text/html", 1000) is False
        
        # Too large
        max_size = cache_manager.settings.max_object_size_mb * 1024 * 1024
        assert cache_manager.is_cacheable("image/png", max_size + 1) is False
    
    @pytest.mark.asyncio
    async def test_get_set(self, cache_manager):
        """Test get and set operations"""
        key = "test_key"
        content = b"test content"
        headers = {"content-type": "text/plain"}
        
        # Set
        result = await cache_manager.set(
            key,
            content,
            "text/plain",
            ttl=60,
            headers=headers
        )
        assert result is True
        
        # Get
        retrieved = await cache_manager.get(key)
        assert retrieved is not None
        
        value, retrieved_headers = retrieved
        assert value == content
        assert retrieved_headers["content-type"] == "text/plain"
        
        # Stats should be updated
        assert cache_manager.stats.hits == 1
        assert cache_manager.stats.misses == 0
    
    @pytest.mark.asyncio
    async def test_cache_miss(self, cache_manager):
        """Test cache miss"""
        result = await cache_manager.get("non_existent_key")
        assert result is None
        
        assert cache_manager.stats.hits == 0
        assert cache_manager.stats.misses == 1
    
    @pytest.mark.asyncio
    async def test_delete(self, cache_manager):
        """Test delete operation"""
        key = "delete_test"
        
        # Set
        await cache_manager.set(key, b"data", "text/plain")
        
        # Delete
        result = await cache_manager.delete(key)
        assert result is True
        
        # Should be gone
        assert await cache_manager.get(key) is None
    
    @pytest.mark.asyncio
    async def test_invalidate_pattern(self, cache_manager):
        """Test pattern-based invalidation"""
        # Set multiple entries
        for i in range(5):
            await cache_manager.set(
                f"asset:{i}",
                f"data{i}".encode(),
                "text/plain"
            )
        
        # Invalidate pattern
        count = await cache_manager.invalidate_pattern("asset:*")
        assert count == 5
        
        # All should be gone
        for i in range(5):
            assert await cache_manager.get(f"asset:{i}") is None
    
    @pytest.mark.asyncio
    async def test_priority_assignment(self, cache_manager):
        """Test automatic priority assignment"""
        # Thumbnail should get high priority
        priority = cache_manager._get_content_priority("image/png")
        assert priority == CACHE_PRIORITY["thumbnail"] or priority == CACHE_PRIORITY["proxy_low"]
        
        # JSON metadata
        priority = cache_manager._get_content_priority("application/json")
        assert priority == CACHE_PRIORITY["metadata"]
        
        # Video
        priority = cache_manager._get_content_priority("video/mp4")
        assert priority == CACHE_PRIORITY["proxy_medium"]
    
    @pytest.mark.asyncio
    async def test_etag_generation(self, cache_manager):
        """Test ETag generation"""
        content1 = b"test content"
        content2 = b"different content"
        
        etag1 = cache_manager._generate_etag(content1)
        etag2 = cache_manager._generate_etag(content2)
        
        # Different content should have different ETags
        assert etag1 != etag2
        
        # Same content should have same ETag
        etag3 = cache_manager._generate_etag(content1)
        assert etag1 == etag3
        
        # Should be properly formatted
        assert etag1.startswith('"') and etag1.endswith('"')