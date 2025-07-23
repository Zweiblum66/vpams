"""
Plugin Service Configuration
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional, List


class Settings(BaseSettings):
    """Plugin Service Settings"""
    
    # Service Info
    service_name: str = "plugin-service"
    service_version: str = "1.0.0"
    environment: str = Field("development", env="ENVIRONMENT")
    
    # Server
    service_port: int = Field(8013, env="SERVICE_PORT")
    workers: int = Field(4, env="WORKERS")
    
    # Plugin Settings
    plugins_dir: str = Field("/app/plugins", env="PLUGINS_DIR")
    plugin_registry_path: str = Field("/app/plugin_registry.json", env="PLUGIN_REGISTRY_PATH")
    plugin_sandbox_enabled: bool = Field(True, env="PLUGIN_SANDBOX_ENABLED")
    plugin_sandbox_dir: str = Field("/app/sandboxes", env="PLUGIN_SANDBOX_DIR")
    plugin_max_execution_time: int = Field(300, env="PLUGIN_MAX_EXECUTION_TIME")  # seconds
    
    # Plugin Restrictions
    plugin_max_memory_mb: int = Field(512, env="PLUGIN_MAX_MEMORY_MB")
    plugin_max_cpu_percent: int = Field(50, env="PLUGIN_MAX_CPU_PERCENT")
    plugin_allowed_hosts: List[str] = Field(
        ["api.mams.local", "storage.mams.local"],
        env="PLUGIN_ALLOWED_HOSTS"
    )
    
    # Database
    database_url: str = Field(
        "postgresql+asyncpg://mams:mams123@postgres:5432/mams_plugins",
        env="DATABASE_URL"
    )
    
    # Redis
    redis_url: str = Field("redis://redis:6379/0", env="REDIS_URL")
    
    # Storage
    storage_type: str = Field("s3", env="STORAGE_TYPE")
    s3_endpoint: str = Field("http://minio:9000", env="S3_ENDPOINT")
    s3_access_key: str = Field("minioadmin", env="S3_ACCESS_KEY")
    s3_secret_key: str = Field("minioadmin", env="S3_SECRET_KEY")
    s3_bucket: str = Field("mams-plugins", env="S3_BUCKET")
    
    # Security
    plugin_signature_verification: bool = Field(True, env="PLUGIN_SIGNATURE_VERIFICATION")
    plugin_signature_public_key: Optional[str] = Field(None, env="PLUGIN_SIGNATURE_PUBLIC_KEY")
    
    # API Keys
    api_key_header: str = Field("X-API-Key", env="API_KEY_HEADER")
    internal_api_key: str = Field("internal-key-123", env="INTERNAL_API_KEY")
    
    # Logging
    log_level: str = Field("INFO", env="LOG_LEVEL")
    log_format: str = Field("json", env="LOG_FORMAT")
    
    # Metrics
    metrics_enabled: bool = Field(True, env="METRICS_ENABLED")
    metrics_port: int = Field(9090, env="METRICS_PORT")
    
    # Marketplace
    marketplace_enabled: bool = Field(True, env="MARKETPLACE_ENABLED")
    marketplace_featured_plugin_ids: List[str] = Field([], env="MARKETPLACE_FEATURED_PLUGINS")
    marketplace_revenue_share_percent: float = Field(30.0, env="MARKETPLACE_REVENUE_SHARE")
    
    # Developer Portal
    developer_portal_enabled: bool = Field(True, env="DEVELOPER_PORTAL_ENABLED")
    developer_portal_url: str = Field("https://developers.mams.local", env="DEVELOPER_PORTAL_URL")
    
    # Plugin Development
    plugin_dev_mode: bool = Field(False, env="PLUGIN_DEV_MODE")
    plugin_hot_reload: bool = Field(False, env="PLUGIN_HOT_RELOAD")
    
    # Rate Limiting
    rate_limit_enabled: bool = Field(True, env="RATE_LIMIT_ENABLED")
    rate_limit_requests_per_minute: int = Field(60, env="RATE_LIMIT_RPM")
    
    # CORS
    cors_origins: List[str] = Field(
        ["http://localhost:3000", "https://mams.local"],
        env="CORS_ORIGINS"
    )
    
    # Debug
    debug: bool = Field(False, env="DEBUG")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Create settings instance
settings = Settings()