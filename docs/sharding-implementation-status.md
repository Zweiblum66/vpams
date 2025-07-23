# Database Sharding Implementation Status - MAMS Project

## Task: PERF-M8-001 - Implement Database Sharding

**Date**: 2025-07-19
**Status**: In Progress

## Overview
Implementing horizontal database sharding for the Asset Management Service to improve performance and scalability. This enables distribution of data across multiple database instances.

## Files Created

### 1. Core Sharding Module (`/services/asset-management/src/db/sharding.py`)
- **Purpose**: Main sharding implementation with routing, session management, and repository patterns
- **Key Components**:
  - `ShardingStrategy`: Enum for sharding strategies (HASH, RANGE, GEOGRAPHY, CUSTOM)
  - `ShardKey`: Enum for shard keys (ASSET_ID, PROJECT_ID, OWNER_ID, CREATED_AT)
  - `ShardConfig`: Configuration for individual shards
  - `ShardRouter`: Routes database operations to appropriate shards
  - `ShardedSession`: Manages database sessions across shards
  - `ShardedRepository`: Base repository with sharding support
  - `AssetShardedRepository`: Asset-specific repository implementation
  - `ShardManager`: Manages shard configuration and migrations

### 2. Database Migration (`/services/asset-management/migrations/alembic/versions/005_add_sharding_support.py`)
- **Purpose**: Database schema changes to support sharding
- **New Tables**:
  - `shard_metadata`: Stores shard configuration
  - `shard_key_mappings`: Tracks entity-to-shard mappings
  - `shard_migrations`: Records shard migration history
  - `shard_statistics`: Monitors shard health and distribution
- **Schema Updates**:
  - Added `shard_id` column to assets, project_containers, and asset_versions tables
  - Created composite indexes for efficient shard key lookups
  - Added stored procedures for cross-shard operations
  - Created triggers for maintaining shard statistics

### 3. Sharding Configuration (`/services/asset-management/src/core/sharding_config.py`)
- **Purpose**: Configuration management for sharding
- **Features**:
  - Pydantic models for type-safe configuration
  - Environment variable support
  - Default configurations for development and production
  - Sharding policies (auto-rebalancing, migration settings, etc.)
  - Support for read replicas and geographic distribution

### 4. Sharding Middleware (`/services/asset-management/src/api/middleware/sharding.py`)
- **Purpose**: FastAPI middleware for handling sharding logic
- **Components**:
  - `ShardingMiddleware`: Main middleware for shard routing
  - `ShardHealthCheckMiddleware`: Monitors shard health
  - `CrossShardQueryMiddleware`: Coordinates cross-shard queries
  - Helper functions for shard-aware responses
  - Exception handlers for sharding-specific errors

## Key Design Decisions

### 1. Sharding Strategy
- **Default**: Hash-based sharding
- **Shard Key**: PROJECT_ID (groups related assets together)
- **Rationale**: Most queries are project-scoped, minimizing cross-shard operations

### 2. Architecture
- **Abstraction Layer**: Clean separation between application and sharding logic
- **Backward Compatibility**: Works with existing code through repository pattern
- **Flexibility**: Supports multiple sharding strategies and easy reconfiguration

### 3. Features Implemented
- **Automatic Shard Selection**: Based on configurable shard key
- **Cross-Shard Queries**: Support for searches and analytics
- **Read Replicas**: Load balancing for read operations
- **Shard Health Monitoring**: Automatic failover capabilities
- **Migration Support**: Tools for rebalancing data across shards

## Configuration Examples

### Development Configuration
```python
ShardingConfiguration(
    enabled=True,
    strategy=ShardingStrategyType.HASH,
    shard_key=ShardKeyType.PROJECT_ID,
    shards=[
        ShardDefinition(
            shard_id="dev_shard1",
            database_url="postgresql+asyncpg://mams:mams@localhost:5432/mams_assets_shard1",
            weight=1.0
        ),
        ShardDefinition(
            shard_id="dev_shard2",
            database_url="postgresql+asyncpg://mams:mams@localhost:5432/mams_assets_shard2",
            weight=1.0
        )
    ]
)
```

### Production Configuration
```python
ShardingConfiguration(
    enabled=True,
    strategy=ShardingStrategyType.HASH,
    shard_key=ShardKeyType.PROJECT_ID,
    shards=[
        # Primary shards by region
        ShardDefinition(
            shard_id="prod_us_east_1",
            database_url="postgresql+asyncpg://mams:${DB_PASSWORD}@us-east-1.db.mams.io:5432/mams_assets_shard1",
            weight=2.0,
            regions=["us-east", "us-central"]
        ),
        # ... additional shards
        # Read replicas
        ShardDefinition(
            shard_id="prod_us_east_1_read",
            database_url="postgresql+asyncpg://mams_read:${DB_PASSWORD}@us-east-1-read.db.mams.io:5432/mams_assets_shard1",
            read_only=True
        )
    ]
)
```

## Usage Example

```python
# Get sharded session
router = await get_shard_router()
sharded_session = ShardedSession(router)

# Create asset on appropriate shard
repo = AssetShardedRepository(sharded_session)
asset = await repo.create_asset({
    "name": "video.mp4",
    "project_id": "123e4567-e89b-12d3-a456-426614174000",
    "owner_id": "user-123"
})

# Query across all shards
results = await repo.search_assets({
    "name": "video",
    "asset_type": AssetType.VIDEO
})
```

## Next Steps

1. **Update Asset Service**: Modify the existing asset service to use sharded repositories
2. **Create Shard Management CLI**: Tools for shard administration
3. **Implement Monitoring Dashboard**: Visualize shard distribution and health
4. **Write Tests**: Comprehensive test suite for sharding functionality
5. **Documentation**: User guide for sharding configuration and operations
6. **Performance Testing**: Benchmark sharded vs non-sharded performance

## Environment Variables

```bash
# Enable sharding
SHARDING_ENABLED=true

# Sharding configuration
SHARDING_STRATEGY=hash
SHARDING_KEY=project_id
SHARD_COUNT=3

# Individual shard configuration
SHARD_0_ID=shard1
SHARD_0_URL=postgresql+asyncpg://user:pass@host:5432/db_shard1
SHARD_0_WEIGHT=1.0
SHARD_0_REGIONS=us-east,us-west

# Sharding policies
SHARDING_AUTO_REBALANCE=false
SHARDING_REBALANCE_THRESHOLD=0.2
SHARDING_MIGRATION_BATCH_SIZE=100
SHARDING_CROSS_SHARD_QUERIES=true
```

## Benefits

1. **Horizontal Scalability**: Distribute data across multiple databases
2. **Performance**: Parallel query execution across shards
3. **Geographic Distribution**: Place data closer to users
4. **Fault Tolerance**: Individual shard failures don't affect entire system
5. **Resource Optimization**: Balance load across database instances

## Current State Summary

- ✅ Core sharding infrastructure implemented
- ✅ Database migrations created
- ✅ Configuration system built
- ✅ Middleware for FastAPI integration
- 🔄 Asset service integration pending
- 🔄 Testing and documentation pending
- 🔄 Monitoring and management tools pending

This implementation provides a solid foundation for horizontal scaling of the MAMS database layer, enabling the system to handle massive amounts of media assets across distributed infrastructure.