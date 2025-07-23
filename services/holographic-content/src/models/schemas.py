"""Pydantic schemas for holographic content service"""

from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional, Literal
from datetime import datetime
from enum import Enum


# Enums
class CaptureDevice(str, Enum):
    AZURE_KINECT = "azure_kinect"
    INTEL_REALSENSE = "intel_realsense"
    DEPTHKIT = "depthkit"
    EVERCOAST = "evercoast"
    SCATTER = "scatter"


class DisplayDevice(str, Enum):
    LOOKING_GLASS_PORTRAIT = "looking_glass_portrait"
    LOOKING_GLASS_8K = "looking_glass_8k"
    LEIA_LUME_PAD = "leia_lume_pad"
    HOLOXICA_MEDICAL = "holoxica_medical"


class ProjectionDevice(str, Enum):
    HOLOLENS2 = "hololens2"
    MAGIC_LEAP_2 = "magic_leap_2"
    DREAMOC_HD3 = "dreamoc_hd3"
    MDH_SILVER = "mdh_silver"


class StreamingProtocol(str, Enum):
    WEBRTC = "webrtc"
    PIXEL_STREAMING = "pixel_streaming"
    HOLOGRAPHIC_STREAM = "holographic_stream"
    HLS_DASH = "hls_dash"


class NeuralModel(str, Enum):
    INSTANT_NGP = "instant_ngp"
    NERF = "nerf"
    MIP_NERF = "mip_nerf"
    NERFACTO = "nerfacto"
    GAUSSIAN_SPLATTING = "gaussian_splatting"
    NEURAL_VOLUMES = "neural_volumes"
    NEURAL_ACTOR = "neural_actor"


class InteractionMethod(str, Enum):
    HAND_TRACKING = "hand_tracking"
    EYE_TRACKING = "eye_tracking"
    VOICE_CONTROL = "voice_control"
    CONTROLLERS = "controllers"
    NEURAL_INTERFACE = "neural_interface"


class GestureType(str, Enum):
    TAP = "tap"
    PINCH = "pinch"
    GRAB = "grab"
    SWIPE = "swipe"
    ROTATE = "rotate"
    BLOOM = "bloom"
    POINT = "point"


class QualityProfile(str, Enum):
    MOBILE = "mobile"
    STANDARD = "standard"
    HIGH = "high"
    ULTRA = "ultra"
    VR = "vr"


# Request/Response Models

# Capture
class HologramCaptureRequest(BaseModel):
    device: CaptureDevice = Field(default=CaptureDevice.AZURE_KINECT)
    duration: int = Field(default=10, ge=1, le=300, description="Capture duration in seconds")
    fps: int = Field(default=30, ge=15, le=120)
    quality: str = Field(default="high")
    camera_count: Optional[int] = Field(default=None, ge=1, le=10)
    config: Optional[Dict[str, Any]] = Field(default_factory=dict)


class HologramCaptureResponse(BaseModel):
    capture_id: str
    device: str
    status: str
    capabilities: Dict[str, Any]


# Processing
class HologramProcessRequest(BaseModel):
    hologram_id: str
    processing_type: Literal["neural", "light_field", "traditional"]
    target_device: Optional[str] = None
    quality: str = Field(default="standard")
    config: Optional[Dict[str, Any]] = Field(default_factory=dict)


class HologramProcessResponse(BaseModel):
    process_id: str
    hologram_id: str
    status: str
    output: Optional[Dict[str, Any]] = None


class NeuralRenderRequest(BaseModel):
    hologram_id: str
    model: NeuralModel = Field(default=NeuralModel.INSTANT_NGP)
    quality: str = Field(default="high")
    enable_relighting: bool = Field(default=False)
    enable_material_editing: bool = Field(default=False)
    config: Optional[Dict[str, Any]] = Field(default_factory=dict)


class NeuralRenderResponse(BaseModel):
    render_id: str
    model: str
    status: str
    capabilities: Dict[str, Any]


class LightFieldProcessRequest(BaseModel):
    hologram_id: str
    target_display: DisplayDevice
    ai_enhance: bool = Field(default=True)
    compression: Optional[str] = Field(default="lz4")
    config: Optional[Dict[str, Any]] = Field(default_factory=dict)


# Display
class HologramDisplayRequest(BaseModel):
    hologram_id: str
    display_type: Literal["light_field", "projection", "volumetric"]
    device: str
    duration: Optional[int] = Field(default=0, description="0 for indefinite")
    config: Optional[Dict[str, Any]] = Field(default_factory=dict)


