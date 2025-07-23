"""
Sharding Configuration for Asset Management Service

This module provides configuration for database sharding including
shard definitions, routing rules, and rebalancing policies.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, validator
from enum import Enum
import os


class ShardingStrategyType(str, Enum):
    """Available sharding strategies"""
    HASH = "hash"
    RANGE = "range"  
    GEOGRAPHY = "geography"
    CUSTOM = "custom"


class ShardKeyType(str, Enum):
    """Available shard keys"""
    ASSET_ID = "asset_id"
    PROJECT_ID = "project_id"
    OWNER_ID = "owner_id"
    CREATED_AT = "created_at"


class ShardDefinition(BaseModel):
    """Configuration for a single shard"""
    shard_id: str = Field(..., description="Unique identifier for the shard")
    database_url: str = Field(..., description="Database connection URL")
    weight: float = Field(1.0, ge=0.0, le=10.0, description="Shard weight for distribution")
    read_only: bool = Field(False, description="Whether this is a read-only replica")
    min_range: Optional[str] = Field(None, description="Minimum range value for range sharding")
    max_range: Optional[str] = Field(None, description="Maximum range value for range sharding")
    regions: List[str] = Field(default_factory=list, description="Geographic regions served")
    max_connections: int = Field(50, ge=1, description="Maximum database connections")
    
    @validator("database_url")
    def validate_database_url(cls, v):
        """Ensure database URL is properly formatted"""
        if not v.startswith(("postgresql://", "postgresql+asyncpg://")):
            raise ValueError("Database URL must be a PostgreSQL URL")
        return v


class ShardingPolicy(BaseModel):
    """Policies for sharding behavior"""
    auto_rebalance: bool = Field(False, description="Enable automatic rebalancing")
    rebalance_threshold: float = Field(0.2, ge=0.0, le=1.0, description="Imbalance threshold to trigger rebalancing")
    migration_batch_size: int = Field(100, ge=1, description="Number of entities to migrate per batch")
    migration_delay_ms: int = Field(100, ge=0, description="Delay between migration batches")
    enable_cross_shard_queries: bool = Field(True, description="Allow queries across multiple shards")
    cache_shard_mappings: bool = Field(True, description="Cache entity-to-shard mappings")
    mapping_cache_ttl: int = Field(3600, ge=0, description="TTL for cached mappings in seconds")
    
    # Read replica policies
    read_preference: str = Field("secondary_preferred", description="Default read preference")
    load_balancing_strategy: str = Field("round_robin", description="Load balancing strategy for replicas")
    max_replica_lag_seconds: int = Field(300, ge=0, description="Maximum acceptable replica lag in seconds")
    health_check_interval_seconds: int = Field(30, ge=5, description="Interval between replica health checks")


class ShardingConfiguration(BaseModel):
    """Complete sharding configuration"""
    enabled: bool = Field(True, description="Enable database sharding")
    strategy: ShardingStrategyType = Field(ShardingStrategyType.HASH, description="Sharding strategy")
    shard_key: ShardKeyType = Field(ShardKeyType.PROJECT_ID, description="Key used for sharding")
    shards: List[ShardDefinition] = Field(..., min_items=1, description="List of shard definitions")
    policy: ShardingPolicy = Field(default_factory=ShardingPolicy, description="Sharding policies")
    
    @validator("shards")
    def validate_shards(cls, v):
        """Validate shard configuration"""
        shard_ids = [s.shard_id for s in v]
        if len(shard_ids) != len(set(shard_ids)):
            raise ValueError("Duplicate shard IDs found")
        
        # Ensure at least one write shard
        write_shards = [s for s in v if not s.read_only]
        if not write_shards:
            raise ValueError("At least one write-enabled shard is required")
        
        return v
    
    @validator("strategy", pre=True)
    def validate_strategy_compatibility(cls, v, values):
        """Validate strategy is compatible with shard definitions"""
        if v == ShardingStrategyType.RANGE:
            shards = values.get("shards", [])
            for shard in shards:
                if not shard.read_only and (shard.min_range is None or shard.max_range is None):
                    raise ValueError("Range sharding requires min_range and max_range for write shards")
        return v


def load_sharding_config() -> ShardingConfiguration:
    """Load sharding configuration from environment or defaults"""
    
    # Check if sharding is enabled
    if os.getenv("SHARDING_ENABLED", "false").lower() == "false":
        # Return minimal config with sharding disabled
        return ShardingConfiguration(
            enabled=False,
            shards=[
                ShardDefinition(
                    shard_id="default",
                    database_url=os.getenv("DATABASE_URL", "postgresql+asyncpg://mams:mams@localhost:5432/mams_assets")
                )
            ]
        )
    
    # Load from environment variables
    strategy = ShardingStrategyType(os.getenv("SHARDING_STRATEGY", "hash"))
    shard_key = ShardKeyType(os.getenv("SHARDING_KEY", "project_id"))
    
    # Load shard definitions
    shards = []
    shard_count = int(os.getenv("SHARD_COUNT", "3"))
    
    for i in range(shard_count):
        shard_id = os.getenv(f"SHARD_{i}_ID", f"shard{i+1}")
        database_url = os.getenv(
            f"SHARD_{i}_URL",
            f"postgresql+asyncpg://mams:mams@localhost:5432/mams_assets_shard{i+1}"
        )
        weight = float(os.getenv(f"SHARD_{i}_WEIGHT", "1.0"))
        read_only = os.getenv(f"SHARD_{i}_READ_ONLY", "false").lower() == "true"
        regions = os.getenv(f"SHARD_{i}_REGIONS", "").split(",") if os.getenv(f"SHARD_{i}_REGIONS") else []
        
        shards.append(ShardDefinition(
            shard_id=shard_id,
            database_url=database_url,
            weight=weight,
            read_only=read_only,
            regions=[r.strip() for r in regions if r.strip()]
        ))
    
    # Load policies
    policy = ShardingPolicy(
        auto_rebalance=os.getenv("SHARDING_AUTO_REBALANCE", "false").lower() == "true",
        rebalance_threshold=float(os.getenv("SHARDING_REBALANCE_THRESHOLD", "0.2")),
        migration_batch_size=int(os.getenv("SHARDING_MIGRATION_BATCH_SIZE", "100")),
        migration_delay_ms=int(os.getenv("SHARDING_MIGRATION_DELAY_MS", "100")),
        enable_cross_shard_queries=os.getenv("SHARDING_CROSS_SHARD_QUERIES", "true").lower() == "true",
        cache_shard_mappings=os.getenv("SHARDING_CACHE_MAPPINGS", "true").lower() == "true",
        mapping_cache_ttl=int(os.getenv("SHARDING_MAPPING_CACHE_TTL", "3600"))
    )
    
    return ShardingConfiguration(
        enabled=True,
        strategy=strategy,
        shard_key=shard_key,
        shards=shards,
        policy=policy
    )


# Default configurations for different environments
DEFAULT_CONFIGS = {
    "development": ShardingConfiguration(
        enabled=True,
        strategy=ShardingStrategyType.HASH,
        shard_key=ShardKeyType.PROJECT_ID,
        shards=[
            ShardDefinition(
                shard_id="dev_shard1",
                database_url="postgresql+asyncpg://mams:mams@localhost:5432/mams_assets_shard1",
                weight=1.0,
                regions=["local"]
            ),
            ShardDefinition(
                shard_id="dev_shard2",
                database_url="postgresql+asyncpg://mams:mams@localhost:5432/mams_assets_shard2",
                weight=1.0,
                regions=["local"]
            )
        ],
        policy=ShardingPolicy(
            auto_rebalance=False,
            enable_cross_shard_queries=True
        )
    ),
    
    "production": ShardingConfiguration(
        enabled=True,
        strategy=ShardingStrategyType.HASH,
        shard_key=ShardKeyType.PROJECT_ID,
        shards=[
            ShardDefinition(
                shard_id="prod_us_east_1",
                database_url="postgresql+asyncpg://mams:${DB_PASSWORD}@us-east-1.db.mams.io:5432/mams_assets_shard1",
                weight=2.0,
                regions=["us-east", "us-central"],
                max_connections=100
            ),
            ShardDefinition(
                shard_id="prod_us_west_1",
                database_url="postgresql+asyncpg://mams:${DB_PASSWORD}@us-west-1.db.mams.io:5432/mams_assets_shard2",
                weight=2.0,
                regions=["us-west", "us-mountain"],
                max_connections=100
            ),
            ShardDefinition(
                shard_id="prod_eu_west_1",
                database_url="postgresql+asyncpg://mams:${DB_PASSWORD}@eu-west-1.db.mams.io:5432/mams_assets_shard3",
                weight=1.5,
                regions=["eu-west", "eu-central"],
                max_connections=100
            ),
            ShardDefinition(
                shard_id="prod_asia_1",
                database_url="postgresql+asyncpg://mams:${DB_PASSWORD}@asia-1.db.mams.io:5432/mams_assets_shard4",
                weight=1.0,
                regions=["asia-pacific", "asia-south"],
                max_connections=100
            ),
            # Read replicas
            ShardDefinition(
                shard_id="prod_us_east_1_read",
                database_url="postgresql+asyncpg://mams_read:${DB_PASSWORD}@us-east-1-read.db.mams.io:5432/mams_assets_shard1",
                weight=0.0,
                read_only=True,
                regions=["us-east", "us-central"],
                max_connections=200
            ),
            ShardDefinition(
                shard_id="prod_eu_west_1_read",
                database_url="postgresql+asyncpg://mams_read:${DB_PASSWORD}@eu-west-1-read.db.mams.io:5432/mams_assets_shard3",
                weight=0.0,
                read_only=True,
                regions=["eu-west", "eu-central"],
                max_connections=200
            )
        ],
        policy=ShardingPolicy(
            auto_rebalance=True,
            rebalance_threshold=0.15,
            migration_batch_size=500,
            migration_delay_ms=50,
            enable_cross_shard_queries=True,
            cache_shard_mappings=True,
            mapping_cache_ttl=7200
        )
    )
}


def get_default_config(environment: str) -> ShardingConfiguration:
    """Get default configuration for an environment"""
    return DEFAULT_CONFIGS.get(environment, DEFAULT_CONFIGS["development"])