"""Configuration settings for Multi-Tenant Service."""

from pydantic import Field
from pydantic_settings import BaseSettings
from typing import List, Optional, Dict, Any
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings."""
    
    # Service configuration
    service_name: str = Field(default="multi-tenant", env="SERVICE_NAME")
    service_port: int = Field(default=8026, env="SERVICE_PORT")
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Database configuration
    database_url: str = Field(env="DATABASE_URL")
    
    # Redis configuration
    redis_url: str = Field(default="redis://localhost:6379/8", env="REDIS_URL")
    
    # Multi-tenancy settings
    multi_tenancy_enabled: bool = Field(default=True, env="MULTI_TENANCY_ENABLED")
    tenant_isolation_mode: str = Field(default="schema", env="TENANT_ISOLATION_MODE")  # schema, database, hybrid
    
    # Tenant management
    max_tenants_per_instance: int = Field(default=1000, env="MAX_TENANTS_PER_INSTANCE")
    default_tenant_quota: Dict[str, Any] = Field(
        default={
            "max_users": 100,
            "max_storage_gb": 1000,
            "max_assets": 100000,
            "max_projects": 1000,
            "max_api_calls_per_hour": 10000
        },
        env="DEFAULT_TENANT_QUOTA"
    )
    
    # Database isolation
    tenant_db_prefix: str = Field(default="mams_tenant_", env="TENANT_DB_PREFIX")
    tenant_schema_prefix: str = Field(default="tenant_", env="TENANT_SCHEMA_PREFIX")
    shared_schema_name: str = Field(default="public", env="SHARED_SCHEMA_NAME")
    
    # Custom domains
    custom_domains_enabled: bool = Field(default=True, env="CUSTOM_DOMAINS_ENABLED")
    domain_verification_enabled: bool = Field(default=True, env="DOMAIN_VERIFICATION_ENABLED")
    domain_ssl_auto_provision: bool = Field(default=True, env="DOMAIN_SSL_AUTO_PROVISION")
    
    # Tenant configuration
    allow_tenant_customization: bool = Field(default=True, env="ALLOW_TENANT_CUSTOMIZATION")
    tenant_config_options: List[str] = Field(
        default=[
            "branding", "theme", "language", "timezone",
            "storage_settings", "workflow_settings",
            "user_settings", "security_settings"
        ],
        env="TENANT_CONFIG_OPTIONS"
    )
    
    # Resource limits
    tenant_resource_limits: Dict[str, Any] = Field(
        default={
            "cpu_cores": 4,
            "memory_gb": 16,
            "concurrent_users": 100,
            "api_rate_limit": 1000,
            "storage_bandwidth_mbps": 1000
        },
        env="TENANT_RESOURCE_LIMITS"
    )
    
    # Billing and metering
    billing_enabled: bool = Field(default=True, env="BILLING_ENABLED")
    usage_tracking_enabled: bool = Field(default=True, env="USAGE_TRACKING_ENABLED")
    billing_metrics: List[str] = Field(
        default=[
            "storage_used", "bandwidth_used", "api_calls",
            "active_users", "compute_hours", "ai_processing"
        ],
        env="BILLING_METRICS"
    )
    
    # Tenant lifecycle
    tenant_provisioning_timeout: int = Field(default=300, env="TENANT_PROVISIONING_TIMEOUT")  # seconds
    tenant_deletion_grace_period: int = Field(default=30, env="TENANT_DELETION_GRACE_PERIOD")  # days
    tenant_backup_enabled: bool = Field(default=True, env="TENANT_BACKUP_ENABLED")
    tenant_backup_retention_days: int = Field(default=90, env="TENANT_BACKUP_RETENTION_DAYS")
    
    # Data isolation
    data_encryption_per_tenant: bool = Field(default=True, env="DATA_ENCRYPTION_PER_TENANT")
    tenant_encryption_key_rotation: int = Field(default=90, env="TENANT_ENCRYPTION_KEY_ROTATION")  # days
    
    # Performance optimization
    tenant_cache_enabled: bool = Field(default=True, env="TENANT_CACHE_ENABLED")
    tenant_cache_ttl: int = Field(default=3600, env="TENANT_CACHE_TTL")  # seconds
    connection_pool_per_tenant: bool = Field(default=True, env="CONNECTION_POOL_PER_TENANT")
    
    # Cross-tenant features
    cross_tenant_sharing_enabled: bool = Field(default=False, env="CROSS_TENANT_SHARING_ENABLED")
    tenant_federation_enabled: bool = Field(default=False, env="TENANT_FEDERATION_ENABLED")
    
    # Monitoring and analytics
    tenant_metrics_enabled: bool = Field(default=True, env="TENANT_METRICS_ENABLED")
    tenant_audit_enabled: bool = Field(default=True, env="TENANT_AUDIT_ENABLED")
    tenant_analytics_retention_days: int = Field(default=365, env="TENANT_ANALYTICS_RETENTION_DAYS")
    
    # Compliance
    data_residency_enabled: bool = Field(default=True, env="DATA_RESIDENCY_ENABLED")
    supported_regions: List[str] = Field(
        default=["us-east", "us-west", "eu-central", "eu-west", "ap-southeast"],
        env="SUPPORTED_REGIONS"
    )
    
    # Tenant templates
    tenant_templates: Dict[str, Any] = Field(
        default={
            "starter": {
                "quota": {"max_users": 10, "max_storage_gb": 100},
                "features": ["basic"]
            },
            "professional": {
                "quota": {"max_users": 100, "max_storage_gb": 1000},
                "features": ["basic", "advanced", "api"]
            },
            "enterprise": {
                "quota": {"max_users": -1, "max_storage_gb": -1},
                "features": ["all"]
            }
        },
        env="TENANT_TEMPLATES"
    )
    
    # Security settings
    tenant_api_key_enabled: bool = Field(default=True, env="TENANT_API_KEY_ENABLED")
    tenant_sso_enabled: bool = Field(default=True, env="TENANT_SSO_ENABLED")
    tenant_ip_whitelist_enabled: bool = Field(default=True, env="TENANT_IP_WHITELIST_ENABLED")
    
    # Integration settings
    webhook_per_tenant: bool = Field(default=True, env="WEBHOOK_PER_TENANT")
    custom_integrations_enabled: bool = Field(default=True, env="CUSTOM_INTEGRATIONS_ENABLED")
    
    # Database management
    auto_vacuum_enabled: bool = Field(default=True, env="AUTO_VACUUM_ENABLED")
    vacuum_schedule: str = Field(default="0 3 * * *", env="VACUUM_SCHEDULE")  # cron format
    
    # Performance settings
    max_concurrent_operations: int = Field(default=100, env="MAX_CONCURRENT_OPERATIONS")
    operation_timeout: int = Field(default=3600, env="OPERATION_TIMEOUT")  # seconds
    
    # Security settings
    allowed_origins: List[str] = Field(default=["http://localhost:3000"], env="ALLOWED_ORIGINS")
    api_key_header: str = Field(default="X-API-Key", env="API_KEY_HEADER")
    require_auth: bool = Field(default=True, env="REQUIRE_AUTH")
    
    # JWT settings
    jwt_secret_key: str = Field(env="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_expiration_minutes: int = Field(default=60, env="JWT_EXPIRATION_MINUTES")
    
    # Rate limiting
    rate_limit_enabled: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
    global_rate_limit: int = Field(default=10000, env="GLOBAL_RATE_LIMIT")  # per hour
    
    # Data retention
    tenant_data_retention_days: int = Field(default=2555, env="TENANT_DATA_RETENTION_DAYS")  # 7 years
    audit_log_retention_days: int = Field(default=2555, env="AUDIT_LOG_RETENTION_DAYS")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()