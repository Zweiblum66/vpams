"""
API Routes for Proxy Generation Service
"""

import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from pydantic import BaseModel, Field

from ..core.logging import get_logger
from ..services.queue_service import JobPriority
from .dependencies import (
    get_current_user,
    get_queue_service,
    get_storage_service,
    get_proxy_processor
)

logger = get_logger(__name__)

router = APIRouter()


# Request/Response Models
class ProxyJobRequest(BaseModel):
    """Request model for creating proxy job"""
    asset_id: str = Field(..., description="Asset ID to generate proxy for")
    input_path: str = Field(..., description="Path to input media file")
    job_type: str = Field(..., description="Type of proxy to generate")
    parameters: Dict[str, Any] = Field({}, description="Job-specific parameters")
    priority: JobPriority = Field(JobPriority.NORMAL, description="Job priority")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class ProxyJobResponse(BaseModel):
    """Response model for proxy job"""
    job_id: str = Field(..., description="Unique job ID")
    asset_id: str = Field(..., description="Asset ID")
    job_type: str = Field(..., description="Proxy type")
    status: str = Field(..., description="Job status")
    message: str = Field(..., description="Status message")


class QueueStatusResponse(BaseModel):
    """Response model for queue status"""
    queue_name: str = Field(..., description="Queue name")
    message_count: int = Field(..., description="Number of messages in queue")
    consumer_count: int = Field(..., description="Number of active consumers")
    active_jobs: int = Field(..., description="Number of active jobs")
    max_concurrent_jobs: int = Field(..., description="Maximum concurrent jobs")


class MediaInfoResponse(BaseModel):
    """Response model for media information"""
    format: Dict[str, Any] = Field(..., description="Media format information")
    duration: float = Field(..., description="Duration in seconds")
    size: int = Field(..., description="File size in bytes")
    bit_rate: int = Field(..., description="Overall bit rate")
    streams: List[Dict[str, Any]] = Field(..., description="Stream information")


# Thumbnail-related request models
class ThumbnailBatchRequest(BaseModel):
    """Request model for batch thumbnail generation"""
    asset_id: str = Field(..., description="Asset ID to generate thumbnails for")
    input_path: str = Field(..., description="Path to input video file")
    count: int = Field(10, ge=1, le=100, description="Number of thumbnails to generate")
    width: int = Field(320, ge=64, le=3840, description="Thumbnail width")
    height: int = Field(180, ge=64, le=2160, description="Thumbnail height")
    format: str = Field("jpg", pattern="^(jpg|jpeg|png|webp)$", description="Output format")
    quality: int = Field(85, ge=1, le=100, description="Quality for lossy formats")
    start_time: float = Field(0, ge=0, description="Start time in seconds")
    duration: Optional[float] = Field(None, ge=0, description="Duration to sample from")
    method: str = Field("interval", pattern="^(interval|scene|keyframe)$", description="Thumbnail selection method")
    priority: JobPriority = Field(JobPriority.NORMAL, description="Job priority")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class ThumbnailSingleRequest(BaseModel):
    """Request model for single thumbnail generation"""
    asset_id: str = Field(..., description="Asset ID to generate thumbnail for")
    input_path: str = Field(..., description="Path to input video file")
    time_offset: Optional[str] = Field("auto", description="Time offset in seconds or 'auto'")
    width: int = Field(320, ge=64, le=3840, description="Thumbnail width")
    height: int = Field(180, ge=64, le=2160, description="Thumbnail height")
    format: str = Field("jpg", pattern="^(jpg|jpeg|png|webp)$", description="Output format")
    quality: int = Field(85, ge=1, le=100, description="Quality for lossy formats")
    priority: JobPriority = Field(JobPriority.NORMAL, description="Job priority")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class ContactSheetRequest(BaseModel):
    """Request model for contact sheet generation"""
    asset_id: str = Field(..., description="Asset ID to generate contact sheet for")
    input_path: str = Field(..., description="Path to input video file")
    grid_size: List[int] = Field([4, 4], min_items=2, max_items=2, description="Grid dimensions [columns, rows]")
    thumb_width: int = Field(320, ge=64, le=1920, description="Individual thumbnail width")
    thumb_height: int = Field(180, ge=64, le=1080, description="Individual thumbnail height")
    padding: int = Field(5, ge=0, le=50, description="Padding between thumbnails")
    background_color: str = Field("black", description="Background color")
    include_timestamps: bool = Field(True, description="Include timestamp overlay")
    font_size: int = Field(12, ge=8, le=48, description="Font size for timestamps")
    font_color: str = Field("white", description="Font color for timestamps")
    priority: JobPriority = Field(JobPriority.NORMAL, description="Job priority")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class WaveformRequest(BaseModel):
    """Request model for waveform generation"""
    asset_id: str = Field(..., description="Asset ID to generate waveform for")
    input_path: str = Field(..., description="Path to input audio/video file")
    width: int = Field(1920, ge=100, le=4096, description="Waveform width")
    height: int = Field(200, ge=50, le=1080, description="Waveform height")
    style: str = Field("line", pattern="^(line|fill|cline)$", description="Waveform style")
    colors: Optional[Dict[str, str]] = Field(None, description="Custom colors for waveform")
    split_channels: bool = Field(False, description="Split stereo channels")
    show_axis: bool = Field(True, description="Show time axis")
    logarithmic: bool = Field(False, description="Use logarithmic scale")
    priority: JobPriority = Field(JobPriority.NORMAL, description="Job priority")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class SpectralWaveformRequest(BaseModel):
    """Request model for spectral waveform (spectrogram) generation"""
    asset_id: str = Field(..., description="Asset ID to generate spectrogram for")
    input_path: str = Field(..., description="Path to input audio/video file")
    width: int = Field(1920, ge=100, le=4096, description="Spectrogram width")
    height: int = Field(512, ge=100, le=2048, description="Spectrogram height")
    color_mode: str = Field("intensity", pattern="^(intensity|rainbow|fire|cool)$", description="Color scheme")
    frequency_scale: str = Field("lin", pattern="^(lin|log|sqrt)$", description="Frequency scale")
    window_size: int = Field(2048, ge=128, le=8192, description="FFT window size")
    overlap: float = Field(0.875, ge=0.0, le=0.99, description="Window overlap factor")
    priority: JobPriority = Field(JobPriority.NORMAL, description="Job priority")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class VectorscopeRequest(BaseModel):
    """Request model for vectorscope generation"""
    asset_id: str = Field(..., description="Asset ID to generate vectorscope for")
    input_path: str = Field(..., description="Path to input audio/video file")
    width: int = Field(256, ge=128, le=1024, description="Vectorscope width")
    height: int = Field(256, ge=128, le=1024, description="Vectorscope height")
    mode: str = Field("lissajous", pattern="^(lissajous|lissajous_xy)$", description="Display mode")
    intensity: float = Field(0.04, ge=0.01, le=1.0, description="Display intensity")
    zoom: float = Field(1.0, ge=0.1, le=10.0, description="Zoom level")
    priority: JobPriority = Field(JobPriority.NORMAL, description="Job priority")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class AudioPeakDetectionRequest(BaseModel):
    """Request model for audio peak detection"""
    asset_id: str = Field(..., description="Asset ID to analyze")
    input_path: str = Field(..., description="Path to input audio/video file")
    threshold: float = Field(-20.0, ge=-60.0, le=0.0, description="Peak detection threshold in dB")
    min_duration: float = Field(0.1, ge=0.01, le=10.0, description="Minimum peak duration in seconds")
    channel: Optional[int] = Field(None, ge=0, le=7, description="Specific channel to analyze (None = all)")
    priority: JobPriority = Field(JobPriority.NORMAL, description="Job priority")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class AudioLevelExtractionRequest(BaseModel):
    """Request model for audio level extraction"""
    asset_id: str = Field(..., description="Asset ID to analyze")
    input_path: str = Field(..., description="Path to input audio/video file")
    interval: float = Field(0.1, ge=0.01, le=10.0, description="Sampling interval in seconds")
    priority: JobPriority = Field(JobPriority.NORMAL, description="Job priority")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class AudioFormatConversionRequest(BaseModel):
    """Request model for audio format conversion"""
    asset_id: str = Field(..., description="Asset ID to convert")
    input_path: str = Field(..., description="Path to input audio/video file")
    output_format: str = Field("mp3", pattern="^(mp3|aac|m4a|flac|wav|opus|ogg|ac3|wma)$", description="Target audio format")
    codec: Optional[str] = Field(None, description="Audio codec to use (auto-selected if None)")
    bitrate: Optional[str] = Field(None, pattern="^\\d+k$", description="Target bitrate (e.g., '192k', '320k')")
    sample_rate: Optional[int] = Field(None, ge=8000, le=192000, description="Target sample rate")
    channels: Optional[int] = Field(None, ge=1, le=8, description="Number of output channels")
    normalize: bool = Field(False, description="Apply loudness normalization")
    target_level: float = Field(-23.0, ge=-70.0, le=0.0, description="Target loudness level (if normalize=True)")
    priority: JobPriority = Field(JobPriority.NORMAL, description="Job priority")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class ImageFormatConversionRequest(BaseModel):
    """Request model for image format conversion"""
    asset_id: str = Field(..., description="Asset ID to convert")
    input_path: str = Field(..., description="Path to input image file")
    output_format: str = Field("jpg", pattern="^(jpg|jpeg|png|webp|bmp|tiff|gif)$", description="Target image format")
    width: Optional[int] = Field(None, ge=1, le=8192, description="Target width (None to keep original)")
    height: Optional[int] = Field(None, ge=1, le=8192, description="Target height (None to keep original)")
    quality: Optional[int] = Field(None, ge=1, le=100, description="Quality for lossy formats")
    preserve_aspect_ratio: bool = Field(True, description="Maintain aspect ratio when resizing")
    priority: JobPriority = Field(JobPriority.NORMAL, description="Job priority")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class ImageSequenceConversionRequest(BaseModel):
    """Request model for image sequence to video/gif conversion"""
    asset_id: str = Field(..., description="Asset ID for the sequence")
    input_pattern: str = Field(..., description="Input pattern (e.g., 'frame_%04d.png')")
    output_format: str = Field("mp4", pattern="^(mp4|webm|gif|avi|mov)$", description="Target format")
    frame_rate: int = Field(24, ge=1, le=120, description="Output frame rate")
    quality: Optional[str] = Field(None, description="Quality setting (format-specific)")
    priority: JobPriority = Field(JobPriority.NORMAL, description="Job priority")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class QualityVariant(BaseModel):
    """Model for adaptive bitrate quality variant"""
    name: str = Field(..., description="Quality variant name (e.g., '720p', '1080p')")
    width: int = Field(..., ge=128, le=7680, description="Video width")
    height: int = Field(..., ge=128, le=4320, description="Video height")
    bitrate: str = Field(..., pattern="^\\d+[kKmM]$", description="Video bitrate (e.g., '2800k', '5M')")
    audio_bitrate: str = Field("192k", pattern="^\\d+[kKmM]$", description="Audio bitrate (e.g., '128k', '192k')")


class AdaptiveBitrateRequest(BaseModel):
    """Request model for adaptive bitrate stream generation"""
    asset_id: str = Field(..., description="Asset ID to generate streams for")
    input_path: str = Field(..., description="Path to input video file")
    stream_formats: List[str] = Field(["hls", "dash"], description="Streaming formats to generate")
    qualities: Optional[List[QualityVariant]] = Field(None, description="Quality variants (auto-generated if None)")
    segment_duration: int = Field(6, ge=1, le=30, description="Segment duration in seconds")
    playlist_type: str = Field("vod", pattern="^(vod|live)$", description="Playlist type")
    force_gpu: bool = Field(True, description="Use GPU acceleration if available")
    priority: JobPriority = Field(JobPriority.HIGH, description="Job priority")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    
    class Config:
        schema_extra = {
            "example": {
                "asset_id": "asset_123",
                "input_path": "/storage/videos/sample.mp4",
                "stream_formats": ["hls", "dash"],
                "qualities": [
                    {
                        "name": "720p",
                        "width": 1280,
                        "height": 720,
                        "bitrate": "2800k",
                        "audio_bitrate": "192k"
                    },
                    {
                        "name": "1080p",
                        "width": 1920,
                        "height": 1080,
                        "bitrate": "5000k",
                        "audio_bitrate": "192k"
                    }
                ],
                "segment_duration": 6,
                "playlist_type": "vod",
                "force_gpu": True,
                "priority": "high"
            }
        }


# Routes
@router.post("/jobs", response_model=ProxyJobResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_proxy_job(
    job_request: ProxyJobRequest,
    current_user: dict = Depends(get_current_user),
    queue_service = Depends(get_queue_service)
):
    """Submit a new proxy generation job"""
    try:
        logger.info(
            "creating_proxy_job",
            user_id=current_user["user_id"],
            asset_id=job_request.asset_id,
            job_type=job_request.job_type
        )
        
        # Submit job to queue
        job_id = await queue_service.submit_job(
            asset_id=job_request.asset_id,
            input_path=job_request.input_path,
            job_type=job_request.job_type,
            parameters=job_request.parameters,
            priority=job_request.priority,
            metadata={
                **(job_request.metadata or {}),
                "submitted_by": current_user["user_id"],
                "submitted_at": datetime.utcnow().isoformat()
            }
        )
        
        return ProxyJobResponse(
            job_id=job_id,
            asset_id=job_request.asset_id,
            job_type=job_request.job_type,
            status="queued",
            message=f"Proxy generation job queued successfully"
        )
        
    except Exception as e:
        logger.error(
            "create_proxy_job_failed",
            error=str(e),
            asset_id=job_request.asset_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create proxy job: {str(e)}"
        )


@router.get("/jobs/active", response_model=List[Dict[str, Any]])
async def get_active_jobs(
    current_user: dict = Depends(get_current_user),
    queue_service = Depends(get_queue_service)
):
    """Get list of active jobs"""
    try:
        active_jobs = queue_service.get_active_jobs()
        
        # Filter by user if not admin
        if "admin" not in current_user.get("roles", []):
            active_jobs = [
                job for job in active_jobs
                if job.get("metadata", {}).get("submitted_by") == current_user["user_id"]
            ]
        
        return active_jobs
        
    except Exception as e:
        logger.error("get_active_jobs_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get active jobs: {str(e)}"
        )


@router.get("/queue/status", response_model=QueueStatusResponse)
async def get_queue_status(
    current_user: dict = Depends(get_current_user),
    queue_service = Depends(get_queue_service)
):
    """Get queue status"""
    try:
        stats = await queue_service.get_queue_stats()
        return QueueStatusResponse(**stats)
        
    except Exception as e:
        logger.error("get_queue_status_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get queue status: {str(e)}"
        )


@router.get("/media/info", response_model=MediaInfoResponse)
async def get_media_info(
    file_path: str = Query(..., description="Path to media file"),
    current_user: dict = Depends(get_current_user),
    proxy_processor = Depends(get_proxy_processor)
):
    """Get media file information"""
    try:
        media_info = await proxy_processor.ffmpeg_service.get_media_info(file_path)
        return MediaInfoResponse(**media_info)
        
    except Exception as e:
        logger.error(
            "get_media_info_failed",
            error=str(e),
            file_path=file_path
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to get media info: {str(e)}"
        )


@router.get("/proxies/{asset_id}")
async def get_asset_proxies(
    asset_id: str = Path(..., description="Asset ID"),
    current_user: dict = Depends(get_current_user),
    storage_service = Depends(get_storage_service)
):
    """Get all proxies for an asset"""
    try:
        # List all proxy types
        proxy_types = ["video", "audio", "thumbnail", "contact_sheet", "waveform"]
        proxies = []
        
        for proxy_type in proxy_types:
            # Check common qualities/formats
            if proxy_type == "video":
                qualities = ["low", "medium", "high", "edit"]
                for quality in qualities:
                    for ext in ["mp4", "webm"]:
                        storage_key = storage_service.generate_storage_key(
                            asset_id=asset_id,
                            proxy_type=proxy_type,
                            quality=quality,
                            extension=ext
                        )
                        
                        if await storage_service.file_exists(storage_key):
                            file_info = await storage_service.get_file_info(storage_key)
                            proxies.append({
                                "proxy_type": proxy_type,
                                "quality": quality,
                                "format": ext,
                                "storage_key": storage_key,
                                **file_info
                            })
            
            elif proxy_type == "thumbnail":
                # Check for thumbnails
                for i in range(10):  # Check up to 10 thumbnails
                    for size in ["small", "medium", "large"]:
                        storage_key = storage_service.generate_storage_key(
                            asset_id=asset_id,
                            proxy_type=proxy_type,
                            quality=f"{size}_{i}",
                            extension="jpg"
                        )
                        
                        if await storage_service.file_exists(storage_key):
                            file_info = await storage_service.get_file_info(storage_key)
                            proxies.append({
                                "proxy_type": proxy_type,
                                "size": size,
                                "index": i,
                                "storage_key": storage_key,
                                **file_info
                            })
            
            else:
                # Check for other proxy types
                storage_key = storage_service.generate_storage_key(
                    asset_id=asset_id,
                    proxy_type=proxy_type,
                    quality="default",
                    extension="jpg" if proxy_type == "contact_sheet" else "png"
                )
                
                if await storage_service.file_exists(storage_key):
                    file_info = await storage_service.get_file_info(storage_key)
                    proxies.append({
                        "proxy_type": proxy_type,
                        "storage_key": storage_key,
                        **file_info
                    })
        
        return {
            "asset_id": asset_id,
            "proxy_count": len(proxies),
            "proxies": proxies
        }
        
    except Exception as e:
        logger.error(
            "get_asset_proxies_failed",
            error=str(e),
            asset_id=asset_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get asset proxies: {str(e)}"
        )


@router.get("/gpu/info")
async def get_gpu_info(
    current_user: dict = Depends(get_current_user),
    proxy_processor = Depends(get_proxy_processor)
):
    """Get GPU acceleration information"""
    try:
        gpu_info = proxy_processor.ffmpeg_service.get_gpu_info()
        return gpu_info
        
    except Exception as e:
        logger.error(
            "get_gpu_info_failed",
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get GPU info: {str(e)}"
        )


@router.post("/gpu/benchmark")
async def benchmark_gpu(
    current_user: dict = Depends(get_current_user),
    proxy_processor = Depends(get_proxy_processor)
):
    """Benchmark GPU encoding performance"""
    try:
        # Only allow admins to run benchmarks
        if "admin" not in current_user.get("roles", []):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin role required for GPU benchmarking"
            )
        
        benchmark_results = await proxy_processor.ffmpeg_service.benchmark_gpu_performance()
        return benchmark_results
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "gpu_benchmark_failed",
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"GPU benchmark failed: {str(e)}"
        )


# Thumbnail generation endpoints
@router.post("/thumbnails/batch")
async def generate_thumbnails(
    request: ThumbnailBatchRequest,
    current_user: dict = Depends(get_current_user),
    proxy_processor = Depends(get_proxy_processor)
):
    """Generate multiple thumbnails from a video"""
    try:
        # Create job for thumbnail generation
        job_params = {
            "count": request.count,
            "width": request.width,
            "height": request.height,
            "format": request.format,
            "quality": request.quality,
            "start_time": request.start_time,
            "duration": request.duration,
            "method": request.method
        }
        
        job_id = await proxy_processor.create_job(
            asset_id=request.asset_id,
            input_path=request.input_path,
            job_type="thumbnail_batch",
            parameters=job_params,
            priority=request.priority,
            metadata=request.metadata
        )
        
        return ProxyJobResponse(
            job_id=job_id,
            status="queued",
            message=f"Thumbnail batch generation job created for {request.count} thumbnails"
        )
        
    except Exception as e:
        logger.error(
            "thumbnail_batch_creation_failed",
            error=str(e),
            asset_id=request.asset_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create thumbnail batch job: {str(e)}"
        )


@router.post("/thumbnails/single")
async def generate_single_thumbnail(
    request: ThumbnailSingleRequest,
    current_user: dict = Depends(get_current_user),
    proxy_processor = Depends(get_proxy_processor)
):
    """Generate a single thumbnail from a video"""
    try:
        # Create job for single thumbnail
        job_params = {
            "time_offset": request.time_offset,
            "width": request.width,
            "height": request.height,
            "format": request.format,
            "quality": request.quality
        }
        
        job_id = await proxy_processor.create_job(
            asset_id=request.asset_id,
            input_path=request.input_path,
            job_type="thumbnail_single",
            parameters=job_params,
            priority=request.priority,
            metadata=request.metadata
        )
        
        return ProxyJobResponse(
            job_id=job_id,
            status="queued",
            message="Single thumbnail generation job created"
        )
        
    except Exception as e:
        logger.error(
            "single_thumbnail_creation_failed",
            error=str(e),
            asset_id=request.asset_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create single thumbnail job: {str(e)}"
        )


