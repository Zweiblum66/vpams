"""
AI Processing Utilities

Handles AI/ML tasks like face detection, object detection, and content analysis.
"""

import asyncio
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import cv2
import numpy as np
import structlog
import json
from datetime import datetime

from ..core.config import settings


logger = structlog.get_logger()


class AIProcessor:
    """Handles AI/ML processing tasks"""
    
    def __init__(self):
        self.models_loaded = False
        self.face_cascade = None
        self.object_detector = None
        self.model_cache_dir = Path(settings.MODEL_CACHE_PATH)
    
    async def initialize(self):
        """Initialize AI processor"""
        logger.info("Initializing AI processor")
        
        # Create model cache directory
        self.model_cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Load models
        await self._load_models()
    
    async def cleanup(self):
        """Cleanup AI processor"""
        pass
    
    async def _load_models(self):
        """Load AI models"""
        try:
            # Load face detection model (Haar Cascade for simplicity)
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            self.face_cascade = cv2.CascadeClassifier(cascade_path)
            
            # In production, load actual models like MTCNN, YOLO, etc.
            # For now, we'll use OpenCV's built-in models
            
            self.models_loaded = True
            logger.info("AI models loaded successfully")
            
        except Exception as e:
            logger.error("Failed to load AI models", error=str(e))
            self.models_loaded = False
    
    async def detect_faces(
        self,
        image_path: Path,
        confidence_threshold: float = 0.5,
        return_visualization: bool = False
    ) -> Dict[str, Any]:
        """Detect faces in image"""
        if not self.models_loaded:
            raise RuntimeError("AI models not loaded")
        
        logger.info("Detecting faces", image_path=str(image_path))
        
        # Read image
        img = cv2.imread(str(image_path))
        if img is None:
            raise ValueError(f"Failed to read image: {image_path}")
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Detect faces
        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30)
        )
        
        # Convert to list of face objects
        face_list = []
        for i, (x, y, w, h) in enumerate(faces):
            face_list.append({
                "id": i,
                "bbox": {
                    "x": int(x),
                    "y": int(y),
                    "width": int(w),
                    "height": int(h)
                },
                "confidence": 0.8  # Haar cascade doesn't provide confidence
            })
        
        result = {
            "faces_detected": len(face_list),
            "faces": face_list,
            "image_size": {
                "width": img.shape[1],
                "height": img.shape[0]
            }
        }
        
        # Create visualization if requested
        if return_visualization:
            viz_img = img.copy()
            for face in face_list:
                bbox = face["bbox"]
                cv2.rectangle(
                    viz_img,
                    (bbox["x"], bbox["y"]),
                    (bbox["x"] + bbox["width"], bbox["y"] + bbox["height"]),
                    (0, 255, 0),
                    2
                )
                cv2.putText(
                    viz_img,
                    f"Face {face['id']}",
                    (bbox["x"], bbox["y"] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (0, 255, 0),
                    1
                )
            
            # Save visualization
            viz_path = image_path.parent / f"{image_path.stem}_faces.jpg"
            cv2.imwrite(str(viz_path), viz_img)
            result["visualization_path"] = viz_path
        
        return result
    
    async def detect_objects(
        self,
        image_path: Path,
        model_name: str = "yolov5",
        confidence_threshold: float = 0.5,
        max_results: int = 10,
        return_visualization: bool = False
    ) -> Dict[str, Any]:
        """Detect objects in image"""
        logger.info("Detecting objects", image_path=str(image_path))
        
        # Read image
        img = cv2.imread(str(image_path))
        if img is None:
            raise ValueError(f"Failed to read image: {image_path}")
        
        # For demo purposes, use simple object detection
        # In production, use YOLO, Detectron2, etc.
        
        # Simulate object detection results
        objects = [
            {
                "id": 0,
                "class": "person",
                "confidence": 0.92,
                "bbox": {
                    "x": 100,
                    "y": 50,
                    "width": 150,
                    "height": 300
                }
            },
            {
                "id": 1,
                "class": "car",
                "confidence": 0.87,
                "bbox": {
                    "x": 300,
                    "y": 200,
                    "width": 200,
                    "height": 150
                }
            }
        ]
        
        # Filter by confidence
        objects = [obj for obj in objects if obj["confidence"] >= confidence_threshold]
        objects = objects[:max_results]
        
        result = {
            "objects_detected": len(objects),
            "objects": objects,
            "model": model_name,
            "image_size": {
                "width": img.shape[1],
                "height": img.shape[0]
            }
        }
        
        # Create visualization if requested
        if return_visualization:
            viz_img = img.copy()
            for obj in objects:
                bbox = obj["bbox"]
                cv2.rectangle(
                    viz_img,
                    (bbox["x"], bbox["y"]),
                    (bbox["x"] + bbox["width"], bbox["y"] + bbox["height"]),
                    (255, 0, 0),
                    2
                )
                label = f"{obj['class']} ({obj['confidence']:.2f})"
                cv2.putText(
                    viz_img,
                    label,
                    (bbox["x"], bbox["y"] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (255, 0, 0),
                    1
                )
            
            # Save visualization
            viz_path = image_path.parent / f"{image_path.stem}_objects.jpg"
            cv2.imwrite(str(viz_path), viz_img)
            result["visualization_path"] = viz_path
        
        return result
    
    async def analyze_scenes(self, video_path: Path) -> Dict[str, Any]:
        """Analyze scenes in video"""
        logger.info("Analyzing scenes", video_path=str(video_path))
        
        # Open video
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise ValueError(f"Failed to open video: {video_path}")
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = frame_count / fps
        
        # Simple scene detection based on histogram differences
        scenes = []
        prev_hist = None
        scene_start = 0
        scene_threshold = 0.5
        
        frame_idx = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Sample every 30 frames (1 second at 30fps)
            if frame_idx % 30 == 0:
                # Calculate histogram
                hist = cv2.calcHist([frame], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
                hist = cv2.normalize(hist, hist).flatten()
                
                if prev_hist is not None:
                    # Calculate histogram difference
                    diff = cv2.compareHist(prev_hist, hist, cv2.HISTCMP_CORREL)
                    
                    # Detect scene change
                    if diff < scene_threshold:
                        scenes.append({
                            "scene_id": len(scenes),
                            "start_time": scene_start,
                            "end_time": frame_idx / fps,
                            "duration": (frame_idx / fps) - scene_start
                        })
                        scene_start = frame_idx / fps
                
                prev_hist = hist
            
            frame_idx += 1
        
        # Add last scene
        if scene_start < duration:
            scenes.append({
                "scene_id": len(scenes),
                "start_time": scene_start,
                "end_time": duration,
                "duration": duration - scene_start
            })
        
        cap.release()
        
        return {
            "total_scenes": len(scenes),
            "scenes": scenes,
            "video_duration": duration,
            "fps": fps,
            "frame_count": frame_count
        }
    
    async def analyze_content(self, media_path: Path) -> Dict[str, Any]:
        """Comprehensive content analysis"""
        logger.info("Analyzing content", media_path=str(media_path))
        
        result = {
            "file_path": str(media_path),
            "analyzed_at": datetime.utcnow().isoformat(),
            "analyses": {}
        }
        
        # Check if image or video
        if media_path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.bmp']:
            # Image analysis
            result["media_type"] = "image"
            
            # Face detection
            try:
                face_result = await self.detect_faces(media_path)
                result["analyses"]["faces"] = face_result
            except Exception as e:
                logger.error("Face detection failed", error=str(e))
            
            # Object detection
            try:
                object_result = await self.detect_objects(media_path)
                result["analyses"]["objects"] = object_result
            except Exception as e:
                logger.error("Object detection failed", error=str(e))
            
            # Image properties
            img = cv2.imread(str(media_path))
            if img is not None:
                result["analyses"]["properties"] = {
                    "width": img.shape[1],
                    "height": img.shape[0],
                    "channels": img.shape[2] if len(img.shape) > 2 else 1,
                    "mean_brightness": float(np.mean(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY))),
                    "dominant_colors": self._get_dominant_colors(img)
                }
        
        elif media_path.suffix.lower() in ['.mp4', '.avi', '.mov', '.mkv']:
            # Video analysis
            result["media_type"] = "video"
            
            # Scene analysis
            try:
                scene_result = await self.analyze_scenes(media_path)
                result["analyses"]["scenes"] = scene_result
            except Exception as e:
                logger.error("Scene analysis failed", error=str(e))
            
            # Extract key frames for analysis
            key_frames = await self._extract_key_frames(media_path)
            
            # Analyze key frames
            if key_frames:
                result["analyses"]["key_frame_analysis"] = []
                for frame_path, timestamp in key_frames:
                    frame_analysis = {
                        "timestamp": timestamp,
                        "faces": await self.detect_faces(frame_path),
                        "objects": await self.detect_objects(frame_path)
                    }
                    result["analyses"]["key_frame_analysis"].append(frame_analysis)
        
        return result
    
    def _get_dominant_colors(self, img: np.ndarray, n_colors: int = 5) -> List[Dict[str, Any]]:
        """Get dominant colors from image"""
        # Reshape image to be a list of pixels
        pixels = img.reshape(-1, 3)
        
        # Simple color quantization using k-means
        from sklearn.cluster import KMeans
        
        kmeans = KMeans(n_clusters=n_colors, random_state=42)
        kmeans.fit(pixels)
        
        colors = []
        for i, color in enumerate(kmeans.cluster_centers_):
            colors.append({
                "color": color.astype(int).tolist(),
                "hex": "#{:02x}{:02x}{:02x}".format(int(color[2]), int(color[1]), int(color[0])),
                "percentage": float(np.sum(kmeans.labels_ == i) / len(pixels))
            })
        
        return sorted(colors, key=lambda x: x["percentage"], reverse=True)
    
    async def _extract_key_frames(self, video_path: Path, n_frames: int = 5) -> List[Tuple[Path, float]]:
        """Extract key frames from video"""
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            return []
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = frame_count / fps
        
        # Extract frames at regular intervals
        interval = duration / n_frames
        key_frames = []
        
        for i in range(n_frames):
            timestamp = i * interval
            frame_idx = int(timestamp * fps)
            
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            
            if ret:
                frame_path = video_path.parent / f"{video_path.stem}_frame_{i}.jpg"
                cv2.imwrite(str(frame_path), frame)
                key_frames.append((frame_path, timestamp))
        
        cap.release()
        return key_frames