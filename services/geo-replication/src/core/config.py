"""
Configuration for geo-replication service
"""

from typing import List, Optional
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Settings for geo-replication service"""
    
    # Service configuration
    SERVICE_NAME: str = "geo-replication"
    SERVICE_VERSION: str = "1.0.0"
    SERVICE_PORT: int = 8015
    
    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # Region configuration
    PRIMARY_REGION: str = "us-east-1"
    SECONDARY_REGIONS: List[str] = ["eu-west-1", "ap-southeast-1"]
    CURRENT_REGION: str = "us-east-1"
    
    # Replication settings
    GEO_REPLICATION_ENABLED: bool = True
    REPLICATION_MODE: str = "async"  # async, sync, semi_sync
    CONFLICT_RESOLUTION_STRATEGY: str = "last_write_wins"
    REPLICATION_BATCH_SIZE: int = 1000
    MAX_REPLICATION_LAG_SECONDS: int = 300
    REPLICATION_INTERVAL_SECONDS: int = 5
    
    # Database URLs (PostgreSQL)
    PRIMARY_DB_URL: str = "postgresql+asyncpg://user:pass@localhost:5432/mams_primary"
    US_EAST_1_DB_URL: str = "postgresql+asyncpg://user:pass@localhost:5432/mams_us_east_1"
    EU_WEST_1_DB_URL: str = "postgresql+asyncpg://user:pass@localhost:5433/mams_eu_west_1"
    AP_SOUTHEAST_1_DB_URL: str = "postgresql+asyncpg://user:pass@localhost:5434/mams_ap_southeast_1"
    
    # MongoDB URLs
    PRIMARY_MONGODB_URL: str = "mongodb://localhost:27017/mams_primary"
    US_EAST_1_MONGODB_URL: str = "mongodb://localhost:27017/mams_us_east_1"
    EU_WEST_1_MONGODB_URL: str = "mongodb://localhost:27018/mams_eu_west_1"
    AP_SOUTHEAST_1_MONGODB_URL: str = "mongodb://localhost:27019/mams_ap_southeast_1"
    MONGODB_DATABASE: str = "mams"
    
    # Redis URLs
    PRIMARY_REDIS_URL: str = "redis://localhost:6379/0"
    US_EAST_1_REDIS_URL: str = "redis://localhost:6379/0"
    EU_WEST_1_REDIS_URL: str = "redis://localhost:6380/0"
    AP_SOUTHEAST_1_REDIS_URL: str = "redis://localhost:6381/0"
    
    # OpenSearch URLs
    PRIMARY_OPENSEARCH_URL: str = "https://localhost:9200"
    US_EAST_1_OPENSEARCH_URL: str = "https://localhost:9200"
    EU_WEST_1_OPENSEARCH_URL: str = "https://localhost:9201"
    AP_SOUTHEAST_1_OPENSEARCH_URL: str = "https://localhost:9202"
    
    # S3 endpoints
    PRIMARY_S3_ENDPOINT: str = "https://s3.us-east-1.amazonaws.com"
    US_EAST_1_S3_ENDPOINT: str = "https://s3.us-east-1.amazonaws.com"
    EU_WEST_1_S3_ENDPOINT: str = "https://s3.eu-west-1.amazonaws.com"
    AP_SOUTHEAST_1_S3_ENDPOINT: str = "https://s3.ap-southeast-1.amazonaws.com"
    
    # AWS configuration
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: str = "us-east-1"
    
    # Authentication
    SECRET_KEY: str = "your-secret-key-here"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["*"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    
    # Monitoring
    PROMETHEUS_ENABLED: bool = True
    PROMETHEUS_PORT: int = 9090
    
    # Health check
    HEALTH_CHECK_INTERVAL: int = 30
    HEALTH_CHECK_TIMEOUT: int = 10
    
    # Retry configuration
    MAX_RETRY_ATTEMPTS: int = 3
    RETRY_DELAY_SECONDS: int = 5
    RETRY_BACKOFF_FACTOR: float = 2.0
    
    # Performance
    CONNECTION_POOL_SIZE: int = 20
    CONNECTION_POOL_TIMEOUT: int = 30
    
    # Feature flags
    ENABLE_CROSS_REGION_SEARCH: bool = True
    ENABLE_AUTO_FAILOVER: bool = True
    ENABLE_CONFLICT_DETECTION: bool = True
    ENABLE_BANDWIDTH_THROTTLING: bool = False
    
    # Bandwidth limits (MB/s)
    REPLICATION_BANDWIDTH_LIMIT: Optional[int] = None  # None = unlimited
    PER_REGION_BANDWIDTH_LIMITS: dict = {}
    
    # Alerting
    ALERT_WEBHOOK_URL: Optional[str] = None
    ALERT_EMAIL_ADDRESSES: List[str] = []
    
    # Metrics storage
    METRICS_RETENTION_DAYS: int = 30
    METRICS_AGGREGATION_INTERVAL: int = 60  # seconds
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


settings = get_settings()