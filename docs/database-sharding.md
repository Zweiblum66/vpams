# Database Sharding Guide - MAMS

## Overview

Database sharding is a horizontal scaling technique that distributes data across multiple database instances (shards) to improve performance, scalability, and availability. MAMS implements a flexible sharding architecture that supports multiple strategies and can be configured based on your specific needs.

## Architecture

### Components

1. **Shard Router**: Determines which shard should handle a specific request based on the sharding strategy and key
2. **Sharded Session**: Manages database connections across multiple shards
3. **Sharded Repository**: Provides data access patterns for sharded entities
4. **Shard Manager**: Handles shard configuration, health monitoring, and rebalancing

### Sharding Strategies

#### 1. Hash-Based Sharding (Default)
- Distributes data evenly across shards using consistent hashing
- Best for: General use cases with uniform data access patterns
- Example: Hash the project_id to determine shard placement

#### 2. Range-Based Sharding
- Distributes data based on value ranges (e.g., alphabetical, numerical)
- Best for: Data with natural ordering or when you need predictable placement
- Example: A-M on shard1, N-Z on shard2

#### 3. Geography-Based Sharding
- Distributes data based on geographic regions
- Best for: Multi-region deployments with data locality requirements
- Example: US data on US shards, EU data on EU shards

### Shard Keys

The shard key determines how data is distributed:

- **PROJECT_ID** (Default): Groups all assets from the same project together
- **OWNER_ID**: Groups all assets from the same user together
- **ASSET_ID**: Distributes individual assets across shards
- **CREATED_AT**: Distributes based on creation time

## Configuration

### Environment Variables

```bash
# Enable sharding
SHARDING_ENABLED=true

# Sharding strategy
SHARDING_STRATEGY=hash  # hash, range, geography

# Shard key
SHARDING_KEY=project_id  # project_id, owner_id, asset_id, created_at

# Number of shards
SHARD_COUNT=3

# Individual shard configuration
SHARD_0_ID=shard1
SHARD_0_URL=postgresql+asyncpg://user:pass@host1:5432/mams_shard1
SHARD_0_WEIGHT=1.0
SHARD_0_REGIONS=us-east,us-west

SHARD_1_ID=shard2
SHARD_1_URL=postgresql+asyncpg://user:pass@host2:5432/mams_shard2
SHARD_1_WEIGHT=1.0
SHARD_1_REGIONS=eu-west,eu-central

# Read replica example
SHARD_2_ID=shard1_read
SHARD_2_URL=postgresql+asyncpg://user:pass@host1-read:5432/mams_shard1
SHARD_2_READ_ONLY=true
SHARD_2_WEIGHT=0.0
```

### Sharding Policies

```bash
# Automatic rebalancing
SHARDING_AUTO_REBALANCE=false
SHARDING_REBALANCE_THRESHOLD=0.2  # 20% imbalance triggers rebalancing

# Migration settings
SHARDING_MIGRATION_BATCH_SIZE=100
SHARDING_MIGRATION_DELAY_MS=100

# Query settings
SHARDING_CROSS_SHARD_QUERIES=true
SHARDING_CACHE_MAPPINGS=true
SHARDING_MAPPING_CACHE_TTL=3600

# Read replica settings
SHARDING_READ_PREFERENCE=secondary_preferred  # primary, primary_preferred, secondary, secondary_preferred, nearest
SHARDING_LOAD_BALANCING_STRATEGY=round_robin  # round_robin, random, least_connections, response_time, weighted
SHARDING_MAX_REPLICA_LAG_SECONDS=300  # 5 minutes
SHARDING_HEALTH_CHECK_INTERVAL_SECONDS=30
```

## Setup Guide

### 1. Prerequisites

- PostgreSQL 15+ installed
- Python 3.11+ environment
- MAMS asset-management service

### 2. Initialize Shards

```bash
# Set up environment
export SHARDING_ENABLED=true
export SHARD_COUNT=3

# Initialize shard databases
cd services/asset-management
python scripts/manage_shards.py init-shards

# Output:
# Initializing 3 shards...
# 
# Processing shard: shard1
#   Creating database mams_assets_shard1
#   Running migrations on mams_assets_shard1
#   ✓ Shard shard1 initialized successfully
# ...
```

### 3. Verify Shard Health

```bash
python scripts/manage_shards.py check-health

# Output:
# Checking shard health...
# 
# shard1: ✓ Healthy
# shard2: ✓ Healthy
# shard3: ✓ Healthy
# 
# Summary: 3/3 shards healthy
```

### 4. Start the Service

```bash
# The service will automatically detect and use sharding
docker-compose up asset-management
```

## Usage

### API Usage

The sharding is transparent to API consumers. However, you can optimize queries by providing shard hints:

```http
# Provide shard hint in header
GET /api/v1/assets?project_id=123
X-Shard-Hint: 123e4567-e89b-12d3-a456-426614174000

# Cross-shard search
GET /api/v1/assets/search?q=video
X-Cross-Shard-Query: true
X-Max-Shards: 5
X-Query-Timeout: 30
```

