"""Configuration settings for Broadcast Integration Service"""

from typing import Optional, Dict, Any
from pydantic_settings import BaseSettings
from pydantic import Field, validator


class Settings(BaseSettings):
    """Service configuration settings"""
    
    # Service info
    service_name: str = Field(default="broadcast-integration", description="Service name")
    service_version: str = Field(default="1.0.0", description="Service version")
    service_port: int = Field(default=8012, description="Service port")
    
    # Environment
    environment: str = Field(default="development", description="Environment name")
    debug: bool = Field(default=False, description="Debug mode")
    
    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/broadcast",
        description="PostgreSQL connection URL"
    )
    database_pool_size: int = Field(default=20, description="Database connection pool size")
    database_max_overflow: int = Field(default=10, description="Maximum overflow connections")
    
    # Redis
    redis_url: str = Field(
        default="redis://localhost:6379/1",
        description="Redis connection URL"
    )
    redis_pool_size: int = Field(default=10, description="Redis connection pool size")
    
    # MOS Integration
    mos_service_url: str = Field(
        default="http://localhost:8011",
        description="MOS Integration Service URL"
    )
    mos_service_timeout: int = Field(default=30, description="MOS service timeout in seconds")
    
    # Newsroom Systems
    enps_enabled: bool = Field(default=False, description="Enable ENPS integration")
    enps_api_url: Optional[str] = Field(default=None, description="ENPS API URL")
    enps_api_key: Optional[str] = Field(default=None, description="ENPS API key")
    
    avid_enabled: bool = Field(default=False, description="Enable Avid iNEWS integration")
    avid_api_url: Optional[str] = Field(default=None, description="Avid API URL")
    avid_api_key: Optional[str] = Field(default=None, description="Avid API key")
    
    ross_enabled: bool = Field(default=False, description="Enable Ross Inception integration")
    ross_api_url: Optional[str] = Field(default=None, description="Ross API URL")
    ross_api_key: Optional[str] = Field(default=None, description="Ross API key")
    
    octopus_enabled: bool = Field(default=False, description="Enable Octopus integration")
    octopus_api_url: Optional[str] = Field(default=None, description="Octopus API URL")
    octopus_api_key: Optional[str] = Field(default=None, description="Octopus API key")
    
    # Automation Systems
    automation_enabled: bool = Field(default=False, description="Enable automation integration")
    playout_system: str = Field(default="generic", description="Playout system type")
    playout_api_url: Optional[str] = Field(default=None, description="Playout API URL")
    playout_api_key: Optional[str] = Field(default=None, description="Playout API key")
    
    # Graphics
    graphics_enabled: bool = Field(default=True, description="Enable graphics management")
    graphics_renderer: str = Field(default="vizrt", description="Graphics renderer system")
    graphics_preview_url: Optional[str] = Field(default=None, description="Graphics preview URL")
    graphics_api_key: Optional[str] = Field(default=None, description="Graphics API key")
    
    # Teleprompter
    teleprompter_enabled: bool = Field(default=True, description="Enable teleprompter features")
    teleprompter_speed_wpm: int = Field(default=180, description="Default words per minute")
    teleprompter_font_size: int = Field(default=32, description="Default font size")
    teleprompter_scroll_margin: int = Field(default=100, description="Scroll margin in pixels")
    
    # WebSocket Configuration
    websocket_enabled: bool = Field(default=True, description="Enable WebSocket support")
    websocket_ping_interval: int = Field(default=30, description="WebSocket ping interval")
    websocket_ping_timeout: int = Field(default=10, description="WebSocket ping timeout")
    
    # Security
    jwt_secret_key: str = Field(default="your-secret-key-here", description="JWT secret key")
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    jwt_expiration_minutes: int = Field(default=60, description="JWT expiration in minutes")
    
    api_key_header: str = Field(default="X-API-Key", description="API key header name")
    cors_origins: list = Field(default=["*"], description="CORS allowed origins")
    
    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(default="json", description="Log format (json or text)")
    log_file: Optional[str] = Field(default=None, description="Log file path")
    
    # Performance
    max_rundown_size: int = Field(default=1000, description="Maximum stories in a rundown")
    max_script_length: int = Field(default=50000, description="Maximum script length in characters")
    cache_ttl: int = Field(default=300, description="Default cache TTL in seconds")
    
    # File Storage
    upload_path: str = Field(default="/tmp/broadcast-uploads", description="Upload directory")
    max_upload_size: int = Field(default=100 * 1024 * 1024, description="Max upload size in bytes")
    
    # Scheduling
    scheduler_enabled: bool = Field(default=True, description="Enable task scheduler")
    scheduler_timezone: str = Field(default="UTC", description="Scheduler timezone")
    
    # Feature Flags
    feature_approval_workflow: bool = Field(default=True, description="Enable approval workflows")
    feature_templates: bool = Field(default=True, description="Enable template system")
    feature_automation: bool = Field(default=True, description="Enable automation features")
    feature_graphics: bool = Field(default=True, description="Enable graphics management")
    feature_live_production: bool = Field(default=True, description="Enable live production features")
    
    @validator("database_url")
    def validate_database_url(cls, v: str) -> str:
        """Ensure database URL uses async driver"""
        if "postgresql://" in v and "+asyncpg" not in v:
            return v.replace("postgresql://", "postgresql+asyncpg://")
        return v
    
    @validator("cors_origins", pre=True)
    def parse_cors_origins(cls, v: Any) -> list:
        """Parse CORS origins from string or list"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    def get_newsroom_config(self) -> Dict[str, Dict[str, Any]]:
        """Get newsroom system configurations"""
        config = {}
        
        if self.enps_enabled:
            config["enps"] = {
                "enabled": True,
                "api_url": self.enps_api_url,
                "api_key": self.enps_api_key
            }
        
        if self.avid_enabled:
            config["avid"] = {
                "enabled": True,
                "api_url": self.avid_api_url,
                "api_key": self.avid_api_key
            }
        
        if self.ross_enabled:
            config["ross"] = {
                "enabled": True,
                "api_url": self.ross_api_url,
                "api_key": self.ross_api_key
            }
        
        if self.octopus_enabled:
            config["octopus"] = {
                "enabled": True,
                "api_url": self.octopus_api_url,
                "api_key": self.octopus_api_key
            }
        
        return config
    
    def get_automation_config(self) -> Dict[str, Any]:
        """Get automation system configuration"""
        if not self.automation_enabled:
            return {"enabled": False}
        
        return {
            "enabled": True,
            "system": self.playout_system,
            "api_url": self.playout_api_url,
            "api_key": self.playout_api_key
        }
    
    def get_graphics_config(self) -> Dict[str, Any]:
        """Get graphics system configuration"""
        if not self.graphics_enabled:
            return {"enabled": False}
        
        return {
            "enabled": True,
            "renderer": self.graphics_renderer,
            "preview_url": self.graphics_preview_url,
            "api_key": self.graphics_api_key
        }
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        

# Create settings instance
settings = Settings()