"""
Rights Management Service - Configuration
"""

from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    """Service configuration settings"""
    
    # Service info
    SERVICE_NAME: str = "rights-management"
    SERVICE_PORT: int = 8011
    DEBUG: bool = False
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://mams:mams@postgres:5432/rights_management"
    
    # MongoDB
    MONGODB_URL: str = "mongodb://mongo:27017/mams"
    
    # Redis
    REDIS_URL: str = "redis://redis:6379/0"
    
    # Auth
    JWT_SECRET_KEY: str = "your-secret-key-here"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    
    # CORS
    CORS_ORIGINS: List[str] = ["*"]
    
    # External services
    GEOLOCATION_API_KEY: str = ""
    GEOLOCATION_API_URL: str = "https://api.ipgeolocation.io/ipgeo"
    
    # Sanctions database
    SANCTIONS_DB_URL: str = ""
    
    # VPN detection
    VPN_DETECTION_API_KEY: str = ""
    VPN_DETECTION_API_URL: str = ""
    
    # Blockchain integration (future)
    BLOCKCHAIN_ENABLED: bool = False
    BLOCKCHAIN_NETWORK: str = "ethereum"
    BLOCKCHAIN_RPC_URL: str = ""
    
    # Smart contracts (future)
    SMART_CONTRACT_ADDRESS: str = ""
    
    # Analytics
    ENABLE_ANALYTICS: bool = True
    ANALYTICS_RETENTION_DAYS: int = 365
    
    # Compliance
    COMPLIANCE_CHECK_ENABLED: bool = True
    AUTO_ALERT_ON_VIOLATION: bool = True
    
    # Performance
    MAX_CONCURRENT_CHECKS: int = 100
    CACHE_TTL_SECONDS: int = 3600
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Create settings instance
settings = Settings()