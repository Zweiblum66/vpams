"""
Predictive Maintenance Service

Predicts system failures and maintenance needs using ML models.
"""

import asyncio
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta, date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, or_
import structlog
import numpy as np
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.preprocessing import StandardScaler
import pandas as pd

from ..core.config import settings
from ..models.schemas import (
    MaintenancePrediction, MaintenanceAlert, SystemComponent,
    RiskLevel, AlertSeverity, ModelType
)
from ..db.models import (
    MaintenancePredictionModel, SystemMetricsModel,
    ComponentHealthModel, MaintenanceHistoryModel
)
from ..utils.metrics import ai_metrics


logger = structlog.get_logger()


class MaintenancePredictor:
    """Predicts maintenance needs and system failures"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.failure_model = RandomForestClassifier(n_estimators=100, random_state=42)
        self.anomaly_detector = IsolationForest(contamination=0.1, random_state=42)
        self.scaler = StandardScaler()
        self.model_trained = False
    
    async def initialize(self):
        """Initialize maintenance predictor"""
        logger.info("Initializing maintenance predictor")
        
        # Load or train models
        await self._load_models()
        
        # Schedule periodic predictions
        asyncio.create_task(self._periodic_prediction())
        
        # Schedule model retraining
        asyncio.create_task(self._periodic_model_update())
    
    async def predict_maintenance(
        self,
        component_type: Optional[str] = None,
        days_ahead: int = 30
    ) -> List[MaintenancePrediction]:
        """Predict maintenance needs for components"""
        logger.info(
            "Predicting maintenance needs",
            component_type=component_type,
            days_ahead=days_ahead
        )
        
        predictions = []
        
        # Get components to analyze
        components = await self._get_components(component_type)
        
        for component in components:
            # Get component metrics
            metrics = await self._get_component_metrics(component.component_id)
            
            if not metrics:
                continue
            
            # Extract features
            features = self._extract_features(metrics)
            
            if len(features) == 0:
                continue
            
            # Make prediction
            if self.model_trained:
                failure_prob = self._predict_failure_probability(features)
                anomaly_score = self._detect_anomalies(features)
            else:
                # Fallback to rule-based prediction
                failure_prob = self._rule_based_prediction(metrics)
                anomaly_score = 0.0
            
            # Determine risk level
            risk_level = self._determine_risk_level(failure_prob, anomaly_score)
            
            # Calculate predicted failure date
            if failure_prob > 0.7:
                days_to_failure = int((1 - failure_prob) * days_ahead)
                predicted_failure = date.today() + timedelta(days=days_to_failure)
            else:
                predicted_failure = None
            
            # Get last maintenance date
            last_maintenance = await self._get_last_maintenance(component.component_id)
            
            # Create prediction
            prediction = MaintenancePrediction(
                component_id=component.component_id,
                component_type=component.component_type,
                component_name=component.component_name,
                risk_level=risk_level,
                failure_probability=failure_prob,
                predicted_failure_date=predicted_failure,
                last_maintenance_date=last_maintenance,
                recommended_actions=self._get_recommended_actions(risk_level, component.component_type),
                confidence_score=0.8 if self.model_trained else 0.6,
                contributing_factors=self._get_contributing_factors(metrics, features)
            )
            
            predictions.append(prediction)
            
            # Store prediction
            await self._store_prediction(prediction)
        
        # Sort by risk level
        predictions.sort(key=lambda p: (p.risk_level.value, p.failure_probability), reverse=True)
        
        # Update metrics
        ai_metrics.maintenance_predictions.inc(len(predictions))
        
        return predictions
    
    async def get_maintenance_alerts(
        self,
        severity: Optional[AlertSeverity] = None,
        component_type: Optional[str] = None
    ) -> List[MaintenanceAlert]:
        """Get active maintenance alerts"""
        alerts = []
        
        # Get recent predictions with high risk
        query = select(MaintenancePredictionModel).where(
            and_(
                MaintenancePredictionModel.risk_level.in_([RiskLevel.HIGH, RiskLevel.CRITICAL]),
                MaintenancePredictionModel.created_at >= datetime.utcnow() - timedelta(days=7)
            )
        )
        
        if component_type:
            query = query.where(MaintenancePredictionModel.component_type == component_type)
        
        result = await self.db.execute(query)
        predictions = result.scalars().all()
        
        for pred in predictions:
            # Determine alert severity
            if pred.risk_level == RiskLevel.CRITICAL:
                alert_severity = AlertSeverity.CRITICAL
            elif pred.failure_probability > 0.8:
                alert_severity = AlertSeverity.HIGH
            else:
                alert_severity = AlertSeverity.MEDIUM
            
            if severity and alert_severity != severity:
                continue
            
            # Create alert
            alert = MaintenanceAlert(
                alert_id=f"alert_{pred.prediction_id}",
                component_id=pred.component_id,
                component_type=pred.component_type,
                component_name=pred.component_name,
                severity=alert_severity,
                title=f"{alert_severity.value} risk of failure: {pred.component_name}",
                description=self._generate_alert_description(pred),
                recommended_actions=pred.recommended_actions,
                created_at=pred.created_at,
                expires_at=pred.created_at + timedelta(days=7),
                acknowledged=False
            )
            
            alerts.append(alert)
        
        return alerts
    
    async def analyze_component_health(
        self,
        component_id: str
    ) -> Dict[str, any]:
        """Analyze detailed health of a component"""
        # Get recent metrics
        metrics = await self._get_component_metrics(component_id, days=30)
        
        if not metrics:
            return {
                "status": "unknown",
                "message": "No metrics available"
            }
        
        # Calculate health indicators
        health_indicators = {
            "cpu_usage": self._analyze_metric_trend([m.cpu_usage for m in metrics if m.cpu_usage]),
            "memory_usage": self._analyze_metric_trend([m.memory_usage for m in metrics if m.memory_usage]),
            "disk_usage": self._analyze_metric_trend([m.disk_usage for m in metrics if m.disk_usage]),
            "error_rate": self._analyze_metric_trend([m.error_rate for m in metrics if m.error_rate]),
            "response_time": self._analyze_metric_trend([m.response_time for m in metrics if m.response_time])
        }
        
        # Overall health score
        health_score = self._calculate_health_score(health_indicators)
        
        # Trend analysis
        trends = {
            "improving": sum(1 for v in health_indicators.values() if v.get("trend") == "improving"),
            "stable": sum(1 for v in health_indicators.values() if v.get("trend") == "stable"),
            "degrading": sum(1 for v in health_indicators.values() if v.get("trend") == "degrading")
        }
        
        return {
            "component_id": component_id,
            "health_score": health_score,
            "status": self._get_health_status(health_score),
            "indicators": health_indicators,
            "trends": trends,
            "recommendations": self._get_health_recommendations(health_indicators)
        }
    
    async def _get_components(self, component_type: Optional[str] = None) -> List[SystemComponent]:
        """Get system components to analyze"""
        query = select(ComponentHealthModel)
        
        if component_type:
            query = query.where(ComponentHealthModel.component_type == component_type)
        
        result = await self.db.execute(query)
        components = result.scalars().all()
        
        return [
            SystemComponent(
                component_id=c.component_id,
                component_type=c.component_type,
                component_name=c.component_name
            )
            for c in components
        ]
    
    async def _get_component_metrics(
        self,
        component_id: str,
        days: int = 7
    ) -> List[SystemMetricsModel]:
        """Get recent metrics for a component"""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        result = await self.db.execute(
            select(SystemMetricsModel)
            .where(
                and_(
                    SystemMetricsModel.component_id == component_id,
                    SystemMetricsModel.timestamp >= cutoff
                )
            )
            .order_by(SystemMetricsModel.timestamp)
        )
        
        return result.scalars().all()
    
    def _extract_features(self, metrics: List[SystemMetricsModel]) -> np.ndarray:
        """Extract features from metrics for ML model"""
        if not metrics:
            return np.array([])
        
        features = []
        
        # Statistical features for each metric
        for metric_name in ['cpu_usage', 'memory_usage', 'disk_usage', 'error_rate', 'response_time']:
            values = [getattr(m, metric_name) for m in metrics if getattr(m, metric_name) is not None]
            
            if values:
                features.extend([
                    np.mean(values),
                    np.std(values),
                    np.max(values),
                    np.min(values),
                    np.percentile(values, 95),
                    len([v for v in values if v > np.percentile(values, 95)])  # Outliers
                ])
            else:
                features.extend([0] * 6)
        
        # Time-based features
        if len(metrics) > 1:
            time_diffs = [
                (metrics[i].timestamp - metrics[i-1].timestamp).total_seconds()
                for i in range(1, len(metrics))
            ]
            features.extend([
                np.mean(time_diffs),
                np.std(time_diffs)
            ])
        else:
            features.extend([0, 0])
        
        return np.array(features).reshape(1, -1)
    
    def _predict_failure_probability(self, features: np.ndarray) -> float:
        """Predict probability of failure using ML model"""
        try:
            # Scale features
            features_scaled = self.scaler.transform(features)
            
            # Get probability
            proba = self.failure_model.predict_proba(features_scaled)[0]
            
            # Return probability of failure (class 1)
            return float(proba[1]) if len(proba) > 1 else 0.0
            
        except Exception as e:
            logger.error("Error in failure prediction", error=str(e))
            return 0.0
    
    def _detect_anomalies(self, features: np.ndarray) -> float:
        """Detect anomalies using isolation forest"""
        try:
            # Scale features
            features_scaled = self.scaler.transform(features)
            
            # Get anomaly score
            score = self.anomaly_detector.decision_function(features_scaled)[0]
            
            # Convert to probability (0-1 range)
            return float(1 / (1 + np.exp(score)))
            
        except Exception as e:
            logger.error("Error in anomaly detection", error=str(e))
            return 0.0
    
    def _rule_based_prediction(self, metrics: List[SystemMetricsModel]) -> float:
        """Fallback rule-based prediction"""
        if not metrics:
            return 0.0
        
        risk_score = 0.0
        
        # Check recent metrics
        recent_metrics = metrics[-10:] if len(metrics) > 10 else metrics
        
        for metric in recent_metrics:
            # CPU usage rules
            if metric.cpu_usage and metric.cpu_usage > 90:
                risk_score += 0.2
            elif metric.cpu_usage and metric.cpu_usage > 80:
                risk_score += 0.1
            
            # Memory usage rules
            if metric.memory_usage and metric.memory_usage > 90:
                risk_score += 0.2
            elif metric.memory_usage and metric.memory_usage > 80:
                risk_score += 0.1
            
            # Error rate rules
            if metric.error_rate and metric.error_rate > 0.05:
                risk_score += 0.3
            elif metric.error_rate and metric.error_rate > 0.01:
                risk_score += 0.1
            
            # Response time rules
            if metric.response_time and metric.response_time > 5000:
                risk_score += 0.2
            elif metric.response_time and metric.response_time > 2000:
                risk_score += 0.1
        
        # Average over metrics
        return min(risk_score / len(recent_metrics), 1.0)
    
    def _determine_risk_level(self, failure_prob: float, anomaly_score: float) -> RiskLevel:
        """Determine risk level based on predictions"""
        combined_score = (failure_prob * 0.7 + anomaly_score * 0.3)
        
        if combined_score > 0.8:
            return RiskLevel.CRITICAL
        elif combined_score > 0.6:
            return RiskLevel.HIGH
        elif combined_score > 0.4:
            return RiskLevel.MEDIUM
        elif combined_score > 0.2:
            return RiskLevel.LOW
        else:
            return RiskLevel.NONE
    
    async def _get_last_maintenance(self, component_id: str) -> Optional[date]:
        """Get last maintenance date for component"""
        result = await self.db.execute(
            select(MaintenanceHistoryModel)
            .where(MaintenanceHistoryModel.component_id == component_id)
            .order_by(MaintenanceHistoryModel.maintenance_date.desc())
            .limit(1)
        )
        
        history = result.scalar_one_or_none()
        return history.maintenance_date if history else None
    
    def _get_recommended_actions(self, risk_level: RiskLevel, component_type: str) -> List[str]:
        """Get recommended actions based on risk level"""
        actions = []
        
        if risk_level == RiskLevel.CRITICAL:
            actions.extend([
                "Immediate inspection required",
                "Prepare for emergency maintenance",
                "Backup critical data",
                "Notify on-call team"
            ])
        elif risk_level == RiskLevel.HIGH:
            actions.extend([
                "Schedule maintenance within 48 hours",
                "Monitor component closely",
                "Prepare replacement parts",
                "Review backup procedures"
            ])
        elif risk_level == RiskLevel.MEDIUM:
            actions.extend([
                "Schedule maintenance within 1 week",
                "Increase monitoring frequency",
                "Order replacement parts if needed"
            ])
        elif risk_level == RiskLevel.LOW:
            actions.extend([
                "Include in next scheduled maintenance",
                "Continue regular monitoring"
            ])
        
        # Component-specific actions
        if component_type == "storage":
            if risk_level >= RiskLevel.HIGH:
                actions.append("Check disk health and SMART status")
        elif component_type == "compute":
            if risk_level >= RiskLevel.HIGH:
                actions.append("Check CPU temperature and cooling")
        elif component_type == "network":
            if risk_level >= RiskLevel.HIGH:
                actions.append("Check network interface errors and packet loss")
        
        return actions
    
    def _get_contributing_factors(
        self,
        metrics: List[SystemMetricsModel],
        features: np.ndarray
    ) -> List[str]:
        """Identify factors contributing to prediction"""
        factors = []
        
        if not metrics:
            return factors
        
        # Analyze recent metrics
        recent = metrics[-10:] if len(metrics) > 10 else metrics
        
        # CPU issues
        cpu_values = [m.cpu_usage for m in recent if m.cpu_usage]
        if cpu_values and np.mean(cpu_values) > 80:
            factors.append(f"High CPU usage (avg: {np.mean(cpu_values):.1f}%)")
        
        # Memory issues
        mem_values = [m.memory_usage for m in recent if m.memory_usage]
        if mem_values and np.mean(mem_values) > 80:
            factors.append(f"High memory usage (avg: {np.mean(mem_values):.1f}%)")
        
        # Error rate issues
        error_values = [m.error_rate for m in recent if m.error_rate]
        if error_values and np.mean(error_values) > 0.01:
            factors.append(f"Elevated error rate (avg: {np.mean(error_values)*100:.2f}%)")
        
        # Response time issues
        response_values = [m.response_time for m in recent if m.response_time]
        if response_values and np.mean(response_values) > 2000:
            factors.append(f"High response time (avg: {np.mean(response_values):.0f}ms)")
        
        # Trend analysis
        if len(metrics) > 20:
            # Check for degrading trends
            for metric_name in ['cpu_usage', 'memory_usage', 'error_rate']:
                values = [getattr(m, metric_name) for m in metrics if getattr(m, metric_name) is not None]
                if values and len(values) > 10:
                    trend = np.polyfit(range(len(values)), values, 1)[0]
                    if trend > 0.5:  # Significant upward trend
                        factors.append(f"Increasing {metric_name.replace('_', ' ')}")
        
        return factors
    
    def _generate_alert_description(self, prediction: MaintenancePredictionModel) -> str:
        """Generate detailed alert description"""
        desc = f"The {prediction.component_name} has a {prediction.failure_probability*100:.0f}% "
        desc += f"probability of failure"
        
        if prediction.predicted_failure_date:
            days_until = (prediction.predicted_failure_date - date.today()).days
            desc += f" within {days_until} days"
        
        desc += ". "
        
        if prediction.contributing_factors:
            desc += "Contributing factors: " + ", ".join(prediction.contributing_factors[:3])
        
        return desc
    
    def _analyze_metric_trend(self, values: List[float]) -> Dict[str, any]:
        """Analyze trend of a metric"""
        if not values or len(values) < 3:
            return {"trend": "unknown", "change": 0}
        
        # Calculate trend using linear regression
        x = list(range(len(values)))
        slope = np.polyfit(x, values, 1)[0]
        
        # Determine trend
        if abs(slope) < 0.1:
            trend = "stable"
        elif slope > 0:
            trend = "degrading"
        else:
            trend = "improving"
        
        # Calculate percentage change
        change = ((values[-1] - values[0]) / values[0]) * 100 if values[0] != 0 else 0
        
        return {
            "trend": trend,
            "change": change,
            "current": values[-1],
            "average": np.mean(values),
            "max": max(values),
            "min": min(values)
        }
    
    def _calculate_health_score(self, indicators: Dict[str, Dict]) -> float:
        """Calculate overall health score"""
        scores = []
        
        for metric, data in indicators.items():
            if data.get("trend") == "unknown":
                continue
            
            # Base score on current value and trend
            if metric in ["cpu_usage", "memory_usage", "disk_usage", "error_rate"]:
                # Lower is better
                if data.get("current", 0) < 50:
                    score = 1.0
                elif data["current"] < 70:
                    score = 0.7
                elif data["current"] < 85:
                    score = 0.4
                else:
                    score = 0.1
            else:  # response_time
                # Lower is better
                if data.get("current", 0) < 1000:
                    score = 1.0
                elif data["current"] < 2000:
                    score = 0.7
                elif data["current"] < 5000:
                    score = 0.4
                else:
                    score = 0.1
            
            # Adjust for trend
            if data["trend"] == "improving":
                score = min(score * 1.2, 1.0)
            elif data["trend"] == "degrading":
                score = score * 0.8
            
            scores.append(score)
        
        return np.mean(scores) if scores else 0.5
    
    def _get_health_status(self, score: float) -> str:
        """Get health status from score"""
        if score >= 0.8:
            return "healthy"
        elif score >= 0.6:
            return "good"
        elif score >= 0.4:
            return "fair"
        elif score >= 0.2:
            return "poor"
        else:
            return "critical"
    
    def _get_health_recommendations(self, indicators: Dict[str, Dict]) -> List[str]:
        """Get health improvement recommendations"""
        recommendations = []
        
        for metric, data in indicators.items():
            if data.get("trend") == "degrading":
                if metric == "cpu_usage":
                    recommendations.append("Consider scaling compute resources or optimizing workload")
                elif metric == "memory_usage":
                    recommendations.append("Investigate memory leaks or increase memory allocation")
                elif metric == "disk_usage":
                    recommendations.append("Clean up disk space or add storage capacity")
                elif metric == "error_rate":
                    recommendations.append("Review error logs and fix underlying issues")
                elif metric == "response_time":
                    recommendations.append("Optimize queries or add caching")
        
        return recommendations
    
    async def _store_prediction(self, prediction: MaintenancePrediction):
        """Store prediction in database"""
        db_pred = MaintenancePredictionModel(
            component_id=prediction.component_id,
            component_type=prediction.component_type,
            component_name=prediction.component_name,
            risk_level=prediction.risk_level,
            failure_probability=prediction.failure_probability,
            predicted_failure_date=prediction.predicted_failure_date,
            last_maintenance_date=prediction.last_maintenance_date,
            recommended_actions=prediction.recommended_actions,
            confidence_score=prediction.confidence_score,
            contributing_factors=prediction.contributing_factors,
            model_used=ModelType.RANDOM_FOREST
        )
        
        self.db.add(db_pred)
        await self.db.commit()
    
    async def _load_models(self):
        """Load or initialize maintenance models"""
        logger.info("Loading maintenance prediction models")
        
        # In production, load from model storage
        # For now, mark as not trained to use rule-based
        self.model_trained = False
    
    async def _periodic_prediction(self):
        """Periodically run maintenance predictions"""
        while True:
            try:
                await asyncio.sleep(6 * 3600)  # Every 6 hours
                
                logger.info("Running periodic maintenance prediction")
                await self.predict_maintenance()
                
            except Exception as e:
                logger.error("Error in periodic prediction", error=str(e))
    
    async def _periodic_model_update(self):
        """Periodically retrain models"""
        while True:
            try:
                await asyncio.sleep(7 * 24 * 3600)  # Weekly
                
                logger.info("Retraining maintenance models")
                await self._train_models()
                
            except Exception as e:
                logger.error("Error in model retraining", error=str(e))
    
    async def _train_models(self):
        """Train maintenance prediction models"""
        # Get historical data
        # In production, implement proper model training
        logger.info("Model training not yet implemented")