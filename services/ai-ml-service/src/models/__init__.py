"""Models module for AI/ML Service"""

from .schemas import (
    TranscriptionRequest,
    TranscriptionResponse,
    ObjectDetectionRequest,
    ObjectDetectionResponse,
    FaceRecognitionRequest,
    FaceRecognitionResponse,
    SceneDetectionRequest,
    SceneDetectionResponse,
    AutoTaggingRequest,
    AutoTaggingResponse,
    ContentModerationRequest,
    ContentModerationResponse,
    SimilaritySearchRequest,
    SimilaritySearchResponse,
    VideoSummarizationRequest,
    VideoSummarizationResponse,
)

from .generative_schemas import (
    # Base models
    GenerativeRequest,
    GenerativeResponse,
    GenerationProvider,
    GenerationType,
    EnhancementType,
    # Text generation
    TextGenerationRequest,
    # Image generation
    ImageGenerationRequest,
    # Video generation
    VideoGenerationRequest,
    # Audio generation
    AudioGenerationRequest,
    # Enhancement
    ContentEnhancementRequest,
    # Creative tools
    StoryboardRequest,
    StoryboardFrame,
    ScriptGenerationRequest,
    CreativeAssistantRequest,
    BrainstormingRequest,
    # Batch processing
    BatchGenerationRequest,
    BatchGenerationResponse,
    # Analysis
    ContentAnalysisRequest,
    ContentAnalysisResponse,
    # Templates and usage
    GenerationTemplate,
    GenerationUsage,
    UsageSummary,
)

__all__ = [
    # Original AI/ML schemas
    "TranscriptionRequest",
    "TranscriptionResponse",
    "ObjectDetectionRequest",
    "ObjectDetectionResponse",
    "FaceRecognitionRequest",
    "FaceRecognitionResponse",
    "SceneDetectionRequest",
    "SceneDetectionResponse",
    "AutoTaggingRequest",
    "AutoTaggingResponse",
    "ContentModerationRequest",
    "ContentModerationResponse",
    "SimilaritySearchRequest",
    "SimilaritySearchResponse",
    "VideoSummarizationRequest",
    "VideoSummarizationResponse",
    # Generative AI schemas
    "GenerativeRequest",
    "GenerativeResponse",
    "GenerationProvider",
    "GenerationType",
    "EnhancementType",
    "TextGenerationRequest",
    "ImageGenerationRequest",
    "VideoGenerationRequest",
    "AudioGenerationRequest",
    "ContentEnhancementRequest",
    "StoryboardRequest",
    "StoryboardFrame",
    "ScriptGenerationRequest",
    "CreativeAssistantRequest",
    "BrainstormingRequest",
    "BatchGenerationRequest",
    "BatchGenerationResponse",
    "ContentAnalysisRequest",
    "ContentAnalysisResponse",
    "GenerationTemplate",
    "GenerationUsage",
    "UsageSummary",
]