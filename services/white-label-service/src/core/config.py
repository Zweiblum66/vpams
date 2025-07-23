"""
Configuration settings for White-Label Service
"""

from pydantic_settings import BaseSettings
from typing import List, Optional
import os


class Settings(BaseSettings):
    """Application settings"""
    
    # Service Info
    service_name: str = "white-label-service"
    service_version: str = "1.0.0"
    debug: bool = False
    port: int = 8012
    
    # Database
    database_url: str = "postgresql+asyncpg://user:password@localhost:5432/mams_whitelabel"
    database_pool_size: int = 20
    database_max_overflow: int = 0
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # Security
    secret_key: str = "your-secret-key-here"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # CORS
    allowed_origins: List[str] = ["*"]
    allowed_hosts: List[str] = ["*"]
    
    # Storage
    storage_backend: str = "local"  # local, s3, azure, gcp
    storage_bucket: Optional[str] = None
    storage_region: Optional[str] = None
    storage_access_key: Optional[str] = None
    storage_secret_key: Optional[str] = None
    
    # CDN
    cdn_base_url: Optional[str] = None
    cdn_enabled: bool = False
    
    # Email
    smtp_server: Optional[str] = None
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_use_tls: bool = True
    
    # External Services
    api_gateway_url: str = "http://localhost:8000"
    user_service_url: str = "http://localhost:8001"
    asset_service_url: str = "http://localhost:8002"
    
    # White-Label Limits
    max_themes_per_tenant: int = 10
    max_logo_size_mb: int = 5
    max_favicon_size_mb: int = 1
    max_custom_css_size_kb: int = 100
    max_custom_domains: int = 5
    
    # Feature Flags
    enable_custom_domains: bool = True
    enable_ssl_provisioning: bool = True
    enable_email_templates: bool = True
    enable_mobile_apps: bool = True
    enable_api_branding: bool = True
    enable_advanced_themes: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()