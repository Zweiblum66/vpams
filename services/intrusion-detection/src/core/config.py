"""Configuration settings for Intrusion Detection Service."""

from pydantic import Field
from pydantic_settings import BaseSettings
from typing import List, Optional
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings."""
    
    # Service configuration
    service_name: str = Field(default="intrusion-detection", env="SERVICE_NAME")
    service_port: int = Field(default=8023, env="SERVICE_PORT")
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Database configuration
    database_url: str = Field(env="DATABASE_URL")
    
    # Redis configuration
    redis_url: str = Field(default="redis://localhost:6379/5", env="REDIS_URL")
    
    # Network monitoring
    network_interface: str = Field(default="eth0", env="NETWORK_INTERFACE")
    capture_filter: str = Field(default="", env="CAPTURE_FILTER")
    packet_buffer_size: int = Field(default=65536, env="PACKET_BUFFER_SIZE")
    max_packets_per_second: int = Field(default=10000, env="MAX_PACKETS_PER_SECOND")
    
    # Intrusion detection settings
    ids_enabled: bool = Field(default=True, env="IDS_ENABLED")
    ids_mode: str = Field(default="active", env="IDS_MODE")  # active, passive, learning
    detection_threshold: float = Field(default=0.8, env="DETECTION_THRESHOLD")
    
    # Anomaly detection
    anomaly_detection_enabled: bool = Field(default=True, env="ANOMALY_DETECTION_ENABLED")
    learning_period_hours: int = Field(default=24, env="LEARNING_PERIOD_HOURS")
    model_update_interval: int = Field(default=3600, env="MODEL_UPDATE_INTERVAL")  # seconds
    
    # Host-based monitoring
    host_monitoring_enabled: bool = Field(default=True, env="HOST_MONITORING_ENABLED")
    file_integrity_monitoring: bool = Field(default=True, env="FILE_INTEGRITY_MONITORING")
    process_monitoring: bool = Field(default=True, env="PROCESS_MONITORING")
    
    # Alert configuration
    alert_enabled: bool = Field(default=True, env="ALERT_ENABLED")
    alert_webhook_url: Optional[str] = Field(default=None, env="ALERT_WEBHOOK_URL")
    alert_email: Optional[str] = Field(default=None, env="ALERT_EMAIL")
    high_severity_threshold: int = Field(default=10, env="HIGH_SEVERITY_THRESHOLD")
    
    # Threat intelligence
    threat_intel_enabled: bool = Field(default=True, env="THREAT_INTEL_ENABLED")
    threat_intel_feeds: List[str] = Field(
        default=[
            "https://feeds.alienvault.com/api/v1/pulses/subscribed",
            "https://rules.emergingthreats.net/open/suricata/rules/"
        ],
        env="THREAT_INTEL_FEEDS"
    )
    threat_intel_update_interval: int = Field(default=7200, env="THREAT_INTEL_UPDATE_INTERVAL")
    
    # Performance settings
    max_concurrent_scans: int = Field(default=10, env="MAX_CONCURRENT_SCANS")
    scan_timeout: int = Field(default=300, env="SCAN_TIMEOUT")  # seconds
    cleanup_interval: int = Field(default=3600, env="CLEANUP_INTERVAL")  # seconds
    
    # Data retention
    event_retention_days: int = Field(default=30, env="EVENT_RETENTION_DAYS")
    log_retention_days: int = Field(default=90, env="LOG_RETENTION_DAYS")
    
    # Security settings
    allowed_origins: List[str] = Field(default=["http://localhost:3000"], env="ALLOWED_ORIGINS")
    api_key_header: str = Field(default="X-API-Key", env="API_KEY_HEADER")
    require_auth: bool = Field(default=True, env="REQUIRE_AUTH")
    
    # Monitoring paths
    monitored_directories: List[str] = Field(
        default=["/etc", "/var/log", "/home", "/opt"],
        env="MONITORED_DIRECTORIES"
    )
    excluded_directories: List[str] = Field(
        default=["/proc", "/sys", "/dev", "/tmp"],
        env="EXCLUDED_DIRECTORIES"
    )
    
    # Signature detection
    signature_files: List[str] = Field(
        default=["/app/rules/emerging-threats.rules", "/app/rules/custom.rules"],
        env="SIGNATURE_FILES"
    )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()