"""
Tests for Predictive Analytics Service

This module contains comprehensive tests for the predictive analytics functionality.
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import MagicMock, AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.predictive_analytics import (
    PredictiveAnalytics, PredictionType, ModelType, ModelPerformance, PredictionResult
)
from src.models.analytics import UserBehavior


@pytest.fixture
def predictive_service():
    """Create a predictive analytics service instance for testing."""
    return PredictiveAnalytics()


@pytest.fixture
async def mock_db():
    """Create a mock database session."""
    db = AsyncMock(spec=AsyncSession)
    db.execute = AsyncMock()
    return db


@pytest.fixture
def sample_user_behaviors():
    """Create sample user behavior data for testing."""
    behaviors = []
    base_date = datetime.utcnow() - timedelta(days=30)
    
    for i in range(50):
        # Create diverse user behaviors
        behavior = MagicMock()
        behavior.id = f"behavior-{i}"
        behavior.user_id = f"user-{i}"
        behavior.period_start = base_date + timedelta(days=i % 30)
        behavior.period_end = base_date + timedelta(days=(i % 30) + 1)
        behavior.sessions_count = np.random.randint(1, 50)
        behavior.total_time_minutes = np.random.randint(10, 500)
        behavior.page_views = np.random.randint(5, 200)
        behavior.actions_count = np.random.randint(5, 100)
        behavior.assets_viewed = np.random.randint(0, 50)
        behavior.assets_uploaded = np.random.randint(0, 20)
        behavior.searches_performed = np.random.randint(0, 30)
        behavior.avg_session_duration = np.random.uniform(5, 30)
        behavior.bounce_rate = np.random.uniform(0, 0.5)
        behavior.workflows_executed = np.random.randint(0, 10)
        
        behaviors.append(behavior)
    
    return behaviors


class TestPredictiveAnalytics:
    """Test cases for the PredictiveAnalytics class."""
    
    @pytest.mark.asyncio
    async def test_collect_churn_training_data(self, predictive_service, mock_db, sample_user_behaviors):
        """Test collecting churn training data."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = sample_user_behaviors
        mock_db.execute.return_value = mock_result
        
        training_data = await predictive_service._collect_churn_training_data(mock_db)
        
        assert len(training_data) == len(sample_user_behaviors)
        assert all(isinstance(item, dict) for item in training_data)
        assert all('is_churned' in item for item in training_data)
        assert all('user_id' in item for item in training_data)
        assert all('sessions_count' in item for item in training_data)
    
    @pytest.mark.asyncio
    async def test_prepare_churn_features(self, predictive_service):
        """Test preparing features for churn prediction."""
        training_data = [
            {
                'user_id': 'user-1',
                'sessions_count': 10,
                'total_time_minutes': 200,
                'page_views': 50,
                'actions_count': 25,
                'assets_viewed': 15,
                'assets_uploaded': 5,
                'searches_performed': 8,
                'avg_session_duration': 20.0,
                'bounce_rate': 0.1,
                'workflows_executed': 2,
                'days_since_activity': 5,
                'is_churned': 0
            },
            {
                'user_id': 'user-2',
                'sessions_count': 2,
                'total_time_minutes': 30,
                'page_views': 8,
                'actions_count': 3,
                'assets_viewed': 2,
                'assets_uploaded': 0,
                'searches_performed': 1,
                'avg_session_duration': 15.0,
                'bounce_rate': 0.5,
                'workflows_executed': 0,
                'days_since_activity': 20,
                'is_churned': 1
            }
        ]
        
        X, y, feature_names = await predictive_service._prepare_churn_features(training_data)
        
        assert X.shape[0] == 2  # Two samples
        assert X.shape[1] == len(feature_names)  # Number of features
        assert len(y) == 2
        assert y[0] == 0 and y[1] == 1  # Churn labels
        
        # Check that additional features are created
        assert 'engagement_score' in feature_names
        assert 'activity_ratio' in feature_names
        assert 'content_interaction_ratio' in feature_names
    
    @pytest.mark.asyncio
    async def test_train_churn_model_insufficient_data(self, predictive_service, mock_db):
        """Test churn model training with insufficient data."""
        # Mock insufficient data
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result
        
        with pytest.raises(ValueError, match="Insufficient data"):
            await predictive_service.train_churn_prediction_model(mock_db)
    
    @pytest.mark.asyncio
    async def test_train_churn_model_success(self, predictive_service, mock_db, sample_user_behaviors):
        """Test successful churn model training."""
        with patch.object(predictive_service, '_get_redis') as mock_redis_getter:
            mock_redis = AsyncMock()
            mock_redis_getter.return_value = mock_redis
            
            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = sample_user_behaviors
            mock_db.execute.return_value = mock_result
            
            performance = await predictive_service.train_churn_prediction_model(mock_db)
            
            assert isinstance(performance, ModelPerformance)
            assert performance.model_type == ModelType.RANDOM_FOREST
            assert performance.prediction_type == PredictionType.USER_CHURN
            assert 0.0 <= performance.accuracy <= 1.0
            assert 0.0 <= performance.precision <= 1.0
            assert 0.0 <= performance.recall <= 1.0
            assert 0.0 <= performance.f1_score <= 1.0
            assert performance.feature_importance is not None
            assert performance.training_date is not None
            
            # Verify model was cached
            mock_redis.setex.assert_called()
    
    @pytest.mark.asyncio
    async def test_get_user_features_for_churn(self, predictive_service, mock_db, sample_user_behaviors):
        """Test getting user features for churn prediction."""
        user_ids = ["user-1", "user-2"]
        
        # Filter behaviors for the specified users
        filtered_behaviors = [b for b in sample_user_behaviors if str(b.user_id) in user_ids]
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = filtered_behaviors
        mock_db.execute.return_value = mock_result
        
        features = await predictive_service._get_user_features_for_churn(user_ids, mock_db)
        
        assert isinstance(features, dict)
        for user_id in user_ids:
            if user_id in features:
                user_features = features[user_id]
                assert 'sessions_count' in user_features
                assert 'engagement_score' in user_features
                assert 'activity_ratio' in user_features
                assert 'content_interaction_ratio' in user_features
                assert 'days_since_activity' in user_features
    
    @pytest.mark.asyncio
    async def test_predict_user_churn_no_model(self, predictive_service, mock_db):
        """Test churn prediction when no model is available."""
        with patch.object(predictive_service, '_load_model', return_value=(None, None)):
            with pytest.raises(ValueError, match="Churn prediction model not found"):
                await predictive_service.predict_user_churn(["user-1"], mock_db)
    
    @pytest.mark.asyncio
    async def test_predict_user_churn_success(self, predictive_service, mock_db):
        """Test successful churn prediction."""
        # Mock model and scaler
        mock_model = MagicMock()
        mock_model.predict_proba.return_value = np.array([[0.7, 0.3], [0.2, 0.8]])  # Probabilities
        mock_model.predict.return_value = np.array([0, 1])  # Predictions
        
        mock_scaler = MagicMock()
        mock_scaler.transform.return_value = np.array([[1, 2, 3], [4, 5, 6]])
        
        with patch.object(predictive_service, '_load_model', return_value=(mock_model, mock_scaler)), \
             patch.object(predictive_service, '_get_user_features_for_churn') as mock_features:
            
            mock_features.return_value = {
                'user-1': {
                    'sessions_count': 10, 'total_time_minutes': 200, 'page_views': 50,
                    'actions_count': 25, 'assets_viewed': 15, 'assets_uploaded': 5,
                    'searches_performed': 8, 'avg_session_duration': 20.0,
                    'bounce_rate': 0.1, 'workflows_executed': 2, 'days_since_activity': 5,
                    'engagement_score': 15.0, 'activity_ratio': 2.5, 'content_interaction_ratio': 0.3
                },
                'user-2': {
                    'sessions_count': 2, 'total_time_minutes': 30, 'page_views': 8,
                    'actions_count': 3, 'assets_viewed': 2, 'assets_uploaded': 0,
                    'searches_performed': 1, 'avg_session_duration': 15.0,
                    'bounce_rate': 0.5, 'workflows_executed': 0, 'days_since_activity': 20,
                    'engagement_score': 2.0, 'activity_ratio': 1.5, 'content_interaction_ratio': 0.25
                }
            }
            
            predictions = await predictive_service.predict_user_churn(['user-1', 'user-2'], mock_db)
            
            assert len(predictions) == 2
            for prediction in predictions:
                assert 'user_id' in prediction
                assert 'churn_probability' in prediction
                assert 'churn_prediction' in prediction
                assert 'risk_level' in prediction
                assert 'days_to_churn_estimate' in prediction
                assert 'recommended_actions' in prediction
                
                # Check probability bounds
                assert 0.0 <= prediction['churn_probability'] <= 1.0
    
    def test_get_churn_risk_level(self, predictive_service):
        """Test churn risk level classification."""
        assert predictive_service._get_churn_risk_level(0.9) == "very_high"
        assert predictive_service._get_churn_risk_level(0.7) == "high"
        assert predictive_service._get_churn_risk_level(0.5) == "medium"
        assert predictive_service._get_churn_risk_level(0.3) == "low"
        assert predictive_service._get_churn_risk_level(0.1) == "very_low"
    
    def test_estimate_days_to_churn(self, predictive_service):
        """Test days to churn estimation."""
        assert predictive_service._estimate_days_to_churn(0.95) == 3
        assert predictive_service._estimate_days_to_churn(0.85) == 7
        assert predictive_service._estimate_days_to_churn(0.7) == 14
        assert predictive_service._estimate_days_to_churn(0.5) == 30
        assert predictive_service._estimate_days_to_churn(0.1) == 60
    
    def test_get_churn_prevention_recommendations(self, predictive_service):
        """Test churn prevention recommendations."""
        # High risk user with low activity
        user_features = {
            'sessions_count': 2,
            'assets_uploaded': 0,
            'avg_session_duration': 3,
            'searches_performed': 25,
            'assets_viewed': 5
        }
        
        recommendations = predictive_service._get_churn_prevention_recommendations(0.8, user_features)
        
        assert isinstance(recommendations, list)
        assert len(recommendations) <= 3
        
        # Check specific recommendations
        assert any("re-engagement" in rec for rec in recommendations)
        assert any("onboarding" in rec for rec in recommendations)
        assert any("upload" in rec for rec in recommendations)
    
    @pytest.mark.asyncio
    async def test_predict_content_popularity(self, predictive_service):
        """Test content popularity prediction."""
        content_features = [
            {
                'id': 'content-1',
                'type': 'video',
                'size_mb': 50,
                'metadata': {'title': 'Test Video', 'description': 'Test description'},
                'uploaded_at': datetime.utcnow() - timedelta(hours=2),
                'creator_id': 'creator-1',
                'creator_avg_views': 1500
            },
            {
                'id': 'content-2',
                'type': 'image',
                'size_mb': 5,
                'metadata': {'title': 'Test Image'},
                'uploaded_at': datetime.utcnow() - timedelta(days=5),
                'creator_id': 'creator-2',
                'creator_avg_views': 500
            }
        ]
        
        predictions = await predictive_service.predict_content_popularity(content_features, 7)
        
        assert len(predictions) == 2
        for prediction in predictions:
            assert 'content_id' in prediction
            assert 'popularity_score' in prediction
            assert 'predicted_views' in prediction
            assert 'predicted_interactions' in prediction
            assert 'confidence' in prediction
            assert 'factors' in prediction
            
            # Check bounds
            assert 0.0 <= prediction['popularity_score'] <= 1.0
            assert prediction['predicted_views'] >= 0
            assert prediction['predicted_interactions'] >= 0
    
    @pytest.mark.asyncio
    async def test_forecast_usage_insufficient_data(self, predictive_service, mock_db):
        """Test usage forecasting with insufficient data."""
        with patch.object(predictive_service, '_get_historical_metric_data', return_value=[]):
            with pytest.raises(ValueError, match="Insufficient historical data"):
                await predictive_service.forecast_usage("page_views", 7, mock_db)
    
    @pytest.mark.asyncio
    async def test_forecast_usage_success(self, predictive_service, mock_db):
        """Test successful usage forecasting."""
        # Mock historical data
        historical_data = [
            {'date': '2025-07-01', 'value': 1000},
            {'date': '2025-07-02', 'value': 1050},
            {'date': '2025-07-03', 'value': 1100},
            {'date': '2025-07-04', 'value': 1150},
            {'date': '2025-07-05', 'value': 1200},
            {'date': '2025-07-06', 'value': 1250},
            {'date': '2025-07-07', 'value': 1300},
            {'date': '2025-07-08', 'value': 1350},
            {'date': '2025-07-09', 'value': 1400},
            {'date': '2025-07-10', 'value': 1450},
            {'date': '2025-07-11', 'value': 1500},
            {'date': '2025-07-12', 'value': 1550},
            {'date': '2025-07-13', 'value': 1600},
            {'date': '2025-07-14', 'value': 1650},
            {'date': '2025-07-15', 'value': 1700}
        ]
        
        with patch.object(predictive_service, '_get_historical_metric_data', return_value=historical_data):
            forecast = await predictive_service.forecast_usage("page_views", 7, mock_db)
            
            assert forecast['metric_name'] == "page_views"
            assert forecast['forecast_period_days'] == 7
            assert len(forecast['forecasts']) == 7
            assert 'trend' in forecast
            assert 'model_metrics' in forecast
            assert 'generated_at' in forecast
            
            # Check forecast structure
            for forecast_point in forecast['forecasts']:
                assert 'date' in forecast_point
                assert 'predicted_value' in forecast_point
                assert 'lower_bound' in forecast_point
                assert 'upper_bound' in forecast_point
                assert 'confidence' in forecast_point
                
                # Check bounds
                assert forecast_point['predicted_value'] >= 0
                assert forecast_point['lower_bound'] >= 0
                assert forecast_point['upper_bound'] >= forecast_point['predicted_value']
    
    @pytest.mark.asyncio
    async def test_detect_anomalies_insufficient_data(self, predictive_service):
        """Test anomaly detection with insufficient data."""
        data_points = [
            {'timestamp': '2025-07-19T10:00:00Z', 'value': 100}
        ]
        
        anomalies = await predictive_service.detect_anomalies("test_metric", data_points, 2.0)
        assert anomalies == []
    
    @pytest.mark.asyncio
    async def test_detect_anomalies_success(self, predictive_service):
        """Test successful anomaly detection."""
        # Create data with clear anomalies
        data_points = []
        base_time = datetime.utcnow()
        
        # Normal data points
        for i in range(20):
            data_points.append({
                'timestamp': (base_time + timedelta(minutes=i)).isoformat(),
                'value': 100 + np.random.normal(0, 5)  # Normal values around 100
            })
        
        # Add anomalies
        data_points.append({
            'timestamp': (base_time + timedelta(minutes=20)).isoformat(),
            'value': 200  # Clear spike
        })
        data_points.append({
            'timestamp': (base_time + timedelta(minutes=21)).isoformat(),
            'value': 10   # Clear drop
        })
        
        anomalies = await predictive_service.detect_anomalies("test_metric", data_points, 2.0)
        
        # Should detect at least one anomaly
        assert len(anomalies) >= 1
        
        for anomaly in anomalies:
            assert 'timestamp' in anomaly
            assert 'value' in anomaly
            assert 'expected_value' in anomaly
            assert 'z_score' in anomaly
            assert 'anomaly_type' in anomaly
            assert 'severity' in anomaly
            assert 'deviation_percent' in anomaly
            
            # Check anomaly type
            assert anomaly['anomaly_type'] in ['spike', 'drop']
            assert anomaly['severity'] in ['low', 'medium', 'high']
            assert anomaly['z_score'] > 2.0  # Above sensitivity threshold
    
    @pytest.mark.asyncio
    async def test_load_model_from_memory(self, predictive_service):
        """Test loading model from memory cache."""
        # Add model to memory cache
        mock_model = MagicMock()
        mock_scaler = MagicMock()
        predictive_service.models['test_model'] = mock_model
        predictive_service.scalers['test_model'] = mock_scaler
        
        model, scaler = await predictive_service._load_model('test_model')
        
        assert model is mock_model
        assert scaler is mock_scaler
    
    @pytest.mark.asyncio
    async def test_load_model_from_redis(self, predictive_service):
        """Test loading model from Redis."""
        with patch.object(predictive_service, '_get_redis') as mock_redis_getter:
            mock_redis = AsyncMock()
            mock_redis_getter.return_value = mock_redis
            
            # Mock Redis data
            mock_model_data = {
                'model': b'mock_model_data',
                'scaler': b'mock_scaler_data'
            }
            mock_redis.get.return_value = json.dumps(mock_model_data)
            
            with patch('joblib.loads', side_effect=[MagicMock(), MagicMock()]):
                model, scaler = await predictive_service._load_model('test_model')
                
                assert model is not None
                assert scaler is not None
                
                # Verify model was cached in memory
                assert 'test_model' in predictive_service.models
                assert 'test_model' in predictive_service.scalers
    
    @pytest.mark.asyncio
    async def test_load_model_not_found(self, predictive_service):
        """Test loading non-existent model."""
        with patch.object(predictive_service, '_get_redis') as mock_redis_getter:
            mock_redis = AsyncMock()
            mock_redis_getter.return_value = mock_redis
            mock_redis.get.return_value = None
            
            model, scaler = await predictive_service._load_model('nonexistent_model')
            
            assert model is None
            assert scaler is None
    
    @pytest.mark.asyncio
    async def test_get_historical_metric_data(self, predictive_service, mock_db):
        """Test getting historical metric data."""
        historical_data = await predictive_service._get_historical_metric_data("page_views", mock_db, 30)
        
        assert len(historical_data) == 30
        for data_point in historical_data:
            assert 'date' in data_point
            assert 'value' in data_point
            assert data_point['value'] >= 0
    
    @pytest.mark.asyncio
    async def test_save_and_get_model_performance(self, predictive_service):
        """Test saving and retrieving model performance."""
        with patch.object(predictive_service, '_get_redis') as mock_redis_getter:
            mock_redis = AsyncMock()
            mock_redis_getter.return_value = mock_redis
            
            performance = ModelPerformance(
                model_type=ModelType.RANDOM_FOREST,
                prediction_type=PredictionType.USER_CHURN,
                accuracy=0.85,
                precision=0.82,
                recall=0.88,
                f1_score=0.85,
                feature_importance={'feature1': 0.4, 'feature2': 0.6},
                training_date=datetime.utcnow()
            )
            
            # Test saving
            await predictive_service.save_model_performance('test_model', performance)
            mock_redis.setex.assert_called()
            
            # Test getting
            mock_redis.get.return_value = json.dumps({
                'model_type': 'random_forest',
                'prediction_type': 'user_churn',
                'accuracy': 0.85,
                'precision': 0.82,
                'recall': 0.88,
                'f1_score': 0.85
            })
            
            retrieved_performance = await predictive_service.get_model_performance('test_model')
            
            assert retrieved_performance is not None
            assert retrieved_performance['accuracy'] == 0.85
            assert retrieved_performance['precision'] == 0.82