class HologramDisplayResponse(BaseModel):
    display_id: str
    device: str
    status: str
    capabilities: Dict[str, Any]


class LightFieldDisplayRequest(BaseModel):
    hologram_id: str
    device: DisplayDevice = Field(default=DisplayDevice.LOOKING_GLASS_PORTRAIT)
    depth_inversion: bool = Field(default=False)
    zoom: float = Field(default=1.0, ge=0.1, le=10.0)
    focus: float = Field(default=0.0, ge=-1.0, le=1.0)
    brightness: float = Field(default=0.8, ge=0.0, le=1.0)
    duration: Optional[int] = Field(default=0)
    config: Optional[Dict[str, Any]] = Field(default_factory=dict)


class ProjectionRequest(BaseModel):
    hologram_id: str
    device: ProjectionDevice = Field(default=ProjectionDevice.HOLOLENS2)
    position: List[float] = Field(default=[0, 0, 2])
    rotation: List[float] = Field(default=[0, 0, 0])
    scale: List[float] = Field(default=[1, 1, 1])
    occlusion: bool = Field(default=True)
    physics: bool = Field(default=False)
    persistence: bool = Field(default=True)
    config: Optional[Dict[str, Any]] = Field(default_factory=dict)


class ProjectionResponse(BaseModel):
    projection_id: str
    device: str
    status: str
    capabilities: Dict[str, Any]


# Interaction
class InteractionSessionRequest(BaseModel):
    hologram_id: str
    methods: List[InteractionMethod] = Field(
        default=[InteractionMethod.HAND_TRACKING, InteractionMethod.VOICE_CONTROL]
    )
    haptic_enabled: bool = Field(default=False)
    config: Optional[Dict[str, Any]] = Field(default_factory=dict)


class SpatialInteractionRequest(BaseModel):
    hologram_id: str
    interaction_type: Literal["gesture", "voice", "gaze", "controller"]
    enable_haptics: bool = Field(default=False)
    config: Optional[Dict[str, Any]] = Field(default_factory=dict)


class SpatialInteractionResponse(BaseModel):
    session_id: str
    hologram_id: str
    enabled_methods: List[str]
    status: str


class GestureInput(BaseModel):
    gesture_type: GestureType
    hand: Literal["left", "right", "both"] = Field(default="right")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict)


class VoiceCommand(BaseModel):
    command: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    language: str = Field(default="en")


class EyeGazeData(BaseModel):
    target: Optional[str] = None
    gaze_point: Dict[str, float] = Field(description="x, y coordinates")
    dwell_time: float = Field(default=0.0, ge=0.0)
    pupil_diameter: Optional[float] = None


# Streaming
class StreamingRequest(BaseModel):
    hologram_id: str
    protocol: StreamingProtocol = Field(default=StreamingProtocol.WEBRTC)
    quality: QualityProfile = Field(default=QualityProfile.STANDARD)
    adaptive_bitrate: bool = Field(default=True)
    low_latency: bool = Field(default=True)
    config: Optional[Dict[str, Any]] = Field(default_factory=dict)


class StreamingResponse(BaseModel):
    stream_id: str
    protocol: str
    status: str
    endpoints: Dict[str, Any]
    quality_profile: str
    capabilities: Dict[str, Any]


class ViewerInfo(BaseModel):
    device: str = Field(default="unknown")
    location: Optional[str] = None
    quality: str = Field(default="auto")
    bandwidth: Optional[int] = None


class StreamMetricsResponse(BaseModel):
    stream_id: str
    status: str
    duration_seconds: float
    viewer_count: int
    metrics: Dict[str, Any]
    total_data_gb: float
    average_bitrate: int
    current_quality: str
    protocol: str


# Database Models
class HologramRecord(BaseModel):
    id: str
    capture_id: Optional[str] = None
    process_id: Optional[str] = None
    format: str
    size_bytes: int
    duration_seconds: Optional[float] = None
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: Optional[datetime] = None


class CaptureSession(BaseModel):
    id: str
    device: str
    status: str
    start_time: datetime
    end_time: Optional[datetime] = None
    frames_captured: int
    output: Optional[Dict[str, Any]] = None


class RenderSession(BaseModel):
    id: str
    hologram_id: str
    model: str
    status: str
    progress: float
    start_time: datetime
    end_time: Optional[datetime] = None
    output: Optional[Dict[str, Any]] = None


class InteractionLog(BaseModel):
    session_id: str
    timestamp: datetime
    interaction_type: str
    data: Dict[str, Any]
    response: Optional[Dict[str, Any]] = None