@router.post("/thumbnails/contact-sheet")
async def generate_contact_sheet(
    request: ContactSheetRequest,
    current_user: dict = Depends(get_current_user),
    proxy_processor = Depends(get_proxy_processor)
):
    """Generate a contact sheet (sprite/mosaic) from a video"""
    try:
        # Create job for contact sheet
        job_params = {
            "grid_size": request.grid_size,
            "thumb_width": request.thumb_width,
            "thumb_height": request.thumb_height,
            "padding": request.padding,
            "background_color": request.background_color,
            "include_timestamps": request.include_timestamps,
            "font_size": request.font_size,
            "font_color": request.font_color
        }
        
        job_id = await proxy_processor.create_job(
            asset_id=request.asset_id,
            input_path=request.input_path,
            job_type="contact_sheet",
            parameters=job_params,
            priority=request.priority,
            metadata=request.metadata
        )
        
        return ProxyJobResponse(
            job_id=job_id,
            status="queued",
            message=f"Contact sheet generation job created ({request.grid_size[0]}x{request.grid_size[1]} grid)"
        )
        
    except Exception as e:
        logger.error(
            "contact_sheet_creation_failed",
            error=str(e),
            asset_id=request.asset_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create contact sheet job: {str(e)}"
        )


# Waveform generation endpoints
@router.post("/waveform/generate")
async def generate_waveform(
    request: WaveformRequest,
    current_user: dict = Depends(get_current_user),
    proxy_processor = Depends(get_proxy_processor)
):
    """Generate an audio waveform visualization"""
    try:
        # Create job for waveform generation
        job_params = {
            "width": request.width,
            "height": request.height,
            "style": request.style,
            "colors": request.colors,
            "split_channels": request.split_channels,
            "show_axis": request.show_axis,
            "logarithmic": request.logarithmic
        }
        
        job_id = await proxy_processor.create_job(
            asset_id=request.asset_id,
            input_path=request.input_path,
            job_type="waveform",
            parameters=job_params,
            priority=request.priority,
            metadata=request.metadata
        )
        
        return ProxyJobResponse(
            job_id=job_id,
            asset_id=request.asset_id,
            job_type="waveform",
            status="queued",
            message=f"Waveform generation job created ({request.width}x{request.height}, style: {request.style})"
        )
        
    except Exception as e:
        logger.error(
            "waveform_creation_failed",
            error=str(e),
            asset_id=request.asset_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create waveform job: {str(e)}"
        )


@router.post("/waveform/spectral")
async def generate_spectral_waveform(
    request: SpectralWaveformRequest,
    current_user: dict = Depends(get_current_user),
    proxy_processor = Depends(get_proxy_processor)
):
    """Generate a spectral waveform (spectrogram) visualization"""
    try:
        # Create job for spectral waveform generation
        job_params = {
            "width": request.width,
            "height": request.height,
            "color_mode": request.color_mode,
            "frequency_scale": request.frequency_scale,
            "window_size": request.window_size,
            "overlap": request.overlap
        }
        
        job_id = await proxy_processor.create_job(
            asset_id=request.asset_id,
            input_path=request.input_path,
            job_type="spectral_waveform",
            parameters=job_params,
            priority=request.priority,
            metadata=request.metadata
        )
        
        return ProxyJobResponse(
            job_id=job_id,
            asset_id=request.asset_id,
            job_type="spectral_waveform",
            status="queued",
            message=f"Spectral waveform generation job created ({request.width}x{request.height}, color: {request.color_mode})"
        )
        
    except Exception as e:
        logger.error(
            "spectral_waveform_creation_failed",
            error=str(e),
            asset_id=request.asset_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create spectral waveform job: {str(e)}"
        )


@router.post("/waveform/vectorscope")
async def generate_vectorscope(
    request: VectorscopeRequest,
    current_user: dict = Depends(get_current_user),
    proxy_processor = Depends(get_proxy_processor)
):
    """Generate a vectorscope visualization for stereo phase analysis"""
    try:
        # Create job for vectorscope generation
        job_params = {
            "width": request.width,
            "height": request.height,
            "mode": request.mode,
            "intensity": request.intensity,
            "zoom": request.zoom
        }
        
        job_id = await proxy_processor.create_job(
            asset_id=request.asset_id,
            input_path=request.input_path,
            job_type="vectorscope",
            parameters=job_params,
            priority=request.priority,
            metadata=request.metadata
        )
        
        return ProxyJobResponse(
            job_id=job_id,
            asset_id=request.asset_id,
            job_type="vectorscope",
            status="queued",
            message=f"Vectorscope generation job created ({request.width}x{request.height}, mode: {request.mode})"
        )
        
    except Exception as e:
        logger.error(
            "vectorscope_creation_failed",
            error=str(e),
            asset_id=request.asset_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create vectorscope job: {str(e)}"
        )


# Audio analysis endpoints
@router.post("/audio/detect-peaks")
async def detect_audio_peaks(
    request: AudioPeakDetectionRequest,
    current_user: dict = Depends(get_current_user),
    proxy_processor = Depends(get_proxy_processor)
):
    """Detect audio peaks and potential clipping in audio/video files"""
    try:
        # This is a synchronous analysis, not a job
        result = await proxy_processor.ffmpeg_service.detect_audio_peaks(
            input_path=request.input_path,
            threshold=request.threshold,
            min_duration=request.min_duration,
            channel=request.channel
        )
        
        return {
            "asset_id": request.asset_id,
            "analysis_type": "peak_detection",
            "threshold_db": request.threshold,
            "min_duration": request.min_duration,
            "channel": request.channel,
            "results": result
        }
        
    except Exception as e:
        logger.error(
            "audio_peak_detection_failed",
            error=str(e),
            asset_id=request.asset_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to detect audio peaks: {str(e)}"
        )


@router.post("/audio/extract-levels")
async def extract_audio_levels(
    request: AudioLevelExtractionRequest,
    current_user: dict = Depends(get_current_user),
    proxy_processor = Depends(get_proxy_processor)
):
    """Extract audio levels at regular intervals for level meter visualization"""
    try:
        # This is a synchronous analysis, not a job
        result = await proxy_processor.ffmpeg_service.extract_audio_levels(
            input_path=request.input_path,
            interval=request.interval
        )
        
        return {
            "asset_id": request.asset_id,
            "analysis_type": "level_extraction",
            "interval": request.interval,
            "results": result
        }
        
    except Exception as e:
        logger.error(
            "audio_level_extraction_failed",
            error=str(e),
            asset_id=request.asset_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to extract audio levels: {str(e)}"
        )


@router.post("/audio/convert")
async def convert_audio_format(
    request: AudioFormatConversionRequest,
    current_user: dict = Depends(get_current_user),
    proxy_processor = Depends(get_proxy_processor)
):
    """Convert audio to different format with optional normalization"""
    try:
        # Create job for audio conversion
        job_params = {
            "format": request.output_format,
            "codec": request.codec,
            "bitrate": request.bitrate,
            "sample_rate": request.sample_rate,
            "channels": request.channels,
            "normalize": request.normalize,
            "target_level": request.target_level
        }
        
        job_id = await proxy_processor.create_job(
            asset_id=request.asset_id,
            input_path=request.input_path,
            job_type="audio_proxy",
            parameters=job_params,
            priority=request.priority,
            metadata=request.metadata
        )
        
        return ProxyJobResponse(
            job_id=job_id,
            asset_id=request.asset_id,
            job_type="audio_proxy",
            status="queued",
            message=f"Audio format conversion job created (format: {request.output_format}, normalize: {request.normalize})"
        )
        
    except Exception as e:
        logger.error(
            "audio_format_conversion_creation_failed",
            error=str(e),
            asset_id=request.asset_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create audio conversion job: {str(e)}"
        )


# Image format conversion endpoints
@router.post("/images/convert")
async def convert_image_format(
    request: ImageFormatConversionRequest,
    current_user: dict = Depends(get_current_user),
    proxy_processor = Depends(get_proxy_processor)
):
    """Convert image to different format with optional resizing"""
    try:
        # This is a synchronous operation, not a job
        result = await proxy_processor.ffmpeg_service.convert_image_format(
            input_path=request.input_path,
            output_path=f"/tmp/{request.asset_id}_converted.{request.output_format}",
            output_format=request.output_format,
            width=request.width,
            height=request.height,
            quality=request.quality,
            preserve_aspect_ratio=request.preserve_aspect_ratio
        )
        
        # Store the converted image
        storage_key = proxy_processor.storage_service.generate_storage_key(
            asset_id=request.asset_id,
            proxy_type="image_conversion",
            quality=f"{result['width']}x{result['height']}",
            extension=request.output_format
        )
        
        storage_url = await proxy_processor.storage_service.store_file(
            file_path=result["output_path"],
            storage_key=storage_key,
            metadata={
                "asset_id": request.asset_id,
                "original_path": request.input_path,
                "format": request.output_format,
                "width": str(result['width']),
                "height": str(result['height']),
                "converted_at": datetime.utcnow().isoformat()
            }
        )
        
        # Clean up temp file
        if os.path.exists(result["output_path"]):
            os.remove(result["output_path"])
        
        return {
            "asset_id": request.asset_id,
            "output_format": request.output_format,
            "width": result['width'],
            "height": result['height'],
            "file_size": result['file_size'],
            "storage_key": storage_key,
            "storage_url": storage_url,
            "processing_time": result['processing_time']
        }
        
    except Exception as e:
        logger.error(
            "image_format_conversion_failed",
            error=str(e),
            asset_id=request.asset_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to convert image: {str(e)}"
        )


@router.post("/images/sequence-to-video")
async def convert_image_sequence(
    request: ImageSequenceConversionRequest,
    current_user: dict = Depends(get_current_user),
    proxy_processor = Depends(get_proxy_processor)
):
    """Convert image sequence to video or animated format"""
    try:
        # Create job for sequence conversion
        job_params = {
            "input_pattern": request.input_pattern,
            "output_format": request.output_format,
            "frame_rate": request.frame_rate,
            "quality": request.quality
        }
        
        job_id = await proxy_processor.create_job(
            asset_id=request.asset_id,
            input_path=request.input_pattern,  # Using pattern as input path
            job_type="image_sequence",
            parameters=job_params,
            priority=request.priority,
            metadata=request.metadata
        )
        
        return ProxyJobResponse(
            job_id=job_id,
            asset_id=request.asset_id,
            job_type="image_sequence",
            status="queued",
            message=f"Image sequence conversion job created (format: {request.output_format}, fps: {request.frame_rate})"
        )
        
    except Exception as e:
        logger.error(
            "image_sequence_conversion_creation_failed",
            error=str(e),
            asset_id=request.asset_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create image sequence conversion job: {str(e)}"
        )


# Adaptive Bitrate Streaming endpoints
@router.post("/video/adaptive-bitrate")
async def generate_adaptive_bitrate_stream(
    request: AdaptiveBitrateRequest,
    current_user: dict = Depends(get_current_user),
    proxy_processor = Depends(get_proxy_processor)
):
    """Generate adaptive bitrate streams (HLS/DASH) for video content"""
    try:
        # Convert quality variants to dict format for FFmpeg service
        qualities = None
        if request.qualities:
            qualities = [
                {
                    "name": quality.name,
                    "width": quality.width,
                    "height": quality.height,
                    "bitrate": quality.bitrate,
                    "audio_bitrate": quality.audio_bitrate
                }
                for quality in request.qualities
            ]
        
        # Create job for adaptive bitrate stream generation
        job_params = {
            "stream_formats": request.stream_formats,
            "qualities": qualities,
            "segment_duration": request.segment_duration,
            "playlist_type": request.playlist_type,
            "force_gpu": request.force_gpu
        }
        
        job_id = await proxy_processor.create_job(
            asset_id=request.asset_id,
            input_path=request.input_path,
            job_type="adaptive_bitrate",
            parameters=job_params,
            priority=request.priority,
            metadata=request.metadata
        )
        
        return ProxyJobResponse(
            job_id=job_id,
            asset_id=request.asset_id,
            job_type="adaptive_bitrate",
            status="queued",
            message=f"Adaptive bitrate stream generation job created (formats: {', '.join(request.stream_formats)})"
        )
        
    except Exception as e:
        logger.error(
            "adaptive_bitrate_creation_failed",
            error=str(e),
            asset_id=request.asset_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create adaptive bitrate job: {str(e)}"
        )


@router.get("/video/adaptive-bitrate/presets")
async def get_adaptive_bitrate_presets(
    current_user: dict = Depends(get_current_user)
):
    """Get available quality presets for adaptive bitrate encoding"""
    try:
        presets = {
            "mobile": [
                {"name": "240p", "width": 426, "height": 240, "bitrate": "400k", "audio_bitrate": "64k"},
                {"name": "360p", "width": 640, "height": 360, "bitrate": "800k", "audio_bitrate": "128k"},
                {"name": "480p", "width": 854, "height": 480, "bitrate": "1400k", "audio_bitrate": "128k"}
            ],
            "standard": [
                {"name": "360p", "width": 640, "height": 360, "bitrate": "800k", "audio_bitrate": "128k"},
                {"name": "480p", "width": 854, "height": 480, "bitrate": "1400k", "audio_bitrate": "128k"},
                {"name": "720p", "width": 1280, "height": 720, "bitrate": "2800k", "audio_bitrate": "192k"},
                {"name": "1080p", "width": 1920, "height": 1080, "bitrate": "5000k", "audio_bitrate": "192k"}
            ],
            "high_quality": [
                {"name": "720p", "width": 1280, "height": 720, "bitrate": "3500k", "audio_bitrate": "192k"},
                {"name": "1080p", "width": 1920, "height": 1080, "bitrate": "6000k", "audio_bitrate": "256k"},
                {"name": "1440p", "width": 2560, "height": 1440, "bitrate": "12000k", "audio_bitrate": "256k"},
                {"name": "2160p", "width": 3840, "height": 2160, "bitrate": "25000k", "audio_bitrate": "320k"}
            ]
        }
        
        return {
            "presets": presets,
            "supported_formats": ["hls", "dash"],
            "default_segment_duration": 6,
            "playlist_types": ["vod", "live"]
        }
        
    except Exception as e:
        logger.error(
            "get_adaptive_bitrate_presets_failed",
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get adaptive bitrate presets: {str(e)}"
        )


# Scene Detection endpoints
class SceneDetectionRequest(BaseModel):
    """Request model for scene detection"""
    asset_id: str = Field(..., description="Asset ID")
    input_path: str = Field(..., description="Path to input video file")
    threshold: float = Field(0.3, ge=0.0, le=1.0, description="Scene change detection threshold")
    min_scene_duration: float = Field(1.0, ge=0.1, description="Minimum scene duration in seconds")
    output_format: str = Field("json", pattern="^(json|csv|timestamps)$", description="Output format")
    save_thumbnails: bool = Field(False, description="Whether to save thumbnails at scene changes")
    thumbnail_size: str = Field("320x180", description="Thumbnail size (WxH)")
    priority: str = Field("normal", pattern="^(low|normal|high)$")
    
    class Config:
        schema_extra = {
            "example": {
                "asset_id": "asset123",
                "input_path": "/storage/videos/sample.mp4",
                "threshold": 0.3,
                "min_scene_duration": 1.0,
                "output_format": "json",
                "save_thumbnails": True,
                "thumbnail_size": "320x180",
                "priority": "normal"
            }
        }


@router.post("/video/detect-scenes")
async def detect_scene_changes(
    request: SceneDetectionRequest,
    current_user: dict = Depends(get_current_user),
    proxy_processor = Depends(get_proxy_processor)
):
    """Detect scene changes in a video file"""
    try:
        # Create job for scene detection
        job_params = {
            "threshold": request.threshold,
            "min_scene_duration": request.min_scene_duration,
            "output_format": request.output_format,
            "save_thumbnails": request.save_thumbnails,
            "thumbnail_size": request.thumbnail_size
        }
        
        # Submit job via queue service
        queue_service = await get_queue_service()
        job_id = await queue_service.submit_job(
            asset_id=request.asset_id,
            input_path=request.input_path,
            job_type="scene_detection",
            parameters=job_params,
            priority=request.priority,
            metadata={
                "submitted_by": current_user["user_id"],
                "submitted_at": datetime.utcnow().isoformat()
            }
        )
        
        logger.info(
            "scene_detection_job_submitted",
            job_id=job_id,
            asset_id=request.asset_id,
            user_id=current_user["user_id"],
            threshold=request.threshold
        )
        
        return {
            "job_id": job_id,
            "asset_id": request.asset_id,
            "job_type": "scene_detection",
            "status": "queued",
            "message": "Scene detection job queued successfully"
        }
        
    except Exception as e:
        logger.error(
            "scene_detection_submission_failed",
            error=str(e),
            asset_id=request.asset_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit scene detection job: {str(e)}"
        )


@router.get("/video/scene-detection-defaults")
async def get_scene_detection_defaults(
    current_user: dict = Depends(get_current_user)
):
    """Get default parameters for scene detection"""
    try:
        return {
            "thresholds": {
                "low": 0.2,       # More sensitive, detects subtle changes
                "medium": 0.3,    # Default, balanced detection
                "high": 0.4       # Less sensitive, major changes only
            },
            "min_scene_durations": {
                "quick_cuts": 0.5,    # For action/music videos
                "normal": 1.0,        # Default
                "slow_pace": 2.0      # For documentaries/interviews
            },
            "thumbnail_sizes": {
                "small": "160x90",
                "medium": "320x180",
                "large": "640x360",
                "hd": "1280x720"
            },
            "output_formats": ["json", "csv", "timestamps"],
            "recommended_settings": {
                "action": {"threshold": 0.25, "min_scene_duration": 0.5},
                "drama": {"threshold": 0.35, "min_scene_duration": 2.0},
                "documentary": {"threshold": 0.4, "min_scene_duration": 3.0},
                "music_video": {"threshold": 0.2, "min_scene_duration": 0.3}
            }
        }
        
    except Exception as e:
        logger.error(
            "get_scene_detection_defaults_failed",
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get scene detection defaults: {str(e)}"
        )


# Smart Cropping endpoints
class SmartCropRequest(BaseModel):
    """Request model for smart cropping"""
    asset_id: str = Field(..., description="Asset ID")
    input_path: str = Field(..., description="Path to input image file")
    output_width: int = Field(..., gt=0, le=8192, description="Output width in pixels")
    output_height: int = Field(..., gt=0, le=8192, description="Output height in pixels")
    crop_mode: str = Field("smart", pattern="^(center|smart|face|saliency|entropy|edge)$", description="Cropping algorithm")
    quality: int = Field(95, ge=1, le=100, description="Output JPEG quality")
    face_padding: float = Field(1.5, ge=1.0, le=3.0, description="Padding factor for face detection")
    focus_point_x: Optional[float] = Field(None, ge=0.0, le=1.0, description="Custom focus point X (0-1)")
    focus_point_y: Optional[float] = Field(None, ge=0.0, le=1.0, description="Custom focus point Y (0-1)")
    priority: str = Field("normal", pattern="^(low|normal|high)$")
    
    class Config:
        schema_extra = {
            "example": {
                "asset_id": "asset123",
                "input_path": "/storage/images/photo.jpg",
                "output_width": 1280,
                "output_height": 720,
                "crop_mode": "smart",
                "quality": 95,
                "face_padding": 1.5,
                "priority": "normal"
            }
        }


class BatchSmartCropRequest(BaseModel):
    """Request model for batch smart cropping"""
    images: List[Dict[str, Any]] = Field(..., description="List of images to crop")
    default_output_width: int = Field(..., gt=0, le=8192, description="Default output width")
    default_output_height: int = Field(..., gt=0, le=8192, description="Default output height")
    default_crop_mode: str = Field("smart", pattern="^(center|smart|face|saliency|entropy|edge)$")
    parallel_workers: int = Field(4, ge=1, le=16, description="Number of parallel workers")
    priority: str = Field("normal", pattern="^(low|normal|high)$")
    
    class Config:
        schema_extra = {
            "example": {
                "images": [
                    {
                        "asset_id": "asset123",
                        "input_path": "/storage/images/photo1.jpg",
                        "output_size": [800, 600],
                        "crop_mode": "face"
                    },
                    {
                        "asset_id": "asset124",
                        "input_path": "/storage/images/photo2.jpg",
                        "focus_point": [0.3, 0.4]
                    }
                ],
                "default_output_width": 1280,
                "default_output_height": 720,
                "default_crop_mode": "smart",
                "parallel_workers": 4,
                "priority": "normal"
            }
        }


