"""
Configuration for Edge Cache Service

This module handles all configuration for the edge cache service including
cache policies, storage backends, and geographic settings.
"""

from typing import Dict, List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings
from enum import Enum


class CacheStrategy(str, Enum):
    """Available caching strategies"""
    LRU = "lru"  # Least Recently Used
    LFU = "lfu"  # Least Frequently Used
    FIFO = "fifo"  # First In First Out
    TTL = "ttl"  # Time To Live based
    ADAPTIVE = "adaptive"  # Adaptive based on usage patterns


class StorageBackend(str, Enum):
    """Available storage backends for cache"""
    MEMORY = "memory"
    REDIS = "redis"
    DISK = "disk"
    HYBRID = "hybrid"  # Memory + Disk


class Settings(BaseSettings):
    """Edge cache service settings"""
    
    # Service settings
    service_name: str = "edge-cache"
    service_port: int = 8000
    debug: bool = False
    
    # Cache settings
    cache_strategy: CacheStrategy = CacheStrategy.LRU
    cache_size_mb: int = Field(1024, description="Total cache size in MB")
    cache_ttl_seconds: int = Field(3600, description="Default TTL in seconds")
    max_object_size_mb: int = Field(100, description="Maximum cacheable object size")
    
    # Storage backend
    storage_backend: StorageBackend = StorageBackend.HYBRID
    memory_cache_size_mb: int = Field(256, description="Memory cache size for hybrid mode")
    disk_cache_path: str = "/var/cache/mams"
    
    # Redis settings (if using Redis backend)
    redis_url: str = "redis://localhost:6379/0"
    redis_max_connections: int = 50
    redis_connection_timeout: int = 10
    
    # Geographic settings
    edge_location: str = Field("us-east-1", description="Edge location identifier")
    edge_region: str = Field("us-east", description="Edge region")
    edge_tier: int = Field(1, description="Edge tier (1=primary, 2=secondary, 3=tertiary)")
    
    # Origin settings
    origin_url: str = "http://api-gateway:8000"
    origin_timeout: int = 30
    origin_retry_count: int = 3
    origin_retry_delay: float = 1.0
    
    # Cache policies
    cache_control_respect: bool = True
    cache_private_content: bool = False
    cache_query_strings: bool = True
    cache_headers: List[str] = Field(
        default_factory=lambda: ["Accept", "Accept-Language", "Authorization"],
        description="Headers to include in cache key"
    )
    
    # Content type policies
    cacheable_content_types: List[str] = Field(
        default_factory=lambda: [
            "image/*",
            "video/*",
            "audio/*",
            "application/json",
            "application/pdf",
            "text/css",
            "text/javascript",
            "application/javascript"
        ]
    )
    
    # Cache invalidation
    invalidation_enabled: bool = True
    invalidation_batch_size: int = 100
    invalidation_delay_ms: int = 100
    
    # Performance settings
    max_concurrent_requests: int = 1000
    request_timeout: int = 60
    keepalive_timeout: int = 5
    
    # Monitoring
    metrics_enabled: bool = True
    metrics_port: int = 9090
    log_level: str = "INFO"
    
    # Security
    enable_auth_caching: bool = True
    auth_cache_ttl: int = 300
    enable_geo_blocking: bool = False
    allowed_countries: List[str] = Field(default_factory=list)
    blocked_countries: List[str] = Field(default_factory=list)
    
    # Advanced features
    enable_compression: bool = True
    compression_level: int = Field(6, ge=1, le=9)
    enable_range_requests: bool = True
    enable_conditional_requests: bool = True
    enable_prefetching: bool = True
    prefetch_threshold: float = Field(0.8, description="Prefetch when 80% through content")
    
    class Config:
        env_prefix = "EDGE_CACHE_"
        case_sensitive = False


# Cache key patterns
CACHE_KEY_PATTERNS = {
    "asset": "edge:{location}:asset:{asset_id}:{variant}",
    "metadata": "edge:{location}:metadata:{asset_id}",
    "search": "edge:{location}:search:{query_hash}",
    "user": "edge:{location}:user:{user_id}",
    "project": "edge:{location}:project:{project_id}",
    "thumbnail": "edge:{location}:thumb:{asset_id}:{size}",
    "proxy": "edge:{location}:proxy:{asset_id}:{quality}"
}


# Cache priority levels
CACHE_PRIORITY = {
    "thumbnail": 10,  # Highest priority
    "metadata": 9,
    "proxy_low": 8,
    "search_results": 7,
    "proxy_medium": 6,
    "user_data": 5,
    "project_data": 4,
    "proxy_high": 3,
    "asset_original": 2,
    "analytics": 1  # Lowest priority
}


# Geographic regions and their edge locations
EDGE_LOCATIONS = {
    "us-east": ["us-east-1", "us-east-2"],
    "us-west": ["us-west-1", "us-west-2"],
    "eu-west": ["eu-west-1", "eu-west-2", "eu-west-3"],
    "eu-central": ["eu-central-1", "eu-central-2"],
    "asia-pacific": ["ap-southeast-1", "ap-southeast-2", "ap-northeast-1"],
    "south-america": ["sa-east-1"],
    "africa": ["af-south-1"],
    "middle-east": ["me-south-1"]
}


def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


def get_cache_key(pattern: str, **kwargs) -> str:
    """Generate cache key from pattern and parameters"""
    if pattern not in CACHE_KEY_PATTERNS:
        raise ValueError(f"Unknown cache key pattern: {pattern}")
    
    return CACHE_KEY_PATTERNS[pattern].format(**kwargs)


def get_nearest_edge_location(user_location: str) -> str:
    """Get nearest edge location for a user location"""
    # This would use geo-IP or latency-based routing in production
    # For now, return a simple mapping
    location_map = {
        "us": "us-east-1",
        "eu": "eu-west-1",
        "asia": "ap-southeast-1",
        "sa": "sa-east-1",
        "af": "af-south-1",
        "me": "me-south-1"
    }
    
    for prefix, edge in location_map.items():
        if user_location.lower().startswith(prefix):
            return edge
    
    return "us-east-1"  # Default