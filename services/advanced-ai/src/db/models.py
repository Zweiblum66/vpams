"""
Database models for Advanced AI Service
"""

from sqlalchemy import (
    Column, String, DateTime, Integer, Float, Boolean,
    Text, JSON, Enum, ForeignKey, Index, UniqueConstraint, Date,
    LargeBinary, CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from .base import Base
from ..models.schemas import (
    PredictionType, ModelType, StorageTier,
    RecommendationType, ClusteringMethod
)


class UsageHistoryModel(Base):
    """Historical usage data"""
    __tablename__ = "usage_history"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    asset_id = Column(String(255), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    access_count = Column(Integer, default=0)
    unique_users = Column(Integer, default=0)
    total_duration_seconds = Column(Float, default=0.0)
    average_session_duration = Column(Float, default=0.0)
    peak_hour = Column(Integer, default=0)
    day_of_week = Column(Integer, default=0)
    metadata = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index("idx_usage_history_asset_timestamp", "asset_id", "timestamp"),
        Index("idx_usage_history_timestamp", "timestamp"),
    )


class PredictionModel(Base):
    """Predictions made by AI models"""
    __tablename__ = "predictions"
    
    prediction_id = Column(String(255), primary_key=True, default=lambda: str(uuid.uuid4()))
    prediction_type = Column(Enum(PredictionType), nullable=False)
    asset_id = Column(String(255), nullable=False)
    prediction_date = Column(Date, nullable=False)
    predicted_value = Column(Float, nullable=False)
    confidence_score = Column(Float, default=0.0)
    model_used = Column(Enum(ModelType), nullable=False)
    metadata = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index("idx_predictions_type_asset", "prediction_type", "asset_id"),
        Index("idx_predictions_date", "prediction_date"),
        Index("idx_predictions_created", "created_at"),
    )


class ModelMetadataModel(Base):
    """ML model metadata and versions"""
    __tablename__ = "model_metadata"
    
    model_id = Column(String(255), primary_key=True, default=lambda: str(uuid.uuid4()))
    model_type = Column(Enum(ModelType), nullable=False)
    model_name = Column(String(255), nullable=False)
    version = Column(String(50), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    last_trained = Column(DateTime(timezone=True), nullable=False)
    training_metrics = Column(JSON, default=dict)
    validation_metrics = Column(JSON, default=dict)
    feature_importance = Column(JSON, default=dict)
    parameters = Column(JSON, default=dict)
    is_active = Column(Boolean, default=True)
    model_path = Column(String(1024), nullable=True)
    
    # Indexes
    __table_args__ = (
        UniqueConstraint("model_type", "version", name="uq_model_type_version"),
        Index("idx_model_metadata_type", "model_type"),
        Index("idx_model_metadata_active", "is_active"),
    )


class StorageRecommendationModel(Base):
    """Storage tier recommendations"""
    __tablename__ = "storage_recommendations"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    asset_id = Column(String(255), nullable=False)
    current_tier = Column(Enum(StorageTier), nullable=False)
    recommended_tier = Column(Enum(StorageTier), nullable=False)
    confidence_score = Column(Float, default=0.0)
    estimated_cost_savings_monthly = Column(Float, default=0.0)
    estimated_access_time_change_ms = Column(Float, default=0.0)
    reasoning = Column(Text, nullable=True)
    transition_date = Column(Date, nullable=True)
    implemented = Column(Boolean, default=False)
    implemented_at = Column(DateTime(timezone=True), nullable=True)
    metadata = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index("idx_storage_recommendations_asset", "asset_id"),
        Index("idx_storage_recommendations_implemented", "implemented"),
        Index("idx_storage_recommendations_created", "created_at"),
    )


class ContentRecommendationModel(Base):
    """Content recommendations"""
    __tablename__ = "content_recommendations"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(255), nullable=True)
    source_asset_id = Column(String(255), nullable=True)
    recommended_asset_id = Column(String(255), nullable=False)
    score = Column(Float, default=0.0)
    recommendation_type = Column(Enum(RecommendationType), nullable=False)
    reason = Column(Text, nullable=True)
    clicked = Column(Boolean, default=False)
    clicked_at = Column(DateTime(timezone=True), nullable=True)
    metadata = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Indexes
    __table_args__ = (
        Index("idx_content_recommendations_user", "user_id"),
        Index("idx_content_recommendations_source", "source_asset_id"),
        Index("idx_content_recommendations_type", "recommendation_type"),
        Index("idx_content_recommendations_expires", "expires_at"),
    )


