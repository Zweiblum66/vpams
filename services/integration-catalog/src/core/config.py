"""
Configuration settings for Integration Catalog Service
"""

import os
from typing import List, Optional
from pydantic import BaseSettings, validator


class Settings(BaseSettings):
    """Application settings"""
    
    # Service Configuration
    service_name: str = "integration-catalog"
    service_version: str = "1.0.0"
    service_port: int = 8014
    environment: str = "development"
    debug: bool = True
    
    # Database Configuration
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/mams_integrations"
    database_pool_size: int = 20
    database_max_overflow: int = 30
    
    # Redis Configuration
    redis_url: str = "redis://localhost:6379/14"
    
    # Security
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # CORS
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:8080"]
    
    # Integration Configuration
    max_integrations_per_category: int = 1000
    auto_approve_verified_integrations: bool = True
    integration_review_required: bool = False
    
    # API Testing Configuration
    api_test_timeout: int = 30
    max_concurrent_tests: int = 10
    
    # File Storage Configuration
    upload_directory: str = "/uploads/integrations"
    max_file_size: int = 50 * 1024 * 1024  # 50MB
    allowed_file_types: List[str] = ["json", "yaml", "yml", "png", "jpg", "jpeg", "svg"]
    
    # External Services
    github_api_base_url: str = "https://api.github.com"
    swagger_hub_api_url: str = "https://api.swaggerhub.com"
    
    @validator("cors_origins", pre=True)
    def assemble_cors_origins(cls, v):
        if isinstance(v, str):
            return [i.strip() for i in v.split(",")]
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()