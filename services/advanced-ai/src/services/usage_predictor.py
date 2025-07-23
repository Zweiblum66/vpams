"""
Usage Prediction Service

Predicts future asset usage patterns using multiple ML models.
"""

import asyncio
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta, date
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error
import xgboost as xgb
from prophet import Prophet
import pmdarima as pm
import torch
import torch.nn as nn
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
import structlog
import joblib
from pathlib import Path

from ..core.config import settings
from ..models.schemas import (
    UsagePattern, UsagePrediction, UsageTrend,
    ModelType, PredictionType
)
from ..db.models import (
    UsageHistoryModel, PredictionModel, ModelMetadataModel
)
from ..utils.feature_engineering import FeatureEngineer
from ..utils.metrics import ai_metrics


logger = structlog.get_logger()


class LSTMPredictor(nn.Module):
    """LSTM model for time series prediction"""
    
    def __init__(self, input_size: int, hidden_size: int = 50, num_layers: int = 2):
        super(LSTMPredictor, self).__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
        self.fc = nn.Linear(hidden_size, 1)
    
    def forward(self, x):
        h0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size)
        c0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size)
        
        out, _ = self.lstm(x, (h0, c0))
        out = self.fc(out[:, -1, :])
        return out


class UsagePredictor:
    """Predicts future usage patterns for assets"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.models: Dict[str, Any] = {}
        self.scalers: Dict[str, StandardScaler] = {}
        self.feature_engineer = FeatureEngineer()
        self.model_path = Path(settings.MODEL_CACHE_PATH) / "usage_prediction"
        self.model_path.mkdir(parents=True, exist_ok=True)
    
    async def initialize(self):
        """Initialize usage predictor"""
        logger.info("Initializing usage predictor")
        
        # Load existing models if available
        await self._load_models()
        
        # Schedule periodic model updates
        asyncio.create_task(self._periodic_model_update())
    
    async def predict_usage(
        self,
        asset_ids: List[str],
        horizon_days: int = 30,
        models_to_use: Optional[List[ModelType]] = None
    ) -> List[UsagePrediction]:
        """Predict future usage for assets"""
        logger.info(
            "Predicting usage",
            asset_count=len(asset_ids),
            horizon_days=horizon_days
        )
        
        predictions = []
        
        for asset_id in asset_ids:
            # Get historical data
            history = await self._get_usage_history(asset_id)
            
            if len(history) < 30:  # Need at least 30 days of history
                logger.warning(f"Insufficient history for asset {asset_id}")
                continue
            
            # Prepare data
            df = self._prepare_dataframe(history)
            
            # Generate predictions from each model
            model_predictions = {}
            models = models_to_use or settings.USAGE_PREDICTION_MODELS
            
            for model_type in models:
                try:
                    if model_type == "prophet":
                        pred = await self._predict_prophet(df, horizon_days)
                    elif model_type == "arima":
                        pred = await self._predict_arima(df, horizon_days)
                    elif model_type == "lstm":
                        pred = await self._predict_lstm(df, horizon_days)
                    elif model_type == "xgboost":
                        pred = await self._predict_xgboost(df, horizon_days)
                    else:
                        continue
                    
                    model_predictions[model_type] = pred
                except Exception as e:
                    logger.error(f"Error in {model_type} prediction", error=str(e))
            
            # Ensemble predictions
            if model_predictions:
                ensemble_predictions = self._ensemble_predictions(model_predictions)
                
                # Create prediction objects
                for i, (date_val, pred_val, lower, upper) in enumerate(ensemble_predictions):
                    prediction = UsagePrediction(
                        asset_id=asset_id,
                        prediction_date=date_val,
                        predicted_access_count=pred_val,
                        confidence_interval_lower=lower,
                        confidence_interval_upper=upper,
                        confidence_score=self._calculate_confidence(lower, upper, pred_val),
                        model_used=ModelType.ENSEMBLE,
                        features_used=self.feature_engineer.get_feature_names()
                    )
                    predictions.append(prediction)
                    
                    # Store prediction
                    await self._store_prediction(prediction)
        
        # Update metrics
        ai_metrics.predictions_made.labels(
            type=PredictionType.USAGE.value,
            model=ModelType.ENSEMBLE.value
        ).inc(len(predictions))
        
        return predictions
    
    async def analyze_trends(self, asset_id: str) -> UsageTrend:
        """Analyze usage trends for an asset"""
        history = await self._get_usage_history(asset_id)
        
        if len(history) < 14:  # Need at least 2 weeks
            return UsageTrend(
                asset_id=asset_id,
                trend_direction="insufficient_data",
                trend_strength=0.0,
                seasonal_pattern=None,
                peak_periods=[],
                forecast_accuracy=0.0
            )
        
        df = self._prepare_dataframe(history)
        
        # Trend analysis
        trend_direction, trend_strength = self._analyze_trend(df)
        
        # Seasonal pattern detection
        seasonal_pattern = self._detect_seasonality(df)
        
        # Peak period identification
        peak_periods = self._identify_peak_periods(df)
        
        # Calculate forecast accuracy from recent predictions
        forecast_accuracy = await self._calculate_forecast_accuracy(asset_id)
        
        return UsageTrend(
            asset_id=asset_id,
            trend_direction=trend_direction,
            trend_strength=trend_strength,
            seasonal_pattern=seasonal_pattern,
            peak_periods=peak_periods,
            forecast_accuracy=forecast_accuracy
        )
    
    async def _predict_prophet(self, df: pd.DataFrame, horizon_days: int) -> List[Tuple[date, float, float, float]]:
        """Prophet model prediction"""
        # Prepare data for Prophet
        prophet_df = df[['date', 'access_count']].rename(columns={'date': 'ds', 'access_count': 'y'})
        
        # Create and fit model
        model = Prophet(
            daily_seasonality=True,
            weekly_seasonality=True,
            yearly_seasonality=True,
            changepoint_prior_scale=0.05
        )
        model.fit(prophet_df)
        
        # Make predictions
        future = model.make_future_dataframe(periods=horizon_days)
        forecast = model.predict(future)
        
        # Extract predictions
        predictions = []
        for _, row in forecast.tail(horizon_days).iterrows():
            predictions.append((
                row['ds'].date(),
                max(0, row['yhat']),  # Ensure non-negative
                max(0, row['yhat_lower']),
                max(0, row['yhat_upper'])
            ))
        
        return predictions
    
    async def _predict_arima(self, df: pd.DataFrame, horizon_days: int) -> List[Tuple[date, float, float, float]]:
        """ARIMA model prediction"""
        # Prepare time series
        ts = df.set_index('date')['access_count']
        
        # Auto ARIMA
        model = pm.auto_arima(
            ts,
            seasonal=True,
            m=7,  # Weekly seasonality
            suppress_warnings=True,
            stepwise=True,
            trace=False
        )
        
        # Make predictions
        forecast, conf_int = model.predict(n_periods=horizon_days, return_conf_int=True)
        
        # Generate dates
        last_date = df['date'].max()
        future_dates = [last_date + timedelta(days=i+1) for i in range(horizon_days)]
        
        # Combine predictions
        predictions = []
        for i, date_val in enumerate(future_dates):
            predictions.append((
                date_val,
                max(0, forecast[i]),
                max(0, conf_int[i][0]),
                max(0, conf_int[i][1])
            ))
        
        return predictions
    
    async def _predict_lstm(self, df: pd.DataFrame, horizon_days: int) -> List[Tuple[date, float, float, float]]:
        """LSTM model prediction"""
        # Prepare sequences
        sequence_length = 30
        X, y = self._create_sequences(df['access_count'].values, sequence_length)
        
        if len(X) == 0:
            return []
        
        # Scale data
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X.reshape(-1, 1)).reshape(X.shape)
        y_scaled = scaler.transform(y.reshape(-1, 1)).flatten()
        
        # Convert to tensors
        X_tensor = torch.FloatTensor(X_scaled).unsqueeze(-1)
        y_tensor = torch.FloatTensor(y_scaled)
        
        # Create and train model
        model = LSTMPredictor(input_size=1)
        optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
        criterion = nn.MSELoss()
        
        # Training
        model.train()
        for epoch in range(100):
            optimizer.zero_grad()
            outputs = model(X_tensor)
            loss = criterion(outputs.squeeze(), y_tensor)
            loss.backward()
            optimizer.step()
        
        # Make predictions
        model.eval()
        last_sequence = X_scaled[-1].reshape(1, sequence_length, 1)
        predictions = []
        
        last_date = df['date'].max()
        
        for i in range(horizon_days):
            with torch.no_grad():
                input_tensor = torch.FloatTensor(last_sequence)
                pred = model(input_tensor)
                pred_value = scaler.inverse_transform(pred.numpy().reshape(-1, 1))[0, 0]
            
            # Simple confidence intervals (±20% for LSTM)
            lower = pred_value * 0.8
            upper = pred_value * 1.2
            
            predictions.append((
                last_date + timedelta(days=i+1),
                max(0, pred_value),
                max(0, lower),
                max(0, upper)
            ))
            
            # Update sequence
            last_sequence = np.roll(last_sequence, -1, axis=1)
            last_sequence[0, -1, 0] = pred.numpy()[0, 0]
        
        return predictions
    
    async def _predict_xgboost(self, df: pd.DataFrame, horizon_days: int) -> List[Tuple[date, float, float, float]]:
        """XGBoost model prediction"""
        # Feature engineering
        features_df = self.feature_engineer.create_features(df)
        
        # Prepare training data
        X = features_df.drop(['date', 'access_count'], axis=1)
        y = features_df['access_count']
        
        # Train model
        model = xgb.XGBRegressor(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.01,
            random_state=42
        )
        model.fit(X, y)
        
        # Generate future features
        last_date = df['date'].max()
        future_dates = [last_date + timedelta(days=i+1) for i in range(horizon_days)]
        
        predictions = []
        for date_val in future_dates:
            # Create features for prediction date
            future_features = self.feature_engineer.create_future_features(
                date_val,
                df['access_count'].tail(30).mean()  # Use recent average as baseline
            )
            
            pred = model.predict(future_features.reshape(1, -1))[0]
            
            # Simple confidence intervals (±15% for XGBoost)
            lower = pred * 0.85
            upper = pred * 1.15
            
            predictions.append((
                date_val,
                max(0, pred),
                max(0, lower),
                max(0, upper)
            ))
        
        return predictions
    
    def _ensemble_predictions(
        self,
        model_predictions: Dict[str, List[Tuple[date, float, float, float]]]
    ) -> List[Tuple[date, float, float, float]]:
        """Ensemble multiple model predictions"""
        # Group predictions by date
        date_predictions = {}
        
        for model_name, predictions in model_predictions.items():
            for date_val, pred, lower, upper in predictions:
                if date_val not in date_predictions:
                    date_predictions[date_val] = {
                        'predictions': [],
                        'lowers': [],
                        'uppers': []
                    }
                
                date_predictions[date_val]['predictions'].append(pred)
                date_predictions[date_val]['lowers'].append(lower)
                date_predictions[date_val]['uppers'].append(upper)
        
        # Calculate ensemble predictions
        ensemble_results = []
        for date_val in sorted(date_predictions.keys()):
            preds = date_predictions[date_val]['predictions']
            lowers = date_predictions[date_val]['lowers']
            uppers = date_predictions[date_val]['uppers']
            
            # Weighted average (could use more sophisticated methods)
            ensemble_pred = np.mean(preds)
            ensemble_lower = np.mean(lowers)
            ensemble_upper = np.mean(uppers)
            
            ensemble_results.append((
                date_val,
                ensemble_pred,
                ensemble_lower,
                ensemble_upper
            ))
        
        return ensemble_results
    
    def _prepare_dataframe(self, history: List[UsagePattern]) -> pd.DataFrame:
        """Prepare dataframe from usage history"""
        data = []
        for pattern in history:
            data.append({
                'date': pattern.timestamp.date(),
                'access_count': pattern.access_count,
                'unique_users': pattern.unique_users,
                'total_duration': pattern.total_duration_seconds,
                'avg_session_duration': pattern.average_session_duration,
                'peak_hour': pattern.peak_hour,
                'day_of_week': pattern.day_of_week
            })
        
        df = pd.DataFrame(data)
        df = df.groupby('date').agg({
            'access_count': 'sum',
            'unique_users': 'sum',
            'total_duration': 'sum',
            'avg_session_duration': 'mean',
            'peak_hour': 'first',
            'day_of_week': 'first'
        }).reset_index()
        
        return df
    
    def _create_sequences(self, data: np.ndarray, seq_length: int) -> Tuple[np.ndarray, np.ndarray]:
        """Create sequences for LSTM training"""
        X, y = [], []
        for i in range(len(data) - seq_length):
            X.append(data[i:i+seq_length])
            y.append(data[i+seq_length])
        return np.array(X), np.array(y)
    
    def _analyze_trend(self, df: pd.DataFrame) -> Tuple[str, float]:
        """Analyze trend direction and strength"""
        # Simple linear regression for trend
        from scipy import stats
        
        x = np.arange(len(df))
        y = df['access_count'].values
        
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
        
        # Determine direction
        if abs(slope) < 0.01:
            direction = "stable"
        elif slope > 0:
            direction = "increasing"
        else:
            direction = "decreasing"
        
        # Strength is based on R-squared
        strength = abs(r_value)
        
        return direction, strength
    
    def _detect_seasonality(self, df: pd.DataFrame) -> Optional[str]:
        """Detect seasonal patterns"""
        if len(df) < 28:  # Need at least 4 weeks
            return None
        
        # Check weekly pattern
        weekly_pattern = df.groupby(df['day_of_week'])['access_count'].mean()
        weekly_variation = weekly_pattern.std() / weekly_pattern.mean()
        
        if weekly_variation > 0.2:
            return "weekly"
        
        # Check daily pattern (by hour)
        hourly_pattern = df.groupby('peak_hour')['access_count'].mean()
        hourly_variation = hourly_pattern.std() / hourly_pattern.mean()
        
        if hourly_variation > 0.3:
            return "daily"
        
        return None
    
    def _identify_peak_periods(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Identify peak usage periods"""
        peaks = []
        
        # Weekly peaks
        weekly_usage = df.groupby('day_of_week')['access_count'].mean()
        peak_day = weekly_usage.idxmax()
        
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        peaks.append({
            'type': 'weekly',
            'period': days[peak_day],
            'average_usage': float(weekly_usage[peak_day])
        })
        
        # Hourly peaks
        hourly_usage = df.groupby('peak_hour')['access_count'].mean()
        peak_hour = hourly_usage.idxmax()
        
        peaks.append({
            'type': 'daily',
            'period': f"{peak_hour}:00",
            'average_usage': float(hourly_usage[peak_hour])
        })
        
        return peaks
    
    def _calculate_confidence(self, lower: float, upper: float, prediction: float) -> float:
        """Calculate confidence score based on prediction interval"""
        if prediction == 0:
            return 0.0
        
        interval_width = upper - lower
        relative_width = interval_width / prediction
        
        # Narrower intervals = higher confidence
        confidence = max(0, min(1, 1 - (relative_width / 2)))
        
        return confidence
    
    async def _get_usage_history(self, asset_id: str) -> List[UsagePattern]:
        """Get usage history from database"""
        cutoff_date = datetime.utcnow() - timedelta(days=settings.USAGE_PREDICTION_WINDOW_DAYS)
        
        result = await self.db.execute(
            select(UsageHistoryModel)
            .where(
                and_(
                    UsageHistoryModel.asset_id == asset_id,
                    UsageHistoryModel.timestamp >= cutoff_date
                )
            )
            .order_by(UsageHistoryModel.timestamp)
        )
        
        history = result.scalars().all()
        return [UsagePattern.from_orm(h) for h in history]
    
    async def _store_prediction(self, prediction: UsagePrediction):
        """Store prediction in database"""
        db_prediction = PredictionModel(
            prediction_id=prediction.prediction_id,
            prediction_type=PredictionType.USAGE,
            asset_id=prediction.asset_id,
            prediction_date=prediction.prediction_date,
            predicted_value=prediction.predicted_access_count,
            confidence_score=prediction.confidence_score,
            model_used=prediction.model_used,
            metadata={
                'confidence_interval': {
                    'lower': prediction.confidence_interval_lower,
                    'upper': prediction.confidence_interval_upper
                },
                'features_used': prediction.features_used
            }
        )
        
        self.db.add(db_prediction)
        await self.db.commit()
    
    async def _calculate_forecast_accuracy(self, asset_id: str) -> float:
        """Calculate historical forecast accuracy"""
        # Get recent predictions and actual values
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        result = await self.db.execute(
            select(PredictionModel)
            .where(
                and_(
                    PredictionModel.asset_id == asset_id,
                    PredictionModel.prediction_type == PredictionType.USAGE,
                    PredictionModel.created_at >= thirty_days_ago,
                    PredictionModel.prediction_date <= datetime.utcnow().date()
                )
            )
        )
        
        predictions = result.scalars().all()
        
        if not predictions:
            return 0.0
        
        # Calculate accuracy
        errors = []
        for pred in predictions:
            # Get actual value for prediction date
            actual_result = await self.db.execute(
                select(UsageHistoryModel)
                .where(
                    and_(
                        UsageHistoryModel.asset_id == asset_id,
                        UsageHistoryModel.timestamp.cast(date) == pred.prediction_date
                    )
                )
            )
            
            actual = actual_result.scalar()
            if actual:
                error = abs(pred.predicted_value - actual.access_count) / (actual.access_count + 1)
                errors.append(error)
        
        if errors:
            # Mean Absolute Percentage Error
            mape = np.mean(errors)
            accuracy = max(0, 1 - mape)
            return accuracy
        
        return 0.0
    
    async def _load_models(self):
        """Load saved models from disk"""
        # Load XGBoost model if exists
        xgb_path = self.model_path / "xgboost_model.pkl"
        if xgb_path.exists():
            self.models['xgboost'] = joblib.load(xgb_path)
        
        # Load LSTM model if exists
        lstm_path = self.model_path / "lstm_model.pth"
        if lstm_path.exists():
            model = LSTMPredictor(input_size=1)
            model.load_state_dict(torch.load(lstm_path))
            self.models['lstm'] = model
        
        # Load scalers
        scaler_path = self.model_path / "scalers.pkl"
        if scaler_path.exists():
            self.scalers = joblib.load(scaler_path)
    
    async def _save_models(self):
        """Save trained models to disk"""
        # Save XGBoost
        if 'xgboost' in self.models:
            joblib.dump(self.models['xgboost'], self.model_path / "xgboost_model.pkl")
        
        # Save LSTM
        if 'lstm' in self.models:
            torch.save(self.models['lstm'].state_dict(), self.model_path / "lstm_model.pth")
        
        # Save scalers
        if self.scalers:
            joblib.dump(self.scalers, self.model_path / "scalers.pkl")
    
    async def _periodic_model_update(self):
        """Periodically retrain models"""
        while True:
            try:
                await asyncio.sleep(settings.MODEL_UPDATE_INTERVAL_HOURS * 3600)
                
                logger.info("Starting periodic model update")
                
                # Retrain models with recent data
                # This is a simplified version - in production, you'd want more sophisticated training
                
                # Update metrics
                ai_metrics.model_updates.labels(
                    model_type="usage_prediction"
                ).inc()
                
            except Exception as e:
                logger.error("Error in periodic model update", error=str(e))