class TestModelPerformance:
    """Test cases for ModelPerformance data class."""
    
    def test_model_performance_creation(self):
        """Test ModelPerformance creation."""
        performance = ModelPerformance(
            model_type=ModelType.RANDOM_FOREST,
            prediction_type=PredictionType.USER_CHURN,
            accuracy=0.85,
            precision=0.82,
            recall=0.88,
            f1_score=0.85,
            rmse=0.15,
            mae=0.12,
            r2_score=0.75,
            feature_importance={'feature1': 0.6, 'feature2': 0.4},
            training_date=datetime.utcnow(),
            validation_metrics={'cv_score': 0.83}
        )
        
        assert performance.model_type == ModelType.RANDOM_FOREST
        assert performance.prediction_type == PredictionType.USER_CHURN
        assert performance.accuracy == 0.85
        assert performance.precision == 0.82
        assert performance.recall == 0.88
        assert performance.f1_score == 0.85
        assert performance.rmse == 0.15
        assert performance.mae == 0.12
        assert performance.r2_score == 0.75
        assert performance.feature_importance == {'feature1': 0.6, 'feature2': 0.4}
        assert performance.validation_metrics == {'cv_score': 0.83}


@pytest.mark.asyncio
async def test_predictive_analytics_cleanup():
    """Test predictive analytics cleanup."""
    service = PredictiveAnalytics()
    mock_redis = AsyncMock()
    service.redis_client = mock_redis
    
    await service.close()
    mock_redis.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_predictive_analytics_error_handling(predictive_service, mock_db):
    """Test error handling in predictive analytics."""
    with patch.object(predictive_service, '_get_redis', side_effect=Exception("Redis connection failed")):
        # Should handle Redis errors gracefully
        model, scaler = await predictive_service._load_model('test_model')
        assert model is None
        assert scaler is None