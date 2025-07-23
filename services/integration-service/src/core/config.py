"""
Configuration settings for the Integration Service
"""

from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """
    Service configuration settings
    """
    # Service info
    SERVICE_NAME: str = "integration-service"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = Field("development", env="ENVIRONMENT")
    DEBUG: bool = Field(True, env="DEBUG")
    PORT: int = Field(8011, env="SERVICE_PORT")
    
    # Database
    DATABASE_URL: str = Field(
        "postgresql+asyncpg://mams:mams@postgres:5432/mams_integration",
        env="DATABASE_URL"
    )
    
    # Redis
    REDIS_URL: str = Field("redis://redis:6379/0", env="REDIS_URL")
    
    # CORS
    ALLOWED_ORIGINS: List[str] = Field(
        ["http://localhost:3000", "http://localhost:8000"],
        env="ALLOWED_ORIGINS"
    )
    
    # Authentication
    JWT_SECRET_KEY: str = Field("your-secret-key-here", env="JWT_SECRET_KEY")
    JWT_ALGORITHM: str = Field("HS256", env="JWT_ALGORITHM")
    JWT_EXPIRATION_MINUTES: int = Field(60, env="JWT_EXPIRATION_MINUTES")
    
    # Integration specific settings
    WEBHOOK_TIMEOUT: int = Field(30, env="WEBHOOK_TIMEOUT")
    WEBHOOK_RETRY_COUNT: int = Field(3, env="WEBHOOK_RETRY_COUNT")
    WEBHOOK_RETRY_DELAY: int = Field(1, env="WEBHOOK_RETRY_DELAY")
    
    # Slack integration
    SLACK_CLIENT_ID: Optional[str] = Field(None, env="SLACK_CLIENT_ID")
    SLACK_CLIENT_SECRET: Optional[str] = Field(None, env="SLACK_CLIENT_SECRET")
    SLACK_SIGNING_SECRET: Optional[str] = Field(None, env="SLACK_SIGNING_SECRET")
    
    # Microsoft Teams integration
    TEAMS_APP_ID: Optional[str] = Field(None, env="TEAMS_APP_ID")
    TEAMS_APP_PASSWORD: Optional[str] = Field(None, env="TEAMS_APP_PASSWORD")
    
    # Rate limiting
    RATE_LIMIT_ENABLED: bool = Field(True, env="RATE_LIMIT_ENABLED")
    RATE_LIMIT_PER_MINUTE: int = Field(60, env="RATE_LIMIT_PER_MINUTE")
    
    # Encryption for sensitive data
    ENCRYPTION_KEY: str = Field(
        "your-encryption-key-here-32-chars",
        env="ENCRYPTION_KEY"
    )
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()