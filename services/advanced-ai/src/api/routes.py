"""
API routes for Advanced AI Service
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, delete
from datetime import datetime, timedelta, date
import asyncio

from ..core.deps import (
    get_db, get_redis, get_usage_predictor, get_storage_optimizer,
    get_recommendation_engine, get_maintenance_predictor, get_video_summarizer,
    get_current_user, verify_api_key
)
from ..models.schemas import (
    UsagePrediction, UsagePredictionRequest, UsageTrend,
    StorageRecommendation, StorageOptimizationPlan,
    ContentRecommendation, RecommendationRequest, RecommendationResponse,
    MaintenancePrediction, MaintenanceAlert,
    CostOptimizationSuggestion, CostForecast,
    VideoSummary, VideoSummaryRequest, SummarySegment, SummaryType, 
    AutoTag, AutoTagRequest, AutoTagResponse, TagCategory, TagSource,
    ContentModerationResult, OCRResult, AudioClassificationResult, TagStatistics,
    ContentCluster, ContentSimilarity, ClusteringRequest, ClusteringResult,
    ClusterStatistics, SimilarityRequest, ClusterRecommendationRequest,
    FeatureImportance, ClusterAnalysis, ClusteringMethod,
    AISearchQuery, AISearchResult,
    MLModel, TrainingJob, PredictionAnalytics
)
from ..db.models import (
    UsageHistoryModel, PredictionModel, StorageRecommendationModel,
    ContentRecommendationModel, MaintenancePredictionModel,
    ContentClusterModel, AutoTagModel, ContentModerationModel,
    OCRResultModel, AudioClassificationModel, TrainingJobModel,
    VideoSummaryModel, SummarySegmentModel, FeatureVectorModel,
    ClusterMembershipModel, AssetSimilarityModel, CostMetricsModel,
    CostOptimizationModel, CostForecastModel, StorageUsageModel,
    CostAnomalyModel
)
from ..services.usage_predictor import UsagePredictor
from ..utils.metrics import ai_metrics


router = APIRouter(prefix="/api/v1/ai", tags=["advanced-ai"])


# Usage Prediction Endpoints
@router.post("/predictions/usage", response_model=List[UsagePrediction])
async def predict_usage(
    request: UsagePredictionRequest,
    background_tasks: BackgroundTasks,
    usage_predictor: UsagePredictor = Depends(get_usage_predictor),
    current_user = Depends(get_current_user)
):
    """Predict future usage patterns for assets"""
    start_time = datetime.utcnow()
    
    try:
        # Get asset IDs to predict
        if request.asset_ids:
            asset_ids = request.asset_ids
        else:
            # Get top accessed assets if not specified
            db = usage_predictor.db
            result = await db.execute(
                select(UsageHistoryModel.asset_id, func.sum(UsageHistoryModel.access_count))
                .group_by(UsageHistoryModel.asset_id)
                .order_by(func.sum(UsageHistoryModel.access_count).desc())
                .limit(100)
            )
            asset_ids = [row[0] for row in result.all()]
        
        # Make predictions
        predictions = await usage_predictor.predict_usage(
            asset_ids=asset_ids,
            horizon_days=request.horizon_days,
            models_to_use=request.models_to_use
        )
        
        # Record metrics
        elapsed = (datetime.utcnow() - start_time).total_seconds()
        ai_metrics.prediction_latency.labels(
            type="usage",
            model="ensemble"
        ).observe(elapsed)
        
        return predictions
        
    except Exception as e:
        logger.error("Error in usage prediction", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Prediction failed: {str(e)}"
        )


@router.get("/predictions/usage/trends/{asset_id}", response_model=UsageTrend)
async def get_usage_trends(
    asset_id: str,
    usage_predictor: UsagePredictor = Depends(get_usage_predictor),
    current_user = Depends(get_current_user)
):
    """Analyze usage trends for a specific asset"""
    trend = await usage_predictor.analyze_trends(asset_id)
    return trend


@router.get("/predictions/usage/history")
async def get_prediction_history(
    asset_id: Optional[str] = Query(None),
    days: int = Query(30, le=90),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get historical predictions and their accuracy"""
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    query = select(PredictionModel).where(
        and_(
            PredictionModel.prediction_type == "usage",
            PredictionModel.created_at >= cutoff_date
        )
    )
    
    if asset_id:
        query = query.where(PredictionModel.asset_id == asset_id)
    
    result = await db.execute(query.order_by(PredictionModel.created_at.desc()))
    predictions = result.scalars().all()
    
    # Calculate accuracy for past predictions
    history = []
    for pred in predictions:
        if pred.prediction_date <= date.today():
            # Get actual value
            actual_result = await db.execute(
                select(func.sum(UsageHistoryModel.access_count))
                .where(
                    and_(
                        UsageHistoryModel.asset_id == pred.asset_id,
                        func.date(UsageHistoryModel.timestamp) == pred.prediction_date
                    )
                )
            )
            actual_value = actual_result.scalar() or 0
            
            accuracy = 1 - abs(pred.predicted_value - actual_value) / (actual_value + 1)
            
            history.append({
                "prediction_id": pred.prediction_id,
                "asset_id": pred.asset_id,
                "prediction_date": pred.prediction_date,
                "predicted_value": pred.predicted_value,
                "actual_value": actual_value,
                "accuracy": max(0, accuracy),
                "model_used": pred.model_used
            })
    
    return history


