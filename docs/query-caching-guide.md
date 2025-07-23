# Query Caching Implementation Guide for MAMS

## Overview

This guide provides comprehensive instructions for implementing query caching across MAMS services using Redis. Query caching significantly improves performance by reducing database load and response times.

## Architecture

### Cache Layers

```
┌─────────────────────────────────┐
│     API Request                 │
└────────────┬────────────────────┘
             │
┌────────────▼────────────────────┐
│     Service Layer               │
│  ┌──────────────────────────┐  │
│  │  Cache Check (Redis)     │  │
│  └────────┬─────────────────┘  │
│           │                     │
│  ┌────────▼─────────────────┐  │
│  │  Database Query          │  │
│  │  (on cache miss)         │  │
│  └──────────────────────────┘  │
└─────────────────────────────────┘
```

### Cache Infrastructure

- **Backend**: Redis 7.0+
- **Client**: redis-py with async support
- **Serialization**: JSON (default) or Pickle (for complex objects)
- **Key Structure**: `{namespace}:{version}:{service}:{resource}:{identifiers}`

## Implementation

### 1. Service Setup

#### Install Dependencies

```bash
pip install redis[hiredis] aioredis
```

#### Initialize Cache in Service

```python
# services/asset-management/src/main.py
from fastapi import FastAPI
from services.common.cache.cache_config import init_service_cache

app = FastAPI()

@app.on_event("startup")
async def startup():
    # Initialize cache
    app.state.cache = await init_service_cache('asset-management')
    
    # Warm up cache with popular items
    await warm_cache(app.state.cache)

@app.on_event("shutdown")
async def shutdown():
    # Close cache connections
    if hasattr(app.state, 'cache'):
        await app.state.cache.disconnect()
```

### 2. Basic Caching Pattern

```python
from services.common.cache.query_cache import QueryCache, CacheKey

class AssetService:
    def __init__(self, db: AsyncSession, cache: QueryCache):
        self.db = db
        self.cache = cache
        
    async def get_asset(self, asset_id: UUID) -> Optional[Asset]:
        # Build cache key
        cache_key = CacheKey.generate('asset', str(asset_id))
        
        # Check cache
        cached = await self.cache.get(cache_key)
        if cached:
            return Asset(**cached)
            
        # Query database
        asset = await self.db.get(Asset, asset_id)
        if asset:
            # Cache the result
            await self.cache.set(
                cache_key,
                asset.dict(),
                ttl=600  # 10 minutes
            )
            
        return asset
```

### 3. Using the @cached Decorator

```python
from services.common.cache.query_cache import cached
from services.common.cache.cache_config import ServiceCacheConfig

class UserService:
    @cached('user_permissions', ttl=3600)
    async def get_user_permissions(self, user_id: UUID) -> List[str]:
        # This query result will be automatically cached
        return await self.db.query(Permission).filter_by(user_id=user_id).all()
    
    @cached('user_profile', ttl=ServiceCacheConfig.USER_CACHE['user_profile'])
    async def get_user_profile(self, user_id: UUID) -> UserProfile:
        return await self.db.get(UserProfile, user_id)
```

### 4. Cache Invalidation

```python
class AssetService:
    async def update_asset(self, asset_id: UUID, data: dict) -> Asset:
        # Update in database
        asset = await self.db.update(Asset, asset_id, data)
        
        # Invalidate cache entries
        await self.invalidate_asset_cache(asset_id)
        
        return asset
        
    async def invalidate_asset_cache(self, asset_id: UUID):
        """Invalidate all cache entries for an asset."""
        patterns = [
            f'asset:{asset_id}',
            f'asset:{asset_id}:*',
            f'asset_list:*',  # Lists might contain this asset
            f'search:*',      # Search results might be affected
        ]
        
        for pattern in patterns:
            await self.cache.delete_pattern(pattern)
```

### 5. Batch Operations

```python
# Cache multiple items at once
async def cache_assets_batch(assets: List[Asset]):
    items = {
        f'asset:{asset.id}': asset.dict()
        for asset in assets
    }
    await cache.multi_set(items, ttl=600)

# Get multiple items at once
async def get_assets_batch(asset_ids: List[UUID]) -> List[Asset]:
    keys = [f'asset:{id}' for id in asset_ids]
    cached_items = await cache.multi_get(keys)
    
    # Find missing items
    missing_ids = [
        asset_ids[i] for i, key in enumerate(keys)
        if key not in cached_items
    ]
    
    # Fetch missing from database
    if missing_ids:
        missing_assets = await db.query(Asset).filter(
            Asset.id.in_(missing_ids)
        ).all()
        
        # Cache them
        await cache_assets_batch(missing_assets)
    
    return assets
```