### Python SDK Usage

```python
from mams_sdk import MAMSClient

client = MAMSClient(
    api_url="https://api.mams.example.com",
    api_key="your-api-key"
)

# Create asset (automatically routed to correct shard)
asset = client.assets.create(
    name="video.mp4",
    project_id="123e4567-e89b-12d3-a456-426614174000",
    file_size=1000000
)

# Query with shard hint for better performance
assets = client.assets.list(
    project_id="123e4567-e89b-12d3-a456-426614174000"
)

# Cross-shard search
results = client.assets.search(
    query="production video",
    cross_shard=True
)
```

## Management

### Monitoring Shard Distribution

```bash
python scripts/manage_shards.py show-stats

# Output:
# Gathering shard statistics...
# 
# shard1:
#   Assets: 45,231
#   Size: 523.45 GB
# 
# shard2:
#   Assets: 44,892
#   Size: 498.23 GB
# 
# shard3:
#   Assets: 46,103
#   Size: 531.87 GB
# 
# ========================================
# Total Assets: 136,226
# Total Size: 1,553.55 GB
# Average per shard: 45,408 assets
```

### Rebalancing Shards

```bash
# Check if rebalancing is needed
python scripts/manage_shards.py rebalance --dry-run

# Output:
# Analyzing shard balance (threshold: 20.0%)...
# 
# shard1: 45,231 assets (0.4% deviation)
# shard2: 44,892 assets (1.2% deviation)
# shard3: 46,103 assets (1.5% deviation)
# 
# Ideal distribution: 45,408 assets per shard
# 
# ✓ Shards are balanced within threshold

# Perform actual rebalancing (if needed)
python scripts/manage_shards.py rebalance --threshold 0.1
```

### Adding New Shards

1. Add shard configuration to environment:
```bash
export SHARD_COUNT=4
export SHARD_3_ID=shard4
export SHARD_3_URL=postgresql+asyncpg://user:pass@host4:5432/mams_shard4
```

2. Initialize the new shard:
```bash
python scripts/manage_shards.py init-shards
```

3. Rebalance data (if needed):
```bash
python scripts/manage_shards.py rebalance
```

## Performance Considerations

### 1. Shard Key Selection

Choose your shard key based on access patterns:

- **PROJECT_ID**: Best when most queries are project-scoped
- **OWNER_ID**: Best when queries are user-scoped
- **ASSET_ID**: Best for even distribution but may require cross-shard queries
- **CREATED_AT**: Best for time-series data or archival patterns

### 2. Query Optimization

#### Efficient Queries (Single Shard)
```python
# Good: Includes shard key in query
assets = await repo.get_assets_by_project(project_id)

# Good: Provides shard hint
asset = await repo.get_asset(asset_id, project_id=project_id)
```

#### Cross-Shard Queries
```python
# Searches across all shards (slower)
results = await repo.search_assets({"name": "video"})

# Use pagination to limit impact
results = await repo.search_assets(
    {"name": "video"},
    limit=20,
    offset=0
)
```

### 3. Connection Pooling

Each shard maintains its own connection pool:

```python
# Configuration per shard
SHARD_0_MAX_CONNECTIONS=50
SHARD_0_POOL_SIZE=10
SHARD_0_POOL_OVERFLOW=20
```

### 4. Caching

Enable shard mapping cache for frequently accessed assets:

```bash
SHARDING_CACHE_MAPPINGS=true
SHARDING_MAPPING_CACHE_TTL=3600  # 1 hour
```

## Read Replicas

Read replicas provide horizontal scaling for read operations and improve availability.

### Read Preferences

1. **PRIMARY**: Always read from primary (no replicas used)
2. **PRIMARY_PREFERRED**: Try primary first, use replica if primary unavailable
3. **SECONDARY**: Always read from replica (error if none available)
4. **SECONDARY_PREFERRED**: Try replica first, use primary if none available
5. **NEAREST**: Use the node with lowest latency

### Load Balancing Strategies

1. **ROUND_ROBIN**: Distribute requests evenly in sequence
2. **RANDOM**: Random selection of available replicas
3. **LEAST_CONNECTIONS**: Route to replica with fewest active connections
4. **RESPONSE_TIME**: Route to replica with lowest average response time
5. **WEIGHTED**: Use configured weights for distribution

### Configuration Example

```bash
# Primary shard
SHARD_0_ID=shard1_primary
SHARD_0_URL=postgresql+asyncpg://user:pass@primary1:5432/mams_shard1
SHARD_0_WEIGHT=1.0
SHARD_0_READ_ONLY=false

# Read replica 1
SHARD_1_ID=shard1_read1
SHARD_1_URL=postgresql+asyncpg://user:pass@replica1a:5432/mams_shard1
SHARD_1_WEIGHT=1.0
SHARD_1_READ_ONLY=true

# Read replica 2
SHARD_2_ID=shard1_read2
SHARD_2_URL=postgresql+asyncpg://user:pass@replica1b:5432/mams_shard1
SHARD_2_WEIGHT=2.0  # Gets 2x traffic compared to replica1
SHARD_2_READ_ONLY=true
```