@router.post("/images/smart-crop")
async def smart_crop_image(
    request: SmartCropRequest,
    current_user: dict = Depends(get_current_user),
    proxy_processor = Depends(get_proxy_processor)
):
    """Apply smart cropping to an image"""
    try:
        # Create job for smart cropping
        job_params = {
            "output_size": (request.output_width, request.output_height),
            "crop_mode": request.crop_mode,
            "quality": request.quality,
            "face_padding": request.face_padding,
            "focus_point": (request.focus_point_x, request.focus_point_y) if request.focus_point_x and request.focus_point_y else None
        }
        
        # Submit job via queue service
        queue_service = await get_queue_service()
        job_id = await queue_service.submit_job(
            asset_id=request.asset_id,
            input_path=request.input_path,
            job_type="smart_crop",
            parameters=job_params,
            priority=request.priority,
            metadata={
                "submitted_by": current_user["user_id"],
                "submitted_at": datetime.utcnow().isoformat()
            }
        )
        
        logger.info(
            "smart_crop_job_submitted",
            job_id=job_id,
            asset_id=request.asset_id,
            user_id=current_user["user_id"],
            crop_mode=request.crop_mode,
            output_size=(request.output_width, request.output_height)
        )
        
        return {
            "job_id": job_id,
            "asset_id": request.asset_id,
            "job_type": "smart_crop",
            "status": "queued",
            "message": "Smart crop job queued successfully"
        }
        
    except Exception as e:
        logger.error(
            "smart_crop_submission_failed",
            error=str(e),
            asset_id=request.asset_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit smart crop job: {str(e)}"
        )


@router.post("/images/batch-smart-crop")
async def batch_smart_crop(
    request: BatchSmartCropRequest,
    current_user: dict = Depends(get_current_user),
    proxy_processor = Depends(get_proxy_processor)
):
    """Apply smart cropping to multiple images"""
    try:
        # Create job for batch smart cropping
        job_params = {
            "images": request.images,
            "default_output_size": (request.default_output_width, request.default_output_height),
            "default_crop_mode": request.default_crop_mode,
            "parallel_workers": request.parallel_workers
        }
        
        # Submit job via queue service
        queue_service = await get_queue_service()
        job_id = await queue_service.submit_job(
            asset_id="batch_" + datetime.utcnow().strftime("%Y%m%d_%H%M%S"),
            input_path="batch",
            job_type="batch_smart_crop",
            parameters=job_params,
            priority=request.priority,
            metadata={
                "submitted_by": current_user["user_id"],
                "submitted_at": datetime.utcnow().isoformat(),
                "batch_size": len(request.images)
            }
        )
        
        logger.info(
            "batch_smart_crop_job_submitted",
            job_id=job_id,
            user_id=current_user["user_id"],
            batch_size=len(request.images),
            default_crop_mode=request.default_crop_mode
        )
        
        return {
            "job_id": job_id,
            "job_type": "batch_smart_crop",
            "batch_size": len(request.images),
            "status": "queued",
            "message": f"Batch smart crop job queued successfully for {len(request.images)} images"
        }
        
    except Exception as e:
        logger.error(
            "batch_smart_crop_submission_failed",
            error=str(e),
            batch_size=len(request.images)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit batch smart crop job: {str(e)}"
        )


@router.get("/images/crop-modes")
async def get_crop_modes(
    current_user: dict = Depends(get_current_user)
):
    """Get available crop modes and their descriptions"""
    try:
        return {
            "crop_modes": {
                "center": {
                    "name": "Center Crop",
                    "description": "Simple center-based cropping",
                    "best_for": ["Symmetric images", "Landscapes", "Architecture"],
                    "performance": "Fast"
                },
                "smart": {
                    "name": "Smart Crop",
                    "description": "Combines multiple detection methods for best results",
                    "best_for": ["General purpose", "Mixed content", "Unknown subjects"],
                    "performance": "Medium"
                },
                "face": {
                    "name": "Face Detection",
                    "description": "Detects and centers on human faces",
                    "best_for": ["Portraits", "Group photos", "Profile pictures"],
                    "performance": "Fast"
                },
                "saliency": {
                    "name": "Saliency Detection",
                    "description": "Finds visually important regions",
                    "best_for": ["Product photos", "Wildlife", "Objects"],
                    "performance": "Medium"
                },
                "entropy": {
                    "name": "Entropy-based",
                    "description": "Crops areas with highest information content",
                    "best_for": ["Detailed images", "Textures", "Patterns"],
                    "performance": "Fast"
                },
                "edge": {
                    "name": "Edge Detection",
                    "description": "Focuses on areas with strong edges",
                    "best_for": ["Graphics", "Text", "Line art"],
                    "performance": "Medium"
                }
            },
            "recommended_sizes": {
                "thumbnail": {"width": 320, "height": 180},
                "social_media_square": {"width": 1080, "height": 1080},
                "social_media_landscape": {"width": 1200, "height": 630},
                "web_banner": {"width": 1920, "height": 600},
                "mobile_hero": {"width": 750, "height": 1334}
            }
        }
        
    except Exception as e:
        logger.error(
            "get_crop_modes_failed",
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get crop modes: {str(e)}"
        )


# Watermarking endpoints
class ImageWatermarkRequest(BaseModel):
    """Request model for image watermarking"""
    asset_id: str = Field(..., description="Asset ID")
    input_path: str = Field(..., description="Path to input image file")
    watermark_path: str = Field(..., description="Path to watermark image/logo")
    position: str = Field("bottom-right", pattern="^(top-left|top-right|bottom-left|bottom-right|center)$", description="Watermark position")
    opacity: float = Field(0.8, ge=0.0, le=1.0, description="Watermark opacity (0.0-1.0)")
    scale: float = Field(0.2, ge=0.05, le=0.5, description="Scale factor for watermark relative to main image")
    margin: int = Field(20, ge=0, le=100, description="Margin from edges in pixels")
    output_format: str = Field("same", pattern="^(same|jpg|png)$", description="Output format")
    quality: int = Field(95, ge=1, le=100, description="Output quality for JPEG")
    priority: str = Field("normal", pattern="^(low|normal|high)$")
    
    class Config:
        schema_extra = {
            "example": {
                "asset_id": "asset123",
                "input_path": "/storage/images/photo.jpg",
                "watermark_path": "/storage/watermarks/logo.png",
                "position": "bottom-right",
                "opacity": 0.8,
                "scale": 0.2,
                "margin": 20,
                "output_format": "same",
                "quality": 95,
                "priority": "normal"
            }
        }


class TextWatermarkRequest(BaseModel):
    """Request model for text watermarking"""
    asset_id: str = Field(..., description="Asset ID")
    input_path: str = Field(..., description="Path to input image file")
    text: str = Field(..., description="Text to use as watermark")
    font_path: Optional[str] = Field(None, description="Path to TrueType font file")
    font_size: int = Field(36, ge=8, le=200, description="Font size in pixels")
    font_color: List[int] = Field([255, 255, 255, 180], min_items=4, max_items=4, description="Font color as RGBA")
    position: str = Field("bottom-right", pattern="^(top-left|top-right|bottom-left|bottom-right|center)$", description="Watermark position")
    margin: int = Field(20, ge=0, le=100, description="Margin from edges in pixels")
    background_color: Optional[List[int]] = Field(None, min_items=4, max_items=4, description="Optional background color as RGBA")
    background_padding: int = Field(10, ge=0, le=50, description="Padding around text background")
    output_format: str = Field("same", pattern="^(same|jpg|png)$", description="Output format")
    quality: int = Field(95, ge=1, le=100, description="Output quality for JPEG")
    priority: str = Field("normal", pattern="^(low|normal|high)$")
    
    class Config:
        schema_extra = {
            "example": {
                "asset_id": "asset123",
                "input_path": "/storage/images/photo.jpg",
                "text": "© 2024 My Company",
                "font_size": 36,
                "font_color": [255, 255, 255, 180],
                "position": "bottom-right",
                "margin": 20,
                "background_color": [0, 0, 0, 100],
                "background_padding": 10,
                "output_format": "same",
                "quality": 95,
                "priority": "normal"
            }
        }


class VideoWatermarkRequest(BaseModel):
    """Request model for video watermarking"""
    asset_id: str = Field(..., description="Asset ID")
    input_path: str = Field(..., description="Path to input video file")
    watermark_path: str = Field(..., description="Path to watermark image/logo")
    position: str = Field("bottom-right", pattern="^(top-left|top-right|bottom-left|bottom-right|center)$", description="Watermark position")
    scale: float = Field(0.2, ge=0.05, le=0.5, description="Scale factor for watermark")
    opacity: float = Field(0.8, ge=0.0, le=1.0, description="Watermark opacity")
    margin: int = Field(20, ge=0, le=100, description="Margin from edges in pixels")
    video_codec: Optional[str] = Field(None, description="Video codec to use (auto-selected if None)")
    audio_codec: str = Field("copy", description="Audio codec (copy = no re-encoding)")
    quality_preset: str = Field("medium", pattern="^(low|medium|high|edit)$", description="Video quality preset")
    priority: str = Field("normal", pattern="^(low|normal|high)$")
    
    class Config:
        schema_extra = {
            "example": {
                "asset_id": "asset123",
                "input_path": "/storage/videos/video.mp4",
                "watermark_path": "/storage/watermarks/logo.png",
                "position": "bottom-right",
                "scale": 0.2,
                "opacity": 0.8,
                "margin": 20,
                "quality_preset": "medium",
                "priority": "normal"
            }
        }


class BatchWatermarkRequest(BaseModel):
    """Request model for batch watermarking"""
    images: List[Dict[str, Any]] = Field(..., description="List of images to watermark")
    default_watermark_path: str = Field(..., description="Default watermark image path")
    default_position: str = Field("bottom-right", pattern="^(top-left|top-right|bottom-left|bottom-right|center)$")
    default_opacity: float = Field(0.8, ge=0.0, le=1.0)
    default_scale: float = Field(0.2, ge=0.05, le=0.5)
    parallel_workers: int = Field(4, ge=1, le=16, description="Number of parallel workers")
    priority: str = Field("normal", pattern="^(low|normal|high)$")
    
    class Config:
        schema_extra = {
            "example": {
                "images": [
                    {
                        "asset_id": "asset123",
                        "input_path": "/storage/images/photo1.jpg",
                        "position": "top-right"
                    },
                    {
                        "asset_id": "asset124",
                        "input_path": "/storage/images/photo2.jpg",
                        "opacity": 0.5
                    }
                ],
                "default_watermark_path": "/storage/watermarks/logo.png",
                "default_position": "bottom-right",
                "default_opacity": 0.8,
                "default_scale": 0.2,
                "parallel_workers": 4,
                "priority": "normal"
            }
        }


@router.post("/images/watermark")
async def add_image_watermark(
    request: ImageWatermarkRequest,
    current_user: dict = Depends(get_current_user),
    proxy_processor = Depends(get_proxy_processor)
):
    """Add watermark to an image"""
    try:
        # Create job for image watermarking
        job_params = {
            "watermark_path": request.watermark_path,
            "position": request.position,
            "opacity": request.opacity,
            "scale": request.scale,
            "margin": request.margin,
            "output_format": request.output_format,
            "quality": request.quality
        }
        
        # Submit job via queue service
        queue_service = await get_queue_service()
        job_id = await queue_service.submit_job(
            asset_id=request.asset_id,
            input_path=request.input_path,
            job_type="image_watermark",
            parameters=job_params,
            priority=request.priority,
            metadata={
                "submitted_by": current_user["user_id"],
                "submitted_at": datetime.utcnow().isoformat()
            }
        )
        
        logger.info(
            "image_watermark_job_submitted",
            job_id=job_id,
            asset_id=request.asset_id,
            user_id=current_user["user_id"],
            position=request.position
        )
        
        return {
            "job_id": job_id,
            "asset_id": request.asset_id,
            "job_type": "image_watermark",
            "status": "queued",
            "message": "Image watermark job queued successfully"
        }
        
    except Exception as e:
        logger.error(
            "image_watermark_submission_failed",
            error=str(e),
            asset_id=request.asset_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit image watermark job: {str(e)}"
        )


@router.post("/images/text-watermark")
async def add_text_watermark(
    request: TextWatermarkRequest,
    current_user: dict = Depends(get_current_user),
    proxy_processor = Depends(get_proxy_processor)
):
    """Add text watermark to an image"""
    try:
        # Convert color lists to tuples
        font_color = tuple(request.font_color)
        background_color = tuple(request.background_color) if request.background_color else None
        
        # Create job for text watermarking
        job_params = {
            "text": request.text,
            "font_path": request.font_path,
            "font_size": request.font_size,
            "font_color": font_color,
            "position": request.position,
            "margin": request.margin,
            "background_color": background_color,
            "background_padding": request.background_padding,
            "output_format": request.output_format,
            "quality": request.quality
        }
        
        # Submit job via queue service
        queue_service = await get_queue_service()
        job_id = await queue_service.submit_job(
            asset_id=request.asset_id,
            input_path=request.input_path,
            job_type="text_watermark",
            parameters=job_params,
            priority=request.priority,
            metadata={
                "submitted_by": current_user["user_id"],
                "submitted_at": datetime.utcnow().isoformat()
            }
        )
        
        logger.info(
            "text_watermark_job_submitted",
            job_id=job_id,
            asset_id=request.asset_id,
            user_id=current_user["user_id"],
            text=request.text
        )
        
        return {
            "job_id": job_id,
            "asset_id": request.asset_id,
            "job_type": "text_watermark",
            "status": "queued",
            "message": "Text watermark job queued successfully"
        }
        
    except Exception as e:
        logger.error(
            "text_watermark_submission_failed",
            error=str(e),
            asset_id=request.asset_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit text watermark job: {str(e)}"
        )


@router.post("/video/watermark")
async def add_video_watermark(
    request: VideoWatermarkRequest,
    current_user: dict = Depends(get_current_user),
    proxy_processor = Depends(get_proxy_processor)
):
    """Add watermark to a video"""
    try:
        # Create job for video watermarking
        job_params = {
            "watermark_path": request.watermark_path,
            "position": request.position,
            "scale": request.scale,
            "opacity": request.opacity,
            "margin": request.margin,
            "video_codec": request.video_codec,
            "audio_codec": request.audio_codec,
            "quality_preset": request.quality_preset
        }
        
        # Submit job via queue service
        queue_service = await get_queue_service()
        job_id = await queue_service.submit_job(
            asset_id=request.asset_id,
            input_path=request.input_path,
            job_type="video_watermark",
            parameters=job_params,
            priority=request.priority,
            metadata={
                "submitted_by": current_user["user_id"],
                "submitted_at": datetime.utcnow().isoformat()
            }
        )
        
        logger.info(
            "video_watermark_job_submitted",
            job_id=job_id,
            asset_id=request.asset_id,
            user_id=current_user["user_id"],
            position=request.position
        )
        
        return {
            "job_id": job_id,
            "asset_id": request.asset_id,
            "job_type": "video_watermark",
            "status": "queued",
            "message": "Video watermark job queued successfully"
        }
        
    except Exception as e:
        logger.error(
            "video_watermark_submission_failed",
            error=str(e),
            asset_id=request.asset_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit video watermark job: {str(e)}"
        )


@router.post("/images/batch-watermark")
async def batch_watermark_images(
    request: BatchWatermarkRequest,
    current_user: dict = Depends(get_current_user),
    proxy_processor = Depends(get_proxy_processor)
):
    """Add watermark to multiple images"""
    try:
        # Create job for batch watermarking
        job_params = {
            "images": request.images,
            "default_watermark_path": request.default_watermark_path,
            "default_position": request.default_position,
            "default_opacity": request.default_opacity,
            "default_scale": request.default_scale,
            "parallel_workers": request.parallel_workers
        }
        
        # Submit job via queue service
        queue_service = await get_queue_service()
        job_id = await queue_service.submit_job(
            asset_id="batch_watermark_" + datetime.utcnow().strftime("%Y%m%d_%H%M%S"),
            input_path="batch",
            job_type="batch_watermark",
            parameters=job_params,
            priority=request.priority,
            metadata={
                "submitted_by": current_user["user_id"],
                "submitted_at": datetime.utcnow().isoformat(),
                "batch_size": len(request.images)
            }
        )
        
        logger.info(
            "batch_watermark_job_submitted",
            job_id=job_id,
            user_id=current_user["user_id"],
            batch_size=len(request.images)
        )
        
        return {
            "job_id": job_id,
            "job_type": "batch_watermark",
            "batch_size": len(request.images),
            "status": "queued",
            "message": f"Batch watermark job queued successfully for {len(request.images)} images"
        }
        
    except Exception as e:
        logger.error(
            "batch_watermark_submission_failed",
            error=str(e),
            batch_size=len(request.images)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit batch watermark job: {str(e)}"
        )


@router.get("/watermark/positions")
async def get_watermark_positions(
    current_user: dict = Depends(get_current_user)
):
    """Get available watermark positions and best practices"""
    try:
        return {
            "positions": {
                "top-left": {
                    "description": "Top left corner",
                    "best_for": ["Signatures", "Artist marks"],
                    "visibility": "High"
                },
                "top-right": {
                    "description": "Top right corner",
                    "best_for": ["Company logos", "Channel branding"],
                    "visibility": "High"
                },
                "bottom-left": {
                    "description": "Bottom left corner",
                    "best_for": ["Copyright notices", "Date stamps"],
                    "visibility": "Medium"
                },
                "bottom-right": {
                    "description": "Bottom right corner (most common)",
                    "best_for": ["Logos", "Website URLs", "Social handles"],
                    "visibility": "Medium"
                },
                "center": {
                    "description": "Center of image/video",
                    "best_for": ["Draft/preview watermarks", "Maximum protection"],
                    "visibility": "Very High"
                }
            },
            "recommended_settings": {
                "subtle": {
                    "opacity": 0.3,
                    "scale": 0.1,
                    "margin": 20,
                    "use_case": "Professional photos, minimal intrusion"
                },
                "standard": {
                    "opacity": 0.6,
                    "scale": 0.15,
                    "margin": 20,
                    "use_case": "General purpose, balanced visibility"
                },
                "prominent": {
                    "opacity": 0.8,
                    "scale": 0.2,
                    "margin": 30,
                    "use_case": "Strong branding, copyright protection"
                },
                "preview": {
                    "opacity": 0.5,
                    "scale": 0.3,
                    "margin": 0,
                    "position": "center",
                    "use_case": "Preview/draft versions"
                }
            },
            "text_watermark_fonts": {
                "default": "System default font",
                "custom": "Upload .ttf or .otf font file"
            }
        }
        
    except Exception as e:
        logger.error(
            "get_watermark_positions_failed",
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get watermark positions: {str(e)}"
        )


# 8K and Ultra HD Processing Endpoints

class UltraHDJobRequest(BaseModel):
    """Request model for Ultra HD processing job"""
    asset_id: str = Field(..., description="Asset ID to process")
    input_path: str = Field(..., description="Path to input media file")
    codec: str = Field("h265", description="Video codec (h264, h265, av1, vp9)")
    quality: str = Field("medium", description="Quality setting (low, medium, high, max)")
    resolution: Optional[str] = Field(None, description="Target resolution (e.g., '7680x4320')")
    enable_hdr: bool = Field(False, description="Enable HDR processing")
    priority: JobPriority = Field(JobPriority.NORMAL, description="Job priority")
    advanced_options: Optional[Dict[str, Any]] = Field(None, description="Advanced processing options")


