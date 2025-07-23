"""
Cache configuration and setup for MAMS services.

This module provides cache configuration and initialization
for different services with appropriate TTL values.
"""

from typing import Dict, Optional
from enum import Enum
from pydantic import BaseSettings
import logging

logger = logging.getLogger(__name__)


class CacheTTL(Enum):
    """Standard TTL values for different cache types."""
    
    # Short-lived caches (1-5 minutes)
    SEARCH_RESULTS = 60  # 1 minute - search results change frequently
    ASSET_LIST = 120  # 2 minutes - asset lists
    ACTIVE_SESSIONS = 300  # 5 minutes - active user sessions
    
    # Medium-lived caches (5-30 minutes)
    ASSET_DETAILS = 600  # 10 minutes - individual asset data
    USER_PROFILE = 900  # 15 minutes - user profiles
    PROJECT_DATA = 1200  # 20 minutes - project information
    METADATA_SCHEMA = 1800  # 30 minutes - metadata schemas
    
    # Long-lived caches (30 minutes - 24 hours)
    USER_PERMISSIONS = 3600  # 1 hour - permissions don't change often
    SYSTEM_CONFIG = 7200  # 2 hours - system configuration
    STATISTICS = 14400  # 4 hours - analytics and statistics
    STATIC_CONTENT = 86400  # 24 hours - rarely changing content
    
    # Special cases
    THUMBNAIL = 604800  # 7 days - thumbnails rarely change
    TRANSCODED_MEDIA = 2592000  # 30 days - transcoded files


class CacheConfig(BaseSettings):
    """Cache configuration settings."""
    
    # Redis connection
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_PASSWORD: Optional[str] = None
    REDIS_SSL: bool = False
    REDIS_MAX_CONNECTIONS: int = 50
    
    # Cache behavior
    CACHE_ENABLED: bool = True
    CACHE_PREFIX: str = "mams"
    CACHE_DEFAULT_TTL: int = 300
    
    # Cache key patterns
    CACHE_KEY_SEPARATOR: str = ":"
    CACHE_VERSION: str = "v1"
    
    # Performance tuning
    CACHE_COMPRESSION_THRESHOLD: int = 1024  # Compress values > 1KB
    CACHE_MAX_KEY_LENGTH: int = 250
    CACHE_POOL_MIN_SIZE: int = 10
    
    class Config:
        env_prefix = "MAMS_CACHE_"


class ServiceCacheConfig:
    """Service-specific cache configurations."""
    
    # Asset Management Service
    ASSET_CACHE = {
        'asset_details': CacheTTL.ASSET_DETAILS.value,
        'asset_list': CacheTTL.ASSET_LIST.value,
        'asset_metadata': CacheTTL.ASSET_DETAILS.value,
        'asset_versions': CacheTTL.ASSET_DETAILS.value,
        'asset_tags': CacheTTL.ASSET_DETAILS.value,
        'asset_search': CacheTTL.SEARCH_RESULTS.value,
        'duplicate_check': CacheTTL.ASSET_LIST.value,
    }
    
    # User Management Service
    USER_CACHE = {
        'user_profile': CacheTTL.USER_PROFILE.value,
        'user_permissions': CacheTTL.USER_PERMISSIONS.value,
        'user_roles': CacheTTL.USER_PERMISSIONS.value,
        'user_groups': CacheTTL.USER_PERMISSIONS.value,
        'permission_check': CacheTTL.USER_PERMISSIONS.value,
        'active_sessions': CacheTTL.ACTIVE_SESSIONS.value,
    }
    
    # Search Service
    SEARCH_CACHE = {
        'search_results': CacheTTL.SEARCH_RESULTS.value,
        'search_suggestions': CacheTTL.SEARCH_RESULTS.value,
        'search_facets': CacheTTL.ASSET_LIST.value,
        'saved_searches': CacheTTL.PROJECT_DATA.value,
        'search_history': CacheTTL.USER_PROFILE.value,
    }
    
    # Project Service
    PROJECT_CACHE = {
        'project_details': CacheTTL.PROJECT_DATA.value,
        'project_hierarchy': CacheTTL.PROJECT_DATA.value,
        'project_assets': CacheTTL.ASSET_LIST.value,
        'project_members': CacheTTL.PROJECT_DATA.value,
        'shotlist': CacheTTL.PROJECT_DATA.value,
        'timeline': CacheTTL.PROJECT_DATA.value,
    }
    
    # Metadata Service
    METADATA_CACHE = {
        'metadata_schema': CacheTTL.METADATA_SCHEMA.value,
        'metadata_values': CacheTTL.ASSET_DETAILS.value,
        'metadata_templates': CacheTTL.METADATA_SCHEMA.value,
        'field_definitions': CacheTTL.METADATA_SCHEMA.value,
    }
    
    # Media Processing
    MEDIA_CACHE = {
        'thumbnails': CacheTTL.THUMBNAIL.value,
        'proxies': CacheTTL.TRANSCODED_MEDIA.value,
        'waveforms': CacheTTL.THUMBNAIL.value,
        'transcoded': CacheTTL.TRANSCODED_MEDIA.value,
        'processing_status': CacheTTL.ACTIVE_SESSIONS.value,
    }
    
    # System
    SYSTEM_CACHE = {
        'config': CacheTTL.SYSTEM_CONFIG.value,
        'statistics': CacheTTL.STATISTICS.value,
        'health_check': 30,  # 30 seconds
        'service_status': 60,  # 1 minute
    }