## Service-Specific Implementations

### Asset Management Service

```python
# Cached asset service implementation
from services.asset_management.src.services.cached_asset_service import CachedAssetService

# In your FastAPI routes
@router.get("/assets/{asset_id}")
async def get_asset(
    asset_id: UUID,
    db: AsyncSession = Depends(get_db),
    cache: QueryCache = Depends(get_cache),
    current_user: User = Depends(get_current_user)
):
    service = CachedAssetService(db, cache)
    asset = await service.get_asset(
        asset_id,
        include_metadata=True,
        user_id=current_user.id
    )
    if not asset:
        raise HTTPException(404, "Asset not found")
    return asset
```

### User Management Service

```python
from services.common.cache.query_cache import UserCache

class CachedUserService:
    def __init__(self, db: AsyncSession, cache: QueryCache):
        self.db = db
        self.user_cache = UserCache(cache)
        
    async def check_permission(
        self,
        user_id: UUID,
        permission: str,
        resource: Optional[str] = None
    ) -> bool:
        # Check cache first
        cached_result = await self.user_cache.check_permission_cached(
            str(user_id), permission, resource
        )
        if cached_result is not None:
            return cached_result
            
        # Query database
        has_permission = await self._check_permission_db(
            user_id, permission, resource
        )
        
        # Cache result
        cache_key = f'permission_check:{user_id}:{permission}'
        if resource:
            cache_key += f':{resource}'
        await self.user_cache.cache.set(
            cache_key,
            has_permission,
            ttl=3600  # 1 hour
        )
        
        return has_permission
```

### Search Service

```python
class CachedSearchService:
    @cached('search_results', ttl=60)  # Short TTL for search
    async def search(
        self,
        query: str,
        filters: Optional[Dict] = None,
        page: int = 1,
        limit: int = 20
    ) -> SearchResults:
        # Complex search query that benefits from caching
        return await self._execute_search(query, filters, page, limit)
    
    @cached('search_suggestions', ttl=300)
    async def get_suggestions(self, prefix: str) -> List[str]:
        # Autocomplete suggestions
        return await self._generate_suggestions(prefix)
```

## Configuration

### Redis Configuration

```yaml
# docker-compose.yml
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: >
      redis-server
      --appendonly yes
      --maxmemory 2gb
      --maxmemory-policy allkeys-lru
      --save 60 1000
      --save 300 10
      --save 900 1
```

### Environment Variables

```env
# Cache configuration
MAMS_CACHE_REDIS_URL=redis://localhost:6379/0
MAMS_CACHE_REDIS_PASSWORD=your-redis-password
MAMS_CACHE_REDIS_SSL=false
MAMS_CACHE_ENABLED=true
MAMS_CACHE_DEFAULT_TTL=300
MAMS_CACHE_PREFIX=mams
MAMS_CACHE_MAX_CONNECTIONS=50
```

### TTL Configuration

Use appropriate TTL values from `ServiceCacheConfig`:

```python
from services.common.cache.cache_config import ServiceCacheConfig

# Asset cache TTLs
asset_ttl = ServiceCacheConfig.ASSET_CACHE['asset_details']  # 600s
list_ttl = ServiceCacheConfig.ASSET_CACHE['asset_list']      # 120s

# User cache TTLs
permission_ttl = ServiceCacheConfig.USER_CACHE['user_permissions']  # 3600s
profile_ttl = ServiceCacheConfig.USER_CACHE['user_profile']        # 900s
```

## Monitoring

### Cache Metrics

```python
from services.common.cache.cache_config import CacheMetrics

# Initialize metrics
metrics = CacheMetrics()

# In your cache logic
async def get_with_metrics(key: str):
    value = await cache.get(key)
    if value:
        metrics.record_hit()
    else:
        metrics.record_miss()
    return value

# Get statistics
stats = metrics.get_stats()
logger.info(f"Cache performance: {stats}")
```

### Redis Monitoring

```bash
# Monitor cache usage
redis-cli INFO stats

# Monitor cache keys
redis-cli --scan --pattern "mams:*" | head -20

# Check memory usage
redis-cli INFO memory

# Monitor commands in real-time
redis-cli MONITOR
```

### Grafana Dashboard

Create Prometheus metrics for cache monitoring:

