"""Configuration settings for the Reseller Tools Service"""

from pydantic import BaseSettings, Field
from typing import List
import os


class Settings(BaseSettings):
    """Application settings"""
    
    # Service configuration
    service_name: str = "reseller-tools"
    service_version: str = "1.0.0"
    port: int = Field(default=8015, env="SERVICE_PORT")
    debug: bool = Field(default=False, env="DEBUG")
    environment: str = Field(default="development", env="ENVIRONMENT")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Database
    database_url: str = Field(env="DATABASE_URL")
    
    # Redis for caching and sessions
    redis_url: str = Field(default="redis://redis:6379/0", env="REDIS_URL")
    
    # Security
    jwt_secret_key: str = Field(env="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_expiration_minutes: int = Field(default=60, env="JWT_EXPIRATION_MINUTES")
    
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
    
    # Payment processing
    stripe_secret_key: str = Field(default="", env="STRIPE_SECRET_KEY")
    stripe_webhook_secret: str = Field(default="", env="STRIPE_WEBHOOK_SECRET")
    
    # Email settings
    smtp_host: str = Field(default="localhost", env="SMTP_HOST")
    smtp_port: int = Field(default=587, env="SMTP_PORT")
    smtp_username: str = Field(default="", env="SMTP_USERNAME")
    smtp_password: str = Field(default="", env="SMTP_PASSWORD")
    smtp_use_tls: bool = Field(default=True, env="SMTP_USE_TLS")
    
    # External API endpoints
    user_management_url: str = Field(
        default="http://user-management:8002",
        env="USER_MANAGEMENT_URL"
    )
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()