@router.post("/jobs/8k-proxy", response_model=ProxyJobResponse, status_code=status.HTTP_201_CREATED)
async def create_8k_proxy_job(
    request: UltraHDJobRequest,
    queue_service=Depends(get_queue_service),
    current_user=Depends(get_current_user)
):
    """Create an 8K video proxy generation job"""
    try:
        # Validate input file exists
        if not os.path.exists(request.input_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Input file not found: {request.input_path}"
            )
        
        # Create job parameters
        parameters = {
            "codec": request.codec,
            "quality": request.quality,
            "enable_hdr": request.enable_hdr,
            "format": "mp4"
        }
        
        if request.resolution:
            parameters["resolution"] = request.resolution
        
        if request.advanced_options:
            parameters["advanced_options"] = request.advanced_options
        
        # Submit job to queue
        job_id = await queue_service.submit_job(
            job_type="8k_proxy",
            asset_id=request.asset_id,
            input_path=request.input_path,
            parameters=parameters,
            priority=request.priority,
            user_id=str(current_user.id)
        )
        
        logger.info(
            "8k_proxy_job_created",
            job_id=job_id,
            asset_id=request.asset_id,
            codec=request.codec,
            quality=request.quality,
            user_id=current_user.id
        )
        
        return ProxyJobResponse(
            job_id=job_id,
            asset_id=request.asset_id,
            job_type="8k_proxy",
            status="queued",
            message="8K proxy generation job queued successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "create_8k_proxy_job_failed",
            error=str(e),
            asset_id=request.asset_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create 8K proxy job: {str(e)}"
        )


@router.post("/jobs/8k-proxy-batch", response_model=ProxyJobResponse, status_code=status.HTTP_201_CREATED)
async def create_8k_proxy_batch_job(
    request: UltraHDJobRequest,
    queue_service=Depends(get_queue_service),
    current_user=Depends(get_current_user)
):
    """Create a batch 8K proxy generation job (multiple resolutions)"""
    try:
        # Validate input file exists
        if not os.path.exists(request.input_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Input file not found: {request.input_path}"
            )
        
        # Create job parameters
        parameters = {
            "codec": request.codec,
            "enable_hdr": request.enable_hdr,
            "format": "mp4"
        }
        
        if request.advanced_options:
            parameters["advanced_options"] = request.advanced_options
        
        # Submit job to queue
        job_id = await queue_service.submit_job(
            job_type="8k_proxy_batch",
            asset_id=request.asset_id,
            input_path=request.input_path,
            parameters=parameters,
            priority=request.priority,
            user_id=str(current_user.id)
        )
        
        logger.info(
            "8k_proxy_batch_job_created",
            job_id=job_id,
            asset_id=request.asset_id,
            codec=request.codec,
            user_id=current_user.id
        )
        
        return ProxyJobResponse(
            job_id=job_id,
            asset_id=request.asset_id,
            job_type="8k_proxy_batch",
            status="queued",
            message="8K proxy batch generation job queued successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "create_8k_proxy_batch_job_failed",
            error=str(e),
            asset_id=request.asset_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create 8K proxy batch job: {str(e)}"
        )


@router.post("/jobs/ultra-hd-analysis", response_model=ProxyJobResponse, status_code=status.HTTP_201_CREATED)
async def create_ultra_hd_analysis_job(
    asset_id: str = Field(..., description="Asset ID to analyze"),
    input_path: str = Field(..., description="Path to input media file"),
    priority: JobPriority = Field(JobPriority.NORMAL, description="Job priority"),
    queue_service=Depends(get_queue_service),
    current_user=Depends(get_current_user)
):
    """Create an Ultra HD video analysis job"""
    try:
        # Validate input file exists
        if not os.path.exists(input_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Input file not found: {input_path}"
            )
        
        # Submit job to queue
        job_id = await queue_service.submit_job(
            job_type="ultra_hd_analysis",
            asset_id=asset_id,
            input_path=input_path,
            parameters={},
            priority=priority,
            user_id=str(current_user.id)
        )
        
        logger.info(
            "ultra_hd_analysis_job_created",
            job_id=job_id,
            asset_id=asset_id,
            user_id=current_user.id
        )
        
        return ProxyJobResponse(
            job_id=job_id,
            asset_id=asset_id,
            job_type="ultra_hd_analysis",
            status="queued",
            message="Ultra HD analysis job queued successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "create_ultra_hd_analysis_job_failed",
            error=str(e),
            asset_id=asset_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create Ultra HD analysis job: {str(e)}"
        )


class HDRProcessingRequest(BaseModel):
    """Request model for HDR processing job"""
    asset_id: str = Field(..., description="Asset ID to process")
    input_path: str = Field(..., description="Path to input media file")
    tone_mapping: str = Field("none", description="Tone mapping method (none, hable, reinhard, mobius)")
    target_nits: int = Field(100, description="Target luminance in nits")
    preserve_hdr: bool = Field(True, description="Preserve HDR metadata")
    output_format: str = Field("mp4", description="Output format")
    priority: JobPriority = Field(JobPriority.NORMAL, description="Job priority")


@router.post("/jobs/hdr-processing", response_model=ProxyJobResponse, status_code=status.HTTP_201_CREATED)
async def create_hdr_processing_job(
    request: HDRProcessingRequest,
    queue_service=Depends(get_queue_service),
    current_user=Depends(get_current_user)
):
    """Create an HDR video processing job"""
    try:
        # Validate input file exists
        if not os.path.exists(request.input_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Input file not found: {request.input_path}"
            )
        
        # Validate tone mapping method
        valid_tone_mapping = ["none", "hable", "reinhard", "mobius"]
        if request.tone_mapping not in valid_tone_mapping:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid tone mapping method. Must be one of: {valid_tone_mapping}"
            )
        
        # Create job parameters
        parameters = {
            "tone_mapping": request.tone_mapping,
            "target_nits": request.target_nits,
            "preserve_hdr": request.preserve_hdr,
            "format": request.output_format
        }
        
        # Submit job to queue
        job_id = await queue_service.submit_job(
            job_type="hdr_processing",
            asset_id=request.asset_id,
            input_path=request.input_path,
            parameters=parameters,
            priority=request.priority,
            user_id=str(current_user.id)
        )
        
        logger.info(
            "hdr_processing_job_created",
            job_id=job_id,
            asset_id=request.asset_id,
            tone_mapping=request.tone_mapping,
            user_id=current_user.id
        )
        
        return ProxyJobResponse(
            job_id=job_id,
            asset_id=request.asset_id,
            job_type="hdr_processing",
            status="queued",
            message="HDR processing job queued successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "create_hdr_processing_job_failed",
            error=str(e),
            asset_id=request.asset_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create HDR processing job: {str(e)}"
        )


# HDR Analysis endpoint
class HDRAnalysisRequest(BaseModel):
    """Request model for HDR analysis job"""
    asset_id: str = Field(..., description="Asset ID to analyze")
    input_path: str = Field(..., description="Path to input media file")
    priority: JobPriority = Field(JobPriority.NORMAL, description="Job priority")


@router.post("/jobs/hdr-analysis", response_model=ProxyJobResponse, status_code=status.HTTP_201_CREATED)
async def create_hdr_analysis_job(
    request: HDRAnalysisRequest,
    queue_service=Depends(get_queue_service),
    current_user=Depends(get_current_user)
):
    """Create an HDR content analysis job"""
    try:
        # Validate input file exists
        if not os.path.exists(request.input_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Input file not found: {request.input_path}"
            )
        
        # Submit job to queue
        job_id = await queue_service.submit_job(
            job_type="hdr_analysis",
            asset_id=request.asset_id,
            input_path=request.input_path,
            parameters={},
            priority=request.priority,
            user_id=str(current_user.id)
        )
        
        logger.info(
            "hdr_analysis_job_created",
            job_id=job_id,
            asset_id=request.asset_id,
            user_id=current_user.id
        )
        
        return ProxyJobResponse(
            job_id=job_id,
            asset_id=request.asset_id,
            job_type="hdr_analysis",
            status="queued",
            message="HDR analysis job queued successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "create_hdr_analysis_job_failed",
            error=str(e),
            asset_id=request.asset_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create HDR analysis job: {str(e)}"
        )


# HDR to SDR conversion endpoint
class HDRToSDRRequest(BaseModel):
    """Request model for HDR to SDR conversion job"""
    asset_id: str = Field(..., description="Asset ID to convert")
    input_path: str = Field(..., description="Path to input HDR media file")
    tone_mapping: str = Field("hable", description="Tone mapping algorithm (hable, reinhard, mobius, clip)")
    target_nits: int = Field(100, ge=50, le=400, description="Target luminance in nits")
    preserve_colors: bool = Field(True, description="Preserve color characteristics")
    output_format: str = Field("mp4", description="Output format")
    priority: JobPriority = Field(JobPriority.NORMAL, description="Job priority")


@router.post("/jobs/hdr-to-sdr", response_model=ProxyJobResponse, status_code=status.HTTP_201_CREATED)
async def create_hdr_to_sdr_job(
    request: HDRToSDRRequest,
    queue_service=Depends(get_queue_service),
    current_user=Depends(get_current_user)
):
    """Create an HDR to SDR conversion job"""
    try:
        # Validate input file exists
        if not os.path.exists(request.input_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Input file not found: {request.input_path}"
            )
        
        # Validate tone mapping method
        valid_tone_mapping = ["hable", "reinhard", "mobius", "clip", "linear", "gamma"]
        if request.tone_mapping not in valid_tone_mapping:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid tone mapping method. Must be one of: {valid_tone_mapping}"
            )
        
        # Create job parameters
        parameters = {
            "tone_mapping": request.tone_mapping,
            "target_nits": request.target_nits,
            "preserve_colors": request.preserve_colors,
            "format": request.output_format
        }
        
        # Submit job to queue
        job_id = await queue_service.submit_job(
            job_type="hdr_to_sdr",
            asset_id=request.asset_id,
            input_path=request.input_path,
            parameters=parameters,
            priority=request.priority,
            user_id=str(current_user.id)
        )
        
        logger.info(
            "hdr_to_sdr_job_created",
            job_id=job_id,
            asset_id=request.asset_id,
            tone_mapping=request.tone_mapping,
            user_id=current_user.id
        )
        
        return ProxyJobResponse(
            job_id=job_id,
            asset_id=request.asset_id,
            job_type="hdr_to_sdr",
            status="queued",
            message="HDR to SDR conversion job queued successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "create_hdr_to_sdr_job_failed",
            error=str(e),
            asset_id=request.asset_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create HDR to SDR job: {str(e)}"
        )


# SDR to HDR conversion endpoint
class SDRToHDRRequest(BaseModel):
    """Request model for SDR to HDR upconversion job"""
    asset_id: str = Field(..., description="Asset ID to convert")
    input_path: str = Field(..., description="Path to input SDR media file")
    target_standard: str = Field("hdr10", description="Target HDR standard (hdr10, hlg)")
    peak_luminance: int = Field(1000, ge=400, le=4000, description="Peak luminance in nits")
    output_format: str = Field("mp4", description="Output format")
    priority: JobPriority = Field(JobPriority.NORMAL, description="Job priority")


@router.post("/jobs/sdr-to-hdr", response_model=ProxyJobResponse, status_code=status.HTTP_201_CREATED)
async def create_sdr_to_hdr_job(
    request: SDRToHDRRequest,
    queue_service=Depends(get_queue_service),
    current_user=Depends(get_current_user)
):
    """Create an SDR to HDR upconversion job"""
    try:
        # Validate input file exists
        if not os.path.exists(request.input_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Input file not found: {request.input_path}"
            )
        
        # Validate HDR standard
        valid_standards = ["hdr10", "hlg"]
        if request.target_standard not in valid_standards:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid HDR standard. Must be one of: {valid_standards}"
            )
        
        # Create job parameters
        parameters = {
            "target_standard": request.target_standard,
            "peak_luminance": request.peak_luminance,
            "format": request.output_format
        }
        
        # Submit job to queue
        job_id = await queue_service.submit_job(
            job_type="sdr_to_hdr",
            asset_id=request.asset_id,
            input_path=request.input_path,
            parameters=parameters,
            priority=request.priority,
            user_id=str(current_user.id)
        )
        
        logger.info(
            "sdr_to_hdr_job_created",
            job_id=job_id,
            asset_id=request.asset_id,
            target_standard=request.target_standard,
            user_id=current_user.id
        )
        
        return ProxyJobResponse(
            job_id=job_id,
            asset_id=request.asset_id,
            job_type="sdr_to_hdr",
            status="queued",
            message="SDR to HDR upconversion job queued successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "create_sdr_to_hdr_job_failed",
            error=str(e),
            asset_id=request.asset_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create SDR to HDR job: {str(e)}"
        )


# HDR delivery optimization endpoint
class HDRDeliveryOptimizationRequest(BaseModel):
    """Request model for HDR delivery optimization job"""
    asset_id: str = Field(..., description="Asset ID to optimize")
    input_path: str = Field(..., description="Path to input HDR media file")
    create_sdr_version: bool = Field(True, description="Create SDR version for compatibility")
    create_mobile_version: bool = Field(True, description="Create mobile-optimized version")
    output_dir: Optional[str] = Field(None, description="Output directory (optional)")
    priority: JobPriority = Field(JobPriority.NORMAL, description="Job priority")


@router.post("/jobs/hdr-delivery-optimization", response_model=ProxyJobResponse, status_code=status.HTTP_201_CREATED)
async def create_hdr_delivery_optimization_job(
    request: HDRDeliveryOptimizationRequest,
    queue_service=Depends(get_queue_service),
    current_user=Depends(get_current_user)
):
    """Create an HDR delivery optimization job"""
    try:
        # Validate input file exists
        if not os.path.exists(request.input_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Input file not found: {request.input_path}"
            )
        
        # Create job parameters
        parameters = {
            "create_sdr_version": request.create_sdr_version,
            "create_mobile_version": request.create_mobile_version,
            "output_dir": request.output_dir
        }
        
        # Submit job to queue
        job_id = await queue_service.submit_job(
            job_type="hdr_delivery_optimization",
            asset_id=request.asset_id,
            input_path=request.input_path,
            parameters=parameters,
            priority=request.priority,
            user_id=str(current_user.id)
        )
        
        logger.info(
            "hdr_delivery_optimization_job_created",
            job_id=job_id,
            asset_id=request.asset_id,
            create_sdr=request.create_sdr_version,
            create_mobile=request.create_mobile_version,
            user_id=current_user.id
        )
        
        return ProxyJobResponse(
            job_id=job_id,
            asset_id=request.asset_id,
            job_type="hdr_delivery_optimization",
            status="queued",
            message="HDR delivery optimization job queued successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "create_hdr_delivery_optimization_job_failed",
            error=str(e),
            asset_id=request.asset_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create HDR delivery optimization job: {str(e)}"
        )


@router.get("/capabilities/ultra-hd")
async def get_ultra_hd_capabilities(
    proxy_processor=Depends(get_proxy_processor)
):
    """Get system Ultra HD processing capabilities"""
    try:
        capabilities = proxy_processor.ultra_hd_service.processing_capabilities
        system_info = proxy_processor.ultra_hd_service.system_info
        
        return {
            "system_info": system_info,
            "processing_capabilities": capabilities,
            "supported_codecs": ["h264", "h265", "av1", "vp9", "prores", "dnxhd"],
            "supported_resolutions": [
                {"name": "8K UHD", "resolution": "7680x4320"},
                {"name": "Cinema 8K", "resolution": "8192x4320"},
                {"name": "4K UHD", "resolution": "3840x2160"},
                {"name": "Cinema 4K", "resolution": "4096x2160"},
            ],
            "quality_presets": ["low", "medium", "high", "max"],
            "processing_methods": ["standard", "chunked", "tiled"],
            "hdr_support": True,
            "tone_mapping_methods": ["none", "hable", "reinhard", "mobius"]
        }
        
    except Exception as e:
        logger.error(
            "get_ultra_hd_capabilities_failed",
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get Ultra HD capabilities: {str(e)}"
        )


# Spherical Video Analysis endpoint
class SphericalAnalysisRequest(BaseModel):
    """Request model for spherical video analysis job"""
    asset_id: str = Field(..., description="Asset ID to analyze")
    input_path: str = Field(..., description="Path to input spherical video file")
    priority: JobPriority = Field(JobPriority.NORMAL, description="Job priority")


@router.post("/jobs/spherical-analysis", response_model=ProxyJobResponse, status_code=status.HTTP_201_CREATED)
async def create_spherical_analysis_job(
    request: SphericalAnalysisRequest,
    queue_service=Depends(get_queue_service),
    current_user=Depends(get_current_user)
):
    """Create a spherical video analysis job"""
    try:
        # Validate input file exists
        if not os.path.exists(request.input_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Input file not found: {request.input_path}"
            )
        
        # Submit job to queue
        job_id = await queue_service.submit_job(
            job_type="spherical_analysis",
            asset_id=request.asset_id,
            input_path=request.input_path,
            parameters={},
            priority=request.priority,
            user_id=str(current_user.id)
        )
        
        logger.info(
            "spherical_analysis_job_created",
            job_id=job_id,
            asset_id=request.asset_id,
            user_id=current_user.id
        )
        
        return ProxyJobResponse(
            job_id=job_id,
            asset_id=request.asset_id,
            job_type="spherical_analysis",
            status="queued",
            message="Spherical video analysis job queued successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "create_spherical_analysis_job_failed",
            error=str(e),
            asset_id=request.asset_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create spherical analysis job: {str(e)}"
        )


# Spherical Conversion endpoint
class SphericalConversionRequest(BaseModel):
    """Request model for spherical projection conversion job"""
    asset_id: str = Field(..., description="Asset ID to convert")
    input_path: str = Field(..., description="Path to input spherical video file")
    input_projection: str = Field("equirectangular", description="Input projection type")
    output_projection: str = Field("cubemap", description="Output projection type")
    stereo_mode: str = Field("mono", description="Stereoscopic mode")
    output_format: str = Field("mp4", description="Output format")
    priority: JobPriority = Field(JobPriority.NORMAL, description="Job priority")


@router.post("/jobs/spherical-conversion", response_model=ProxyJobResponse, status_code=status.HTTP_201_CREATED)
async def create_spherical_conversion_job(
    request: SphericalConversionRequest,
    queue_service=Depends(get_queue_service),
    current_user=Depends(get_current_user)
):
    """Create a spherical projection conversion job"""
    try:
        # Validate input file exists
        if not os.path.exists(request.input_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Input file not found: {request.input_path}"
            )
        
        # Validate projection types
        valid_projections = ["equirectangular", "cubemap", "cubemap32", "eac", "octahedron", "perspective"]
        if request.input_projection not in valid_projections:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid input projection. Must be one of: {valid_projections}"
            )
        if request.output_projection not in valid_projections:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid output projection. Must be one of: {valid_projections}"
            )
        
        # Create job parameters
        parameters = {
            "input_projection": request.input_projection,
            "output_projection": request.output_projection,
            "stereo_mode": request.stereo_mode,
            "format": request.output_format
        }
        
        # Submit job to queue
        job_id = await queue_service.submit_job(
            job_type="spherical_conversion",
            asset_id=request.asset_id,
            input_path=request.input_path,
            parameters=parameters,
            priority=request.priority,
            user_id=str(current_user.id)
        )
        
        logger.info(
            "spherical_conversion_job_created",
            job_id=job_id,
            asset_id=request.asset_id,
            input_projection=request.input_projection,
            output_projection=request.output_projection,
            user_id=current_user.id
        )
        
        return ProxyJobResponse(
            job_id=job_id,
            asset_id=request.asset_id,
            job_type="spherical_conversion",
            status="queued",
            message="Spherical conversion job queued successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "create_spherical_conversion_job_failed",
            error=str(e),
            asset_id=request.asset_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create spherical conversion job: {str(e)}"
        )


# VR Optimization endpoint
class VROptimizationRequest(BaseModel):
    """Request model for VR optimization job"""
    asset_id: str = Field(..., description="Asset ID to optimize")
    input_path: str = Field(..., description="Path to input spherical video file")
    target_headsets: List[str] = Field(["generic"], description="Target VR headsets")
    output_dir: Optional[str] = Field(None, description="Output directory")
    priority: JobPriority = Field(JobPriority.NORMAL, description="Job priority")


