"""Pydantic schemas for generative AI features"""

from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field, validator
from enum import Enum
import uuid


class GenerationProvider(str, Enum):
    """Supported generation providers"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    STABILITY = "stability"
    REPLICATE = "replicate"
    LOCAL = "local"
    HUGGINGFACE = "huggingface"


class GenerationType(str, Enum):
    """Types of content generation"""
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    CODE = "code"
    STORYBOARD = "storyboard"
    SCRIPT = "script"


class EnhancementType(str, Enum):
    """Types of content enhancement"""
    UPSCALE_IMAGE = "upscale_image"
    DENOISE_AUDIO = "denoise_audio"
    STABILIZE_VIDEO = "stabilize_video"
    REWRITE_TEXT = "rewrite_text"
    TRANSLATE = "translate"
    COLORIZE = "colorize"
    REMOVE_BACKGROUND = "remove_background"
    INTERPOLATE_FRAMES = "interpolate_frames"


# Base Request/Response Models

class GenerativeRequest(BaseModel):
    """Base request for generative AI"""
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    generation_type: GenerationType
    provider: Optional[GenerationProvider] = None
    model: Optional[str] = None
    user_id: str
    metadata: Optional[Dict[str, Any]] = None
    priority: int = Field(default=0, ge=0, le=10)
    callback_url: Optional[str] = None


class GenerativeResponse(BaseModel):
    """Base response for generative AI"""
    request_id: str
    status: str = Field(..., description="completed, failed, processing")
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    provider: str = "unknown"
    model_used: str = "unknown"
    processing_time: float = 0.0
    usage_metrics: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


# Text Generation Models

class TextGenerationRequest(BaseModel):
    """Request for text generation"""
    prompt: str = Field(..., description="Input prompt for generation")
    system_prompt: Optional[str] = Field(None, description="System prompt for context")
    max_tokens: Optional[int] = Field(1000, ge=1, le=32000)
    temperature: Optional[float] = Field(0.7, ge=0, le=2)
    top_p: Optional[float] = Field(0.9, ge=0, le=1)
    frequency_penalty: Optional[float] = Field(0, ge=-2, le=2)
    presence_penalty: Optional[float] = Field(0, ge=-2, le=2)
    stop_sequences: Optional[List[str]] = None
    num_outputs: Optional[int] = Field(1, ge=1, le=10)
    provider: Optional[GenerationProvider] = None
    model: Optional[str] = None
    
    class Config:
        schema_extra = {
            "example": {
                "prompt": "Write a creative story about AI and humans working together",
                "max_tokens": 500,
                "temperature": 0.8
            }
        }


# Image Generation Models

class ImageGenerationRequest(BaseModel):
    """Request for image generation"""
    prompt: str = Field(..., description="Text prompt for image generation")
    negative_prompt: Optional[str] = Field(None, description="What to avoid in the image")
    width: Optional[int] = Field(1024, ge=256, le=2048)
    height: Optional[int] = Field(1024, ge=256, le=2048)
    num_images: Optional[int] = Field(1, ge=1, le=4)
    style: Optional[str] = Field(None, description="Art style (realistic, artistic, etc)")
    quality: Optional[str] = Field("standard", description="standard or hd")
    seed: Optional[int] = Field(None, description="Seed for reproducibility")
    steps: Optional[int] = Field(30, ge=10, le=150)
    cfg_scale: Optional[float] = Field(7.5, ge=1, le=20)
    output_format: str = Field("url", description="url or base64")
    provider: Optional[GenerationProvider] = None
    model: Optional[str] = None
    
    @validator("width", "height")
    def validate_dimensions(cls, v):
        """Ensure dimensions are multiples of 8"""
        if v % 8 != 0:
            raise ValueError("Dimensions must be multiples of 8")
        return v


# Video Generation Models

class VideoGenerationRequest(BaseModel):
    """Request for video generation"""
    prompt: str = Field(..., description="Text prompt for video generation")
    duration: float = Field(5.0, ge=1, le=30, description="Duration in seconds")
    fps: int = Field(24, ge=8, le=60)
    width: Optional[int] = Field(1024, ge=256, le=1920)
    height: Optional[int] = Field(576, ge=256, le=1080)
    video_type: str = Field("text_to_video", description="text_to_video, image_to_video")
    init_image: Optional[str] = Field(None, description="Initial image URL for image_to_video")
    motion_amount: Optional[float] = Field(0.5, ge=0, le=1)
    seed: Optional[int] = None
    output_format: str = Field("mp4", description="mp4, webm, gif")
    provider: Optional[GenerationProvider] = None
    model: Optional[str] = None


# Audio Generation Models

class AudioGenerationRequest(BaseModel):
    """Request for audio generation"""
    text: str = Field(..., description="Text for TTS or prompt for music")
    audio_type: str = Field("speech", description="speech, music, sound_effect")
    voice: Optional[str] = Field(None, description="Voice ID for TTS")
    language: Optional[str] = Field("en", description="Language code")
    speed: Optional[float] = Field(1.0, ge=0.25, le=4.0)
    pitch: Optional[float] = Field(0, ge=-2, le=2)
    duration: Optional[float] = Field(None, description="Duration for music generation")
    genre: Optional[str] = Field(None, description="Music genre")
    instruments: Optional[List[str]] = Field(None, description="Instruments for music")
    mood: Optional[str] = Field(None, description="Mood/emotion")
    output_format: str = Field("mp3", description="mp3, wav, ogg")
    sample_rate: Optional[int] = Field(44100, description="Audio sample rate")
    provider: Optional[GenerationProvider] = None
    model: Optional[str] = None
    seed: Optional[int] = None


# Content Enhancement Models

class ContentEnhancementRequest(BaseModel):
    """Request for content enhancement"""
    content_url: Optional[str] = Field(None, description="URL of content to enhance")
    content_data: Optional[str] = Field(None, description="Raw content data (text/base64)")
    content_type: str = Field(..., description="text, image, video, audio")
    enhancement_type: EnhancementType
    parameters: Dict[str, Any] = Field(default_factory=dict)
    output_format: Optional[str] = None
    provider: Optional[GenerationProvider] = None
    user_id: str
    
    @validator("content_url", "content_data")
    def validate_content_source(cls, v, values):
        """Ensure either URL or data is provided"""
        if not v and not values.get("content_data") and not values.get("content_url"):
            raise ValueError("Either content_url or content_data must be provided")
        return v


# Storyboard Generation Models

class StoryboardRequest(BaseModel):
    """Request for storyboard generation"""
    script: str = Field(..., description="Script or scene descriptions")
    style: str = Field("realistic", description="Visual style for storyboard")
    aspect_ratio: str = Field("16:9", description="Aspect ratio of frames")
    frames_per_scene: int = Field(1, ge=1, le=5)
    include_camera_angles: bool = Field(True)
    include_shot_types: bool = Field(True)
    color_palette: Optional[str] = Field(None, description="Preferred color scheme")
    reference_images: Optional[List[str]] = Field(None, description="Reference image URLs")
    output_resolution: str = Field("1920x1080")
    metadata: Optional[Dict[str, Any]] = None


class StoryboardFrame(BaseModel):
    """Individual storyboard frame"""
    scene_number: int
    frame_number: int
    description: str
    image_url: str
    camera_angle: Optional[str] = None
    shot_type: Optional[str] = None
    duration: float = Field(5.0, description="Duration in seconds")
    dialogue: Optional[str] = None
    notes: Optional[str] = None


# Script Generation Models

class ScriptGenerationRequest(BaseModel):
    """Request for script generation"""
    outline: str = Field(..., description="Story outline or treatment")
    script_type: str = Field(..., description="screenplay, commercial, documentary, etc")
    genre: str = Field(..., description="Genre of the script")
    duration: int = Field(..., description="Target duration in minutes")
    target_audience: Optional[str] = None
    tone: Optional[str] = Field(None, description="Tone/mood of the script")
    characters: Optional[List[Dict[str, str]]] = None
    locations: Optional[List[str]] = None
    key_themes: Optional[List[str]] = None
    reference_scripts: Optional[List[str]] = None
    format_style: Optional[str] = Field("standard", description="Formatting style")
    include_directions: bool = Field(True)
    metadata: Optional[Dict[str, Any]] = None


# Creative Assistant Models

class CreativeAssistantRequest(BaseModel):
    """Request for creative assistance"""
    task_type: str = Field(..., description="brainstorm, critique, collaborate, suggest")
    context: str = Field(..., description="Current creative context")
    specific_request: str = Field(..., description="What help is needed")
    constraints: Optional[List[str]] = None
    preferences: Optional[Dict[str, Any]] = None
    examples: Optional[List[str]] = None
    interaction_mode: str = Field("single", description="single, conversation")


class BrainstormingRequest(BaseModel):
    """Request for brainstorming session"""
    topic: str = Field(..., description="Topic to brainstorm about")
    category: str = Field(..., description="Category (names, concepts, taglines, etc)")
    num_ideas: int = Field(10, ge=1, le=100)
    constraints: Optional[List[str]] = None
    style: Optional[str] = None
    diversity_level: float = Field(0.7, ge=0, le=1)
    include_reasoning: bool = Field(False)


# Batch Processing Models

class BatchGenerationRequest(BaseModel):
    """Request for batch content generation"""
    requests: List[Union[
        TextGenerationRequest,
        ImageGenerationRequest,
        AudioGenerationRequest
    ]]
    parallel_processing: bool = Field(True)
    max_parallel: int = Field(5, ge=1, le=20)
    stop_on_error: bool = Field(False)
    callback_url: Optional[str] = None


class BatchGenerationResponse(BaseModel):
    """Response for batch generation"""
    batch_id: str
    total_requests: int
    completed: int = 0
    failed: int = 0
    results: List[GenerativeResponse] = Field(default_factory=list)
    status: str = Field("processing")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None


# Content Analysis Models

class ContentAnalysisRequest(BaseModel):
    """Request for AI content analysis"""
    content_url: str
    content_type: str = Field(..., description="image, video, audio, text")
    analysis_types: List[str] = Field(..., description="caption, transcribe, sentiment, etc")
    language: Optional[str] = Field("en")
    detail_level: str = Field("standard", description="basic, standard, detailed")
    custom_prompts: Optional[Dict[str, str]] = None


class ContentAnalysisResponse(BaseModel):
    """Response for content analysis"""
    content_url: str
    content_type: str
    analyses: Dict[str, Any] = Field(default_factory=dict)
    confidence_scores: Dict[str, float] = Field(default_factory=dict)
    processing_time: float
    metadata: Dict[str, Any] = Field(default_factory=dict)


# Template Models

class GenerationTemplate(BaseModel):
    """Template for common generation tasks"""
    template_id: str
    name: str
    description: str
    category: str
    generation_type: GenerationType
    base_parameters: Dict[str, Any]
    variable_parameters: List[str]
    examples: Optional[List[Dict[str, Any]]] = None
    tags: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# Usage and Cost Models

class GenerationUsage(BaseModel):
    """Track usage and costs for generation"""
    user_id: str
    request_id: str
    generation_type: GenerationType
    provider: str
    model: str
    tokens_used: Optional[int] = None
    compute_seconds: Optional[float] = None
    storage_bytes: Optional[int] = None
    cost_estimate: float
    actual_cost: Optional[float] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class UsageSummary(BaseModel):
    """Summary of generation usage"""
    user_id: str
    period_start: datetime
    period_end: datetime
    total_requests: int
    total_cost: float
    by_type: Dict[str, Dict[str, Any]]
    by_provider: Dict[str, Dict[str, Any]]
    top_models: List[Dict[str, Any]]
    usage_trend: List[Dict[str, Any]]