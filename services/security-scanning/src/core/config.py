"""Configuration settings for Security Scanning Service."""

from pydantic import Field
from pydantic_settings import BaseSettings
from typing import List, Optional, Dict, Any
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings."""
    
    # Service configuration
    service_name: str = Field(default="security-scanning", env="SERVICE_NAME")
    service_port: int = Field(default=8024, env="SERVICE_PORT")
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Database configuration
    database_url: str = Field(env="DATABASE_URL")
    
    # Redis configuration
    redis_url: str = Field(default="redis://localhost:6379/6", env="REDIS_URL")
    
    # Scanning configuration
    scanning_enabled: bool = Field(default=True, env="SCANNING_ENABLED")
    max_concurrent_scans: int = Field(default=5, env="MAX_CONCURRENT_SCANS")
    scan_timeout_minutes: int = Field(default=60, env="SCAN_TIMEOUT_MINUTES")
    
    # Network scanning
    network_scan_enabled: bool = Field(default=True, env="NETWORK_SCAN_ENABLED")
    nmap_path: str = Field(default="/usr/bin/nmap", env="NMAP_PATH")
    masscan_path: str = Field(default="/usr/bin/masscan", env="MASSCAN_PATH")
    
    # Web application scanning
    web_scan_enabled: bool = Field(default=True, env="WEB_SCAN_ENABLED")
    nikto_path: str = Field(default="/usr/bin/nikto", env="NIKTO_PATH")
    dirb_path: str = Field(default="/usr/bin/dirb", env="DIRB_PATH")
    sqlmap_path: str = Field(default="/usr/bin/sqlmap", env="SQLMAP_PATH")
    
    # SSL/TLS scanning
    ssl_scan_enabled: bool = Field(default=True, env="SSL_SCAN_ENABLED")
    sslyze_enabled: bool = Field(default=True, env="SSLYZE_ENABLED")
    
    # Vulnerability scanning
    vuln_scan_enabled: bool = Field(default=True, env="VULN_SCAN_ENABLED")
    cve_database_path: str = Field(default="/app/data/cve", env="CVE_DATABASE_PATH")
    
    # Infrastructure scanning
    infra_scan_enabled: bool = Field(default=True, env="INFRA_SCAN_ENABLED")
    docker_scan_enabled: bool = Field(default=True, env="DOCKER_SCAN_ENABLED")
    k8s_scan_enabled: bool = Field(default=True, env="K8S_SCAN_ENABLED")
    
    # Scan profiles
    scan_profiles: Dict[str, Any] = Field(
        default={
            "quick": {"timeout": 300, "intensity": "low"},
            "standard": {"timeout": 1800, "intensity": "medium"},
            "thorough": {"timeout": 3600, "intensity": "high"},
            "custom": {"timeout": 7200, "intensity": "max"}
        },
        env="SCAN_PROFILES"
    )
    
    # Rate limiting
    rate_limit_enabled: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
    scans_per_hour: int = Field(default=10, env="SCANS_PER_HOUR")
    
    # Reporting
    report_storage_path: str = Field(default="/app/reports", env="REPORT_STORAGE_PATH")
    report_formats: List[str] = Field(
        default=["json", "html", "pdf", "xml"],
        env="REPORT_FORMATS"
    )
    report_retention_days: int = Field(default=90, env="REPORT_RETENTION_DAYS")
    
    # Alert configuration
    alert_enabled: bool = Field(default=True, env="ALERT_ENABLED")
    alert_webhook_url: Optional[str] = Field(default=None, env="ALERT_WEBHOOK_URL")
    alert_email: Optional[str] = Field(default=None, env="ALERT_EMAIL")
    critical_severity_threshold: int = Field(default=5, env="CRITICAL_SEVERITY_THRESHOLD")
    
    # Integration settings
    threat_intel_enabled: bool = Field(default=True, env="THREAT_INTEL_ENABLED")
    misp_url: Optional[str] = Field(default=None, env="MISP_URL")
    misp_key: Optional[str] = Field(default=None, env="MISP_KEY")
    
    # Vulnerability feeds
    nvd_feed_enabled: bool = Field(default=True, env="NVD_FEED_ENABLED")
    nvd_api_key: Optional[str] = Field(default=None, env="NVD_API_KEY")
    
    # Security settings
    allowed_origins: List[str] = Field(default=["http://localhost:3000"], env="ALLOWED_ORIGINS")
    api_key_header: str = Field(default="X-API-Key", env="API_KEY_HEADER")
    require_auth: bool = Field(default=True, env="REQUIRE_AUTH")
    
    # Scan targets configuration
    allowed_target_networks: List[str] = Field(
        default=["192.168.0.0/16", "10.0.0.0/8", "172.16.0.0/12"],
        env="ALLOWED_TARGET_NETWORKS"
    )
    blocked_target_networks: List[str] = Field(
        default=["169.254.0.0/16", "224.0.0.0/4"],
        env="BLOCKED_TARGET_NETWORKS"
    )
    
    # Performance settings
    scan_queue_size: int = Field(default=100, env="SCAN_QUEUE_SIZE")
    worker_threads: int = Field(default=4, env="WORKER_THREADS")
    memory_limit_mb: int = Field(default=2048, env="MEMORY_LIMIT_MB")
    
    # Data retention
    scan_data_retention_days: int = Field(default=365, env="SCAN_DATA_RETENTION_DAYS")
    log_retention_days: int = Field(default=90, env="LOG_RETENTION_DAYS")
    
    # Web application specific
    user_agents: List[str] = Field(
        default=[
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "SecurityScanner/1.0"
        ],
        env="USER_AGENTS"
    )
    
    # Network scan options
    tcp_port_ranges: List[str] = Field(
        default=["1-1000", "3000-3010", "8000-8100", "9000-9100"],
        env="TCP_PORT_RANGES"
    )
    udp_port_ranges: List[str] = Field(
        default=["53", "67-68", "123", "161", "500", "1194"],
        env="UDP_PORT_RANGES"
    )
    
    # SSL/TLS configuration
    ssl_protocols: List[str] = Field(
        default=["tls1_2", "tls1_3"],
        env="SSL_PROTOCOLS"
    )
    cipher_suites: List[str] = Field(
        default=["ALL"],
        env="CIPHER_SUITES"
    )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()