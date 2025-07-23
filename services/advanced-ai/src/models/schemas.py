"""
Pydantic schemas for Advanced AI Service
"""

from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, validator
from datetime import datetime, date
from enum import Enum
import uuid


class PredictionType(str, Enum):
    """Types of predictions"""
    USAGE = "usage"
    STORAGE = "storage"
    COST = "cost"
    MAINTENANCE = "maintenance"
    PERFORMANCE = "performance"


class ModelType(str, Enum):
    """Machine learning model types"""
    PROPHET = "prophet"
    ARIMA = "arima"
    LSTM = "lstm"
    XGBOOST = "xgboost"
    RANDOM_FOREST = "random_forest"
    LINEAR_REGRESSION = "linear_regression"
    ENSEMBLE = "ensemble"


class StorageTier(str, Enum):
    """Storage tier types"""
    HOT = "hot"
    WARM = "warm"
    COLD = "cold"
    ARCHIVE = "archive"


class RecommendationType(str, Enum):
    """Recommendation types"""
    SIMILAR_CONTENT = "similar_content"
    COLLABORATIVE = "collaborative"
    TRENDING = "trending"
    PERSONALIZED = "personalized"
    WORKFLOW = "workflow"


class TagCategory(str, Enum):
    """Auto-tag categories"""
    OBJECT = "object"
    SCENE = "scene"
    CONTENT = "content"
    VISUAL = "visual"
    TECHNICAL = "technical"
    CONTEXT = "context"
    MODERATION = "moderation"
    TEMPORAL = "temporal"
    AUDIO = "audio"


class TagSource(str, Enum):
    """Tag source systems"""
    YOLO = "yolo"
    HUGGINGFACE = "huggingface"
    OCR = "ocr"
    ANALYSIS = "analysis"
    MODERATION = "moderation"
    METADATA = "metadata"
    SYSTEM = "system"
    USER = "user"
    WHISPER = "whisper"


class TagConfidence(str, Enum):
    """Tag confidence levels"""
    VERY_HIGH = "very_high"  # > 0.9
    HIGH = "high"            # 0.7 - 0.9
    MEDIUM = "medium"        # 0.5 - 0.7
    LOW = "low"              # 0.3 - 0.5
    VERY_LOW = "very_low"    # < 0.3


class SummaryType(str, Enum):
    """Video summary types"""
    HIGHLIGHTS = "highlights"
    SCENES = "scenes"
    TRANSCRIPT = "transcript"
    ACTION = "action"
    INTELLIGENT = "intelligent"


class ClusteringMethod(str, Enum):
    """Clustering methods"""
    KMEANS = "kmeans"
    DBSCAN = "dbscan"
    HIERARCHICAL = "hierarchical"
    SPECTRAL = "spectral"


# Content Clustering Schemas

class ContentCluster(BaseModel):
    """Content cluster information"""
    cluster_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: Optional[str] = None
    description: Optional[str] = None
    cluster_size: int
    representative_assets: List[str] = Field(default_factory=list)
    cluster_center: Optional[List[float]] = None
    dominant_features: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    
    @validator('cluster_center')
    def validate_cluster_center(cls, v):
        if v is not None:
            return [float(x) for x in v]
        return v


class ContentSimilarity(BaseModel):
    """Content similarity result"""
    asset_id: str
    similarity_score: float = Field(ge=0, le=1)
    matching_features: List[str] = Field(default_factory=list)
    cluster_id: Optional[str] = None
    explanation: Optional[str] = None


class ClusteringRequest(BaseModel):
    """Request for content clustering"""
    asset_ids: List[str]
    clustering_method: ClusteringMethod = ClusteringMethod.DBSCAN
    feature_types: Optional[List[str]] = None
    options: Optional[Dict[str, Any]] = None
    min_cluster_size: int = Field(default=3, ge=1)
    max_clusters: Optional[int] = None


class ClusterStatistics(BaseModel):
    """Clustering analysis statistics"""
    total_assets: int
    total_clusters: int
    largest_cluster_size: int
    smallest_cluster_size: int
    average_cluster_size: float
    silhouette_score: float = Field(ge=-1, le=1)
    outliers_count: int = Field(default=0)
    cluster_distribution: Dict[str, int] = Field(default_factory=dict)