class MaintenancePredictionModel(Base):
    """Predictive maintenance predictions"""
    __tablename__ = "maintenance_predictions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    component_id = Column(String(255), nullable=False)
    component_type = Column(String(100), nullable=False)
    failure_probability = Column(Float, default=0.0)
    predicted_failure_date = Column(Date, nullable=True)
    confidence_score = Column(Float, default=0.0)
    risk_level = Column(String(50), nullable=False)
    recommended_actions = Column(JSON, default=list)
    contributing_factors = Column(JSON, default=list)
    alert_sent = Column(Boolean, default=False)
    alert_sent_at = Column(DateTime(timezone=True), nullable=True)
    resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index("idx_maintenance_predictions_component", "component_id"),
        Index("idx_maintenance_predictions_risk", "risk_level"),
        Index("idx_maintenance_predictions_resolved", "resolved"),
    )


class ContentClusterModel(Base):
    """Content clustering results"""
    __tablename__ = "content_clusters"
    
    cluster_id = Column(String(255), primary_key=True, default=lambda: str(uuid.uuid4()))
    cluster_name = Column(String(255), nullable=True)
    cluster_description = Column(Text, nullable=True)
    clustering_method = Column(Enum(ClusteringMethod), nullable=False)
    centroid_asset_id = Column(String(255), nullable=True)
    cluster_size = Column(Integer, default=0)
    cluster_cohesion = Column(Float, default=0.0)
    top_tags = Column(JSON, default=list)
    metadata = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    members = relationship("ClusterMemberModel", back_populates="cluster")
    
    # Indexes
    __table_args__ = (
        Index("idx_content_clusters_method", "clustering_method"),
        Index("idx_content_clusters_created", "created_at"),
    )


class ClusterMemberModel(Base):
    """Members of content clusters"""
    __tablename__ = "cluster_members"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    cluster_id = Column(String(255), ForeignKey("content_clusters.cluster_id"), nullable=False)
    asset_id = Column(String(255), nullable=False)
    distance_to_centroid = Column(Float, default=0.0)
    joined_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Relationships
    cluster = relationship("ContentClusterModel", back_populates="members")
    
    # Indexes
    __table_args__ = (
        UniqueConstraint("cluster_id", "asset_id", name="uq_cluster_member"),
        Index("idx_cluster_members_asset", "asset_id"),
    )


class AutoTagModel(Base):
    """Auto-generated tags"""
    __tablename__ = "auto_tags"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    asset_id = Column(String(255), nullable=False)
    tag = Column(String(255), nullable=False)
    confidence = Column(Float, default=0.0)
    category = Column(String(50), nullable=False)
    source = Column(String(50), nullable=False)
    model_version = Column(String(50), nullable=True)
    approved = Column(Boolean, default=False)
    approved_by = Column(String(255), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        UniqueConstraint("asset_id", "tag", "source", name="uq_asset_tag_source"),
        Index("idx_auto_tags_asset", "asset_id"),
        Index("idx_auto_tags_confidence", "confidence"),
        Index("idx_auto_tags_approved", "approved"),
    )


class TrainingJobModel(Base):
    """Model training jobs"""
    __tablename__ = "training_jobs"
    
    job_id = Column(String(255), primary_key=True, default=lambda: str(uuid.uuid4()))
    model_type = Column(Enum(ModelType), nullable=False)
    status = Column(String(50), default="pending")
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    training_data_size = Column(Integer, default=0)
    validation_data_size = Column(Integer, default=0)
    epochs_completed = Column(Integer, default=0)
    current_loss = Column(Float, nullable=True)
    best_validation_score = Column(Float, nullable=True)
    error_message = Column(Text, nullable=True)
    created_by = Column(String(255), nullable=True)
    metadata = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index("idx_training_jobs_status", "status"),
        Index("idx_training_jobs_model_type", "model_type"),
        Index("idx_training_jobs_created", "created_at"),
    )


class AISearchQueryModel(Base):
    """AI-powered search queries"""
    __tablename__ = "ai_search_queries"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    query = Column(Text, nullable=False)
    search_type = Column(String(50), nullable=False)
    user_id = Column(String(255), nullable=True)
    results_count = Column(Integer, default=0)
    avg_relevance_score = Column(Float, default=0.0)
    execution_time_ms = Column(Float, default=0.0)
    clicked_results = Column(JSON, default=list)
    metadata = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index("idx_ai_search_queries_user", "user_id"),
        Index("idx_ai_search_queries_type", "search_type"),
        Index("idx_ai_search_queries_created", "created_at"),
    )


