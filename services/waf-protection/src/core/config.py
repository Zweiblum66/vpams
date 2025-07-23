"""
Configuration for WAF Protection Service
"""

from typing import List, Optional, Dict, Any
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings"""
    
    # Service configuration
    service_name: str = Field(default="waf-protection", env="SERVICE_NAME")
    service_port: int = Field(default=8022, env="SERVICE_PORT")
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost/mams_waf",
        env="DATABASE_URL"
    )
    
    # Redis
    redis_url: str = Field(
        default="redis://localhost:6379/4",
        env="REDIS_URL"
    )
    
    # WAF Configuration
    waf_enabled: bool = Field(default=True, env="WAF_ENABLED")
    waf_mode: str = Field(default="blocking", env="WAF_MODE")  # blocking, monitoring, off
    
    # Rate Limiting
    rate_limit_enabled: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
    rate_limit_requests_per_minute: int = Field(default=60, env="RATE_LIMIT_RPM")
    rate_limit_burst: int = Field(default=10, env="RATE_LIMIT_BURST")
    
    # IP Filtering
    ip_whitelist: List[str] = Field(default_factory=list, env="IP_WHITELIST")
    ip_blacklist: List[str] = Field(default_factory=list, env="IP_BLACKLIST")
    
    # Geo Blocking
    geo_blocking_enabled: bool = Field(default=False, env="GEO_BLOCKING_ENABLED")
    blocked_countries: List[str] = Field(default_factory=list, env="BLOCKED_COUNTRIES")
    allowed_countries: List[str] = Field(default_factory=list, env="ALLOWED_COUNTRIES")
    geoip_database_path: str = Field(default="/app/data/GeoLite2-Country.mmdb", env="GEOIP_DATABASE_PATH")
    
    # SQL Injection Protection
    sql_injection_protection: bool = Field(default=True, env="SQL_INJECTION_PROTECTION")
    sql_injection_sensitivity: str = Field(default="medium", env="SQL_INJECTION_SENSITIVITY")  # low, medium, high
    
    # XSS Protection
    xss_protection: bool = Field(default=True, env="XSS_PROTECTION")
    xss_sensitivity: str = Field(default="medium", env="XSS_SENSITIVITY")  # low, medium, high
    
    # CSRF Protection
    csrf_protection: bool = Field(default=True, env="CSRF_PROTECTION")
    csrf_token_name: str = Field(default="csrf_token", env="CSRF_TOKEN_NAME")
    csrf_header_name: str = Field(default="X-CSRF-Token", env="CSRF_HEADER_NAME")
    
    # Request Size Limits
    max_request_size: int = Field(default=100 * 1024 * 1024, env="MAX_REQUEST_SIZE")  # 100MB
    max_header_size: int = Field(default=8192, env="MAX_HEADER_SIZE")  # 8KB
    max_url_length: int = Field(default=4096, env="MAX_URL_LENGTH")  # 4KB
    
    # File Upload Protection
    allowed_file_extensions: List[str] = Field(
        default=[".jpg", ".jpeg", ".png", ".gif", ".mp4", ".mov", ".avi", ".pdf", ".doc", ".docx"],
        env="ALLOWED_FILE_EXTENSIONS"
    )
    blocked_file_extensions: List[str] = Field(
        default=[".exe", ".bat", ".cmd", ".scr", ".com", ".pif", ".vbs", ".js", ".jar"],
        env="BLOCKED_FILE_EXTENSIONS"
    )
    max_file_size: int = Field(default=500 * 1024 * 1024, env="MAX_FILE_SIZE")  # 500MB
    
    # Bot Protection
    bot_protection_enabled: bool = Field(default=True, env="BOT_PROTECTION_ENABLED")
    bot_detection_sensitivity: str = Field(default="medium", env="BOT_DETECTION_SENSITIVITY")
    challenge_bad_bots: bool = Field(default=True, env="CHALLENGE_BAD_BOTS")
    
    # DDoS Protection
    ddos_protection_enabled: bool = Field(default=True, env="DDOS_PROTECTION_ENABLED")
    ddos_threshold_per_minute: int = Field(default=300, env="DDOS_THRESHOLD_PER_MINUTE")
    ddos_block_duration: int = Field(default=300, env="DDOS_BLOCK_DURATION")  # seconds
    
    # Logging and Monitoring
    log_blocked_requests: bool = Field(default=True, env="LOG_BLOCKED_REQUESTS")
    log_suspicious_requests: bool = Field(default=True, env="LOG_SUSPICIOUS_REQUESTS")
    detailed_logging: bool = Field(default=False, env="DETAILED_LOGGING")
    
    # Custom Rules
    custom_rules_enabled: bool = Field(default=True, env="CUSTOM_RULES_ENABLED")
    custom_rules_file: str = Field(default="/app/config/custom_rules.yaml", env="CUSTOM_RULES_FILE")
    
    # Alerting
    alert_webhook_url: Optional[str] = Field(default=None, env="ALERT_WEBHOOK_URL")
    alert_email: Optional[str] = Field(default=None, env="ALERT_EMAIL")
    alert_threshold: int = Field(default=10, env="ALERT_THRESHOLD")  # alerts per minute
    
    # API Security
    api_key_header: str = Field(default="X-API-Key", env="API_KEY_HEADER")
    jwt_secret_key: str = Field(default="your-secret-key", env="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    
    # Service URLs
    api_gateway_url: str = Field(
        default="http://api-gateway:8000",
        env="API_GATEWAY_URL"
    )
    user_service_url: str = Field(
        default="http://user-management:8002",
        env="USER_SERVICE_URL"
    )
    monitoring_service_url: str = Field(
        default="http://monitoring:8020",
        env="MONITORING_SERVICE_URL"
    )
    
    # Performance Settings
    cache_ttl: int = Field(default=300, env="CACHE_TTL")  # seconds
    max_concurrent_requests: int = Field(default=1000, env="MAX_CONCURRENT_REQUESTS")
    request_timeout: int = Field(default=30, env="REQUEST_TIMEOUT")  # seconds
    
    # SSL/TLS Settings
    enforce_https: bool = Field(default=True, env="ENFORCE_HTTPS")
    hsts_max_age: int = Field(default=31536000, env="HSTS_MAX_AGE")  # 1 year
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings"""
    return settings