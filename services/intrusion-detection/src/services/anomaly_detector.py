"""
Machine learning-based anomaly detection for network traffic and system behavior.

Uses various ML algorithms to detect unusual patterns that may indicate security threats.
"""

import asyncio
import json
import pickle
import os
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, deque
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import DBSCAN
from sklearn.decomposition import PCA
import structlog

from ..core.config import get_settings
from ..core.exceptions import AnomalyDetectionError
from ..models.schemas import NetworkPacket, AnomalyResult


logger = structlog.get_logger()


class AnomalyDetector:
    """Machine learning-based anomaly detection system."""
    
    def __init__(self):
        self.settings = get_settings()
        
        # ML Models
        self.isolation_forest: Optional[IsolationForest] = None
        self.scaler: Optional[StandardScaler] = None
        self.dbscan: Optional[DBSCAN] = None
        self.pca: Optional[PCA] = None
        
        # Feature extraction
        self.feature_window = deque(maxlen=1000)
        self.baseline_stats: Dict[str, Any] = {}
        
        # Traffic patterns
        self.traffic_profiles: Dict[str, Dict] = defaultdict(dict)
        self.connection_patterns: Dict[str, List] = defaultdict(list)
        
        # Model state
        self.model_trained = False
        self.last_training = None
        self.training_data: List[Dict] = []
        
        # Thresholds
        self.anomaly_threshold = self.settings.detection_threshold
        self.learning_period = timedelta(hours=self.settings.learning_period_hours)
        
        # Statistics
        self.stats = {
            "packets_analyzed": 0,
            "anomalies_detected": 0,
            "false_positives": 0,
            "model_accuracy": 0.0,
            "last_retrain": None
        }
    
    async def initialize(self) -> None:
        """Initialize anomaly detection system."""
        try:
            logger.info("Initializing anomaly detector")
            
            # Load existing models if available
            await self._load_models()
            
            # Initialize baseline statistics
            await self._initialize_baseline()
            
            # Start background training task
            asyncio.create_task(self._periodic_retraining())
            
            logger.info(
                "Anomaly detector initialized",
                model_trained=self.model_trained,
                threshold=self.anomaly_threshold
            )
            
        except Exception as e:
            logger.error("Failed to initialize anomaly detector", error=str(e))
            raise AnomalyDetectionError(f"Initialization failed: {str(e)}")
    
    async def _load_models(self) -> None:
        """Load pre-trained models from disk."""
        try:
            model_dir = "/app/models"
            os.makedirs(model_dir, exist_ok=True)
            
            model_files = {
                "isolation_forest": "isolation_forest.pkl",
                "scaler": "scaler.pkl",
                "baseline_stats": "baseline_stats.json"
            }
            
            for model_name, filename in model_files.items():
                filepath = os.path.join(model_dir, filename)
                
                if os.path.exists(filepath):
                    if filename.endswith('.pkl'):
                        with open(filepath, 'rb') as f:
                            if model_name == "isolation_forest":
                                self.isolation_forest = pickle.load(f)
                            elif model_name == "scaler":
                                self.scaler = pickle.load(f)
                    elif filename.endswith('.json'):
                        with open(filepath, 'r') as f:
                            self.baseline_stats = json.load(f)
                    
                    logger.debug(f"Loaded model: {model_name}")
            
            if self.isolation_forest and self.scaler:
                self.model_trained = True
                logger.info("Pre-trained models loaded successfully")
            
        except Exception as e:
            logger.warning("Could not load pre-trained models", error=str(e))
    
    async def _save_models(self) -> None:
        """Save trained models to disk."""
        try:
            model_dir = "/app/models"
            os.makedirs(model_dir, exist_ok=True)
            
            if self.isolation_forest:
                with open(os.path.join(model_dir, "isolation_forest.pkl"), 'wb') as f:
                    pickle.dump(self.isolation_forest, f)
            
            if self.scaler:
                with open(os.path.join(model_dir, "scaler.pkl"), 'wb') as f:
                    pickle.dump(self.scaler, f)
            
            if self.baseline_stats:
                with open(os.path.join(model_dir, "baseline_stats.json"), 'w') as f:
                    json.dump(self.baseline_stats, f)
            
            logger.info("Models saved successfully")
            
        except Exception as e:
            logger.error("Failed to save models", error=str(e))
    
    async def _initialize_baseline(self) -> None:
        """Initialize baseline statistics for normal behavior."""
        if not self.baseline_stats:
            self.baseline_stats = {
                "packet_sizes": {"mean": 500, "std": 200},
                "inter_arrival_times": {"mean": 0.1, "std": 0.05},
                "port_distribution": {},
                "protocol_distribution": {"tcp": 0.7, "udp": 0.2, "icmp": 0.1},
                "connection_rates": {"mean": 10, "std": 5},
                "payload_entropy": {"mean": 0.8, "std": 0.2}
            }
    
    async def analyze_packet(self, packet: NetworkPacket) -> AnomalyResult:
        """Analyze a single packet for anomalies."""
        try:
            self.stats["packets_analyzed"] += 1
            
            # Extract features from packet
            features = self._extract_packet_features(packet)
            
            # Add to feature window for temporal analysis
            self.feature_window.append({
                "timestamp": packet.timestamp,
                "features": features,
                "packet_id": packet.id
            })
            
            # Perform anomaly detection
            anomaly_results = []
            
            # Statistical anomaly detection
            stat_result = await self._statistical_anomaly_detection(features, packet)
            if stat_result:
                anomaly_results.append(stat_result)
            
            # ML-based anomaly detection
            if self.model_trained:
                ml_result = await self._ml_anomaly_detection(features, packet)
                if ml_result:
                    anomaly_results.append(ml_result)
            
            # Behavioral anomaly detection
            behavioral_result = await self._behavioral_anomaly_detection(packet)
            if behavioral_result:
                anomaly_results.append(behavioral_result)
            
            # Combine results
            if anomaly_results:
                # Take the highest scoring anomaly
                best_result = max(anomaly_results, key=lambda x: x.score)
                self.stats["anomalies_detected"] += 1
                return best_result
            
            # No anomaly detected
            return AnomalyResult(
                is_anomaly=False,
                score=0.0,
                anomaly_type="normal",
                confidence=0.9,
                features_analyzed=list(features.keys()),
                threshold_used=self.anomaly_threshold
            )
            
        except Exception as e:
            logger.error("Error analyzing packet for anomalies", packet_id=packet.id, error=str(e))
            raise AnomalyDetectionError(f"Packet analysis failed: {str(e)}")
    
    def _extract_packet_features(self, packet: NetworkPacket) -> Dict[str, float]:
        """Extract features from network packet for ML analysis."""
        features = {}
        
        # Basic packet features
        features["payload_size"] = float(packet.payload_size)
        features["source_port"] = float(packet.source_port or 0)
        features["dest_port"] = float(packet.dest_port or 0)
        
        # Protocol encoding
        protocol_encoding = {
            "tcp": 1.0, "udp": 2.0, "icmp": 3.0,
            "http": 4.0, "https": 5.0, "dns": 6.0,
            "ssh": 7.0, "ftp": 8.0, "smtp": 9.0
        }
        features["protocol"] = protocol_encoding.get(packet.protocol.value, 0.0)
        
        # Time-based features
        current_time = packet.timestamp.timestamp()
        features["hour_of_day"] = float(packet.timestamp.hour)
        features["day_of_week"] = float(packet.timestamp.weekday())\n        \n        # Connection features\n        features["num_flags"] = float(len(packet.flags))\n        features["has_syn"] = 1.0 if "SYN" in packet.flags else 0.0\n        features["has_ack"] = 1.0 if "ACK" in packet.flags else 0.0\n        features["has_fin"] = 1.0 if "FIN" in packet.flags else 0.0\n        features["has_rst"] = 1.0 if "RST" in packet.flags else 0.0\n        \n        # Payload entropy (simplified)\n        if packet.payload_hash:\n            # Use hash to estimate entropy\n            hash_bytes = bytes.fromhex(packet.payload_hash)\n            entropy = sum(b for b in hash_bytes) / len(hash_bytes) / 255.0\n            features["payload_entropy"] = entropy\n        else:\n            features["payload_entropy"] = 0.0\n        \n        # Metadata features\n        if packet.metadata:\n            features["ttl"] = float(packet.metadata.get("ttl", 64))\n            features["packet_length"] = float(packet.metadata.get("length", 0))\n        \n        return features\n    \n    async def _statistical_anomaly_detection(self, features: Dict[str, float], packet: NetworkPacket) -> Optional[AnomalyResult]:\n        """Statistical anomaly detection based on baseline."""\n        try:\n            anomaly_score = 0.0\n            anomaly_factors = []\n            \n            # Check packet size anomaly\n            baseline_size = self.baseline_stats["packet_sizes"]\n            size_zscore = abs(features["payload_size"] - baseline_size["mean"]) / baseline_size["std"]\n            if size_zscore > 3.0:  # 3-sigma rule\n                anomaly_score += 0.3\n                anomaly_factors.append("unusual_packet_size")\n            \n            # Check port anomaly\n            dest_port = packet.dest_port\n            if dest_port and dest_port > 1024:  # High port number\n                if dest_port not in [8080, 8443, 9000]:  # Common high ports\n                    anomaly_score += 0.2\n                    anomaly_factors.append("high_port_number")\n            \n            # Check protocol distribution\n            protocol_dist = self.baseline_stats["protocol_distribution"]\n            expected_prob = protocol_dist.get(packet.protocol.value, 0.01)\n            if expected_prob < 0.1:  # Rare protocol\n                anomaly_score += 0.4\n                anomaly_factors.append("rare_protocol")\n            \n            # Check time-based anomaly\n            hour = packet.timestamp.hour\n            if hour < 6 or hour > 22:  # Outside business hours\n                anomaly_score += 0.1\n                anomaly_factors.append("off_hours_activity")\n            \n            if anomaly_score >= self.anomaly_threshold:\n                return AnomalyResult(\n                    is_anomaly=True,\n                    score=min(anomaly_score, 1.0),\n                    anomaly_type="statistical",\n                    confidence=0.7,\n                    features_analyzed=list(features.keys()),\n                    threshold_used=self.anomaly_threshold,\n                    metadata={\n                        "anomaly_factors": anomaly_factors,\n                        "z_scores": {"packet_size": size_zscore}\n                    }\n                )\n            \n            return None\n            \n        except Exception as e:\n            logger.error("Statistical anomaly detection error", error=str(e))\n            return None\n    \n    async def _ml_anomaly_detection(self, features: Dict[str, float], packet: NetworkPacket) -> Optional[AnomalyResult]:\n        """Machine learning-based anomaly detection."""\n        try:\n            if not self.isolation_forest or not self.scaler:\n                return None\n            \n            # Prepare feature vector\n            feature_names = ["payload_size", "protocol", "hour_of_day", "day_of_week", \n                           "num_flags", "has_syn", "has_ack", "payload_entropy"]\n            \n            feature_vector = [features.get(name, 0.0) for name in feature_names]\n            feature_array = np.array(feature_vector).reshape(1, -1)\n            \n            # Scale features\n            scaled_features = self.scaler.transform(feature_array)\n            \n            # Predict anomaly\n            anomaly_score = self.isolation_forest.decision_function(scaled_features)[0]\n            is_anomaly = self.isolation_forest.predict(scaled_features)[0] == -1\n            \n            # Convert score to 0-1 range\n            normalized_score = max(0.0, min(1.0, (-anomaly_score + 0.5) / 1.0))\n            \n            if is_anomaly and normalized_score >= self.anomaly_threshold:\n                return AnomalyResult(\n                    is_anomaly=True,\n                    score=normalized_score,\n                    anomaly_type="ml_isolation_forest",\n                    confidence=0.8,\n                    features_analyzed=feature_names,\n                    threshold_used=self.anomaly_threshold,\n                    metadata={\n                        "raw_score": float(anomaly_score),\n                        "feature_vector": feature_vector\n                    }\n                )\n            \n            return None\n            \n        except Exception as e:\n            logger.error("ML anomaly detection error", error=str(e))\n            return None\n    \n    async def _behavioral_anomaly_detection(self, packet: NetworkPacket) -> Optional[AnomalyResult]:\n        """Behavioral anomaly detection based on traffic patterns."""\n        try:\n            anomaly_score = 0.0\n            anomaly_factors = []\n            \n            source_ip = packet.source_ip\n            current_time = packet.timestamp\n            \n            # Update traffic profile for source IP\n            if source_ip not in self.traffic_profiles:\n                self.traffic_profiles[source_ip] = {\n                    "first_seen": current_time,\n                    "packet_count": 0,\n                    "protocols": set(),\n                    "ports": set(),\n                    "last_activity": current_time\n                }\n            \n            profile = self.traffic_profiles[source_ip]\n            profile["packet_count"] += 1\n            profile["protocols"].add(packet.protocol.value)\n            if packet.dest_port:\n                profile["ports"].add(packet.dest_port)\n            \n            time_since_last = (current_time - profile["last_activity"]).total_seconds()\n            profile["last_activity"] = current_time\n            \n            # Check for rapid-fire connections\n            if time_since_last < 0.1 and profile["packet_count"] > 100:\n                anomaly_score += 0.4\n                anomaly_factors.append("rapid_connections")\n            \n            # Check for port scanning behavior\n            if len(profile["ports"]) > 20:  # Accessing many ports\n                anomaly_score += 0.5\n                anomaly_factors.append("port_scanning")\n            \n            # Check for protocol anomalies\n            if len(profile["protocols"]) > 5:  # Using many protocols\n                anomaly_score += 0.3\n                anomaly_factors.append("protocol_diversity")\n            \n            # Check for new host behavior\n            time_since_first = (current_time - profile["first_seen"]).total_seconds()\n            if time_since_first < 300 and profile["packet_count"] > 500:  # High activity from new host\n                anomaly_score += 0.4\n                anomaly_factors.append("new_host_high_activity")\n            \n            if anomaly_score >= self.anomaly_threshold:\n                return AnomalyResult(\n                    is_anomaly=True,\n                    score=min(anomaly_score, 1.0),\n                    anomaly_type="behavioral",\n                    confidence=0.75,\n                    features_analyzed=["connection_patterns", "temporal_behavior"],\n                    threshold_used=self.anomaly_threshold,\n                    metadata={\n                        "anomaly_factors": anomaly_factors,\n                        "traffic_profile": {\n                            "packet_count": profile["packet_count"],\n                            "protocols": list(profile["protocols"]),\n                            "port_count": len(profile["ports"]),\n                            "time_since_first_seen": time_since_first\n                        }\n                    }\n                )\n            \n            return None\n            \n        except Exception as e:\n            logger.error("Behavioral anomaly detection error", error=str(e))\n            return None\n    \n    async def _periodic_retraining(self) -> None:\n        """Periodically retrain ML models with new data."""\n        while True:\n            try:\n                await asyncio.sleep(self.settings.model_update_interval)\n                \n                if len(self.feature_window) > 100:  # Minimum data for training\n                    await self._train_models()\n                \n            except Exception as e:\n                logger.error("Error in periodic retraining", error=str(e))\n                await asyncio.sleep(3600)  # Wait 1 hour on error\n    \n    async def _train_models(self) -> None:\n        """Train/retrain ML models with collected data."""\n        try:\n            logger.info("Starting model training")\n            \n            # Prepare training data\n            training_features = []\n            for window_item in self.feature_window:\n                features = window_item["features"]\n                feature_vector = [\n                    features.get("payload_size", 0.0),\n                    features.get("protocol", 0.0),\n                    features.get("hour_of_day", 0.0),\n                    features.get("day_of_week", 0.0),\n                    features.get("num_flags", 0.0),\n                    features.get("has_syn", 0.0),\n                    features.get("has_ack", 0.0),\n                    features.get("payload_entropy", 0.0)\n                ]\n                training_features.append(feature_vector)\n            \n            if len(training_features) < 50:\n                logger.warning("Insufficient training data", samples=len(training_features))\n                return\n            \n            # Convert to numpy array\n            X = np.array(training_features)\n            \n            # Initialize and train scaler\n            self.scaler = StandardScaler()\n            X_scaled = self.scaler.fit_transform(X)\n            \n            # Train Isolation Forest\n            self.isolation_forest = IsolationForest(\n                contamination=0.1,  # Expect 10% anomalies\n                random_state=42,\n                n_estimators=100\n            )\n            self.isolation_forest.fit(X_scaled)\n            \n            # Update model state\n            self.model_trained = True\n            self.last_training = datetime.utcnow()\n            self.stats["last_retrain"] = self.last_training\n            \n            # Save models\n            await self._save_models()\n            \n            logger.info(\n                "Model training completed",\n                samples=len(training_features),\n                timestamp=self.last_training\n            )\n            \n        except Exception as e:\n            logger.error("Model training failed", error=str(e))\n            raise AnomalyDetectionError(f"Model training failed: {str(e)}")\n    \n    async def update_baseline(self, feedback_data: List[Dict[str, Any]]) -> None:\n        """Update baseline statistics based on feedback."""\n        try:\n            # Process feedback to improve baseline\n            for feedback in feedback_data:\n                if feedback.get("is_false_positive"):\n                    self.stats["false_positives"] += 1\n                    # Adjust thresholds based on false positives\n                    if self.stats["false_positives"] > 10:\n                        self.anomaly_threshold = min(0.9, self.anomaly_threshold + 0.05)\n            \n            logger.info("Baseline updated", false_positives=self.stats["false_positives"])\n            \n        except Exception as e:\n            logger.error("Error updating baseline", error=str(e))\n    \n    def get_statistics(self) -> Dict[str, Any]:\n        """Get anomaly detector statistics."""\n        return {\n            **self.stats,\n            "model_trained": self.model_trained,\n            "threshold": self.anomaly_threshold,\n            "feature_window_size": len(self.feature_window),\n            "traffic_profiles_count": len(self.traffic_profiles)\n        }