# Search Engine Optimization Guide

This guide covers the search indexing optimizations implemented in the MAMS Search Engine Service.

## Overview

The optimized search indexing system provides significant performance improvements for high-volume indexing and search operations through:

- **Parallel bulk indexing** with adaptive batching
- **Async OpenSearch client** with connection pooling
- **Query optimization** with caching and rewriting
- **Index health monitoring** and automatic optimization
- **Adaptive refresh intervals** based on workload

## Key Components

### 1. Optimized Indexer (`OptimizedIndexer`)

The optimized indexer provides high-performance bulk indexing with:

- **Queued indexing**: Documents are queued and processed in optimal batches
- **Parallel processing**: Multiple bulk operations run concurrently
- **Adaptive refresh**: Refresh intervals adjust based on indexing rate
- **Automatic retries**: Failed documents are retried with exponential backoff

#### Usage Example

```python
from src.core.optimized_indexer import OptimizedIndexer

# Initialize indexer
indexer = OptimizedIndexer(
    settings=settings,
    client=opensearch_client,
    batch_size=500,              # Documents per batch
    max_queue_size=10000,        # Maximum queue size
    parallel_bulk_processes=4    # Concurrent bulk operations
)

await indexer.initialize()

# Index documents
await indexer.index_documents([
    ("assets", "asset1", {"title": "Asset 1", "type": "video"}),
    ("assets", "asset2", {"title": "Asset 2", "type": "image"}),
    # ... more documents
])

# Get statistics
stats = indexer.get_stats()
print(f"Indexed: {stats['documents_indexed']}")
print(f"Failed: {stats['documents_failed']}")
print(f"Queue size: {stats['queue_size']}")
```

### 2. Async OpenSearch Client (`OptimizedAsyncOpenSearch`)

Provides async operations with connection pooling:

```python
from src.core.async_opensearch import get_opensearch_client

# Get optimized client
client = await get_opensearch_client(settings)

# Optimize for bulk indexing
await client.optimize_for_indexing()

# Perform parallel bulk indexing
result = await client.parallel_bulk_index(
    actions=documents,
    chunk_size=500,
    max_concurrent_chunks=4
)

# Restore normal settings
await client.restore_normal_settings()
```

### 3. Query Optimizer (`QueryOptimizer`)

Optimizes search queries for better performance:

```python
from src.core.query_optimizer import QueryOptimizer

optimizer = QueryOptimizer(client, redis_client)

# Optimize a query
optimized = await optimizer.optimize_query({
    "query": {
        "bool": {
            "must": [
                {"wildcard": {"title": "*video*"}},
                {"range": {"created_at": {"gte": "2024-01-01"}}}
            ]
        }
    }
})

# Execute with caching
result = await optimizer.execute_with_cache(
    index="assets",
    query=optimized
)

# Analyze slow queries
slow_queries = await optimizer.analyze_slow_queries(threshold_ms=1000)
```

### 4. Index Monitor (`IndexMonitor`)

Monitors and automatically optimizes index health:

```python
from src.core.index_monitor import IndexMonitor

monitor = IndexMonitor(client)
await monitor.start_monitoring()

# Get index health
health = await monitor.analyze_index_health("assets")
print(f"Status: {health.status}")
print(f"Issues: {health.issues}")
print(f"Recommendations: {health.recommendations}")

# Force optimization
await monitor.auto_optimize_index("assets", health)
```

## API Endpoints

### Bulk Indexing

```bash
# Bulk index documents
POST /api/v1/optimize/bulk
{
    "index": "assets",
    "documents": [
        {"id": "1", "title": "Asset 1"},
        {"id": "2", "title": "Asset 2"}
    ],
    "immediate": false
}

# Get indexing statistics
GET /api/v1/optimize/indexing/stats

# Flush indexing queue
POST /api/v1/optimize/indexing/flush
```

### Query Optimization