class CacheKeyBuilder:
    """Utility for building consistent cache keys."""
    
    def __init__(self, config: CacheConfig):
        self.config = config
        self.separator = config.CACHE_KEY_SEPARATOR
        self.prefix = config.CACHE_PREFIX
        self.version = config.CACHE_VERSION
        
    def build(self, service: str, resource: str, *identifiers, **params) -> str:
        """
        Build a cache key.
        
        Args:
            service: Service name (e.g., 'asset', 'user')
            resource: Resource type (e.g., 'details', 'list')
            *identifiers: Resource identifiers
            **params: Additional parameters
            
        Returns:
            Cache key string
        """
        parts = [self.prefix, self.version, service, resource]
        
        # Add identifiers
        parts.extend(str(id) for id in identifiers)
        
        # Add sorted parameters
        if params:
            param_str = ','.join(f"{k}={v}" for k, v in sorted(params.items()))
            parts.append(param_str)
            
        key = self.separator.join(parts)
        
        # Ensure key length is within limits
        if len(key) > self.config.CACHE_MAX_KEY_LENGTH:
            # Hash the key if too long
            import hashlib
            hash_suffix = hashlib.md5(key.encode()).hexdigest()[:8]
            key = key[:self.config.CACHE_MAX_KEY_LENGTH - 9] + f"_{hash_suffix}"
            
        return key
        
    def build_pattern(self, service: str, resource: str, *partial_ids) -> str:
        """Build a pattern for cache invalidation."""
        parts = [self.prefix, self.version, service, resource]
        parts.extend(str(id) for id in partial_ids)
        parts.append('*')
        return self.separator.join(parts)


class CacheMetrics:
    """Track cache performance metrics."""
    
    def __init__(self):
        self.hits = 0
        self.misses = 0
        self.errors = 0
        self.evictions = 0
        
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0
        
    def record_hit(self):
        """Record a cache hit."""
        self.hits += 1
        
    def record_miss(self):
        """Record a cache miss."""
        self.misses += 1
        
    def record_error(self):
        """Record a cache error."""
        self.errors += 1
        
    def record_eviction(self):
        """Record a cache eviction."""
        self.evictions += 1
        
    def get_stats(self) -> Dict:
        """Get cache statistics."""
        return {
            'hits': self.hits,
            'misses': self.misses,
            'errors': self.errors,
            'evictions': self.evictions,
            'hit_rate': f"{self.hit_rate * 100:.2f}%",
            'total_requests': self.hits + self.misses
        }


