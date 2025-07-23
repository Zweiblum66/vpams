"""
Configuration for failover service
"""

from typing import List, Optional, Dict, Any
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Settings for failover service"""
    
    # Service configuration
    SERVICE_NAME: str = "failover"
    SERVICE_VERSION: str = "1.0.0"
    SERVICE_PORT: int = 8017
    
    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # Region configuration
    PRIMARY_REGION: str = "us-east-1"
    SECONDARY_REGIONS: List[str] = ["us-west-2", "eu-west-1", "ap-southeast-1"]
    CURRENT_REGION: str = "us-east-1"
    
    # Failover configuration
    HEALTH_CHECK_INTERVAL_SECONDS: int = 30
    HEALTH_CHECK_TIMEOUT_SECONDS: int = 10
    FAILOVER_THRESHOLD: int = 3  # Number of failed health checks before failover
    FAILBACK_DELAY_MINUTES: int = 30  # Wait time before failing back to primary
    AUTO_FAILOVER_ENABLED: bool = True
    AUTO_FAILBACK_ENABLED: bool = True
    
    # Service health check endpoints
    SERVICE_HEALTH_ENDPOINTS: Dict[str, str] = {
        "api_gateway": "http://api-gateway:8000/health",
        "user_management": "http://user-management:8001/health",
        "storage": "http://storage:8002/health",
        "asset_management": "http://asset-management:8003/health",
        "metadata": "http://metadata:8004/health",
        "search": "http://search:8005/health",
        "ingest": "http://ingest:8006/health",
        "proxy_generation": "http://proxy-generation:8007/health",
        "workflow": "http://workflow:8008/health",
        "ai_ml": "http://ai-ml:8009/health",
        "rights_management": "http://rights-management:8010/health",
        "monitoring": "http://monitoring:8011/health",
        "integration": "http://integration:8012/health"
    }
    
    # Database failover
    DATABASE_ENDPOINTS: Dict[str, Dict[str, str]] = {
        "us-east-1": {
            "postgresql": "postgresql://user:pass@postgres-us-east-1:5432/mams",
            "mongodb": "mongodb://mongo-us-east-1:27017/mams",
            "redis": "redis://redis-us-east-1:6379/0",
            "opensearch": "https://opensearch-us-east-1:9200"
        },
        "us-west-2": {
            "postgresql": "postgresql://user:pass@postgres-us-west-2:5432/mams",
            "mongodb": "mongodb://mongo-us-west-2:27017/mams",
            "redis": "redis://redis-us-west-2:6379/0",
            "opensearch": "https://opensearch-us-west-2:9200"
        },
        "eu-west-1": {
            "postgresql": "postgresql://user:pass@postgres-eu-west-1:5432/mams",
            "mongodb": "mongodb://mongo-eu-west-1:27017/mams",
            "redis": "redis://redis-eu-west-1:6379/0",
            "opensearch": "https://opensearch-eu-west-1:9200"
        },
        "ap-southeast-1": {
            "postgresql": "postgresql://user:pass@postgres-ap-southeast-1:5432/mams",
            "mongodb": "mongodb://mongo-ap-southeast-1:27017/mams",
            "redis": "redis://redis-ap-southeast-1:6379/0",
            "opensearch": "https://opensearch-ap-southeast-1:9200"
        }
    }
    
    # Load balancer configuration
    LOAD_BALANCER_TYPE: str = "round_robin"  # round_robin, least_connections, weighted
    REGION_WEIGHTS: Dict[str, float] = {
        "us-east-1": 0.4,
        "us-west-2": 0.3,
        "eu-west-1": 0.2,
        "ap-southeast-1": 0.1
    }
    
    # Recovery Point Objective (RPO) and Recovery Time Objective (RTO)
    RPO_MINUTES: int = 5  # Maximum acceptable data loss
    RTO_MINUTES: int = 15  # Maximum acceptable downtime
    
    # Notification configuration
    ENABLE_NOTIFICATIONS: bool = True
    NOTIFICATION_WEBHOOKS: List[str] = []
    NOTIFICATION_EMAILS: List[str] = []
    SLACK_WEBHOOK_URL: Optional[str] = None
    PAGERDUTY_INTEGRATION_KEY: Optional[str] = None
    
    # Redis configuration for state management
    REDIS_URL: str = "redis://localhost:6379/1"
    
    # Database URL for failover event storage
    DATABASE_URL: str = "postgresql+asyncpg://user:pass@localhost:5432/mams_failover"
    
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
    
    # Metrics
    PROMETHEUS_ENABLED: bool = True
    PROMETHEUS_PORT: int = 9090
    
    # Feature flags
    ENABLE_CROSS_REGION_SYNC: bool = True
    ENABLE_DATA_CONSISTENCY_CHECK: bool = True
    ENABLE_AUTOMATIC_SCALING: bool = False
    ENABLE_PREDICTIVE_FAILOVER: bool = False
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


settings = get_settings()