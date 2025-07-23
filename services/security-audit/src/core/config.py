"""
Configuration for Security Audit Service
"""

from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings"""
    
    # Service configuration
    service_name: str = Field(default="security-audit", env="SERVICE_NAME")
    service_port: int = Field(default=8021, env="SERVICE_PORT")
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost/mams_security",
        env="DATABASE_URL"
    )
    
    # Redis
    redis_url: str = Field(
        default="redis://localhost:6379/3",
        env="REDIS_URL"
    )
    
    # Security scanning configuration
    scan_interval_minutes: int = Field(default=60, env="SCAN_INTERVAL_MINUTES")
    max_concurrent_scans: int = Field(default=5, env="MAX_CONCURRENT_SCANS")
    scan_timeout_seconds: int = Field(default=300, env="SCAN_TIMEOUT_SECONDS")
    
    # OWASP ZAP configuration
    zap_api_key: Optional[str] = Field(default=None, env="ZAP_API_KEY")
    zap_proxy_host: str = Field(default="localhost", env="ZAP_PROXY_HOST")
    zap_proxy_port: int = Field(default=8080, env="ZAP_PROXY_PORT")
    
    # Network scanning
    network_scan_enabled: bool = Field(default=True, env="NETWORK_SCAN_ENABLED")
    network_subnets: List[str] = Field(
        default=["192.168.1.0/24"],
        env="NETWORK_SUBNETS"
    )
    
    # Compliance standards
    enable_iso27001: bool = Field(default=True, env="ENABLE_ISO27001")
    enable_gdpr: bool = Field(default=True, env="ENABLE_GDPR")
    enable_soc2: bool = Field(default=True, env="ENABLE_SOC2")
    enable_pci_dss: bool = Field(default=False, env="ENABLE_PCI_DSS")
    
    # Vulnerability database
    nvd_api_key: Optional[str] = Field(default=None, env="NVD_API_KEY")
    cve_feed_url: str = Field(
        default="https://nvd.nist.gov/feeds/json/cve/1.1/nvdcve-1.1-recent.json.gz",
        env="CVE_FEED_URL"
    )
    
    # Alerting
    alert_webhook_url: Optional[str] = Field(default=None, env="ALERT_WEBHOOK_URL")
    alert_email: Optional[str] = Field(default=None, env="ALERT_EMAIL")
    critical_severity_threshold: float = Field(default=9.0, env="CRITICAL_SEVERITY_THRESHOLD")
    high_severity_threshold: float = Field(default=7.0, env="HIGH_SEVERITY_THRESHOLD")
    
    # API Security
    api_key_header: str = Field(default="X-API-Key", env="API_KEY_HEADER")
    jwt_secret_key: str = Field(default="your-secret-key", env="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    
    # Service URLs
    user_service_url: str = Field(
        default="http://user-management:8002",
        env="USER_SERVICE_URL"
    )
    asset_service_url: str = Field(
        default="http://asset-management:8003",
        env="ASSET_SERVICE_URL"
    )
    api_gateway_url: str = Field(
        default="http://api-gateway:8000",
        env="API_GATEWAY_URL"
    )
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings"""
    return settings