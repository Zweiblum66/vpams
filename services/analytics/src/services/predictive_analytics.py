"""
Predictive Analytics Service

This service provides machine learning-powered predictive analytics including
user behavior prediction, churn analysis, content recommendations, and trend forecasting.
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import asyncio
import joblib
import json

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
import redis.asyncio as redis

# Machine Learning imports
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LogisticRegression, LinearRegression
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, mean_squared_error, classification_report
from sklearn.decomposition import PCA
import xgboost as xgb

from ..models.analytics import (
    Event, UserSession, UserBehavior, AssetInteraction, SearchQuery
)
from ..core.config import settings
from shared.tracing.python_tracing import trace_async_function
from shared.logging.python_logging import get_logger

logger = get_logger(__name__)


class PredictionType(str, Enum):
    """Types of predictions available."""
    USER_CHURN = "user_churn"
    CONTENT_POPULARITY = "content_popularity"
    USER_ENGAGEMENT = "user_engagement"
    USAGE_FORECASTING = "usage_forecasting"
    ANOMALY_DETECTION = "anomaly_detection"
    RECOMMENDATION = "recommendation"
    TREND_ANALYSIS = "trend_analysis"


class ModelType(str, Enum):
    """Machine learning model types."""
    RANDOM_FOREST = "random_forest"
    LOGISTIC_REGRESSION = "logistic_regression"
    XGBOOST = "xgboost"
    LINEAR_REGRESSION = "linear_regression"
    NEURAL_NETWORK = "neural_network"
    CLUSTERING = "clustering"


@dataclass
class PredictionResult:
    """Result of a prediction."""
    prediction_type: PredictionType
    prediction_id: str
    model_version: str
    predictions: List[Dict[str, Any]]
    confidence_scores: List[float]
    feature_importance: Dict[str, float]
    model_metrics: Dict[str, float]
    generated_at: datetime
    expires_at: datetime


@dataclass
class ModelPerformance:
    """Model performance metrics."""
    model_type: ModelType
    prediction_type: PredictionType
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    rmse: Optional[float] = None
    mae: Optional[float] = None
    r2_score: Optional[float] = None
    feature_importance: Dict[str, float] = None
    training_date: datetime = None
    validation_metrics: Dict[str, float] = None


class PredictiveAnalytics:
    """Service for predictive analytics and machine learning."""
    
    def __init__(self):
        self.redis_client = None
        self.models = {}
        self.scalers = {}
        self.encoders = {}
        self.model_cache = {}
        
    async def _get_redis(self) -> redis.Redis:
        """Get Redis connection."""
        if not self.redis_client:
            self.redis_client = redis.from_url(settings.REDIS_URL)
        return self.redis_client
    
    @trace_async_function(operation_name="predictive.train_churn_model")
    async def train_churn_prediction_model(self, db: AsyncSession) -> ModelPerformance:
        """Train a model to predict user churn."""
        try:
            # Collect training data
            training_data = await self._collect_churn_training_data(db)
            
            if len(training_data) < 100:
                raise ValueError("Insufficient data for churn model training (need at least 100 samples)")
            
            # Prepare features and labels
            X, y, feature_names = await self._prepare_churn_features(training_data)
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y
            )
            
            # Scale features
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            # Train Random Forest model
            model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=42,
                class_weight='balanced'
            )
            model.fit(X_train_scaled, y_train)
            
            # Evaluate model
            y_pred = model.predict(X_test_scaled)
            accuracy = accuracy_score(y_test, y_pred)
            
            from sklearn.metrics import precision_score, recall_score, f1_score
            precision = precision_score(y_test, y_pred, average='weighted')
            recall = recall_score(y_test, y_pred, average='weighted')
            f1 = f1_score(y_test, y_pred, average='weighted')
            
            # Feature importance
            feature_importance = dict(zip(feature_names, model.feature_importances_))
            
            # Save model and scaler
            self.models['churn_prediction'] = model
            self.scalers['churn_prediction'] = scaler
            
            # Cache model in Redis
            redis_client = await self._get_redis()
            model_data = {
                'model': joblib.dumps(model),
                'scaler': joblib.dumps(scaler),
                'feature_names': feature_names,
                'trained_at': datetime.utcnow().isoformat()
            }
            await redis_client.setex(
                'model:churn_prediction',
                86400 * 7,  # 7 days
                json.dumps(model_data, default=str)
            )
            
            performance = ModelPerformance(
                model_type=ModelType.RANDOM_FOREST,
                prediction_type=PredictionType.USER_CHURN,
                accuracy=accuracy,
                precision=precision,
                recall=recall,
                f1_score=f1,
                feature_importance=feature_importance,
                training_date=datetime.utcnow(),
                validation_metrics={
                    'train_accuracy': model.score(X_train_scaled, y_train),
                    'test_accuracy': accuracy,
                    'sample_count': len(training_data)
                }
            )
            
            logger.info(f"Churn prediction model trained with accuracy: {accuracy:.3f}")
            return performance
            
        except Exception as e:
            logger.error(f"Failed to train churn model: {e}", exc_info=True)
            raise
    
    async def _collect_churn_training_data(self, db: AsyncSession) -> List[Dict[str, Any]]:
        """Collect data for churn model training."""
        # Get user behavior data from last 90 days
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=90)
        
        query = select(UserBehavior).where(
            and_(
                UserBehavior.period_start >= start_date,
                UserBehavior.period_end <= end_date
            )
        )
        result = await db.execute(query)
        behaviors = result.scalars().all()
        
        training_data = []
        for behavior in behaviors:
            # Determine churn label (user inactive for 14+ days)
            last_activity = behavior.period_end
            days_since_activity = (datetime.utcnow() - last_activity).days
            is_churned = 1 if days_since_activity > 14 else 0
            
            training_data.append({
                'user_id': str(behavior.user_id),
                'sessions_count': behavior.sessions_count,
                'total_time_minutes': behavior.total_time_minutes,
                'page_views': behavior.page_views,
                'actions_count': behavior.actions_count,
                'assets_viewed': behavior.assets_viewed,
                'assets_uploaded': behavior.assets_uploaded,
                'searches_performed': behavior.searches_performed,
                'avg_session_duration': behavior.avg_session_duration or 0,
                'bounce_rate': behavior.bounce_rate or 0,
                'workflows_executed': behavior.workflows_executed or 0,
                'days_since_activity': days_since_activity,
                'is_churned': is_churned
            })
        
        return training_data
    
    async def _prepare_churn_features(self, training_data: List[Dict[str, Any]]) -> Tuple[np.ndarray, np.ndarray, List[str]]:
        """Prepare features for churn prediction."""
        df = pd.DataFrame(training_data)
        
        feature_columns = [
            'sessions_count', 'total_time_minutes', 'page_views', 'actions_count',
            'assets_viewed', 'assets_uploaded', 'searches_performed',
            'avg_session_duration', 'bounce_rate', 'workflows_executed',
            'days_since_activity'
        ]
        
        # Create additional features
        df['engagement_score'] = (
            df['sessions_count'] * 0.3 +
            df['actions_count'] * 0.4 +
            df['assets_uploaded'] * 0.3
        )
        
        df['activity_ratio'] = df['actions_count'] / (df['sessions_count'] + 1)
        df['content_interaction_ratio'] = df['assets_viewed'] / (df['page_views'] + 1)
        
        feature_columns.extend(['engagement_score', 'activity_ratio', 'content_interaction_ratio'])
        
        X = df[feature_columns].fillna(0).values
        y = df['is_churned'].values
        
        return X, y, feature_columns
    
    @trace_async_function(operation_name="predictive.predict_user_churn")
    async def predict_user_churn(
        self,
        user_ids: List[str],
        db: AsyncSession
    ) -> List[Dict[str, Any]]:
        """Predict churn probability for users."""
        try:
            # Load model
            model, scaler = await self._load_model('churn_prediction')
            
            if not model:
                raise ValueError("Churn prediction model not found. Train model first.")
            
            # Get user features
            user_features = await self._get_user_features_for_churn(user_ids, db)
            
            if not user_features:
                return []
            
            # Prepare features
            feature_matrix = []
            valid_users = []
            
            for user_id, features in user_features.items():
                if features:  # Ensure user has feature data
                    feature_vector = [
                        features.get('sessions_count', 0),
                        features.get('total_time_minutes', 0),
                        features.get('page_views', 0),
                        features.get('actions_count', 0),
                        features.get('assets_viewed', 0),
                        features.get('assets_uploaded', 0),
                        features.get('searches_performed', 0),
                        features.get('avg_session_duration', 0),
                        features.get('bounce_rate', 0),
                        features.get('workflows_executed', 0),
                        features.get('days_since_activity', 0),
                        features.get('engagement_score', 0),
                        features.get('activity_ratio', 0),
                        features.get('content_interaction_ratio', 0)
                    ]
                    feature_matrix.append(feature_vector)
                    valid_users.append(user_id)
            
            if not feature_matrix:
                return []
            
            # Scale features and predict
            X_scaled = scaler.transform(feature_matrix)
            churn_probabilities = model.predict_proba(X_scaled)[:, 1]  # Probability of churn
            churn_predictions = model.predict(X_scaled)
            
            # Prepare results
            predictions = []
            for i, user_id in enumerate(valid_users):
                predictions.append({
                    'user_id': user_id,
                    'churn_probability': float(churn_probabilities[i]),
                    'churn_prediction': bool(churn_predictions[i]),
                    'risk_level': self._get_churn_risk_level(churn_probabilities[i]),
                    'days_to_churn_estimate': self._estimate_days_to_churn(churn_probabilities[i]),
                    'recommended_actions': self._get_churn_prevention_recommendations(
                        churn_probabilities[i], user_features[user_id]
                    )
                })
            
            return predictions
            
        except Exception as e:
            logger.error(f"Failed to predict user churn: {e}", exc_info=True)
            raise
    
    async def _get_user_features_for_churn(
        self,
        user_ids: List[str],
        db: AsyncSession
    ) -> Dict[str, Dict[str, Any]]:
        """Get user features for churn prediction."""
        # Get recent user behavior data
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=30)
        
        query = select(UserBehavior).where(
            and_(
                UserBehavior.user_id.in_(user_ids),
                UserBehavior.period_start >= start_date
            )
        )
        result = await db.execute(query)
        behaviors = result.scalars().all()
        
        user_features = {}
        for behavior in behaviors:
            user_id = str(behavior.user_id)
            
            # Calculate additional features
            engagement_score = (
                behavior.sessions_count * 0.3 +
                behavior.actions_count * 0.4 +
                (behavior.assets_uploaded or 0) * 0.3
            )
            
            activity_ratio = behavior.actions_count / (behavior.sessions_count + 1)
            content_interaction_ratio = behavior.assets_viewed / (behavior.page_views + 1)
            days_since_activity = (datetime.utcnow() - behavior.period_end).days
            
            user_features[user_id] = {
                'sessions_count': behavior.sessions_count,
                'total_time_minutes': behavior.total_time_minutes,
                'page_views': behavior.page_views,
                'actions_count': behavior.actions_count,
                'assets_viewed': behavior.assets_viewed,
                'assets_uploaded': behavior.assets_uploaded or 0,
                'searches_performed': behavior.searches_performed,
                'avg_session_duration': behavior.avg_session_duration or 0,
                'bounce_rate': behavior.bounce_rate or 0,
                'workflows_executed': behavior.workflows_executed or 0,
                'days_since_activity': days_since_activity,
                'engagement_score': engagement_score,
                'activity_ratio': activity_ratio,
                'content_interaction_ratio': content_interaction_ratio
            }
        
        return user_features
    
    def _get_churn_risk_level(self, churn_probability: float) -> str:
        """Get risk level based on churn probability."""
        if churn_probability >= 0.8:
            return "very_high"
        elif churn_probability >= 0.6:
            return "high"
        elif churn_probability >= 0.4:
            return "medium"
        elif churn_probability >= 0.2:
            return "low"
        else:
            return "very_low"
    
    def _estimate_days_to_churn(self, churn_probability: float) -> int:
        """Estimate days until churn based on probability."""
        # Simple heuristic: higher probability = fewer days
        if churn_probability >= 0.9:
            return 3
        elif churn_probability >= 0.8:
            return 7
        elif churn_probability >= 0.6:
            return 14
        elif churn_probability >= 0.4:
            return 30
        else:
            return 60
    
    def _get_churn_prevention_recommendations(
        self,
        churn_probability: float,
        user_features: Dict[str, Any]
    ) -> List[str]:
        """Get recommendations to prevent user churn."""
        recommendations = []
        
        if churn_probability >= 0.6:
            recommendations.append("Send personalized re-engagement email")
            recommendations.append("Offer premium features trial")
            
        if user_features.get('sessions_count', 0) < 5:
            recommendations.append("Provide onboarding assistance")
            recommendations.append("Send feature tutorial emails")
            
        if user_features.get('assets_uploaded', 0) == 0:
            recommendations.append("Encourage first upload with incentives")
            recommendations.append("Provide upload tutorial")
            
        if user_features.get('avg_session_duration', 0) < 5:
            recommendations.append("Improve user experience")
            recommendations.append("Provide quick start guide")
            
        if user_features.get('searches_performed', 0) > 20 and user_features.get('assets_viewed', 0) < 10:
            recommendations.append("Improve search result relevance")
            recommendations.append("Provide search tips and filters")
        
        return recommendations[:3]  # Return top 3 recommendations
    
    @trace_async_function(operation_name="predictive.predict_content_popularity")
    async def predict_content_popularity(
        self,
        content_features: List[Dict[str, Any]],
        prediction_horizon_days: int = 7
    ) -> List[Dict[str, Any]]:
        """Predict content popularity based on features."""
        try:
            # For now, use a simple heuristic-based approach
            # In production, this would use a trained ML model
            
            predictions = []
            for content in content_features:
                # Calculate popularity score based on various factors
                base_score = 0.5
                
                # Content type factor
                content_type = content.get('type', 'unknown')
                if content_type == 'video':
                    base_score += 0.2
                elif content_type == 'image':
                    base_score += 0.1
                
                # Size factor (moderate size preferred)
                file_size = content.get('size_mb', 0)
                if 10 <= file_size <= 100:
                    base_score += 0.1
                elif file_size > 500:
                    base_score -= 0.1
                
                # Metadata completeness factor
                metadata_score = len(content.get('metadata', {})) / 10.0
                base_score += min(metadata_score * 0.2, 0.2)
                
                # Upload time factor (recent uploads get boost)
                upload_time = content.get('uploaded_at')
                if upload_time:
                    days_old = (datetime.utcnow() - upload_time).days
                    if days_old <= 1:
                        base_score += 0.15
                    elif days_old <= 7:
                        base_score += 0.1
                
                # Creator factor (based on historical performance)
                creator_id = content.get('creator_id')
                creator_boost = content.get('creator_avg_views', 0) / 1000.0
                base_score += min(creator_boost * 0.1, 0.15)
                
                # Normalize score
                popularity_score = min(max(base_score, 0.0), 1.0)
                
                # Predict view counts
                predicted_views = int(popularity_score * 1000 * prediction_horizon_days / 7)
                predicted_interactions = int(popularity_score * 100 * prediction_horizon_days / 7)
                
                predictions.append({
                    'content_id': content.get('id'),
                    'popularity_score': popularity_score,
                    'predicted_views': predicted_views,
                    'predicted_interactions': predicted_interactions,
                    'confidence': 0.7,  # Placeholder confidence
                    'factors': {
                        'content_type_boost': content_type == 'video',
                        'optimal_size': 10 <= file_size <= 100,
                        'metadata_complete': len(content.get('metadata', {})) >= 5,
                        'recently_uploaded': (datetime.utcnow() - upload_time).days <= 7 if upload_time else False
                    }
                })
            
            return predictions
            
        except Exception as e:
            logger.error(f"Failed to predict content popularity: {e}", exc_info=True)
            raise
    
    @trace_async_function(operation_name="predictive.forecast_usage")
    async def forecast_usage(
        self,
        metric_name: str,
        forecast_days: int,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Forecast usage metrics using time series analysis."""
        try:
            # Get historical data
            historical_data = await self._get_historical_metric_data(metric_name, db)
            
            if len(historical_data) < 14:
                raise ValueError(f"Insufficient historical data for forecasting (need at least 14 days)")
            
            # Prepare time series data
            df = pd.DataFrame(historical_data)
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
            
            # Simple linear trend forecast (in production, use ARIMA or Prophet)
            X = np.arange(len(df)).reshape(-1, 1)
            y = df['value'].values
            
            # Fit linear regression
            model = LinearRegression()
            model.fit(X, y)
            
            # Generate forecasts
            future_X = np.arange(len(df), len(df) + forecast_days).reshape(-1, 1)
            forecasts = model.predict(future_X)
            
            # Calculate confidence intervals (simple approach)
            residuals = y - model.predict(X)
            std_error = np.std(residuals)
            
            forecast_dates = []
            forecast_data = []
            
            last_date = df['date'].iloc[-1]
            for i in range(forecast_days):
                forecast_date = last_date + timedelta(days=i+1)
                forecast_value = max(0, forecasts[i])  # Ensure non-negative
                
                forecast_dates.append(forecast_date)
                forecast_data.append({
                    'date': forecast_date.isoformat(),
                    'predicted_value': float(forecast_value),
                    'lower_bound': max(0, float(forecast_value - 1.96 * std_error)),
                    'upper_bound': float(forecast_value + 1.96 * std_error),
                    'confidence': 0.8
                })
            
            # Calculate trend
            trend_slope = model.coef_[0]
            trend_direction = "increasing" if trend_slope > 0 else "decreasing" if trend_slope < 0 else "stable"
            
            return {
                'metric_name': metric_name,
                'forecast_period_days': forecast_days,
                'forecasts': forecast_data,
                'trend': {
                    'direction': trend_direction,
                    'slope': float(trend_slope),
                    'r2_score': float(model.score(X, y))
                },
                'model_metrics': {
                    'mae': float(np.mean(np.abs(residuals))),
                    'rmse': float(np.sqrt(np.mean(residuals**2))),
                    'mape': float(np.mean(np.abs(residuals / y)) * 100)
                },
                'generated_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to forecast usage: {e}", exc_info=True)
            raise
    
    async def _get_historical_metric_data(
        self,
        metric_name: str,
        db: AsyncSession,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """Get historical metric data for forecasting."""
        # This is a placeholder implementation
        # In production, this would query actual metrics data
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Generate sample historical data
        historical_data = []
        base_value = 1000
        
        for i in range(days):
            date = start_date + timedelta(days=i)
            # Add some trend and noise
            trend = i * 5
            noise = np.random.normal(0, 50)
            value = max(0, base_value + trend + noise)
            
            historical_data.append({
                'date': date.strftime('%Y-%m-%d'),
                'value': value
            })
        
        return historical_data
    
    @trace_async_function(operation_name="predictive.detect_anomalies")
    async def detect_anomalies(
        self,
        metric_name: str,
        data_points: List[Dict[str, Any]],
        sensitivity: float = 2.0
    ) -> List[Dict[str, Any]]:
        """Detect anomalies in metric data."""
        try:
            if len(data_points) < 10:
                return []
            
            # Extract values
            values = [point['value'] for point in data_points]
            timestamps = [point['timestamp'] for point in data_points]
            
            # Calculate rolling statistics
            df = pd.DataFrame({'value': values, 'timestamp': timestamps})
            df['rolling_mean'] = df['value'].rolling(window=7, min_periods=1).mean()
            df['rolling_std'] = df['value'].rolling(window=7, min_periods=1).std()
            
            # Detect anomalies using Z-score
            anomalies = []
            for i, (_, row) in enumerate(df.iterrows()):
                if row['rolling_std'] > 0:
                    z_score = abs((row['value'] - row['rolling_mean']) / row['rolling_std'])
                    
                    if z_score > sensitivity:
                        anomaly_type = "spike" if row['value'] > row['rolling_mean'] else "drop"
                        severity = "high" if z_score > 3 else "medium" if z_score > 2.5 else "low"
                        
                        anomalies.append({
                            'timestamp': timestamps[i],
                            'value': values[i],
                            'expected_value': float(row['rolling_mean']),
                            'z_score': float(z_score),
                            'anomaly_type': anomaly_type,
                            'severity': severity,
                            'deviation_percent': float(abs(row['value'] - row['rolling_mean']) / row['rolling_mean'] * 100)
                        })
            
            return anomalies
            
        except Exception as e:
            logger.error(f"Failed to detect anomalies: {e}", exc_info=True)
            return []
    
    async def _load_model(self, model_name: str) -> Tuple[Any, Any]:
        """Load model and scaler from cache or Redis."""
        try:
            # Check in-memory cache first
            if model_name in self.models:
                return self.models[model_name], self.scalers.get(model_name)
            
            # Load from Redis
            redis_client = await self._get_redis()
            model_data = await redis_client.get(f'model:{model_name}')
            
            if model_data:
                data = json.loads(model_data)
                model = joblib.loads(data['model'])
                scaler = joblib.loads(data['scaler']) if 'scaler' in data else None
                
                # Cache in memory
                self.models[model_name] = model
                if scaler:
                    self.scalers[model_name] = scaler
                
                return model, scaler
            
            return None, None
            
        except Exception as e:
            logger.error(f"Failed to load model {model_name}: {e}")
            return None, None
    
    async def get_model_performance(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Get performance metrics for a model."""
        try:
            redis_client = await self._get_redis()
            performance_data = await redis_client.get(f'model_performance:{model_name}')
            
            if performance_data:
                return json.loads(performance_data)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get model performance: {e}")
            return None
    
    async def save_model_performance(self, model_name: str, performance: ModelPerformance):
        """Save model performance metrics."""
        try:
            redis_client = await self._get_redis()
            performance_data = {
                'model_type': performance.model_type,
                'prediction_type': performance.prediction_type,
                'accuracy': performance.accuracy,
                'precision': performance.precision,
                'recall': performance.recall,
                'f1_score': performance.f1_score,
                'rmse': performance.rmse,
                'mae': performance.mae,
                'r2_score': performance.r2_score,
                'feature_importance': performance.feature_importance,
                'training_date': performance.training_date.isoformat() if performance.training_date else None,
                'validation_metrics': performance.validation_metrics
            }
            
            await redis_client.setex(
                f'model_performance:{model_name}',
                86400 * 30,  # 30 days
                json.dumps(performance_data, default=str)
            )
            
        except Exception as e:
            logger.error(f"Failed to save model performance: {e}")
    
    async def close(self):
        """Clean up resources."""
        if self.redis_client:
            await self.redis_client.close()