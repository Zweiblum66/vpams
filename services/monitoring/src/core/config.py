"""
Configuration settings for the Monitoring Service
"""

from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """
    Service configuration settings
    """
    # Service info
    SERVICE_NAME: str = "monitoring"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = Field("development", env="ENVIRONMENT")
    DEBUG: bool = Field(True, env="DEBUG")
    PORT: int = Field(8012, env="SERVICE_PORT")
    
    # Database
    DATABASE_URL: str = Field(
        "postgresql+asyncpg://mams:mams@postgres:5432/mams_monitoring",
        env="DATABASE_URL"
    )
    
    # Redis
    REDIS_URL: str = Field("redis://redis:6379/0", env="REDIS_URL")
    
    # CORS
    ALLOWED_ORIGINS: List[str] = Field(
        ["http://localhost:3000", "http://localhost:8000"],
        env="ALLOWED_ORIGINS"
    )
    
    # Monitoring specific settings
    METRICS_RETENTION_DAYS: int = Field(30, env="METRICS_RETENTION_DAYS")
    METRICS_COLLECTION_INTERVAL: int = Field(60, env="METRICS_COLLECTION_INTERVAL")  # seconds
    
    # Service discovery
    API_GATEWAY_URL: str = Field("http://api-gateway:8000", env="API_GATEWAY_URL")
    USER_SERVICE_URL: str = Field("http://user-management:8001", env="USER_SERVICE_URL")
    ASSET_SERVICE_URL: str = Field("http://asset-management:8003", env="ASSET_SERVICE_URL")
    STORAGE_SERVICE_URL: str = Field("http://storage-abstraction:8002", env="STORAGE_SERVICE_URL")
    METADATA_SERVICE_URL: str = Field("http://metadata-service:8004", env="METADATA_SERVICE_URL")
    SEARCH_SERVICE_URL: str = Field("http://search-engine:8005", env="SEARCH_SERVICE_URL")
    INGEST_SERVICE_URL: str = Field("http://ingest-service:8006", env="INGEST_SERVICE_URL")
    PROXY_SERVICE_URL: str = Field("http://proxy-generation:8007", env="PROXY_SERVICE_URL")
    WORKFLOW_SERVICE_URL: str = Field("http://workflow-engine:8008", env="WORKFLOW_SERVICE_URL")
    AI_SERVICE_URL: str = Field("http://ai-ml-service:8009", env="AI_SERVICE_URL")
    RIGHTS_SERVICE_URL: str = Field("http://rights-management:8010", env="RIGHTS_SERVICE_URL")
    INTEGRATION_SERVICE_URL: str = Field("http://integration-service:8011", env="INTEGRATION_SERVICE_URL")
    
    # Alert settings
    ALERT_WEBHOOK_URL: Optional[str] = Field(None, env="ALERT_WEBHOOK_URL")
    ALERT_EMAIL_ENABLED: bool = Field(False, env="ALERT_EMAIL_ENABLED")
    ALERT_EMAIL_FROM: Optional[str] = Field(None, env="ALERT_EMAIL_FROM")
    ALERT_EMAIL_TO: List[str] = Field([], env="ALERT_EMAIL_TO")
    
    # Prometheus settings
    PROMETHEUS_MULTIPROC_DIR: Optional[str] = Field(None, env="PROMETHEUS_MULTIPROC_DIR")
    
    # Authentication
    JWT_SECRET_KEY: str = Field("your-secret-key-here", env="JWT_SECRET_KEY")
    JWT_ALGORITHM: str = Field("HS256", env="JWT_ALGORITHM")
    JWT_EXPIRATION_MINUTES: int = Field(60, env="JWT_EXPIRATION_MINUTES")
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()