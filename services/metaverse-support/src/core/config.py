"""Configuration settings for Metaverse Support Service"""

from typing import List, Optional, Dict, Any
from pydantic import BaseSettings, Field, validator

class Settings(BaseSettings):
    """Application settings"""
    
    # Service configuration
    SERVICE_NAME: str = Field(default="metaverse-support", env="SERVICE_NAME")
    SERVICE_PORT: int = Field(default=8022, env="SERVICE_PORT")
    DEBUG: bool = Field(default=False, env="DEBUG")
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Database configuration
    DATABASE_URL: str = Field(..., env="DATABASE_URL")
    REDIS_URL: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    
    # Security
    JWT_SECRET_KEY: str = Field(..., env="JWT_SECRET_KEY")
    JWT_ALGORITHM: str = Field(default="HS256", env="JWT_ALGORITHM")
    JWT_EXPIRATION_MINUTES: int = Field(default=60, env="JWT_EXPIRATION_MINUTES")
    
    # CORS
    ALLOWED_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"],
        env="ALLOWED_ORIGINS"
    )
    
    # Virtual Worlds Configuration
    UNITY_SERVER_URL: str = Field(default="http://localhost:7777", env="UNITY_SERVER_URL")
    UNREAL_SERVER_URL: str = Field(default="http://localhost:7778", env="UNREAL_SERVER_URL")
    VRCHAT_SDK_KEY: Optional[str] = Field(default=None, env="VRCHAT_SDK_KEY")
    HORIZON_WORLDS_TOKEN: Optional[str] = Field(default=None, env="HORIZON_WORLDS_TOKEN")
    ROBLOX_API_KEY: Optional[str] = Field(default=None, env="ROBLOX_API_KEY")
    MINECRAFT_REALM_KEY: Optional[str] = Field(default=None, env="MINECRAFT_REALM_KEY")
    FORTNITE_CREATIVE_KEY: Optional[str] = Field(default=None, env="FORTNITE_CREATIVE_KEY")
    
    # VR/AR Hardware Configuration
    OCULUS_APP_ID: Optional[str] = Field(default=None, env="OCULUS_APP_ID")
    STEAMVR_SDK_PATH: Optional[str] = Field(default=None, env="STEAMVR_SDK_PATH")
    HOLOLENS_DEVICE_PORTAL: Optional[str] = Field(default=None, env="HOLOLENS_DEVICE_PORTAL")
    MAGIC_LEAP_SDK_KEY: Optional[str] = Field(default=None, env="MAGIC_LEAP_SDK_KEY")
    APPLE_ARKIT_TEAM_ID: Optional[str] = Field(default=None, env="APPLE_ARKIT_TEAM_ID")
    ANDROID_ARCORE_API_KEY: Optional[str] = Field(default=None, env="ANDROID_ARCORE_API_KEY")
    
    # Spatial Computing
    SPATIAL_ANCHOR_SERVICE_URL: str = Field(
        default="http://localhost:8090", 
        env="SPATIAL_ANCHOR_SERVICE_URL"
    )
    AZURE_SPATIAL_ANCHORS_ACCOUNT_ID: Optional[str] = Field(
        default=None, 
        env="AZURE_SPATIAL_ANCHORS_ACCOUNT_ID"
    )
    AZURE_SPATIAL_ANCHORS_KEY: Optional[str] = Field(
        default=None, 
        env="AZURE_SPATIAL_ANCHORS_KEY"
    )
    
    # Blockchain Integration (Web3)
    WEB3_SERVICE_URL: str = Field(
        default="http://localhost:8021", 
        env="WEB3_SERVICE_URL"
    )
    ETHEREUM_RPC_URL: str = Field(
        default="https://mainnet.infura.io/v3/YOUR_PROJECT_ID",
        env="ETHEREUM_RPC_URL"
    )
    POLYGON_RPC_URL: str = Field(
        default="https://polygon-mainnet.infura.io/v3/YOUR_PROJECT_ID",
        env="POLYGON_RPC_URL"
    )
    
    # NFT Marketplaces
    OPENSEA_API_KEY: Optional[str] = Field(default=None, env="OPENSEA_API_KEY")
    RARIBLE_API_KEY: Optional[str] = Field(default=None, env="RARIBLE_API_KEY")
    FOUNDATION_API_KEY: Optional[str] = Field(default=None, env="FOUNDATION_API_KEY")
    
    # Avatar Systems
    READY_PLAYER_ME_APP_ID: Optional[str] = Field(default=None, env="READY_PLAYER_ME_APP_ID")
    VROID_SDK_KEY: Optional[str] = Field(default=None, env="VROID_SDK_KEY")
    MIXAMO_API_KEY: Optional[str] = Field(default=None, env="MIXAMO_API_KEY")
    
    # AI/ML Services for Metaverse
    AI_SERVICE_URL: str = Field(
        default="http://localhost:8003",
        env="AI_SERVICE_URL"
    )
    OPENAI_API_KEY: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    
    # Media Processing
    FFMPEG_PATH: str = Field(default="ffmpeg", env="FFMPEG_PATH")
    BLENDER_PATH: Optional[str] = Field(default=None, env="BLENDER_PATH")
    
    # Storage for 3D Assets
    ASSET_STORAGE_URL: str = Field(
        default="http://localhost:8002",
        env="ASSET_STORAGE_URL"
    )
    IPFS_GATEWAY_URL: str = Field(
        default="https://ipfs.io/ipfs/",
        env="IPFS_GATEWAY_URL"
    )
    
    # Social Features
    DISCORD_BOT_TOKEN: Optional[str] = Field(default=None, env="DISCORD_BOT_TOKEN")
    TWITTER_API_KEY: Optional[str] = Field(default=None, env="TWITTER_API_KEY")
    
    # Performance Settings
    MAX_CONCURRENT_RENDERS: int = Field(default=5, env="MAX_CONCURRENT_RENDERS")
    MAX_AVATAR_POLYGON_COUNT: int = Field(default=100000, env="MAX_AVATAR_POLYGON_COUNT")
    MAX_WORLD_SIZE_MB: int = Field(default=500, env="MAX_WORLD_SIZE_MB")
    RENDER_QUALITY_PRESETS: Dict[str, Any] = Field(
        default={
            "mobile": {"resolution": "1080x1920", "fps": 30, "quality": "medium"},
            "vr": {"resolution": "2160x1200", "fps": 90, "quality": "high"},
            "ar": {"resolution": "1334x750", "fps": 60, "quality": "high"},
            "desktop": {"resolution": "1920x1080", "fps": 60, "quality": "ultra"}
        }
    )
    
    # Cross-Platform Compatibility
    SUPPORTED_VR_FORMATS: List[str] = Field(
        default=["fbx", "gltf", "obj", "dae", "blend"],
        env="SUPPORTED_VR_FORMATS"
    )
    SUPPORTED_AR_FORMATS: List[str] = Field(
        default=["usdz", "glb", "fbx", "obj"],
        env="SUPPORTED_AR_FORMATS"
    )
    SUPPORTED_TEXTURE_FORMATS: List[str] = Field(
        default=["png", "jpg", "jpeg", "tga", "exr", "hdr"],
        env="SUPPORTED_TEXTURE_FORMATS"
    )
    
    # Analytics and Metrics
    ANALYTICS_SERVICE_URL: str = Field(
        default="http://localhost:8010",
        env="ANALYTICS_SERVICE_URL"
    )
    
    # Feature Flags
    ENABLE_VR_SUPPORT: bool = Field(default=True, env="ENABLE_VR_SUPPORT")
    ENABLE_AR_SUPPORT: bool = Field(default=True, env="ENABLE_AR_SUPPORT")
    ENABLE_BLOCKCHAIN_FEATURES: bool = Field(default=True, env="ENABLE_BLOCKCHAIN_FEATURES")
    ENABLE_SOCIAL_FEATURES: bool = Field(default=True, env="ENABLE_SOCIAL_FEATURES")
    ENABLE_AI_AVATAR_GENERATION: bool = Field(default=False, env="ENABLE_AI_AVATAR_GENERATION")
    ENABLE_PHYSICS_SIMULATION: bool = Field(default=True, env="ENABLE_PHYSICS_SIMULATION")
    ENABLE_VOICE_CHAT: bool = Field(default=False, env="ENABLE_VOICE_CHAT")
    
    @validator("ALLOWED_ORIGINS", pre=True)
    def parse_cors_origins(cls, v):
        """Parse CORS origins from string or list"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @validator("SUPPORTED_VR_FORMATS", "SUPPORTED_AR_FORMATS", "SUPPORTED_TEXTURE_FORMATS", pre=True)
    def parse_format_lists(cls, v):
        """Parse format lists from string or list"""
        if isinstance(v, str):
            return [fmt.strip() for fmt in v.split(",")]
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Global settings instance
settings = Settings()