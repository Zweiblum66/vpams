"""Configuration settings for Beta Program Service"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings"""
    
    # Service configuration
    service_name: str = Field(default="beta-program", env="SERVICE_NAME")
    service_port: int = Field(default=8019, env="SERVICE_PORT")
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/beta_program",
        env="DATABASE_URL"
    )
    
    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    redis_ttl: int = Field(default=3600, env="REDIS_TTL")
    
    # Email configuration
    email_provider: str = Field(default="sendgrid", env="EMAIL_PROVIDER")
    email_api_key: Optional[str] = Field(default=None, env="EMAIL_API_KEY")
    email_from_address: str = Field(default="beta@mams.io", env="EMAIL_FROM_ADDRESS")
    email_from_name: str = Field(default="MAMS Beta Program", env="EMAIL_FROM_NAME")
    
    # Beta program settings
    beta_registration_open: bool = Field(default=True, env="BETA_REGISTRATION_OPEN")
    beta_invitation_required: bool = Field(default=False, env="BETA_INVITATION_REQUIRED")
    max_beta_users: int = Field(default=1000, env="MAX_BETA_USERS")
    beta_phase: str = Field(default="closed_beta", env="BETA_PHASE")  # closed_beta, open_beta, release_candidate
    
    # Feature flags
    default_feature_rollout_percentage: int = Field(default=10, env="DEFAULT_FEATURE_ROLLOUT_PERCENTAGE")
    feature_flag_cache_ttl: int = Field(default=300, env="FEATURE_FLAG_CACHE_TTL")
    
    # Analytics
    analytics_retention_days: int = Field(default=90, env="ANALYTICS_RETENTION_DAYS")
    analytics_batch_size: int = Field(default=1000, env="ANALYTICS_BATCH_SIZE")
    
    # Communication
    beta_updates_enabled: bool = Field(default=True, env="BETA_UPDATES_ENABLED")
    feedback_notification_email: Optional[str] = Field(default=None, env="FEEDBACK_NOTIFICATION_EMAIL")
    
    # Security
    api_key_header: str = Field(default="X-API-Key", env="API_KEY_HEADER")
    jwt_secret_key: str = Field(default="your-secret-key-here", env="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_expiration_minutes: int = Field(default=60, env="JWT_EXPIRATION_MINUTES")
    
    # External services
    user_service_url: str = Field(default="http://user-management:8002", env="USER_SERVICE_URL")
    notification_service_url: str = Field(default="http://notification:8015", env="NOTIFICATION_SERVICE_URL")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()