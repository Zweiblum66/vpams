"""
Tests for Usage Predictor Service
"""

import pytest
from datetime import datetime, timedelta, date
from unittest.mock import Mock, AsyncMock, patch
import numpy as np
import pandas as pd

from src.services.usage_predictor import UsagePredictor
from src.models.schemas import (
    UsagePrediction, UsagePredictionRequest, UsageTrend,
    ModelType, TrendDirection
)
from src.db.models import UsageHistoryModel, PredictionModel


@pytest.fixture
def mock_db():
    """Mock database session"""
    db = AsyncMock()
    db.execute = AsyncMock()
    db.add = Mock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    return db


@pytest.fixture
def usage_predictor(mock_db):
    """Create usage predictor instance"""
    return UsagePredictor(db=mock_db)


@pytest.fixture
def sample_usage_history():
    """Sample usage history data"""
    return [
        UsageHistoryModel(
            asset_id="asset1",
            user_id="user1",
            access_count=10,
            timestamp=datetime.utcnow() - timedelta(days=i)
        )
        for i in range(30)
    ]


class TestUsagePredictor:
    """Test usage prediction functionality"""
    
    @pytest.mark.asyncio
    async def test_initialize(self, usage_predictor):
        """Test predictor initialization"""
        await usage_predictor.initialize()
        
        assert usage_predictor.prophet_model is not None
        assert usage_predictor.arima_model is not None
        assert usage_predictor.lstm_model is not None
        assert usage_predictor.xgboost_model is not None
    
    @pytest.mark.asyncio
    async def test_predict_usage_single_asset(self, usage_predictor, mock_db):
        """Test usage prediction for single asset"""
        # Mock historical data
        mock_result = Mock()
        mock_result.all.return_value = [
            (datetime.utcnow() - timedelta(days=i), 10 + i % 5)
            for i in range(30)
        ]
        mock_db.execute.return_value = mock_result
        
        # Make prediction
        predictions = await usage_predictor.predict_usage(
            asset_ids=["asset1"],
            horizon_days=7
        )
        
        assert len(predictions) == 7
        assert all(p.asset_id == "asset1" for p in predictions)
        assert all(isinstance(p, UsagePrediction) for p in predictions)
        assert all(p.confidence_score > 0 for p in predictions)
    
    @pytest.mark.asyncio
    async def test_predict_usage_multiple_models(self, usage_predictor, mock_db):
        """Test prediction with specific models"""
        # Mock historical data
        mock_result = Mock()
        mock_result.all.return_value = [
            (datetime.utcnow() - timedelta(days=i), 10)
            for i in range(30)
        ]
        mock_db.execute.return_value = mock_result
        
        # Test with Prophet only
        predictions = await usage_predictor.predict_usage(
            asset_ids=["asset1"],
            horizon_days=7,
            models_to_use=[ModelType.PROPHET]
        )
        
        assert len(predictions) == 7
        assert all(p.model_used == ModelType.PROPHET for p in predictions)
    
    @pytest.mark.asyncio
    async def test_analyze_trends(self, usage_predictor, mock_db):
        """Test trend analysis"""
        # Mock historical data with upward trend
        mock_result = Mock()
        mock_result.all.return_value = [
            (datetime.utcnow() - timedelta(days=30-i), i * 2)
            for i in range(30)
        ]
        mock_db.execute.return_value = mock_result
        
        trend = await usage_predictor.analyze_trends("asset1")
        
        assert isinstance(trend, UsageTrend)
        assert trend.asset_id == "asset1"
        assert trend.trend_direction == TrendDirection.INCREASING
        assert trend.growth_rate > 0
        assert len(trend.seasonal_patterns) > 0
    
    @pytest.mark.asyncio
    async def test_prophet_prediction(self, usage_predictor):
        """Test Prophet model prediction"""
        # Create sample data
        dates = pd.date_range(
            start=datetime.utcnow() - timedelta(days=90),
            end=datetime.utcnow(),
            freq='D'
        )
        values = [50 + i % 7 * 10 + np.random.normal(0, 5) for i in range(len(dates))]
        
        predictions = await usage_predictor._predict_with_prophet(
            dates.tolist(),
            values,
            horizon_days=7
        )
        
        assert len(predictions) == 7
        assert all(isinstance(p, tuple) for p in predictions)
        assert all(len(p) == 4 for p in predictions)  # date, value, lower, upper
    
    @pytest.mark.asyncio
    async def test_arima_prediction(self, usage_predictor):
        """Test ARIMA model prediction"""
        # Create sample data
        values = [50 + i % 7 * 10 for i in range(90)]
        
        predictions = await usage_predictor._predict_with_arima(values, horizon_days=7)
        
        assert len(predictions) == 7
        assert all(isinstance(p, float) for p in predictions)
    
    @pytest.mark.asyncio
    async def test_lstm_prediction(self, usage_predictor):
        """Test LSTM model prediction"""
        # Create sample data
        values = [50 + i % 7 * 10 for i in range(90)]
        
        predictions = await usage_predictor._predict_with_lstm(values, horizon_days=7)
        
        assert len(predictions) == 7
        assert all(isinstance(p, float) for p in predictions)
    
    @pytest.mark.asyncio
    async def test_xgboost_prediction(self, usage_predictor):
        """Test XGBoost model prediction"""
        # Create sample data
        dates = pd.date_range(
            start=datetime.utcnow() - timedelta(days=90),
            end=datetime.utcnow(),
            freq='D'
        )
        values = [50 + i % 7 * 10 for i in range(len(dates))]
        
        predictions = await usage_predictor._predict_with_xgboost(
            dates.tolist(),
            values,
            horizon_days=7
        )
        
        assert len(predictions) == 7
        assert all(isinstance(p, float) for p in predictions)
    
    @pytest.mark.asyncio
    async def test_ensemble_prediction(self, usage_predictor):
        """Test ensemble prediction combining multiple models"""
        # Create predictions from different models
        predictions_list = [
            [50, 52, 54, 56, 58, 60, 62],  # Increasing trend
            [50, 50, 50, 50, 50, 50, 50],  # Flat
            [50, 48, 46, 44, 42, 40, 38],  # Decreasing trend
        ]
        
        ensemble = usage_predictor._ensemble_predictions(predictions_list)
        
        assert len(ensemble) == 7
        # Ensemble should be average of inputs
        for i, val in enumerate(ensemble):
            expected = sum(p[i] for p in predictions_list) / len(predictions_list)
            assert abs(val - expected) < 0.01
    
    @pytest.mark.asyncio
    async def test_store_predictions(self, usage_predictor, mock_db):
        """Test storing predictions in database"""
        predictions = [
            UsagePrediction(
                asset_id="asset1",
                prediction_date=date.today() + timedelta(days=i),
                predicted_access_count=50 + i,
                confidence_interval_lower=45 + i,
                confidence_interval_upper=55 + i,
                confidence_score=0.85,
                model_used=ModelType.PROPHET
            )
            for i in range(7)
        ]
        
        await usage_predictor._store_predictions(predictions)
        
        # Verify database calls
        assert mock_db.add.call_count == 7
        assert mock_db.commit.called
    
    @pytest.mark.asyncio
    async def test_calculate_confidence_score(self, usage_predictor):
        """Test confidence score calculation"""
        # Test with consistent predictions
        predictions = [50, 50, 50, 50]
        score = usage_predictor._calculate_confidence_score(predictions)
        assert score > 0.9  # High confidence for consistent predictions
        
        # Test with varying predictions
        predictions = [50, 100, 25, 75]
        score = usage_predictor._calculate_confidence_score(predictions)
        assert score < 0.5  # Low confidence for varying predictions
    
    @pytest.mark.asyncio
    async def test_detect_seasonality(self, usage_predictor):
        """Test seasonality detection"""
        # Create data with weekly pattern
        values = []
        for week in range(13):  # 13 weeks
            values.extend([100, 80, 70, 60, 50, 40, 120])  # Weekly pattern
        
        patterns = usage_predictor._detect_seasonality(values)
        
        assert "weekly" in patterns
        assert patterns["weekly"]["period"] == 7
        assert patterns["weekly"]["strength"] > 0.5
    
    @pytest.mark.asyncio
    async def test_empty_history_handling(self, usage_predictor, mock_db):
        """Test handling of assets with no history"""
        # Mock empty historical data
        mock_result = Mock()
        mock_result.all.return_value = []
        mock_db.execute.return_value = mock_result
        
        predictions = await usage_predictor.predict_usage(
            asset_ids=["asset1"],
            horizon_days=7
        )
        
        # Should return empty predictions for assets with no history
        assert len(predictions) == 0
    
    @pytest.mark.asyncio
    async def test_prediction_with_outliers(self, usage_predictor, mock_db):
        """Test prediction handling with outliers in data"""
        # Mock data with outliers
        mock_result = Mock()
        data = [(datetime.utcnow() - timedelta(days=i), 50) for i in range(30)]
        # Add outliers
        data[10] = (data[10][0], 500)  # 10x normal value
        data[20] = (data[20][0], 5)    # 0.1x normal value
        mock_result.all.return_value = data
        mock_db.execute.return_value = mock_result
        
        predictions = await usage_predictor.predict_usage(
            asset_ids=["asset1"],
            horizon_days=7
        )
        
        # Predictions should be reasonable despite outliers
        assert len(predictions) == 7
        assert all(20 < p.predicted_access_count < 80 for p in predictions)