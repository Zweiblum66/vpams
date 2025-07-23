"""
Configuration settings for Billing Service
"""
from pydantic import BaseSettings, Field, validator
from typing import List, Optional
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings"""
    
    # Service info
    SERVICE_NAME: str = "billing-service"
    SERVICE_VERSION: str = "1.0.0"
    DEBUG: bool = Field(False, env="DEBUG")
    
    # Server
    HOST: str = Field("0.0.0.0", env="HOST")
    PORT: int = Field(8015, env="PORT")
    WORKERS: int = Field(4, env="WORKERS")
    
    # Database
    DATABASE_URL: str = Field(..., env="DATABASE_URL")
    DATABASE_POOL_SIZE: int = Field(20, env="DATABASE_POOL_SIZE")
    DATABASE_MAX_OVERFLOW: int = Field(10, env="DATABASE_MAX_OVERFLOW")
    
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
    
    # Stripe
    STRIPE_SECRET_KEY: Optional[str] = Field(None, env="STRIPE_SECRET_KEY")
    STRIPE_WEBHOOK_SECRET: Optional[str] = Field(None, env="STRIPE_WEBHOOK_SECRET")
    STRIPE_PUBLISHABLE_KEY: Optional[str] = Field(None, env="STRIPE_PUBLISHABLE_KEY")
    
    # PayPal
    PAYPAL_CLIENT_ID: Optional[str] = Field(None, env="PAYPAL_CLIENT_ID")
    PAYPAL_CLIENT_SECRET: Optional[str] = Field(None, env="PAYPAL_CLIENT_SECRET")
    PAYPAL_WEBHOOK_ID: Optional[str] = Field(None, env="PAYPAL_WEBHOOK_ID")
    PAYPAL_MODE: str = Field("sandbox", env="PAYPAL_MODE")  # sandbox or live
    
    # Tax services
    TAXJAR_API_KEY: Optional[str] = Field(None, env="TAXJAR_API_KEY")
    AVALARA_ACCOUNT_ID: Optional[str] = Field(None, env="AVALARA_ACCOUNT_ID")
    AVALARA_LICENSE_KEY: Optional[str] = Field(None, env="AVALARA_LICENSE_KEY")
    
    # Email
    SMTP_HOST: str = Field("localhost", env="SMTP_HOST")
    SMTP_PORT: int = Field(587, env="SMTP_PORT")
    SMTP_USER: Optional[str] = Field(None, env="SMTP_USER")
    SMTP_PASSWORD: Optional[str] = Field(None, env="SMTP_PASSWORD")
    SMTP_TLS: bool = Field(True, env="SMTP_TLS")
    EMAIL_FROM: str = Field("billing@mams.io", env="EMAIL_FROM")
    
    # Features
    ENABLE_USAGE_BILLING: bool = Field(True, env="ENABLE_USAGE_BILLING")
    ENABLE_MULTI_CURRENCY: bool = Field(True, env="ENABLE_MULTI_CURRENCY")
    ENABLE_TAX_CALCULATION: bool = Field(True, env="ENABLE_TAX_CALCULATION")
    ENABLE_DUNNING: bool = Field(True, env="ENABLE_DUNNING")
    ENABLE_METRICS: bool = Field(True, env="ENABLE_METRICS")
    
    # Webhooks
    WEBHOOK_RETRY_COUNT: int = Field(3, env="WEBHOOK_RETRY_COUNT")
    WEBHOOK_TIMEOUT: int = Field(30, env="WEBHOOK_TIMEOUT")
    WEBHOOK_SECRET: str = Field(..., env="WEBHOOK_SECRET")
    
    # Logging
    LOG_LEVEL: str = Field("INFO", env="LOG_LEVEL")
    LOG_FORMAT: str = Field("json", env="LOG_FORMAT")
    
    # Monitoring
    SENTRY_DSN: Optional[str] = Field(None, env="SENTRY_DSN")
    JAEGER_AGENT_HOST: Optional[str] = Field(None, env="JAEGER_AGENT_HOST")
    JAEGER_AGENT_PORT: int = Field(6831, env="JAEGER_AGENT_PORT")
    
    # Rate limiting
    RATE_LIMIT_ENABLED: bool = Field(True, env="RATE_LIMIT_ENABLED")
    RATE_LIMIT_REQUESTS: int = Field(100, env="RATE_LIMIT_REQUESTS")
    RATE_LIMIT_PERIOD: int = Field(60, env="RATE_LIMIT_PERIOD")  # seconds
    
    # Service URLs
    USER_SERVICE_URL: str = Field("http://user-management:8001", env="USER_SERVICE_URL")
    NOTIFICATION_SERVICE_URL: str = Field("http://notification:8016", env="NOTIFICATION_SERVICE_URL")
    
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