```python
from prometheus_client import Counter, Histogram, Gauge

# Define metrics
cache_hits = Counter('mams_cache_hits_total', 'Total cache hits', ['service', 'operation'])
cache_misses = Counter('mams_cache_misses_total', 'Total cache misses', ['service', 'operation'])
cache_latency = Histogram('mams_cache_latency_seconds', 'Cache operation latency', ['operation'])
cache_size = Gauge('mams_cache_size_bytes', 'Current cache size')

# Use in cache operations
with cache_latency.labels(operation='get').time():
    value = await cache.get(key)
    
if value:
    cache_hits.labels(service='asset', operation='get').inc()
else:
    cache_misses.labels(service='asset', operation='get').inc()
```

## Best Practices

### 1. Cache Key Design

```python
# Good: Hierarchical, predictable keys
"mams:v1:asset:details:123e4567-e89b-12d3-a456-426614174000"
"mams:v1:user:permissions:123:asset.create"

# Bad: Flat, unpredictable keys
"asset_123e4567-e89b-12d3-a456-426614174000"
"user123permissions"
```

### 2. TTL Strategy

- **Short TTL (1-5 min)**: Search results, active sessions
- **Medium TTL (5-30 min)**: Asset lists, user profiles
- **Long TTL (1-24 hours)**: Permissions, system config
- **Very Long TTL (days)**: Thumbnails, transcoded media

### 3. Cache Warming

```python
# Warm cache on startup
async def warm_cache(cache: QueryCache):
    # Get frequently accessed items
    popular_assets = await get_popular_assets(limit=100)
    active_users = await get_active_users(limit=50)
    
    # Pre-load into cache
    for asset in popular_assets:
        await cache.set(f'asset:{asset.id}', asset.dict(), ttl=3600)
        
    for user in active_users:
        permissions = await get_user_permissions(user.id)
        await cache.set(f'user_permissions:{user.id}', permissions, ttl=3600)
```

### 4. Invalidation Patterns

```python
# Invalidate related caches together
async def invalidate_user_caches(user_id: UUID):
    patterns = [
        f'user:{user_id}:*',
        f'user_permissions:{user_id}',
        f'user_profile:{user_id}',
        f'user_assets:{user_id}:*',
    ]
    
    for pattern in patterns:
        await cache.delete_pattern(pattern)
```

### 5. Error Handling

```python
# Graceful degradation
async def get_asset_safe(asset_id: UUID) -> Optional[Asset]:
    try:
        # Try cache
        cached = await cache.get(f'asset:{asset_id}')
        if cached:
            return Asset(**cached)
    except Exception as e:
        logger.error(f"Cache error: {e}")
        # Continue without cache
        
    # Fallback to database
    return await db.get(Asset, asset_id)
```

## Troubleshooting

### Common Issues

1. **High Memory Usage**
   ```bash
   # Check Redis memory
   redis-cli INFO memory | grep used_memory_human
   
   # Set memory limit
   redis-cli CONFIG SET maxmemory 2gb
   redis-cli CONFIG SET maxmemory-policy allkeys-lru
   ```

2. **Connection Pool Exhaustion**
   ```python
   # Increase pool size
   cache = QueryCache(
       redis_url=REDIS_URL,
       max_connections=100  # Increase from default 50
   )
   ```

3. **Stale Data**
   ```python
   # Force refresh
   asset = await service.get_asset(
       asset_id,
       force_refresh=True  # Bypass cache
   )
   ```

4. **Serialization Errors**
   ```python
   # Use custom serializer for complex objects
   await cache.set(
       key,
       value,
       serializer=lambda x: pickle.dumps(x)
   )
   ```

## Performance Impact

### Expected Improvements

- **Response Time**: 50-80% reduction for cached queries
- **Database Load**: 60-90% reduction in query volume
- **Throughput**: 3-5x increase in requests/second
- **Latency**: <5ms for cache hits vs 50-200ms for database queries

### Measurement

```python
import time

# Measure cache performance
async def measure_performance():
    # Without cache
    start = time.time()
    asset = await db.get(Asset, asset_id)
    db_time = time.time() - start
    
    # With cache (hit)
    start = time.time()
    asset = await cache.get(f'asset:{asset_id}')
    cache_time = time.time() - start
    
    print(f"Database: {db_time*1000:.2f}ms")
    print(f"Cache: {cache_time*1000:.2f}ms")
    print(f"Speedup: {db_time/cache_time:.1f}x")
```

## Next Steps

1. **Implement distributed caching** with Redis Cluster
2. **Add cache preloading** for predictive caching
3. **Implement cache synchronization** across services
4. **Add cache analytics** dashboard
5. **Optimize serialization** with MessagePack or Protocol Buffers