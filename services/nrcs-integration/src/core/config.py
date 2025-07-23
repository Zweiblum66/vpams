"""Configuration settings for NRCS Integration Service"""

from typing import List, Optional, Dict, Any
from pydantic import BaseSettings, Field, validator
from functools import lru_cache
import os


class Settings(BaseSettings):
    """Application settings"""
    
    # Service Configuration
    service_name: str = Field(default="nrcs-integration", description="Service name")
    service_host: str = Field(default="0.0.0.0", description="Service host")
    service_port: int = Field(default=8014, description="Service port")
    debug: bool = Field(default=False, description="Debug mode")
    log_level: str = Field(default="INFO", description="Logging level")
    environment: str = Field(default="development", description="Environment (development, staging, production)")
    
    # Database Configuration
    database_url: str = Field(..., description="Database connection URL")
    database_pool_size: int = Field(default=10, description="Database connection pool size")
    database_max_overflow: int = Field(default=20, description="Database max overflow connections")
    
    # Redis Configuration
    redis_url: str = Field(default="redis://redis:6379/3", description="Redis connection URL")
    
    # Authentication
    jwt_secret_key: str = Field(..., description="JWT secret key")
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    jwt_expiration_minutes: int = Field(default=60, description="JWT token expiration in minutes")
    
    # CORS Settings
    allowed_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"],
        description="Allowed CORS origins"
    )
    
    # ENPS Configuration
    enps_enabled: bool = Field(default=False, env="ENPS_ENABLED", description="Enable ENPS integration")
    enps_server: str = Field(default="", env="ENPS_SERVER", description="ENPS server hostname")
    enps_port: int = Field(default=9000, env="ENPS_PORT", description="ENPS server port")
    enps_database: str = Field(default="ENPS_DB", env="ENPS_DATABASE", description="ENPS database name")
    enps_user: str = Field(default="", env="ENPS_USER", description="ENPS username")
    enps_password: str = Field(default="", env="ENPS_PASSWORD", description="ENPS password")
    enps_ldap_server: str = Field(default="", env="ENPS_LDAP_SERVER", description="ENPS LDAP server")
    enps_ldap_base_dn: str = Field(default="", env="ENPS_LDAP_BASE_DN", description="LDAP base DN")
    enps_timeout: int = Field(default=30, env="ENPS_TIMEOUT", description="ENPS connection timeout")
    
    # Avid iNEWS Configuration
    avid_enabled: bool = Field(default=False, env="AVID_ENABLED", description="Enable Avid iNEWS integration")
    avid_server: str = Field(default="", env="AVID_SERVER", description="Avid iNEWS server hostname")
    avid_port: int = Field(default=21, env="AVID_PORT", description="Avid FTP port")
    avid_ftp_user: str = Field(default="", env="AVID_FTP_USER", description="Avid FTP username")
    avid_ftp_password: str = Field(default="", env="AVID_FTP_PASSWORD", description="Avid FTP password")
    avid_api_url: str = Field(default="", env="AVID_API_URL", description="Avid API URL")
    avid_api_key: str = Field(default="", env="AVID_API_KEY", description="Avid API key")
    avid_timeout: int = Field(default=60, env="AVID_TIMEOUT", description="Avid connection timeout")
    avid_passive_mode: bool = Field(default=True, env="AVID_PASSIVE_MODE", description="FTP passive mode")
    
    # Ross Inception Configuration
    ross_enabled: bool = Field(default=False, env="ROSS_ENABLED", description="Enable Ross Inception integration")
    ross_api_url: str = Field(default="", env="ROSS_API_URL", description="Ross API URL")
    ross_api_key: str = Field(default="", env="ROSS_API_KEY", description="Ross API key")
    ross_websocket_url: str = Field(default="", env="ROSS_WEBSOCKET_URL", description="Ross WebSocket URL")
    ross_username: str = Field(default="", env="ROSS_USERNAME", description="Ross username")
    ross_password: str = Field(default="", env="ROSS_PASSWORD", description="Ross password")
    ross_timeout: int = Field(default=30, env="ROSS_TIMEOUT", description="Ross connection timeout")
    ross_heartbeat_interval: int = Field(default=30, env="ROSS_HEARTBEAT_INTERVAL", description="Ross heartbeat interval")
    
    # Octopus Configuration
    octopus_enabled: bool = Field(default=False, env="OCTOPUS_ENABLED", description="Enable Octopus integration")
    octopus_api_url: str = Field(default="", env="OCTOPUS_API_URL", description="Octopus API URL")
    octopus_username: str = Field(default="", env="OCTOPUS_USERNAME", description="Octopus username")
    octopus_password: str = Field(default="", env="OCTOPUS_PASSWORD", description="Octopus password")
    octopus_tenant: str = Field(default="", env="OCTOPUS_TENANT", description="Octopus tenant ID")
    octopus_timeout: int = Field(default=45, env="OCTOPUS_TIMEOUT", description="Octopus connection timeout")
    octopus_api_version: str = Field(default="v2", env="OCTOPUS_API_VERSION", description="Octopus API version")
    
    # Integration Settings
    sync_interval_seconds: int = Field(default=30, description="Synchronization interval in seconds")
    max_concurrent_connections: int = Field(default=10, description="Maximum concurrent NRCS connections")
    retry_attempts: int = Field(default=3, description="Number of retry attempts for failed operations")
    retry_delay_seconds: int = Field(default=5, description="Delay between retry attempts")
    archive_retention_days: int = Field(default=365, description="Archive retention period in days")
    
    # Feature Flags
    enable_real_time_sync: bool = Field(default=True, description="Enable real-time synchronization")
    enable_archive_integration: bool = Field(default=True, description="Enable archive integration")
    enable_user_sync: bool = Field(default=True, description="Enable user synchronization")
    enable_assignment_sync: bool = Field(default=True, description="Enable assignment synchronization")
    enable_wire_ingestion: bool = Field(default=True, description="Enable wire service ingestion")
    enable_analytics: bool = Field(default=True, description="Enable analytics tracking")
    
    # Performance Settings
    story_batch_size: int = Field(default=50, description="Story processing batch size")
    rundown_cache_ttl: int = Field(default=300, description="Rundown cache TTL in seconds")
    user_cache_ttl: int = Field(default=3600, description="User cache TTL in seconds")
    connection_pool_size: int = Field(default=10, description="Connection pool size per NRCS")
    max_story_size_mb: int = Field(default=10, description="Maximum story size in MB")
    
    # Monitoring & Alerting
    enable_metrics: bool = Field(default=True, description="Enable Prometheus metrics")
    enable_health_checks: bool = Field(default=True, description="Enable health checks")
    alert_webhook_url: str = Field(default="", description="Webhook URL for alerts")
    alert_email_addresses: List[str] = Field(default=[], description="Email addresses for alerts")
    
    # Security Settings
    encrypt_credentials: bool = Field(default=True, description="Encrypt stored credentials")
    audit_logging: bool = Field(default=True, description="Enable audit logging")
    ip_whitelist: List[str] = Field(default=[], description="IP whitelist for API access")
    api_rate_limit_per_minute: int = Field(default=100, description="API rate limit per minute")
    
    # Development Settings
    development_mode: bool = Field(default=False, description="Development mode (allows mock auth)")
    enable_api_docs: bool = Field(default=True, description="Enable API documentation")
    log_sql_queries: bool = Field(default=False, description="Log SQL queries")
    
    @validator("allowed_origins", pre=True)
    def parse_allowed_origins(cls, v):
        """Parse allowed origins from string or list"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @validator("alert_email_addresses", pre=True)
    def parse_alert_emails(cls, v):
        """Parse alert email addresses from string or list"""
        if isinstance(v, str):
            return [email.strip() for email in v.split(",")]
        return v
    
    @validator("ip_whitelist", pre=True)
    def parse_ip_whitelist(cls, v):
        """Parse IP whitelist from string or list"""
        if isinstance(v, str):
            return [ip.strip() for ip in v.split(",")]
        return v
    
    def get_nrcs_systems(self) -> Dict[str, Dict[str, Any]]:
        """Get enabled NRCS systems with their configurations"""
        systems = {}
        
        if self.enps_enabled:
            systems['enps'] = {
                'type': 'enps',
                'server': self.enps_server,
                'port': self.enps_port,
                'database': self.enps_database,
                'user': self.enps_user,
                'password': self.enps_password,
                'ldap_server': self.enps_ldap_server,
                'ldap_base_dn': self.enps_ldap_base_dn,
                'timeout': self.enps_timeout,
            }
        
        if self.avid_enabled:
            systems['avid'] = {
                'type': 'avid',
                'server': self.avid_server,
                'port': self.avid_port,
                'ftp_user': self.avid_ftp_user,
                'ftp_password': self.avid_ftp_password,
                'api_url': self.avid_api_url,
                'api_key': self.avid_api_key,
                'timeout': self.avid_timeout,
                'passive_mode': self.avid_passive_mode,
            }
        
        if self.ross_enabled:
            systems['ross'] = {
                'type': 'ross',
                'api_url': self.ross_api_url,
                'api_key': self.ross_api_key,
                'websocket_url': self.ross_websocket_url,
                'username': self.ross_username,
                'password': self.ross_password,
                'timeout': self.ross_timeout,
                'heartbeat_interval': self.ross_heartbeat_interval,
            }
        
        if self.octopus_enabled:
            systems['octopus'] = {
                'type': 'octopus',
                'api_url': self.octopus_api_url,
                'username': self.octopus_username,
                'password': self.octopus_password,
                'tenant': self.octopus_tenant,
                'timeout': self.octopus_timeout,
                'api_version': self.octopus_api_version,
            }
        
        return systems
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Global settings instance
settings = get_settings()