class ClusteringResult(BaseModel):
    """Result of clustering operation"""
    clusters: List[ContentCluster]
    statistics: ClusterStatistics
    processing_time_seconds: float
    feature_types: List[str]
    method: ClusteringMethod
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SimilarityRequest(BaseModel):
    """Request for content similarity search"""
    asset_id: str
    similarity_threshold: float = Field(default=0.7, ge=0, le=1)
    max_results: int = Field(default=10, ge=1, le=100)
    feature_types: Optional[List[str]] = None
    exclude_clusters: Optional[List[str]] = None


class ClusterRecommendationRequest(BaseModel):
    """Request for cluster-based recommendations"""
    user_id: str
    max_recommendations: int = Field(default=20, ge=1, le=100)
    exclude_seen: bool = Field(default=True)
    cluster_preferences: Optional[Dict[str, float]] = None


class FeatureImportance(BaseModel):
    """Feature importance for clustering"""
    feature_type: str
    importance_score: float = Field(ge=0, le=1)
    contribution_percentage: float = Field(ge=0, le=100)
    examples: List[str] = Field(default_factory=list)


class ClusterAnalysis(BaseModel):
    """Detailed cluster analysis"""
    cluster_id: str
    centroid_description: str
    feature_importance: List[FeatureImportance]
    representative_samples: List[str]
    cluster_themes: List[str] = Field(default_factory=list)
    quality_metrics: Dict[str, float] = Field(default_factory=dict)
    suggestions: List[str] = Field(default_factory=list)


# Usage Prediction Models
class UsagePattern(BaseModel):
    """Historical usage pattern"""
    asset_id: str
    timestamp: datetime
    access_count: int
    unique_users: int
    total_duration_seconds: float
    average_session_duration: float
    peak_hour: int
    day_of_week: int
    metadata: Dict[str, Any] = Field(default_factory=dict)


class UsagePrediction(BaseModel):
    """Usage prediction result"""
    prediction_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    asset_id: str
    prediction_date: date
    predicted_access_count: float
    confidence_interval_lower: float
    confidence_interval_upper: float
    confidence_score: float = Field(ge=0, le=1)
    model_used: ModelType
    features_used: List[str]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class UsagePredictionRequest(BaseModel):
    """Request for usage prediction"""
    asset_ids: Optional[List[str]] = Field(default=None, description="Specific assets to predict")
    horizon_days: int = Field(default=30, ge=1, le=365)
    include_confidence_intervals: bool = Field(default=True)
    models_to_use: Optional[List[ModelType]] = None


class UsageTrend(BaseModel):
    """Usage trend analysis"""
    asset_id: str
    trend_direction: str = Field(description="increasing, decreasing, stable")
    trend_strength: float = Field(ge=0, le=1)
    seasonal_pattern: Optional[str] = None
    peak_periods: List[Dict[str, Any]]
    forecast_accuracy: float = Field(ge=0, le=1)


# Storage Optimization Models
class StorageMetrics(BaseModel):
    """Storage metrics for an asset"""
    asset_id: str
    current_tier: StorageTier
    size_bytes: int
    last_accessed: datetime
    access_frequency_daily: float
    access_frequency_weekly: float
    access_frequency_monthly: float
    age_days: int
    cost_per_month: float


class StorageRecommendation(BaseModel):
    """Storage tier recommendation"""
    asset_id: str
    current_tier: StorageTier
    recommended_tier: StorageTier
    confidence_score: float = Field(ge=0, le=1)
    estimated_cost_savings_monthly: float
    estimated_access_time_change_ms: float
    reasoning: str
    transition_date: Optional[date] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class StorageOptimizationPlan(BaseModel):
    """Overall storage optimization plan"""
    plan_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    total_assets: int
    recommendations: List[StorageRecommendation]
    total_cost_savings_monthly: float
    total_storage_to_move_gb: float
    implementation_priority: List[str]  # Asset IDs in priority order
    created_at: datetime = Field(default_factory=datetime.utcnow)


