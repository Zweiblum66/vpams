"""
Tests for Predictive Analytics API

This module contains comprehensive tests for the predictive analytics API endpoints.
"""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient
from fastapi import FastAPI

from src.api.v1.predictive import router
from src.services.predictive_analytics import PredictionType, ModelType, ModelPerformance


@pytest.fixture
def app():
    """Create FastAPI app for testing."""
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/predictive")
    return app


@pytest.fixture
async def client(app):
    """Create test client."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_current_user():
    """Mock current user."""
    user = MagicMock()
    user.id = "test-user-123"
    user.has_permission = MagicMock(return_value=True)
    return user


@pytest.fixture
def sample_churn_predictions():
    """Sample churn prediction data."""
    return [
        {
            "user_id": "user-1",
            "churn_probability": 0.85,
            "churn_prediction": True,
            "risk_level": "high",
            "days_to_churn_estimate": 7,
            "recommended_actions": [
                "Send personalized re-engagement email",
                "Offer premium features trial"
            ]
        },
        {
            "user_id": "user-2",
            "churn_probability": 0.15,
            "churn_prediction": False,
            "risk_level": "very_low",
            "days_to_churn_estimate": 60,
            "recommended_actions": []
        }
    ]


@pytest.fixture
def sample_content_popularity():
    """Sample content popularity predictions."""
    return [
        {
            "content_id": "content-1",
            "popularity_score": 0.75,
            "predicted_views": 1500,
            "predicted_interactions": 150,
            "confidence": 0.8,
            "factors": {
                "content_type_boost": True,
                "optimal_size": True,
                "metadata_complete": True,
                "recently_uploaded": True
            }
        }
    ]


@pytest.fixture
def sample_usage_forecast():
    """Sample usage forecast data."""
    return {
        "metric_name": "page_views",
        "forecast_period_days": 7,
        "forecasts": [
            {
                "date": "2025-07-20T00:00:00Z",
                "predicted_value": 1250.0,
                "lower_bound": 1100.0,
                "upper_bound": 1400.0,
                "confidence": 0.8
            },
            {
                "date": "2025-07-21T00:00:00Z",
                "predicted_value": 1275.0,
                "lower_bound": 1125.0,
                "upper_bound": 1425.0,
                "confidence": 0.8
            }
        ],
        "trend": {
            "direction": "increasing",
            "slope": 25.0,
            "r2_score": 0.85
        },
        "model_metrics": {
            "mae": 45.2,
            "rmse": 65.8,
            "mape": 3.5
        },
        "generated_at": "2025-07-19T10:00:00Z"
    }


class TestPredictiveAPI:
    """Test cases for predictive analytics API endpoints."""
    
    @pytest.mark.asyncio
    async def test_predict_user_churn_success(self, client, app, mock_current_user, sample_churn_predictions):
        """Test successful user churn prediction."""
        request_data = {
            "user_ids": ["user-1", "user-2"],
            "include_recommendations": True
        }
        
        with patch("src.api.v1.predictive.get_current_user", return_value=mock_current_user), \
             patch("src.api.v1.predictive.get_session"), \
             patch("src.api.v1.predictive.predictive_service.predict_user_churn") as mock_predict:
            
            mock_predict.return_value = sample_churn_predictions
            
            response = await client.post("/api/v1/predictive/churn/predict", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            assert len(data["predictions"]) == 2
            assert data["model_version"] == "1.0.0"
            assert data["total_users_analyzed"] == 2
            assert data["high_risk_users_count"] == 1
            assert "generated_at" in data
    
    @pytest.mark.asyncio
    async def test_predict_user_churn_no_permission(self, client, app, mock_current_user):
        """Test churn prediction without permission."""
        mock_current_user.has_permission.return_value = False
        request_data = {"user_ids": ["user-1"]}
        
        with patch("src.api.v1.predictive.get_current_user", return_value=mock_current_user), \
             patch("src.api.v1.predictive.get_session"):
            
            response = await client.post("/api/v1/predictive/churn/predict", json=request_data)
            
            assert response.status_code == 403
            data = response.json()
            assert data["detail"] == "Insufficient permissions"
    
    @pytest.mark.asyncio
    async def test_predict_user_churn_validation_error(self, client, app, mock_current_user):
        """Test churn prediction with validation error."""
        # Too many user IDs
        request_data = {"user_ids": ["user-" + str(i) for i in range(101)]}
        
        with patch("src.api.v1.predictive.get_current_user", return_value=mock_current_user), \
             patch("src.api.v1.predictive.get_session"):
            
            response = await client.post("/api/v1/predictive/churn/predict", json=request_data)
            
            assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_batch_predict_user_churn_success(self, client, app, mock_current_user):
        """Test successful batch churn prediction."""
        request_data = {
            "user_ids": ["user-" + str(i) for i in range(50)],
            "include_recommendations": True
        }
        
        with patch("src.api.v1.predictive.get_current_user", return_value=mock_current_user), \
             patch("src.api.v1.predictive.get_session"), \
             patch("src.api.v1.predictive._process_churn_batch") as mock_process:
            
            response = await client.post("/api/v1/predictive/churn/batch-predict", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            assert "batch_id" in data
            assert data["status"] == "queued"
            assert "Churn prediction queued for 50 users" in data["message"]
            assert "estimated_completion_minutes" in data
            assert "queued_at" in data
    
    @pytest.mark.asyncio
    async def test_batch_predict_user_churn_too_many_users(self, client, app, mock_current_user):
        """Test batch churn prediction with too many users."""
        request_data = {
            "user_ids": ["user-" + str(i) for i in range(1001)]  # Exceeds limit
        }
        
        with patch("src.api.v1.predictive.get_current_user", return_value=mock_current_user), \
             patch("src.api.v1.predictive.get_session"):
            
            response = await client.post("/api/v1/predictive/churn/batch-predict", json=request_data)
            
            assert response.status_code == 400
            data = response.json()
            assert "Maximum 1000 users per batch" in data["detail"]
    
    @pytest.mark.asyncio
    async def test_get_churn_batch_result_success(self, client, app, mock_current_user):
        """Test successful batch result retrieval."""
        batch_id = "churn_batch_20250719_100000"
        mock_result = {
            "batch_id": batch_id,
            "predictions": [{"user_id": "user-1", "churn_probability": 0.5}],
            "total_users": 1,
            "high_risk_count": 0,
            "processed_at": "2025-07-19T10:05:00Z",
            "requested_by": "test-user-123"
        }
        
        with patch("src.api.v1.predictive.get_current_user", return_value=mock_current_user), \
             patch("src.api.v1.predictive.get_session"), \
             patch("src.api.v1.predictive.predictive_service._get_redis") as mock_redis_getter:
            
            mock_redis = AsyncMock()
            mock_redis_getter.return_value = mock_redis
            mock_redis.get.return_value = json.dumps(mock_result)
            
            response = await client.get(f"/api/v1/predictive/churn/batch-result/{batch_id}")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "completed"
            assert data["batch_id"] == batch_id
            assert "predictions" in data
            assert data["total_users"] == 1
            assert data["high_risk_count"] == 0
    
    @pytest.mark.asyncio
    async def test_get_churn_batch_result_not_found(self, client, app, mock_current_user):
        """Test batch result not found."""
        batch_id = "nonexistent_batch"
        
        with patch("src.api.v1.predictive.get_current_user", return_value=mock_current_user), \
             patch("src.api.v1.predictive.get_session"), \
             patch("src.api.v1.predictive.predictive_service._get_redis") as mock_redis_getter:
            
            mock_redis = AsyncMock()
            mock_redis_getter.return_value = mock_redis
            mock_redis.get.return_value = None
            
            response = await client.get(f"/api/v1/predictive/churn/batch-result/{batch_id}")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "not_found"
            assert "Batch result not found or expired" in data["message"]
    
    @pytest.mark.asyncio
    async def test_predict_content_popularity_success(self, client, app, mock_current_user, sample_content_popularity):
        """Test successful content popularity prediction."""
        request_data = {
            "content_features": [
                {
                    "id": "content-1",
                    "type": "video",
                    "size_mb": 50,
                    "metadata": {"title": "Test Video"},
                    "uploaded_at": datetime.utcnow().isoformat(),
                    "creator_id": "creator-1",
                    "creator_avg_views": 1500
                }
            ],
            "prediction_horizon_days": 7
        }
        
        with patch("src.api.v1.predictive.get_current_user", return_value=mock_current_user), \
             patch("src.api.v1.predictive.get_session"), \
             patch("src.api.v1.predictive.predictive_service.predict_content_popularity") as mock_predict:
            
            mock_predict.return_value = sample_content_popularity
            
            response = await client.post("/api/v1/predictive/content/popularity", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            assert len(data["predictions"]) == 1
            assert data["prediction_horizon_days"] == 7
            assert data["model_confidence"] == 0.75
            assert "generated_at" in data
    
    @pytest.mark.asyncio
    async def test_forecast_usage_success(self, client, app, mock_current_user, sample_usage_forecast):
        """Test successful usage forecasting."""
        request_data = {
            "metric_name": "page_views",
            "forecast_days": 7,
            "include_confidence_intervals": True
        }
        
        with patch("src.api.v1.predictive.get_current_user", return_value=mock_current_user), \
             patch("src.api.v1.predictive.get_session"), \
             patch("src.api.v1.predictive.predictive_service.forecast_usage") as mock_forecast:
            
            mock_forecast.return_value = sample_usage_forecast
            
            response = await client.post("/api/v1/predictive/usage/forecast", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["metric_name"] == "page_views"
            assert data["forecast_period_days"] == 7
            assert len(data["forecasts"]) == 2
            assert "trend" in data
            assert "model_metrics" in data
            assert "generated_at" in data
    
    @pytest.mark.asyncio
    async def test_detect_anomalies_success(self, client, app, mock_current_user):
        """Test successful anomaly detection."""
        request_data = {
            "metric_name": "page_views",
            "data_points": [
                {"timestamp": "2025-07-19T09:00:00Z", "value": 100},
                {"timestamp": "2025-07-19T10:00:00Z", "value": 200},
                {"timestamp": "2025-07-19T11:00:00Z", "value": 150}
            ],
            "sensitivity": 2.0
        }
        
        mock_anomalies = [
            {
                "timestamp": "2025-07-19T10:00:00Z",
                "value": 200,
                "expected_value": 125.0,
                "z_score": 2.5,
                "anomaly_type": "spike",
                "severity": "medium",
                "deviation_percent": 60.0
            }
        ]
        
        with patch("src.api.v1.predictive.get_current_user", return_value=mock_current_user), \
             patch("src.api.v1.predictive.predictive_service.detect_anomalies") as mock_detect:
            
            mock_detect.return_value = mock_anomalies
            
            response = await client.post("/api/v1/predictive/anomalies/detect", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["metric_name"] == "page_views"
            assert len(data["anomalies"]) == 1
            assert data["total_data_points"] == 3
            assert data["anomalies_detected"] == 1
            assert data["sensitivity_used"] == 2.0
            assert "analysis_timestamp" in data
    
    @pytest.mark.asyncio
    async def test_detect_anomalies_view_permission(self, client, app, mock_current_user):
        """Test anomaly detection with view permission."""
        mock_current_user.has_permission = MagicMock(side_effect=lambda perm: perm == "analytics.view")
        
        request_data = {
            "metric_name": "page_views",
            "data_points": [{"timestamp": "2025-07-19T09:00:00Z", "value": 100}],
            "sensitivity": 2.0
        }
        
        with patch("src.api.v1.predictive.get_current_user", return_value=mock_current_user), \
             patch("src.api.v1.predictive.predictive_service.detect_anomalies") as mock_detect:
            
            mock_detect.return_value = []
            
            response = await client.post("/api/v1/predictive/anomalies/detect", json=request_data)
            
            assert response.status_code == 200
            mock_current_user.has_permission.assert_called_with("analytics.view")
    
    @pytest.mark.asyncio
    async def test_train_model_success(self, client, app, mock_current_user):
        """Test successful model training."""
        mock_current_user.has_permission = MagicMock(side_effect=lambda perm: perm == "analytics.admin")
        
        request_data = {
            "model_type": PredictionType.USER_CHURN,
            "training_params": {"max_depth": 10}
        }
        
        with patch("src.api.v1.predictive.get_current_user", return_value=mock_current_user), \
             patch("src.api.v1.predictive.get_session"), \
             patch("src.api.v1.predictive._train_model_background") as mock_train:
            
            response = await client.post("/api/v1/predictive/models/train/user_churn", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            assert "job_id" in data
            assert data["model_type"] == "user_churn"
            assert data["status"] == "queued"
            assert "Model training queued" in data["message"]
            assert data["estimated_completion_minutes"] == 30
            assert "queued_at" in data
    
    @pytest.mark.asyncio
    async def test_train_model_no_admin_permission(self, client, app, mock_current_user):
        """Test model training without admin permission."""
        mock_current_user.has_permission.return_value = False
        
        request_data = {
            "model_type": PredictionType.USER_CHURN,
            "training_params": {}
        }
        
        with patch("src.api.v1.predictive.get_current_user", return_value=mock_current_user), \
             patch("src.api.v1.predictive.get_session"):
            
            response = await client.post("/api/v1/predictive/models/train/user_churn", json=request_data)
            
            assert response.status_code == 403
            data = response.json()
            assert data["detail"] == "Insufficient permissions"
    
    @pytest.mark.asyncio
    async def test_get_training_result_success(self, client, app, mock_current_user):
        """Test successful training result retrieval."""
        mock_current_user.has_permission = MagicMock(side_effect=lambda perm: perm == "analytics.admin")
        
        job_id = "training_user_churn_20250719_100000"
        mock_result = {
            "job_id": job_id,
            "model_type": "user_churn",
            "status": "completed",
            "performance": {
                "accuracy": 0.85,
                "precision": 0.82,
                "recall": 0.88,
                "f1_score": 0.85
            },
            "completed_at": "2025-07-19T10:30:00Z",
            "requested_by": "test-user-123"
        }
        
        with patch("src.api.v1.predictive.get_current_user", return_value=mock_current_user), \
             patch("src.api.v1.predictive.predictive_service._get_redis") as mock_redis_getter:
            
            mock_redis = AsyncMock()
            mock_redis_getter.return_value = mock_redis
            mock_redis.get.return_value = json.dumps(mock_result)
            
            response = await client.get(f"/api/v1/predictive/models/training-result/{job_id}")
            
            assert response.status_code == 200
            data = response.json()
            assert data["job_id"] == job_id
            assert data["status"] == "completed"
            assert "performance" in data
            assert data["performance"]["accuracy"] == 0.85
    
    @pytest.mark.asyncio
    async def test_get_training_result_not_found(self, client, app, mock_current_user):
        """Test training result not found."""
        mock_current_user.has_permission = MagicMock(side_effect=lambda perm: perm == "analytics.admin")
        
        job_id = "nonexistent_job"
        
        with patch("src.api.v1.predictive.get_current_user", return_value=mock_current_user), \
             patch("src.api.v1.predictive.predictive_service._get_redis") as mock_redis_getter:
            
            mock_redis = AsyncMock()
            mock_redis_getter.return_value = mock_redis
            mock_redis.get.return_value = None
            
            response = await client.get(f"/api/v1/predictive/models/training-result/{job_id}")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "not_found"
            assert "Training result not found or expired" in data["message"]
    
    @pytest.mark.asyncio
    async def test_get_models_performance_success(self, client, app, mock_current_user):
        """Test successful model performance retrieval."""
        mock_current_user.has_permission = MagicMock(side_effect=lambda perm: perm == "analytics.view")
        
        mock_performance = {
            "model_type": "random_forest",
            "prediction_type": "user_churn",
            "accuracy": 0.85,
            "precision": 0.82,
            "recall": 0.88,
            "f1_score": 0.85
        }
        
        with patch("src.api.v1.predictive.get_current_user", return_value=mock_current_user), \
             patch("src.api.v1.predictive.predictive_service.get_model_performance") as mock_perf:
            
            mock_perf.return_value = mock_performance
            
            response = await client.get("/api/v1/predictive/models/performance")
            
            assert response.status_code == 200
            data = response.json()
            assert "models" in data
            assert "churn_prediction" in data["models"]
            assert data["models"]["churn_prediction"]["accuracy"] == 0.85
            assert "retrieved_at" in data
    
    @pytest.mark.asyncio
    async def test_get_churn_insights_summary_success(self, client, app, mock_current_user):
        """Test successful churn insights summary."""
        mock_current_user.has_permission = MagicMock(side_effect=lambda perm: perm == "analytics.view")
        
        with patch("src.api.v1.predictive.get_current_user", return_value=mock_current_user), \
             patch("src.api.v1.predictive.get_session"):
            
            response = await client.get("/api/v1/predictive/insights/churn-summary?period_days=30")
            
            assert response.status_code == 200
            data = response.json()
            assert data["period_days"] == 30
            assert "churn_statistics" in data
            assert "risk_distribution" in data
            assert "top_churn_factors" in data
            assert "recommendations" in data
            assert "analysis_date" in data
            
            # Check structure
            churn_stats = data["churn_statistics"]
            assert "total_users_analyzed" in churn_stats
            assert "churned_users" in churn_stats
            assert "churn_rate_percent" in churn_stats
    
    @pytest.mark.asyncio
    async def test_get_predictive_trends_success(self, client, app, mock_current_user, sample_usage_forecast):
        """Test successful predictive trends retrieval."""
        mock_current_user.has_permission = MagicMock(side_effect=lambda perm: perm == "analytics.view")
        
        with patch("src.api.v1.predictive.get_current_user", return_value=mock_current_user), \
             patch("src.api.v1.predictive.get_session"), \
             patch("src.api.v1.predictive.predictive_service.forecast_usage") as mock_forecast:
            
            mock_forecast.return_value = sample_usage_forecast
            
            response = await client.get("/api/v1/predictive/insights/trends?metrics=user_sessions&forecast_days=14")
            
            assert response.status_code == 200
            data = response.json()
            assert "user_sessions" in data["metrics_analyzed"]
            assert data["forecast_horizon_days"] == 14
            assert "trends" in data
            assert "user_sessions" in data["trends"]
            assert "generated_at" in data
    
    @pytest.mark.asyncio
    async def test_get_predictive_trends_with_error(self, client, app, mock_current_user):
        """Test predictive trends with forecast error."""
        mock_current_user.has_permission = MagicMock(side_effect=lambda perm: perm == "analytics.view")
        
        with patch("src.api.v1.predictive.get_current_user", return_value=mock_current_user), \
             patch("src.api.v1.predictive.get_session"), \
             patch("src.api.v1.predictive.predictive_service.forecast_usage") as mock_forecast:
            
            mock_forecast.side_effect = Exception("Insufficient data")
            
            response = await client.get("/api/v1/predictive/insights/trends?metrics=invalid_metric")
            
            assert response.status_code == 200
            data = response.json()
            assert "invalid_metric" in data["trends"]
            assert "error" in data["trends"]["invalid_metric"]
            assert "Failed to forecast invalid_metric" in data["trends"]["invalid_metric"]["error"]
    
    @pytest.mark.asyncio
    async def test_health_check(self, client, app):
        """Test predictive analytics health check."""
        response = await client.get("/api/v1/predictive/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "predictive_analytics"
        assert "timestamp" in data
        assert "available_predictions" in data
        assert "supported_models" in data
        
        # Check available predictions
        predictions = data["available_predictions"]
        assert "user_churn" in predictions
        assert "content_popularity" in predictions
        
        # Check supported models
        models = data["supported_models"]
        assert "random_forest" in models
        assert "linear_regression" in models


class TestPredictiveAPIModels:
    """Test cases for predictive API request/response models."""
    
    def test_churn_prediction_request_validation(self):
        """Test ChurnPredictionRequest model validation."""
        from src.api.v1.predictive import ChurnPredictionRequest
        
        # Valid request
        valid_request = ChurnPredictionRequest(
            user_ids=["user-1", "user-2"],
            include_recommendations=True
        )
        
        assert valid_request.user_ids == ["user-1", "user-2"]
        assert valid_request.include_recommendations is True
        
        # Test validation limits
        with pytest.raises(ValueError):
            ChurnPredictionRequest(user_ids=[])  # Empty list
        
        with pytest.raises(ValueError):
            ChurnPredictionRequest(user_ids=["user-" + str(i) for i in range(101)])  # Too many
    
    def test_content_popularity_request_validation(self):
        """Test ContentPopularityRequest model validation."""
        from src.api.v1.predictive import ContentPopularityRequest
        
        valid_request = ContentPopularityRequest(
            content_features=[{"id": "content-1", "type": "video"}],
            prediction_horizon_days=7
        )
        
        assert len(valid_request.content_features) == 1
        assert valid_request.prediction_horizon_days == 7
        
        # Test horizon limits
        with pytest.raises(ValueError):
            ContentPopularityRequest(
                content_features=[{"id": "content-1"}],
                prediction_horizon_days=0  # Too low
            )
        
        with pytest.raises(ValueError):
            ContentPopularityRequest(
                content_features=[{"id": "content-1"}],
                prediction_horizon_days=31  # Too high
            )
    
    def test_usage_forecast_request_validation(self):
        """Test UsageForecastRequest model validation."""
        from src.api.v1.predictive import UsageForecastRequest
        
        valid_request = UsageForecastRequest(
            metric_name="page_views",
            forecast_days=14,
            include_confidence_intervals=True
        )
        
        assert valid_request.metric_name == "page_views"
        assert valid_request.forecast_days == 14
        assert valid_request.include_confidence_intervals is True
    
    def test_anomaly_detection_request_validation(self):
        """Test AnomalyDetectionRequest model validation."""
        from src.api.v1.predictive import AnomalyDetectionRequest
        
        valid_request = AnomalyDetectionRequest(
            metric_name="page_views",
            data_points=[{"timestamp": "2025-07-19T10:00:00Z", "value": 100}],
            sensitivity=2.5
        )
        
        assert valid_request.metric_name == "page_views"
        assert len(valid_request.data_points) == 1
        assert valid_request.sensitivity == 2.5
        
        # Test sensitivity limits
        with pytest.raises(ValueError):
            AnomalyDetectionRequest(
                metric_name="test",
                data_points=[],
                sensitivity=0.5  # Too low
            )
        
        with pytest.raises(ValueError):
            AnomalyDetectionRequest(
                metric_name="test", 
                data_points=[],
                sensitivity=6.0  # Too high
            )


@pytest.mark.asyncio
async def test_predictive_api_error_handling(client, app, mock_current_user):
    """Test API error handling for unexpected exceptions."""
    with patch("src.api.v1.predictive.get_current_user", return_value=mock_current_user), \
         patch("src.api.v1.predictive.get_session"), \
         patch("src.api.v1.predictive.predictive_service.predict_user_churn",
               side_effect=Exception("Model training failed")):
        
        request_data = {"user_ids": ["user-1"]}
        response = await client.post("/api/v1/predictive/churn/predict", json=request_data)
        
        # The API should handle the exception gracefully
        assert response.status_code == 500
        data = response.json()
        assert "Failed to predict churn" in data["detail"]


@pytest.mark.asyncio
async def test_predictive_api_background_tasks():
    """Test background task functions."""
    from src.api.v1.predictive import _process_churn_batch, _train_model_background
    
    # Mock dependencies
    mock_db = AsyncMock()
    mock_predictive_service = AsyncMock()
    
    with patch("src.api.v1.predictive.predictive_service", mock_predictive_service):
        mock_redis = AsyncMock()
        mock_predictive_service._get_redis.return_value = mock_redis
        mock_predictive_service.predict_user_churn.return_value = [
            {"user_id": "user-1", "churn_probability": 0.5, "risk_level": "medium"}
        ]
        
        # Test churn batch processing
        await _process_churn_batch("batch-123", ["user-1"], "requester-456", mock_db)
        
        mock_predictive_service.predict_user_churn.assert_called_once_with(["user-1"], mock_db)
        mock_redis.setex.assert_called()
        
        # Test model training background task
        mock_performance = ModelPerformance(
            model_type=ModelType.RANDOM_FOREST,
            prediction_type=PredictionType.USER_CHURN,
            accuracy=0.85,
            precision=0.82,
            recall=0.88,
            f1_score=0.85
        )
        mock_predictive_service.train_churn_prediction_model.return_value = mock_performance
        
        await _train_model_background("job-789", PredictionType.USER_CHURN, {}, "requester-456", mock_db)
        
        mock_predictive_service.train_churn_prediction_model.assert_called_once_with(mock_db)
        mock_predictive_service.save_model_performance.assert_called_once()