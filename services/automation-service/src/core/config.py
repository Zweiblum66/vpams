"""Configuration settings for Broadcast Automation Service"""

from typing import List, Optional, Dict, Any
from pydantic import BaseSettings, Field, validator
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings"""
    
    # Service Configuration
    service_name: str = Field(default="automation-service", description="Service name")
    service_host: str = Field(default="0.0.0.0", description="Service host")
    service_port: int = Field(default=8015, description="Service port")
    debug: bool = Field(default=False, description="Debug mode")
    log_level: str = Field(default="INFO", description="Logging level")
    environment: str = Field(default="development", description="Environment")
    
    # Database Configuration
    database_url: str = Field(..., description="Database connection URL")
    database_pool_size: int = Field(default=10, description="Database connection pool size")
    database_max_overflow: int = Field(default=20, description="Database max overflow connections")
    
    # Redis Configuration
    redis_url: str = Field(default="redis://redis:6379/4", description="Redis connection URL")
    
    # Authentication
    jwt_secret_key: str = Field(..., description="JWT secret key")
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    jwt_expiration_minutes: int = Field(default=60, description="JWT token expiration")
    
    # CORS Settings
    allowed_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"],
        description="Allowed CORS origins"
    )
    
    # Device Discovery
    enable_auto_discovery: bool = Field(default=True, description="Enable device auto-discovery")
    discovery_interval: int = Field(default=300, description="Discovery interval in seconds")
    discovery_timeout: int = Field(default=30, description="Discovery timeout in seconds")
    discovery_protocols: List[str] = Field(
        default=["mdns", "ssdp", "ember", "ndi"],
        description="Discovery protocols to use"
    )
    
    # Protocol Settings
    default_control_protocol: str = Field(default="tcp", description="Default control protocol")
    control_timeout: int = Field(default=5, description="Control command timeout in seconds")
    command_retry_count: int = Field(default=3, description="Command retry count")
    heartbeat_interval: int = Field(default=10, description="Device heartbeat interval")
    max_command_queue_size: int = Field(default=1000, description="Maximum command queue size")
    
    # Switcher Configuration
    switcher_enabled: bool = Field(default=True, description="Enable switcher control")
    default_switcher_type: str = Field(default="ross", description="Default switcher type")
    switcher_connection_pool_size: int = Field(default=5, description="Switcher connection pool size")
    switcher_command_delay_ms: int = Field(default=10, description="Delay between switcher commands")
    
    # Camera Configuration
    camera_enabled: bool = Field(default=True, description="Enable camera control")
    default_camera_protocol: str = Field(default="visca", description="Default camera protocol")
    ptz_speed_scale: float = Field(default=1.0, description="PTZ speed scaling factor")
    preset_recall_timeout: int = Field(default=10, description="Preset recall timeout")
    camera_home_on_startup: bool = Field(default=True, description="Home cameras on startup")
    max_ptz_speed: int = Field(default=24, description="Maximum PTZ speed")
    
    # Audio Configuration
    audio_enabled: bool = Field(default=True, description="Enable audio control")
    default_audio_protocol: str = Field(default="ember", description="Default audio protocol")
    audio_fade_curve: str = Field(default="linear", description="Audio fade curve type")
    default_crossfade_time: int = Field(default=1000, description="Default crossfade time in ms")
    audio_meter_interval: int = Field(default=100, description="Audio meter update interval")
    
    # Graphics Configuration
    graphics_enabled: bool = Field(default=True, description="Enable graphics control")
    default_graphics_protocol: str = Field(default="viz", description="Default graphics protocol")
    template_cache_size: int = Field(default=100, description="Graphics template cache size")
    graphics_preview_enabled: bool = Field(default=True, description="Enable graphics preview")
    
    # Lighting Configuration
    lighting_enabled: bool = Field(default=True, description="Enable lighting control")
    default_lighting_protocol: str = Field(default="artnet", description="Default lighting protocol")
    dmx_universe_count: int = Field(default=4, description="Number of DMX universes")
    lighting_fade_time: int = Field(default=1000, description="Default lighting fade time")
    
    # Show Control
    show_control_enabled: bool = Field(default=True, description="Enable show control")
    cue_preload_count: int = Field(default=5, description="Number of cues to preload")
    emergency_stop_gpi: int = Field(default=16, description="Emergency stop GPI input")
    rehearsal_mode_default: bool = Field(default=False, description="Default to rehearsal mode")
    
    # Macro Engine
    macro_enabled: bool = Field(default=True, description="Enable macro engine")
    max_macro_actions: int = Field(default=1000, description="Maximum actions per macro")
    macro_execution_timeout: int = Field(default=300, description="Macro execution timeout")
    macro_storage_path: str = Field(default="/data/macros", description="Macro storage path")
    
    # Remote Production
    remote_control_enabled: bool = Field(default=True, description="Enable remote control")
    control_latency_compensation: bool = Field(default=True, description="Enable latency compensation")
    max_control_latency_ms: int = Field(default=200, description="Maximum control latency")
    remote_preview_quality: str = Field(default="medium", description="Remote preview quality")
    
    # Virtual Production
    virtual_production_enabled: bool = Field(default=False, description="Enable virtual production")
    tracking_system: str = Field(default="freed", description="Camera tracking system")
    render_engine: str = Field(default="unreal", description="Virtual render engine")
    
    # Monitoring & Alerts
    enable_device_monitoring: bool = Field(default=True, description="Enable device monitoring")
    monitoring_interval: int = Field(default=5, description="Monitoring interval in seconds")
    alert_on_device_failure: bool = Field(default=True, description="Alert on device failure")
    alert_webhook_url: str = Field(default="", description="Alert webhook URL")
    device_timeout_seconds: int = Field(default=30, description="Device timeout")
    
    # Performance Settings
    max_concurrent_commands: int = Field(default=100, description="Max concurrent commands")
    command_buffer_size: int = Field(default=10000, description="Command buffer size")
    enable_command_batching: bool = Field(default=True, description="Enable command batching")
    batch_window_ms: int = Field(default=50, description="Command batch window")
    
    # Security Settings
    device_auth_required: bool = Field(default=True, description="Require device authentication")
    encrypt_control_traffic: bool = Field(default=True, description="Encrypt control traffic")
    command_authorization: bool = Field(default=True, description="Enable command authorization")
    emergency_override_pin: str = Field(default="", description="Emergency override PIN")
    
    # Development Settings
    development_mode: bool = Field(default=False, description="Development mode")
    simulate_devices: bool = Field(default=False, description="Simulate devices for testing")
    log_device_commands: bool = Field(default=False, description="Log all device commands")
    
    @validator("allowed_origins", pre=True)
    def parse_allowed_origins(cls, v):
        """Parse allowed origins from string or list"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @validator("discovery_protocols", pre=True)
    def parse_discovery_protocols(cls, v):
        """Parse discovery protocols from string or list"""
        if isinstance(v, str):
            return [proto.strip() for proto in v.split(",")]
        return v
    
    def get_device_config(self, device_type: str) -> Dict[str, Any]:
        """Get configuration for specific device type"""
        configs = {
            'switcher': {
                'enabled': self.switcher_enabled,
                'default_type': self.default_switcher_type,
                'pool_size': self.switcher_connection_pool_size,
                'command_delay': self.switcher_command_delay_ms,
            },
            'camera': {
                'enabled': self.camera_enabled,
                'default_protocol': self.default_camera_protocol,
                'ptz_speed_scale': self.ptz_speed_scale,
                'preset_timeout': self.preset_recall_timeout,
                'home_on_startup': self.camera_home_on_startup,
                'max_speed': self.max_ptz_speed,
            },
            'audio': {
                'enabled': self.audio_enabled,
                'default_protocol': self.default_audio_protocol,
                'fade_curve': self.audio_fade_curve,
                'crossfade_time': self.default_crossfade_time,
                'meter_interval': self.audio_meter_interval,
            },
            'graphics': {
                'enabled': self.graphics_enabled,
                'default_protocol': self.default_graphics_protocol,
                'cache_size': self.template_cache_size,
                'preview_enabled': self.graphics_preview_enabled,
            },
            'lighting': {
                'enabled': self.lighting_enabled,
                'default_protocol': self.default_lighting_protocol,
                'universe_count': self.dmx_universe_count,
                'fade_time': self.lighting_fade_time,
            }
        }
        return configs.get(device_type, {})
    
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