"""Configuration settings for the Partner APIs Service"""

from pydantic import BaseSettings, Field
from typing import List, Dict, Any
import os


class Settings(BaseSettings):
    """Application settings"""
    
    # Service configuration
    service_name: str = "partner-apis"
    service_version: str = "1.0.0"
    port: int = Field(default=8016, env="SERVICE_PORT")
    debug: bool = Field(default=False, env="DEBUG")
    environment: str = Field(default="development", env="ENVIRONMENT")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Database
    database_url: str = Field(env="DATABASE_URL")
    
    # Redis for caching and rate limiting
    redis_url: str = Field(default="redis://redis:6379/0", env="REDIS_URL")
    
    # Security
    jwt_secret_key: str = Field(env="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_expiration_minutes: int = Field(default=60, env="JWT_EXPIRATION_MINUTES")
    
    # API Key settings
    api_key_length: int = Field(default=32, env="API_KEY_LENGTH")
    api_key_prefix: str = Field(default="mams_", env="API_KEY_PREFIX")
    
    # Rate limiting defaults
    default_rate_limit: str = Field(default="1000/hour", env="DEFAULT_RATE_LIMIT")
    default_burst_limit: int = Field(default=100, env="DEFAULT_BURST_LIMIT")
    
    # CORS settings
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"],
        env="CORS_ORIGINS"
    )
    
    # Trusted hosts for production
    allowed_hosts: List[str] = Field(
        default=["localhost", "127.0.0.1"],
        env="ALLOWED_HOSTS"
    )
    
    # External service URLs
    user_management_url: str = Field(
        default="http://user-management:8002",
        env="USER_MANAGEMENT_URL"
    )
    asset_management_url: str = Field(
        default="http://asset-management:8001",
        env="ASSET_MANAGEMENT_URL"
    )
    metadata_service_url: str = Field(
        default="http://metadata-service:8005",
        env="METADATA_SERVICE_URL"
    )
    search_engine_url: str = Field(
        default="http://search-engine:8006",
        env="SEARCH_ENGINE_URL"
    )
    workflow_engine_url: str = Field(
        default="http://workflow-engine:8009",
        env="WORKFLOW_ENGINE_URL"
    )
    
    # Webhook settings
    webhook_timeout: int = Field(default=30, env="WEBHOOK_TIMEOUT")
    webhook_retry_attempts: int = Field(default=3, env="WEBHOOK_RETRY_ATTEMPTS")
    webhook_retry_delay: int = Field(default=60, env="WEBHOOK_RETRY_DELAY")
    
    # Analytics settings
    analytics_retention_days: int = Field(default=90, env="ANALYTICS_RETENTION_DAYS")
    
    # Feature flags
    enable_api_v2: bool = Field(default=True, env="ENABLE_API_V2")
    enable_webhooks: bool = Field(default=True, env="ENABLE_WEBHOOKS")
    enable_analytics: bool = Field(default=True, env="ENABLE_ANALYTICS")
    enable_rate_limiting: bool = Field(default=True, env="ENABLE_RATE_LIMITING")
    
    # Partner tier configurations
    partner_tiers: Dict[str, Dict[str, Any]] = {
        "basic": {
            "rate_limit": "500/hour",
            "burst_limit": 50,
            "features": ["assets", "metadata", "search"],
            "webhook_limit": 5,
            "api_versions": ["v1"]
        },
        "standard": {
            "rate_limit": "2000/hour", 
            "burst_limit": 200,
            "features": ["assets", "metadata", "search", "workflows", "projects"],
            "webhook_limit": 20,
            "api_versions": ["v1", "v2"]
        },
        "premium": {
            "rate_limit": "10000/hour",
            "burst_limit": 1000,
            "features": ["*"],
            "webhook_limit": 100,
            "api_versions": ["v1", "v2"]
        },
        "enterprise": {
            "rate_limit": "unlimited",
            "burst_limit": 5000,
            "features": ["*"],
            "webhook_limit": "unlimited",
            "api_versions": ["v1", "v2"]
        }
    }
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()