@router.post("/jobs/vr-optimization", response_model=ProxyJobResponse, status_code=status.HTTP_201_CREATED)
async def create_vr_optimization_job(
    request: VROptimizationRequest,
    queue_service=Depends(get_queue_service),
    current_user=Depends(get_current_user)
):
    """Create a VR optimization job"""
    try:
        # Validate input file exists
        if not os.path.exists(request.input_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Input file not found: {request.input_path}"
            )
        
        # Validate headsets
        valid_headsets = ["oculus_quest", "oculus_rift", "htc_vive", "pico", "generic"]
        for headset in request.target_headsets:
            if headset not in valid_headsets:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid headset: {headset}. Must be one of: {valid_headsets}"
                )
        
        # Create job parameters
        parameters = {
            "target_headsets": request.target_headsets,
            "output_dir": request.output_dir
        }
        
        # Submit job to queue
        job_id = await queue_service.submit_job(
            job_type="vr_optimization",
            asset_id=request.asset_id,
            input_path=request.input_path,
            parameters=parameters,
            priority=request.priority,
            user_id=str(current_user.id)
        )
        
        logger.info(
            "vr_optimization_job_created",
            job_id=job_id,
            asset_id=request.asset_id,
            target_headsets=request.target_headsets,
            user_id=current_user.id
        )
        
        return ProxyJobResponse(
            job_id=job_id,
            asset_id=request.asset_id,
            job_type="vr_optimization",
            status="queued",
            message="VR optimization job queued successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "create_vr_optimization_job_failed",
            error=str(e),
            asset_id=request.asset_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create VR optimization job: {str(e)}"
        )


# Spatial Metadata endpoint
class SpatialMetadataRequest(BaseModel):
    """Request model for spatial metadata injection job"""
    asset_id: str = Field(..., description="Asset ID to process")
    input_path: str = Field(..., description="Path to input spherical video file")
    projection: str = Field("equirectangular", description="Projection type")
    stereo_mode: str = Field("mono", description="Stereoscopic mode")
    output_format: str = Field("mp4", description="Output format")
    priority: JobPriority = Field(JobPriority.NORMAL, description="Job priority")


@router.post("/jobs/spatial-metadata", response_model=ProxyJobResponse, status_code=status.HTTP_201_CREATED)
async def create_spatial_metadata_job(
    request: SpatialMetadataRequest,
    queue_service=Depends(get_queue_service),
    current_user=Depends(get_current_user)
):
    """Create a spatial metadata injection job"""
    try:
        # Validate input file exists
        if not os.path.exists(request.input_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Input file not found: {request.input_path}"
            )
        
        # Create job parameters
        parameters = {
            "projection": request.projection,
            "stereo_mode": request.stereo_mode,
            "format": request.output_format
        }
        
        # Submit job to queue
        job_id = await queue_service.submit_job(
            job_type="spatial_metadata",
            asset_id=request.asset_id,
            input_path=request.input_path,
            parameters=parameters,
            priority=request.priority,
            user_id=str(current_user.id)
        )
        
        logger.info(
            "spatial_metadata_job_created",
            job_id=job_id,
            asset_id=request.asset_id,
            projection=request.projection,
            user_id=current_user.id
        )
        
        return ProxyJobResponse(
            job_id=job_id,
            asset_id=request.asset_id,
            job_type="spatial_metadata",
            status="queued",
            message="Spatial metadata job queued successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "create_spatial_metadata_job_failed",
            error=str(e),
            asset_id=request.asset_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create spatial metadata job: {str(e)}"
        )


@router.get("/capabilities/hdr")
async def get_hdr_capabilities(
    proxy_processor=Depends(get_proxy_processor)
):
    """Get system HDR processing capabilities"""
    try:
        capabilities = await proxy_processor.hdr_service.get_hdr_processing_capabilities()
        
        return {
            "hdr_capabilities": capabilities,
            "supported_standards": ["HDR10", "HLG", "HDR10+", "Dolby Vision"],
            "tone_mapping_algorithms": ["hable", "reinhard", "mobius", "clip", "linear", "gamma"],
            "color_spaces": ["bt2020", "bt709", "dci-p3"],
            "transfer_functions": ["smpte2084", "arib-std-b67", "bt709"],
            "supported_bit_depths": [8, 10, 12],
            "features": {
                "hdr_to_sdr_conversion": True,
                "sdr_to_hdr_upconversion": True,
                "metadata_preservation": True,
                "delivery_optimization": True,
                "content_analysis": True
            }
        }
        
    except Exception as e:
        logger.error(
            "get_hdr_capabilities_failed",
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get HDR capabilities: {str(e)}"
        )


@router.get("/capabilities/spherical")
async def get_spherical_capabilities(
    proxy_processor=Depends(get_proxy_processor)
):
    """Get system spherical video processing capabilities"""
    try:
        capabilities = await proxy_processor.spherical_service.get_spherical_capabilities()
        
        return {
            "spherical_capabilities": capabilities,
            "supported_projections": ["equirectangular", "cubemap", "cubemap32", "eac", "octahedron", "perspective"],
            "supported_stereo_modes": ["mono", "side_by_side", "top_bottom"],
            "supported_headsets": ["oculus_quest", "oculus_rift", "htc_vive", "pico", "generic"],
            "quality_presets": ["low", "medium", "high", "ultra"],
            "interpolation_methods": ["nearest", "bilinear", "bicubic", "lanczos"],
            "max_resolution": "8K (7680x3840)",
            "recommended_fps": [60, 90, 120],
            "features": {
                "projection_conversion": True,
                "vr_optimization": True,
                "spatial_metadata": True,
                "stereoscopic_support": True,
                "content_analysis": True
            }
        }
        
    except Exception as e:
        logger.error(
            "get_spherical_capabilities_failed",
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get spherical capabilities: {str(e)}"
        )


# VR Content Processing Endpoints

class VRContentAnalysisRequest(BaseModel):
    """Request model for VR content analysis"""
    asset_id: str = Field(..., description="Asset ID to analyze")
    input_path: str = Field(..., description="Path to VR content file")
    priority: JobPriority = Field(JobPriority.NORMAL, description="Job priority")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class VRContentProcessingRequest(BaseModel):
    """Request model for VR content processing"""
    asset_id: str = Field(..., description="Asset ID to process")
    input_path: str = Field(..., description="Path to VR content file")
    platform: str = Field("oculus_quest", description="Target VR platform")
    preset: str = Field("vr_high", description="Quality preset")
    custom_params: Optional[Dict[str, Any]] = Field(None, description="Custom processing parameters")
    priority: JobPriority = Field(JobPriority.NORMAL, description="Job priority")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class VRPreviewRequest(BaseModel):
    """Request model for VR preview creation"""
    asset_id: str = Field(..., description="Asset ID")
    input_path: str = Field(..., description="Path to VR content file")
    preview_type: str = Field("flat", pattern="^(flat|little_planet|panoramic|cube_map)$", description="Preview type")
    duration: int = Field(30, ge=1, le=300, description="Preview duration in seconds")
    priority: JobPriority = Field(JobPriority.NORMAL, description="Job priority")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class VRMotionExtractionRequest(BaseModel):
    """Request model for VR motion data extraction"""
    asset_id: str = Field(..., description="Asset ID")
    input_path: str = Field(..., description="Path to VR content file")
    priority: JobPriority = Field(JobPriority.NORMAL, description="Job priority")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class VRStreamingOptimizationRequest(BaseModel):
    """Request model for VR streaming optimization"""
    asset_id: str = Field(..., description="Asset ID")
    input_path: str = Field(..., description="Path to VR content file")
    streaming_type: str = Field("adaptive", pattern="^(adaptive|low_latency)$", description="Streaming optimization type")
    priority: JobPriority = Field(JobPriority.NORMAL, description="Job priority")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class VRThumbnailSequenceRequest(BaseModel):
    """Request model for VR thumbnail sequence"""
    asset_id: str = Field(..., description="Asset ID")
    input_path: str = Field(..., description="Path to VR content file")
    count: int = Field(12, ge=1, le=100, description="Number of thumbnails")
    preview_angles: Optional[List[List[float]]] = Field(None, description="Custom preview angles as [[yaw, pitch], ...]")
    priority: JobPriority = Field(JobPriority.NORMAL, description="Job priority")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


@router.post("/jobs/vr-content-analysis", response_model=ProxyJobResponse)
async def create_vr_content_analysis_job(
    request: VRContentAnalysisRequest,
    current_user: dict = Depends(get_current_user),
    queue_service = Depends(get_queue_service)
):
    """Create job for VR content analysis"""
    try:
        # Validate input path
        if not request.input_path:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Input path is required"
            )
        
        # Create job
        job = ProxyJob(
            job_id=f"vr_analysis_{request.asset_id}_{datetime.utcnow().timestamp()}",
            job_type="vr_content_analysis",
            asset_id=request.asset_id,
            input_path=request.input_path,
            parameters={},
            priority=request.priority,
            metadata=request.metadata or {},
            created_by=current_user["id"]
        )
        
        # Queue job
        job_id = await queue_service.publish_job(job)
        
        logger.info(
            "vr_content_analysis_job_created",
            job_id=job_id,
            asset_id=request.asset_id,
            user_id=current_user["id"]
        )
        
        return ProxyJobResponse(
            job_id=job_id,
            asset_id=request.asset_id,
            job_type="vr_content_analysis",
            status="queued",
            message="VR content analysis job queued successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "create_vr_content_analysis_job_failed",
            error=str(e),
            asset_id=request.asset_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create VR content analysis job: {str(e)}"
        )


@router.post("/jobs/vr-content-processing", response_model=ProxyJobResponse)
async def create_vr_content_processing_job(
    request: VRContentProcessingRequest,
    current_user: dict = Depends(get_current_user),
    queue_service = Depends(get_queue_service)
):
    """Create job for VR content processing"""
    try:
        # Validate input path
        if not request.input_path:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Input path is required"
            )
        
        # Create job
        job = ProxyJob(
            job_id=f"vr_process_{request.asset_id}_{datetime.utcnow().timestamp()}",
            job_type="vr_content_processing",
            asset_id=request.asset_id,
            input_path=request.input_path,
            parameters={
                "platform": request.platform,
                "preset": request.preset,
                "custom_params": request.custom_params or {}
            },
            priority=request.priority,
            metadata=request.metadata or {},
            created_by=current_user["id"]
        )
        
        # Queue job
        job_id = await queue_service.publish_job(job)
        
        logger.info(
            "vr_content_processing_job_created",
            job_id=job_id,
            asset_id=request.asset_id,
            platform=request.platform,
            preset=request.preset,
            user_id=current_user["id"]
        )
        
        return ProxyJobResponse(
            job_id=job_id,
            asset_id=request.asset_id,
            job_type="vr_content_processing",
            status="queued",
            message="VR content processing job queued successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "create_vr_content_processing_job_failed",
            error=str(e),
            asset_id=request.asset_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create VR content processing job: {str(e)}"
        )


@router.post("/jobs/vr-preview", response_model=ProxyJobResponse)
async def create_vr_preview_job(
    request: VRPreviewRequest,
    current_user: dict = Depends(get_current_user),
    queue_service = Depends(get_queue_service)
):
    """Create job for VR preview generation"""
    try:
        # Validate input path
        if not request.input_path:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Input path is required"
            )
        
        # Create job
        job = ProxyJob(
            job_id=f"vr_preview_{request.asset_id}_{datetime.utcnow().timestamp()}",
            job_type="vr_preview",
            asset_id=request.asset_id,
            input_path=request.input_path,
            parameters={
                "preview_type": request.preview_type,
                "duration": request.duration
            },
            priority=request.priority,
            metadata=request.metadata or {},
            created_by=current_user["id"]
        )
        
        # Queue job
        job_id = await queue_service.publish_job(job)
        
        logger.info(
            "vr_preview_job_created",
            job_id=job_id,
            asset_id=request.asset_id,
            preview_type=request.preview_type,
            user_id=current_user["id"]
        )
        
        return ProxyJobResponse(
            job_id=job_id,
            asset_id=request.asset_id,
            job_type="vr_preview",
            status="queued",
            message="VR preview job queued successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "create_vr_preview_job_failed",
            error=str(e),
            asset_id=request.asset_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create VR preview job: {str(e)}"
        )


@router.post("/jobs/vr-motion-extraction", response_model=ProxyJobResponse)
async def create_vr_motion_extraction_job(
    request: VRMotionExtractionRequest,
    current_user: dict = Depends(get_current_user),
    queue_service = Depends(get_queue_service)
):
    """Create job for VR motion data extraction"""
    try:
        # Validate input path
        if not request.input_path:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Input path is required"
            )
        
        # Create job
        job = ProxyJob(
            job_id=f"vr_motion_{request.asset_id}_{datetime.utcnow().timestamp()}",
            job_type="vr_motion_extraction",
            asset_id=request.asset_id,
            input_path=request.input_path,
            parameters={},
            priority=request.priority,
            metadata=request.metadata or {},
            created_by=current_user["id"]
        )
        
        # Queue job
        job_id = await queue_service.publish_job(job)
        
        logger.info(
            "vr_motion_extraction_job_created",
            job_id=job_id,
            asset_id=request.asset_id,
            user_id=current_user["id"]
        )
        
        return ProxyJobResponse(
            job_id=job_id,
            asset_id=request.asset_id,
            job_type="vr_motion_extraction",
            status="queued",
            message="VR motion extraction job queued successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "create_vr_motion_extraction_job_failed",
            error=str(e),
            asset_id=request.asset_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create VR motion extraction job: {str(e)}"
        )


@router.post("/jobs/vr-streaming-optimization", response_model=ProxyJobResponse)
async def create_vr_streaming_optimization_job(
    request: VRStreamingOptimizationRequest,
    current_user: dict = Depends(get_current_user),
    queue_service = Depends(get_queue_service)
):
    """Create job for VR streaming optimization"""
    try:
        # Validate input path
        if not request.input_path:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Input path is required"
            )
        
        # Create job
        job = ProxyJob(
            job_id=f"vr_streaming_{request.asset_id}_{datetime.utcnow().timestamp()}",
            job_type="vr_streaming_optimization",
            asset_id=request.asset_id,
            input_path=request.input_path,
            parameters={
                "streaming_type": request.streaming_type
            },
            priority=request.priority,
            metadata=request.metadata or {},
            created_by=current_user["id"]
        )
        
        # Queue job
        job_id = await queue_service.publish_job(job)
        
        logger.info(
            "vr_streaming_optimization_job_created",
            job_id=job_id,
            asset_id=request.asset_id,
            streaming_type=request.streaming_type,
            user_id=current_user["id"]
        )
        
        return ProxyJobResponse(
            job_id=job_id,
            asset_id=request.asset_id,
            job_type="vr_streaming_optimization",
            status="queued",
            message="VR streaming optimization job queued successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "create_vr_streaming_optimization_job_failed",
            error=str(e),
            asset_id=request.asset_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create VR streaming optimization job: {str(e)}"
        )


@router.post("/jobs/vr-thumbnail-sequence", response_model=ProxyJobResponse)
async def create_vr_thumbnail_sequence_job(
    request: VRThumbnailSequenceRequest,
    current_user: dict = Depends(get_current_user),
    queue_service = Depends(get_queue_service)
):
    """Create job for VR thumbnail sequence generation"""
    try:
        # Validate input path
        if not request.input_path:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Input path is required"
            )
        
        # Convert preview angles format
        preview_angles = None
        if request.preview_angles:
            preview_angles = [(angle[0], angle[1]) for angle in request.preview_angles]
        
        # Create job
        job = ProxyJob(
            job_id=f"vr_thumbs_{request.asset_id}_{datetime.utcnow().timestamp()}",
            job_type="vr_thumbnail_sequence",
            asset_id=request.asset_id,
            input_path=request.input_path,
            parameters={
                "count": request.count,
                "preview_angles": preview_angles
            },
            priority=request.priority,
            metadata=request.metadata or {},
            created_by=current_user["id"]
        )
        
        # Queue job
        job_id = await queue_service.publish_job(job)
        
        logger.info(
            "vr_thumbnail_sequence_job_created",
            job_id=job_id,
            asset_id=request.asset_id,
            count=request.count,
            user_id=current_user["id"]
        )
        
        return ProxyJobResponse(
            job_id=job_id,
            asset_id=request.asset_id,
            job_type="vr_thumbnail_sequence",
            status="queued",
            message="VR thumbnail sequence job queued successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "create_vr_thumbnail_sequence_job_failed",
            error=str(e),
            asset_id=request.asset_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create VR thumbnail sequence job: {str(e)}"
        )


@router.get("/capabilities/vr")
async def get_vr_capabilities(
    proxy_processor=Depends(get_proxy_processor)
):
    """Get system VR content processing capabilities"""
    try:
        return {
            "vr_capabilities": {
                "gpu_available": True,  # Would check actual GPU in production
                "ffmpeg_vr_support": True,
                "spatial_audio_support": True
            },
            "content_types": ["vr180", "vr360", "ar_object", "volumetric", "light_field", "holographic"],
            "render_modes": ["monoscopic", "stereoscopic_sbs", "stereoscopic_tb", "anaglyph", "multi_view"],
            "interaction_modes": ["passive", "gaze_based", "controller", "hand_tracking", "full_body"],
            "supported_platforms": [
                "oculus_quest", "oculus_rift", "htc_vive", "valve_index", "pico",
                "playstation_vr", "windows_mr", "magic_leap", "hololens", 
                "apple_vision_pro", "web_xr"
            ],
            "preview_types": ["flat", "little_planet", "panoramic", "cube_map"],
            "streaming_types": ["adaptive", "low_latency"],
            "quality_presets": ["vr_low", "vr_medium", "vr_high", "vr_ultra"],
            "max_resolution": "8K (8192x4096)",
            "supported_fps": [60, 72, 80, 90, 96, 120, 144],
            "features": {
                "content_analysis": True,
                "platform_optimization": True,
                "preview_generation": True,
                "motion_extraction": True,
                "streaming_optimization": True,
                "thumbnail_sequences": True,
                "spatial_audio_processing": True
            }
        }
        
    except Exception as e:
        logger.error(
            "get_vr_capabilities_failed",
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get VR capabilities: {str(e)}"
        )


# Spatial Audio Processing Endpoints

class SpatialAudioAnalysisRequest(BaseModel):
    """Request model for spatial audio analysis"""
    asset_id: str = Field(..., description="Asset ID to analyze")
    input_path: str = Field(..., description="Path to audio file")
    priority: JobPriority = Field(JobPriority.NORMAL, description="Job priority")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class SpatialAudioConversionRequest(BaseModel):
    """Request model for spatial audio conversion"""
    asset_id: str = Field(..., description="Asset ID to convert")
    input_path: str = Field(..., description="Path to audio file")
    target_format: str = Field("5.1", description="Target spatial format (stereo, 5.1, 7.1, 7.1.4, etc.)")
    codec: Optional[str] = Field(None, description="Optional audio codec")
    custom_params: Optional[Dict[str, Any]] = Field(None, description="Custom conversion parameters")
    priority: JobPriority = Field(JobPriority.NORMAL, description="Job priority")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class AmbisonicEncodingRequest(BaseModel):
    """Request model for Ambisonic encoding"""
    asset_id: str = Field(..., description="Asset ID")
    input_path: str = Field(..., description="Path to audio file")
    order: int = Field(1, ge=1, le=5, description="Ambisonic order (1-5)")
    normalize: bool = Field(True, description="Normalize output")
    priority: JobPriority = Field(JobPriority.NORMAL, description="Job priority")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class BinauralRenderingRequest(BaseModel):
    """Request model for binaural rendering"""
    asset_id: str = Field(..., description="Asset ID")
    input_path: str = Field(..., description="Path to Ambisonic audio")
    hrtf_profile: str = Field("generic", description="HRTF profile (generic, kemar, cipic, etc.)")
    head_tracking: Optional[Dict[str, float]] = Field(None, description="Head tracking data (yaw, pitch, roll)")
    priority: JobPriority = Field(JobPriority.NORMAL, description="Job priority")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class RoomAcousticsRequest(BaseModel):
    """Request model for room acoustics simulation"""
    asset_id: str = Field(..., description="Asset ID")
    input_path: str = Field(..., description="Path to audio file")
    room_preset: str = Field("studio", description="Room preset (anechoic, studio, living_room, concert_hall, cathedral, outdoor)")
    custom_params: Optional[Dict[str, float]] = Field(None, description="Custom room parameters")
    priority: JobPriority = Field(JobPriority.NORMAL, description="Job priority")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class SpatialMixRequest(BaseModel):
    """Request model for spatial audio mixing"""
    asset_id: str = Field(..., description="Asset ID for the mix")
    input_files: List[Dict[str, Any]] = Field(..., description="List of input files with position data")
    output_format: str = Field("5.1", description="Output spatial format")
    priority: JobPriority = Field(JobPriority.NORMAL, description="Job priority")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


