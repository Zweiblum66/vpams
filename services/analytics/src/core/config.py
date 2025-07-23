"""
Analytics Service Configuration
"""

import os
from typing import List, Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configuration settings for the analytics service."""
    
    # Service settings
    SERVICE_NAME: str = "analytics"
    DEBUG: bool = False
    
    # Database settings
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://mams:mams_password@postgres:5432/mams_analytics"
    )
    
    # Redis settings (for caching and real-time data)
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
    
    # ClickHouse settings (for analytics data warehouse)
    CLICKHOUSE_URL: str = os.getenv(
        "CLICKHOUSE_URL",
        "clickhouse://default:@clickhouse:9000/mams_analytics"
    )
    
    # TimescaleDB settings (for time-series data)
    TIMESCALE_URL: str = os.getenv(
        "TIMESCALE_URL",
        "postgresql+asyncpg://mams:mams_password@timescaledb:5432/mams_timeseries"
    )
    
    # CORS settings
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8080",
        "https://mams.local",
        "https://*.mams.local"
    ]
    
    # Analytics settings
    ANALYTICS_BATCH_SIZE: int = 1000
    ANALYTICS_BATCH_INTERVAL: int = 300  # 5 minutes
    RETENTION_DAYS_RAW: int = 90
    RETENTION_DAYS_AGGREGATED: int = 365 * 2  # 2 years
    
    # Data collection settings
    TRACK_USER_SESSIONS: bool = True
    TRACK_API_CALLS: bool = True
    TRACK_ASSET_INTERACTIONS: bool = True
    TRACK_SEARCH_QUERIES: bool = True
    TRACK_WORKFLOW_EXECUTIONS: bool = True
    
    # Real-time analytics
    ENABLE_REAL_TIME_ANALYTICS: bool = True
    REAL_TIME_WINDOW_SIZE: int = 3600  # 1 hour
    
    # Report generation
    ENABLE_SCHEDULED_REPORTS: bool = True
    REPORT_GENERATION_INTERVAL: int = 3600  # 1 hour
    
    # Data privacy settings
    ANONYMIZE_USER_DATA: bool = False
    GDPR_COMPLIANCE_MODE: bool = False
    DATA_RETENTION_POLICY: str = "standard"  # standard, strict, minimal
    
    # Performance settings
    MAX_CONCURRENT_QUERIES: int = 10
    QUERY_TIMEOUT_SECONDS: int = 30
    CACHE_TTL_SECONDS: int = 300  # 5 minutes
    
    # External integrations
    GRAFANA_URL: Optional[str] = os.getenv("GRAFANA_URL")
    GRAFANA_API_KEY: Optional[str] = os.getenv("GRAFANA_API_KEY")
    
    # Alerting
    ENABLE_ANALYTICS_ALERTS: bool = True
    ALERT_THRESHOLDS: dict = {
        "high_error_rate": 0.05,  # 5%
        "low_user_activity": 0.1,  # 90% decrease
        "storage_usage_warning": 0.8,  # 80%
        "performance_degradation": 2.0  # 2x slower than baseline
    }
    
    # Export settings
    ENABLE_DATA_EXPORT: bool = True
    MAX_EXPORT_ROWS: int = 1000000
    EXPORT_FORMATS: List[str] = ["csv", "json", "parquet"]
    
    # Machine learning settings
    ENABLE_ML_FEATURES: bool = True
    ML_MODEL_UPDATE_INTERVAL: int = 86400  # 24 hours
    PREDICTION_HORIZON_DAYS: int = 30
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()