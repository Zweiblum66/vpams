"""
Configuration settings for Onboarding Service
"""
from pydantic import BaseSettings, Field, validator
from typing import List, Optional
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings"""
    
    # Service info
    SERVICE_NAME: str = "onboarding-service"
    SERVICE_VERSION: str = "1.0.0"
    DEBUG: bool = Field(False, env="DEBUG")
    
    # Server
    HOST: str = Field("0.0.0.0", env="HOST")
    PORT: int = Field(8019, env="PORT")
    WORKERS: int = Field(4, env="WORKERS")
    
    # Database
    DATABASE_URL: str = Field(..., env="DATABASE_URL")
    DATABASE_POOL_SIZE: int = Field(10, env="DATABASE_POOL_SIZE")
    DATABASE_MAX_OVERFLOW: int = Field(5, env="DATABASE_MAX_OVERFLOW")
    
    # Redis
    REDIS_URL: str = Field(..., env="REDIS_URL")
    REDIS_MAX_CONNECTIONS: int = Field(50, env="REDIS_MAX_CONNECTIONS")
    
    # Security
    SECRET_KEY: str = Field(..., env="SECRET_KEY")
    ALGORITHM: str = Field("HS256", env="ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(60, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    
    # CORS
    ALLOWED_ORIGINS: List[str] = Field(
        ["http://localhost:3000", "http://localhost:3001"],
        env="ALLOWED_ORIGINS"
    )
    
    # Analytics
    ANALYTICS_ENABLED: bool = Field(True, env="ANALYTICS_ENABLED")
    SEGMENT_WRITE_KEY: Optional[str] = Field(None, env="SEGMENT_WRITE_KEY")
    
    # Features
    ENABLE_VIDEO_TUTORIALS: bool = Field(True, env="ENABLE_VIDEO_TUTORIALS")
    ENABLE_INTERACTIVE_GUIDES: bool = Field(True, env="ENABLE_INTERACTIVE_GUIDES")
    ENABLE_PRACTICE_MODE: bool = Field(True, env="ENABLE_PRACTICE_MODE")
    ENABLE_CERTIFICATIONS: bool = Field(True, env="ENABLE_CERTIFICATIONS")
    
    # Onboarding defaults
    DEFAULT_FLOW_DURATION_MINUTES: int = Field(30, env="DEFAULT_FLOW_DURATION_MINUTES")
    MAX_SKIP_PERCENTAGE: float = Field(0.3, env="MAX_SKIP_PERCENTAGE")  # 30% of steps can be skipped
    ACHIEVEMENT_CHECK_INTERVAL: int = Field(300, env="ACHIEVEMENT_CHECK_INTERVAL")  # 5 minutes
    
    # External services
    USER_SERVICE_URL: str = Field("http://user-management:8001", env="USER_SERVICE_URL")
    ASSET_SERVICE_URL: str = Field("http://asset-management:8004", env="ASSET_SERVICE_URL")
    NOTIFICATION_SERVICE_URL: str = Field("http://notification:8016", env="NOTIFICATION_SERVICE_URL")
    
    # Logging
    LOG_LEVEL: str = Field("INFO", env="LOG_LEVEL")
    LOG_FORMAT: str = Field("json", env="LOG_FORMAT")
    
    # Monitoring
    SENTRY_DSN: Optional[str] = Field(None, env="SENTRY_DSN")
    
    @validator("ALLOWED_ORIGINS", pre=True)
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @validator("DATABASE_URL")
    def validate_database_url(cls, v):
        if not v.startswith(("postgresql://", "postgresql+asyncpg://")):
            raise ValueError("DATABASE_URL must be a PostgreSQL URL")
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


settings = get_settings()