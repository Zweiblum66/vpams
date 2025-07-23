"""
Configuration settings for Blockchain Service.
"""
from typing import Optional, List
from pydantic import Field, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # Service Information
    service_name: str = "blockchain-service"
    service_version: str = "1.0.0"
    debug: bool = Field(default=False, env="DEBUG")
    
    # API Configuration
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    api_prefix: str = "/api/v1"
    
    # Database
    database_url: str = Field(env="DATABASE_URL")
    database_pool_size: int = Field(default=10, env="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=20, env="DATABASE_MAX_OVERFLOW")
    
    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    redis_password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    
    # Blockchain Networks
    ethereum_rpc_url: str = Field(env="ETHEREUM_RPC_URL")
    polygon_rpc_url: str = Field(env="POLYGON_RPC_URL") 
    avalanche_rpc_url: str = Field(env="AVALANCHE_RPC_URL")
    bsc_rpc_url: str = Field(env="BSC_RPC_URL")
    
    # Private Keys (for transaction signing)
    private_key: str = Field(env="BLOCKCHAIN_PRIVATE_KEY")
    
    # Smart Contract Addresses
    rights_contract_ethereum: Optional[str] = Field(default=None, env="RIGHTS_CONTRACT_ETHEREUM")
    rights_contract_polygon: Optional[str] = Field(default=None, env="RIGHTS_CONTRACT_POLYGON")
    rights_contract_avalanche: Optional[str] = Field(default=None, env="RIGHTS_CONTRACT_AVALANCHE")
    rights_contract_bsc: Optional[str] = Field(default=None, env="RIGHTS_CONTRACT_BSC")
    
    # IPFS Configuration
    ipfs_node_url: str = Field(default="http://localhost:5001", env="IPFS_NODE_URL")
    ipfs_gateway_url: str = Field(default="http://localhost:8080", env="IPFS_GATEWAY_URL")
    
    # Gas Configuration
    gas_limit: int = Field(default=300000, env="GAS_LIMIT")
    gas_price_gwei: int = Field(default=20, env="GAS_PRICE_GWEI")
    max_fee_per_gas_gwei: int = Field(default=30, env="MAX_FEE_PER_GAS_GWEI")
    max_priority_fee_per_gas_gwei: int = Field(default=2, env="MAX_PRIORITY_FEE_PER_GAS_GWEI")
    
    # Rights Management
    default_license_duration_days: int = Field(default=365, env="DEFAULT_LICENSE_DURATION_DAYS")
    royalty_percentage: float = Field(default=5.0, env="ROYALTY_PERCENTAGE")
    
    # Security
    jwt_secret: str = Field(env="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_expiration_minutes: int = Field(default=60, env="JWT_EXPIRATION_MINUTES")
    
    # Monitoring
    enable_metrics: bool = Field(default=True, env="ENABLE_METRICS")
    metrics_port: int = Field(default=8001, env="METRICS_PORT")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Rate Limiting
    rate_limit_requests: int = Field(default=1000, env="RATE_LIMIT_REQUESTS")
    rate_limit_window: int = Field(default=3600, env="RATE_LIMIT_WINDOW")  # seconds
    
    # Network Settings
    supported_networks: List[str] = ["ethereum", "polygon", "avalanche", "bsc"]
    default_network: str = Field(default="polygon", env="DEFAULT_NETWORK")
    
    # Transaction Settings
    confirmation_blocks: int = Field(default=3, env="CONFIRMATION_BLOCKS")
    transaction_timeout: int = Field(default=300, env="TRANSACTION_TIMEOUT")  # seconds
    retry_attempts: int = Field(default=3, env="RETRY_ATTEMPTS")
    
    @validator("royalty_percentage")
    def validate_royalty_percentage(cls, v):
        if not 0 <= v <= 100:
            raise ValueError("Royalty percentage must be between 0 and 100")
        return v
    
    @validator("default_network")
    def validate_default_network(cls, v, values):
        supported = values.get("supported_networks", [])
        if v not in supported:
            raise ValueError(f"Default network must be one of: {supported}")
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()