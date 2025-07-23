"""
Predictive Analytics API

This module provides REST API endpoints for machine learning-powered
predictive analytics including churn prediction, content popularity,
and usage forecasting.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from shared.auth.dependencies import get_current_user
from shared.db.postgres import get_session
from shared.tracing.python_tracing import trace_async_function

from ...services.predictive_analytics import PredictiveAnalytics, PredictionType, ModelType

router = APIRouter()

# Initialize predictive analytics service
predictive_service = PredictiveAnalytics()


class ChurnPredictionRequest(BaseModel):
    """Request model for churn prediction."""
    user_ids: List[str] = Field(..., min_items=1, max_items=100, description="User IDs to analyze")
    include_recommendations: bool = Field(True, description="Include prevention recommendations")


class ContentPopularityRequest(BaseModel):
    """Request model for content popularity prediction."""
    content_features: List[Dict[str, Any]] = Field(..., description="Content features for prediction")
    prediction_horizon_days: int = Field(7, ge=1, le=30, description="Prediction horizon in days")


class UsageForecastRequest(BaseModel):
    """Request model for usage forecasting."""
    metric_name: str = Field(..., description="Metric to forecast")
    forecast_days: int = Field(7, ge=1, le=90, description="Number of days to forecast")
    include_confidence_intervals: bool = Field(True, description="Include confidence intervals")


class AnomalyDetectionRequest(BaseModel):
    """Request model for anomaly detection."""
    metric_name: str = Field(..., description="Metric to analyze")
    data_points: List[Dict[str, Any]] = Field(..., description="Data points to analyze")
    sensitivity: float = Field(2.0, ge=1.0, le=5.0, description="Detection sensitivity")


class ModelTrainingRequest(BaseModel):
    """Request model for model training."""
    model_type: PredictionType = Field(..., description="Type of model to train")
    training_params: Dict[str, Any] = Field(default_factory=dict, description="Training parameters")


class ChurnPredictionResponse(BaseModel):
    """Response model for churn predictions."""
    predictions: List[Dict[str, Any]]
    model_version: str
    generated_at: str
    total_users_analyzed: int
    high_risk_users_count: int


class ContentPopularityResponse(BaseModel):
    """Response model for content popularity predictions."""
    predictions: List[Dict[str, Any]]
    prediction_horizon_days: int
    model_confidence: float
    generated_at: str


class UsageForecastResponse(BaseModel):
    """Response model for usage forecasting."""
    metric_name: str
    forecast_period_days: int
    forecasts: List[Dict[str, Any]]
    trend: Dict[str, Any]
    model_metrics: Dict[str, float]
    generated_at: str


class AnomalyDetectionResponse(BaseModel):
    """Response model for anomaly detection."""
    metric_name: str
    anomalies: List[Dict[str, Any]]
    total_data_points: int
    anomalies_detected: int
    sensitivity_used: float
    analysis_timestamp: str


@router.post("/churn/predict", response_model=ChurnPredictionResponse)
async def predict_user_churn(
    request: ChurnPredictionRequest,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    """Predict user churn probability."""
    
    if not current_user.has_permission("analytics.predict"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    try:
        # Get churn predictions
        predictions = await predictive_service.predict_user_churn(
            request.user_ids, db
        )
        
        # Count high-risk users
        high_risk_count = sum(
            1 for pred in predictions 
            if pred.get('risk_level') in ['high', 'very_high']
        )
        
        return ChurnPredictionResponse(
            predictions=predictions,
            model_version="1.0.0",
            generated_at=datetime.utcnow().isoformat(),
            total_users_analyzed=len(predictions),
            high_risk_users_count=high_risk_count
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to predict churn: {str(e)}")


@router.post("/churn/batch-predict")
async def batch_predict_user_churn(
    request: ChurnPredictionRequest,
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    """Predict user churn for large batches (async processing)."""
    
    if not current_user.has_permission("analytics.predict"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    if len(request.user_ids) > 1000:
        raise HTTPException(status_code=400, detail="Maximum 1000 users per batch")
    
    try:
        # Generate batch ID
        batch_id = f"churn_batch_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        # Add to background tasks
        background_tasks.add_task(
            _process_churn_batch,
            batch_id,
            request.user_ids,
            str(current_user.id),
            db
        )
        
        return {
            "batch_id": batch_id,
            "status": "queued",
            "message": f"Churn prediction queued for {len(request.user_ids)} users",
            "estimated_completion_minutes": max(1, len(request.user_ids) // 100),
            "queued_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to queue churn prediction: {str(e)}")


async def _process_churn_batch(
    batch_id: str,
    user_ids: List[str],
    requesting_user_id: str,
    db: AsyncSession
):
    """Background task for batch churn prediction."""
    try:
        predictions = await predictive_service.predict_user_churn(user_ids, db)
        
        # Store results in cache
        redis_client = await predictive_service._get_redis()
        result_data = {
            "batch_id": batch_id,
            "predictions": predictions,
            "total_users": len(predictions),
            "high_risk_count": sum(1 for p in predictions if p.get('risk_level') in ['high', 'very_high']),
            "processed_at": datetime.utcnow().isoformat(),
            "requested_by": requesting_user_id
        }
        
        await redis_client.setex(
            f"churn_batch_result:{batch_id}",
            3600,  # 1 hour expiration
            json.dumps(result_data, default=str)
        )
        
    except Exception as e:
        # Store error in cache
        redis_client = await predictive_service._get_redis()
        await redis_client.setex(
            f"churn_batch_result:{batch_id}",
            3600,
            json.dumps({"error": str(e), "batch_id": batch_id})
        )


@router.get("/churn/batch-result/{batch_id}")
async def get_churn_batch_result(
    batch_id: str,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    """Get result of batch churn prediction."""
    
    if not current_user.has_permission("analytics.predict"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    try:
        redis_client = await predictive_service._get_redis()
        result_data = await redis_client.get(f"churn_batch_result:{batch_id}")
        
        if not result_data:
            return {
                "status": "not_found",
                "message": "Batch result not found or expired"
            }
        
        result = json.loads(result_data)
        
        if "error" in result:
            return {
                "status": "error",
                "batch_id": batch_id,
                "error": result["error"]
            }
        
        return {
            "status": "completed",
            "batch_id": batch_id,
            "predictions": result["predictions"],
            "total_users": result["total_users"],
            "high_risk_count": result["high_risk_count"],
            "processed_at": result["processed_at"]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get batch result: {str(e)}")


@router.post("/content/popularity", response_model=ContentPopularityResponse)
async def predict_content_popularity(
    request: ContentPopularityRequest,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    """Predict content popularity."""
    
    if not current_user.has_permission("analytics.predict"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    try:
        predictions = await predictive_service.predict_content_popularity(
            request.content_features,
            request.prediction_horizon_days
        )
        
        return ContentPopularityResponse(
            predictions=predictions,
            prediction_horizon_days=request.prediction_horizon_days,
            model_confidence=0.75,  # Placeholder confidence
            generated_at=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to predict content popularity: {str(e)}")


@router.post("/usage/forecast", response_model=UsageForecastResponse)
async def forecast_usage(
    request: UsageForecastRequest,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    """Forecast usage metrics."""
    
    if not current_user.has_permission("analytics.predict"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    try:
        forecast_result = await predictive_service.forecast_usage(
            request.metric_name,
            request.forecast_days,
            db
        )
        
        return UsageForecastResponse(**forecast_result)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to forecast usage: {str(e)}")


@router.post("/anomalies/detect", response_model=AnomalyDetectionResponse)
async def detect_anomalies(
    request: AnomalyDetectionRequest,
    current_user = Depends(get_current_user)
):
    """Detect anomalies in metric data."""
    
    if not current_user.has_permission("analytics.view"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    try:
        anomalies = await predictive_service.detect_anomalies(
            request.metric_name,
            request.data_points,
            request.sensitivity
        )
        
        return AnomalyDetectionResponse(
            metric_name=request.metric_name,
            anomalies=anomalies,
            total_data_points=len(request.data_points),
            anomalies_detected=len(anomalies),
            sensitivity_used=request.sensitivity,
            analysis_timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to detect anomalies: {str(e)}")


@router.post("/models/train/{model_type}")
async def train_model(
    model_type: PredictionType,
    request: ModelTrainingRequest,
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    """Train a predictive model."""
    
    if not current_user.has_permission("analytics.admin"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    try:
        # Generate training job ID
        job_id = f"training_{model_type}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        # Add training to background tasks
        background_tasks.add_task(
            _train_model_background,
            job_id,
            model_type,
            request.training_params,
            str(current_user.id),
            db
        )
        
        return {
            "job_id": job_id,
            "model_type": model_type,
            "status": "queued",
            "message": f"Model training queued for {model_type}",
            "estimated_completion_minutes": 30,
            "queued_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to queue model training: {str(e)}")


async def _train_model_background(
    job_id: str,
    model_type: PredictionType,
    training_params: Dict[str, Any],
    requesting_user_id: str,
    db: AsyncSession
):
    """Background task for model training."""
    try:
        if model_type == PredictionType.USER_CHURN:
            performance = await predictive_service.train_churn_prediction_model(db)
            
            # Save performance metrics
            await predictive_service.save_model_performance('churn_prediction', performance)
            
            result_data = {
                "job_id": job_id,
                "model_type": model_type,
                "status": "completed",
                "performance": {
                    "accuracy": performance.accuracy,
                    "precision": performance.precision,
                    "recall": performance.recall,
                    "f1_score": performance.f1_score
                },
                "completed_at": datetime.utcnow().isoformat(),
                "requested_by": requesting_user_id
            }
        else:
            result_data = {
                "job_id": job_id,
                "model_type": model_type,
                "status": "error",
                "error": f"Model type {model_type} not implemented yet"
            }
        
        # Store results
        redis_client = await predictive_service._get_redis()
        await redis_client.setex(
            f"training_result:{job_id}",
            86400,  # 24 hours
            json.dumps(result_data, default=str)
        )
        
    except Exception as e:
        # Store error
        redis_client = await predictive_service._get_redis()
        await redis_client.setex(
            f"training_result:{job_id}",
            86400,
            json.dumps({"job_id": job_id, "status": "error", "error": str(e)})
        )


@router.get("/models/training-result/{job_id}")
async def get_training_result(
    job_id: str,
    current_user = Depends(get_current_user)
):
    """Get model training result."""
    
    if not current_user.has_permission("analytics.admin"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    try:
        redis_client = await predictive_service._get_redis()
        result_data = await redis_client.get(f"training_result:{job_id}")
        
        if not result_data:
            return {
                "status": "not_found",
                "message": "Training result not found or expired"
            }
        
        return json.loads(result_data)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get training result: {str(e)}")


@router.get("/models/performance")
async def get_models_performance(
    current_user = Depends(get_current_user)
):
    """Get performance metrics for all models."""
    
    if not current_user.has_permission("analytics.view"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    try:
        models = ['churn_prediction']  # Add more models as they're implemented
        performance_data = {}
        
        for model_name in models:
            performance = await predictive_service.get_model_performance(model_name)
            if performance:
                performance_data[model_name] = performance
        
        return {
            "models": performance_data,
            "retrieved_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get model performance: {str(e)}")


@router.get("/insights/churn-summary")
async def get_churn_insights_summary(
    period_days: int = Query(30, ge=7, le=90, description="Analysis period in days"),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    """Get summary insights about user churn patterns."""
    
    if not current_user.has_permission("analytics.view"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    try:
        # This would analyze churn patterns over the specified period
        # For now, return sample insights
        
        insights = {
            "period_days": period_days,
            "analysis_date": datetime.utcnow().isoformat(),
            "churn_statistics": {
                "total_users_analyzed": 1250,
                "churned_users": 89,
                "churn_rate_percent": 7.1,
                "predicted_churn_next_week": 15,
                "at_risk_users": 45
            },
            "risk_distribution": {
                "very_high": 8,
                "high": 15,
                "medium": 22,
                "low": 35,
                "very_low": 1170
            },
            "top_churn_factors": [
                {
                    "factor": "low_session_frequency",
                    "impact_score": 0.85,
                    "description": "Users with less than 2 sessions per week"
                },
                {
                    "factor": "no_content_uploads",
                    "impact_score": 0.72,
                    "description": "Users who haven't uploaded any content"
                },
                {
                    "factor": "short_session_duration",
                    "impact_score": 0.68,
                    "description": "Average session duration less than 5 minutes"
                }
            ],
            "recommendations": [
                "Implement proactive engagement campaigns for at-risk users",
                "Improve onboarding flow to increase content uploads",
                "Add tutorial content to increase session engagement",
                "Create personalized feature recommendations"
            ]
        }
        
        return insights
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get churn insights: {str(e)}")


@router.get("/insights/trends")
async def get_predictive_trends(
    metrics: List[str] = Query([], description="Metrics to analyze"),
    forecast_days: int = Query(14, ge=7, le=30, description="Forecast horizon"),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    """Get predictive trends analysis."""
    
    if not current_user.has_permission("analytics.view"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    try:
        if not metrics:
            metrics = ["user_sessions", "page_views", "asset_uploads"]
        
        trends_analysis = {}
        
        for metric in metrics:
            try:
                forecast_result = await predictive_service.forecast_usage(
                    metric, forecast_days, db
                )
                trends_analysis[metric] = forecast_result
            except Exception as e:
                trends_analysis[metric] = {
                    "error": f"Failed to forecast {metric}: {str(e)}"
                }
        
        return {
            "metrics_analyzed": metrics,
            "forecast_horizon_days": forecast_days,
            "trends": trends_analysis,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get predictive trends: {str(e)}")


@router.get("/health")
async def health_check():
    """Health check for predictive analytics service."""
    return {
        "status": "healthy",
        "service": "predictive_analytics",
        "timestamp": datetime.utcnow().isoformat(),
        "available_predictions": [pt.value for pt in PredictionType],
        "supported_models": [mt.value for mt in ModelType]
    }