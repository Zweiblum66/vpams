"""Configuration for Web3 Integration Service"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional, List

class Settings(BaseSettings):
    # Service configuration
    SERVICE_NAME: str = Field("web3-integration", env="SERVICE_NAME")
    PORT: int = Field(8021, env="PORT")
    DEBUG: bool = Field(False, env="DEBUG")
    LOG_LEVEL: str = Field("INFO", env="LOG_LEVEL")
    
    # Database
    DATABASE_URL: str = Field(
        "postgresql+asyncpg://postgres:postgres@localhost:5432/web3_integration",
        env="DATABASE_URL"
    )
    
    # Redis
    REDIS_URL: str = Field("redis://localhost:6379/0", env="REDIS_URL")
    
    # JWT
    JWT_SECRET_KEY: str = Field("your-secret-key-here", env="JWT_SECRET_KEY")
    JWT_ALGORITHM: str = Field("HS256", env="JWT_ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(60, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    
    # CORS
    ALLOWED_ORIGINS: List[str] = Field(
        ["http://localhost:3000", "http://localhost:8080"],
        env="ALLOWED_ORIGINS"
    )
    
    # Blockchain RPC URLs
    ETHEREUM_RPC_URL: str = Field(
        "https://mainnet.infura.io/v3/YOUR_PROJECT_ID",
        env="ETHEREUM_RPC_URL"
    )
    POLYGON_RPC_URL: str = Field(
        "https://polygon-mainnet.infura.io/v3/YOUR_PROJECT_ID",
        env="POLYGON_RPC_URL"
    )
    ARBITRUM_RPC_URL: str = Field(
        "https://arbitrum-mainnet.infura.io/v3/YOUR_PROJECT_ID",
        env="ARBITRUM_RPC_URL"
    )
    OPTIMISM_RPC_URL: str = Field(
        "https://optimism-mainnet.infura.io/v3/YOUR_PROJECT_ID",
        env="OPTIMISM_RPC_URL"
    )
    AVALANCHE_RPC_URL: str = Field(
        "https://avalanche-mainnet.infura.io/v3/YOUR_PROJECT_ID",
        env="AVALANCHE_RPC_URL"
    )
    BSC_RPC_URL: str = Field(
        "https://bsc-dataseed.binance.org",
        env="BSC_RPC_URL"
    )
    
    # IPFS Configuration
    IPFS_API_URL: str = Field("http://localhost:5001", env="IPFS_API_URL")
    IPFS_GATEWAY_URL: str = Field("https://ipfs.io/ipfs/", env="IPFS_GATEWAY_URL")
    ipfs_pin_remote: bool = True
    IPFS_CLUSTER_URL: Optional[str] = Field(None, env="IPFS_CLUSTER_URL")
    
    # Pinata (IPFS Pinning Service)
    PINATA_API_KEY: Optional[str] = Field(None, env="PINATA_API_KEY")
    PINATA_SECRET_KEY: Optional[str] = Field(None, env="PINATA_SECRET_KEY")
    
    # Arweave Configuration
    ARWEAVE_URL: str = Field("https://arweave.net", env="ARWEAVE_URL")
    ARWEAVE_KEY: Optional[str] = Field(None, env="ARWEAVE_KEY")
    
    # Filecoin Configuration
    FILECOIN_API_URL: Optional[str] = Field(None, env="FILECOIN_API_URL")
    FILECOIN_TOKEN: Optional[str] = Field(None, env="FILECOIN_TOKEN")
    
    # ENS (Ethereum Name Service)
    ens_enabled: bool = True
    ens_registry_address: Optional[str] = None
    
    # SIWE (Sign-In with Ethereum)
    siwe_enabled: bool = True
    siwe_domain: str = "mams.io"
    siwe_statement: str = "Sign in to MAMS with your Ethereum wallet"
    
    # Gas Configuration
    gas_price_multiplier: float = 1.2
    max_gas_price_gwei: int = 300
    gas_limit_buffer: float = 1.1
    
    # Transaction Settings
    transaction_timeout_seconds: int = 300
    transaction_confirmation_blocks: int = 3
    retry_failed_transactions: bool = True
    max_transaction_retries: int = 3
    
    # Wallet Management
    wallet_encryption_key: Optional[str] = None
    enable_hardware_wallets: bool = True
    supported_wallets: List[str] = ["metamask", "walletconnect", "coinbase", "ledger", "trezor"]
    
    # Smart Contract Settings
    contract_deployment_gas_limit: int = 5000000
    enable_contract_verification: bool = True
    etherscan_api_key: Optional[str] = None
    
    # DeFi Integration
    enable_defi_features: bool = True
    uniswap_router_address: Optional[str] = None
    aave_pool_address: Optional[str] = None
    compound_comptroller_address: Optional[str] = None
    
    # NFT Settings
    nft_metadata_standard: str = "opensea"  # opensea, rarible, custom
    enable_lazy_minting: bool = True
    royalty_percentage: float = 2.5
    
    # DAO Features
    enable_dao_features: bool = True
    governance_token_address: Optional[str] = None
    voting_period_blocks: int = 40320  # ~7 days on Ethereum
    proposal_threshold: int = 1000  # tokens required to create proposal
    
    # Security Settings
    enable_transaction_simulation: bool = True
    blacklist_addresses: List[str] = []
    whitelist_contracts_only: bool = False
    enable_flashloan_protection: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()