"""
Auto-Tagging Service

Provides intelligent content analysis and automatic tagging using multiple AI models:
- Object detection for images and videos
- Scene classification and analysis
- Content moderation and safety detection
- OCR and text recognition
- Audio classification
- Custom tag extraction
"""

import asyncio
from typing import Dict, List, Optional, Tuple, Set, Any
from datetime import datetime
from pathlib import Path
import tempfile
import json
from sqlalchemy.ext.asyncio import AsyncSession
from aioredis import Redis
import structlog
import numpy as np
import cv2
from PIL import Image
import torch
from transformers import pipeline, AutoModel, AutoTokenizer
import whisper
from ultralytics import YOLO
import easyocr

from ..core.config import settings
from ..models.schemas import (
    AutoTag, TagCategory, TagSource, TagConfidence,
    ContentModerationResult, OCRResult, AudioClassificationResult
)
from ..db.models import AutoTagModel, ContentModerationModel
from ..utils.metrics import ai_metrics
from ..utils.image_utils import ImageProcessor
from ..utils.audio_utils import AudioProcessor


logger = structlog.get_logger()


class AutoTagger:
    """Advanced auto-tagging service with multiple AI models"""
    
    def __init__(self, db: AsyncSession, redis: Redis):
        self.db = db
        self.redis = redis
        self.image_processor = ImageProcessor()
        self.audio_processor = AudioProcessor()
        
        # AI Models
        self.object_detection_model = None
        self.scene_classification_model = None
        self.content_moderation_model = None
        self.ocr_reader = None
        self.whisper_model = None
        self.custom_models = {}
        
        # Classification categories
        self.scene_categories = [
            "indoor", "outdoor", "nature", "urban", "landscape", "portrait",
            "sports", "music", "food", "technology", "animals", "vehicles",
            "architecture", "art", "business", "education", "entertainment",
            "news", "documentary", "commercial", "social", "travel"
        ]
        
        self.object_categories = [
            "person", "animal", "vehicle", "furniture", "electronics", "clothing",
            "food", "building", "plant", "tool", "appliance", "artwork",
            "document", "book", "computer", "phone", "instrument", "toy"
        ]
    
    async def initialize(self):
        """Initialize auto-tagger with AI models"""
        logger.info("Initializing auto-tagger service")
        
        # Load models
        await self._load_models()
        
        # Schedule periodic model updates
        asyncio.create_task(self._periodic_model_update())
    
    async def analyze_and_tag_asset(
        self,
        asset_id: str,
        file_path: str,
        asset_type: str,
        options: Optional[Dict] = None
    ) -> List[AutoTag]:
        """Analyze asset and generate comprehensive tags"""
        logger.info(
            "Starting auto-tagging analysis",
            asset_id=asset_id,
            asset_type=asset_type
        )
        
        start_time = datetime.utcnow()
        all_tags = []
        
        try:
            # Perform different analysis based on asset type
            if asset_type.startswith('image'):
                all_tags.extend(await self._analyze_image(file_path, asset_id))
            elif asset_type.startswith('video'):
                all_tags.extend(await self._analyze_video(file_path, asset_id))
            elif asset_type.startswith('audio'):
                all_tags.extend(await self._analyze_audio(file_path, asset_id))
            elif asset_type.startswith('document'):
                all_tags.extend(await self._analyze_document(file_path, asset_id))
            else:
                # Generic file analysis
                all_tags.extend(await self._analyze_generic_file(file_path, asset_id))
            
            # Add contextual tags based on metadata
            if options and 'metadata' in options:
                all_tags.extend(await self._extract_contextual_tags(
                    options['metadata'], asset_id
                ))
            
            # Filter and deduplicate tags
            filtered_tags = await self._filter_and_rank_tags(all_tags)
            
            # Store tags in database
            await self._store_tags(filtered_tags)
            
            # Update metrics
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            ai_metrics.auto_tagging_requests.inc()
            ai_metrics.auto_tagging_time.observe(processing_time)
            ai_metrics.tags_generated.labels(
                asset_type=asset_type
            ).inc(len(filtered_tags))
            
            logger.info(
                "Auto-tagging completed",
                asset_id=asset_id,
                tags_count=len(filtered_tags),
                processing_time=processing_time
            )
            
            return filtered_tags
            
        except Exception as e:
            logger.error("Error in auto-tagging", asset_id=asset_id, error=str(e))
            ai_metrics.auto_tagging_errors.inc()
            raise
    
    async def _analyze_image(self, file_path: str, asset_id: str) -> List[AutoTag]:
        """Comprehensive image analysis"""
        tags = []
        
        # Load image
        image = cv2.imread(file_path)
        if image is None:
            logger.warning("Could not load image", file_path=file_path)
            return tags
        
        # Object detection
        if self.object_detection_model:
            object_tags = await self._detect_objects_in_image(image, asset_id)
            tags.extend(object_tags)
        
        # Scene classification
        scene_tags = await self._classify_image_scene(image, asset_id)
        tags.extend(scene_tags)
        
        # OCR text extraction
        if self.ocr_reader:
            ocr_tags = await self._extract_text_from_image(image, asset_id)
            tags.extend(ocr_tags)
        
        # Color analysis
        color_tags = await self._analyze_image_colors(image, asset_id)
        tags.extend(color_tags)
        
        # Composition analysis
        composition_tags = await self._analyze_image_composition(image, asset_id)
        tags.extend(composition_tags)
        
        # Content moderation
        if self.content_moderation_model:
            moderation_tags = await self._moderate_image_content(image, asset_id)
            tags.extend(moderation_tags)
        
        # Technical metadata tags
        technical_tags = await self._extract_image_technical_tags(file_path, asset_id)
        tags.extend(technical_tags)
        
        return tags
    
    async def _analyze_video(self, file_path: str, asset_id: str) -> List[AutoTag]:
        """Comprehensive video analysis"""
        tags = []
        
        # Open video
        cap = cv2.VideoCapture(file_path)
        if not cap.isOpened():
            logger.warning("Could not open video", file_path=file_path)
            return tags
        
        # Get video properties
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = frame_count / fps if fps > 0 else 0
        
        # Sample frames for analysis (every 10% of video)
        sample_frames = []
        sample_indices = [int(i * frame_count / 10) for i in range(10)]
        
        for frame_idx in sample_indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            if ret:
                sample_frames.append(frame)
        
        cap.release()
        
        # Analyze sample frames
        for i, frame in enumerate(sample_frames):
            # Object detection
            if self.object_detection_model:
                object_tags = await self._detect_objects_in_image(frame, asset_id)
                # Add temporal information
                for tag in object_tags:
                    tag.metadata['frame_sample'] = i
                    tag.metadata['timestamp'] = (i * duration / 10) if duration > 0 else 0
                tags.extend(object_tags)
            
            # Scene classification
            scene_tags = await self._classify_image_scene(frame, asset_id)
            for tag in scene_tags:
                tag.metadata['frame_sample'] = i
            tags.extend(scene_tags)
        
        # Audio analysis
        audio_tags = await self._analyze_video_audio(file_path, asset_id)
        tags.extend(audio_tags)
        
        # Motion analysis
        motion_tags = await self._analyze_video_motion(file_path, asset_id)
        tags.extend(motion_tags)
        
        # Technical metadata
        technical_tags = await self._extract_video_technical_tags(file_path, asset_id)
        tags.extend(technical_tags)
        
        return tags
    
    async def _analyze_audio(self, file_path: str, asset_id: str) -> List[AutoTag]:
        """Comprehensive audio analysis"""
        tags = []
        
        # Audio classification
        classification_tags = await self._classify_audio_content(file_path, asset_id)
        tags.extend(classification_tags)
        
        # Speech detection and transcription
        if self.whisper_model:
            speech_tags = await self._analyze_audio_speech(file_path, asset_id)
            tags.extend(speech_tags)
        
        # Music analysis
        music_tags = await self._analyze_audio_music(file_path, asset_id)
        tags.extend(music_tags)
        
        # Technical analysis
        technical_tags = await self._extract_audio_technical_tags(file_path, asset_id)
        tags.extend(technical_tags)
        
        return tags
    
    async def _analyze_document(self, file_path: str, asset_id: str) -> List[AutoTag]:
        """Document analysis"""
        tags = []
        
        # Convert document to images for OCR
        if file_path.lower().endswith('.pdf'):
            text_content = await self._extract_pdf_text(file_path)
        else:
            text_content = await self._extract_text_file_content(file_path)
        
        if text_content:
            # Text analysis
            text_tags = await self._analyze_text_content(text_content, asset_id)
            tags.extend(text_tags)
            
            # Language detection
            language_tags = await self._detect_text_language(text_content, asset_id)
            tags.extend(language_tags)
            
            # Entity extraction
            entity_tags = await self._extract_text_entities(text_content, asset_id)
            tags.extend(entity_tags)
        
        return tags
    
    async def _analyze_generic_file(self, file_path: str, asset_id: str) -> List[AutoTag]:
        """Generic file analysis"""
        tags = []
        
        # File extension and type tags
        file_ext = Path(file_path).suffix.lower()
        if file_ext:
            tags.append(AutoTag(
                asset_id=asset_id,
                tag_name=f"file_type_{file_ext[1:]}",
                category=TagCategory.TECHNICAL,
                confidence=1.0,
                source=TagSource.SYSTEM,
                metadata={'file_extension': file_ext}
            ))
        
        # File size analysis
        try:
            file_size = Path(file_path).stat().st_size
            size_category = self._categorize_file_size(file_size)
            tags.append(AutoTag(
                asset_id=asset_id,
                tag_name=f"size_{size_category}",
                category=TagCategory.TECHNICAL,
                confidence=1.0,
                source=TagSource.SYSTEM,
                metadata={'file_size_bytes': file_size}
            ))
        except OSError:
            pass
        
        return tags
    
    async def _detect_objects_in_image(self, image: np.ndarray, asset_id: str) -> List[AutoTag]:
        """Detect objects using YOLO model"""
        tags = []
        
        try:
            # Run object detection
            results = self.object_detection_model(image)
            
            for result in results:
                boxes = result.boxes
                if boxes is not None:
                    for box in boxes:
                        # Get class name and confidence
                        class_id = int(box.cls[0])
                        confidence = float(box.conf[0])
                        class_name = self.object_detection_model.names[class_id]
                        
                        # Filter by confidence threshold
                        if confidence >= settings.AUTO_TAGGING_CONFIDENCE_THRESHOLD:
                            # Get bounding box coordinates
                            x1, y1, x2, y2 = box.xyxy[0].tolist()
                            
                            tag = AutoTag(
                                asset_id=asset_id,
                                tag_name=class_name,
                                category=TagCategory.OBJECT,
                                confidence=confidence,
                                source=TagSource.YOLO,
                                metadata={
                                    'bbox': [x1, y1, x2, y2],
                                    'area': (x2 - x1) * (y2 - y1),
                                    'model_version': getattr(self.object_detection_model, 'version', 'unknown')
                                }
                            )
                            tags.append(tag)
            
        except Exception as e:
            logger.error("Error in object detection", error=str(e))
        
        return tags
    
    async def _classify_image_scene(self, image: np.ndarray, asset_id: str) -> List[AutoTag]:
        """Classify image scene"""
        tags = []
        
        try:
            if self.scene_classification_model:
                # Preprocess image for scene classification
                image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                pil_image = Image.fromarray(image_rgb)
                
                # Get predictions
                predictions = self.scene_classification_model(pil_image)
                
                for prediction in predictions:
                    if prediction['score'] >= settings.AUTO_TAGGING_CONFIDENCE_THRESHOLD:
                        tag = AutoTag(
                            asset_id=asset_id,
                            tag_name=prediction['label'],
                            category=TagCategory.SCENE,
                            confidence=prediction['score'],
                            source=TagSource.HUGGINGFACE,
                            metadata={
                                'model_name': 'scene_classification',
                                'all_predictions': predictions[:5]  # Top 5
                            }
                        )
                        tags.append(tag)
            
            # Rule-based scene detection
            rule_based_tags = await self._rule_based_scene_detection(image, asset_id)
            tags.extend(rule_based_tags)
            
        except Exception as e:
            logger.error("Error in scene classification", error=str(e))
        
        return tags
    
    async def _extract_text_from_image(self, image: np.ndarray, asset_id: str) -> List[AutoTag]:
        """Extract text using OCR"""
        tags = []
        
        try:
            # Use EasyOCR
            results = self.ocr_reader.readtext(image)
            
            extracted_texts = []
            for (bbox, text, confidence) in results:
                if confidence >= 0.5:  # OCR confidence threshold
                    extracted_texts.append(text.strip())
            
            if extracted_texts:
                # Create text content tag
                full_text = " ".join(extracted_texts)
                tag = AutoTag(
                    asset_id=asset_id,
                    tag_name="contains_text",
                    category=TagCategory.CONTENT,
                    confidence=0.9,
                    source=TagSource.OCR,
                    metadata={
                        'extracted_text': full_text[:500],  # Limit text length
                        'text_count': len(extracted_texts),
                        'avg_confidence': np.mean([conf for _, _, conf in results])
                    }
                )
                tags.append(tag)
                
                # Analyze extracted text for keywords
                text_analysis_tags = await self._analyze_extracted_text(full_text, asset_id)
                tags.extend(text_analysis_tags)
            
        except Exception as e:
            logger.error("Error in OCR", error=str(e))
        
        return tags
    
    async def _analyze_image_colors(self, image: np.ndarray, asset_id: str) -> List[AutoTag]:
        """Analyze image colors"""
        tags = []
        
        try:
            # Convert to RGB
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Calculate dominant colors
            pixels = image_rgb.reshape(-1, 3)
            from sklearn.cluster import KMeans
            
            # Get 5 dominant colors
            kmeans = KMeans(n_clusters=5, random_state=42, n_init=10)
            kmeans.fit(pixels)
            
            colors = kmeans.cluster_centers_.astype(int)
            percentages = np.bincount(kmeans.labels_) / len(kmeans.labels_)
            
            # Color categories
            for i, (color, percentage) in enumerate(zip(colors, percentages)):
                if percentage > 0.1:  # At least 10% of image
                    color_name = self._rgb_to_color_name(color)
                    
                    tag = AutoTag(
                        asset_id=asset_id,
                        tag_name=f"color_{color_name}",
                        category=TagCategory.VISUAL,
                        confidence=float(percentage),
                        source=TagSource.ANALYSIS,
                        metadata={
                            'rgb': color.tolist(),
                            'percentage': float(percentage),
                            'dominant_rank': i + 1
                        }
                    )
                    tags.append(tag)
            
            # Overall color temperature
            avg_color = np.mean(pixels, axis=0)
            temperature = self._calculate_color_temperature(avg_color)
            
            temp_tag = AutoTag(
                asset_id=asset_id,
                tag_name=f"temperature_{temperature}",
                category=TagCategory.VISUAL,
                confidence=0.8,
                source=TagSource.ANALYSIS,
                metadata={'avg_rgb': avg_color.tolist()}
            )
            tags.append(temp_tag)
            
        except Exception as e:
            logger.error("Error in color analysis", error=str(e))
        
        return tags
    
    async def _analyze_image_composition(self, image: np.ndarray, asset_id: str) -> List[AutoTag]:
        """Analyze image composition"""
        tags = []
        
        try:
            height, width = image.shape[:2]
            
            # Aspect ratio
            aspect_ratio = width / height
            aspect_category = self._categorize_aspect_ratio(aspect_ratio)
            
            tags.append(AutoTag(
                asset_id=asset_id,
                tag_name=f"aspect_{aspect_category}",
                category=TagCategory.TECHNICAL,
                confidence=1.0,
                source=TagSource.ANALYSIS,
                metadata={'aspect_ratio': aspect_ratio}
            ))
            
            # Resolution category
            total_pixels = width * height
            resolution_category = self._categorize_resolution(total_pixels)
            
            tags.append(AutoTag(
                asset_id=asset_id,
                tag_name=f"resolution_{resolution_category}",
                category=TagCategory.TECHNICAL,
                confidence=1.0,
                source=TagSource.ANALYSIS,
                metadata={
                    'width': width,
                    'height': height,
                    'total_pixels': total_pixels
                }
            ))
            
            # Brightness analysis
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            avg_brightness = np.mean(gray)
            brightness_category = self._categorize_brightness(avg_brightness)
            
            tags.append(AutoTag(
                asset_id=asset_id,
                tag_name=f"brightness_{brightness_category}",
                category=TagCategory.VISUAL,
                confidence=0.9,
                source=TagSource.ANALYSIS,
                metadata={'avg_brightness': float(avg_brightness)}
            ))
            
            # Contrast analysis
            contrast = np.std(gray)
            contrast_category = self._categorize_contrast(contrast)
            
            tags.append(AutoTag(
                asset_id=asset_id,
                tag_name=f"contrast_{contrast_category}",
                category=TagCategory.VISUAL,
                confidence=0.9,
                source=TagSource.ANALYSIS,
                metadata={'contrast_std': float(contrast)}
            ))
            
        except Exception as e:
            logger.error("Error in composition analysis", error=str(e))
        
        return tags
    
    async def _moderate_image_content(self, image: np.ndarray, asset_id: str) -> List[AutoTag]:
        """Content moderation and safety detection"""
        tags = []
        
        try:
            if self.content_moderation_model:
                # Convert image for moderation model
                image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                pil_image = Image.fromarray(image_rgb)
                
                # Get moderation results
                results = self.content_moderation_model(pil_image)
                
                for result in results:
                    if result['score'] > 0.1:  # Low threshold for safety
                        tag = AutoTag(
                            asset_id=asset_id,
                            tag_name=f"content_{result['label']}",
                            category=TagCategory.MODERATION,
                            confidence=result['score'],
                            source=TagSource.MODERATION,
                            metadata={
                                'moderation_type': result['label'],
                                'risk_level': self._categorize_risk_level(result['score'])
                            }
                        )
                        tags.append(tag)
                
                # Store moderation result
                await self._store_moderation_result(asset_id, results)
        
        except Exception as e:
            logger.error("Error in content moderation", error=str(e))
        
        return tags
    
    async def _extract_contextual_tags(self, metadata: Dict, asset_id: str) -> List[AutoTag]:
        """Extract tags from metadata context"""
        tags = []
        
        # Location tags
        if 'location' in metadata or 'gps' in metadata:
            location_tag = AutoTag(
                asset_id=asset_id,
                tag_name="has_location",
                category=TagCategory.CONTEXT,
                confidence=1.0,
                source=TagSource.METADATA,
                metadata={'location_data': metadata.get('location', metadata.get('gps'))}
            )
            tags.append(location_tag)
        
        # Time-based tags
        if 'date_taken' in metadata or 'creation_date' in metadata:
            date_str = metadata.get('date_taken', metadata.get('creation_date'))
            if date_str:
                time_tags = await self._extract_time_based_tags(date_str, asset_id)
                tags.extend(time_tags)
        
        # Camera/device tags
        if 'camera_model' in metadata or 'device' in metadata:
            device = metadata.get('camera_model', metadata.get('device'))
            device_tag = AutoTag(
                asset_id=asset_id,
                tag_name=f"device_{device.lower().replace(' ', '_')}",
                category=TagCategory.TECHNICAL,
                confidence=1.0,
                source=TagSource.METADATA,
                metadata={'device_info': device}
            )
            tags.append(device_tag)
        
        return tags
    
    async def _filter_and_rank_tags(self, tags: List[AutoTag]) -> List[AutoTag]:
        """Filter, deduplicate and rank tags"""
        if not tags:
            return []
        
        # Group by tag name
        tag_groups = {}
        for tag in tags:
            key = f"{tag.tag_name}_{tag.category}"
            if key not in tag_groups:
                tag_groups[key] = []
            tag_groups[key].append(tag)
        
        # Merge duplicates and take highest confidence
        merged_tags = []
        for group in tag_groups.values():
            if len(group) == 1:
                merged_tags.append(group[0])
            else:
                # Merge multiple tags with same name
                best_tag = max(group, key=lambda t: t.confidence)
                
                # Combine metadata
                combined_metadata = {}
                for tag in group:
                    combined_metadata.update(tag.metadata)
                best_tag.metadata = combined_metadata
                
                # Average confidence if from same source
                if all(t.source == best_tag.source for t in group):
                    best_tag.confidence = np.mean([t.confidence for t in group])
                
                merged_tags.append(best_tag)
        
        # Filter by confidence threshold
        filtered_tags = [
            tag for tag in merged_tags 
            if tag.confidence >= settings.AUTO_TAGGING_CONFIDENCE_THRESHOLD
        ]
        
        # Sort by confidence
        filtered_tags.sort(key=lambda t: t.confidence, reverse=True)
        
        # Limit number of tags
        max_tags = getattr(settings, 'MAX_AUTO_TAGS_PER_ASSET', 50)
        return filtered_tags[:max_tags]
    
    async def _store_tags(self, tags: List[AutoTag]):
        """Store tags in database"""
        for tag in tags:
            db_tag = AutoTagModel(
                asset_id=tag.asset_id,
                tag_name=tag.tag_name,
                category=tag.category,
                confidence=tag.confidence,
                source=tag.source,
                metadata=tag.metadata,
                created_at=datetime.utcnow()
            )
            self.db.add(db_tag)
        
        await self.db.commit()
    
    async def _store_moderation_result(self, asset_id: str, results: List[Dict]):
        """Store content moderation results"""
        moderation_result = ContentModerationModel(
            asset_id=asset_id,
            results=results,
            overall_score=max([r['score'] for r in results]) if results else 0.0,
            flagged=any(r['score'] > 0.8 for r in results),
            reviewed=False,
            created_at=datetime.utcnow()
        )
        
        self.db.add(moderation_result)
        await self.db.commit()
    
    # Helper methods for categorization
    def _rgb_to_color_name(self, rgb: np.ndarray) -> str:
        """Convert RGB to color name"""
        r, g, b = rgb
        
        if r > 200 and g > 200 and b > 200:
            return "white"
        elif r < 50 and g < 50 and b < 50:
            return "black"
        elif r > g and r > b:
            return "red"
        elif g > r and g > b:
            return "green"
        elif b > r and b > g:
            return "blue"
        elif r > 150 and g > 150:
            return "yellow"
        elif r > 150 and b > 150:
            return "magenta"
        elif g > 150 and b > 150:
            return "cyan"
        elif r > 100 and g > 50 and b < 50:
            return "orange"
        elif r > 100 and g < 100 and b > 100:
            return "purple"
        else:
            return "mixed"
    
    def _calculate_color_temperature(self, avg_color: np.ndarray) -> str:
        """Calculate color temperature"""
        r, g, b = avg_color
        
        if b > r and b > g:
            return "cool"
        elif r > b and r > g:
            return "warm"
        else:
            return "neutral"
    
    def _categorize_aspect_ratio(self, ratio: float) -> str:
        """Categorize aspect ratio"""
        if ratio > 2.0:
            return "ultra_wide"
        elif ratio > 1.5:
            return "wide"
        elif ratio > 1.1:
            return "landscape"
        elif ratio > 0.9:
            return "square"
        else:
            return "portrait"
    
    def _categorize_resolution(self, pixels: int) -> str:
        """Categorize resolution"""
        if pixels > 8000000:  # > 8MP
            return "high"
        elif pixels > 2000000:  # > 2MP
            return "medium"
        else:
            return "low"
    
    def _categorize_brightness(self, brightness: float) -> str:
        """Categorize brightness"""
        if brightness > 200:
            return "bright"
        elif brightness > 100:
            return "normal"
        else:
            return "dark"
    
    def _categorize_contrast(self, contrast: float) -> str:
        """Categorize contrast"""
        if contrast > 80:
            return "high"
        elif contrast > 40:
            return "medium"
        else:
            return "low"
    
    def _categorize_file_size(self, size_bytes: int) -> str:
        """Categorize file size"""
        mb = size_bytes / (1024 * 1024)
        
        if mb > 1000:
            return "very_large"
        elif mb > 100:
            return "large"
        elif mb > 10:
            return "medium"
        else:
            return "small"
    
    def _categorize_risk_level(self, score: float) -> str:
        """Categorize moderation risk level"""
        if score > 0.8:
            return "high"
        elif score > 0.5:
            return "medium"
        else:
            return "low"
    
    async def _load_models(self):
        """Load AI models for auto-tagging"""
        logger.info("Loading auto-tagging models")
        
        try:
            # Object Detection (YOLO)
            if settings.AUTO_TAGGING_ENABLED:
                self.object_detection_model = YOLO('yolov8n.pt')
                logger.info("Loaded YOLO object detection model")
            
            # Scene Classification
            self.scene_classification_model = pipeline(
                "image-classification",
                model="google/vit-base-patch16-224",
                return_top_k=5
            )
            logger.info("Loaded scene classification model")
            
            # Content Moderation
            self.content_moderation_model = pipeline(
                "image-classification",
                model="Falconsai/nsfw_image_detection",
                return_top_k=3
            )
            logger.info("Loaded content moderation model")
            
            # OCR
            self.ocr_reader = easyocr.Reader(['en', 'es', 'fr', 'de'])
            logger.info("Loaded OCR model")
            
            # Whisper for audio
            if settings.ENABLE_TRANSCRIPTION:
                self.whisper_model = whisper.load_model("base")
                logger.info("Loaded Whisper transcription model")
            
        except Exception as e:
            logger.error("Error loading models", error=str(e))
            # Continue without models - will use fallback methods
    
    async def _periodic_model_update(self):
        """Periodically update models"""
        while True:
            try:
                await asyncio.sleep(24 * 3600)  # Daily
                logger.info("Checking for model updates")
                # In production, implement model update logic
                
            except Exception as e:
                logger.error("Error in periodic model update", error=str(e))
    
    # Placeholder methods for additional analysis
    async def _analyze_video_audio(self, file_path: str, asset_id: str) -> List[AutoTag]:
        """Analyze audio track of video"""
        # Implementation would extract audio and analyze
        return []
    
    async def _analyze_video_motion(self, file_path: str, asset_id: str) -> List[AutoTag]:
        """Analyze motion in video"""
        # Implementation would analyze motion patterns
        return []
    
    async def _extract_video_technical_tags(self, file_path: str, asset_id: str) -> List[AutoTag]:
        """Extract technical video tags"""
        # Implementation would analyze video technical properties
        return []
    
    async def _classify_audio_content(self, file_path: str, asset_id: str) -> List[AutoTag]:
        """Classify audio content"""
        # Implementation would classify audio (speech, music, etc.)
        return []
    
    async def _analyze_audio_speech(self, file_path: str, asset_id: str) -> List[AutoTag]:
        """Analyze speech in audio"""
        # Implementation would use Whisper for speech analysis
        return []
    
    async def _analyze_audio_music(self, file_path: str, asset_id: str) -> List[AutoTag]:
        """Analyze music in audio"""
        # Implementation would analyze musical content
        return []
    
    async def _extract_audio_technical_tags(self, file_path: str, asset_id: str) -> List[AutoTag]:
        """Extract technical audio tags"""
        # Implementation would analyze audio technical properties
        return []
    
    async def _extract_pdf_text(self, file_path: str) -> str:
        """Extract text from PDF"""
        # Implementation would use PDF extraction library
        return ""
    
    async def _extract_text_file_content(self, file_path: str) -> str:
        """Extract content from text file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception:
            return ""
    
    async def _analyze_text_content(self, text: str, asset_id: str) -> List[AutoTag]:
        """Analyze text content"""
        # Implementation would use NLP for text analysis
        return []
    
    async def _detect_text_language(self, text: str, asset_id: str) -> List[AutoTag]:
        """Detect text language"""
        # Implementation would use language detection
        return []
    
    async def _extract_text_entities(self, text: str, asset_id: str) -> List[AutoTag]:
        """Extract named entities from text"""
        # Implementation would use NER
        return []
    
    async def _rule_based_scene_detection(self, image: np.ndarray, asset_id: str) -> List[AutoTag]:
        """Rule-based scene detection"""
        # Simple rule-based scene detection
        return []
    
    async def _analyze_extracted_text(self, text: str, asset_id: str) -> List[AutoTag]:
        """Analyze extracted text for keywords"""
        # Implementation would analyze text for relevant keywords
        return []
    
    async def _extract_time_based_tags(self, date_str: str, asset_id: str) -> List[AutoTag]:
        """Extract time-based contextual tags"""
        # Implementation would analyze date/time for context
        return []
    
    async def _extract_image_technical_tags(self, file_path: str, asset_id: str) -> List[AutoTag]:
        """Extract technical image metadata tags"""
        # Implementation would read EXIF and technical data
        return []