```bash
# Optimize a query
POST /api/v1/optimize/query/optimize
{
    "index": "assets",
    "query": {
        "query": {"match": {"title": "video"}}
    }
}

# Execute optimized query with caching
POST /api/v1/optimize/query/execute?use_cache=true
{
    "index": "assets",
    "query": {
        "query": {"match": {"title": "video"}}
    }
}

# Get slow query analysis
GET /api/v1/optimize/query/slow?threshold_ms=1000
```

### Index Monitoring

```bash
# Get all indices health
GET /api/v1/optimize/indices/health

# Get specific index health
GET /api/v1/optimize/indices/assets/health

# Optimize an index
POST /api/v1/optimize/indices/assets/optimize

# Force merge an index
POST /api/v1/optimize/indices/assets/force-merge?max_segments=1

# Get cluster health
GET /api/v1/optimize/cluster/health
```

### Settings Optimization

```bash
# Optimize cluster for indexing
POST /api/v1/optimize/settings/optimize
{
    "mode": "indexing"  # or "searching", "balanced"
}

# Create optimized index
POST /api/v1/optimize/indices/create-optimized?index_name=new_assets&estimated_size_gb=100&estimated_doc_count=1000000

# Reindex with optimization
POST /api/v1/optimize/reindex
{
    "source_index": "assets",
    "target_index": "assets_v2",
    "settings": {
        "number_of_shards": 5,
        "number_of_replicas": 1
    }
}
```

## Performance Tuning

### 1. Index Settings

For high-volume indexing:
```json
{
    "index": {
        "refresh_interval": "30s",
        "number_of_replicas": 0,
        "translog": {
            "durability": "async",
            "sync_interval": "30s"
        }
    }
}
```

For search performance:
```json
{
    "index": {
        "refresh_interval": "1s",
        "number_of_replicas": 1,
        "search": {
            "idle": {
                "after": "30s"
            }
        }
    }
}
```

### 2. Shard Sizing

Optimal shard count calculation:
- **By size**: 20-40GB per shard
- **By documents**: 20-50M documents per shard
- **Maximum**: 20 shards per index

### 3. Query Optimization Rules

The query optimizer applies these transformations:

1. **Wildcard optimization**: Converts wildcards to more efficient queries
   - `*term` → prefix query on reverse field
   - `term*` → match_phrase_prefix

2. **Bool query optimization**: Moves non-scoring queries to filter context
   - term, terms, range, exists → filter context

3. **Aggregation optimization**: Adds execution hints
   - Large cardinality → `execution_hint: map`
   - Small cardinality → `execution_hint: global_ordinals`

4. **Range query optimization**: Adds format hints for date fields

### 4. Monitoring Metrics

Key metrics to monitor:

- **Indexing rate**: Documents per second
- **Search rate**: Queries per second
- **Refresh time**: Should be < 1 second
- **Segment count**: < 50 per shard
- **Deleted docs ratio**: < 30%
- **JVM heap usage**: < 75%

## Best Practices

### 1. Bulk Indexing

- Use batches of 500-1000 documents
- Disable refresh during bulk operations
- Enable parallel indexing for large datasets
- Monitor queue size to prevent memory issues

### 2. Search Performance

- Use query caching for repeated queries
- Optimize queries before execution
- Monitor slow queries and optimize patterns
- Use appropriate field types in mappings

### 3. Index Maintenance

- Force merge old indices to reduce segments
- Monitor and fix yellow/red indices
- Shrink over-sharded indices
- Archive or delete old data

### 4. Cluster Health

- Monitor JVM heap usage
- Balance shards across nodes
- Use dedicated master nodes for large clusters
- Regular snapshots for backup

## Troubleshooting

### High Indexing Latency

1. Check refresh interval (increase for bulk operations)
2. Verify shard count (too many shards slow indexing)
3. Monitor thread pool rejections
4. Check disk I/O performance

### Slow Searches

1. Analyze query profile
2. Check cache hit rates
3. Optimize query structure
4. Add more replicas for read scaling

### Memory Issues

1. Reduce batch sizes
2. Decrease queue size limits
3. Force merge to reduce segments
4. Adjust JVM heap settings

### Index Health Issues

1. Check unassigned shards
2. Verify disk space
3. Review cluster allocation settings
4. Check node connectivity