# Video Summarization Models
class VideoSummaryModel(Base):
    """Video summaries"""
    __tablename__ = "video_summaries"
    
    summary_id = Column(String(255), primary_key=True, default=lambda: str(uuid.uuid4()))
    asset_id = Column(String(255), nullable=False, index=True)
    original_duration = Column(Float, nullable=False)
    summary_duration = Column(Float, nullable=False)
    target_duration_percent = Column(Integer, nullable=False)
    actual_duration_percent = Column(Float, nullable=False)
    summary_type = Column(String(50), nullable=False)
    confidence_score = Column(Float, nullable=False, default=0.0)
    processing_time = Column(Float, nullable=False, default=0.0)
    model_used = Column(Enum(ModelType), nullable=False)
    summary_video_path = Column(String(1024), nullable=True)
    keyframes_count = Column(Integer, default=0)
    transcript_highlights_count = Column(Integer, default=0)
    metadata = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), onupdate=datetime.utcnow)
    
    # Relationships
    segments = relationship("SummarySegmentModel", back_populates="summary", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index("idx_video_summaries_asset", "asset_id"),
        Index("idx_video_summaries_type", "summary_type"),
        Index("idx_video_summaries_created", "created_at"),
        Index("idx_video_summaries_confidence", "confidence_score"),
    )


class SummarySegmentModel(Base):
    """Video summary segments"""
    __tablename__ = "summary_segments"
    
    segment_id = Column(String(255), primary_key=True, default=lambda: str(uuid.uuid4()))
    summary_id = Column(String(255), ForeignKey("video_summaries.summary_id"), nullable=False)
    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)
    duration = Column(Float, nullable=False)
    importance_score = Column(Float, nullable=False, default=0.0)
    scene_type = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    keyframe_path = Column(String(1024), nullable=True)
    transcript_text = Column(Text, nullable=True)
    segment_order = Column(Integer, nullable=False, default=0)
    metadata = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Relationships
    summary = relationship("VideoSummaryModel", back_populates="segments")
    
    # Indexes
    __table_args__ = (
        Index("idx_summary_segments_summary", "summary_id"),
        Index("idx_summary_segments_time", "start_time", "end_time"),
        Index("idx_summary_segments_importance", "importance_score"),
        Index("idx_summary_segments_order", "summary_id", "segment_order"),
    )


class VideoKeyFrameModel(Base):
    """Video keyframes"""
    __tablename__ = "video_keyframes"
    
    keyframe_id = Column(String(255), primary_key=True, default=lambda: str(uuid.uuid4()))
    summary_id = Column(String(255), ForeignKey("video_summaries.summary_id"), nullable=False)
    segment_id = Column(String(255), ForeignKey("summary_segments.segment_id"), nullable=True)
    timestamp = Column(Float, nullable=False)
    frame_number = Column(Integer, nullable=False)
    thumbnail_path = Column(String(1024), nullable=False)
    importance_score = Column(Float, nullable=False, default=0.0)
    image_features = Column(JSON, default=dict)  # For similarity search
    metadata = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index("idx_video_keyframes_summary", "summary_id"),
        Index("idx_video_keyframes_segment", "segment_id"),
        Index("idx_video_keyframes_timestamp", "timestamp"),
        Index("idx_video_keyframes_importance", "importance_score"),
    )


class TranscriptHighlightModel(Base):
    """Transcript highlights"""
    __tablename__ = "transcript_highlights"
    
    highlight_id = Column(String(255), primary_key=True, default=lambda: str(uuid.uuid4()))
    summary_id = Column(String(255), ForeignKey("video_summaries.summary_id"), nullable=False)
    segment_id = Column(String(255), ForeignKey("summary_segments.segment_id"), nullable=True)
    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)
    text = Column(Text, nullable=False)
    confidence = Column(Float, nullable=False, default=0.0)
    importance_score = Column(Float, nullable=False, default=0.5)
    speaker_id = Column(String(255), nullable=True)
    language = Column(String(10), nullable=True)
    text_features = Column(JSON, default=dict)  # For semantic search
    metadata = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index("idx_transcript_highlights_summary", "summary_id"),
        Index("idx_transcript_highlights_segment", "segment_id"),
        Index("idx_transcript_highlights_time", "start_time", "end_time"),
        Index("idx_transcript_highlights_importance", "importance_score"),
        Index("idx_transcript_highlights_speaker", "speaker_id"),
    )