# Content Recommendation Models
class ContentFeatures(BaseModel):
    """Features extracted from content"""
    asset_id: str
    content_type: str
    duration_seconds: Optional[float] = None
    tags: List[str] = Field(default_factory=list)
    categories: List[str] = Field(default_factory=list)
    technical_metadata: Dict[str, Any] = Field(default_factory=dict)
    visual_features: Optional[List[float]] = None
    audio_features: Optional[List[float]] = None
    text_embeddings: Optional[List[float]] = None


class ContentRecommendation(BaseModel):
    """Content recommendation"""
    recommended_asset_id: str
    score: float = Field(ge=0, le=1)
    recommendation_type: RecommendationType
    reason: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RecommendationRequest(BaseModel):
    """Request for content recommendations"""
    user_id: Optional[str] = None
    asset_id: Optional[str] = None
    recommendation_type: RecommendationType = RecommendationType.PERSONALIZED
    max_recommendations: int = Field(default=20, ge=1, le=100)
    filters: Optional[Dict[str, Any]] = None


class RecommendationResponse(BaseModel):
    """Response with recommendations"""
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    recommendations: List[ContentRecommendation]
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    cache_ttl_seconds: int
    model_version: str


# Predictive Maintenance Models
class SystemMetrics(BaseModel):
    """System health metrics"""
    component_id: str
    component_type: str
    timestamp: datetime
    cpu_usage: float = Field(ge=0, le=100)
    memory_usage: float = Field(ge=0, le=100)
    disk_usage: float = Field(ge=0, le=100)
    error_rate: float = Field(ge=0)
    response_time_ms: float = Field(ge=0)
    throughput: float = Field(ge=0)
    temperature: Optional[float] = None
    custom_metrics: Dict[str, float] = Field(default_factory=dict)


class MaintenancePrediction(BaseModel):
    """Predictive maintenance result"""
    component_id: str
    component_type: str
    failure_probability: float = Field(ge=0, le=1)
    predicted_failure_date: Optional[date] = None
    confidence_score: float = Field(ge=0, le=1)
    risk_level: str = Field(description="low, medium, high, critical")
    recommended_actions: List[str]
    contributing_factors: List[Dict[str, Any]]
    created_at: datetime = Field(default_factory=datetime.utcnow)


class MaintenanceAlert(BaseModel):
    """Maintenance alert"""
    alert_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    component_id: str
    severity: str = Field(description="info, warning, critical")
    message: str
    predicted_failure_date: Optional[date] = None
    recommended_action: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    acknowledged: bool = Field(default=False)


# Cost Optimization Models
class CostMetrics(BaseModel):
    """Cost metrics for resources"""
    resource_id: str
    resource_type: str
    period_start: date
    period_end: date
    storage_cost: float
    compute_cost: float
    transfer_cost: float
    total_cost: float
    usage_efficiency: float = Field(ge=0, le=1)


class CostOptimizationSuggestion(BaseModel):
    """Cost optimization suggestion"""
    suggestion_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    resource_id: str
    resource_type: str
    current_cost_monthly: float
    projected_cost_monthly: float
    savings_monthly: float
    savings_percentage: float
    optimization_type: str
    description: str
    implementation_effort: str = Field(description="low, medium, high")
    risk_level: str = Field(description="low, medium, high")
    steps: List[str]


class CostForecast(BaseModel):
    """Cost forecast"""
    forecast_date: date
    forecasted_cost: float
    confidence_interval_lower: float
    confidence_interval_upper: float
    breakdown: Dict[str, float]  # Cost by category
    influencing_factors: List[str]


# Content Intelligence Models
class VideoSummary(BaseModel):
    """Video summarization result"""
    asset_id: str
    original_duration_seconds: float
    summary_duration_seconds: float
    key_moments: List[Dict[str, Any]]  # timestamp, description, confidence
    scene_changes: List[float]  # Timestamps
    summary_video_url: Optional[str] = None
    thumbnail_urls: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AutoTag(BaseModel):
    """Auto-generated tag"""
    tag: str
    confidence: float = Field(ge=0, le=1)
    category: str = Field(description="object, scene, action, emotion, technical")
    source: str = Field(description="visual, audio, text, metadata")


