"""
Configuration for SLA Management Service.
"""
from typing import Optional, List
from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """SLA management service configuration."""
    
    # Service configuration
    service_name: str = Field(default="sla-management", env="SERVICE_NAME")
    service_port: int = Field(default=8011, env="SERVICE_PORT")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    debug: bool = Field(default=False, env="DEBUG")
    
    # Database configuration
    database_url: str = Field(..., env="DATABASE_URL")
    redis_url: str = Field(..., env="REDIS_URL")
    
    # Security configuration
    jwt_secret_key: str = Field(..., env="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_expiration_minutes: int = Field(default=60, env="JWT_EXPIRATION_MINUTES")
    
    # SLA monitoring configuration
    monitoring_interval_minutes: int = Field(default=5, env="MONITORING_INTERVAL_MINUTES")
    compliance_calculation_schedule: str = Field(default="0 1 * * *", env="COMPLIANCE_SCHEDULE")  # Daily at 1 AM
    max_concurrent_calculations: int = Field(default=10, env="MAX_CONCURRENT_CALCULATIONS")
    
    # Notification configuration
    email_smtp_host: Optional[str] = Field(None, env="EMAIL_SMTP_HOST")
    email_smtp_port: int = Field(default=587, env="EMAIL_SMTP_PORT")
    email_username: Optional[str] = Field(None, env="EMAIL_USERNAME")
    email_password: Optional[str] = Field(None, env="EMAIL_PASSWORD")
    email_from_address: str = Field(default="noreply@mams.example.com", env="EMAIL_FROM_ADDRESS")
    
    # Webhook configuration
    webhook_timeout_seconds: int = Field(default=30, env="WEBHOOK_TIMEOUT_SECONDS")
    webhook_retry_attempts: int = Field(default=3, env="WEBHOOK_RETRY_ATTEMPTS")
    webhook_retry_delay_seconds: int = Field(default=60, env="WEBHOOK_RETRY_DELAY_SECONDS")
    
    # Slack integration
    slack_bot_token: Optional[str] = Field(None, env="SLACK_BOT_TOKEN")
    slack_webhook_url: Optional[str] = Field(None, env="SLACK_WEBHOOK_URL")
    
    # SMS configuration
    sms_provider: str = Field(default="twilio", env="SMS_PROVIDER")
    twilio_account_sid: Optional[str] = Field(None, env="TWILIO_ACCOUNT_SID")
    twilio_auth_token: Optional[str] = Field(None, env="TWILIO_AUTH_TOKEN")
    twilio_from_number: Optional[str] = Field(None, env="TWILIO_FROM_NUMBER")
    
    # Penalty calculation
    penalty_calculation_enabled: bool = Field(default=True, env="PENALTY_CALCULATION_ENABLED")
    penalty_auto_apply: bool = Field(default=False, env="PENALTY_AUTO_APPLY")
    penalty_approval_required: bool = Field(default=True, env="PENALTY_APPROVAL_REQUIRED")
    max_penalty_per_agreement: float = Field(default=100.0, env="MAX_PENALTY_PER_AGREEMENT")
    
    # Data retention
    metric_data_retention_days: int = Field(default=2555, env="METRIC_DATA_RETENTION_DAYS")  # 7 years
    compliance_record_retention_days: int = Field(default=2555, env="COMPLIANCE_RETENTION_DAYS")
    notification_log_retention_days: int = Field(default=365, env="NOTIFICATION_LOG_RETENTION_DAYS")
    
    # Performance settings
    metric_calculation_batch_size: int = Field(default=100, env="METRIC_CALCULATION_BATCH_SIZE")
    compliance_calculation_timeout_minutes: int = Field(default=30, env="COMPLIANCE_CALCULATION_TIMEOUT")
    notification_batch_size: int = Field(default=50, env="NOTIFICATION_BATCH_SIZE")
    
    # Rate limiting
    rate_limit_per_minute: int = Field(default=100, env="RATE_LIMIT_PER_MINUTE")
    rate_limit_burst: int = Field(default=200, env="RATE_LIMIT_BURST")
    
    # Caching
    cache_ttl_seconds: int = Field(default=300, env="CACHE_TTL_SECONDS")  # 5 minutes
    compliance_cache_ttl_seconds: int = Field(default=3600, env="COMPLIANCE_CACHE_TTL")  # 1 hour
    
    # External integrations
    metrics_collection_api_url: Optional[str] = Field(None, env="METRICS_COLLECTION_API_URL")
    metrics_collection_api_key: Optional[str] = Field(None, env="METRICS_COLLECTION_API_KEY")
    billing_system_api_url: Optional[str] = Field(None, env="BILLING_SYSTEM_API_URL")
    billing_system_api_key: Optional[str] = Field(None, env="BILLING_SYSTEM_API_KEY")
    
    # Monitoring and alerting
    prometheus_metrics_enabled: bool = Field(default=True, env="PROMETHEUS_METRICS_ENABLED")
    health_check_interval_seconds: int = Field(default=30, env="HEALTH_CHECK_INTERVAL")
    
    # Feature flags
    enable_predictive_analysis: bool = Field(default=False, env="ENABLE_PREDICTIVE_ANALYSIS")
    enable_automated_escalation: bool = Field(default=True, env="ENABLE_AUTOMATED_ESCALATION")
    enable_compliance_forecasting: bool = Field(default=False, env="ENABLE_COMPLIANCE_FORECASTING")
    enable_custom_metrics: bool = Field(default=True, env="ENABLE_CUSTOM_METRICS")
    
    # SLA templates configuration
    allow_custom_sla_creation: bool = Field(default=True, env="ALLOW_CUSTOM_SLA_CREATION")
    require_legal_approval: bool = Field(default=True, env="REQUIRE_LEGAL_APPROVAL")
    max_custom_metrics_per_sla: int = Field(default=20, env="MAX_CUSTOM_METRICS_PER_SLA")
    max_custom_penalties_per_sla: int = Field(default=10, env="MAX_CUSTOM_PENALTIES_PER_SLA")
    
    # Reporting
    report_generation_enabled: bool = Field(default=True, env="REPORT_GENERATION_ENABLED")
    report_storage_path: str = Field(default="/tmp/sla-reports", env="REPORT_STORAGE_PATH")
    max_report_size_mb: int = Field(default=50, env="MAX_REPORT_SIZE_MB")
    report_retention_days: int = Field(default=90, env="REPORT_RETENTION_DAYS")
    
    # Advanced features
    ai_powered_insights_enabled: bool = Field(default=False, env="AI_POWERED_INSIGHTS_ENABLED")
    anomaly_detection_enabled: bool = Field(default=False, env="ANOMALY_DETECTION_ENABLED")
    trend_analysis_enabled: bool = Field(default=True, env="TREND_ANALYSIS_ENABLED")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()