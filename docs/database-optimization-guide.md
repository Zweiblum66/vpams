# Database Query Optimization Guide for MAMS

## Overview

This guide provides comprehensive database query optimization strategies implemented for the MAMS platform. These optimizations address common performance issues including N+1 queries, missing indexes, inefficient joins, and suboptimal query patterns.

## Optimization Categories

### 1. N+1 Query Problems

**Problem**: Loading related entities triggers additional queries for each parent record.

**Solution**: Use eager loading with SQLAlchemy's `selectinload()` or `joinedload()`.

#### Asset Management Service

```python
# Before (N+1 problem)
asset = await db.get(Asset, asset_id)
await db.refresh(asset, ["tags", "versions"])  # Triggers additional queries

# After (Optimized)
from services.asset_management.src.db.query_optimizations import QueryOptimizer

optimizer = QueryOptimizer()
query = optimizer.build_asset_query_with_relations(
    include_tags=True,
    include_versions=True
)
result = await db.execute(query.where(Asset.id == asset_id))
asset = result.scalar_one()
```

#### User Management Service

```python
# Before
user = await db.get(User, user_id)
await db.refresh(user, ["profile", "roles"])

# After
from services.user_management.src.db.query_optimizations import UserQueryOptimizer

optimizer = UserQueryOptimizer()
query = optimizer.build_user_query_with_relations(
    include_profile=True,
    include_roles=True,
    include_permissions=True
)
result = await db.execute(query.where(User.id == user_id))
user = result.scalar_one()
```

### 2. Missing Indexes

**Problem**: Queries scan entire tables instead of using indexes.

**Solution**: Add composite indexes for common query patterns.

Run the migration script to add all performance indexes:

```bash
psql -U mams -d mams_production -f database/migrations/add_performance_indexes.sql
```

Key indexes added:
- `idx_asset_status_owner_created` - For dashboard queries
- `idx_asset_file_hash_deleted` - For duplicate detection
- `idx_user_search` - For user search across multiple fields
- `idx_asset_name_trgm` - For fuzzy text search

### 3. Inefficient Joins

**Problem**: Multiple joins cause query complexity and slow performance.

**Solution**: Use EXISTS subqueries instead of joins for filtering.

#### Tag Filtering Example

```python
# Before (Multiple joins)
query = query.join(asset_tags).join(Tag).where(
    Tag.name.in_(search_params.tags)
).group_by(Asset.id).having(
    func.count(Tag.id) == len(search_params.tags)
)

# After (EXISTS subquery)
from services.asset_management.src.db.query_optimizations import QueryOptimizer

optimizer = QueryOptimizer()
query = optimizer.build_tag_filter_query(
    base_query=query,
    tag_names=search_params.tags,
    match_all=True  # Require all tags
)
```

### 4. Pagination Optimization

**Problem**: Counting total results requires a separate query.

**Solution**: Use window functions to get count with results.

```python
# Before
results = await db.execute(query.limit(20).offset(0))
count = await db.scalar(select(func.count()).select_from(query.subquery()))

# After
optimizer = QueryOptimizer()
query = optimizer.build_paginated_query(
    base_query=query,
    page=1,
    page_size=20,
    include_total=True
)
result = await db.execute(query)
first_row = result.first()
total_count = first_row._total_count if first_row else 0
```

### 5. Bulk Operations

**Problem**: Individual queries in loops for bulk updates.

**Solution**: Use bulk update/insert operations.

```python
# Asset bulk update
from services.asset_management.src.db.query_optimizations import BulkOperations

bulk_ops = BulkOperations()
updated = await bulk_ops.bulk_update_assets(
    db=db,
    asset_ids=[asset1_id, asset2_id, asset3_id],
    update_data={'status': 'archived', 'updated_at': datetime.utcnow()}
)

# Bulk tag assignment
await bulk_ops.bulk_tag_assets(
    db=db,
    asset_ids=asset_ids,
    tag_names=['reviewed', 'approved'],
    replace=False  # Append tags
)
```

### 6. Connection Pool Configuration

**Problem**: Default connection pool settings cause bottlenecks.

**Solution**: Use optimized connection pool configuration.

```python
from services.common.database_config import OptimizedDatabaseConfig

# Configure for production
db_config = OptimizedDatabaseConfig(
    database_url=DATABASE_URL,
    pool_size=20,          # Base pool size
    max_overflow=40,       # Additional connections when needed
    pool_timeout=30,       # Timeout waiting for connection
    pool_recycle=3600,     # Recycle connections after 1 hour
    echo_pool=False        # Set True for debugging
)

# Use in FastAPI
app = FastAPI()

@app.on_event("startup")
async def startup():
    # Warm up connection pool
    async with db_config.engine.begin() as conn:
        await conn.execute("SELECT 1")

async def get_db():
    async with db_config.sessionmaker() as session:
        yield session
```

