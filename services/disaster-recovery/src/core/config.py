"""
Configuration settings for Disaster Recovery Service
"""

from pydantic_settings import BaseSettings
from typing import List, Optional
import os


class Settings(BaseSettings):
    """Application settings"""
    
    # Service configuration
    SERVICE_NAME: str = "disaster-recovery"
    SERVICE_PORT: int = 8014
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://user:pass@localhost:5432/mams_dr"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/9"
    
    # Storage
    BACKUP_BUCKET: str = "mams-backups"
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: str = "us-east-1"
    
    # Security
    JWT_SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = 60
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8080"]
    
    # Disaster Recovery Settings
    DEFAULT_RTO_CRITICAL_MINUTES: int = 60
    DEFAULT_RTO_HIGH_MINUTES: int = 240
    DEFAULT_RTO_MEDIUM_MINUTES: int = 1440
    DEFAULT_RTO_LOW_MINUTES: int = 4320
    
    DEFAULT_RPO_CRITICAL_MINUTES: int = 15
    DEFAULT_RPO_HIGH_MINUTES: int = 60
    DEFAULT_RPO_MEDIUM_MINUTES: int = 240
    DEFAULT_RPO_LOW_MINUTES: int = 1440
    
    # Backup Settings
    BACKUP_RETENTION_DAYS_DEFAULT: int = 30
    BACKUP_COMPRESSION_ENABLED: bool = True
    BACKUP_ENCRYPTION_ENABLED: bool = True
    BACKUP_VERIFICATION_ENABLED: bool = True
    BACKUP_MAX_CONCURRENT: int = 5
    
    # Failover Settings
    FAILOVER_HEALTH_CHECK_INTERVAL_SECONDS: int = 30
    FAILOVER_AUTO_THRESHOLD_DEFAULT: int = 3
    FAILOVER_NOTIFICATION_CHANNELS: List[str] = ["email", "slack"]
    
    # Recovery Testing
    TEST_ENVIRONMENT_PREFIX: str = "dr-test"
    TEST_DATA_SAMPLE_PERCENTAGE: float = 10.0
    TEST_NOTIFICATION_ENABLED: bool = True
    
    # Monitoring
    MONITORING_ENABLED: bool = True
    METRICS_RETENTION_DAYS: int = 90
    ALERT_THRESHOLD_RTO_PERCENTAGE: float = 80.0
    ALERT_THRESHOLD_RPO_PERCENTAGE: float = 80.0
    
    # Notification Settings
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM_EMAIL: str = "dr-alerts@mams.example.com"
    
    SLACK_WEBHOOK_URL: Optional[str] = None
    TEAMS_WEBHOOK_URL: Optional[str] = None
    PAGERDUTY_API_KEY: Optional[str] = None
    
    # External Services
    PROMETHEUS_METRICS_ENABLED: bool = True
    GRAFANA_API_URL: Optional[str] = None
    GRAFANA_API_KEY: Optional[str] = None
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 100
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Create settings instance
settings = Settings()

# Validate critical settings
if settings.DEBUG:
    import warnings
    warnings.warn("Running in DEBUG mode - not suitable for production!")
    
if settings.JWT_SECRET_KEY == "your-secret-key-change-in-production":
    import warnings
    warnings.warn("Using default JWT secret key - change in production!")