@router.post("/jobs/spatial-audio-analysis", response_model=ProxyJobResponse)
async def create_spatial_audio_analysis_job(
    request: SpatialAudioAnalysisRequest,
    current_user: dict = Depends(get_current_user),
    queue_service = Depends(get_queue_service)
):
    """Create job for spatial audio analysis"""
    try:
        # Validate input path
        if not request.input_path:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Input path is required"
            )
        
        # Create job
        job = ProxyJob(
            job_id=f"spatial_analysis_{request.asset_id}_{datetime.utcnow().timestamp()}",
            job_type="spatial_audio_analysis",
            asset_id=request.asset_id,
            input_path=request.input_path,
            parameters={},
            priority=request.priority,
            metadata=request.metadata or {},
            created_by=current_user["id"]
        )
        
        # Queue job
        job_id = await queue_service.publish_job(job)
        
        logger.info(
            "spatial_audio_analysis_job_created",
            job_id=job_id,
            asset_id=request.asset_id,
            user_id=current_user["id"]
        )
        
        return ProxyJobResponse(
            job_id=job_id,
            asset_id=request.asset_id,
            job_type="spatial_audio_analysis",
            status="queued",
            message="Spatial audio analysis job queued successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "create_spatial_audio_analysis_job_failed",
            error=str(e),
            asset_id=request.asset_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create spatial audio analysis job: {str(e)}"
        )


@router.post("/jobs/spatial-audio-conversion", response_model=ProxyJobResponse)
async def create_spatial_audio_conversion_job(
    request: SpatialAudioConversionRequest,
    current_user: dict = Depends(get_current_user),
    queue_service = Depends(get_queue_service)
):
    """Create job for spatial audio format conversion"""
    try:
        # Validate input path
        if not request.input_path:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Input path is required"
            )
        
        # Create job
        job = ProxyJob(
            job_id=f"spatial_convert_{request.asset_id}_{datetime.utcnow().timestamp()}",
            job_type="spatial_audio_conversion",
            asset_id=request.asset_id,
            input_path=request.input_path,
            parameters={
                "target_format": request.target_format,
                "codec": request.codec,
                "custom_params": request.custom_params or {}
            },
            priority=request.priority,
            metadata=request.metadata or {},
            created_by=current_user["id"]
        )
        
        # Queue job
        job_id = await queue_service.publish_job(job)
        
        logger.info(
            "spatial_audio_conversion_job_created",
            job_id=job_id,
            asset_id=request.asset_id,
            target_format=request.target_format,
            user_id=current_user["id"]
        )
        
        return ProxyJobResponse(
            job_id=job_id,
            asset_id=request.asset_id,
            job_type="spatial_audio_conversion",
            status="queued",
            message="Spatial audio conversion job queued successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "create_spatial_audio_conversion_job_failed",
            error=str(e),
            asset_id=request.asset_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create spatial audio conversion job: {str(e)}"
        )


@router.post("/jobs/ambisonic-encoding", response_model=ProxyJobResponse)
async def create_ambisonic_encoding_job(
    request: AmbisonicEncodingRequest,
    current_user: dict = Depends(get_current_user),
    queue_service = Depends(get_queue_service)
):
    """Create job for Ambisonic encoding"""
    try:
        # Validate input path
        if not request.input_path:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Input path is required"
            )
        
        # Create job
        job = ProxyJob(
            job_id=f"ambisonic_{request.asset_id}_{datetime.utcnow().timestamp()}",
            job_type="ambisonic_encoding",
            asset_id=request.asset_id,
            input_path=request.input_path,
            parameters={
                "order": request.order,
                "normalize": request.normalize
            },
            priority=request.priority,
            metadata=request.metadata or {},
            created_by=current_user["id"]
        )
        
        # Queue job
        job_id = await queue_service.publish_job(job)
        
        logger.info(
            "ambisonic_encoding_job_created",
            job_id=job_id,
            asset_id=request.asset_id,
            order=request.order,
            user_id=current_user["id"]
        )
        
        return ProxyJobResponse(
            job_id=job_id,
            asset_id=request.asset_id,
            job_type="ambisonic_encoding",
            status="queued",
            message="Ambisonic encoding job queued successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "create_ambisonic_encoding_job_failed",
            error=str(e),
            asset_id=request.asset_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create Ambisonic encoding job: {str(e)}"
        )


@router.post("/jobs/binaural-rendering", response_model=ProxyJobResponse)
async def create_binaural_rendering_job(
    request: BinauralRenderingRequest,
    current_user: dict = Depends(get_current_user),
    queue_service = Depends(get_queue_service)
):
    """Create job for binaural rendering from Ambisonic"""
    try:
        # Validate input path
        if not request.input_path:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Input path is required"
            )
        
        # Create job
        job = ProxyJob(
            job_id=f"binaural_{request.asset_id}_{datetime.utcnow().timestamp()}",
            job_type="binaural_rendering",
            asset_id=request.asset_id,
            input_path=request.input_path,
            parameters={
                "hrtf_profile": request.hrtf_profile,
                "head_tracking": request.head_tracking
            },
            priority=request.priority,
            metadata=request.metadata or {},
            created_by=current_user["id"]
        )
        
        # Queue job
        job_id = await queue_service.publish_job(job)
        
        logger.info(
            "binaural_rendering_job_created",
            job_id=job_id,
            asset_id=request.asset_id,
            hrtf_profile=request.hrtf_profile,
            user_id=current_user["id"]
        )
        
        return ProxyJobResponse(
            job_id=job_id,
            asset_id=request.asset_id,
            job_type="binaural_rendering",
            status="queued",
            message="Binaural rendering job queued successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "create_binaural_rendering_job_failed",
            error=str(e),
            asset_id=request.asset_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create binaural rendering job: {str(e)}"
        )


@router.post("/jobs/room-acoustics", response_model=ProxyJobResponse)
async def create_room_acoustics_job(
    request: RoomAcousticsRequest,
    current_user: dict = Depends(get_current_user),
    queue_service = Depends(get_queue_service)
):
    """Create job for room acoustics simulation"""
    try:
        # Validate input path
        if not request.input_path:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Input path is required"
            )
        
        # Create job
        job = ProxyJob(
            job_id=f"room_{request.asset_id}_{datetime.utcnow().timestamp()}",
            job_type="room_acoustics",
            asset_id=request.asset_id,
            input_path=request.input_path,
            parameters={
                "room_preset": request.room_preset,
                "custom_params": request.custom_params
            },
            priority=request.priority,
            metadata=request.metadata or {},
            created_by=current_user["id"]
        )
        
        # Queue job
        job_id = await queue_service.publish_job(job)
        
        logger.info(
            "room_acoustics_job_created",
            job_id=job_id,
            asset_id=request.asset_id,
            room_preset=request.room_preset,
            user_id=current_user["id"]
        )
        
        return ProxyJobResponse(
            job_id=job_id,
            asset_id=request.asset_id,
            job_type="room_acoustics",
            status="queued",
            message="Room acoustics job queued successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "create_room_acoustics_job_failed",
            error=str(e),
            asset_id=request.asset_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create room acoustics job: {str(e)}"
        )


@router.post("/jobs/spatial-mix", response_model=ProxyJobResponse)
async def create_spatial_mix_job(
    request: SpatialMixRequest,
    current_user: dict = Depends(get_current_user),
    queue_service = Depends(get_queue_service)
):
    """Create job for spatial audio mixing"""
    try:
        # Validate input files
        if not request.input_files:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one input file is required"
            )
        
        # Create job
        job = ProxyJob(
            job_id=f"spatial_mix_{request.asset_id}_{datetime.utcnow().timestamp()}",
            job_type="spatial_mix",
            asset_id=request.asset_id,
            input_path="",  # Not used for spatial mix
            parameters={
                "input_files": request.input_files,
                "output_format": request.output_format
            },
            priority=request.priority,
            metadata=request.metadata or {},
            created_by=current_user["id"]
        )
        
        # Queue job
        job_id = await queue_service.publish_job(job)
        
        logger.info(
            "spatial_mix_job_created",
            job_id=job_id,
            asset_id=request.asset_id,
            input_count=len(request.input_files),
            output_format=request.output_format,
            user_id=current_user["id"]
        )
        
        return ProxyJobResponse(
            job_id=job_id,
            asset_id=request.asset_id,
            job_type="spatial_mix",
            status="queued",
            message="Spatial mix job queued successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "create_spatial_mix_job_failed",
            error=str(e),
            asset_id=request.asset_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create spatial mix job: {str(e)}"
        )


@router.get("/capabilities/spatial-audio")
async def get_spatial_audio_capabilities(
    proxy_processor=Depends(get_proxy_processor)
):
    """Get system spatial audio processing capabilities"""
    try:
        return {
            "spatial_audio_capabilities": {
                "ffmpeg_spatial_support": True,
                "ambisonics_support": True,
                "binaural_support": True,
                "object_based_support": True
            },
            "supported_formats": [
                "stereo", "5.1", "7.1", "7.1.4", "9.1.6",
                "ambisonic_foa", "ambisonic_hoa", "binaural", "object_based"
            ],
            "ambisonic_orders": [1, 2, 3, 4, 5],
            "spatial_codecs": [
                "aac_spatial", "eac3_atmos", "truehd_atmos", "dts_x",
                "opus_spatial", "flac_spatial", "pcm"
            ],
            "hrtf_profiles": ["generic", "kemar", "cipic", "listen", "ari", "custom"],
            "room_presets": [
                "anechoic", "studio", "living_room", "concert_hall",
                "cathedral", "outdoor", "custom"
            ],
            "max_channels": 64,
            "max_ambisonic_order": 5,
            "features": {
                "spatial_analysis": True,
                "format_conversion": True,
                "ambisonic_encoding": True,
                "binaural_rendering": True,
                "room_simulation": True,
                "spatial_mixing": True,
                "object_extraction": True,
                "immersive_preview": True,
                "soundfield_analysis": True
            }
        }
        
    except Exception as e:
        logger.error(
            "get_spatial_audio_capabilities_failed",
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get spatial audio capabilities: {str(e)}"
        )


# Live Streaming Endpoints

class LiveStreamStartRequest(BaseModel):
    """Request model for starting a live stream"""
    asset_id: str = Field(..., description="Asset ID for the stream")
    input_source: str = Field(..., description="Input source URL or device")
    output_url: str = Field(..., description="Output streaming URL")
    protocol: str = Field("hls", description="Streaming protocol (hls, dash, rtmp, rtsp, srt)")
    quality: str = Field("high", description="Stream quality preset")
    codec: str = Field("h264", description="Video codec")
    audio_codec: str = Field("aac", description="Audio codec")
    latency: str = Field("low", description="Target latency mode")
    dvr_mode: str = Field("disabled", description="DVR recording mode")
    custom_params: Optional[Dict[str, Any]] = Field(None, description="Custom streaming parameters")
    priority: JobPriority = Field(JobPriority.HIGH, description="Job priority")


@router.post("/jobs/live-stream-start", response_model=ProxyJobResponse)
async def start_live_stream(
    request: LiveStreamStartRequest,
    current_user: dict = Depends(get_current_user),
    queue_service = Depends(get_queue_service)
):
    """Start a new live stream"""
    try:
        # Validate protocol
        valid_protocols = ["hls", "dash", "rtmp", "rtsp", "srt", "webrtc", "rist", "ndi"]
        if request.protocol not in valid_protocols:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid protocol. Must be one of: {valid_protocols}"
            )
        
        # Create job
        job = ProxyJob(
            job_id=f"stream_start_{request.asset_id}_{datetime.utcnow().timestamp()}",
            job_type="live_stream_start",
            asset_id=request.asset_id,
            input_path=request.input_source,
            parameters={
                "input_source": request.input_source,
                "output_url": request.output_url,
                "protocol": request.protocol,
                "quality": request.quality,
                "codec": request.codec,
                "audio_codec": request.audio_codec,
                "latency": request.latency,
                "dvr_mode": request.dvr_mode,
                "custom_params": request.custom_params
            },
            priority=request.priority,
            created_at=datetime.utcnow(),
            status=JobStatus.PENDING
        )
        
        # Submit job
        await queue_service.submit_job(job)
        
        logger.info(
            "live_stream_start_job_created",
            job_id=job.job_id,
            asset_id=request.asset_id,
            protocol=request.protocol
        )
        
        return ProxyJobResponse(
            job_id=job.job_id,
            asset_id=request.asset_id,
            job_type="live_stream_start",
            status="pending",
            message="Live stream start job created successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "create_live_stream_start_job_failed",
            error=str(e),
            asset_id=request.asset_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create live stream start job: {str(e)}"
        )


class LiveStreamStopRequest(BaseModel):
    """Request model for stopping a live stream"""
    asset_id: str = Field(..., description="Asset ID of the stream")
    stream_id: str = Field(..., description="Stream ID to stop")
    priority: JobPriority = Field(JobPriority.HIGH, description="Job priority")


@router.post("/jobs/live-stream-stop", response_model=ProxyJobResponse)
async def stop_live_stream(
    request: LiveStreamStopRequest,
    current_user: dict = Depends(get_current_user),
    queue_service = Depends(get_queue_service)
):
    """Stop an active live stream"""
    try:
        # Create job
        job = ProxyJob(
            job_id=f"stream_stop_{request.asset_id}_{datetime.utcnow().timestamp()}",
            job_type="live_stream_stop",
            asset_id=request.asset_id,
            input_path="",  # Not needed for stop
            parameters={
                "stream_id": request.stream_id
            },
            priority=request.priority,
            created_at=datetime.utcnow(),
            status=JobStatus.PENDING
        )
        
        # Submit job
        await queue_service.submit_job(job)
        
        logger.info(
            "live_stream_stop_job_created",
            job_id=job.job_id,
            stream_id=request.stream_id
        )
        
        return ProxyJobResponse(
            job_id=job.job_id,
            asset_id=request.asset_id,
            job_type="live_stream_stop",
            status="pending",
            message="Live stream stop job created successfully"
        )
        
    except Exception as e:
        logger.error(
            "create_live_stream_stop_job_failed",
            error=str(e),
            stream_id=request.stream_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create live stream stop job: {str(e)}"
        )


class AdaptiveStreamRequest(BaseModel):
    """Request model for creating adaptive bitrate stream"""
    asset_id: str = Field(..., description="Asset ID for the stream")
    input_source: str = Field(..., description="Input source URL or device")
    output_base_path: str = Field(..., description="Base path for output files")
    protocol: str = Field("hls", description="Streaming protocol (hls or dash)")
    codec: str = Field("h264", description="Video codec")
    audio_codec: str = Field("aac", description="Audio codec")
    ladder: Optional[List[Dict[str, Any]]] = Field(None, description="Custom ABR ladder")
    priority: JobPriority = Field(JobPriority.NORMAL, description="Job priority")


@router.post("/jobs/adaptive-stream", response_model=ProxyJobResponse)
async def create_adaptive_stream(
    request: AdaptiveStreamRequest,
    current_user: dict = Depends(get_current_user),
    queue_service = Depends(get_queue_service)
):
    """Create an adaptive bitrate stream"""
    try:
        # Validate protocol
        if request.protocol not in ["hls", "dash"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Adaptive streaming only supports HLS and DASH protocols"
            )
        
        # Create job
        job = ProxyJob(
            job_id=f"adaptive_{request.asset_id}_{datetime.utcnow().timestamp()}",
            job_type="adaptive_stream",
            asset_id=request.asset_id,
            input_path=request.input_source,
            parameters={
                "input_source": request.input_source,
                "output_base_path": request.output_base_path,
                "protocol": request.protocol,
                "codec": request.codec,
                "audio_codec": request.audio_codec,
                "ladder": request.ladder
            },
            priority=request.priority,
            created_at=datetime.utcnow(),
            status=JobStatus.PENDING
        )
        
        # Submit job
        await queue_service.submit_job(job)
        
        logger.info(
            "adaptive_stream_job_created",
            job_id=job.job_id,
            asset_id=request.asset_id,
            protocol=request.protocol
        )
        
        return ProxyJobResponse(
            job_id=job.job_id,
            asset_id=request.asset_id,
            job_type="adaptive_stream",
            status="pending",
            message="Adaptive stream job created successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "create_adaptive_stream_job_failed",
            error=str(e),
            asset_id=request.asset_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create adaptive stream job: {str(e)}"
        )


class StreamOverlayRequest(BaseModel):
    """Request model for adding overlay to stream"""
    asset_id: str = Field(..., description="Asset ID of the stream")
    stream_id: str = Field(..., description="Stream ID to add overlay to")
    overlay_type: str = Field(..., description="Type of overlay (logo, text, lower_third, etc.)")
    overlay_data: Dict[str, Any] = Field(..., description="Overlay configuration data")
    priority: JobPriority = Field(JobPriority.NORMAL, description="Job priority")


@router.post("/jobs/stream-overlay", response_model=ProxyJobResponse)
async def add_stream_overlay(
    request: StreamOverlayRequest,
    current_user: dict = Depends(get_current_user),
    queue_service = Depends(get_queue_service)
):
    """Add overlay to an active stream"""
    try:
        # Create job
        job = ProxyJob(
            job_id=f"overlay_{request.stream_id}_{datetime.utcnow().timestamp()}",
            job_type="stream_overlay",
            asset_id=request.asset_id,
            input_path="",  # Not needed
            parameters={
                "stream_id": request.stream_id,
                "overlay_type": request.overlay_type,
                "overlay_data": request.overlay_data
            },
            priority=request.priority,
            created_at=datetime.utcnow(),
            status=JobStatus.PENDING
        )
        
        # Submit job
        await queue_service.submit_job(job)
        
        logger.info(
            "stream_overlay_job_created",
            job_id=job.job_id,
            stream_id=request.stream_id,
            overlay_type=request.overlay_type
        )
        
        return ProxyJobResponse(
            job_id=job.job_id,
            asset_id=request.asset_id,
            job_type="stream_overlay",
            status="pending",
            message="Stream overlay job created successfully"
        )
        
    except Exception as e:
        logger.error(
            "create_stream_overlay_job_failed",
            error=str(e),
            stream_id=request.stream_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create stream overlay job: {str(e)}"
        )


class StreamRecordingRequest(BaseModel):
    """Request model for recording from stream"""
    asset_id: str = Field(..., description="Asset ID of the stream")
    stream_id: str = Field(..., description="Stream ID to record from")
    output_path: str = Field(..., description="Path to save the recording")
    duration: Optional[int] = Field(None, description="Recording duration in seconds")
    priority: JobPriority = Field(JobPriority.NORMAL, description="Job priority")


@router.post("/jobs/stream-recording", response_model=ProxyJobResponse)
async def create_stream_recording(
    request: StreamRecordingRequest,
    current_user: dict = Depends(get_current_user),
    queue_service = Depends(get_queue_service)
):
    """Create a recording from an active stream"""
    try:
        # Create job
        job = ProxyJob(
            job_id=f"recording_{request.stream_id}_{datetime.utcnow().timestamp()}",
            job_type="stream_recording",
            asset_id=request.asset_id,
            input_path="",  # Not needed
            parameters={
                "stream_id": request.stream_id,
                "output_path": request.output_path,
                "duration": request.duration
            },
            priority=request.priority,
            created_at=datetime.utcnow(),
            status=JobStatus.PENDING
        )
        
        # Submit job
        await queue_service.submit_job(job)
        
        logger.info(
            "stream_recording_job_created",
            job_id=job.job_id,
            stream_id=request.stream_id,
            duration=request.duration
        )
        
        return ProxyJobResponse(
            job_id=job.job_id,
            asset_id=request.asset_id,
            job_type="stream_recording",
            status="pending",
            message="Stream recording job created successfully"
        )
        
    except Exception as e:
        logger.error(
            "create_stream_recording_job_failed",
            error=str(e),
            stream_id=request.stream_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create stream recording job: {str(e)}"
        )


@router.get("/streams/{stream_id}/status")
async def get_stream_status(
    stream_id: str,
    current_user: dict = Depends(get_current_user),
    proxy_processor = Depends(get_proxy_processor)
):
    """Get status of a live stream"""
    try:
        status = await proxy_processor.live_streaming_service.get_stream_status(stream_id)
        return status
        
    except Exception as e:
        logger.error(
            "get_stream_status_failed",
            error=str(e),
            stream_id=stream_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get stream status: {str(e)}"
        )