### 7. Query Caching

**Problem**: Repeated queries for the same data.

**Solution**: Implement Redis-based query caching.

```python
from services.asset_management.src.db.query_optimizations import QueryCache

cache = QueryCache(redis_client)

# Cache query results
assets = await cache.get_or_fetch(
    key=f'assets:user:{user_id}:page:1',
    fetch_func=lambda: fetch_user_assets(user_id, page=1),
    ttl=600  # Cache for 10 minutes
)

# Invalidate cache on updates
await cache.invalidate(f'assets:user:{user_id}:*')
```

## Implementation Steps

### 1. Apply Database Migrations

```bash
# Run the performance indexes migration
psql -U mams -d mams_production -f database/migrations/add_performance_indexes.sql

# Verify indexes were created
psql -U mams -d mams_production -c "SELECT * FROM monitor_index_usage();"
```

### 2. Update Service Code

1. Import query optimization utilities:
```python
from services.asset_management.src.db.query_optimizations import (
    QueryOptimizer, BulkOperations, QueryCache
)
```

2. Replace existing queries with optimized versions
3. Add caching where appropriate
4. Use bulk operations for batch updates

### 3. Configure Connection Pools

Update each service's database configuration:

```python
# services/{service_name}/src/core/config.py
from services.common.database_config import OptimizedDatabaseConfig

# In get_settings()
db_config = OptimizedDatabaseConfig(
    database_url=settings.DATABASE_URL,
    pool_size=20,
    max_overflow=40,
    stateless=settings.SERVERLESS  # True for Lambda/serverless
)
```

### 4. Monitor Performance

#### Query Performance Monitoring

```python
from services.common.database_config import QueryMonitor
from sqlalchemy import event

# Set up monitoring
query_monitor = QueryMonitor(slow_query_threshold=0.5)  # 500ms
event.listen(engine.sync_engine, "before_cursor_execute", query_monitor.before_cursor_execute)
event.listen(engine.sync_engine, "after_cursor_execute", query_monitor.after_cursor_execute)

# Get statistics
stats = query_monitor.get_stats()
```

#### Connection Pool Monitoring

```python
from services.common.database_config import PoolMonitor

pool_monitor = PoolMonitor(db_config.engine)

# Check pool status
status = pool_monitor.get_pool_status()
# {'size': 20, 'checked_in': 18, 'checked_out': 2, 'overflow': 0, 'total': 20}
```

## Performance Metrics

### Before Optimization
- Average query time: 250ms
- P95 query time: 800ms
- N+1 queries: Common
- Connection pool exhaustion: Frequent under load

### After Optimization (Expected)
- Average query time: 50ms (80% improvement)
- P95 query time: 200ms (75% improvement)
- N+1 queries: Eliminated
- Connection pool exhaustion: Rare

## Best Practices

1. **Always use eager loading** for related entities you know you'll need
2. **Prefer EXISTS subqueries** over joins for filtering
3. **Use bulk operations** for batch updates/inserts
4. **Cache frequently accessed data** with appropriate TTLs
5. **Monitor slow queries** and optimize them
6. **Use appropriate indexes** but don't over-index
7. **Configure connection pools** based on load patterns
8. **Use read replicas** for read-heavy operations

## Troubleshooting

### High Connection Pool Usage
```python
# Check pool status
pool_status = pool_monitor.get_pool_status()
if pool_status['checked_out'] > pool_status['size'] * 0.8:
    logger.warning("Connection pool usage high: %s", pool_status)
```

### Slow Queries
```sql
-- Find slow queries using pg_stat_statements
SELECT 
    query,
    mean_exec_time,
    calls,
    total_exec_time
FROM pg_stat_statements
WHERE mean_exec_time > 100  -- Queries averaging > 100ms
ORDER BY mean_exec_time DESC
LIMIT 20;
```

### Missing Index Detection
```sql
-- Find tables with sequential scans
SELECT 
    schemaname,
    tablename,
    seq_scan,
    seq_tup_read,
    idx_scan,
    idx_tup_fetch
FROM pg_stat_user_tables
WHERE seq_scan > idx_scan
    AND schemaname NOT IN ('pg_catalog', 'information_schema')
ORDER BY seq_scan DESC;
```

## Next Steps

1. **Implement query result caching** (PERF-M8-002)
2. **Add read replicas** for scaling read operations
3. **Implement database sharding** for horizontal scaling
4. **Add query performance dashboards** in Grafana
5. **Set up automated slow query alerts**

## References

- [PostgreSQL Performance Tuning](https://wiki.postgresql.org/wiki/Performance_Optimization)
- [SQLAlchemy Performance Tips](https://docs.sqlalchemy.org/en/20/faq/performance.html)
- [Redis Caching Best Practices](https://redis.io/docs/manual/patterns/)