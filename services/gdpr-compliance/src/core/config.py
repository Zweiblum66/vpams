"""Configuration settings for GDPR Compliance Service"""

from typing import Optional, List
from pydantic import Field, validator
from pydantic_settings import BaseSettings
from datetime import timedelta


class Settings(BaseSettings):
    """GDPR Compliance Service configuration"""
    
    # Service Configuration
    service_name: str = "gdpr-compliance"
    service_version: str = "1.0.0"
    debug: bool = False
    
    # Database Configuration
    database_url: str = Field(..., env="DATABASE_URL")
    mongodb_url: str = Field(..., env="MONGODB_URL")
    redis_url: str = Field(..., env="REDIS_URL")
    
    # GDPR Configuration
    gdpr_data_retention_days: int = Field(2555, env="GDPR_DATA_RETENTION_DAYS")  # 7 years default
    gdpr_export_timeout_minutes: int = Field(60, env="GDPR_EXPORT_TIMEOUT_MINUTES")
    gdpr_deletion_grace_period_days: int = Field(30, env="GDPR_DELETION_GRACE_PERIOD_DAYS")
    gdpr_anonymization_enabled: bool = Field(True, env="GDPR_ANONYMIZATION_ENABLED")
    gdpr_export_formats: List[str] = Field(
        default_factory=lambda: ["json", "csv", "pdf"],
        env="GDPR_EXPORT_FORMATS"
    )
    
    # Privacy Configuration
    privacy_default_consent: bool = Field(False, env="PRIVACY_DEFAULT_CONSENT")
    privacy_policy_version: str = Field("1.0", env="PRIVACY_POLICY_VERSION")
    privacy_cookie_expiry_days: int = Field(365, env="PRIVACY_COOKIE_EXPIRY_DAYS")
    
    # Email Configuration
    smtp_host: str = Field("localhost", env="SMTP_HOST")
    smtp_port: int = Field(587, env="SMTP_PORT")
    smtp_username: Optional[str] = Field(None, env="SMTP_USERNAME")
    smtp_password: Optional[str] = Field(None, env="SMTP_PASSWORD")
    smtp_use_tls: bool = Field(True, env="SMTP_USE_TLS")
    smtp_from_email: str = Field("privacy@mams.local", env="SMTP_FROM_EMAIL")
    
    # Storage Configuration
    export_storage_path: str = Field("/app/exports", env="EXPORT_STORAGE_PATH")
    temp_storage_path: str = Field("/tmp/gdpr", env="TEMP_STORAGE_PATH")
    export_retention_days: int = Field(7, env="EXPORT_RETENTION_DAYS")
    
    # Security Configuration
    encryption_key: Optional[str] = Field(None, env="ENCRYPTION_KEY")
    anonymization_salt: Optional[str] = Field(None, env="ANONYMIZATION_SALT")
    
    # Logging Configuration
    log_level: str = Field("INFO", env="LOG_LEVEL")
    log_format: str = "json"
    audit_log_enabled: bool = Field(True, env="AUDIT_LOG_ENABLED")
    
    # Rate Limiting
    rate_limit_requests_per_minute: int = Field(60, env="RATE_LIMIT_REQUESTS_PER_MINUTE")
    rate_limit_exports_per_day: int = Field(10, env="RATE_LIMIT_EXPORTS_PER_DAY")
    
    # Notification Settings
    notification_email_enabled: bool = Field(True, env="NOTIFICATION_EMAIL_ENABLED")
    notification_webhook_enabled: bool = Field(False, env="NOTIFICATION_WEBHOOK_ENABLED")
    notification_webhook_url: Optional[str] = Field(None, env="NOTIFICATION_WEBHOOK_URL")
    
    # Retention scheduler settings
    retention_scheduler_interval_minutes: int = Field(60, env="RETENTION_SCHEDULER_INTERVAL_MINUTES")
    
    class Config:
        env_file = ".env"
        case_sensitive = False
    
    @validator("gdpr_data_retention_days")
    def validate_retention_days(cls, v):
        if v < 0:
            raise ValueError("Data retention days must be non-negative")
        return v
    
    @validator("gdpr_deletion_grace_period_days")
    def validate_grace_period(cls, v):
        if v < 1 or v > 90:
            raise ValueError("Deletion grace period must be between 1 and 90 days")
        return v
    
    @validator("log_level")
    def validate_log_level(cls, v):
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of: {valid_levels}")
        return v.upper()
    
    @validator("gdpr_export_formats")
    def validate_export_formats(cls, v):
        valid_formats = ["json", "csv", "xml", "pdf", "excel"]
        for format in v:
            if format not in valid_formats:
                raise ValueError(f"Export format must be one of: {valid_formats}")
        return v
    
    @property
    def export_timeout(self) -> timedelta:
        """Get export timeout as timedelta"""
        return timedelta(minutes=self.gdpr_export_timeout_minutes)
    
    @property
    def deletion_grace_period(self) -> timedelta:
        """Get deletion grace period as timedelta"""
        return timedelta(days=self.gdpr_deletion_grace_period_days)
    
    @property
    def retention_period(self) -> timedelta:
        """Get data retention period as timedelta"""
        return timedelta(days=self.gdpr_data_retention_days)


# Global settings instance
settings = Settings()