@router.get("/streams/{stream_id}/statistics")
async def get_stream_statistics(
    stream_id: str,
    current_user: dict = Depends(get_current_user),
    proxy_processor = Depends(get_proxy_processor)
):
    """Get real-time statistics for a live stream"""
    try:
        stats = await proxy_processor.live_streaming_service.get_stream_statistics(stream_id)
        return stats
        
    except Exception as e:
        logger.error(
            "get_stream_statistics_failed",
            error=str(e),
            stream_id=stream_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get stream statistics: {str(e)}"
        )


@router.get("/capabilities/live-streaming")
async def get_live_streaming_capabilities(
    proxy_processor = Depends(get_proxy_processor)
):
    """Get system live streaming capabilities"""
    try:
        return proxy_processor.live_streaming_service.get_streaming_capabilities()
        
    except Exception as e:
        logger.error(
            "get_live_streaming_capabilities_failed",
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get live streaming capabilities: {str(e)}"
        )


# Remote Production Endpoints

class RemoteProductionCreateRequest(BaseModel):
    """Request model for creating remote production"""
    asset_id: str = Field(..., description="Asset ID for the production")
    production_name: str = Field(..., description="Production name")
    director_id: str = Field(..., description="Director user ID")
    configuration: Dict[str, Any] = Field({}, description="Production configuration")
    priority: JobPriority = Field(JobPriority.HIGH, description="Job priority")


@router.post("/jobs/remote-production-create", response_model=ProxyJobResponse)
async def create_remote_production(
    request: RemoteProductionCreateRequest,
    current_user: dict = Depends(get_current_user),
    queue_service = Depends(get_queue_service)
):
    """Create a new remote production session"""
    try:
        # Create job
        job = ProxyJob(
            job_id=f"prod_create_{request.asset_id}_{datetime.utcnow().timestamp()}",
            job_type="remote_production_create",
            asset_id=request.asset_id,
            input_path="",
            parameters={
                "production_name": request.production_name,
                "director_id": request.director_id,
                "configuration": request.configuration
            },
            priority=request.priority,
            created_at=datetime.utcnow(),
            status=JobStatus.PENDING
        )
        
        # Submit job
        await queue_service.submit_job(job)
        
        logger.info(
            "remote_production_create_job_created",
            job_id=job.job_id,
            asset_id=request.asset_id,
            production_name=request.production_name
        )
        
        return ProxyJobResponse(
            job_id=job.job_id,
            asset_id=request.asset_id,
            job_type="remote_production_create",
            status="pending",
            message="Remote production creation job created successfully"
        )
        
    except Exception as e:
        logger.error(
            "create_remote_production_job_failed",
            error=str(e),
            asset_id=request.asset_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create remote production job: {str(e)}"
        )


class RemoteParticipantAddRequest(BaseModel):
    """Request model for adding remote participant"""
    asset_id: str = Field(..., description="Asset ID")
    production_id: str = Field(..., description="Production ID")
    participant_id: str = Field(..., description="Participant ID")
    participant_name: str = Field(..., description="Participant name")
    role: str = Field("observer", description="Production role")
    capabilities: Dict[str, Any] = Field({}, description="Participant capabilities")
    priority: JobPriority = Field(JobPriority.HIGH, description="Job priority")


@router.post("/jobs/remote-participant-add", response_model=ProxyJobResponse)
async def add_remote_participant(
    request: RemoteParticipantAddRequest,
    current_user: dict = Depends(get_current_user),
    queue_service = Depends(get_queue_service)
):
    """Add participant to remote production"""
    try:
        # Validate role
        valid_roles = ["director", "producer", "camera_operator", "audio_operator", 
                      "graphics_operator", "switcher", "engineer", "talent", "observer"]
        if request.role not in valid_roles:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role. Must be one of: {valid_roles}"
            )
        
        # Create job
        job = ProxyJob(
            job_id=f"participant_{request.production_id}_{datetime.utcnow().timestamp()}",
            job_type="remote_participant_add",
            asset_id=request.asset_id,
            input_path="",
            parameters={
                "production_id": request.production_id,
                "participant_id": request.participant_id,
                "participant_name": request.participant_name,
                "role": request.role,
                "capabilities": request.capabilities
            },
            priority=request.priority,
            created_at=datetime.utcnow(),
            status=JobStatus.PENDING
        )
        
        # Submit job
        await queue_service.submit_job(job)
        
        logger.info(
            "remote_participant_add_job_created",
            job_id=job.job_id,
            production_id=request.production_id,
            participant_id=request.participant_id
        )
        
        return ProxyJobResponse(
            job_id=job.job_id,
            asset_id=request.asset_id,
            job_type="remote_participant_add",
            status="pending",
            message="Remote participant add job created successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "add_remote_participant_job_failed",
            error=str(e),
            production_id=request.production_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add remote participant job: {str(e)}"
        )


class RemoteSourceAddRequest(BaseModel):
    """Request model for adding remote source"""
    asset_id: str = Field(..., description="Asset ID")
    production_id: str = Field(..., description="Production ID")
    source_name: str = Field(..., description="Source name")
    source_type: str = Field("srt", description="Source type")
    participant_id: str = Field(..., description="Participant ID")
    connection_params: Dict[str, Any] = Field({}, description="Connection parameters")
    priority: JobPriority = Field(JobPriority.HIGH, description="Job priority")


@router.post("/jobs/remote-source-add", response_model=ProxyJobResponse)
async def add_remote_source(
    request: RemoteSourceAddRequest,
    current_user: dict = Depends(get_current_user),
    queue_service = Depends(get_queue_service)
):
    """Add remote source to production"""
    try:
        # Validate source type
        valid_types = ["camera", "screen_share", "mobile", "satellite", 
                      "bonded_cellular", "srt", "rtmp", "ndi", "webrtc"]
        if request.source_type not in valid_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid source type. Must be one of: {valid_types}"
            )
        
        # Create job
        job = ProxyJob(
            job_id=f"source_{request.production_id}_{datetime.utcnow().timestamp()}",
            job_type="remote_source_add",
            asset_id=request.asset_id,
            input_path="",
            parameters={
                "production_id": request.production_id,
                "source_name": request.source_name,
                "source_type": request.source_type,
                "participant_id": request.participant_id,
                "connection_params": request.connection_params
            },
            priority=request.priority,
            created_at=datetime.utcnow(),
            status=JobStatus.PENDING
        )
        
        # Submit job
        await queue_service.submit_job(job)
        
        logger.info(
            "remote_source_add_job_created",
            job_id=job.job_id,
            production_id=request.production_id,
            source_name=request.source_name
        )
        
        return ProxyJobResponse(
            job_id=job.job_id,
            asset_id=request.asset_id,
            job_type="remote_source_add",
            status="pending",
            message="Remote source add job created successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "add_remote_source_job_failed",
            error=str(e),
            production_id=request.production_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add remote source job: {str(e)}"
        )


class TallyUpdateRequest(BaseModel):
    """Request model for updating tally state"""
    asset_id: str = Field(..., description="Asset ID")
    production_id: str = Field(..., description="Production ID")
    source_id: str = Field(..., description="Source ID")
    tally_state: str = Field("off", description="Tally state (off, preview, program, next)")
    priority: JobPriority = Field(JobPriority.HIGH, description="Job priority")


@router.post("/jobs/tally-update", response_model=ProxyJobResponse)
async def update_tally_state(
    request: TallyUpdateRequest,
    current_user: dict = Depends(get_current_user),
    queue_service = Depends(get_queue_service)
):
    """Update tally light state for remote source"""
    try:
        # Validate tally state
        valid_states = ["off", "preview", "program", "next"]
        if request.tally_state not in valid_states:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid tally state. Must be one of: {valid_states}"
            )
        
        # Create job
        job = ProxyJob(
            job_id=f"tally_{request.source_id}_{datetime.utcnow().timestamp()}",
            job_type="tally_update",
            asset_id=request.asset_id,
            input_path="",
            parameters={
                "production_id": request.production_id,
                "source_id": request.source_id,
                "tally_state": request.tally_state
            },
            priority=request.priority,
            created_at=datetime.utcnow(),
            status=JobStatus.PENDING
        )
        
        # Submit job
        await queue_service.submit_job(job)
        
        logger.info(
            "tally_update_job_created",
            job_id=job.job_id,
            source_id=request.source_id,
            tally_state=request.tally_state
        )
        
        return ProxyJobResponse(
            job_id=job.job_id,
            asset_id=request.asset_id,
            job_type="tally_update",
            status="pending",
            message="Tally update job created successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "update_tally_state_job_failed",
            error=str(e),
            source_id=request.source_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update tally state job: {str(e)}"
        )


class ReturnFeedConfigRequest(BaseModel):
    """Request model for configuring return feed"""
    asset_id: str = Field(..., description="Asset ID")
    production_id: str = Field(..., description="Production ID")
    participant_id: str = Field(..., description="Participant ID")
    feed_type: str = Field("program_clean", description="Feed type")
    custom_sources: Optional[List[str]] = Field(None, description="Custom source IDs")
    priority: JobPriority = Field(JobPriority.NORMAL, description="Job priority")


@router.post("/jobs/return-feed-config", response_model=ProxyJobResponse)
async def configure_return_feed(
    request: ReturnFeedConfigRequest,
    current_user: dict = Depends(get_current_user),
    queue_service = Depends(get_queue_service)
):
    """Configure return video feed for participant"""
    try:
        # Validate feed type
        valid_types = ["program_clean", "program_dirty", "multiview", 
                      "preview", "custom", "confidence"]
        if request.feed_type not in valid_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid feed type. Must be one of: {valid_types}"
            )
        
        # Create job
        job = ProxyJob(
            job_id=f"feed_{request.participant_id}_{datetime.utcnow().timestamp()}",
            job_type="return_feed_config",
            asset_id=request.asset_id,
            input_path="",
            parameters={
                "production_id": request.production_id,
                "participant_id": request.participant_id,
                "feed_type": request.feed_type,
                "custom_sources": request.custom_sources
            },
            priority=request.priority,
            created_at=datetime.utcnow(),
            status=JobStatus.PENDING
        )
        
        # Submit job
        await queue_service.submit_job(job)
        
        logger.info(
            "return_feed_config_job_created",
            job_id=job.job_id,
            participant_id=request.participant_id,
            feed_type=request.feed_type
        )
        
        return ProxyJobResponse(
            job_id=job.job_id,
            asset_id=request.asset_id,
            job_type="return_feed_config",
            status="pending",
            message="Return feed configuration job created successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "configure_return_feed_job_failed",
            error=str(e),
            participant_id=request.participant_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to configure return feed job: {str(e)}"
        )


@router.get("/productions/{production_id}/metrics")
async def get_production_metrics(
    production_id: str,
    current_user: dict = Depends(get_current_user),
    proxy_processor = Depends(get_proxy_processor)
):
    """Get metrics for a remote production"""
    try:
        metrics = await proxy_processor.remote_production_service.get_production_metrics(production_id)
        return metrics
        
    except Exception as e:
        logger.error(
            "get_production_metrics_failed",
            error=str(e),
            production_id=production_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get production metrics: {str(e)}"
        )


@router.get("/capabilities/remote-production")
async def get_remote_production_capabilities(
    proxy_processor = Depends(get_proxy_processor)
):
    """Get system remote production capabilities"""
    try:
        return proxy_processor.remote_production_service.get_remote_production_capabilities()
        
    except Exception as e:
        logger.error(
            "get_remote_production_capabilities_failed",
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get remote production capabilities: {str(e)}"
        )


# Cloud Switching endpoints
class CloudSwitchingCreateRequest(BaseModel):
    """Request model for creating cloud switching session"""
    asset_id: str = Field(..., description="Asset ID for the switching session")
    session_name: str = Field(..., description="Session name")
    configuration: Dict[str, Any] = Field({}, description="Switching configuration")
    priority: str = Field("normal", pattern="^(low|normal|high)$")
    
    class Config:
        schema_extra = {
            "example": {
                "asset_id": "asset123",
                "session_name": "Live Event 2025",
                "configuration": {
                    "mix_effects": {
                        "enable_main": True,
                        "enable_sub": True,
                        "enable_aux": True
                    },
                    "default_inputs": [
                        {
                            "id": "camera1",
                            "name": "Main Camera",
                            "type": "srt",
                            "url": "srt://0.0.0.0:9000?mode=listener"
                        }
                    ]
                },
                "priority": "high"
            }
        }


@router.post("/cloud-switching/create")
async def create_cloud_switching_session(
    request: CloudSwitchingCreateRequest,
    current_user: dict = Depends(get_current_user),
    proxy_processor = Depends(get_proxy_processor)
):
    """Create a new cloud switching session"""
    try:
        job_params = {
            "session_name": request.session_name,
            "configuration": request.configuration
        }
        
        queue_service = await get_queue_service()
        job_id = await queue_service.submit_job(
            asset_id=request.asset_id,
            input_path="",
            job_type="cloud_switching_create",
            parameters=job_params,
            priority=request.priority,
            metadata={
                "submitted_by": current_user["user_id"],
                "submitted_at": datetime.utcnow().isoformat()
            }
        )
        
        logger.info(
            "cloud_switching_create_job_submitted",
            job_id=job_id,
            asset_id=request.asset_id
        )
        
        return ProxyJobResponse(
            job_id=job_id,
            asset_id=request.asset_id,
            job_type="cloud_switching_create",
            status="queued",
            message="Cloud switching session creation job submitted"
        )
        
    except Exception as e:
        logger.error(
            "create_cloud_switching_session_failed",
            error=str(e),
            asset_id=request.asset_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create cloud switching session: {str(e)}"
        )


class SwitchingInputAddRequest(BaseModel):
    """Request model for adding input to switching session"""
    asset_id: str = Field(..., description="Asset ID")
    session_id: str = Field(..., description="Switching session ID")
    input_name: str = Field(..., description="Input name")
    input_type: str = Field(..., description="Input type")
    input_url: str = Field("", description="Input URL or path")
    settings: Dict[str, Any] = Field({}, description="Input-specific settings")
    priority: str = Field("normal", pattern="^(low|normal|high)$")
    
    class Config:
        schema_extra = {
            "example": {
                "asset_id": "asset123",
                "session_id": "session456",
                "input_name": "Camera 2",
                "input_type": "rtmp",
                "input_url": "rtmp://localhost:1935/live/camera2",
                "settings": {},
                "priority": "normal"
            }
        }


@router.post("/cloud-switching/add-input")
async def add_switching_input(
    request: SwitchingInputAddRequest,
    current_user: dict = Depends(get_current_user),
    proxy_processor = Depends(get_proxy_processor)
):
    """Add an input to a cloud switching session"""
    try:
        job_params = {
            "session_id": request.session_id,
            "input_name": request.input_name,
            "input_type": request.input_type,
            "input_url": request.input_url,
            "settings": request.settings
        }
        
        queue_service = await get_queue_service()
        job_id = await queue_service.submit_job(
            asset_id=request.asset_id,
            input_path="",
            job_type="switching_input_add",
            parameters=job_params,
            priority=request.priority,
            metadata={
                "submitted_by": current_user["user_id"],
                "submitted_at": datetime.utcnow().isoformat()
            }
        )
        
        logger.info(
            "switching_input_add_job_submitted",
            job_id=job_id,
            session_id=request.session_id
        )
        
        return ProxyJobResponse(
            job_id=job_id,
            asset_id=request.asset_id,
            job_type="switching_input_add",
            status="queued",
            message="Switching input add job submitted"
        )
        
    except Exception as e:
        logger.error(
            "add_switching_input_failed",
            error=str(e),
            session_id=request.session_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add switching input: {str(e)}"
        )


class SwitchingExecuteRequest(BaseModel):
    """Request model for executing a switch"""
    asset_id: str = Field(..., description="Asset ID")
    session_id: str = Field(..., description="Switching session ID")
    input_id: str = Field(..., description="Input to switch to")
    mix_effect: str = Field("main", description="Mix effect bus")
    transition_type: Optional[str] = Field(None, description="Transition type")
    transition_duration_ms: int = Field(0, description="Transition duration in milliseconds")
    priority: str = Field("high", pattern="^(low|normal|high)$")
    
    class Config:
        schema_extra = {
            "example": {
                "asset_id": "asset123",
                "session_id": "session456",
                "input_id": "camera2",
                "mix_effect": "main",
                "transition_type": "dissolve",
                "transition_duration_ms": 1000,
                "priority": "high"
            }
        }


@router.post("/cloud-switching/switch")
async def execute_switch(
    request: SwitchingExecuteRequest,
    current_user: dict = Depends(get_current_user),
    proxy_processor = Depends(get_proxy_processor)
):
    """Execute a switch in a cloud switching session"""
    try:
        job_params = {
            "session_id": request.session_id,
            "input_id": request.input_id,
            "mix_effect": request.mix_effect,
            "transition_type": request.transition_type,
            "transition_duration_ms": request.transition_duration_ms
        }
        
        queue_service = await get_queue_service()
        job_id = await queue_service.submit_job(
            asset_id=request.asset_id,
            input_path="",
            job_type="switching_switch",
            parameters=job_params,
            priority=request.priority,
            metadata={
                "submitted_by": current_user["user_id"],
                "submitted_at": datetime.utcnow().isoformat()
            }
        )
        
        logger.info(
            "switching_execute_job_submitted",
            job_id=job_id,
            session_id=request.session_id
        )
        
        return ProxyJobResponse(
            job_id=job_id,
            asset_id=request.asset_id,
            job_type="switching_switch",
            status="queued",
            message="Switching execute job submitted"
        )
        
    except Exception as e:
        logger.error(
            "execute_switch_failed",
            error=str(e),
            session_id=request.session_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute switch: {str(e)}"
        )


class SwitchingOutputConfigRequest(BaseModel):
    """Request model for configuring switching output"""
    asset_id: str = Field(..., description="Asset ID")
    session_id: str = Field(..., description="Switching session ID")
    output_format: str = Field(..., description="Output format")
    destination: str = Field(..., description="Output destination URL/path")
    settings: Dict[str, Any] = Field({}, description="Output-specific settings")
    priority: str = Field("normal", pattern="^(low|normal|high)$")
    
    class Config:
        schema_extra = {
            "example": {
                "asset_id": "asset123",
                "session_id": "session456",
                "output_format": "hls",
                "destination": "http://localhost:8080/live/output",
                "settings": {
                    "bitrate": "5000k",
                    "resolution": "1920x1080",
                    "framerate": 30
                },
                "priority": "normal"
            }
        }


@router.post("/cloud-switching/configure-output")
async def configure_switching_output(
    request: SwitchingOutputConfigRequest,
    current_user: dict = Depends(get_current_user),
    proxy_processor = Depends(get_proxy_processor)
):
    """Configure output for a cloud switching session"""
    try:
        job_params = {
            "session_id": request.session_id,
            "output_format": request.output_format,
            "destination": request.destination,
            "settings": request.settings
        }
        
        queue_service = await get_queue_service()
        job_id = await queue_service.submit_job(
            asset_id=request.asset_id,
            input_path="",
            job_type="switching_output_config",
            parameters=job_params,
            priority=request.priority,
            metadata={
                "submitted_by": current_user["user_id"],
                "submitted_at": datetime.utcnow().isoformat()
            }
        )
        
        logger.info(
            "switching_output_config_job_submitted",
            job_id=job_id,
            session_id=request.session_id
        )
        
        return ProxyJobResponse(
            job_id=job_id,
            asset_id=request.asset_id,
            job_type="switching_output_config",
            status="queued",
            message="Switching output configuration job submitted"
        )
        
    except Exception as e:
        logger.error(
            "configure_switching_output_failed",
            error=str(e),
            session_id=request.session_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to configure switching output: {str(e)}"
        )


@router.get("/cloud-switching/{session_id}/metrics")
async def get_switching_metrics(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    proxy_processor = Depends(get_proxy_processor)
):
    """Get metrics for a cloud switching session"""
    try:
        metrics = await proxy_processor.cloud_switching_service.get_session_metrics(session_id)
        return metrics
        
    except Exception as e:
        logger.error(
            "get_switching_metrics_failed",
            error=str(e),
            session_id=session_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get switching metrics: {str(e)}"
        )


@router.get("/capabilities/cloud-switching")
async def get_cloud_switching_capabilities(
    proxy_processor = Depends(get_proxy_processor)
):
    """Get system cloud switching capabilities"""
    try:
        return proxy_processor.cloud_switching_service.get_cloud_switching_capabilities()
        
    except Exception as e:
        logger.error(
            "get_cloud_switching_capabilities_failed",
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get cloud switching capabilities: {str(e)}"
        )


