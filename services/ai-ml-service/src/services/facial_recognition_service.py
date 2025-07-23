"""
Facial Recognition Service

This service handles facial recognition and identification using various models.
"""

import asyncio
import time
from typing import Dict, Any, List, Optional, Union, Tuple
import uuid
from pathlib import Path
import hashlib
import pickle
import base64

import numpy as np
import cv2
from PIL import Image
import torch
import structlog

from ..core.config import settings
from ..core.exceptions import InferenceError, ValidationError, ProcessingError
from ..core.logging import MLLogger
from ..db.models import MLProcessingJob, MLProcessingResult
from ..db.base import get_db_session


class FacialRecognitionService:
    """Service for facial recognition and identification."""
    
    def __init__(self, model_manager):
        self.model_manager = model_manager
        self.logger = MLLogger("facial_recognition")
        self.face_database = {}  # In-memory face database
        
    async def detect_and_recognize_faces(
        self,
        image_data: Union[np.ndarray, bytes, str, Path],
        known_faces: Optional[Dict[str, np.ndarray]] = None,
        min_face_size: int = 20,
        confidence_threshold: float = 0.6,
        distance_threshold: float = 0.6,
        return_face_crops: bool = False,
        return_embeddings: bool = False,
        asset_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Detect and recognize faces in an image.
        
        Args:
            image_data: Image data (numpy array, bytes, file path, or Path object)
            known_faces: Dictionary of known face embeddings {person_id: embedding}
            min_face_size: Minimum face size in pixels
            confidence_threshold: Minimum confidence for face detection
            distance_threshold: Maximum distance for face recognition
            return_face_crops: Whether to return cropped face images
            return_embeddings: Whether to return face embeddings
            asset_id: Asset ID for database logging
            
        Returns:
            Dictionary containing face detection and recognition results
        """
        start_time = time.time()
        
        try:
            # Load and validate image
            image = await self._load_image(image_data)
            
            # Get face detection model
            face_model_info = await self.model_manager.get_model("face_detection")
            
            # Detect faces
            face_detections = await self._detect_faces(
                face_model_info.model, image, min_face_size, confidence_threshold
            )
            
            # Extract face embeddings and perform recognition
            recognized_faces = []
            for detection in face_detections:
                try:
                    # Extract face crop
                    face_crop = await self._extract_face_crop(image, detection)
                    
                    # Get face embedding
                    embedding = await self._get_face_embedding(face_crop)
                    
                    # Perform recognition if known faces provided
                    recognition_result = None
                    if known_faces:
                        recognition_result = await self._recognize_face(
                            embedding, known_faces, distance_threshold
                        )
                    
                    # Build result
                    face_result = {
                        "detection": detection,
                        "recognition": recognition_result,
                        "face_id": self._generate_face_id(embedding)
                    }
                    
                    if return_face_crops:
                        face_result["face_crop"] = self._encode_face_crop(face_crop)
                    
                    if return_embeddings:
                        face_result["embedding"] = embedding.tolist()
                    
                    recognized_faces.append(face_result)
                    
                except Exception as e:
                    self.logger.log_error("face_processing", str(e))
                    continue
            
            # Create response
            response = {
                "faces": recognized_faces,
                "total_faces": len(recognized_faces),
                "model_name": face_model_info.name,
                "model_version": face_model_info.metadata.get("version", "unknown"),
                "confidence_threshold": confidence_threshold,
                "distance_threshold": distance_threshold,
                "image_size": {
                    "width": image.shape[1],
                    "height": image.shape[0]
                },
                "processing_time": time.time() - start_time
            }
            
            # Log to database if asset_id provided
            if asset_id:
                await self._log_to_database(asset_id, response, recognized_faces)
            
            # Log inference
            self.logger.log_inference(
                "facial_recognition", 
                "image", 
                response["processing_time"],
                batch_size=1
            )
            
            return response
            
        except Exception as e:
            self.logger.log_error("facial_recognition", str(e), asset_id=asset_id)
            raise InferenceError(f"Facial recognition failed: {e}")
    
    async def add_known_face(
        self,
        person_id: str,
        image_data: Union[np.ndarray, bytes, str, Path],
        face_bbox: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        Add a known face to the database.
        
        Args:
            person_id: Unique identifier for the person
            image_data: Image containing the face
            face_bbox: Optional bounding box of the face
            
        Returns:
            Dictionary containing the face embedding and metadata
        """
        try:
            # Load image
            image = await self._load_image(image_data)
            
            # If no bounding box provided, detect the largest face
            if face_bbox is None:
                face_model_info = await self.model_manager.get_model("face_detection")
                face_detections = await self._detect_faces(
                    face_model_info.model, image, min_face_size=20, confidence_threshold=0.5
                )
                
                if not face_detections:
                    raise ValidationError("No faces detected in the image")
                
                # Use the largest face
                face_bbox = max(face_detections, key=lambda x: x["bbox"]["width"] * x["bbox"]["height"])["bbox"]
            
            # Extract face crop
            face_crop = await self._extract_face_crop_from_bbox(image, face_bbox)
            
            # Get face embedding
            embedding = await self._get_face_embedding(face_crop)
            
            # Store in database
            face_id = self._generate_face_id(embedding)
            face_data = {
                "person_id": person_id,
                "face_id": face_id,
                "embedding": embedding,
                "bbox": face_bbox,
                "created_at": time.time()
            }
            
            # Add to in-memory database
            self.face_database[person_id] = face_data
            
            return {
                "person_id": person_id,
                "face_id": face_id,
                "embedding_shape": embedding.shape,
                "bbox": face_bbox,
                "status": "added"
            }
            
        except Exception as e:
            self.logger.log_error("add_known_face", str(e), person_id=person_id)
            raise InferenceError(f"Failed to add known face: {e}")
    
    async def search_similar_faces(
        self,
        query_image: Union[np.ndarray, bytes, str, Path],
        similarity_threshold: float = 0.6,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for similar faces in the database.
        
        Args:
            query_image: Image containing the face to search for
            similarity_threshold: Minimum similarity threshold
            max_results: Maximum number of results to return
            
        Returns:
            List of similar faces with similarity scores
        """
        try:
            # Load image and extract face
            image = await self._load_image(query_image)
            
            # Detect faces
            face_model_info = await self.model_manager.get_model("face_detection")
            face_detections = await self._detect_faces(
                face_model_info.model, image, min_face_size=20, confidence_threshold=0.5
            )
            
            if not face_detections:
                return []
            
            # Use the largest face
            largest_face = max(face_detections, key=lambda x: x["bbox"]["width"] * x["bbox"]["height"])
            face_crop = await self._extract_face_crop(image, largest_face)
            
            # Get query embedding
            query_embedding = await self._get_face_embedding(face_crop)
            
            # Search in database
            similar_faces = []
            for person_id, face_data in self.face_database.items():
                distance = np.linalg.norm(query_embedding - face_data["embedding"])
                similarity = 1.0 - distance  # Convert distance to similarity
                
                if similarity >= similarity_threshold:
                    similar_faces.append({
                        "person_id": person_id,
                        "face_id": face_data["face_id"],
                        "similarity": similarity,
                        "distance": distance,
                        "bbox": face_data["bbox"]
                    })
            
            # Sort by similarity and limit results
            similar_faces.sort(key=lambda x: x["similarity"], reverse=True)
            return similar_faces[:max_results]
            
        except Exception as e:
            self.logger.log_error("search_similar_faces", str(e))
            raise InferenceError(f"Face search failed: {e}")
    
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
    
    async def _detect_faces(
        self,
        model,
        image: np.ndarray,
        min_face_size: int,
        confidence_threshold: float
    ) -> List[Dict[str, Any]]:
        """Detect faces in image."""
        faces = []
        
        # Check model type
        if hasattr(model, 'detect_faces'):
            # MTCNN model
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            results = model.detect_faces(rgb_image, min_face_size=min_face_size)
            
            for result in results:
                if result['confidence'] >= confidence_threshold:
                    x, y, w, h = result['box']
                    faces.append({
                        "confidence": result['confidence'],
                        "bbox": {
                            "x": x, "y": y, "width": w, "height": h,
                            "x1": x, "y1": y, "x2": x + w, "y2": y + h
                        },
                        "landmarks": result.get('keypoints', {})
                    })
        else:
            # OpenCV Haar cascade
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            faces_detected = model.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)
            
            for (x, y, w, h) in faces_detected:
                faces.append({
                    "confidence": 1.0,  # Haar cascades don't provide confidence
                    "bbox": {
                        "x": x, "y": y, "width": w, "height": h,
                        "x1": x, "y1": y, "x2": x + w, "y2": y + h
                    }
                })
        
        return faces
    
    async def _extract_face_crop(self, image: np.ndarray, detection: Dict[str, Any]) -> np.ndarray:
        """Extract face crop from detection."""
        bbox = detection["bbox"]
        x1, y1, x2, y2 = int(bbox["x1"]), int(bbox["y1"]), int(bbox["x2"]), int(bbox["y2"])
        
        # Add padding
        padding = 20
        x1 = max(0, x1 - padding)
        y1 = max(0, y1 - padding)
        x2 = min(image.shape[1], x2 + padding)
        y2 = min(image.shape[0], y2 + padding)
        
        face_crop = image[y1:y2, x1:x2]
        
        # Resize to standard size
        face_crop = cv2.resize(face_crop, (160, 160))
        
        return face_crop
    
    async def _extract_face_crop_from_bbox(self, image: np.ndarray, bbox: Dict[str, float]) -> np.ndarray:
        """Extract face crop from bounding box."""
        x1, y1 = int(bbox["x1"]), int(bbox["y1"])
        x2, y2 = int(bbox["x2"]), int(bbox["y2"])
        
        # Add padding
        padding = 20
        x1 = max(0, x1 - padding)
        y1 = max(0, y1 - padding)
        x2 = min(image.shape[1], x2 + padding)
        y2 = min(image.shape[0], y2 + padding)
        
        face_crop = image[y1:y2, x1:x2]
        
        # Resize to standard size
        face_crop = cv2.resize(face_crop, (160, 160))
        
        return face_crop
    
    async def _get_face_embedding(self, face_crop: np.ndarray) -> np.ndarray:
        """Get face embedding using a simple approach."""
        # This is a simplified embedding - in production, use proper face embedding models
        # like FaceNet, ArcFace, or similar
        
        # Convert to grayscale and normalize
        gray = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)
        normalized = gray.astype(np.float32) / 255.0
        
        # Create a simple embedding using histogram and texture features
        # Histogram features
        hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
        hist = hist.flatten() / hist.sum()  # Normalize
        
        # LBP (Local Binary Pattern) features
        lbp = self._calculate_lbp(gray)
        lbp_hist = cv2.calcHist([lbp], [0], None, [256], [0, 256])
        lbp_hist = lbp_hist.flatten() / lbp_hist.sum()  # Normalize
        
        # Combine features
        embedding = np.concatenate([hist, lbp_hist])
        
        return embedding
    
    def _calculate_lbp(self, image: np.ndarray, radius: int = 3, n_points: int = 24) -> np.ndarray:
        """Calculate Local Binary Pattern features."""
        # Simple LBP implementation
        lbp = np.zeros_like(image, dtype=np.uint8)
        
        for i in range(radius, image.shape[0] - radius):
            for j in range(radius, image.shape[1] - radius):
                center = image[i, j]
                binary_string = ""
                
                # Sample points around the center
                for k in range(n_points):
                    angle = 2 * np.pi * k / n_points
                    x = i + int(radius * np.cos(angle))
                    y = j + int(radius * np.sin(angle))
                    
                    if 0 <= x < image.shape[0] and 0 <= y < image.shape[1]:
                        binary_string += "1" if image[x, y] >= center else "0"
                    else:
                        binary_string += "0"
                
                lbp[i, j] = int(binary_string, 2) if binary_string else 0
        
        return lbp
    
    async def _recognize_face(
        self,
        embedding: np.ndarray,
        known_faces: Dict[str, np.ndarray],
        distance_threshold: float
    ) -> Optional[Dict[str, Any]]:
        """Recognize face against known faces."""
        best_match = None
        min_distance = float('inf')
        
        for person_id, known_embedding in known_faces.items():
            distance = np.linalg.norm(embedding - known_embedding)
            
            if distance < min_distance and distance <= distance_threshold:
                min_distance = distance
                best_match = {
                    "person_id": person_id,
                    "distance": distance,
                    "confidence": 1.0 - distance  # Convert to confidence
                }
        
        return best_match
    
    def _generate_face_id(self, embedding: np.ndarray) -> str:
        """Generate unique face ID from embedding."""
        embedding_bytes = embedding.tobytes()
        return hashlib.md5(embedding_bytes).hexdigest()
    
    def _encode_face_crop(self, face_crop: np.ndarray) -> str:
        """Encode face crop to base64."""
        _, buffer = cv2.imencode('.jpg', face_crop)
        crop_base64 = base64.b64encode(buffer).decode('utf-8')
        return crop_base64
    
    async def _log_to_database(
        self,
        asset_id: str,
        response: Dict[str, Any],
        faces: List[Dict[str, Any]]
    ) -> None:
        """Log facial recognition results to database."""
        try:
            async with get_db_session() as session:
                # Create processing job
                job = MLProcessingJob(
                    asset_id=uuid.UUID(asset_id),
                    job_type="facial_recognition",
                    status="completed",
                    input_data={
                        "confidence_threshold": response["confidence_threshold"],
                        "distance_threshold": response["distance_threshold"],
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
                
                # Create result records for each face
                for face in faces:
                    detection = face["detection"]
                    recognition = face.get("recognition")
                    
                    result = MLProcessingResult(
                        job_id=job.id,
                        result_type="facial_recognition",
                        result_data=face,
                        confidence=detection["confidence"],
                        bbox_x=detection["bbox"]["x"],
                        bbox_y=detection["bbox"]["y"],
                        bbox_width=detection["bbox"]["width"],
                        bbox_height=detection["bbox"]["height"],
                        metadata={
                            "face_id": face["face_id"],
                            "person_id": recognition["person_id"] if recognition else None,
                            "recognition_confidence": recognition["confidence"] if recognition else None,
                            "recognition_distance": recognition["distance"] if recognition else None
                        }
                    )
                    session.add(result)
                
                await session.commit()
                
        except Exception as e:
            self.logger.log_error("database_logging", str(e), asset_id=asset_id)
    
    async def get_face_database_info(self) -> Dict[str, Any]:
        """Get information about the face database."""
        return {
            "total_faces": len(self.face_database),
            "persons": list(self.face_database.keys()),
            "database_size": len(self.face_database)
        }
    
    async def remove_known_face(self, person_id: str) -> bool:
        """Remove a known face from the database."""
        if person_id in self.face_database:
            del self.face_database[person_id]
            return True
        return False
    
    async def get_model_info(self) -> Dict[str, Any]:
        """Get facial recognition model information."""
        try:
            model_info = await self.model_manager.get_model("face_detection")
            return {
                "name": model_info.name,
                "type": model_info.model_type,
                "metadata": model_info.metadata,
                "face_database_size": len(self.face_database)
            }
        except Exception as e:
            self.logger.log_error("get_model_info", str(e))
            return {}