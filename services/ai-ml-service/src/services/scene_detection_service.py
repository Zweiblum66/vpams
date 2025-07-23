"""
Scene Detection Service

This service handles scene detection and classification in videos and images.
"""

import asyncio
import time
from typing import Dict, Any, List, Optional, Union, Tuple
import uuid
from pathlib import Path

import numpy as np
import cv2
from PIL import Image
import torch
from transformers import AutoFeatureExtractor, AutoModelForImageClassification
import structlog

from ..core.config import settings
from ..core.exceptions import InferenceError, ValidationError, ProcessingError
from ..core.logging import MLLogger
from ..db.models import MLProcessingJob, MLProcessingResult
from ..db.base import get_db_session


class SceneDetectionService:
    """Service for scene detection and classification in videos and images."""
    
    def __init__(self, model_manager):
        self.model_manager = model_manager
        self.logger = MLLogger("scene_detection")
        
    async def detect_scenes(
        self,
        image_data: Union[np.ndarray, bytes, str, Path],
        confidence_threshold: float = 0.1,
        top_k: int = 5,
        return_features: bool = False,
        asset_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Detect scenes in an image.
        
        Args:
            image_data: Image data (numpy array, bytes, file path, or Path object)
            confidence_threshold: Minimum confidence score for classifications
            top_k: Number of top classifications to return
            return_features: Whether to return feature vectors
            asset_id: Asset ID for database logging
            
        Returns:
            Dictionary containing scene detection results
        """
        start_time = time.time()
        
        try:
            # Load and validate image
            image = await self._load_image(image_data)
            
            # Get model
            model_info = await self.model_manager.get_model("scene_detection")
            model = model_info.model
            feature_extractor = model_info.metadata.get("feature_extractor")
            
            # Run inference
            results = await self._run_inference(
                model, feature_extractor, image, confidence_threshold, top_k
            )
            
            # Create response
            response = {
                "scenes": results["scenes"],
                "total_scenes": len(results["scenes"]),
                "model_name": model_info.name,
                "model_version": model_info.metadata.get("version", "unknown"),
                "confidence_threshold": confidence_threshold,
                "top_k": top_k,
                "image_size": {
                    "width": image.shape[1],
                    "height": image.shape[0]
                },
                "processing_time": time.time() - start_time
            }
            
            if return_features and "features" in results:
                response["features"] = results["features"]
            
            # Log to database if asset_id provided
            if asset_id:
                await self._log_to_database(asset_id, response, results["scenes"])
            
            # Log inference
            self.logger.log_inference(
                "scene_detection", 
                "image", 
                response["processing_time"],
                batch_size=1
            )
            
            return response
            
        except Exception as e:
            self.logger.log_error("scene_detection", str(e), asset_id=asset_id)
            raise InferenceError(f"Scene detection failed: {e}")
    
    async def detect_scenes_video(
        self,
        video_path: Union[str, Path],
        sample_rate: int = 30,  # Extract frame every N frames
        confidence_threshold: float = 0.1,
        top_k: int = 5,
        scene_change_threshold: float = 0.3,
        asset_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Detect scenes in a video by analyzing frames.
        
        Args:
            video_path: Path to video file
            sample_rate: Extract frame every N frames
            confidence_threshold: Minimum confidence score for classifications
            top_k: Number of top classifications to return per frame
            scene_change_threshold: Threshold for detecting scene changes
            asset_id: Asset ID for database logging
            
        Returns:
            Dictionary containing video scene detection results
        """
        start_time = time.time()
        
        try:
            # Open video
            cap = cv2.VideoCapture(str(video_path))
            if not cap.isOpened():
                raise ValidationError(f"Could not open video file: {video_path}")
            
            # Get video properties
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = total_frames / fps if fps > 0 else 0
            
            # Extract and analyze frames
            frame_results = []
            frame_count = 0
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Process every sample_rate frames
                if frame_count % sample_rate == 0:
                    try:
                        # Convert BGR to RGB
                        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        
                        # Detect scenes in this frame
                        frame_result = await self.detect_scenes(
                            image_data=rgb_frame,
                            confidence_threshold=confidence_threshold,
                            top_k=top_k,
                            return_features=True
                        )
                        
                        # Add timing information
                        frame_result["frame_number"] = frame_count
                        frame_result["timestamp"] = frame_count / fps if fps > 0 else 0
                        
                        frame_results.append(frame_result)
                        
                    except Exception as e:
                        self.logger.log_error("frame_processing", str(e), frame_number=frame_count)
                
                frame_count += 1
            
            cap.release()
            
            # Analyze scene changes
            scenes = await self._analyze_scene_changes(frame_results, scene_change_threshold)
            
            # Create response
            response = {
                "scenes": scenes,
                "total_scenes": len(scenes),
                "frame_results": frame_results,
                "video_info": {
                    "duration": duration,
                    "fps": fps,
                    "total_frames": total_frames,
                    "analyzed_frames": len(frame_results)
                },
                "processing_time": time.time() - start_time,
                "sample_rate": sample_rate,
                "scene_change_threshold": scene_change_threshold
            }
            
            # Log to database if asset_id provided
            if asset_id:
                await self._log_video_to_database(asset_id, response)
            
            # Log inference
            self.logger.log_inference(
                "scene_detection_video", 
                "video", 
                response["processing_time"],
                batch_size=len(frame_results)
            )
            
            return response
            
        except Exception as e:
            self.logger.log_error("scene_detection_video", str(e), asset_id=asset_id)
            raise InferenceError(f"Video scene detection failed: {e}")
    
    async def _load_image(self, image_data: Union[np.ndarray, bytes, str, Path]) -> np.ndarray:
        """Load and validate image data."""
        if isinstance(image_data, np.ndarray):
            return image_data
        elif isinstance(image_data, bytes):
            # Convert bytes to image
            nparr = np.frombuffer(image_data, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if image is None:
                raise ValidationError("Could not decode image from bytes")
            return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        elif isinstance(image_data, (str, Path)):
            # Load from file path
            image = cv2.imread(str(image_data))
            if image is None:
                raise ValidationError(f"Could not load image from path: {image_data}")
            return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        else:
            raise ValidationError(f"Unsupported image data type: {type(image_data)}")
    
    async def _run_inference(
        self,
        model,
        feature_extractor,
        image: np.ndarray,
        confidence_threshold: float,
        top_k: int
    ) -> Dict[str, Any]:
        """Run scene detection inference."""
        # Prepare input
        inputs = feature_extractor(images=image, return_tensors="pt")
        
        # Run inference
        with torch.no_grad():
            outputs = model(**inputs)
            predictions = torch.nn.functional.softmax(outputs.logits, dim=-1)
        
        # Get top predictions
        top_predictions = torch.topk(predictions, k=min(top_k, predictions.size(-1)))
        
        # Process results
        scenes = []
        for i in range(top_predictions.indices.size(-1)):
            confidence = float(top_predictions.values[0][i])
            class_idx = int(top_predictions.indices[0][i])
            
            if confidence >= confidence_threshold:
                # Get class name from model config
                class_name = model.config.id2label.get(class_idx, f"class_{class_idx}")
                
                scenes.append({
                    "class_name": class_name,
                    "class_id": class_idx,
                    "confidence": confidence
                })
        
        result = {
            "scenes": scenes,
            "features": predictions[0].tolist()  # Feature vector
        }
        
        return result
    
    async def _analyze_scene_changes(
        self,
        frame_results: List[Dict[str, Any]],
        scene_change_threshold: float
    ) -> List[Dict[str, Any]]:
        """Analyze scene changes across video frames."""
        if not frame_results:
            return []
        
        scenes = []
        current_scene = None
        
        for i, frame_result in enumerate(frame_results):
            frame_scenes = frame_result.get("scenes", [])
            
            if not frame_scenes:
                continue
            
            # Get dominant scene (highest confidence)
            dominant_scene = frame_scenes[0]
            
            # Check if this is a scene change
            if current_scene is None:
                # First scene
                current_scene = {
                    "scene_name": dominant_scene["class_name"],
                    "scene_id": dominant_scene["class_id"],
                    "confidence": dominant_scene["confidence"],
                    "start_time": frame_result["timestamp"],
                    "start_frame": frame_result["frame_number"],
                    "end_time": frame_result["timestamp"],
                    "end_frame": frame_result["frame_number"]
                }
            else:
                # Check if scene changed
                confidence_diff = abs(current_scene["confidence"] - dominant_scene["confidence"])
                scene_changed = (
                    current_scene["scene_name"] != dominant_scene["class_name"] or
                    confidence_diff > scene_change_threshold
                )
                
                if scene_changed:
                    # End current scene
                    scenes.append(current_scene)
                    
                    # Start new scene
                    current_scene = {
                        "scene_name": dominant_scene["class_name"],
                        "scene_id": dominant_scene["class_id"],
                        "confidence": dominant_scene["confidence"],
                        "start_time": frame_result["timestamp"],
                        "start_frame": frame_result["frame_number"],
                        "end_time": frame_result["timestamp"],
                        "end_frame": frame_result["frame_number"]
                    }
                else:
                    # Continue current scene
                    current_scene["end_time"] = frame_result["timestamp"]
                    current_scene["end_frame"] = frame_result["frame_number"]
                    # Update confidence (running average)
                    current_scene["confidence"] = (
                        current_scene["confidence"] + dominant_scene["confidence"]
                    ) / 2
        
        # Add final scene
        if current_scene:
            scenes.append(current_scene)
        
        return scenes
    
    async def _log_to_database(
        self,
        asset_id: str,
        response: Dict[str, Any],
        scenes: List[Dict[str, Any]]
    ) -> None:
        """Log scene detection results to database."""
        try:
            async with get_db_session() as session:
                # Create processing job
                job = MLProcessingJob(
                    asset_id=uuid.UUID(asset_id),
                    job_type="scene_detection",
                    status="completed",
                    input_data={
                        "confidence_threshold": response["confidence_threshold"],
                        "top_k": response["top_k"],
                        "image_size": response["image_size"]
                    },
                    results=response,
                    model_name=response["model_name"],
                    model_version=response["model_version"],
                    processing_time=response["processing_time"],
                    completed_at=time.time()
                )
                
                session.add(job)
                await session.flush()
                
                # Create result records for each scene
                for scene in scenes:
                    result = MLProcessingResult(
                        job_id=job.id,
                        result_type="scene_detection",
                        result_data=scene,
                        confidence=scene["confidence"],
                        metadata={
                            "class_name": scene["class_name"],
                            "class_id": scene["class_id"]
                        }
                    )
                    session.add(result)
                
                await session.commit()
                
        except Exception as e:
            self.logger.log_error("database_logging", str(e), asset_id=asset_id)
    
    async def _log_video_to_database(
        self,
        asset_id: str,
        response: Dict[str, Any]
    ) -> None:
        """Log video scene detection results to database."""
        try:
            async with get_db_session() as session:
                # Create processing job
                job = MLProcessingJob(
                    asset_id=uuid.UUID(asset_id),
                    job_type="scene_detection_video",
                    status="completed",
                    input_data={
                        "video_info": response["video_info"],
                        "sample_rate": response["sample_rate"],
                        "scene_change_threshold": response["scene_change_threshold"]
                    },
                    results=response,
                    model_name="scene_detection",
                    processing_time=response["processing_time"],
                    completed_at=time.time()
                )
                
                session.add(job)
                await session.flush()
                
                # Create result records for each scene
                for scene in response["scenes"]:
                    result = MLProcessingResult(
                        job_id=job.id,
                        result_type="scene_detection_video",
                        result_data=scene,
                        confidence=scene["confidence"],
                        start_time=scene["start_time"],
                        end_time=scene["end_time"],
                        metadata={
                            "scene_name": scene["scene_name"],
                            "scene_id": scene["scene_id"],
                            "start_frame": scene["start_frame"],
                            "end_frame": scene["end_frame"]
                        }
                    )
                    session.add(result)
                
                await session.commit()
                
        except Exception as e:
            self.logger.log_error("database_logging", str(e), asset_id=asset_id)
    
    async def get_supported_scenes(self) -> List[str]:
        """Get list of supported scene classes."""
        try:
            model_info = await self.model_manager.get_model("scene_detection")
            model = model_info.model
            
            if hasattr(model, 'config') and hasattr(model.config, 'id2label'):
                return list(model.config.id2label.values())
            return []
        except Exception as e:
            self.logger.log_error("get_scenes", str(e))
            return []
    
    async def get_model_info(self) -> Dict[str, Any]:
        """Get scene detection model information."""
        try:
            model_info = await self.model_manager.get_model("scene_detection")
            return {
                "name": model_info.name,
                "type": model_info.model_type,
                "metadata": model_info.metadata,
                "supported_scenes": await self.get_supported_scenes()
            }
        except Exception as e:
            self.logger.log_error("get_model_info", str(e))
            return {}