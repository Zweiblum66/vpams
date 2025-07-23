"""
Object Detection Service

This service handles object detection in images using YOLO models.
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
from ultralytics import YOLO
import structlog

from ..core.config import settings
from ..core.exceptions import InferenceError, ValidationError, ProcessingError
from ..core.logging import MLLogger
from ..db.models import MLProcessingJob, MLProcessingResult
from ..db.base import get_db_session


class ObjectDetectionService:
    """Service for object detection in images."""
    
    def __init__(self, model_manager):
        self.model_manager = model_manager
        self.logger = MLLogger("object_detection")
        
    async def detect_objects(
        self,
        image_data: Union[np.ndarray, bytes, str, Path],
        confidence_threshold: float = 0.5,
        iou_threshold: float = 0.45,
        max_detections: int = 100,
        class_filter: Optional[List[str]] = None,
        return_crops: bool = False,
        asset_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Detect objects in an image.
        
        Args:
            image_data: Image data (numpy array, bytes, file path, or Path object)
            confidence_threshold: Minimum confidence score for detections
            iou_threshold: IoU threshold for non-maximum suppression
            max_detections: Maximum number of detections to return
            class_filter: List of class names to filter detections
            return_crops: Whether to return cropped images of detections
            asset_id: Asset ID for database logging
            
        Returns:
            Dictionary containing detection results
        """
        start_time = time.time()
        
        try:
            # Load and validate image
            image = await self._load_image(image_data)
            
            # Get model
            model_info = await self.model_manager.get_model("object_detection")
            model = model_info.model
            
            # Run inference
            results = await self._run_inference(
                model, image, confidence_threshold, iou_threshold, max_detections
            )
            
            # Process results
            detections = await self._process_results(
                results, image, class_filter, return_crops
            )
            
            # Create response
            response = {
                "detections": detections,
                "total_objects": len(detections),
                "model_name": model_info.name,
                "model_version": model_info.metadata.get("version", "unknown"),
                "confidence_threshold": confidence_threshold,
                "iou_threshold": iou_threshold,
                "image_size": {
                    "width": image.shape[1],
                    "height": image.shape[0]
                },
                "processing_time": time.time() - start_time
            }
            
            # Log to database if asset_id provided
            if asset_id:
                await self._log_to_database(asset_id, response, detections)
            
            # Log inference
            self.logger.log_inference(
                "object_detection", 
                "image", 
                response["processing_time"],
                batch_size=1
            )
            
            return response
            
        except Exception as e:
            self.logger.log_error("object_detection", str(e), asset_id=asset_id)
            raise InferenceError(f"Object detection failed: {e}")
    
    async def detect_objects_batch(
        self,
        image_batch: List[Union[np.ndarray, bytes, str, Path]],
        confidence_threshold: float = 0.5,
        iou_threshold: float = 0.45,
        max_detections: int = 100,
        class_filter: Optional[List[str]] = None,
        return_crops: bool = False,
        asset_ids: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Detect objects in a batch of images.
        
        Args:
            image_batch: List of image data
            confidence_threshold: Minimum confidence score for detections
            iou_threshold: IoU threshold for non-maximum suppression
            max_detections: Maximum number of detections to return per image
            class_filter: List of class names to filter detections
            return_crops: Whether to return cropped images of detections
            asset_ids: List of asset IDs for database logging
            
        Returns:
            List of detection results for each image
        """
        start_time = time.time()
        
        try:
            # Create tasks for batch processing
            tasks = []
            for i, image_data in enumerate(image_batch):
                asset_id = asset_ids[i] if asset_ids and i < len(asset_ids) else None
                task = self.detect_objects(
                    image_data=image_data,
                    confidence_threshold=confidence_threshold,
                    iou_threshold=iou_threshold,
                    max_detections=max_detections,
                    class_filter=class_filter,
                    return_crops=return_crops,
                    asset_id=asset_id
                )
                tasks.append(task)
            
            # Process batch
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Handle exceptions
            successful_results = []
            failed_count = 0
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    failed_count += 1
                    self.logger.log_error("batch_object_detection", str(result), batch_index=i)
                    successful_results.append(None)
                else:
                    successful_results.append(result)
            
            # Log batch processing
            processing_time = time.time() - start_time
            self.logger.log_batch_processing(
                batch_size=len(image_batch),
                processing_time=processing_time,
                success_count=len(image_batch) - failed_count,
                error_count=failed_count
            )
            
            return successful_results
            
        except Exception as e:
            self.logger.log_error("batch_object_detection", str(e))
            raise InferenceError(f"Batch object detection failed: {e}")
    
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
            return image
        elif isinstance(image_data, (str, Path)):
            # Load from file path
            image = cv2.imread(str(image_data))
            if image is None:
                raise ValidationError(f"Could not load image from path: {image_data}")
            return image
        else:
            raise ValidationError(f"Unsupported image data type: {type(image_data)}")
    
    async def _run_inference(
        self,
        model: YOLO,
        image: np.ndarray,
        confidence_threshold: float,
        iou_threshold: float,
        max_detections: int
    ) -> List[Any]:
        """Run YOLO inference on image."""
        # Run inference
        results = model(
            image,
            conf=confidence_threshold,
            iou=iou_threshold,
            max_det=max_detections,
            verbose=False
        )
        return results
    
    async def _process_results(
        self,
        results: List[Any],
        image: np.ndarray,
        class_filter: Optional[List[str]] = None,
        return_crops: bool = False
    ) -> List[Dict[str, Any]]:
        """Process YOLO detection results."""
        detections = []
        
        for result in results:
            boxes = result.boxes
            if boxes is not None:
                for box in boxes:
                    # Extract detection data
                    confidence = float(box.conf[0])
                    class_id = int(box.cls[0])
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    
                    # Get class name
                    class_name = result.names[class_id] if hasattr(result, 'names') else str(class_id)
                    
                    # Apply class filter if specified
                    if class_filter and class_name not in class_filter:
                        continue
                    
                    # Create detection dict
                    detection = {
                        "class_name": class_name,
                        "class_id": class_id,
                        "confidence": confidence,
                        "bbox": {
                            "x1": x1,
                            "y1": y1,
                            "x2": x2,
                            "y2": y2,
                            "width": x2 - x1,
                            "height": y2 - y1,
                            "center_x": (x1 + x2) / 2,
                            "center_y": (y1 + y2) / 2
                        },
                        "area": (x2 - x1) * (y2 - y1),
                        "relative_area": ((x2 - x1) * (y2 - y1)) / (image.shape[0] * image.shape[1])
                    }
                    
                    # Add crop if requested
                    if return_crops:
                        crop = image[int(y1):int(y2), int(x1):int(x2)]
                        if crop.size > 0:
                            # Convert to base64 or save temporarily
                            detection["crop"] = self._encode_crop(crop)
                    
                    detections.append(detection)
        
        # Sort by confidence (highest first)
        detections.sort(key=lambda x: x["confidence"], reverse=True)
        
        return detections
    
    def _encode_crop(self, crop: np.ndarray) -> str:
        """Encode crop image to base64."""
        import base64
        _, buffer = cv2.imencode('.jpg', crop)
        crop_base64 = base64.b64encode(buffer).decode('utf-8')
        return crop_base64
    
    async def _log_to_database(
        self,
        asset_id: str,
        response: Dict[str, Any],
        detections: List[Dict[str, Any]]
    ) -> None:
        """Log detection results to database."""
        try:
            async with get_db_session() as session:
                # Create processing job
                job = MLProcessingJob(
                    asset_id=uuid.UUID(asset_id),
                    job_type="object_detection",
                    status="completed",
                    input_data={
                        "confidence_threshold": response["confidence_threshold"],
                        "iou_threshold": response["iou_threshold"],
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
                
                # Create result records for each detection
                for detection in detections:
                    result = MLProcessingResult(
                        job_id=job.id,
                        result_type="object_detection",
                        result_data=detection,
                        confidence=detection["confidence"],
                        bbox_x=detection["bbox"]["x1"],
                        bbox_y=detection["bbox"]["y1"],
                        bbox_width=detection["bbox"]["width"],
                        bbox_height=detection["bbox"]["height"],
                        metadata={
                            "class_name": detection["class_name"],
                            "class_id": detection["class_id"],
                            "area": detection["area"],
                            "relative_area": detection["relative_area"]
                        }
                    )
                    session.add(result)
                
                await session.commit()
                
        except Exception as e:
            self.logger.log_error("database_logging", str(e), asset_id=asset_id)
    
    async def get_supported_classes(self) -> List[str]:
        """Get list of supported object classes."""
        try:
            model_info = await self.model_manager.get_model("object_detection")
            if hasattr(model_info.model, 'names'):
                return list(model_info.model.names.values())
            return []
        except Exception as e:
            self.logger.log_error("get_classes", str(e))
            return []
    
    async def get_model_info(self) -> Dict[str, Any]:
        """Get object detection model information."""
        try:
            model_info = await self.model_manager.get_model("object_detection")
            return {
                "name": model_info.name,
                "type": model_info.model_type,
                "metadata": model_info.metadata,
                "supported_classes": await self.get_supported_classes()
            }
        except Exception as e:
            self.logger.log_error("get_model_info", str(e))
            return {}