# Storage Optimization Endpoints
@router.post("/optimization/storage", response_model=StorageOptimizationPlan)
async def optimize_storage(
    min_savings_percent: float = Query(10, ge=0, le=100),
    storage_optimizer = Depends(get_storage_optimizer),
    current_user = Depends(get_current_user)
):
    """Generate storage optimization recommendations"""
    # This would be implemented in storage_optimizer.py
    # For now, return a placeholder
    return StorageOptimizationPlan(
        total_assets=0,
        recommendations=[],
        total_cost_savings_monthly=0,
        total_storage_to_move_gb=0,
        implementation_priority=[]
    )


@router.get("/optimization/storage/recommendations")
async def get_storage_recommendations(
    asset_id: Optional[str] = Query(None),
    implemented: Optional[bool] = Query(None),
    limit: int = Query(100, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get storage optimization recommendations"""
    query = select(StorageRecommendationModel)
    
    if asset_id:
        query = query.where(StorageRecommendationModel.asset_id == asset_id)
    if implemented is not None:
        query = query.where(StorageRecommendationModel.implemented == implemented)
    
    result = await db.execute(
        query.order_by(StorageRecommendationModel.estimated_cost_savings_monthly.desc())
        .limit(limit)
    )
    
    recommendations = result.scalars().all()
    return [StorageRecommendation.from_orm(r) for r in recommendations]


# Content Recommendation Endpoints
@router.post("/recommendations/content", response_model=RecommendationResponse)
async def get_content_recommendations(
    request: RecommendationRequest,
    recommendation_engine = Depends(get_recommendation_engine),
    current_user = Depends(get_current_user)
):
    """Get content recommendations"""
    # This would be implemented in recommendation_engine.py
    # For now, return a placeholder
    return RecommendationResponse(
        recommendations=[],
        cache_ttl_seconds=3600,
        model_version="1.0.0"
    )


@router.post("/recommendations/feedback")
async def record_recommendation_feedback(
    recommendation_id: int,
    clicked: bool,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Record user feedback on recommendations"""
    recommendation = await db.get(ContentRecommendationModel, recommendation_id)
    if not recommendation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recommendation not found"
        )
    
    recommendation.clicked = clicked
    if clicked:
        recommendation.clicked_at = datetime.utcnow()
    
    await db.commit()
    
    # Update metrics
    if clicked:
        ai_metrics.recommendation_click_rate.labels(
            type=recommendation.recommendation_type
        ).inc()
    
    return {"message": "Feedback recorded"}


# Predictive Maintenance Endpoints
@router.get("/maintenance/predictions", response_model=List[MaintenancePrediction])
async def get_maintenance_predictions(
    component_type: Optional[str] = Query(None),
    risk_level: Optional[str] = Query(None),
    days_ahead: int = Query(30, le=365),
    maintenance_predictor = Depends(get_maintenance_predictor),
    current_user = Depends(get_current_user)
):
    """Get predictive maintenance forecasts"""
    # This would be implemented in maintenance_predictor.py
    # For now, return empty list
    return []


@router.get("/maintenance/alerts", response_model=List[MaintenanceAlert])
async def get_maintenance_alerts(
    severity: Optional[str] = Query(None),
    acknowledged: Optional[bool] = Query(None),
    limit: int = Query(100, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get maintenance alerts"""
    # Query would go here
    return []


# Cost Optimization Endpoints
@router.get("/optimization/cost/suggestions", response_model=List[CostOptimizationSuggestion])
async def get_cost_suggestions(
    min_savings: float = Query(100, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get cost optimization suggestions"""
    # Implementation would analyze costs and suggest optimizations
    return []


@router.get("/optimization/cost/forecast", response_model=List[CostForecast])
async def get_cost_forecast(
    days_ahead: int = Query(30, ge=1, le=365),
    current_user = Depends(get_current_user)
):
    """Get cost forecast"""
    # Implementation would predict future costs
    return []


# Content Intelligence Endpoints
@router.post("/content/summarize", response_model=VideoSummary)
async def summarize_video(
    request: VideoSummaryRequest,
    background_tasks: BackgroundTasks,
    video_summarizer = Depends(get_video_summarizer),
    current_user = Depends(get_current_user)
):
    """Generate video summary"""
    try:
        # Get video file path (this would interface with asset service)
        video_path = await _get_asset_file_path(request.asset_id)
        
        if not video_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Asset not found or no video file available"
            )
        
        # Generate summary
        summary = await video_summarizer.summarize_video(
            asset_id=request.asset_id,
            video_path=video_path,
            target_duration_percent=request.target_duration_percent,
            summary_type=request.summary_type,
            options=request.options or {}
        )
        
        # Generate video file if requested
        if request.generate_video_file:
            background_tasks.add_task(
                _generate_summary_video,
                video_path,
                summary.segments,
                summary.summary_id
            )
        
        return summary
        
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video file not found"
        )
    except Exception as e:
        logger.error("Error generating video summary", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Summarization failed: {str(e)}"
        )


@router.get("/content/summaries/{asset_id}", response_model=List[VideoSummary])
async def get_video_summaries(
    asset_id: str,
    summary_type: Optional[SummaryType] = Query(None),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get existing video summaries for an asset"""
    query = select(VideoSummaryModel).where(
        VideoSummaryModel.asset_id == asset_id
    )
    
    if summary_type:
        query = query.where(VideoSummaryModel.summary_type == summary_type.value)
    
    result = await db.execute(
        query.order_by(VideoSummaryModel.created_at.desc()).limit(limit)
    )
    
    summaries = result.scalars().all()
    
    # Convert to response models
    response_summaries = []
    for summary in summaries:
        # Get segments
        segments_result = await db.execute(
            select(SummarySegmentModel)
            .where(SummarySegmentModel.summary_id == summary.summary_id)
            .order_by(SummarySegmentModel.segment_order)
        )
        segments = segments_result.scalars().all()
        
        # Convert to schema
        summary_schema = VideoSummary(
            summary_id=summary.summary_id,
            asset_id=summary.asset_id,
            original_duration=summary.original_duration,
            summary_duration=summary.summary_duration,
            target_duration_percent=summary.target_duration_percent,
            actual_duration_percent=summary.actual_duration_percent,
            summary_type=SummaryType(summary.summary_type),
            segments=[SummarySegment(
                segment_id=s.segment_id,
                start_time=s.start_time,
                end_time=s.end_time,
                duration=s.duration,
                importance_score=s.importance_score,
                scene_type=s.scene_type,
                description=s.description or "",
                keyframe_path=s.keyframe_path,
                transcript_text=s.transcript_text
            ) for s in segments],
            keyframes=[],  # Would load if needed
            transcript_highlights=[],  # Would load if needed
            confidence_score=summary.confidence_score,
            processing_time=summary.processing_time,
            model_used=summary.model_used,
            summary_video_path=summary.summary_video_path,
            created_at=summary.created_at
        )
        response_summaries.append(summary_schema)
    
    return response_summaries


@router.get("/content/summaries/{summary_id}/download")
async def download_summary_video(
    summary_id: str,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Download generated summary video"""
    summary = await db.get(VideoSummaryModel, summary_id)
    
    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Summary not found"
        )
    
    if not summary.summary_video_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Summary video not available"
        )
    
    from fastapi.responses import FileResponse
    return FileResponse(
        summary.summary_video_path,
        media_type="video/mp4",
        filename=f"summary_{summary_id}.mp4"
    )


