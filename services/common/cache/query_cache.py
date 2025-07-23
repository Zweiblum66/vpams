"""
Query caching implementation for MAMS services.

This module provides a comprehensive caching layer for database queries
to improve performance and reduce database load.
"""

import json
import hashlib
import pickle
from typing import Any, Optional, Callable, Dict, List, Union
from datetime import datetime, timedelta
from functools import wraps
import asyncio
from redis import asyncio as aioredis
import logging

logger = logging.getLogger(__name__)


class CacheKey:
    """Utility class for generating consistent cache keys."""
    
    @staticmethod
    def generate(
        prefix: str,
        *args,
        **kwargs
    ) -> str:
        """
        Generate a cache key from prefix and parameters.
        
        Args:
            prefix: Cache key prefix (e.g., 'asset', 'user')
            *args: Positional arguments to include in key
            **kwargs: Keyword arguments to include in key
            
        Returns:
            Cache key string
        """
        # Create a consistent string representation
        key_parts = [prefix]
        
        # Add positional arguments
        for arg in args:
            if isinstance(arg, (str, int, float, bool)):
                key_parts.append(str(arg))
            elif isinstance(arg, (list, tuple)):
                key_parts.append(':'.join(str(x) for x in arg))
            elif isinstance(arg, dict):
                # Sort dict keys for consistency
                sorted_items = sorted(arg.items())
                key_parts.append(':'.join(f"{k}={v}" for k, v in sorted_items))
            else:
                # For complex objects, use hash
                key_parts.append(hashlib.md5(
                    str(arg).encode()
                ).hexdigest()[:8])
                
        # Add keyword arguments (sorted for consistency)
        for key, value in sorted(kwargs.items()):
            key_parts.append(f"{key}={value}")
            
        return ':'.join(key_parts)
    
    @staticmethod
    def generate_pattern(prefix: str, *partial_args) -> str:
        """Generate a pattern for cache key matching."""
        key_parts = [prefix]
        key_parts.extend(str(arg) for arg in partial_args)
        key_parts.append('*')
        return ':'.join(key_parts)