class ContentCluster(BaseModel):
    """Content cluster"""
    cluster_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    cluster_name: Optional[str] = None
    cluster_description: Optional[str] = None
    centroid_asset_id: Optional[str] = None
    member_asset_ids: List[str]
    cluster_size: int
    cluster_cohesion: float = Field(ge=0, le=1)
    top_tags: List[str]
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AISearchQuery(BaseModel):
    """AI-powered search query"""
    query: str
    search_type: str = Field(default="hybrid", description="keyword, semantic, visual, hybrid")
    filters: Optional[Dict[str, Any]] = None
    boost_recent: bool = Field(default=True)
    personalize: bool = Field(default=True)
    explain_results: bool = Field(default=False)
    max_results: int = Field(default=20, ge=1, le=100)


class AISearchResult(BaseModel):
    """AI search result"""
    asset_id: str
    score: float = Field(ge=0, le=1)
    match_type: str = Field(description="exact, semantic, visual, related")
    explanation: Optional[str] = None
    highlights: Optional[Dict[str, List[str]]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


# Model Management
class MLModel(BaseModel):
    """Machine learning model metadata"""
    model_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    model_type: ModelType
    model_name: str
    version: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_trained: datetime
    training_metrics: Dict[str, float]
    validation_metrics: Dict[str, float]
    feature_importance: Optional[Dict[str, float]] = None
    parameters: Dict[str, Any]
    is_active: bool = Field(default=True)


class TrainingJob(BaseModel):
    """Model training job"""
    job_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    model_type: ModelType
    status: str = Field(default="pending", description="pending, running, completed, failed")
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    training_data_size: int
    validation_data_size: int
    epochs_completed: int = Field(default=0)
    current_loss: Optional[float] = None
    best_validation_score: Optional[float] = None
    error_message: Optional[str] = None


# Analytics Models
class PredictionAnalytics(BaseModel):
    """Analytics for predictions"""
    prediction_type: PredictionType
    period_start: date
    period_end: date
    total_predictions: int
    average_accuracy: float = Field(ge=0, le=1)
    model_performance: Dict[str, Dict[str, float]]
    top_predicted_assets: List[Dict[str, Any]]
    error_analysis: Dict[str, Any]


# Video Summarization Models
class SummaryType(str, Enum):
    """Video summary types"""
    HIGHLIGHTS = "highlights"
    SCENES = "scenes"
    TRANSCRIPT = "transcript"
    ACTION = "action"
    INTELLIGENT = "intelligent"


class SummarySegment(BaseModel):
    """Video summary segment"""
    segment_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    start_time: float = Field(ge=0, description="Start time in seconds")
    end_time: float = Field(ge=0, description="End time in seconds")
    duration: float = Field(ge=0, description="Duration in seconds")
    importance_score: float = Field(ge=0, le=1, description="Importance score")
    scene_type: str = Field(description="Type of scene: action, dialogue, visual, etc.")
    description: str = Field(description="Brief description of the segment")
    keyframe_path: Optional[str] = None
    transcript_text: Optional[str] = None


class KeyFrame(BaseModel):
    """Key frame from video"""
    timestamp: float = Field(ge=0, description="Timestamp in seconds")
    frame_number: int = Field(ge=0, description="Frame number")
    thumbnail_path: str = Field(description="Path to thumbnail image")
    importance_score: float = Field(ge=0, le=1, description="Importance score")


class TranscriptHighlight(BaseModel):
    """Highlighted transcript segment"""
    start_time: float = Field(ge=0, description="Start time in seconds")
    end_time: float = Field(ge=0, description="End time in seconds")
    text: str = Field(description="Transcript text")
    confidence: float = Field(ge=0, le=1, description="Transcription confidence")
    importance_score: float = Field(ge=0, le=1, default=0.5)


class VideoSummary(BaseModel):
    """Video summary result"""
    summary_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    asset_id: str
    original_duration: float = Field(ge=0, description="Original video duration in seconds")
    summary_duration: float = Field(ge=0, description="Summary duration in seconds")
    target_duration_percent: int = Field(ge=1, le=100, description="Target duration percentage")
    actual_duration_percent: float = Field(ge=0, le=100, description="Actual duration percentage")
    summary_type: SummaryType
    segments: List[SummarySegment]
    keyframes: List[KeyFrame] = Field(default_factory=list)
    transcript_highlights: List[TranscriptHighlight] = Field(default_factory=list)
    confidence_score: float = Field(ge=0, le=1, description="Overall confidence")
    processing_time: float = Field(ge=0, description="Processing time in seconds")
    model_used: ModelType
    summary_video_path: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class VideoSummaryRequest(BaseModel):
    """Request for video summarization"""
    asset_id: str
    target_duration_percent: int = Field(default=10, ge=1, le=50)
    summary_type: SummaryType = Field(default=SummaryType.INTELLIGENT)
    include_keyframes: bool = Field(default=True)
    include_transcript: bool = Field(default=True)
    generate_video_file: bool = Field(default=False)
    options: Optional[Dict[str, Any]] = Field(default_factory=dict)


# System Component Models (for maintenance)
class SystemComponent(BaseModel):
    """System component for monitoring"""
    component_id: str
    component_type: str
    component_name: str
    location: Optional[str] = None
    is_critical: bool = Field(default=False)


class RiskLevel(str, Enum):
    """Risk levels for maintenance predictions"""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertSeverity(str, Enum):
    """Alert severity levels"""
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MaintenancePrediction(BaseModel):
    """Predictive maintenance result"""
    prediction_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    component_id: str
    component_type: str
    component_name: str
    risk_level: RiskLevel
    failure_probability: float = Field(ge=0, le=1)
    predicted_failure_date: Optional[date] = None
    last_maintenance_date: Optional[date] = None
    recommended_actions: List[str]
    confidence_score: float = Field(ge=0, le=1)
    contributing_factors: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class MaintenanceAlert(BaseModel):
    """Maintenance alert"""
    alert_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    component_id: str
    component_type: str
    component_name: str
    severity: AlertSeverity
    title: str
    description: str
    recommended_actions: List[str]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    acknowledged: bool = Field(default=False)
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None


# Auto-Tagging Schemas

class AutoTag(BaseModel):
    """Auto-generated tag for content"""
    tag_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    asset_id: str
    tag_name: str
    category: TagCategory
    confidence: float = Field(ge=0, le=1)
    source: TagSource
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    @validator('confidence')
    def validate_confidence(cls, v):
        return round(v, 3)


class AutoTagRequest(BaseModel):
    """Request for auto-tagging"""
    asset_id: str
    file_path: str
    asset_type: str
    options: Optional[Dict[str, Any]] = None
    min_confidence: float = Field(default=0.5, ge=0, le=1)
    categories: Optional[List[TagCategory]] = None
    force_reanalysis: bool = Field(default=False)


class AutoTagResponse(BaseModel):
    """Response for auto-tagging"""
    asset_id: str
    tags: List[AutoTag]
    processing_time_seconds: float
    analysis_summary: Dict[str, Any]
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ContentModerationResult(BaseModel):
    """Content moderation analysis result"""
    moderation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    asset_id: str
    overall_score: float = Field(ge=0, le=1)
    flagged: bool
    categories: List[Dict[str, float]]
    risk_level: str
    reviewed: bool = Field(default=False)
    reviewer_id: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class OCRResult(BaseModel):
    """OCR text extraction result"""
    ocr_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    asset_id: str
    extracted_text: str
    confidence: float = Field(ge=0, le=1)
    language: Optional[str] = None
    bounding_boxes: List[Dict[str, Any]] = Field(default_factory=list)
    page_number: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AudioClassificationResult(BaseModel):
    """Audio content classification result"""
    classification_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    asset_id: str
    content_type: str  # speech, music, noise, silence
    confidence: float = Field(ge=0, le=1)
    features: Dict[str, float]
    segments: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class TagStatistics(BaseModel):
    """Statistics for auto-tagging"""
    total_tags: int
    tags_by_category: Dict[TagCategory, int]
    tags_by_source: Dict[TagSource, int]
    average_confidence: float
    confidence_distribution: Dict[str, int]
    top_tags: List[Dict[str, Any]]
    processing_time_avg: float
    last_updated: datetime = Field(default_factory=datetime.utcnow)