# System Component Models for Maintenance
class SystemMetricsModel(Base):
    """System metrics for predictive maintenance"""
    __tablename__ = "system_metrics"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    component_id = Column(String(255), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    cpu_usage = Column(Float, nullable=True)
    memory_usage = Column(Float, nullable=True)
    disk_usage = Column(Float, nullable=True)
    network_io = Column(Float, nullable=True)
    error_rate = Column(Float, nullable=True)
    response_time = Column(Float, nullable=True)
    temperature = Column(Float, nullable=True)
    uptime = Column(Float, nullable=True)
    custom_metrics = Column(JSON, default=dict)
    
    # Indexes
    __table_args__ = (
        Index("idx_system_metrics_component_time", "component_id", "timestamp"),
        Index("idx_system_metrics_timestamp", "timestamp"),
    )


class ComponentHealthModel(Base):
    """Component health status"""
    __tablename__ = "component_health"
    
    component_id = Column(String(255), primary_key=True)
    component_type = Column(String(100), nullable=False)
    component_name = Column(String(255), nullable=False)
    location = Column(String(255), nullable=True)
    is_critical = Column(Boolean, default=False)
    health_score = Column(Float, default=1.0)
    status = Column(String(50), default="healthy")
    last_maintenance = Column(DateTime(timezone=True), nullable=True)
    next_scheduled_maintenance = Column(DateTime(timezone=True), nullable=True)
    configuration = Column(JSON, default=dict)
    metadata = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), onupdate=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index("idx_component_health_type", "component_type"),
        Index("idx_component_health_status", "status"),
        Index("idx_component_health_critical", "is_critical"),
        Index("idx_component_health_score", "health_score"),
    )


class MaintenanceHistoryModel(Base):
    """Maintenance history"""
    __tablename__ = "maintenance_history"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    component_id = Column(String(255), ForeignKey("component_health.component_id"), nullable=False)
    maintenance_type = Column(String(100), nullable=False)
    maintenance_date = Column(Date, nullable=False)
    description = Column(Text, nullable=True)
    performed_by = Column(String(255), nullable=True)
    cost = Column(Float, nullable=True)
    downtime_minutes = Column(Integer, nullable=True)
    issues_found = Column(JSON, default=list)
    parts_replaced = Column(JSON, default=list)
    metadata = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index("idx_maintenance_history_component", "component_id"),
        Index("idx_maintenance_history_date", "maintenance_date"),
        Index("idx_maintenance_history_type", "maintenance_type"),
    )


class AutoTagModel(Base):
    """Auto-generated tags for content"""
    __tablename__ = "auto_tags"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    asset_id = Column(String(36), nullable=False, index=True)
    tag_name = Column(String(255), nullable=False, index=True)
    category = Column(String(50), nullable=False, index=True)
    confidence = Column(Float, nullable=False, index=True)
    source = Column(String(50), nullable=False, index=True)
    metadata = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    
    # Indexes
    __table_args__ = (
        Index("idx_auto_tags_asset_category", "asset_id", "category"),
        Index("idx_auto_tags_confidence", "confidence"),
        Index("idx_auto_tags_source_category", "source", "category"),
        Index("idx_auto_tags_name_confidence", "tag_name", "confidence"),
    )


class ContentModerationModel(Base):
    """Content moderation results"""
    __tablename__ = "content_moderation"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    asset_id = Column(String(36), nullable=False, unique=True, index=True)
    results = Column(JSON, nullable=False)
    overall_score = Column(Float, nullable=False, index=True)
    flagged = Column(Boolean, nullable=False, default=False, index=True)
    reviewed = Column(Boolean, nullable=False, default=False, index=True)
    reviewer_id = Column(String(36), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index("idx_content_moderation_flagged", "flagged", "reviewed"),
        Index("idx_content_moderation_score", "overall_score"),
    )


class OCRResultModel(Base):
    """OCR text extraction results"""
    __tablename__ = "ocr_results"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    asset_id = Column(String(36), nullable=False, index=True)
    extracted_text = Column(Text, nullable=False)
    confidence = Column(Float, nullable=False, index=True)
    language = Column(String(10), nullable=True, index=True)
    bounding_boxes = Column(JSON, default=list)
    page_number = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    
    # Indexes
    __table_args__ = (
        Index("idx_ocr_results_asset", "asset_id"),
        Index("idx_ocr_results_confidence", "confidence"),
        Index("idx_ocr_results_language", "language"),
    )


