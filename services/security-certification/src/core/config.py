"""
Configuration for Security Certification Service.
"""
from typing import Optional, List
from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Security certification service configuration."""
    
    # Service configuration
    service_name: str = Field(default="security-certification", env="SERVICE_NAME")
    service_port: int = Field(default=8010, env="SERVICE_PORT")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    debug: bool = Field(default=False, env="DEBUG")
    
    # Database configuration
    database_url: str = Field(..., env="DATABASE_URL")
    mongodb_url: Optional[str] = Field(None, env="MONGODB_URL")
    redis_url: str = Field(..., env="REDIS_URL")
    
    # Security configuration
    jwt_secret_key: str = Field(..., env="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_expiration_minutes: int = Field(default=60, env="JWT_EXPIRATION_MINUTES")
    
    # External security tools
    nmap_path: str = Field(default="/usr/bin/nmap", env="NMAP_PATH")
    openvas_host: Optional[str] = Field(None, env="OPENVAS_HOST")
    openvas_port: int = Field(default=9390, env="OPENVAS_PORT")
    openvas_username: Optional[str] = Field(None, env="OPENVAS_USERNAME")
    openvas_password: Optional[str] = Field(None, env="OPENVAS_PASSWORD")
    
    # Security scanning configuration
    max_scan_targets: int = Field(default=50, env="MAX_SCAN_TARGETS")
    scan_timeout_minutes: int = Field(default=120, env="SCAN_TIMEOUT_MINUTES")
    max_concurrent_scans: int = Field(default=5, env="MAX_CONCURRENT_SCANS")
    
    # SSL/TLS configuration
    ssl_verify: bool = Field(default=True, env="SSL_VERIFY")
    ssl_cert_check_enabled: bool = Field(default=True, env="SSL_CERT_CHECK_ENABLED")
    
    # Compliance configuration
    compliance_cache_ttl: int = Field(default=3600, env="COMPLIANCE_CACHE_TTL")  # 1 hour
    audit_retention_days: int = Field(default=2555, env="AUDIT_RETENTION_DAYS")  # 7 years
    
    # Report generation
    report_storage_path: str = Field(default="/tmp/security-reports", env="REPORT_STORAGE_PATH")
    max_report_size_mb: int = Field(default=100, env="MAX_REPORT_SIZE_MB")
    
    # Notification configuration
    notification_webhook_url: Optional[str] = Field(None, env="NOTIFICATION_WEBHOOK_URL")
    email_smtp_host: Optional[str] = Field(None, env="EMAIL_SMTP_HOST")
    email_smtp_port: int = Field(default=587, env="EMAIL_SMTP_PORT")
    email_username: Optional[str] = Field(None, env="EMAIL_USERNAME")
    email_password: Optional[str] = Field(None, env="EMAIL_PASSWORD")
    
    # External integrations
    vulnerability_db_url: str = Field(
        default="https://cve.circl.lu/api/",
        env="VULNERABILITY_DB_URL"
    )
    security_advisories_url: str = Field(
        default="https://api.github.com/advisories",
        env="SECURITY_ADVISORIES_URL"
    )
    
    # Rate limiting
    rate_limit_per_minute: int = Field(default=100, env="RATE_LIMIT_PER_MINUTE")
    rate_limit_burst: int = Field(default=200, env="RATE_LIMIT_BURST")
    
    # Feature flags
    enable_automated_scanning: bool = Field(default=True, env="ENABLE_AUTOMATED_SCANNING")
    enable_vulnerability_correlation: bool = Field(default=True, env="ENABLE_VULN_CORRELATION")
    enable_compliance_automation: bool = Field(default=True, env="ENABLE_COMPLIANCE_AUTOMATION")
    enable_risk_scoring: bool = Field(default=True, env="ENABLE_RISK_SCORING")
    
    # Advanced security features
    enable_threat_intelligence: bool = Field(default=False, env="ENABLE_THREAT_INTELLIGENCE")
    threat_intel_api_key: Optional[str] = Field(None, env="THREAT_INTEL_API_KEY")
    enable_devsecops_integration: bool = Field(default=True, env="ENABLE_DEVSECOPS")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()