class QueryCache:
    """Main query caching class with Redis backend."""
    
    def __init__(
        self,
        redis_url: str,
        default_ttl: int = 300,
        max_connections: int = 50,
        namespace: str = 'mams'
    ):
        """
        Initialize query cache.
        
        Args:
            redis_url: Redis connection URL
            default_ttl: Default TTL in seconds (5 minutes)
            max_connections: Maximum Redis connections
            namespace: Cache key namespace
        """
        self.redis_url = redis_url
        self.default_ttl = default_ttl
        self.namespace = namespace
        self._redis = None
        self._pool = None
        self.max_connections = max_connections
        
    async def connect(self):
        """Connect to Redis."""
        if not self._pool:
            self._pool = aioredis.ConnectionPool.from_url(
                self.redis_url,
                max_connections=self.max_connections,
                decode_responses=False  # We'll handle encoding
            )
        if not self._redis:
            self._redis = aioredis.Redis(connection_pool=self._pool)
            
    async def disconnect(self):
        """Disconnect from Redis."""
        if self._redis:
            await self._redis.close()
            self._redis = None
        if self._pool:
            await self._pool.disconnect()
            self._pool = None
            
    def _make_key(self, key: str) -> str:
        """Add namespace to cache key."""
        return f"{self.namespace}:{key}"
    
    async def get(
        self,
        key: str,
        deserializer: Optional[Callable] = None
    ) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            deserializer: Optional custom deserializer
            
        Returns:
            Cached value or None
        """
        await self.connect()
        
        try:
            value = await self._redis.get(self._make_key(key))
            if value is None:
                return None
                
            # Deserialize
            if deserializer:
                return deserializer(value)
            else:
                # Try JSON first, fall back to pickle
                try:
                    return json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    return pickle.loads(value)
                    
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            return None
            
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        serializer: Optional[Callable] = None
    ) -> bool:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
            serializer: Optional custom serializer
            
        Returns:
            Success boolean
        """
        await self.connect()
        
        ttl = ttl or self.default_ttl
        
        try:
            # Serialize
            if serializer:
                serialized = serializer(value)
            else:
                # Try JSON first, fall back to pickle
                try:
                    serialized = json.dumps(value, default=str)
                except (TypeError, ValueError):
                    serialized = pickle.dumps(value)
                    
            await self._redis.setex(
                self._make_key(key),
                ttl,
                serialized
            )
            return True
            
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False
            
    async def delete(self, key: str) -> bool:
        """Delete a cache entry."""
        await self.connect()
        
        try:
            result = await self._redis.delete(self._make_key(key))
            return result > 0
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False
            
    async def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching pattern.
        
        Args:
            pattern: Pattern to match (e.g., 'user:123:*')
            
        Returns:
            Number of deleted keys
        """
        await self.connect()
        
        full_pattern = self._make_key(pattern)
        deleted = 0
        
        try:
            # Use SCAN to avoid blocking
            cursor = 0
            while True:
                cursor, keys = await self._redis.scan(
                    cursor,
                    match=full_pattern,
                    count=100
                )
                
                if keys:
                    deleted += await self._redis.delete(*keys)
                    
                if cursor == 0:
                    break
                    
            return deleted
            
        except Exception as e:
            logger.error(f"Cache delete pattern error for {pattern}: {e}")
            return 0
            
    async def get_or_set(
        self,
        key: str,
        factory: Callable,
        ttl: Optional[int] = None,
        force_refresh: bool = False
    ) -> Any:
        """
        Get from cache or compute and set.
        
        Args:
            key: Cache key
            factory: Async function to compute value
            ttl: Time to live
            force_refresh: Force recomputation
            
        Returns:
            Cached or computed value
        """
        if not force_refresh:
            cached = await self.get(key)
            if cached is not None:
                return cached
                
        # Compute value
        value = await factory()
        
        # Cache it
        await self.set(key, value, ttl)
        
        return value
        
    async def multi_get(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple values at once."""
        await self.connect()
        
        full_keys = [self._make_key(key) for key in keys]
        
        try:
            values = await self._redis.mget(full_keys)
            
            result = {}
            for key, value in zip(keys, values):
                if value is not None:
                    try:
                        result[key] = json.loads(value)
                    except (json.JSONDecodeError, TypeError):
                        result[key] = pickle.loads(value)
                        
            return result
            
        except Exception as e:
            logger.error(f"Cache multi_get error: {e}")
            return {}
            
    async def multi_set(
        self,
        items: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> bool:
        """Set multiple values at once."""
        await self.connect()
        
        ttl = ttl or self.default_ttl
        
        try:
            pipe = self._redis.pipeline()
            
            for key, value in items.items():
                try:
                    serialized = json.dumps(value, default=str)
                except (TypeError, ValueError):
                    serialized = pickle.dumps(value)
                    
                pipe.setex(self._make_key(key), ttl, serialized)
                
            await pipe.execute()
            return True
            
        except Exception as e:
            logger.error(f"Cache multi_set error: {e}")
            return False


def cached(
    key_prefix: str,
    ttl: Optional[int] = None,
    key_builder: Optional[Callable] = None
):
    """
    Decorator for caching function results.
    
    Args:
        key_prefix: Prefix for cache keys
        ttl: Time to live in seconds
        key_builder: Optional function to build cache key
        
    Example:
        @cached('user_assets', ttl=600)
        async def get_user_assets(user_id: UUID, page: int = 1):
            # Expensive database query
            return await db.fetch_assets(user_id, page)
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get cache instance from somewhere (e.g., app state)
            cache = getattr(wrapper, '_cache', None)
            if not cache:
                logger.warning(f"No cache configured for {func.__name__}")
                return await func(*args, **kwargs)
                
            # Build cache key
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                # Default key building
                cache_key = CacheKey.generate(
                    key_prefix,
                    *args[1:],  # Skip 'self' if present
                    **kwargs
                )
                
            # Try to get from cache
            try:
                cached_value = await cache.get(cache_key)
                if cached_value is not None:
                    logger.debug(f"Cache hit for {cache_key}")
                    return cached_value
            except Exception as e:
                logger.error(f"Cache error, continuing without cache: {e}")
                
            # Compute value
            result = await func(*args, **kwargs)
            
            # Cache it
            try:
                await cache.set(cache_key, result, ttl)
            except Exception as e:
                logger.error(f"Failed to cache result: {e}")
                
            return result
            
        # Allow setting cache instance
        wrapper._cache = None
        return wrapper
        
    return decorator


class CacheInvalidation:
    """Handles cache invalidation patterns."""
    
    def __init__(self, cache: QueryCache):
        self.cache = cache
        
    async def invalidate_user(self, user_id: str):
        """Invalidate all user-related caches."""
        patterns = [
            f'user:{user_id}:*',
            f'user_assets:{user_id}:*',
            f'user_permissions:{user_id}:*',
            f'user_profile:{user_id}'
        ]
        
        for pattern in patterns:
            await self.cache.delete_pattern(pattern)
            
    async def invalidate_asset(self, asset_id: str):
        """Invalidate all asset-related caches."""
        patterns = [
            f'asset:{asset_id}:*',
            f'asset_metadata:{asset_id}',
            f'asset_versions:{asset_id}:*',
            'asset_list:*'  # List caches might be affected
        ]
        
        for pattern in patterns:
            await self.cache.delete_pattern(pattern)
            
    async def invalidate_search(self):
        """Invalidate all search-related caches."""
        await self.cache.delete_pattern('search:*')
        
    async def invalidate_project(self, project_id: str):
        """Invalidate project-related caches."""
        patterns = [
            f'project:{project_id}:*',
            f'project_assets:{project_id}:*',
            'project_list:*'
        ]
        
        for pattern in patterns:
            await self.cache.delete_pattern(pattern)


# Service-specific cache implementations
class AssetCache:
    """Asset-specific caching logic."""
    
    def __init__(self, cache: QueryCache):
        self.cache = cache
        self.invalidator = CacheInvalidation(cache)
        
    async def get_asset(self, asset_id: str) -> Optional[Dict]:
        """Get cached asset."""
        return await self.cache.get(f'asset:{asset_id}')
        
    async def set_asset(self, asset_id: str, asset_data: Dict, ttl: int = 600):
        """Cache asset data."""
        await self.cache.set(f'asset:{asset_id}', asset_data, ttl)
        
    async def get_asset_list(
        self,
        user_id: str,
        page: int,
        filters: Optional[Dict] = None
    ) -> Optional[Dict]:
        """Get cached asset list."""
        filter_key = CacheKey.generate('filters', **(filters or {}))
        key = f'asset_list:{user_id}:{page}:{filter_key}'
        return await self.cache.get(key)
        
    async def invalidate_on_update(self, asset_id: str):
        """Invalidate caches when asset is updated."""
        await self.invalidator.invalidate_asset(asset_id)
        # Also invalidate list caches
        await self.cache.delete_pattern('asset_list:*')


class UserCache:
    """User-specific caching logic."""
    
    def __init__(self, cache: QueryCache):
        self.cache = cache
        self.invalidator = CacheInvalidation(cache)
        
    async def get_user_permissions(self, user_id: str) -> Optional[List[str]]:
        """Get cached user permissions."""
        return await self.cache.get(f'user_permissions:{user_id}')
        
    async def set_user_permissions(
        self,
        user_id: str,
        permissions: List[str],
        ttl: int = 3600
    ):
        """Cache user permissions."""
        await self.cache.set(
            f'user_permissions:{user_id}',
            permissions,
            ttl
        )
        
    async def check_permission_cached(
        self,
        user_id: str,
        permission: str,
        resource: Optional[str] = None
    ) -> Optional[bool]:
        """Check permission from cache."""
        key = f'permission_check:{user_id}:{permission}'
        if resource:
            key += f':{resource}'
        return await self.cache.get(key)


# Example usage
"""
# 1. Initialize cache
cache = QueryCache(
    redis_url="redis://localhost:6379/0",
    default_ttl=300,
    namespace='mams'
)

# 2. Use in service
class AssetService:
    def __init__(self, db, cache):
        self.db = db
        self.cache = AssetCache(cache)
        
    async def get_asset(self, asset_id: UUID):
        # Try cache first
        cached = await self.cache.get_asset(str(asset_id))
        if cached:
            return cached
            
        # Fetch from DB
        asset = await self.db.get(Asset, asset_id)
        
        # Cache it
        await self.cache.set_asset(str(asset_id), asset.dict())
        
        return asset

# 3. Use decorator
@cached('user_assets', ttl=600)
async def get_user_assets(user_id: UUID, page: int = 1):
    return await db.query(Asset).filter_by(owner_id=user_id).paginate(page)

# 4. Invalidation
async def update_asset(asset_id: UUID, data: dict):
    # Update in DB
    await db.update(Asset, asset_id, data)
    
    # Invalidate caches
    await cache.invalidator.invalidate_asset(str(asset_id))
"""