# Cache initialization helpers
async def init_service_cache(
    service_name: str,
    config: Optional[CacheConfig] = None
) -> 'QueryCache':
    """
    Initialize cache for a specific service.
    
    Args:
        service_name: Name of the service
        config: Optional cache configuration
        
    Returns:
        Initialized QueryCache instance
    """
    from .query_cache import QueryCache
    
    if config is None:
        config = CacheConfig()
        
    # Build Redis URL with password if provided
    redis_url = config.REDIS_URL
    if config.REDIS_PASSWORD:
        # Parse and add password
        from urllib.parse import urlparse, urlunparse
        parsed = urlparse(redis_url)
        netloc = f":{config.REDIS_PASSWORD}@{parsed.hostname}"
        if parsed.port:
            netloc += f":{parsed.port}"
        redis_url = urlunparse((
            parsed.scheme,
            netloc,
            parsed.path,
            parsed.params,
            parsed.query,
            parsed.fragment
        ))
        
    cache = QueryCache(
        redis_url=redis_url,
        default_ttl=config.CACHE_DEFAULT_TTL,
        max_connections=config.REDIS_MAX_CONNECTIONS,
        namespace=f"{config.CACHE_PREFIX}:{service_name}"
    )
    
    await cache.connect()
    
    logger.info(f"Initialized cache for service: {service_name}")
    
    return cache


# Warming strategies
class CacheWarmer:
    """Strategies for warming up caches."""
    
    def __init__(self, cache: 'QueryCache', db):
        self.cache = cache
        self.db = db
        
    async def warm_user_permissions(self, user_ids: list):
        """Pre-load user permissions into cache."""
        from .query_cache import UserCache
        user_cache = UserCache(self.cache)
        
        for user_id in user_ids:
            # Fetch permissions from DB
            permissions = await self._fetch_user_permissions(user_id)
            
            # Cache them
            await user_cache.set_user_permissions(
                str(user_id),
                permissions,
                ttl=CacheTTL.USER_PERMISSIONS.value
            )
            
    async def warm_popular_assets(self, limit: int = 100):
        """Pre-load popular assets into cache."""
        from .query_cache import AssetCache
        asset_cache = AssetCache(self.cache)
        
        # Get most accessed assets
        popular_assets = await self._fetch_popular_assets(limit)
        
        for asset in popular_assets:
            await asset_cache.set_asset(
                str(asset['id']),
                asset,
                ttl=CacheTTL.ASSET_DETAILS.value
            )
            
    async def _fetch_user_permissions(self, user_id):
        """Fetch user permissions from database."""
        # Implementation depends on your DB structure
        pass
        
    async def _fetch_popular_assets(self, limit):
        """Fetch popular assets from database."""
        # Implementation depends on your DB structure
        pass


# Example usage
"""
# 1. Initialize cache for a service
from services.common.cache.cache_config import init_service_cache, ServiceCacheConfig

cache = await init_service_cache('asset-management')

# 2. Use service-specific TTL values
from services.common.cache.cache_config import ServiceCacheConfig

ttl = ServiceCacheConfig.ASSET_CACHE['asset_details']  # 600 seconds

# 3. Build cache keys consistently
from services.common.cache.cache_config import CacheKeyBuilder, CacheConfig

config = CacheConfig()
key_builder = CacheKeyBuilder(config)

# Build key: "mams:v1:asset:details:123"
cache_key = key_builder.build('asset', 'details', asset_id)

# Build pattern: "mams:v1:asset:list:user123:*"
pattern = key_builder.build_pattern('asset', 'list', user_id)

# 4. Track cache metrics
from services.common.cache.cache_config import CacheMetrics

metrics = CacheMetrics()

# In your cache logic
if cached_value:
    metrics.record_hit()
else:
    metrics.record_miss()
    
# Get statistics
stats = metrics.get_stats()
print(f"Cache hit rate: {stats['hit_rate']}")

# 5. Warm up caches
warmer = CacheWarmer(cache, db)
await warmer.warm_user_permissions(['user1', 'user2'])
await warmer.warm_popular_assets(100)
"""