class AudioClassificationModel(Base):
    """Audio content classification results"""
    __tablename__ = "audio_classifications"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    asset_id = Column(String(36), nullable=False, index=True)
    content_type = Column(String(50), nullable=False, index=True)
    confidence = Column(Float, nullable=False, index=True)
    features = Column(JSON, nullable=False)
    segments = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    
    # Indexes
    __table_args__ = (
        Index("idx_audio_classifications_asset", "asset_id"),
        Index("idx_audio_classifications_type", "content_type"),
        Index("idx_audio_classifications_confidence", "confidence"),
    )


class FeatureVectorModel(Base):
    """Feature vectors for content clustering"""
    __tablename__ = "feature_vectors"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    asset_id = Column(String(36), nullable=False, index=True)
    feature_type = Column(String(50), nullable=False, index=True)
    vector_data = Column(LargeBinary, nullable=False)  # Serialized numpy array
    vector_size = Column(Integer, nullable=False)
    metadata = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    
    # Indexes
    __table_args__ = (
        Index("idx_feature_vectors_asset_type", "asset_id", "feature_type"),
        Index("idx_feature_vectors_type", "feature_type"),
        UniqueConstraint("asset_id", "feature_type", name="uq_asset_feature_type")
    )


class ClusterMembershipModel(Base):
    """Asset cluster membership"""
    __tablename__ = "cluster_memberships"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    asset_id = Column(String(36), nullable=False, index=True)
    cluster_id = Column(String(36), nullable=False, index=True)
    distance_to_center = Column(Float, nullable=True)
    membership_confidence = Column(Float, nullable=True)
    assigned_at = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    
    # Indexes
    __table_args__ = (
        Index("idx_cluster_memberships_asset", "asset_id"),
        Index("idx_cluster_memberships_cluster", "cluster_id"),
        Index("idx_cluster_memberships_confidence", "membership_confidence"),
        UniqueConstraint("asset_id", "cluster_id", name="uq_asset_cluster")
    )


class AssetSimilarityModel(Base):
    """Asset similarity relationships"""
    __tablename__ = "asset_similarities"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    asset_id_1 = Column(String(36), nullable=False, index=True)
    asset_id_2 = Column(String(36), nullable=False, index=True)
    similarity_score = Column(Float, nullable=False, index=True)
    matching_features = Column(JSON, default=list)
    calculated_at = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    
    # Indexes
    __table_args__ = (
        Index("idx_asset_similarities_score", "similarity_score"),
        Index("idx_asset_similarities_asset1", "asset_id_1"),
        Index("idx_asset_similarities_asset2", "asset_id_2"),
        Index("idx_asset_similarities_pair", "asset_id_1", "asset_id_2"),
        CheckConstraint("asset_id_1 != asset_id_2", name="check_different_assets")
    )


class CostMetricsModel(Base):
    """Cost metrics for resources"""
    __tablename__ = "cost_metrics"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    resource_id = Column(String(36), nullable=False, index=True)
    resource_type = Column(String(50), nullable=False, index=True)
    period_start = Column(Date, nullable=False, index=True)
    period_end = Column(Date, nullable=False, index=True)
    storage_cost = Column(Float, nullable=False, default=0.0)
    compute_cost = Column(Float, nullable=False, default=0.0)
    transfer_cost = Column(Float, nullable=False, default=0.0)
    total_cost = Column(Float, nullable=False, index=True)
    usage_efficiency = Column(Float, nullable=False, default=0.0)
    metadata = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    
    # Indexes
    __table_args__ = (
        Index("idx_cost_metrics_resource_period", "resource_id", "period_start", "period_end"),
        Index("idx_cost_metrics_type_cost", "resource_type", "total_cost"),
        Index("idx_cost_metrics_efficiency", "usage_efficiency"),
        UniqueConstraint("resource_id", "period_start", "period_end", name="uq_resource_period")
    )