@router.delete("/content/summaries/{summary_id}")
async def delete_video_summary(
    summary_id: str,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Delete a video summary"""
    summary = await db.get(VideoSummaryModel, summary_id)
    
    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Summary not found"
        )
    
    # Delete associated files
    if summary.summary_video_path:
        try:
            import os
            os.remove(summary.summary_video_path)
        except OSError:
            pass
    
    # Delete from database (cascades to segments)
    await db.delete(summary)
    await db.commit()
    
    return {"message": "Summary deleted successfully"}


@router.get("/content/tags/{asset_id}", response_model=List[AutoTag])
async def get_auto_tags(
    asset_id: str,
    min_confidence: float = Query(0.7, ge=0, le=1),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get auto-generated tags for an asset"""
    result = await db.execute(
        select(AutoTagModel)
        .where(
            and_(
                AutoTagModel.asset_id == asset_id,
                AutoTagModel.confidence >= min_confidence
            )
        )
        .order_by(AutoTagModel.confidence.desc())
    )
    
    tags = result.scalars().all()
    return [AutoTag.from_orm(tag) for tag in tags]


@router.get("/content/clusters", response_model=List[ContentCluster])
async def get_content_clusters(
    min_size: int = Query(5, ge=2),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get content clusters"""
    result = await db.execute(
        select(ContentClusterModel)
        .where(ContentClusterModel.cluster_size >= min_size)
        .order_by(ContentClusterModel.cluster_size.desc())
    )
    
    clusters = result.scalars().all()
    return [ContentCluster.from_orm(cluster) for cluster in clusters]


# AI Search Endpoints
@router.post("/search", response_model=List[AISearchResult])
async def ai_search(
    query: AISearchQuery,
    current_user = Depends(get_current_user)
):
    """AI-powered search"""
    # This would implement semantic/visual search
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="AI search not yet implemented"
    )


# Model Management Endpoints
@router.get("/models", response_model=List[MLModel])
async def list_models(
    model_type: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """List ML models"""
    from ..db.models import ModelMetadataModel
    
    query = select(ModelMetadataModel)
    
    if model_type:
        query = query.where(ModelMetadataModel.model_type == model_type)
    if is_active is not None:
        query = query.where(ModelMetadataModel.is_active == is_active)
    
    result = await db.execute(query.order_by(ModelMetadataModel.created_at.desc()))
    models = result.scalars().all()
    
    return [MLModel.from_orm(model) for model in models]


# Auto-Tagging Endpoints

@router.post("/content/auto-tag", response_model=AutoTagResponse)
async def auto_tag_content(
    request: AutoTagRequest,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    current_user = Depends(get_current_user)
):
    """Auto-tag content with AI analysis"""
    from ..services.auto_tagger import AutoTagger
    
    # Initialize auto-tagger
    auto_tagger = AutoTagger(db=db, redis=redis)
    await auto_tagger.initialize()
    
    # Check if analysis already exists (unless force_reanalysis)
    if not request.force_reanalysis:
        cache_key = f"auto_tags:{request.asset_id}"
        cached_result = await redis.get(cache_key)
        if cached_result:
            return AutoTagResponse.parse_raw(cached_result)
    
    # Analyze and tag content
    tags = await auto_tagger.analyze_and_tag_asset(
        asset_id=request.asset_id,
        file_path=request.file_path,
        asset_type=request.asset_type,
        options=request.options
    )
    
    # Filter by confidence and categories if specified
    filtered_tags = []
    for tag in tags:
        if tag.confidence >= request.min_confidence:
            if request.categories is None or tag.category in request.categories:
                filtered_tags.append(tag)
    
    # Create response
    response = AutoTagResponse(
        asset_id=request.asset_id,
        tags=filtered_tags,
        processing_time_seconds=0.0,  # Will be calculated by auto_tagger
        analysis_summary={
            "total_tags": len(filtered_tags),
            "categories": list(set(tag.category for tag in filtered_tags)),
            "sources": list(set(tag.source for tag in filtered_tags)),
            "avg_confidence": sum(tag.confidence for tag in filtered_tags) / len(filtered_tags) if filtered_tags else 0
        }
    )
    
    # Cache result for 1 hour
    cache_key = f"auto_tags:{request.asset_id}"
    await redis.setex(cache_key, 3600, response.json())
    
    return response


@router.get("/content/{asset_id}/tags", response_model=List[AutoTag])
async def get_asset_tags(
    asset_id: str,
    category: Optional[TagCategory] = Query(None),
    source: Optional[TagSource] = Query(None),
    min_confidence: float = Query(0.0, ge=0, le=1),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get existing tags for an asset"""
    from ..db.models import AutoTagModel
    
    query = select(AutoTagModel).where(AutoTagModel.asset_id == asset_id)
    
    if category:
        query = query.where(AutoTagModel.category == category)
    if source:
        query = query.where(AutoTagModel.source == source)
    if min_confidence > 0:
        query = query.where(AutoTagModel.confidence >= min_confidence)
    
    result = await db.execute(query.order_by(AutoTagModel.confidence.desc()))
    tags = result.scalars().all()
    
    return [AutoTag.from_orm(tag) for tag in tags]


@router.delete("/content/{asset_id}/tags")
async def delete_asset_tags(
    asset_id: str,
    category: Optional[TagCategory] = Query(None),
    source: Optional[TagSource] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Delete tags for an asset"""
    from ..db.models import AutoTagModel
    
    query = delete(AutoTagModel).where(AutoTagModel.asset_id == asset_id)
    
    if category:
        query = query.where(AutoTagModel.category == category)
    if source:
        query = query.where(AutoTagModel.source == source)
    
    result = await db.execute(query)
    await db.commit()
    
    return {"deleted_count": result.rowcount}


@router.get("/content/moderation/{asset_id}", response_model=ContentModerationResult)
async def get_moderation_result(
    asset_id: str,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get content moderation results"""
    from ..db.models import ContentModerationModel
    
    result = await db.execute(
        select(ContentModerationModel).where(ContentModerationModel.asset_id == asset_id)
    )
    moderation = result.scalar_one_or_none()
    
    if not moderation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Moderation result not found"
        )
    
    return ContentModerationResult.from_orm(moderation)


@router.post("/content/moderation/{moderation_id}/review")
async def review_moderation_result(
    moderation_id: str,
    review_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Review and approve/reject moderation result"""
    from ..db.models import ContentModerationModel
    
    result = await db.execute(
        select(ContentModerationModel).where(ContentModerationModel.id == moderation_id)
    )
    moderation = result.scalar_one_or_none()
    
    if not moderation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Moderation result not found"
        )
    
    moderation.reviewed = True
    moderation.reviewer_id = current_user.id
    moderation.reviewed_at = datetime.utcnow()
    moderation.notes = review_data.get('notes')
    
    await db.commit()
    
    return {"message": "Moderation reviewed successfully"}


@router.get("/content/ocr/{asset_id}", response_model=List[OCRResult])
async def get_ocr_results(
    asset_id: str,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get OCR results for an asset"""
    from ..db.models import OCRResultModel
    
    result = await db.execute(
        select(OCRResultModel)
        .where(OCRResultModel.asset_id == asset_id)
        .order_by(OCRResultModel.page_number.asc())
    )
    ocr_results = result.scalars().all()
    
    return [OCRResult.from_orm(ocr) for ocr in ocr_results]


@router.get("/tags/statistics", response_model=TagStatistics)
async def get_tag_statistics(
    asset_type: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get auto-tagging statistics"""
    from ..db.models import AutoTagModel
    from sqlalchemy import func
    
    # Base query
    query = select(AutoTagModel)
    
    if date_from:
        query = query.where(AutoTagModel.created_at >= date_from)
    if date_to:
        query = query.where(AutoTagModel.created_at <= date_to)
    
    # Get all tags
    result = await db.execute(query)
    all_tags = result.scalars().all()
    
    if not all_tags:
        return TagStatistics(
            total_tags=0,
            tags_by_category={},
            tags_by_source={},
            average_confidence=0.0,
            confidence_distribution={},
            top_tags=[],
            processing_time_avg=0.0
        )
    
    # Calculate statistics
    tags_by_category = {}
    tags_by_source = {}
    confidence_sum = 0
    confidence_distribution = {"high": 0, "medium": 0, "low": 0}
    tag_name_counts = {}
    
    for tag in all_tags:
        # Category stats
        if tag.category not in tags_by_category:
            tags_by_category[tag.category] = 0
        tags_by_category[tag.category] += 1
        
        # Source stats
        if tag.source not in tags_by_source:
            tags_by_source[tag.source] = 0
        tags_by_source[tag.source] += 1
        
        # Confidence stats
        confidence_sum += tag.confidence
        if tag.confidence >= 0.8:
            confidence_distribution["high"] += 1
        elif tag.confidence >= 0.5:
            confidence_distribution["medium"] += 1
        else:
            confidence_distribution["low"] += 1
        
        # Tag name counts
        if tag.tag_name not in tag_name_counts:
            tag_name_counts[tag.tag_name] = 0
        tag_name_counts[tag.tag_name] += 1
    
    # Top tags
    top_tags = [
        {"tag_name": name, "count": count}
        for name, count in sorted(tag_name_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    ]
    
    return TagStatistics(
        total_tags=len(all_tags),
        tags_by_category=tags_by_category,
        tags_by_source=tags_by_source,
        average_confidence=confidence_sum / len(all_tags),
        confidence_distribution=confidence_distribution,
        top_tags=top_tags,
        processing_time_avg=2.5  # Placeholder - would be calculated from metrics
    )


# Content Clustering Endpoints

@router.post("/clustering/cluster", response_model=ClusteringResult)
async def cluster_content(
    request: ClusteringRequest,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    current_user = Depends(get_current_user)
):
    """Cluster content based on extracted features"""
    from ..services.content_clusterer import ContentClusterer
    
    # Initialize clusterer
    clusterer = ContentClusterer(db=db, redis=redis)
    await clusterer.initialize()
    
    # Perform clustering
    result = await clusterer.cluster_content(
        asset_ids=request.asset_ids,
        clustering_method=request.clustering_method,
        feature_types=request.feature_types,
        options=request.options
    )
    
    return result


@router.post("/clustering/similarity", response_model=List[ContentSimilarity])
async def find_similar_content(
    request: SimilarityRequest,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    current_user = Depends(get_current_user)
):
    """Find content similar to a given asset"""
    from ..services.content_clusterer import ContentClusterer
    
    # Initialize clusterer
    clusterer = ContentClusterer(db=db, redis=redis)
    await clusterer.initialize()
    
    # Find similar content
    similarities = await clusterer.find_similar_content(
        asset_id=request.asset_id,
        similarity_threshold=request.similarity_threshold,
        max_results=request.max_results,
        feature_types=request.feature_types
    )
    
    return similarities


@router.get("/clustering/clusters", response_model=List[ContentCluster])
async def get_content_clusters(
    min_size: int = Query(1, ge=1),
    max_results: int = Query(50, ge=1, le=200),
    created_after: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get existing content clusters"""
    query = select(ContentClusterModel).where(ContentClusterModel.cluster_size >= min_size)
    
    if created_after:
        query = query.where(ContentClusterModel.created_at >= created_after)
    
    query = query.order_by(ContentClusterModel.cluster_size.desc()).limit(max_results)
    
    result = await db.execute(query)
    clusters = result.scalars().all()
    
    return [ContentCluster.from_orm(cluster) for cluster in clusters]


@router.get("/clustering/clusters/{cluster_id}", response_model=ContentCluster)
async def get_cluster_details(
    cluster_id: str,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get detailed information about a specific cluster"""
    result = await db.execute(
        select(ContentClusterModel).where(ContentClusterModel.cluster_id == cluster_id)
    )
    cluster = result.scalar_one_or_none()
    
    if not cluster:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cluster not found"
        )
    
    return ContentCluster.from_orm(cluster)


@router.get("/clustering/clusters/{cluster_id}/members", response_model=List[str])
async def get_cluster_members(
    cluster_id: str,
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get asset IDs that belong to a specific cluster"""
    result = await db.execute(
        select(ClusterMembershipModel.asset_id)
        .where(ClusterMembershipModel.cluster_id == cluster_id)
        .order_by(ClusterMembershipModel.membership_confidence.desc())
        .limit(limit)
    )
    asset_ids = result.scalars().all()
    
    return list(asset_ids)


@router.post("/clustering/recommendations", response_model=List[str])
async def get_cluster_recommendations(
    request: ClusterRecommendationRequest,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    current_user = Depends(get_current_user)
):
    """Get content recommendations based on cluster analysis"""
    from ..services.content_clusterer import ContentClusterer
    
    # Initialize clusterer
    clusterer = ContentClusterer(db=db, redis=redis)
    await clusterer.initialize()
    
    # Get recommendations
    recommendations = await clusterer.get_cluster_recommendations(
        user_id=request.user_id,
        max_recommendations=request.max_recommendations
    )
    
    return recommendations


@router.get("/clustering/asset/{asset_id}/cluster", response_model=Optional[ContentCluster])
async def get_asset_cluster(
    asset_id: str,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get the cluster that an asset belongs to"""
    # Get cluster membership
    membership_result = await db.execute(
        select(ClusterMembershipModel.cluster_id)
        .where(ClusterMembershipModel.asset_id == asset_id)
        .order_by(ClusterMembershipModel.membership_confidence.desc())
        .limit(1)
    )
    cluster_id = membership_result.scalar_one_or_none()
    
    if not cluster_id:
        return None
    
    # Get cluster details
    cluster_result = await db.execute(
        select(ContentClusterModel).where(ContentClusterModel.cluster_id == cluster_id)
    )
    cluster = cluster_result.scalar_one_or_none()
    
    if cluster:
        return ContentCluster.from_orm(cluster)
    else:
        return None


@router.post("/clustering/incremental")
async def update_clusters_incremental(
    asset_ids: List[str],
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    current_user = Depends(get_current_user)
):
    """Update clusters incrementally with new assets"""
    from ..services.content_clusterer import ContentClusterer
    
    # Schedule incremental update
    background_tasks.add_task(
        incremental_clustering_task, 
        asset_ids, 
        db, 
        redis
    )
    
    return {"message": f"Incremental clustering scheduled for {len(asset_ids)} assets"}


@router.delete("/clustering/clusters/{cluster_id}")
async def delete_cluster(
    cluster_id: str,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Delete a cluster and its memberships"""
    # Delete cluster memberships
    await db.execute(
        delete(ClusterMembershipModel).where(ClusterMembershipModel.cluster_id == cluster_id)
    )
    
    # Delete cluster
    result = await db.execute(
        delete(ContentClusterModel).where(ContentClusterModel.cluster_id == cluster_id)
    )
    
    await db.commit()
    
    if result.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cluster not found"
        )
    
    return {"message": "Cluster deleted successfully"}


@router.get("/clustering/statistics", response_model=ClusterStatistics)
async def get_clustering_statistics(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get overall clustering statistics"""
    # Get total clusters
    clusters_result = await db.execute(select(func.count(ContentClusterModel.cluster_id)))
    total_clusters = clusters_result.scalar()
    
    # Get total assets in clusters
    assets_result = await db.execute(select(func.count(ClusterMembershipModel.asset_id)))
    total_assets = assets_result.scalar()
    
    # Get cluster sizes
    sizes_result = await db.execute(select(ContentClusterModel.cluster_size))
    sizes = sizes_result.scalars().all()
    
    if sizes:
        largest_cluster_size = max(sizes)
        smallest_cluster_size = min(sizes)
        average_cluster_size = sum(sizes) / len(sizes)
    else:
        largest_cluster_size = 0
        smallest_cluster_size = 0
        average_cluster_size = 0.0
    
    return ClusterStatistics(
        total_assets=total_assets or 0,
        total_clusters=total_clusters or 0,
        largest_cluster_size=largest_cluster_size,
        smallest_cluster_size=smallest_cluster_size,
        average_cluster_size=average_cluster_size,
        silhouette_score=0.0,  # Would be calculated from stored metrics
        outliers_count=0,  # Would be calculated
        cluster_distribution={}  # Would be calculated
    )


# Cost Optimization Endpoints

@router.post("/cost/analyze", response_model=List[Dict[str, Any]])
async def analyze_resource_costs(
    resource_ids: Optional[List[str]] = None,
    resource_types: Optional[List[str]] = None,
    analysis_period_days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    current_user = Depends(get_current_user)
):
    """Analyze costs for specified resources"""
    from ..services.cost_optimizer import CostOptimizer
    
    # Initialize cost optimizer
    optimizer = CostOptimizer(db=db, redis=redis)
    await optimizer.initialize()
    
    # Analyze costs
    analyses = await optimizer.analyze_resource_costs(
        resource_ids=resource_ids,
        resource_types=resource_types,
        analysis_period_days=analysis_period_days
    )
    
    # Convert to serializable format
    result = []
    for analysis in analyses:
        result.append({
            "resource_id": analysis.resource_id,
            "resource_type": analysis.resource_type,
            "current_monthly_cost": analysis.current_monthly_cost,
            "usage_patterns": analysis.usage_patterns,
            "efficiency_score": analysis.efficiency_score,
            "optimization_potential": analysis.optimization_potential,
            "recommendations": analysis.recommendations
        })
    
    return result


@router.post("/cost/optimize", response_model=List[CostOptimizationSuggestion])
async def generate_optimization_suggestions(
    resource_ids: Optional[List[str]] = None,
    min_savings_percentage: float = Query(10.0, ge=0, le=100),
    max_risk_level: str = Query("medium", regex="^(low|medium|high)$"),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    current_user = Depends(get_current_user)
):
    """Generate cost optimization suggestions"""
    from ..services.cost_optimizer import CostOptimizer
    
    # Initialize cost optimizer
    optimizer = CostOptimizer(db=db, redis=redis)
    await optimizer.initialize()
    
    # Generate suggestions
    suggestions = await optimizer.generate_optimization_suggestions(
        resource_ids=resource_ids,
        min_savings_percentage=min_savings_percentage,
        max_risk_level=max_risk_level
    )
    
    return suggestions


@router.post("/cost/forecast", response_model=List[CostForecast])
async def forecast_costs(
    resource_ids: Optional[List[str]] = None,
    forecast_days: int = Query(90, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    current_user = Depends(get_current_user)
):
    """Forecast future costs"""
    from ..services.cost_optimizer import CostOptimizer
    
    # Initialize cost optimizer
    optimizer = CostOptimizer(db=db, redis=redis)
    await optimizer.initialize()
    
    # Generate forecasts
    forecasts = await optimizer.forecast_costs(
        resource_ids=resource_ids,
        forecast_days=forecast_days
    )
    
    return forecasts


@router.get("/cost/anomalies", response_model=List[Dict[str, Any]])
async def detect_cost_anomalies(
    lookback_days: int = Query(7, ge=1, le=30),
    anomaly_threshold: float = Query(2.0, ge=1.0, le=5.0),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    current_user = Depends(get_current_user)
):
    """Detect cost anomalies"""
    from ..services.cost_optimizer import CostOptimizer
    
    # Initialize cost optimizer
    optimizer = CostOptimizer(db=db, redis=redis)
    await optimizer.initialize()
    
    # Detect anomalies
    anomalies = await optimizer.detect_cost_anomalies(
        lookback_days=lookback_days,
        anomaly_threshold=anomaly_threshold
    )
    
    return anomalies


@router.post("/cost/storage-optimize", response_model=List[CostOptimizationSuggestion])
async def optimize_storage_tiers(
    asset_ids: Optional[List[str]] = None,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    current_user = Depends(get_current_user)
):
    """Optimize storage tier assignments"""
    from ..services.cost_optimizer import CostOptimizer
    
    # Initialize cost optimizer
    optimizer = CostOptimizer(db=db, redis=redis)
    await optimizer.initialize()
    
    # Optimize storage tiers
    suggestions = await optimizer.optimize_storage_tiers(asset_ids=asset_ids)
    
    return suggestions


@router.get("/cost/suggestions", response_model=List[CostOptimizationSuggestion])
async def get_cost_optimization_suggestions(
    status: str = Query("pending", regex="^(pending|approved|implemented|rejected)$"),
    optimization_type: Optional[str] = Query(None),
    min_savings: float = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get existing cost optimization suggestions"""
    from ..db.models import CostOptimizationModel
    
    query = select(CostOptimizationModel).where(CostOptimizationModel.status == status)
    
    if optimization_type:
        query = query.where(CostOptimizationModel.optimization_type == optimization_type)
    
    if min_savings > 0:
        query = query.where(CostOptimizationModel.savings_monthly >= min_savings)
    
    query = query.order_by(CostOptimizationModel.savings_monthly.desc()).limit(limit)
    
    result = await db.execute(query)
    suggestions = result.scalars().all()
    
    return [CostOptimizationSuggestion.from_orm(suggestion) for suggestion in suggestions]


@router.put("/cost/suggestions/{suggestion_id}/approve")
async def approve_cost_optimization(
    suggestion_id: str,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Approve a cost optimization suggestion"""
    from ..db.models import CostOptimizationModel
    
    result = await db.execute(
        select(CostOptimizationModel).where(CostOptimizationModel.id == suggestion_id)
    )
    suggestion = result.scalar_one_or_none()
    
    if not suggestion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cost optimization suggestion not found"
        )
    
    suggestion.status = "approved"
    suggestion.approved_by = current_user.id
    suggestion.updated_at = datetime.utcnow()
    
    await db.commit()
    
    return {"message": "Cost optimization suggestion approved"}


@router.put("/cost/suggestions/{suggestion_id}/implement")
async def implement_cost_optimization(
    suggestion_id: str,
    actual_savings: Optional[float] = None,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Mark a cost optimization suggestion as implemented"""
    from ..db.models import CostOptimizationModel
    
    result = await db.execute(
        select(CostOptimizationModel).where(CostOptimizationModel.id == suggestion_id)
    )
    suggestion = result.scalar_one_or_none()
    
    if not suggestion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cost optimization suggestion not found"
        )
    
    suggestion.status = "implemented"
    suggestion.implemented_at = datetime.utcnow()
    suggestion.updated_at = datetime.utcnow()
    
    if actual_savings is not None:
        suggestion.actual_savings = actual_savings
    
    await db.commit()
    
    return {"message": "Cost optimization suggestion marked as implemented"}


@router.get("/cost/metrics", response_model=List[CostMetrics])
async def get_cost_metrics(
    resource_ids: Optional[List[str]] = Query(None),
    resource_types: Optional[List[str]] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get cost metrics for resources"""
    from ..db.models import CostMetricsModel
    
    query = select(CostMetricsModel)
    
    if resource_ids:
        query = query.where(CostMetricsModel.resource_id.in_(resource_ids))
    
    if resource_types:
        query = query.where(CostMetricsModel.resource_type.in_(resource_types))
    
    if start_date:
        query = query.where(CostMetricsModel.period_start >= start_date)
    
    if end_date:
        query = query.where(CostMetricsModel.period_end <= end_date)
    
    query = query.order_by(CostMetricsModel.period_start.desc())
    
    result = await db.execute(query)
    metrics = result.scalars().all()
    
    return [CostMetrics.from_orm(metric) for metric in metrics]


@router.get("/cost/statistics")
async def get_cost_statistics(
    period_days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get cost optimization statistics"""
    from ..db.models import CostOptimizationModel, CostMetricsModel
    
    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=period_days)
    
    # Get total potential savings
    savings_result = await db.execute(
        select(func.sum(CostOptimizationModel.savings_monthly))
        .where(CostOptimizationModel.status == 'pending')
    )
    total_potential_savings = savings_result.scalar() or 0.0
    
    # Get implemented savings
    implemented_result = await db.execute(
        select(func.sum(CostOptimizationModel.actual_savings))
        .where(CostOptimizationModel.status == 'implemented')
        .where(CostOptimizationModel.implemented_at >= start_date)
    )
    implemented_savings = implemented_result.scalar() or 0.0
    
    # Get total costs
    cost_result = await db.execute(
        select(func.sum(CostMetricsModel.total_cost))
        .where(CostMetricsModel.period_start >= start_date)
    )
    total_costs = cost_result.scalar() or 0.0
    
    # Get suggestion counts by type
    type_result = await db.execute(
        select(
            CostOptimizationModel.optimization_type,
            func.count(CostOptimizationModel.id)
        )
        .where(CostOptimizationModel.status == 'pending')
        .group_by(CostOptimizationModel.optimization_type)
    )
    suggestions_by_type = dict(type_result.fetchall())
    
    return {
        "period_days": period_days,
        "total_potential_savings": total_potential_savings,
        "implemented_savings": implemented_savings,
        "total_costs": total_costs,
        "savings_rate": (implemented_savings / total_costs * 100) if total_costs > 0 else 0,
        "suggestions_by_type": suggestions_by_type,
        "optimization_efficiency": (implemented_savings / total_potential_savings * 100) if total_potential_savings > 0 else 0
    }


@router.post("/models/train")
async def train_model(
    model_type: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Trigger model training"""
    # Create training job
    job = TrainingJobModel(
        model_type=model_type,
        status="pending",
        created_by=current_user.id
    )
    db.add(job)
    await db.commit()
    
    # Trigger training in background
    background_tasks.add_task(train_model_task, job.job_id, model_type)
    
    return {"job_id": job.job_id, "status": "training started"}


@router.get("/models/jobs/{job_id}", response_model=TrainingJob)
async def get_training_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get training job status"""
    job = await db.get(TrainingJobModel, job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Training job not found"
        )
    
    return TrainingJob.from_orm(job)


# Analytics Endpoints
@router.get("/analytics/predictions", response_model=PredictionAnalytics)
async def get_prediction_analytics(
    prediction_type: str,
    days: int = Query(30, le=365),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get prediction analytics"""
    # Calculate analytics from predictions
    start_date = date.today() - timedelta(days=days)
    end_date = date.today()
    
    # Get prediction counts and accuracy
    result = await db.execute(
        select(
            func.count(PredictionModel.prediction_id),
            func.avg(PredictionModel.confidence_score)
        )
        .where(
            and_(
                PredictionModel.prediction_type == prediction_type,
                PredictionModel.created_at >= datetime.combine(start_date, datetime.min.time())
            )
        )
    )
    
    count, avg_confidence = result.first()
    
    return PredictionAnalytics(
        prediction_type=prediction_type,
        period_start=start_date,
        period_end=end_date,
        total_predictions=count or 0,
        average_accuracy=avg_confidence or 0,
        model_performance={},
        top_predicted_assets=[],
        error_analysis={}
    )


# Health Check
@router.get("/health")
async def health_check(
    db: AsyncSession = Depends(get_db),
    redis = Depends(get_redis)
):
    """Health check endpoint"""
    try:
        # Check database
        await db.execute("SELECT 1")
        
        # Check Redis
        await redis.ping()
        
        return {
            "status": "healthy",
            "service": "advanced-ai",
            "timestamp": datetime.utcnow(),
            "components": {
                "database": "healthy",
                "redis": "healthy",
                "models": "loaded"
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "advanced-ai",
            "error": str(e),
            "timestamp": datetime.utcnow()
        }


# Background task placeholder
async def train_model_task(job_id: str, model_type: str):
    """Background task to train model"""
    # This would contain actual training logic
    pass


# Helper functions for video summarization
async def _get_asset_file_path(asset_id: str) -> Optional[str]:
    """Get video file path for asset (interface with asset service)"""
    # This would interface with the asset management service
    # For now, return a mock path
    return f"/storage/videos/{asset_id}.mp4"


async def _generate_summary_video(
    video_path: str,
    segments: List[SummarySegment],
    summary_id: str
):
    """Background task to generate summary video file"""
    try:
        from ..services.video_summarizer import VideoSummarizer
        from ..core.deps import get_db, get_redis
        
        # This would use proper dependency injection in production
        # For now, create a temporary instance
        async with get_db() as db:
            redis = await get_redis()
            summarizer = VideoSummarizer(db, redis)
            
            output_path = f"/storage/summaries/summary_{summary_id}.mp4"
            await summarizer.generate_summary_video(
                video_path, segments, output_path
            )
            
            # Update database with video path
            from ..db.models import VideoSummaryModel
            summary = await db.get(VideoSummaryModel, summary_id)
            if summary:
                summary.summary_video_path = output_path
                await db.commit()
        
    except Exception as e:
        logger.error("Error generating summary video", error=str(e))