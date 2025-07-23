"""
Configuration settings for Partner Service
"""

import os
from typing import List, Optional
from pydantic import BaseSettings, validator


class Settings(BaseSettings):
    """Application settings"""
    
    # Service Configuration
    service_name: str = "partner-service"
    service_version: str = "1.0.0"
    service_port: int = 8012
    environment: str = "development"
    debug: bool = True
    
    # Database Configuration
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/mams_partners"
    database_pool_size: int = 20
    database_max_overflow: int = 30
    
    # Redis Configuration
    redis_url: str = "redis://localhost:6379/12"
    
    # Security
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # CORS
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:8080"]
    
    # Partner Portal Configuration
    max_partners_per_company: int = 100
    partner_approval_required: bool = True
    auto_approve_trusted_domains: List[str] = []
    
    # File Upload Configuration
    max_file_size: int = 100 * 1024 * 1024  # 100MB
    allowed_file_types: List[str] = ["pdf", "doc", "docx", "xlsx", "pptx", "png", "jpg", "jpeg"]
    upload_directory: str = "/uploads/partners"
    
    # Email Configuration
    smtp_server: str = "localhost"
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_use_tls: bool = True
    from_email: str = "noreply@mams.com"
    
    # External API Configuration
    mams_api_base_url: str = "http://localhost:8000"
    user_service_url: str = "http://localhost:8001"
    notification_service_url: str = "http://localhost:8013"
    
    @validator("cors_origins", pre=True)
    def assemble_cors_origins(cls, v):
        if isinstance(v, str):
            return [i.strip() for i in v.split(",")]
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()