# Virtual Studio endpoints
class VirtualStudioCreateRequest(BaseModel):
    """Request model for creating virtual studio session"""
    asset_id: str = Field(..., description="Asset ID for the studio session")
    studio_name: str = Field(..., description="Studio name")
    configuration: Dict[str, Any] = Field({}, description="Studio configuration")
    priority: str = Field("normal", pattern="^(low|normal|high)$")
    
    class Config:
        schema_extra = {
            "example": {
                "asset_id": "asset123",
                "studio_name": "Virtual Studio 1",
                "configuration": {
                    "resolution": "1920x1080",
                    "framerate": 30,
                    "chroma_key": {
                        "method": "green_screen",
                        "tolerance": 0.2
                    }
                },
                "priority": "normal"
            }
        }


@router.post("/virtual-studio/create")
async def create_virtual_studio(
    request: VirtualStudioCreateRequest,
    current_user: dict = Depends(get_current_user),
    proxy_processor = Depends(get_proxy_processor)
):
    """Create a new virtual studio session"""
    try:
        job_params = {
            "studio_name": request.studio_name,
            "configuration": request.configuration
        }
        
        queue_service = await get_queue_service()
        job_id = await queue_service.submit_job(
            asset_id=request.asset_id,
            input_path="",
            job_type="virtual_studio_create",
            parameters=job_params,
            priority=request.priority,
            metadata={
                "submitted_by": current_user["user_id"],
                "submitted_at": datetime.utcnow().isoformat()
            }
        )
        
        logger.info(
            "virtual_studio_create_job_submitted",
            job_id=job_id,
            asset_id=request.asset_id
        )
        
        return ProxyJobResponse(
            job_id=job_id,
            asset_id=request.asset_id,
            job_type="virtual_studio_create",
            status="queued",
            message="Virtual studio creation job submitted"
        )
        
    except Exception as e:
        logger.error(
            "create_virtual_studio_failed",
            error=str(e),
            asset_id=request.asset_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create virtual studio: {str(e)}"
        )


class VirtualStudioChromaConfigRequest(BaseModel):
    """Request model for configuring chroma key"""
    asset_id: str = Field(..., description="Asset ID")
    studio_id: str = Field(..., description="Studio session ID")
    method: str = Field(..., description="Chroma key method")
    settings: Dict[str, Any] = Field({}, description="Chroma key settings")
    priority: str = Field("normal", pattern="^(low|normal|high)$")
    
    class Config:
        schema_extra = {
            "example": {
                "asset_id": "asset123",
                "studio_id": "studio456",
                "method": "green_screen",
                "settings": {
                    "tolerance": 0.2,
                    "edge_softness": 0.1,
                    "spill_suppression": 0.3
                },
                "priority": "normal"
            }
        }


@router.post("/virtual-studio/configure-chroma")
async def configure_virtual_studio_chroma(
    request: VirtualStudioChromaConfigRequest,
    current_user: dict = Depends(get_current_user),
    proxy_processor = Depends(get_proxy_processor)
):
    """Configure chroma key for virtual studio"""
    try:
        job_params = {
            "studio_id": request.studio_id,
            "method": request.method,
            "settings": request.settings
        }
        
        queue_service = await get_queue_service()
        job_id = await queue_service.submit_job(
            asset_id=request.asset_id,
            input_path="",
            job_type="virtual_studio_chroma_config",
            parameters=job_params,
            priority=request.priority,
            metadata={
                "submitted_by": current_user["user_id"],
                "submitted_at": datetime.utcnow().isoformat()
            }
        )
        
        logger.info(
            "virtual_studio_chroma_config_job_submitted",
            job_id=job_id,
            studio_id=request.studio_id
        )
        
        return ProxyJobResponse(
            job_id=job_id,
            asset_id=request.asset_id,
            job_type="virtual_studio_chroma_config",
            status="queued",
            message="Virtual studio chroma configuration job submitted"
        )
        
    except Exception as e:
        logger.error(
            "configure_virtual_studio_chroma_failed",
            error=str(e),
            studio_id=request.studio_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to configure virtual studio chroma: {str(e)}"
        )


class VirtualStudioSetLoadRequest(BaseModel):
    """Request model for loading virtual set"""
    asset_id: str = Field(..., description="Asset ID")
    studio_id: str = Field(..., description="Studio session ID")
    set_type: str = Field(..., description="Virtual set type")
    set_data: Dict[str, Any] = Field({}, description="Set configuration and assets")
    priority: str = Field("normal", pattern="^(low|normal|high)$")
    
    class Config:
        schema_extra = {
            "example": {
                "asset_id": "asset123",
                "studio_id": "studio456",
                "set_type": "static_2d",
                "set_data": {
                    "background_image": "/assets/sets/newsroom.jpg",
                    "depth_map": "/assets/sets/newsroom_depth.png"
                },
                "priority": "normal"
            }
        }


@router.post("/virtual-studio/load-set")
async def load_virtual_set(
    request: VirtualStudioSetLoadRequest,
    current_user: dict = Depends(get_current_user),
    proxy_processor = Depends(get_proxy_processor)
):
    """Load a virtual set into the studio"""
    try:
        job_params = {
            "studio_id": request.studio_id,
            "set_type": request.set_type,
            "set_data": request.set_data
        }
        
        queue_service = await get_queue_service()
        job_id = await queue_service.submit_job(
            asset_id=request.asset_id,
            input_path="",
            job_type="virtual_studio_set_load",
            parameters=job_params,
            priority=request.priority,
            metadata={
                "submitted_by": current_user["user_id"],
                "submitted_at": datetime.utcnow().isoformat()
            }
        )
        
        logger.info(
            "virtual_studio_set_load_job_submitted",
            job_id=job_id,
            studio_id=request.studio_id
        )
        
        return ProxyJobResponse(
            job_id=job_id,
            asset_id=request.asset_id,
            job_type="virtual_studio_set_load",
            status="queued",
            message="Virtual studio set load job submitted"
        )
        
    except Exception as e:
        logger.error(
            "load_virtual_set_failed",
            error=str(e),
            studio_id=request.studio_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load virtual set: {str(e)}"
        )


class VirtualStudioARAddRequest(BaseModel):
    """Request model for adding AR element"""
    asset_id: str = Field(..., description="Asset ID")
    studio_id: str = Field(..., description="Studio session ID")
    element_type: str = Field(..., description="AR element type")
    properties: Dict[str, Any] = Field({}, description="Element properties")
    priority: str = Field("normal", pattern="^(low|normal|high)$")
    
    class Config:
        schema_extra = {
            "example": {
                "asset_id": "asset123",
                "studio_id": "studio456",
                "element_type": "text",
                "properties": {
                    "text": "BREAKING NEWS",
                    "position": [0, -0.5, 0],
                    "font": "Arial",
                    "size": 72,
                    "color": [255, 0, 0]
                },
                "priority": "normal"
            }
        }


@router.post("/virtual-studio/add-ar-element")
async def add_ar_element(
    request: VirtualStudioARAddRequest,
    current_user: dict = Depends(get_current_user),
    proxy_processor = Depends(get_proxy_processor)
):
    """Add an AR element to virtual studio"""
    try:
        job_params = {
            "studio_id": request.studio_id,
            "element_type": request.element_type,
            "properties": request.properties
        }
        
        queue_service = await get_queue_service()
        job_id = await queue_service.submit_job(
            asset_id=request.asset_id,
            input_path="",
            job_type="virtual_studio_ar_add",
            parameters=job_params,
            priority=request.priority,
            metadata={
                "submitted_by": current_user["user_id"],
                "submitted_at": datetime.utcnow().isoformat()
            }
        )
        
        logger.info(
            "virtual_studio_ar_add_job_submitted",
            job_id=job_id,
            studio_id=request.studio_id
        )
        
        return ProxyJobResponse(
            job_id=job_id,
            asset_id=request.asset_id,
            job_type="virtual_studio_ar_add",
            status="queued",
            message="Virtual studio AR element add job submitted"
        )
        
    except Exception as e:
        logger.error(
            "add_ar_element_failed",
            error=str(e),
            studio_id=request.studio_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add AR element: {str(e)}"
        )


@router.get("/virtual-studio/{studio_id}/metrics")
async def get_virtual_studio_metrics(
    studio_id: str,
    current_user: dict = Depends(get_current_user),
    proxy_processor = Depends(get_proxy_processor)
):
    """Get metrics for a virtual studio session"""
    try:
        metrics = await proxy_processor.virtual_studio_service.get_studio_metrics(studio_id)
        return metrics
        
    except Exception as e:
        logger.error(
            "get_virtual_studio_metrics_failed",
            error=str(e),
            studio_id=studio_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get virtual studio metrics: {str(e)}"
        )


@router.get("/capabilities/virtual-studio")
async def get_virtual_studio_capabilities(
    proxy_processor = Depends(get_proxy_processor)
):
    """Get system virtual studio capabilities"""
    try:
        return proxy_processor.virtual_studio_service.get_virtual_studio_capabilities()
        
    except Exception as e:
        logger.error(
            "get_virtual_studio_capabilities_failed",
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get virtual studio capabilities: {str(e)}"
        )


# Live Graphics endpoints
class LiveGraphicsCreateRequest(BaseModel):
    """Request model for creating live graphics session"""
    asset_id: str = Field(..., description="Asset ID for the graphics session")
    session_name: str = Field(..., description="Graphics session name")
    configuration: Dict[str, Any] = Field({}, description="Graphics configuration")
    priority: str = Field("normal", pattern="^(low|normal|high)$")
    
    class Config:
        schema_extra = {
            "example": {
                "asset_id": "asset123",
                "session_name": "News Graphics",
                "configuration": {
                    "resolution": "1920x1080",
                    "framerate": 30,
                    "format": "rgba",
                    "engine": "html_css"
                },
                "priority": "normal"
            }
        }


class LiveGraphicsTemplateLoadRequest(BaseModel):
    """Request model for loading graphics template"""
    asset_id: str = Field(..., description="Asset ID")
    session_id: str = Field(..., description="Graphics session ID")
    template_type: str = Field(..., description="Template type (lower_third, ticker, etc)")
    template_data: Dict[str, Any] = Field({}, description="Template configuration and assets")
    priority: str = Field("normal", pattern="^(low|normal|high)$")
    
    class Config:
        schema_extra = {
            "example": {
                "asset_id": "asset123",
                "session_id": "session456",
                "template_type": "lower_third",
                "template_data": {
                    "fields": {
                        "title": {"default": "Breaking News", "editable": True},
                        "subtitle": {"default": "Live from scene", "editable": True}
                    },
                    "styles": {
                        "background": "rgba(0,0,0,0.8)",
                        "title_color": "#FFFFFF",
                        "subtitle_color": "#CCCCCC"
                    }
                },
                "priority": "normal"
            }
        }


class LiveGraphicsShowRequest(BaseModel):
    """Request model for showing/hiding graphics"""
    asset_id: str = Field(..., description="Asset ID")
    session_id: str = Field(..., description="Graphics session ID")
    graphic_id: str = Field(..., description="Graphic ID to show/hide")
    action: str = Field("show", pattern="^(show|hide)$", description="Show or hide action")
    animation: Optional[str] = Field(None, description="Animation type")
    duration_ms: int = Field(500, ge=0, le=5000, description="Animation duration")
    priority: str = Field("normal", pattern="^(low|normal|high)$")
    
    class Config:
        schema_extra = {
            "example": {
                "asset_id": "asset123",
                "session_id": "session456",
                "graphic_id": "graphic789",
                "action": "show",
                "animation": "fade",
                "duration_ms": 500,
                "priority": "normal"
            }
        }


class LiveGraphicsDataUpdateRequest(BaseModel):
    """Request model for updating graphic data"""
    asset_id: str = Field(..., description="Asset ID")
    session_id: str = Field(..., description="Graphics session ID")
    graphic_id: str = Field(..., description="Graphic ID to update")
    data: Dict[str, Any] = Field(..., description="Data to update")
    priority: str = Field("normal", pattern="^(low|normal|high)$")
    
    class Config:
        schema_extra = {
            "example": {
                "asset_id": "asset123",
                "session_id": "session456",
                "graphic_id": "graphic789",
                "data": {
                    "title": "Weather Update",
                    "subtitle": "Temperature rising to 85°F"
                },
                "priority": "normal"
            }
        }


class LiveGraphicsPlaylistRequest(BaseModel):
    """Request model for creating graphics playlist"""
    asset_id: str = Field(..., description="Asset ID")
    session_id: str = Field(..., description="Graphics session ID")
    items: List[Dict[str, Any]] = Field(..., description="Playlist items")
    priority: str = Field("normal", pattern="^(low|normal|high)$")
    
    class Config:
        schema_extra = {
            "example": {
                "asset_id": "asset123",
                "session_id": "session456",
                "items": [
                    {
                        "graphic_id": "graphic1",
                        "duration": 5000,
                        "data": {"title": "Item 1"}
                    },
                    {
                        "template_id": "template1",
                        "duration": 3000,
                        "data": {"title": "Item 2"}
                    }
                ],
                "priority": "normal"
            }
        }


@router.post("/live-graphics/create")
async def create_live_graphics_session(
    request: LiveGraphicsCreateRequest,
    current_user: dict = Depends(get_current_user),
    proxy_processor = Depends(get_proxy_processor)
):
    """Create a new live graphics session"""
    try:
        job_params = {
            "session_name": request.session_name,
            "configuration": request.configuration
        }
        
        queue_service = await get_queue_service()
        job_id = await queue_service.submit_job(
            asset_id=request.asset_id,
            input_path="",
            job_type="live_graphics_create",
            parameters=job_params,
            priority=request.priority,
            metadata={
                "submitted_by": current_user["user_id"],
                "submitted_at": datetime.utcnow().isoformat()
            }
        )
        
        logger.info(
            "live_graphics_create_job_submitted",
            job_id=job_id,
            asset_id=request.asset_id
        )
        
        return {
            "job_id": job_id,
            "asset_id": request.asset_id,
            "job_type": "live_graphics_create",
            "status": "submitted",
            "message": "Live graphics session creation job submitted successfully"
        }
        
    except Exception as e:
        logger.error(
            "live_graphics_create_submission_failed",
            error=str(e),
            asset_id=request.asset_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit live graphics session creation job: {str(e)}"
        )


@router.post("/live-graphics/load-template")
async def load_graphics_template(
    request: LiveGraphicsTemplateLoadRequest,
    current_user: dict = Depends(get_current_user),
    proxy_processor = Depends(get_proxy_processor)
):
    """Load a graphics template into session"""
    try:
        job_params = {
            "session_id": request.session_id,
            "template_type": request.template_type,
            "template_data": request.template_data
        }
        
        queue_service = await get_queue_service()
        job_id = await queue_service.submit_job(
            asset_id=request.asset_id,
            input_path="",
            job_type="live_graphics_template_load",
            parameters=job_params,
            priority=request.priority,
            metadata={
                "submitted_by": current_user["user_id"],
                "submitted_at": datetime.utcnow().isoformat()
            }
        )
        
        logger.info(
            "live_graphics_template_load_job_submitted",
            job_id=job_id,
            session_id=request.session_id
        )
        
        return {
            "job_id": job_id,
            "asset_id": request.asset_id,
            "job_type": "live_graphics_template_load",
            "status": "submitted",
            "message": "Graphics template load job submitted successfully"
        }
        
    except Exception as e:
        logger.error(
            "live_graphics_template_load_submission_failed",
            error=str(e),
            session_id=request.session_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit graphics template load job: {str(e)}"
        )


@router.post("/live-graphics/show")
async def show_hide_graphic(
    request: LiveGraphicsShowRequest,
    current_user: dict = Depends(get_current_user),
    proxy_processor = Depends(get_proxy_processor)
):
    """Show or hide a graphic with animation"""
    try:
        job_params = {
            "session_id": request.session_id,
            "graphic_id": request.graphic_id,
            "action": request.action,
            "animation": request.animation,
            "duration_ms": request.duration_ms
        }
        
        queue_service = await get_queue_service()
        job_id = await queue_service.submit_job(
            asset_id=request.asset_id,
            input_path="",
            job_type="live_graphics_show",
            parameters=job_params,
            priority=request.priority,
            metadata={
                "submitted_by": current_user["user_id"],
                "submitted_at": datetime.utcnow().isoformat()
            }
        )
        
        logger.info(
            f"live_graphics_{request.action}_job_submitted",
            job_id=job_id,
            session_id=request.session_id,
            graphic_id=request.graphic_id
        )
        
        return {
            "job_id": job_id,
            "asset_id": request.asset_id,
            "job_type": "live_graphics_show",
            "status": "submitted",
            "message": f"Graphics {request.action} job submitted successfully"
        }
        
    except Exception as e:
        logger.error(
            f"live_graphics_{request.action}_submission_failed",
            error=str(e),
            session_id=request.session_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit graphics {request.action} job: {str(e)}"
        )


@router.post("/live-graphics/update-data")
async def update_graphic_data(
    request: LiveGraphicsDataUpdateRequest,
    current_user: dict = Depends(get_current_user),
    proxy_processor = Depends(get_proxy_processor)
):
    """Update graphic data dynamically"""
    try:
        job_params = {
            "session_id": request.session_id,
            "graphic_id": request.graphic_id,
            "data": request.data
        }
        
        queue_service = await get_queue_service()
        job_id = await queue_service.submit_job(
            asset_id=request.asset_id,
            input_path="",
            job_type="live_graphics_data_update",
            parameters=job_params,
            priority=request.priority,
            metadata={
                "submitted_by": current_user["user_id"],
                "submitted_at": datetime.utcnow().isoformat()
            }
        )
        
        logger.info(
            "live_graphics_data_update_job_submitted",
            job_id=job_id,
            session_id=request.session_id,
            graphic_id=request.graphic_id
        )
        
        return {
            "job_id": job_id,
            "asset_id": request.asset_id,
            "job_type": "live_graphics_data_update",
            "status": "submitted",
            "message": "Graphics data update job submitted successfully"
        }
        
    except Exception as e:
        logger.error(
            "live_graphics_data_update_submission_failed",
            error=str(e),
            session_id=request.session_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit graphics data update job: {str(e)}"
        )


@router.post("/live-graphics/create-playlist")
async def create_graphics_playlist(
    request: LiveGraphicsPlaylistRequest,
    current_user: dict = Depends(get_current_user),
    proxy_processor = Depends(get_proxy_processor)
):
    """Create a graphics playlist"""
    try:
        job_params = {
            "session_id": request.session_id,
            "items": request.items
        }
        
        queue_service = await get_queue_service()
        job_id = await queue_service.submit_job(
            asset_id=request.asset_id,
            input_path="",
            job_type="live_graphics_playlist_create",
            parameters=job_params,
            priority=request.priority,
            metadata={
                "submitted_by": current_user["user_id"],
                "submitted_at": datetime.utcnow().isoformat()
            }
        )
        
        logger.info(
            "live_graphics_playlist_create_job_submitted",
            job_id=job_id,
            session_id=request.session_id,
            item_count=len(request.items)
        )
        
        return {
            "job_id": job_id,
            "asset_id": request.asset_id,
            "job_type": "live_graphics_playlist_create",
            "status": "submitted",
            "message": "Graphics playlist creation job submitted successfully"
        }
        
    except Exception as e:
        logger.error(
            "live_graphics_playlist_create_submission_failed",
            error=str(e),
            session_id=request.session_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit graphics playlist creation job: {str(e)}"
        )


@router.get("/live-graphics/{session_id}/metrics")
async def get_live_graphics_metrics(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    proxy_processor = Depends(get_proxy_processor)
):
    """Get metrics for a live graphics session"""
    try:
        metrics = await proxy_processor.live_graphics_service.get_session_metrics(session_id)
        return metrics
        
    except Exception as e:
        logger.error(
            "get_live_graphics_metrics_failed",
            error=str(e),
            session_id=session_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get live graphics metrics: {str(e)}"
        )


@router.get("/capabilities/live-graphics")
async def get_live_graphics_capabilities(
    proxy_processor = Depends(get_proxy_processor)
):
    """Get system live graphics capabilities"""
    try:
        return proxy_processor.live_graphics_service.get_live_graphics_capabilities()
        
    except Exception as e:
        logger.error(
            "get_live_graphics_capabilities_failed",
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get live graphics capabilities: {str(e)}"
        )