"""Pydantic schemas for Metaverse Support Service"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, validator

# Base schemas
class MetaverseAssetBase(BaseModel):
    """Base schema for metaverse assets"""
    name: str
    description: Optional[str] = None
    asset_type: str  # "3d_model", "texture", "animation", "audio", "video"
    file_format: str
    file_size_mb: float
    created_at: Optional[datetime] = None

class MetaverseDeploymentBase(BaseModel):
    """Base schema for metaverse deployments"""
    asset_id: str
    platform: str
    status: str = "pending"
    deployed_at: Optional[datetime] = None

# Virtual World schemas
class VirtualWorldDeploymentRequest(BaseModel):
    """Request to deploy asset to virtual world"""
    asset_id: str = Field(..., description="ID of the asset to deploy")
    platform: str = Field(..., description="Target virtual world platform")
    deployment_config: Dict[str, Any] = Field(default_factory=dict, description="Platform-specific deployment configuration")
    
    @validator('platform')
    def validate_platform(cls, v):
        allowed_platforms = ["unity", "unreal", "vrchat", "horizon_worlds", "roblox", "minecraft", "fortnite_creative"]
        if v not in allowed_platforms:
            raise ValueError(f"Platform must be one of: {allowed_platforms}")
        return v

class VirtualWorldDeploymentResponse(BaseModel):
    """Response from virtual world deployment"""
    success: bool
    asset_id: str
    platform: str
    deployment_result: Dict[str, Any]
    message: Optional[str] = None

class MultiPlatformDeploymentRequest(BaseModel):
    """Request to deploy asset to multiple virtual world platforms"""
    asset_id: str = Field(..., description="ID of the asset to deploy")
    platforms: List[str] = Field(..., description="List of target platforms")
    deployment_configs: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict, 
        description="Platform-specific deployment configurations"
    )

class MultiPlatformDeploymentResponse(BaseModel):
    """Response from multi-platform deployment"""
    asset_id: str
    deployments: Dict[str, Any]
    total_platforms: int
    successful_deployments: int

class PlatformCapabilitiesResponse(BaseModel):
    """Platform capabilities response"""
    name: str
    supported_formats: List[str]
    max_asset_size_mb: int
    max_concurrent_users: int
    connection_status: str

# VR schemas
class VRDeploymentRequest(BaseModel):
    """Request to deploy asset for VR"""
    asset_id: str = Field(..., description="ID of the asset to deploy")
    vr_platform: str = Field(..., description="Target VR platform (oculus, steamvr, etc.)")
    target_fps: int = Field(default=90, description="Target frame rate for VR")
    comfort_settings: Dict[str, bool] = Field(
        default_factory=lambda: {
            "teleport_locomotion": True,
            "vignetting": True,
            "snap_turn": True
        }
    )
    headset_compatibility: List[str] = Field(
        default_factory=lambda: ["oculus_quest", "htc_vive", "valve_index"]
    )

class VRDeploymentResponse(BaseModel):
    """Response from VR deployment"""
    asset_id: str
    vr_platform: str
    vr_format: str
    target_fps: int
    comfort_settings: Dict[str, bool]
    deployment_url: Optional[str] = None
    status: str

# AR schemas
class ARDeploymentRequest(BaseModel):
    """Request to deploy asset for AR"""
    asset_id: str = Field(..., description="ID of the asset to deploy")
    ar_platform: str = Field(..., description="Target AR platform (arkit, arcore, etc.)")
    anchor_type: str = Field(default="plane", description="Type of AR anchor")
    scale_factor: float = Field(default=1.0, description="Scale factor for AR object")
    interaction_enabled: bool = Field(default=True, description="Enable user interactions")
    
    @validator('ar_platform')
    def validate_ar_platform(cls, v):
        allowed_platforms = ["arkit", "arcore", "hololens", "magic_leap"]
        if v not in allowed_platforms:
            raise ValueError(f"AR platform must be one of: {allowed_platforms}")
        return v
    
    @validator('anchor_type')
    def validate_anchor_type(cls, v):
        allowed_types = ["plane", "image", "object", "face", "world"]
        if v not in allowed_types:
            raise ValueError(f"Anchor type must be one of: {allowed_types}")
        return v

class ARDeploymentResponse(BaseModel):
    """Response from AR deployment"""
    asset_id: str
    ar_platform: str
    format: str
    anchor_type: str
    scale_factor: float
    deployment_url: Optional[str] = None
    status: str

class ARExperienceRequest(BaseModel):
    """Request to create AR experience"""
    asset_id: str
    experience_type: str = Field(default="basic_placement", description="Type of AR experience")
    interactions: List[str] = Field(default_factory=list, description="Available interactions")
    animations: List[str] = Field(default_factory=list, description="Available animations")
    audio_enabled: bool = Field(default=False, description="Enable audio in AR experience")
    multi_user: bool = Field(default=False, description="Support multiple users")

# Avatar schemas
class AvatarCreationRequest(BaseModel):
    """Request to create an avatar"""
    style: str = Field(default="realistic", description="Avatar style (realistic, anime, cartoon)")
    platform: str = Field(default="ready_player_me", description="Avatar creation platform")
    gender: str = Field(default="neutral", description="Avatar gender")
    customizations: Dict[str, Any] = Field(default_factory=dict, description="Avatar customizations")

class AvatarCreationResponse(BaseModel):
    """Response from avatar creation"""
    avatar_id: str
    platform: str
    style: str
    customizations: Dict[str, Any]
    export_formats: List[str]
    download_urls: Dict[str, str]
    created_at: datetime
    status: str

class AvatarAnimationRequest(BaseModel):
    """Request to animate an avatar"""
    avatar_id: str
    animation_type: str = Field(..., description="Type of animation (idle, walking, dancing, etc.)")
    duration: float = Field(default=5.0, description="Animation duration in seconds")
    loop: bool = Field(default=True, description="Whether animation should loop")
    transitions: List[str] = Field(default_factory=list, description="Animation transitions")

class AvatarOptimizationRequest(BaseModel):
    """Request to optimize avatar for platform"""
    avatar_id: str
    target_platform: str = Field(..., description="Target metaverse platform")
    optimization_level: str = Field(default="medium", description="Optimization level (low, medium, high)")
    
    @validator('optimization_level')
    def validate_optimization_level(cls, v):
        allowed_levels = ["low", "medium", "high", "ultra"]
        if v not in allowed_levels:
            raise ValueError(f"Optimization level must be one of: {allowed_levels}")
        return v

# Spatial Computing schemas
class SpatialAnchorRequest(BaseModel):
    """Request to create spatial anchor"""
    asset_id: str
    anchor_type: str = Field(..., description="Type of spatial anchor")
    coordinates: Dict[str, float] = Field(..., description="3D coordinates")
    persistence: bool = Field(default=True, description="Whether anchor should persist")

class SpatialMappingRequest(BaseModel):
    """Request for spatial mapping"""
    space_id: str
    mapping_resolution: float = Field(default=0.1, description="Mapping resolution in meters")
    include_semantics: bool = Field(default=True, description="Include semantic information")

# Cross-Platform schemas
class CrossPlatformAssetRequest(BaseModel):
    """Request to create cross-platform compatible asset"""
    asset_id: str
    target_platforms: List[str] = Field(..., description="List of target platforms")
    optimization_settings: Dict[str, Any] = Field(
        default_factory=dict,
        description="Platform-specific optimization settings"
    )
    quality_presets: Dict[str, str] = Field(
        default_factory=lambda: {
            "mobile": "medium",
            "vr": "high", 
            "ar": "high",
            "desktop": "ultra"
        }
    )

class CrossPlatformAssetResponse(BaseModel):
    """Response from cross-platform asset creation"""
    asset_id: str
    platform_versions: Dict[str, Dict[str, Any]]
    total_platforms: int
    successful_conversions: int
    failed_conversions: List[str]

# Blockchain schemas
class NFTMintRequest(BaseModel):
    """Request to mint NFT from metaverse asset"""
    asset_id: str
    blockchain: str = Field(default="ethereum", description="Target blockchain")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="NFT metadata")
    royalty_percentage: float = Field(default=0.0, ge=0, le=100, description="Royalty percentage")

class VirtualEconomyRequest(BaseModel):
    """Request for virtual economy integration"""
    asset_id: str
    virtual_world: str
    price_tokens: float = Field(..., description="Price in virtual tokens")
    tradeable: bool = Field(default=True, description="Whether asset can be traded")
    limited_edition: Optional[int] = Field(None, description="Limited edition count")

# Analytics schemas
class MetaverseAnalyticsRequest(BaseModel):
    """Request for metaverse analytics"""
    metric_type: str = Field(..., description="Type of metric to track")
    time_range: Dict[str, datetime] = Field(..., description="Time range for analytics")
    platforms: List[str] = Field(default_factory=list, description="Platforms to include")
    granularity: str = Field(default="daily", description="Data granularity")

class UserEngagementMetrics(BaseModel):
    """User engagement metrics in metaverse"""
    total_users: int
    active_sessions: int
    average_session_duration: float
    interactions_per_session: float
    retention_rate: float
    platform_breakdown: Dict[str, int]

# Social Features schemas
class VirtualEventRequest(BaseModel):
    """Request to create virtual event"""
    name: str
    description: str
    virtual_world: str
    start_time: datetime
    duration_hours: float
    max_participants: int = Field(default=100)
    event_type: str = Field(default="general", description="Type of event")

class SocialInteractionConfig(BaseModel):
    """Configuration for social interactions"""
    voice_chat: bool = Field(default=False)
    text_chat: bool = Field(default=True)
    gesture_system: bool = Field(default=True)
    friend_system: bool = Field(default=True)
    group_activities: List[str] = Field(default_factory=list)

# Health check and status schemas
class ServiceHealthResponse(BaseModel):
    """Service health check response"""
    status: str
    service: str
    version: str
    timestamp: datetime
    platforms: Dict[str, Any]
    active_deployments: int

class PlatformStatusResponse(BaseModel):
    """Platform status response"""
    platform_name: str
    status: str
    connection_quality: str
    active_sessions: int
    error_count: int
    last_health_check: datetime

# Configuration schemas
class MetaversePlatformConfig(BaseModel):
    """Configuration for metaverse platform"""
    platform_name: str
    enabled: bool = Field(default=True)
    api_credentials: Dict[str, str] = Field(default_factory=dict)
    rate_limits: Dict[str, int] = Field(default_factory=dict)
    optimization_settings: Dict[str, Any] = Field(default_factory=dict)

# Error schemas
class MetaverseError(BaseModel):
    """Metaverse service error response"""
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime
    request_id: Optional[str] = None

# WebRTC/Streaming schemas
class LiveStreamRequest(BaseModel):
    """Request to stream metaverse content"""
    asset_id: str
    stream_quality: str = Field(default="1080p", description="Stream quality")
    platform: str = Field(..., description="Target streaming platform")
    viewer_interaction: bool = Field(default=False, description="Allow viewer interaction")

class VoiceChatConfig(BaseModel):
    """Voice chat configuration for metaverse"""
    enabled: bool = Field(default=False)
    spatial_audio: bool = Field(default=True)
    voice_effects: bool = Field(default=False)
    noise_cancellation: bool = Field(default=True)
    quality: str = Field(default="medium", description="Audio quality")