class CostOptimizationModel(Base):
    """Cost optimization suggestions"""
    __tablename__ = "cost_optimizations"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    resource_id = Column(String(36), nullable=False, index=True)
    resource_type = Column(String(50), nullable=False, index=True)
    optimization_type = Column(String(50), nullable=False, index=True)
    current_cost_monthly = Column(Float, nullable=False)
    projected_cost_monthly = Column(Float, nullable=False)
    savings_monthly = Column(Float, nullable=False, index=True)
    savings_percentage = Column(Float, nullable=False, index=True)
    description = Column(Text, nullable=False)
    implementation_effort = Column(String(20), nullable=False)  # low, medium, high
    risk_level = Column(String(20), nullable=False)  # low, medium, high
    steps = Column(JSON, nullable=False)
    status = Column(String(20), nullable=False, default='pending', index=True)  # pending, approved, implemented, rejected
    approved_by = Column(String(36), nullable=True)
    implemented_at = Column(DateTime(timezone=True), nullable=True)
    actual_savings = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index("idx_cost_optimizations_resource", "resource_id"),
        Index("idx_cost_optimizations_type", "optimization_type"),
        Index("idx_cost_optimizations_savings", "savings_monthly"),
        Index("idx_cost_optimizations_status", "status"),
        Index("idx_cost_optimizations_risk_effort", "risk_level", "implementation_effort"),
    )


class CostForecastModel(Base):
    """Cost forecasts"""
    __tablename__ = "cost_forecasts"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    resource_id = Column(String(36), nullable=True, index=True)  # Null for global forecasts
    resource_type = Column(String(50), nullable=True, index=True)
    forecast_date = Column(Date, nullable=False, index=True)
    forecasted_cost = Column(Float, nullable=False, index=True)
    confidence_interval_lower = Column(Float, nullable=True)
    confidence_interval_upper = Column(Float, nullable=True)
    model_used = Column(String(50), nullable=False)
    factors = Column(JSON, default=dict)  # Factors influencing the forecast
    actual_cost = Column(Float, nullable=True)  # Filled in later for validation
    forecast_accuracy = Column(Float, nullable=True)  # Calculated when actual cost is known
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    
    # Indexes
    __table_args__ = (
        Index("idx_cost_forecasts_resource_date", "resource_id", "forecast_date"),
        Index("idx_cost_forecasts_date", "forecast_date"),
        Index("idx_cost_forecasts_accuracy", "forecast_accuracy"),
        UniqueConstraint("resource_id", "forecast_date", name="uq_resource_forecast_date")
    )


class StorageUsageModel(Base):
    """Storage usage tracking for cost analysis"""
    __tablename__ = "storage_usage"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    asset_id = Column(String(36), nullable=False, index=True)
    storage_tier = Column(String(20), nullable=False, index=True)
    size_bytes = Column(Integer, nullable=False)
    access_count = Column(Integer, nullable=False, default=0)
    last_accessed = Column(DateTime(timezone=True), nullable=True, index=True)
    cost_per_gb_month = Column(Float, nullable=False)
    monthly_cost = Column(Float, nullable=False, index=True)
    period_start = Column(Date, nullable=False, index=True)
    period_end = Column(Date, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    
    # Indexes
    __table_args__ = (
        Index("idx_storage_usage_asset_period", "asset_id", "period_start", "period_end"),
        Index("idx_storage_usage_tier_cost", "storage_tier", "monthly_cost"),
        Index("idx_storage_usage_access", "last_accessed"),
        UniqueConstraint("asset_id", "period_start", "period_end", name="uq_asset_usage_period")
    )


class CostAnomalyModel(Base):
    """Cost anomaly detection results"""
    __tablename__ = "cost_anomalies"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    resource_id = Column(String(36), nullable=False, index=True)
    resource_type = Column(String(50), nullable=False, index=True)
    anomaly_date = Column(Date, nullable=False, index=True)
    expected_cost = Column(Float, nullable=False)
    actual_cost = Column(Float, nullable=False, index=True)
    cost_difference = Column(Float, nullable=False, index=True)
    anomaly_score = Column(Float, nullable=False, index=True)  # How anomalous (0-1)
    severity = Column(String(20), nullable=False, index=True)  # low, medium, high, critical
    description = Column(Text, nullable=False)
    possible_causes = Column(JSON, default=list)
    investigation_status = Column(String(20), nullable=False, default='pending', index=True)
    resolution = Column(Text, nullable=True)
    resolved_by = Column(String(36), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    
    # Indexes
    __table_args__ = (
        Index("idx_cost_anomalies_resource_date", "resource_id", "anomaly_date"),
        Index("idx_cost_anomalies_severity", "severity"),
        Index("idx_cost_anomalies_score", "anomaly_score"),
        Index("idx_cost_anomalies_status", "investigation_status"),
    )