### Monitoring Read Replicas

```http
GET /api/v1/monitoring/shards/replicas

{
  "read_preference": "secondary_preferred",
  "load_balancing": "round_robin",
  "replicas": {
    "shard1_read1": {
      "is_primary": false,
      "is_healthy": true,
      "total_queries": 15420,
      "failed_queries": 12,
      "success_rate": "99.9%",
      "avg_response_time_ms": "5.23",
      "active_connections": 3,
      "lag_seconds": 2,
      "last_check": "2024-01-15 10:30:45"
    }
  }
}
```

### Replica Lag Monitoring

```bash
# Check replica lag
python scripts/manage_shards.py check-lag

# Output:
# Checking replica lag...
# 
# shard1_read1: 2 seconds
# shard1_read2: 3 seconds
# shard2_read1: 1 second
# 
# ⚠️  All replicas within acceptable lag (max: 300s)
```

### Handling Replica Failures

The system automatically handles replica failures:

1. **Health Checks**: Regular health checks detect unhealthy replicas
2. **Automatic Failover**: Unhealthy replicas are removed from rotation
3. **Recovery**: Recovered replicas are automatically re-added
4. **Lag Protection**: Replicas with excessive lag are temporarily excluded

## Troubleshooting

### Common Issues

#### 1. Uneven Distribution
**Symptom**: Some shards have significantly more data
**Solution**: 
- Check shard weights are configured correctly
- Consider changing shard key
- Run rebalancing operation

#### 2. Cross-Shard Query Performance
**Symptom**: Search queries are slow
**Solution**:
- Add appropriate indexes on all shards
- Use pagination to limit result sets
- Consider caching frequent queries

#### 3. Connection Exhaustion
**Symptom**: "Too many connections" errors
**Solution**:
- Reduce connection pool size per shard
- Implement connection pooling at application level
- Consider read replicas for read-heavy workloads

### Health Checks

The service exposes shard health via the monitoring endpoint:

```http
GET /api/v1/monitoring/shards

{
  "status": "healthy",
  "shards": {
    "shard1": {
      "status": "healthy",
      "response_time_ms": 5,
      "connections": {
        "active": 3,
        "idle": 7,
        "total": 10
      }
    },
    "shard2": {
      "status": "healthy",
      "response_time_ms": 6,
      "connections": {
        "active": 2,
        "idle": 8,
        "total": 10
      }
    }
  }
}
```

## Best Practices

1. **Plan Shard Key Carefully**: Changing shard key requires data migration
2. **Monitor Distribution**: Regular monitoring prevents hotspots
3. **Use Read Replicas**: Offload read traffic from primary shards
4. **Test Failover**: Ensure your application handles shard failures gracefully
5. **Backup Individually**: Each shard should have its own backup strategy
6. **Document Shard Mapping**: Keep track of which data lives where

## Migration Guide

### Migrating from Non-Sharded to Sharded

1. **Backup existing database**
```bash
pg_dump mams_assets > mams_assets_backup.sql
```

2. **Initialize shards**
```bash
python scripts/manage_shards.py init-shards
```

3. **Run migration script**
```bash
python scripts/migrate_to_shards.py \
  --source postgresql://user:pass@host/mams_assets \
  --strategy hash \
  --key project_id
```

4. **Verify data integrity**
```bash
python scripts/verify_migration.py
```

5. **Update application configuration**
```bash
export SHARDING_ENABLED=true
```

6. **Deploy and test**

## Advanced Topics

### Custom Sharding Strategy

Implement a custom strategy by extending the base class:

```python
from src.db.sharding import ShardRouter, ShardingStrategy

class CustomShardRouter(ShardRouter):
    def _custom_shard(self, key_value: Any) -> ShardConfig:
        # Implement your custom logic
        if isinstance(key_value, str) and key_value.startswith("priority_"):
            return self.shards["premium_shard"]
        return super()._hash_shard(key_value)
```

### Cross-Shard Transactions

For operations that span multiple shards:

```python
async def transfer_assets(from_project_id: UUID, to_project_id: UUID):
    # Use distributed transaction coordinator
    async with distributed_transaction() as tx:
        # Remove from source shard
        await tx.execute_on_shard(
            from_project_id,
            "UPDATE assets SET project_id = %s WHERE project_id = %s",
            (to_project_id, from_project_id)
        )
        
        # Update indexes on both shards
        await tx.commit()
```

### Shard Maintenance

Schedule maintenance windows per shard:

```python
# Maintenance mode for single shard
async def maintenance_mode(shard_id: str):
    router = await get_shard_router()
    shard = router.shards[shard_id]
    
    # Mark shard as read-only
    shard.read_only = True
    
    # Perform maintenance
    await perform_maintenance(shard)
    
    # Restore write access
    shard.read_only = False
```

## Conclusion

Database sharding in MAMS provides horizontal scalability for growing media asset collections. With proper configuration and monitoring, it can handle millions of assets across distributed infrastructure while maintaining performance and reliability.