"""
API routes for AI/ML Service
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio
import structlog

from ..core.config import settings
from ..core.exceptions import InferenceError, ValidationError, ProcessingError
from ..db.base import get_db
from ..services.ml_service import MLService
from ..services.model_manager import ModelManager

logger = structlog.get_logger(__name__)

router = APIRouter()


async def get_ml_service() -> MLService:
    """Dependency to get ML service instance."""
    from ..main import app
    return app.state.ml_service


async def get_model_manager() -> ModelManager:
    """Dependency to get model manager instance."""
    from ..main import app
    return app.state.model_manager


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "ai-ml-service",
        "version": settings.VERSION
    }


@router.get("/models")
async def list_models(model_manager: ModelManager = Depends(get_model_manager)):
    """List all available models."""
    try:
        loaded_models = model_manager.list_loaded_models()
        cache_stats = model_manager.get_cache_stats()
        
        available_models = [
            "object_detection",
            "face_detection", 
            "scene_detection",
            "speech_to_text",
            "content_moderation",
            "sentiment_analysis",
            "entity_recognition",
            "language_detection",
            "speaker_diarization",
            "keyword_extraction"
        ]
        
        return {
            "data": {
                "available_models": available_models,
                "loaded_models": loaded_models,
                "cache_stats": cache_stats
            }
        }
    except Exception as e:
        logger.error("Failed to list models", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to list models")


@router.get("/models/{model_name}")
async def get_model_info(
    model_name: str,
    model_manager: ModelManager = Depends(get_model_manager)
):
    """Get information about a specific model."""
    try:
        model_info = model_manager.get_model_info(model_name)
        if not model_info:
            raise HTTPException(status_code=404, detail=f"Model {model_name} not found")
        
        return {"data": model_info}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get model info", model_name=model_name, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get model information")


@router.post("/models/{model_name}/load")
async def load_model(
    model_name: str,
    model_manager: ModelManager = Depends(get_model_manager)
):
    """Load a specific model."""
    try:
        model_info = await model_manager.get_model(model_name)
        return {
            "data": {
                "model_name": model_info.name,
                "model_type": model_info.model_type,
                "loaded": True
            }
        }
    except Exception as e:
        logger.error("Failed to load model", model_name=model_name, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to load model: {e}")


@router.post("/models/{model_name}/unload")
async def unload_model(
    model_name: str,
    model_manager: ModelManager = Depends(get_model_manager)
):
    """Unload a specific model."""
    try:
        success = await model_manager.unload_model(model_name)
        if not success:
            raise HTTPException(status_code=404, detail=f"Model {model_name} not loaded")
        
        return {"data": {"model_name": model_name, "unloaded": True}}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to unload model", model_name=model_name, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to unload model: {e}")


@router.post("/detect/objects")
async def detect_objects(
    file: UploadFile = File(...),
    confidence_threshold: float = Form(0.5),
    iou_threshold: float = Form(0.45),
    max_detections: int = Form(100),
    return_crops: bool = Form(False),
    asset_id: Optional[str] = Form(None),
    ml_service: MLService = Depends(get_ml_service)
):
    """Detect objects in an uploaded image."""
    try:
        # Validate file type
        if not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        # Read image data
        image_data = await file.read()
        
        # Validate file size
        if len(image_data) > settings.MAX_IMAGE_SIZE:
            raise HTTPException(
                status_code=413, 
                detail=f"Image too large. Maximum size: {settings.MAX_IMAGE_SIZE} bytes"
            )
        
        # Get object detection service
        from ..services.object_detection_service import ObjectDetectionService
        from ..main import app
        object_detection_service = ObjectDetectionService(app.state.model_manager)
        
        # Run object detection
        results = await object_detection_service.detect_objects(
            image_data=image_data,
            confidence_threshold=confidence_threshold,
            iou_threshold=iou_threshold,
            max_detections=max_detections,
            return_crops=return_crops,
            asset_id=asset_id
        )
        
        return {"data": results}
    
    except HTTPException:
        raise
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except InferenceError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error("Object detection failed", error=str(e))
        raise HTTPException(status_code=500, detail="Object detection failed")


@router.post("/detect/objects/batch")
async def detect_objects_batch(
    files: List[UploadFile] = File(...),
    confidence_threshold: float = Form(0.5),
    iou_threshold: float = Form(0.45),
    max_detections: int = Form(100),
    return_crops: bool = Form(False),
    asset_ids: Optional[str] = Form(None),
    ml_service: MLService = Depends(get_ml_service)
):
    """Detect objects in a batch of uploaded images."""
    try:
        # Validate batch size
        if len(files) > 10:  # Limit batch size
            raise HTTPException(status_code=400, detail="Maximum batch size is 10 images")
        
        # Validate file types and read data
        image_batch = []
        for file in files:
            if not file.content_type.startswith("image/"):
                raise HTTPException(status_code=400, detail=f"File {file.filename} must be an image")
            
            image_data = await file.read()
            
            if len(image_data) > settings.MAX_IMAGE_SIZE:
                raise HTTPException(
                    status_code=413, 
                    detail=f"Image {file.filename} too large. Maximum size: {settings.MAX_IMAGE_SIZE} bytes"
                )
            
            image_batch.append(image_data)
        
        # Parse asset IDs if provided
        parsed_asset_ids = None
        if asset_ids:
            try:
                parsed_asset_ids = asset_ids.split(",")
            except:
                parsed_asset_ids = None
        
        # Get object detection service
        from ..services.object_detection_service import ObjectDetectionService
        from ..main import app
        object_detection_service = ObjectDetectionService(app.state.model_manager)
        
        # Run batch object detection
        results = await object_detection_service.detect_objects_batch(
            image_batch=image_batch,
            confidence_threshold=confidence_threshold,
            iou_threshold=iou_threshold,
            max_detections=max_detections,
            return_crops=return_crops,
            asset_ids=parsed_asset_ids
        )
        
        return {"data": results}
    
    except HTTPException:
        raise
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except InferenceError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error("Batch object detection failed", error=str(e))
        raise HTTPException(status_code=500, detail="Batch object detection failed")


@router.get("/detect/objects/classes")
async def get_object_classes(ml_service: MLService = Depends(get_ml_service)):
    """Get supported object detection classes."""
    try:
        from ..services.object_detection_service import ObjectDetectionService
        object_detection_service = ObjectDetectionService(app.state.model_manager)
        
        classes = await object_detection_service.get_supported_classes()
        
        return {"data": {"classes": classes, "total": len(classes)}}
    
    except Exception as e:
        logger.error("Failed to get object classes", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get object classes")


@router.get("/detect/objects/model-info")
async def get_object_detection_model_info(ml_service: MLService = Depends(get_ml_service)):
    """Get object detection model information."""
    try:
        from ..services.object_detection_service import ObjectDetectionService
        object_detection_service = ObjectDetectionService(app.state.model_manager)
        
        model_info = await object_detection_service.get_model_info()
        
        return {"data": model_info}
    
    except Exception as e:
        logger.error("Failed to get model info", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get model information")


@router.post("/detect/scenes")
async def detect_scenes(
    file: UploadFile = File(...),
    confidence_threshold: float = Form(0.1),
    top_k: int = Form(5),
    return_features: bool = Form(False),
    asset_id: Optional[str] = Form(None),
    ml_service: MLService = Depends(get_ml_service)
):
    """Detect scenes in an uploaded image."""
    try:
        # Validate file type
        if not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        # Read image data
        image_data = await file.read()
        
        # Validate file size
        if len(image_data) > settings.MAX_IMAGE_SIZE:
            raise HTTPException(
                status_code=413, 
                detail=f"Image too large. Maximum size: {settings.MAX_IMAGE_SIZE} bytes"
            )
        
        # Get scene detection service
        from ..services.scene_detection_service import SceneDetectionService
        from ..main import app
        scene_detection_service = SceneDetectionService(app.state.model_manager)
        
        # Run scene detection
        results = await scene_detection_service.detect_scenes(
            image_data=image_data,
            confidence_threshold=confidence_threshold,
            top_k=top_k,
            return_features=return_features,
            asset_id=asset_id
        )
        
        return {"data": results}
    
    except HTTPException:
        raise
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except InferenceError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error("Scene detection failed", error=str(e))
        raise HTTPException(status_code=500, detail="Scene detection failed")


@router.post("/detect/scenes/video")
async def detect_scenes_video(
    file: UploadFile = File(...),
    sample_rate: int = Form(30),
    confidence_threshold: float = Form(0.1),
    top_k: int = Form(5),
    scene_change_threshold: float = Form(0.3),
    asset_id: Optional[str] = Form(None),
    ml_service: MLService = Depends(get_ml_service)
):
    """Detect scenes in an uploaded video."""
    try:
        # Validate file type
        if not file.content_type.startswith("video/"):
            raise HTTPException(status_code=400, detail="File must be a video")
        
        # Read video data
        video_data = await file.read()
        
        # Validate file size
        if len(video_data) > settings.MAX_VIDEO_SIZE:
            raise HTTPException(
                status_code=413, 
                detail=f"Video too large. Maximum size: {settings.MAX_VIDEO_SIZE} bytes"
            )
        
        # Save video temporarily
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_file:
            tmp_file.write(video_data)
            tmp_file_path = tmp_file.name
        
        try:
            # Get scene detection service
            from ..services.scene_detection_service import SceneDetectionService
            from ..main import app
            scene_detection_service = SceneDetectionService(app.state.model_manager)
            
            # Run video scene detection
            results = await scene_detection_service.detect_scenes_video(
                video_path=tmp_file_path,
                sample_rate=sample_rate,
                confidence_threshold=confidence_threshold,
                top_k=top_k,
                scene_change_threshold=scene_change_threshold,
                asset_id=asset_id
            )
            
            return {"data": results}
        
        finally:
            # Clean up temporary file
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)
    
    except HTTPException:
        raise
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except InferenceError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error("Video scene detection failed", error=str(e))
        raise HTTPException(status_code=500, detail="Video scene detection failed")


@router.get("/detect/scenes/classes")
async def get_scene_classes(ml_service: MLService = Depends(get_ml_service)):
    """Get supported scene detection classes."""
    try:
        from ..services.scene_detection_service import SceneDetectionService
        from ..main import app
        scene_detection_service = SceneDetectionService(app.state.model_manager)
        
        classes = await scene_detection_service.get_supported_scenes()
        
        return {"data": {"classes": classes, "total": len(classes)}}
    
    except Exception as e:
        logger.error("Failed to get scene classes", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get scene classes")


@router.get("/detect/scenes/model-info")
async def get_scene_detection_model_info(ml_service: MLService = Depends(get_ml_service)):
    """Get scene detection model information."""
    try:
        from ..services.scene_detection_service import SceneDetectionService
        from ..main import app
        scene_detection_service = SceneDetectionService(app.state.model_manager)
        
        model_info = await scene_detection_service.get_model_info()
        
        return {"data": model_info}
    
    except Exception as e:
        logger.error("Failed to get scene detection model info", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get scene detection model information")


@router.post("/detect/faces")
async def detect_faces(
    file: UploadFile = File(...),
    min_face_size: int = Form(20),
    ml_service: MLService = Depends(get_ml_service)
):
    """Detect faces in an uploaded image."""
    try:
        # Validate file type
        if not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        # Read image data
        image_data = await file.read()
        
        # Validate file size
        if len(image_data) > settings.MAX_IMAGE_SIZE:
            raise HTTPException(
                status_code=413, 
                detail=f"Image too large. Maximum size: {settings.MAX_IMAGE_SIZE} bytes"
            )
        
        # Run face detection
        results = await ml_service.detect_faces(image_data, min_face_size)
        
        return {"data": results}
    
    except HTTPException:
        raise
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except InferenceError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error("Face detection failed", error=str(e))
        raise HTTPException(status_code=500, detail="Face detection failed")


@router.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),
    language: Optional[str] = Form(None),
    return_segments: bool = Form(True),
    return_word_timestamps: bool = Form(False),
    temperature: float = Form(0.0),
    beam_size: int = Form(5),
    best_of: int = Form(5),
    initial_prompt: Optional[str] = Form(None),
    asset_id: Optional[str] = Form(None),
    ml_service: MLService = Depends(get_ml_service)
):
    """Transcribe audio to text."""
    try:
        # Validate file type
        if not file.content_type.startswith("audio/"):
            raise HTTPException(status_code=400, detail="File must be an audio file")
        
        # Read audio data
        audio_data = await file.read()
        
        # Validate file size
        if len(audio_data) > settings.MAX_AUDIO_SIZE:
            raise HTTPException(
                status_code=413, 
                detail=f"Audio file too large. Maximum size: {settings.MAX_AUDIO_SIZE} bytes"
            )
        
        # Get speech-to-text service
        from ..services.speech_to_text_service import SpeechToTextService
        from ..main import app
        stt_service = SpeechToTextService(app.state.model_manager)
        
        # Run speech-to-text
        results = await stt_service.transcribe_audio(
            audio_data=audio_data,
            language=language,
            return_segments=return_segments,
            return_word_timestamps=return_word_timestamps,
            temperature=temperature,
            beam_size=beam_size,
            best_of=best_of,
            initial_prompt=initial_prompt,
            asset_id=asset_id
        )
        
        return {"data": results}
    
    except HTTPException:
        raise
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except InferenceError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error("Speech-to-text failed", error=str(e))
        raise HTTPException(status_code=500, detail="Speech-to-text failed")


@router.post("/transcribe/video")
async def transcribe_video(
    file: UploadFile = File(...),
    language: Optional[str] = Form(None),
    return_segments: bool = Form(True),
    return_word_timestamps: bool = Form(False),
    extract_audio: bool = Form(True),
    asset_id: Optional[str] = Form(None),
    ml_service: MLService = Depends(get_ml_service)
):
    """Transcribe audio from video file."""
    try:
        # Validate file type
        if not file.content_type.startswith("video/"):
            raise HTTPException(status_code=400, detail="File must be a video file")
        
        # Read video data
        video_data = await file.read()
        
        # Validate file size
        if len(video_data) > settings.MAX_VIDEO_SIZE:
            raise HTTPException(
                status_code=413, 
                detail=f"Video file too large. Maximum size: {settings.MAX_VIDEO_SIZE} bytes"
            )
        
        # Save video temporarily
        import tempfile
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_file:
            tmp_file.write(video_data)
            tmp_file_path = tmp_file.name
        
        try:
            # Get speech-to-text service
            from ..services.speech_to_text_service import SpeechToTextService
            from ..main import app
            stt_service = SpeechToTextService(app.state.model_manager)
            
            # Run video transcription
            results = await stt_service.transcribe_video(
                video_path=tmp_file_path,
                extract_audio=extract_audio,
                language=language,
                return_segments=return_segments,
                return_word_timestamps=return_word_timestamps,
                asset_id=asset_id
            )
            
            return {"data": results}
        
        finally:
            # Clean up temporary file
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)
    
    except HTTPException:
        raise
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except InferenceError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error("Video transcription failed", error=str(e))
        raise HTTPException(status_code=500, detail="Video transcription failed")


@router.post("/transcribe/batch")
async def transcribe_batch(
    files: List[UploadFile] = File(...),
    language: Optional[str] = Form(None),
    return_segments: bool = Form(True),
    return_word_timestamps: bool = Form(False),
    asset_ids: Optional[str] = Form(None),
    ml_service: MLService = Depends(get_ml_service)
):
    """Transcribe a batch of audio files."""
    try:
        # Validate batch size
        if len(files) > 5:  # Limit batch size for transcription
            raise HTTPException(status_code=400, detail="Maximum batch size is 5 audio files")
        
        # Validate file types and read data
        audio_batch = []
        for file in files:
            if not file.content_type.startswith("audio/"):
                raise HTTPException(status_code=400, detail=f"File {file.filename} must be an audio file")
            
            audio_data = await file.read()
            
            if len(audio_data) > settings.MAX_AUDIO_SIZE:
                raise HTTPException(
                    status_code=413, 
                    detail=f"Audio file {file.filename} too large. Maximum size: {settings.MAX_AUDIO_SIZE} bytes"
                )
            
            audio_batch.append(audio_data)
        
        # Parse asset IDs if provided
        parsed_asset_ids = None
        if asset_ids:
            try:
                parsed_asset_ids = asset_ids.split(",")
            except:
                parsed_asset_ids = None
        
        # Get speech-to-text service
        from ..services.speech_to_text_service import SpeechToTextService
        from ..main import app
        stt_service = SpeechToTextService(app.state.model_manager)
        
        # Run batch transcription
        results = await stt_service.transcribe_batch(
            audio_batch=audio_batch,
            language=language,
            return_segments=return_segments,
            return_word_timestamps=return_word_timestamps,
            asset_ids=parsed_asset_ids
        )
        
        return {"data": results}
    
    except HTTPException:
        raise
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except InferenceError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error("Batch transcription failed", error=str(e))
        raise HTTPException(status_code=500, detail="Batch transcription failed")


@router.post("/transcribe/detect-language")
async def detect_language(
    file: UploadFile = File(...),
    duration: float = Form(30.0),
    ml_service: MLService = Depends(get_ml_service)
):
    """Detect language of audio file."""
    try:
        # Validate file type
        if not file.content_type.startswith("audio/"):
            raise HTTPException(status_code=400, detail="File must be an audio file")
        
        # Read audio data
        audio_data = await file.read()
        
        # Validate file size
        if len(audio_data) > settings.MAX_AUDIO_SIZE:
            raise HTTPException(
                status_code=413, 
                detail=f"Audio file too large. Maximum size: {settings.MAX_AUDIO_SIZE} bytes"
            )
        
        # Get speech-to-text service
        from ..services.speech_to_text_service import SpeechToTextService
        from ..main import app
        stt_service = SpeechToTextService(app.state.model_manager)
        
        # Run language detection
        results = await stt_service.detect_language(
            audio_data=audio_data,
            duration=duration
        )
        
        return {"data": results}
    
    except HTTPException:
        raise
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except InferenceError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error("Language detection failed", error=str(e))
        raise HTTPException(status_code=500, detail="Language detection failed")


@router.get("/transcribe/languages")
async def get_supported_languages(ml_service: MLService = Depends(get_ml_service)):
    """Get supported languages for speech-to-text."""
    try:
        from ..services.speech_to_text_service import SpeechToTextService
        from ..main import app
        stt_service = SpeechToTextService(app.state.model_manager)
        
        languages = await stt_service.get_supported_languages()
        
        return {"data": {"languages": languages, "total": len(languages)}}
    
    except Exception as e:
        logger.error("Failed to get supported languages", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get supported languages")


@router.get("/transcribe/model-info")
async def get_speech_to_text_model_info(ml_service: MLService = Depends(get_ml_service)):
    """Get speech-to-text model information."""
    try:
        from ..services.speech_to_text_service import SpeechToTextService
        from ..main import app
        stt_service = SpeechToTextService(app.state.model_manager)
        
        model_info = await stt_service.get_model_info()
        
        return {"data": model_info}
    
    except Exception as e:
        logger.error("Failed to get speech-to-text model info", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get speech-to-text model information")


@router.post("/recognize/faces")
async def recognize_faces(
    file: UploadFile = File(...),
    min_face_size: int = Form(20),
    confidence_threshold: float = Form(0.6),
    distance_threshold: float = Form(0.6),
    return_face_crops: bool = Form(False),
    return_embeddings: bool = Form(False),
    asset_id: Optional[str] = Form(None),
    ml_service: MLService = Depends(get_ml_service)
):
    """Detect and recognize faces in an uploaded image."""
    try:
        # Validate file type
        if not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        # Read image data
        image_data = await file.read()
        
        # Validate file size
        if len(image_data) > settings.MAX_IMAGE_SIZE:
            raise HTTPException(
                status_code=413, 
                detail=f"Image too large. Maximum size: {settings.MAX_IMAGE_SIZE} bytes"
            )
        
        # Get facial recognition service
        from ..services.facial_recognition_service import FacialRecognitionService
        from ..main import app
        facial_recognition_service = FacialRecognitionService(app.state.model_manager)
        
        # Run facial recognition
        results = await facial_recognition_service.detect_and_recognize_faces(
            image_data=image_data,
            min_face_size=min_face_size,
            confidence_threshold=confidence_threshold,
            distance_threshold=distance_threshold,
            return_face_crops=return_face_crops,
            return_embeddings=return_embeddings,
            asset_id=asset_id
        )
        
        return {"data": results}
    
    except HTTPException:
        raise
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except InferenceError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error("Facial recognition failed", error=str(e))
        raise HTTPException(status_code=500, detail="Facial recognition failed")


@router.post("/recognize/faces/add-known-face")
async def add_known_face(
    person_id: str = Form(...),
    file: UploadFile = File(...),
    face_bbox_x1: Optional[float] = Form(None),
    face_bbox_y1: Optional[float] = Form(None),
    face_bbox_x2: Optional[float] = Form(None),
    face_bbox_y2: Optional[float] = Form(None),
    ml_service: MLService = Depends(get_ml_service)
):
    """Add a known face to the recognition database."""
    try:
        # Validate file type
        if not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        # Read image data
        image_data = await file.read()
        
        # Validate file size
        if len(image_data) > settings.MAX_IMAGE_SIZE:
            raise HTTPException(
                status_code=413, 
                detail=f"Image too large. Maximum size: {settings.MAX_IMAGE_SIZE} bytes"
            )
        
        # Parse face bounding box if provided
        face_bbox = None
        if all(x is not None for x in [face_bbox_x1, face_bbox_y1, face_bbox_x2, face_bbox_y2]):
            face_bbox = {
                "x1": face_bbox_x1,
                "y1": face_bbox_y1,
                "x2": face_bbox_x2,
                "y2": face_bbox_y2
            }
        
        # Get facial recognition service
        from ..services.facial_recognition_service import FacialRecognitionService
        from ..main import app
        facial_recognition_service = FacialRecognitionService(app.state.model_manager)
        
        # Add known face
        results = await facial_recognition_service.add_known_face(
            person_id=person_id,
            image_data=image_data,
            face_bbox=face_bbox
        )
        
        return {"data": results}
    
    except HTTPException:
        raise
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except InferenceError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error("Failed to add known face", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to add known face")


@router.post("/recognize/faces/search")
async def search_similar_faces(
    file: UploadFile = File(...),
    similarity_threshold: float = Form(0.6),
    max_results: int = Form(10),
    ml_service: MLService = Depends(get_ml_service)
):
    """Search for similar faces in the database."""
    try:
        # Validate file type
        if not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        # Read image data
        image_data = await file.read()
        
        # Validate file size
        if len(image_data) > settings.MAX_IMAGE_SIZE:
            raise HTTPException(
                status_code=413, 
                detail=f"Image too large. Maximum size: {settings.MAX_IMAGE_SIZE} bytes"
            )
        
        # Get facial recognition service
        from ..services.facial_recognition_service import FacialRecognitionService
        from ..main import app
        facial_recognition_service = FacialRecognitionService(app.state.model_manager)
        
        # Search for similar faces
        results = await facial_recognition_service.search_similar_faces(
            query_image=image_data,
            similarity_threshold=similarity_threshold,
            max_results=max_results
        )
        
        return {"data": {"similar_faces": results, "total": len(results)}}
    
    except HTTPException:
        raise
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except InferenceError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error("Face search failed", error=str(e))
        raise HTTPException(status_code=500, detail="Face search failed")


@router.get("/recognize/faces/database")
async def get_face_database_info(ml_service: MLService = Depends(get_ml_service)):
    """Get information about the face recognition database."""
    try:
        from ..services.facial_recognition_service import FacialRecognitionService
        from ..main import app
        facial_recognition_service = FacialRecognitionService(app.state.model_manager)
        
        info = await facial_recognition_service.get_face_database_info()
        
        return {"data": info}
    
    except Exception as e:
        logger.error("Failed to get face database info", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get face database information")


@router.delete("/recognize/faces/remove/{person_id}")
async def remove_known_face(
    person_id: str,
    ml_service: MLService = Depends(get_ml_service)
):
    """Remove a known face from the recognition database."""
    try:
        from ..services.facial_recognition_service import FacialRecognitionService
        from ..main import app
        facial_recognition_service = FacialRecognitionService(app.state.model_manager)
        
        success = await facial_recognition_service.remove_known_face(person_id)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"Person {person_id} not found in database")
        
        return {"data": {"person_id": person_id, "removed": True}}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to remove known face", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to remove known face")


@router.get("/recognize/faces/model-info")
async def get_facial_recognition_model_info(ml_service: MLService = Depends(get_ml_service)):
    """Get facial recognition model information."""
    try:
        from ..services.facial_recognition_service import FacialRecognitionService
        from ..main import app
        facial_recognition_service = FacialRecognitionService(app.state.model_manager)
        
        model_info = await facial_recognition_service.get_model_info()
        
        return {"data": model_info}
    
    except Exception as e:
        logger.error("Failed to get facial recognition model info", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get facial recognition model information")


# Knowledge Base and Archive-Based Recognition Endpoints

@router.post("/knowledge-base/entities")
async def add_entity_to_knowledge_base(
    entity_type: str = Form(...),
    entity_id: str = Form(...),
    entity_name: str = Form(...),
    description: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    categories: Optional[str] = Form(None),
    confidence_threshold: float = Form(0.7),
    trigger_retroactive_analysis: bool = Form(True),
    file: Optional[UploadFile] = File(None),
    ml_service: MLService = Depends(get_ml_service)
):
    """Add a new entity to the knowledge base."""
    try:
        # Parse tags and categories
        parsed_tags = tags.split(",") if tags else None
        parsed_categories = categories.split(",") if categories else None
        
        # Extract features from file if provided
        features = None
        if file:
            if not file.content_type.startswith("image/"):
                raise HTTPException(status_code=400, detail="File must be an image")
            
            image_data = await file.read()
            
            if len(image_data) > settings.MAX_IMAGE_SIZE:
                raise HTTPException(
                    status_code=413, 
                    detail=f"Image too large. Maximum size: {settings.MAX_IMAGE_SIZE} bytes"
                )
            
            # Extract features based on entity type
            if entity_type == "person":
                # Extract face features
                from ..services.facial_recognition_service import FacialRecognitionService
                from ..main import app
                facial_service = FacialRecognitionService(app.state.model_manager)
                
                face_result = await facial_service.detect_and_recognize_faces(
                    image_data=image_data,
                    return_embeddings=True
                )
                
                if face_result["faces"]:
                    features = {
                        "face_embedding": {
                            "vector": face_result["faces"][0]["embedding"],
                            "confidence": face_result["faces"][0]["detection"]["confidence"]
                        }
                    }
            
            elif entity_type == "logo":
                # Extract logo features (would implement logo detection)
                # For now, use object detection as placeholder
                from ..services.object_detection_service import ObjectDetectionService
                from ..main import app
                object_service = ObjectDetectionService(app.state.model_manager)
                
                detection_result = await object_service.detect_objects(
                    image_data=image_data,
                    return_crops=True
                )
                
                if detection_result["detections"]:
                    # Use first detection as logo
                    features = {
                        "logo_embedding": {
                            "vector": [0.0] * 512,  # Placeholder embedding
                            "confidence": detection_result["detections"][0]["confidence"]
                        }
                    }
        
        # Get knowledge base service
        from ..services.knowledge_base_service import KnowledgeBaseService
        from ..main import app
        kb_service = KnowledgeBaseService(app.state.model_manager)
        
        # Add entity
        result = await kb_service.add_entity(
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            description=description,
            tags=parsed_tags,
            categories=parsed_categories,
            confidence_threshold=confidence_threshold,
            features=features,
            trigger_retroactive_analysis=trigger_retroactive_analysis
        )
        
        return {"data": result}
    
    except HTTPException:
        raise
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except InferenceError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error("Failed to add entity to knowledge base", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to add entity to knowledge base")


@router.post("/knowledge-base/entities/from-detection")
async def add_entity_from_detection(
    asset_id: str = Form(...),
    entity_type: str = Form(...),
    entity_id: str = Form(...),
    entity_name: str = Form(...),
    detection_data: str = Form(...),  # JSON string
    trigger_retroactive_analysis: bool = Form(True),
    ml_service: MLService = Depends(get_ml_service)
):
    """Add an entity based on a detection in an asset."""
    try:
        import json
        
        # Parse detection data
        try:
            detection_dict = json.loads(detection_data)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid detection data JSON")
        
        # Get knowledge base service
        from ..services.knowledge_base_service import KnowledgeBaseService
        from ..main import app
        kb_service = KnowledgeBaseService(app.state.model_manager)
        
        # Add entity from detection
        result = await kb_service.add_entity_from_detection(
            asset_id=asset_id,
            detection_data=detection_dict,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            trigger_retroactive_analysis=trigger_retroactive_analysis
        )
        
        return {"data": result}
    
    except HTTPException:
        raise
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except InferenceError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error("Failed to add entity from detection", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to add entity from detection")


@router.get("/knowledge-base/entities/search")
async def search_entities(
    query: Optional[str] = None,
    entity_types: Optional[str] = None,
    tags: Optional[str] = None,
    categories: Optional[str] = None,
    limit: int = 50,
    ml_service: MLService = Depends(get_ml_service)
):
    """Search entities in the knowledge base."""
    try:
        # Parse filters
        parsed_entity_types = entity_types.split(",") if entity_types else None
        parsed_tags = tags.split(",") if tags else None
        parsed_categories = categories.split(",") if categories else None
        
        # Get knowledge base service
        from ..services.knowledge_base_service import KnowledgeBaseService
        from ..main import app
        kb_service = KnowledgeBaseService(app.state.model_manager)
        
        # Search entities
        entities = await kb_service.search_entities(
            query=query,
            entity_types=parsed_entity_types,
            tags=parsed_tags,
            categories=parsed_categories,
            limit=limit
        )
        
        return {"data": {"entities": entities, "total": len(entities)}}
    
    except Exception as e:
        logger.error("Failed to search entities", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to search entities")


@router.get("/knowledge-base/entities/{entity_id}")
async def get_entity_details(
    entity_id: str,
    ml_service: MLService = Depends(get_ml_service)
):
    """Get detailed information about an entity."""
    try:
        # Get knowledge base service
        from ..services.knowledge_base_service import KnowledgeBaseService
        from ..main import app
        kb_service = KnowledgeBaseService(app.state.model_manager)
        
        # Search for the entity
        entities = await kb_service.search_entities(
            query=entity_id,
            limit=1
        )
        
        if not entities:
            raise HTTPException(status_code=404, detail="Entity not found")
        
        return {"data": entities[0]}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get entity details", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get entity details")


@router.get("/knowledge-base/assets/{asset_id}/entities")
async def get_asset_entities(
    asset_id: str,
    entity_types: Optional[str] = None,
    include_metadata: bool = True,
    ml_service: MLService = Depends(get_ml_service)
):
    """Get all entities detected in an asset."""
    try:
        # Parse entity types
        parsed_entity_types = entity_types.split(",") if entity_types else None
        
        # Get knowledge base service
        from ..services.knowledge_base_service import KnowledgeBaseService
        from ..main import app
        kb_service = KnowledgeBaseService(app.state.model_manager)
        
        # Get asset entities
        result = await kb_service.get_asset_entities(
            asset_id=asset_id,
            entity_types=parsed_entity_types,
            include_metadata=include_metadata
        )
        
        return {"data": result}
    
    except Exception as e:
        logger.error("Failed to get asset entities", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get asset entities")


@router.get("/knowledge-base/stats")
async def get_knowledge_base_stats(ml_service: MLService = Depends(get_ml_service)):
    """Get statistics about the knowledge base."""
    try:
        # Get knowledge base service
        from ..services.knowledge_base_service import KnowledgeBaseService
        from ..main import app
        kb_service = KnowledgeBaseService(app.state.model_manager)
        
        # Get stats
        stats = await kb_service.get_knowledge_base_stats()
        
        return {"data": stats}
    
    except Exception as e:
        logger.error("Failed to get knowledge base stats", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get knowledge base stats")


@router.get("/retroactive-analysis/jobs")
async def list_retroactive_analysis_jobs(ml_service: MLService = Depends(get_ml_service)):
    """List pending retroactive analysis jobs."""
    try:
        # Get retroactive analysis engine
        from ..services.retroactive_analysis_engine import RetroactiveAnalysisEngine
        from ..services.knowledge_base_service import KnowledgeBaseService
        from ..main import app
        
        kb_service = KnowledgeBaseService(app.state.model_manager)
        analysis_engine = RetroactiveAnalysisEngine(app.state.model_manager, kb_service)
        
        # List pending jobs
        jobs = await analysis_engine.list_pending_jobs()
        
        return {"data": {"jobs": jobs, "total": len(jobs)}}
    
    except Exception as e:
        logger.error("Failed to list retroactive analysis jobs", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to list retroactive analysis jobs")


@router.get("/retroactive-analysis/jobs/{job_id}")
async def get_retroactive_analysis_job_status(
    job_id: str,
    ml_service: MLService = Depends(get_ml_service)
):
    """Get the status of a retroactive analysis job."""
    try:
        # Get retroactive analysis engine
        from ..services.retroactive_analysis_engine import RetroactiveAnalysisEngine
        from ..services.knowledge_base_service import KnowledgeBaseService
        from ..main import app
        
        kb_service = KnowledgeBaseService(app.state.model_manager)
        analysis_engine = RetroactiveAnalysisEngine(app.state.model_manager, kb_service)
        
        # Get job status
        status = await analysis_engine.get_job_status(job_id)
        
        return {"data": status}
    
    except HTTPException:
        raise
    except ValidationError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Failed to get job status", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get job status")


@router.post("/retroactive-analysis/jobs/{job_id}/process")
async def process_retroactive_analysis_job(
    job_id: str,
    batch_size: int = 100,
    ml_service: MLService = Depends(get_ml_service)
):
    """Process a retroactive analysis job."""
    try:
        # Get retroactive analysis engine
        from ..services.retroactive_analysis_engine import RetroactiveAnalysisEngine
        from ..services.knowledge_base_service import KnowledgeBaseService
        from ..main import app
        
        kb_service = KnowledgeBaseService(app.state.model_manager)
        analysis_engine = RetroactiveAnalysisEngine(app.state.model_manager, kb_service)
        
        # Process job (this should typically be done in a background task)
        # For now, we'll return a task ID and process async
        import asyncio
        
        task = asyncio.create_task(
            analysis_engine.process_retroactive_analysis_job(job_id, batch_size)
        )
        
        return {
            "data": {
                "job_id": job_id,
                "task_started": True,
                "message": "Retroactive analysis job started in background"
            }
        }
    
    except HTTPException:
        raise
    except ValidationError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Failed to process retroactive analysis job", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to process retroactive analysis job")


@router.get("/cache/stats")
async def get_cache_stats(
    model_manager: ModelManager = Depends(get_model_manager)
):
    """Get cache statistics."""
    try:
        stats = model_manager.get_cache_stats()
        return {"data": stats}
    except Exception as e:
        logger.error("Failed to get cache stats", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get cache statistics")


@router.post("/cache/clear")
async def clear_cache(
    model_manager: ModelManager = Depends(get_model_manager)
):
    """Clear model cache."""
    try:
        await model_manager.clear_cache()
        return {"data": {"message": "Cache cleared successfully"}}
    except Exception as e:
        logger.error("Failed to clear cache", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to clear cache")


@router.post("/moderate/content")
async def moderate_content(
    text: str = Form(...),
    threshold: float = Form(0.5),
    asset_id: Optional[str] = Form(None),
    ml_service: MLService = Depends(get_ml_service)
):
    """Moderate text content for toxicity and inappropriate content."""
    try:
        # Validate input
        if not text:
            raise HTTPException(status_code=400, detail="Text content is required")
        
        # Validate threshold
        if threshold < 0.0 or threshold > 1.0:
            raise HTTPException(status_code=400, detail="Threshold must be between 0.0 and 1.0")
        
        # Run content moderation
        results = await ml_service.moderate_content(text, threshold)
        
        # Add asset_id to results if provided
        if asset_id:
            results["asset_id"] = asset_id
        
        return {"data": results}
    
    except HTTPException:
        raise
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except InferenceError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error("Content moderation failed", error=str(e))
        raise HTTPException(status_code=500, detail="Content moderation failed")


@router.post("/moderate/batch")
async def moderate_content_batch(
    texts: List[str] = Form(...),
    threshold: float = Form(0.5),
    asset_ids: Optional[str] = Form(None),
    ml_service: MLService = Depends(get_ml_service)
):
    """Moderate multiple texts for toxicity and inappropriate content."""
    try:
        # Validate batch size
        if len(texts) > 20:  # Limit batch size
            raise HTTPException(status_code=400, detail="Maximum batch size is 20 texts")
        
        # Validate threshold
        if threshold < 0.0 or threshold > 1.0:
            raise HTTPException(status_code=400, detail="Threshold must be between 0.0 and 1.0")
        
        # Parse asset_ids if provided
        asset_id_list = []
        if asset_ids:
            asset_id_list = [id.strip() for id in asset_ids.split(",")]
        
        # Process each text
        results = []
        for i, text in enumerate(texts):
            if not text:
                continue
                
            try:
                result = await ml_service.moderate_content(text, threshold)
                
                # Add asset_id if provided
                if asset_id_list and i < len(asset_id_list):
                    result["asset_id"] = asset_id_list[i]
                
                results.append(result)
                
            except Exception as e:
                logger.error("Content moderation failed for text", text_index=i, error=str(e))
                results.append({
                    "error": str(e),
                    "text_index": i,
                    "text": text[:50] + "..." if len(text) > 50 else text
                })
        
        return {"data": {"results": results, "total_processed": len(results)}}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Batch content moderation failed", error=str(e))
        raise HTTPException(status_code=500, detail="Batch content moderation failed")


@router.post("/moderate/video-transcript")
async def moderate_video_transcript(
    file: UploadFile = File(...),
    threshold: float = Form(0.5),
    language: Optional[str] = Form(None),
    asset_id: Optional[str] = Form(None),
    ml_service: MLService = Depends(get_ml_service)
):
    """Transcribe video and moderate the transcript for content."""
    try:
        # Validate file type
        if not file.content_type.startswith("video/"):
            raise HTTPException(status_code=400, detail="File must be a video file")
        
        # Read video data
        video_data = await file.read()
        
        # Validate file size
        if len(video_data) > settings.MAX_VIDEO_SIZE:
            raise HTTPException(
                status_code=413, 
                detail=f"Video file too large. Maximum size: {settings.MAX_VIDEO_SIZE} bytes"
            )
        
        # Save video temporarily
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_file:
            tmp_file.write(video_data)
            tmp_file_path = tmp_file.name
        
        try:
            # First, transcribe the video
            import librosa
            audio, sr = librosa.load(tmp_file_path, sr=16000)
            
            # Run speech-to-text
            transcription_results = await ml_service.transcribe_audio(audio, language)
            
            # Then moderate the transcript
            if transcription_results.get("text"):
                moderation_results = await ml_service.moderate_content(
                    transcription_results["text"], 
                    threshold
                )
                
                # Combine results
                combined_results = {
                    "transcription": transcription_results,
                    "moderation": moderation_results,
                    "asset_id": asset_id
                }
                
                return {"data": combined_results}
            else:
                raise HTTPException(status_code=400, detail="No transcription text found")
        
        finally:
            # Clean up temporary file
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)
    
    except HTTPException:
        raise
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except InferenceError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error("Video transcript moderation failed", error=str(e))
        raise HTTPException(status_code=500, detail="Video transcript moderation failed")


@router.post("/analyze/sentiment")
async def analyze_sentiment(
    text: str = Form(...),
    asset_id: Optional[str] = Form(None),
    ml_service: MLService = Depends(get_ml_service)
):
    """Analyze sentiment of text content."""
    try:
        # Validate input
        if not text:
            raise HTTPException(status_code=400, detail="Text content is required")
        
        # Run sentiment analysis
        results = await ml_service.analyze_sentiment(text)
        
        # Add asset_id to results if provided
        if asset_id:
            results["asset_id"] = asset_id
        
        return {"data": results}
    
    except HTTPException:
        raise
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except InferenceError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error("Sentiment analysis failed", error=str(e))
        raise HTTPException(status_code=500, detail="Sentiment analysis failed")


@router.post("/analyze/sentiment/batch")
async def analyze_sentiment_batch(
    texts: List[str] = Form(...),
    asset_ids: Optional[str] = Form(None),
    ml_service: MLService = Depends(get_ml_service)
):
    """Analyze sentiment of multiple texts."""
    try:
        # Validate batch size
        if len(texts) > 20:  # Limit batch size
            raise HTTPException(status_code=400, detail="Maximum batch size is 20 texts")
        
        # Parse asset_ids if provided
        asset_id_list = []
        if asset_ids:
            asset_id_list = [id.strip() for id in asset_ids.split(",")]
        
        # Process each text
        results = []
        for i, text in enumerate(texts):
            if not text:
                continue
                
            try:
                result = await ml_service.analyze_sentiment(text)
                
                # Add asset_id if provided
                if asset_id_list and i < len(asset_id_list):
                    result["asset_id"] = asset_id_list[i]
                
                results.append(result)
                
            except Exception as e:
                logger.error("Sentiment analysis failed for text", text_index=i, error=str(e))
                results.append({
                    "error": str(e),
                    "text_index": i,
                    "text": text[:50] + "..." if len(text) > 50 else text
                })
        
        return {"data": {"results": results, "total_processed": len(results)}}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Batch sentiment analysis failed", error=str(e))
        raise HTTPException(status_code=500, detail="Batch sentiment analysis failed")


@router.post("/analyze/sentiment-with-moderation")
async def analyze_sentiment_with_moderation(
    text: str = Form(...),
    moderation_threshold: float = Form(0.5),
    asset_id: Optional[str] = Form(None),
    ml_service: MLService = Depends(get_ml_service)
):
    """Analyze sentiment and moderate content in a single request."""
    try:
        # Validate input
        if not text:
            raise HTTPException(status_code=400, detail="Text content is required")
        
        # Validate threshold
        if moderation_threshold < 0.0 or moderation_threshold > 1.0:
            raise HTTPException(status_code=400, detail="Moderation threshold must be between 0.0 and 1.0")
        
        # Run both analyses concurrently
        sentiment_task = ml_service.analyze_sentiment(text)
        moderation_task = ml_service.moderate_content(text, moderation_threshold)
        
        sentiment_results, moderation_results = await asyncio.gather(
            sentiment_task, moderation_task
        )
        
        # Combine results
        combined_results = {
            "sentiment": sentiment_results,
            "moderation": moderation_results,
            "asset_id": asset_id
        }
        
        return {"data": combined_results}
    
    except HTTPException:
        raise
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except InferenceError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error("Sentiment analysis with moderation failed", error=str(e))
        raise HTTPException(status_code=500, detail="Sentiment analysis with moderation failed")


@router.post("/detect/language")
async def detect_language(
    text: str = Form(...),
    confidence_threshold: float = Form(0.5),
    asset_id: Optional[str] = Form(None),
    ml_service: MLService = Depends(get_ml_service)
):
    """Detect the language of text content."""
    try:
        # Validate input
        if not text:
            raise HTTPException(status_code=400, detail="Text content is required")
        
        # Validate threshold
        if confidence_threshold < 0.0 or confidence_threshold > 1.0:
            raise HTTPException(status_code=400, detail="Confidence threshold must be between 0.0 and 1.0")
        
        # Run language detection
        results = await ml_service.detect_language(text, confidence_threshold)
        
        # Add asset_id to results if provided
        if asset_id:
            results["asset_id"] = asset_id
        
        return {"data": results}
    
    except HTTPException:
        raise
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except InferenceError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error("Language detection failed", error=str(e))
        raise HTTPException(status_code=500, detail="Language detection failed")


@router.post("/detect/language/batch")
async def detect_language_batch(
    texts: List[str] = Form(...),
    confidence_threshold: float = Form(0.5),
    asset_ids: Optional[str] = Form(None),
    ml_service: MLService = Depends(get_ml_service)
):
    """Detect language for multiple texts."""
    try:
        # Validate batch size
        if len(texts) > 20:  # Limit batch size
            raise HTTPException(status_code=400, detail="Maximum batch size is 20 texts")
        
        # Validate threshold
        if confidence_threshold < 0.0 or confidence_threshold > 1.0:
            raise HTTPException(status_code=400, detail="Confidence threshold must be between 0.0 and 1.0")
        
        # Parse asset_ids if provided
        asset_id_list = []
        if asset_ids:
            asset_id_list = [id.strip() for id in asset_ids.split(",")]
        
        # Process each text
        results = []
        for i, text in enumerate(texts):
            if not text:
                continue
                
            try:
                result = await ml_service.detect_language(text, confidence_threshold)
                
                # Add asset_id if provided
                if asset_id_list and i < len(asset_id_list):
                    result["asset_id"] = asset_id_list[i]
                
                results.append(result)
                
            except Exception as e:
                logger.error("Language detection failed for text", text_index=i, error=str(e))
                results.append({
                    "error": str(e),
                    "text_index": i,
                    "text": text[:50] + "..." if len(text) > 50 else text
                })
        
        return {"data": {"results": results, "total_processed": len(results)}}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Batch language detection failed", error=str(e))
        raise HTTPException(status_code=500, detail="Batch language detection failed")


@router.post("/transcribe/multilingual")
async def transcribe_multilingual(
    file: UploadFile = File(...),
    language: Optional[str] = Form(None),
    auto_detect_language: bool = Form(True),
    return_segments: bool = Form(True),
    return_word_timestamps: bool = Form(False),
    asset_id: Optional[str] = Form(None),
    ml_service: MLService = Depends(get_ml_service)
):
    """Transcribe audio with multi-language support and automatic language detection."""
    try:
        # Validate file type
        if not file.content_type.startswith("audio/"):
            raise HTTPException(status_code=400, detail="File must be an audio file")
        
        # Read audio data
        audio_data = await file.read()
        
        # Validate file size
        if len(audio_data) > settings.MAX_AUDIO_SIZE:
            raise HTTPException(
                status_code=413, 
                detail=f"Audio file too large. Maximum size: {settings.MAX_AUDIO_SIZE} bytes"
            )
        
        # Validate language code if provided
        if language:
            valid_languages = [
                "en", "es", "fr", "de", "it", "pt", "ru", "zh", "ja", "ko", "ar", "hi", "tr", "pl", "nl",
                "sv", "da", "no", "fi", "cs", "hu", "el", "he", "th", "vi", "id", "ms", "tl", "uk", "bg",
                "hr", "sk", "sl", "et", "lv", "lt", "ro", "ca", "eu", "gl", "cy", "ga", "is", "mt", "sq",
                "mk", "be", "ka", "hy", "az", "kk", "ky", "uz", "mn", "ne", "si", "my", "km", "lo", "bn",
                "ta", "te", "ml", "kn", "gu", "pa", "or", "mr", "as", "ur", "fa", "ps", "sw", "yo", "zu",
                "xh", "af", "am", "so", "ha", "ig"
            ]
            if language not in valid_languages:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Unsupported language code: {language}. Supported: {', '.join(valid_languages)}"
                )
        
        # Run multilingual transcription
        results = await ml_service.transcribe_audio_multilingual(
            audio_data=audio_data,
            language=language,
            auto_detect_language=auto_detect_language
        )
        
        # Add asset_id to results if provided
        if asset_id:
            results["asset_id"] = asset_id
        
        return {"data": results}
    
    except HTTPException:
        raise
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except InferenceError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error("Multilingual transcription failed", error=str(e))
        raise HTTPException(status_code=500, detail="Multilingual transcription failed")


@router.post("/analyze/multilingual")
async def analyze_multilingual(
    text: str = Form(...),
    auto_detect_language: bool = Form(True),
    target_language: Optional[str] = Form(None),
    include_sentiment: bool = Form(True),
    include_moderation: bool = Form(True),
    moderation_threshold: float = Form(0.5),
    asset_id: Optional[str] = Form(None),
    ml_service: MLService = Depends(get_ml_service)
):
    """Comprehensive multilingual text analysis including language detection, sentiment, and moderation."""
    try:
        # Validate input
        if not text:
            raise HTTPException(status_code=400, detail="Text content is required")
        
        # Validate thresholds
        if moderation_threshold < 0.0 or moderation_threshold > 1.0:
            raise HTTPException(status_code=400, detail="Moderation threshold must be between 0.0 and 1.0")
        
        # Start with language detection if requested
        analysis_results = {}
        
        if auto_detect_language:
            language_result = await ml_service.detect_language(text)
            analysis_results["language_detection"] = language_result
            detected_language = language_result["detected_language"]
        else:
            detected_language = target_language or "en"
        
        # Run additional analyses concurrently
        tasks = []
        
        if include_sentiment:
            tasks.append(("sentiment", ml_service.analyze_sentiment(text)))
        
        if include_moderation:
            tasks.append(("moderation", ml_service.moderate_content(text, moderation_threshold)))
        
        # Execute concurrent analyses
        if tasks:
            task_results = await asyncio.gather(*[task[1] for task in tasks])
            for i, (analysis_type, _) in enumerate(tasks):
                analysis_results[analysis_type] = task_results[i]
        
        # Combine results
        combined_results = {
            "text": text,
            "detected_language": detected_language,
            "analyses": analysis_results,
            "asset_id": asset_id
        }
        
        return {"data": combined_results}
    
    except HTTPException:
        raise
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except InferenceError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error("Multilingual analysis failed", error=str(e))
        raise HTTPException(status_code=500, detail="Multilingual analysis failed")


@router.get("/supported-languages")
async def get_supported_languages():
    """Get list of supported languages for various AI/ML operations."""
    try:
        languages = {
            "speech_to_text": {
                "whisper_supported": [
                    {"code": "en", "name": "English"},
                    {"code": "es", "name": "Spanish"},
                    {"code": "fr", "name": "French"},
                    {"code": "de", "name": "German"},
                    {"code": "it", "name": "Italian"},
                    {"code": "pt", "name": "Portuguese"},
                    {"code": "ru", "name": "Russian"},
                    {"code": "zh", "name": "Chinese"},
                    {"code": "ja", "name": "Japanese"},
                    {"code": "ko", "name": "Korean"},
                    {"code": "ar", "name": "Arabic"},
                    {"code": "hi", "name": "Hindi"},
                    {"code": "tr", "name": "Turkish"},
                    {"code": "pl", "name": "Polish"},
                    {"code": "nl", "name": "Dutch"},
                    {"code": "sv", "name": "Swedish"},
                    {"code": "da", "name": "Danish"},
                    {"code": "no", "name": "Norwegian"},
                    {"code": "fi", "name": "Finnish"},
                    {"code": "cs", "name": "Czech"},
                    {"code": "hu", "name": "Hungarian"},
                    {"code": "el", "name": "Greek"},
                    {"code": "he", "name": "Hebrew"},
                    {"code": "th", "name": "Thai"},
                    {"code": "vi", "name": "Vietnamese"},
                    {"code": "id", "name": "Indonesian"},
                    {"code": "ms", "name": "Malay"},
                    {"code": "tl", "name": "Filipino"},
                    {"code": "uk", "name": "Ukrainian"},
                    {"code": "bg", "name": "Bulgarian"},
                    {"code": "hr", "name": "Croatian"},
                    {"code": "sk", "name": "Slovak"},
                    {"code": "sl", "name": "Slovenian"},
                    {"code": "et", "name": "Estonian"},
                    {"code": "lv", "name": "Latvian"},
                    {"code": "lt", "name": "Lithuanian"},
                    {"code": "ro", "name": "Romanian"},
                    {"code": "ca", "name": "Catalan"},
                    {"code": "eu", "name": "Basque"},
                    {"code": "gl", "name": "Galician"},
                    {"code": "cy", "name": "Welsh"},
                    {"code": "ga", "name": "Irish"},
                    {"code": "is", "name": "Icelandic"},
                    {"code": "mt", "name": "Maltese"},
                    {"code": "sq", "name": "Albanian"},
                    {"code": "mk", "name": "Macedonian"},
                    {"code": "be", "name": "Belarusian"},
                    {"code": "ka", "name": "Georgian"},
                    {"code": "hy", "name": "Armenian"},
                    {"code": "az", "name": "Azerbaijani"},
                    {"code": "kk", "name": "Kazakh"},
                    {"code": "ky", "name": "Kyrgyz"},
                    {"code": "uz", "name": "Uzbek"},
                    {"code": "mn", "name": "Mongolian"},
                    {"code": "ne", "name": "Nepali"},
                    {"code": "si", "name": "Sinhala"},
                    {"code": "my", "name": "Myanmar"},
                    {"code": "km", "name": "Khmer"},
                    {"code": "lo", "name": "Lao"},
                    {"code": "bn", "name": "Bengali"},
                    {"code": "ta", "name": "Tamil"},
                    {"code": "te", "name": "Telugu"},
                    {"code": "ml", "name": "Malayalam"},
                    {"code": "kn", "name": "Kannada"},
                    {"code": "gu", "name": "Gujarati"},
                    {"code": "pa", "name": "Punjabi"},
                    {"code": "or", "name": "Oriya"},
                    {"code": "mr", "name": "Marathi"},
                    {"code": "as", "name": "Assamese"},
                    {"code": "ur", "name": "Urdu"},
                    {"code": "fa", "name": "Persian"},
                    {"code": "ps", "name": "Pashto"},
                    {"code": "sw", "name": "Swahili"},
                    {"code": "yo", "name": "Yoruba"},
                    {"code": "zu", "name": "Zulu"},
                    {"code": "xh", "name": "Xhosa"},
                    {"code": "af", "name": "Afrikaans"},
                    {"code": "am", "name": "Amharic"},
                    {"code": "so", "name": "Somali"},
                    {"code": "ha", "name": "Hausa"},
                    {"code": "ig", "name": "Igbo"}
                ]
            },
            "language_detection": {
                "langdetect_supported": [
                    {"code": "en", "name": "English"},
                    {"code": "es", "name": "Spanish"},
                    {"code": "fr", "name": "French"},
                    {"code": "de", "name": "German"},
                    {"code": "it", "name": "Italian"},
                    {"code": "pt", "name": "Portuguese"},
                    {"code": "ru", "name": "Russian"},
                    {"code": "zh", "name": "Chinese"},
                    {"code": "ja", "name": "Japanese"},
                    {"code": "ko", "name": "Korean"},
                    {"code": "ar", "name": "Arabic"},
                    {"code": "hi", "name": "Hindi"},
                    {"code": "tr", "name": "Turkish"},
                    {"code": "pl", "name": "Polish"},
                    {"code": "nl", "name": "Dutch"},
                    {"code": "sv", "name": "Swedish"},
                    {"code": "da", "name": "Danish"},
                    {"code": "no", "name": "Norwegian"},
                    {"code": "fi", "name": "Finnish"},
                    {"code": "cs", "name": "Czech"},
                    {"code": "hu", "name": "Hungarian"},
                    {"code": "el", "name": "Greek"},
                    {"code": "he", "name": "Hebrew"},
                    {"code": "th", "name": "Thai"},
                    {"code": "vi", "name": "Vietnamese"},
                    {"code": "id", "name": "Indonesian"},
                    {"code": "ms", "name": "Malay"},
                    {"code": "tl", "name": "Filipino"},
                    {"code": "uk", "name": "Ukrainian"},
                    {"code": "bg", "name": "Bulgarian"},
                    {"code": "hr", "name": "Croatian"},
                    {"code": "sk", "name": "Slovak"},
                    {"code": "sl", "name": "Slovenian"},
                    {"code": "et", "name": "Estonian"},
                    {"code": "lv", "name": "Latvian"},
                    {"code": "lt", "name": "Lithuanian"},
                    {"code": "ro", "name": "Romanian"},
                    {"code": "ca", "name": "Catalan"},
                    {"code": "eu", "name": "Basque"},
                    {"code": "gl", "name": "Galician"},
                    {"code": "cy", "name": "Welsh"},
                    {"code": "ga", "name": "Irish"},
                    {"code": "is", "name": "Icelandic"},
                    {"code": "mt", "name": "Maltese"},
                    {"code": "sq", "name": "Albanian"},
                    {"code": "mk", "name": "Macedonian"},
                    {"code": "be", "name": "Belarusian"},
                    {"code": "ka", "name": "Georgian"},
                    {"code": "hy", "name": "Armenian"},
                    {"code": "az", "name": "Azerbaijani"},
                    {"code": "kk", "name": "Kazakh"},
                    {"code": "ky", "name": "Kyrgyz"},
                    {"code": "uz", "name": "Uzbek"},
                    {"code": "mn", "name": "Mongolian"},
                    {"code": "ne", "name": "Nepali"},
                    {"code": "si", "name": "Sinhala"},
                    {"code": "my", "name": "Myanmar"},
                    {"code": "km", "name": "Khmer"},
                    {"code": "lo", "name": "Lao"},
                    {"code": "bn", "name": "Bengali"},
                    {"code": "ta", "name": "Tamil"},
                    {"code": "te", "name": "Telugu"},
                    {"code": "ml", "name": "Malayalam"},
                    {"code": "kn", "name": "Kannada"},
                    {"code": "gu", "name": "Gujarati"},
                    {"code": "pa", "name": "Punjabi"},
                    {"code": "or", "name": "Oriya"},
                    {"code": "mr", "name": "Marathi"},
                    {"code": "as", "name": "Assamese"},
                    {"code": "ur", "name": "Urdu"},
                    {"code": "fa", "name": "Persian"},
                    {"code": "ps", "name": "Pashto"},
                    {"code": "sw", "name": "Swahili"},
                    {"code": "yo", "name": "Yoruba"},
                    {"code": "zu", "name": "Zulu"},
                    {"code": "xh", "name": "Xhosa"},
                    {"code": "af", "name": "Afrikaans"},
                    {"code": "am", "name": "Amharic"},
                    {"code": "so", "name": "Somali"},
                    {"code": "ha", "name": "Hausa"},
                    {"code": "ig", "name": "Igbo"}
                ]
            }
        }
        
        return {"data": languages}
    
    except Exception as e:
        logger.error("Failed to get supported languages", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get supported languages")


@router.post("/transcribe/with-speakers")
async def transcribe_with_speakers(
    file: UploadFile = File(...),
    language: Optional[str] = Form(None),
    num_speakers: Optional[int] = Form(None),
    min_speakers: int = Form(1),
    max_speakers: int = Form(10),
    auto_detect_language: bool = Form(True),
    return_segments: bool = Form(True),
    asset_id: Optional[str] = Form(None),
    ml_service: MLService = Depends(get_ml_service)
):
    """Transcribe audio with speaker diarization."""
    try:
        # Validate file type
        if not file.content_type.startswith("audio/"):
            raise HTTPException(status_code=400, detail="File must be an audio file")
        
        # Read audio data
        audio_data = await file.read()
        
        # Validate file size
        if len(audio_data) > settings.MAX_AUDIO_SIZE:
            raise HTTPException(
                status_code=413, 
                detail=f"Audio file too large. Maximum size: {settings.MAX_AUDIO_SIZE} bytes"
            )
        
        # Validate speaker parameters
        if num_speakers is not None and (num_speakers < 1 or num_speakers > 20):
            raise HTTPException(status_code=400, detail="Number of speakers must be between 1 and 20")
        
        if min_speakers < 1 or min_speakers > 20:
            raise HTTPException(status_code=400, detail="Minimum speakers must be between 1 and 20")
        
        if max_speakers < 1 or max_speakers > 20:
            raise HTTPException(status_code=400, detail="Maximum speakers must be between 1 and 20")
        
        if min_speakers > max_speakers:
            raise HTTPException(status_code=400, detail="Minimum speakers cannot be greater than maximum speakers")
        
        # Run transcription with speaker diarization
        results = await ml_service.transcribe_with_speakers(
            audio_data=audio_data,
            language=language,
            num_speakers=num_speakers,
            min_speakers=min_speakers,
            max_speakers=max_speakers,
            auto_detect_language=auto_detect_language,
            return_segments=return_segments
        )
        
        # Add asset_id to results if provided
        if asset_id:
            results["asset_id"] = asset_id
        
        return {"data": results}
    
    except HTTPException:
        raise
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except InferenceError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error("Transcription with speakers failed", error=str(e))
        raise HTTPException(status_code=500, detail="Transcription with speakers failed")


@router.post("/diarize/speakers")
async def diarize_speakers(
    file: UploadFile = File(...),
    num_speakers: Optional[int] = Form(None),
    min_speakers: int = Form(1),
    max_speakers: int = Form(10),
    asset_id: Optional[str] = Form(None),
    ml_service: MLService = Depends(get_ml_service)
):
    """Perform speaker diarization on audio to identify different speakers."""
    try:
        # Validate file type
        if not file.content_type.startswith("audio/"):
            raise HTTPException(status_code=400, detail="File must be an audio file")
        
        # Read audio data
        audio_data = await file.read()
        
        # Validate file size
        if len(audio_data) > settings.MAX_AUDIO_SIZE:
            raise HTTPException(
                status_code=413, 
                detail=f"Audio file too large. Maximum size: {settings.MAX_AUDIO_SIZE} bytes"
            )
        
        # Validate speaker parameters
        if num_speakers is not None and (num_speakers < 1 or num_speakers > 20):
            raise HTTPException(status_code=400, detail="Number of speakers must be between 1 and 20")
        
        if min_speakers < 1 or min_speakers > 20:
            raise HTTPException(status_code=400, detail="Minimum speakers must be between 1 and 20")
        
        if max_speakers < 1 or max_speakers > 20:
            raise HTTPException(status_code=400, detail="Maximum speakers must be between 1 and 20")
        
        if min_speakers > max_speakers:
            raise HTTPException(status_code=400, detail="Minimum speakers cannot be greater than maximum speakers")
        
        # Run speaker diarization
        results = await ml_service.diarize_speakers(
            audio_data=audio_data,
            num_speakers=num_speakers,
            min_speakers=min_speakers,
            max_speakers=max_speakers
        )
        
        # Add asset_id to results if provided
        if asset_id:
            results["asset_id"] = asset_id
        
        return {"data": results}
    
    except HTTPException:
        raise
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except InferenceError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error("Speaker diarization failed", error=str(e))
        raise HTTPException(status_code=500, detail="Speaker diarization failed")


@router.get("/diarize/speakers/model-info")
async def get_speaker_diarization_model_info(ml_service: MLService = Depends(get_ml_service)):
    """Get speaker diarization model information."""
    try:
        from ..main import app
        model_manager = app.state.model_manager
        
        # Get model info
        model_info = model_manager.get_model_info("speaker_diarization")
        
        if not model_info:
            raise HTTPException(status_code=404, detail="Speaker diarization model not loaded")
        
        return {"data": model_info}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get speaker diarization model info", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get speaker diarization model information")


@router.post("/extract/keywords")
async def extract_keywords(
    text: str = Form(...),
    max_keywords: int = Form(10),
    algorithm: str = Form("tfidf"),
    language: Optional[str] = Form(None),
    asset_id: Optional[str] = Form(None),
    ml_service: MLService = Depends(get_ml_service)
):
    """Extract keywords from text content."""
    try:
        # Validate input
        if not text:
            raise HTTPException(status_code=400, detail="Text content is required")
        
        # Validate max_keywords
        if max_keywords < 1 or max_keywords > 50:
            raise HTTPException(status_code=400, detail="Max keywords must be between 1 and 50")
        
        # Validate algorithm
        valid_algorithms = ["tfidf", "textrank", "yake", "bert"]
        if algorithm not in valid_algorithms:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid algorithm. Supported: {', '.join(valid_algorithms)}"
            )
        
        # Run keyword extraction
        results = await ml_service.extract_keywords(
            text=text,
            max_keywords=max_keywords,
            algorithm=algorithm,
            language=language
        )
        
        # Add asset_id to results if provided
        if asset_id:
            results["asset_id"] = asset_id
        
        return {"data": results}
    
    except HTTPException:
        raise
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except InferenceError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error("Keyword extraction failed", error=str(e))
        raise HTTPException(status_code=500, detail="Keyword extraction failed")


@router.post("/extract/keywords/batch")
async def extract_keywords_batch(
    texts: List[str] = Form(...),
    max_keywords: int = Form(10),
    algorithm: str = Form("tfidf"),
    language: Optional[str] = Form(None),
    asset_ids: Optional[str] = Form(None),
    ml_service: MLService = Depends(get_ml_service)
):
    """Extract keywords from multiple texts."""
    try:
        # Validate batch size
        if len(texts) > 20:  # Limit batch size
            raise HTTPException(status_code=400, detail="Maximum batch size is 20 texts")
        
        # Validate max_keywords
        if max_keywords < 1 or max_keywords > 50:
            raise HTTPException(status_code=400, detail="Max keywords must be between 1 and 50")
        
        # Validate algorithm
        valid_algorithms = ["tfidf", "textrank", "yake", "bert"]
        if algorithm not in valid_algorithms:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid algorithm. Supported: {', '.join(valid_algorithms)}"
            )
        
        # Parse asset_ids if provided
        asset_id_list = []
        if asset_ids:
            asset_id_list = [id.strip() for id in asset_ids.split(",")]
        
        # Process each text
        results = []
        for i, text in enumerate(texts):
            if not text:
                continue
                
            try:
                result = await ml_service.extract_keywords(
                    text=text,
                    max_keywords=max_keywords,
                    algorithm=algorithm,
                    language=language
                )
                
                # Add asset_id if provided
                if asset_id_list and i < len(asset_id_list):
                    result["asset_id"] = asset_id_list[i]
                
                results.append(result)
                
            except Exception as e:
                logger.error("Keyword extraction failed for text", text_index=i, error=str(e))
                results.append({
                    "error": str(e),
                    "text_index": i,
                    "text": text[:50] + "..." if len(text) > 50 else text
                })
        
        return {"data": {"results": results, "total_processed": len(results)}}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Batch keyword extraction failed", error=str(e))
        raise HTTPException(status_code=500, detail="Batch keyword extraction failed")


@router.get("/extract/keywords/algorithms")
async def get_supported_keyword_algorithms():
    """Get supported keyword extraction algorithms."""
    try:
        algorithms = [
            {
                "name": "tfidf",
                "description": "TF-IDF (Term Frequency-Inverse Document Frequency)",
                "features": ["Fast", "Language-independent", "Good for general content"]
            },
            {
                "name": "textrank",
                "description": "TextRank algorithm based on PageRank",
                "features": ["Graph-based", "Good for coherent text", "Unsupervised"]
            },
            {
                "name": "yake",
                "description": "Yet Another Keyword Extractor",
                "features": ["Unsupervised", "Language-independent", "Good for short texts"]
            },
            {
                "name": "bert",
                "description": "BERT-based semantic keyword extraction",
                "features": ["Semantic understanding", "Context-aware", "State-of-the-art"]
            }
        ]
        
        return {"data": {"algorithms": algorithms, "total": len(algorithms)}}
    
    except Exception as e:
        logger.error("Failed to get supported keyword algorithms", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get supported keyword algorithms")


@router.get("/extract/keywords/model-info")
async def get_keyword_extraction_model_info(ml_service: MLService = Depends(get_ml_service)):
    """Get keyword extraction model information."""
    try:
        from ..main import app
        model_manager = app.state.model_manager
        
        # Get model info
        model_info = model_manager.get_model_info("keyword_extraction")
        
        if not model_info:
            raise HTTPException(status_code=404, detail="Keyword extraction model not loaded")
        
        return {"data": model_info}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get keyword extraction model info", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get keyword extraction model information")


@router.post("/recognize/entities")
async def recognize_entities(
    text: str = Form(...),
    confidence_threshold: float = Form(0.8),
    entity_types: Optional[str] = Form(None),
    asset_id: Optional[str] = Form(None),
    ml_service: MLService = Depends(get_ml_service)
):
    """Recognize named entities in text content."""
    try:
        # Validate input
        if not text:
            raise HTTPException(status_code=400, detail="Text content is required")
        
        # Validate confidence threshold
        if confidence_threshold < 0.0 or confidence_threshold > 1.0:
            raise HTTPException(status_code=400, detail="Confidence threshold must be between 0.0 and 1.0")
        
        # Parse entity types if provided
        parsed_entity_types = None
        if entity_types:
            parsed_entity_types = [et.strip() for et in entity_types.split(",")]
        
        # Run entity recognition
        results = await ml_service.recognize_entities(
            text=text,
            confidence_threshold=confidence_threshold,
            entity_types=parsed_entity_types
        )
        
        # Add asset_id to results if provided
        if asset_id:
            results["asset_id"] = asset_id
        
        return {"data": results}
    
    except HTTPException:
        raise
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except InferenceError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error("Entity recognition failed", error=str(e))
        raise HTTPException(status_code=500, detail="Entity recognition failed")


@router.post("/recognize/entities/batch")
async def recognize_entities_batch(
    texts: List[str] = Form(...),
    confidence_threshold: float = Form(0.8),
    entity_types: Optional[str] = Form(None),
    asset_ids: Optional[str] = Form(None),
    ml_service: MLService = Depends(get_ml_service)
):
    """Recognize named entities in multiple texts."""
    try:
        # Validate batch size
        if len(texts) > 20:  # Limit batch size
            raise HTTPException(status_code=400, detail="Maximum batch size is 20 texts")
        
        # Validate confidence threshold
        if confidence_threshold < 0.0 or confidence_threshold > 1.0:
            raise HTTPException(status_code=400, detail="Confidence threshold must be between 0.0 and 1.0")
        
        # Parse entity types if provided
        parsed_entity_types = None
        if entity_types:
            parsed_entity_types = [et.strip() for et in entity_types.split(",")]
        
        # Parse asset_ids if provided
        asset_id_list = []
        if asset_ids:
            asset_id_list = [id.strip() for id in asset_ids.split(",")]
        
        # Process each text
        results = []
        for i, text in enumerate(texts):
            if not text:
                continue
                
            try:
                result = await ml_service.recognize_entities(
                    text=text,
                    confidence_threshold=confidence_threshold,
                    entity_types=parsed_entity_types
                )
                
                # Add asset_id if provided
                if asset_id_list and i < len(asset_id_list):
                    result["asset_id"] = asset_id_list[i]
                
                results.append(result)
                
            except Exception as e:
                logger.error("Entity recognition failed for text", text_index=i, error=str(e))
                results.append({
                    "error": str(e),
                    "text_index": i,
                    "text": text[:50] + "..." if len(text) > 50 else text
                })
        
        return {"data": {"results": results, "total_processed": len(results)}}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Batch entity recognition failed", error=str(e))
        raise HTTPException(status_code=500, detail="Batch entity recognition failed")


@router.get("/recognize/entities/types")
async def get_supported_entity_types():
    """Get supported entity types for named entity recognition."""
    try:
        entity_types = [
            {
                "type": "PERSON",
                "description": "Names of people",
                "examples": ["John Smith", "Dr. Johnson", "Maria Garcia"]
            },
            {
                "type": "ORG",
                "description": "Organizations and companies",
                "examples": ["Microsoft", "NASA", "European Union"]
            },
            {
                "type": "LOC",
                "description": "Locations and places",
                "examples": ["New York", "Paris", "Mount Everest"]
            },
            {
                "type": "MISC",
                "description": "Miscellaneous entities",
                "examples": ["dates", "times", "events"]
            }
        ]
        
        return {"data": {"entity_types": entity_types, "total": len(entity_types)}}
    
    except Exception as e:
        logger.error("Failed to get supported entity types", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get supported entity types")


@router.get("/recognize/entities/model-info")
async def get_entity_recognition_model_info(ml_service: MLService = Depends(get_ml_service)):
    """Get entity recognition model information."""
    try:
        from ..main import app
        model_manager = app.state.model_manager
        
        # Get model info
        model_info = model_manager.get_model_info("entity_recognition")
        
        if not model_info:
            raise HTTPException(status_code=404, detail="Entity recognition model not loaded")
        
        return {"data": model_info}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get entity recognition model info", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get entity recognition model information")


@router.get("/metrics")
async def get_metrics():
    """Get service metrics."""
    # TODO: Implement metrics collection
    return {
        "data": {
            "service": "ai-ml-service",
            "version": settings.VERSION,
            "status": "healthy"
        }
    }