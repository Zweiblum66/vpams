"""
Proxy Processor - Main processing logic for proxy generation
"""

import os
import tempfile
import uuid
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime

from .ffmpeg_service import get_ffmpeg_service, FFmpegService
from .storage_service import get_storage_service, StorageService
from .queue_service import ProxyJob, JobStatus
from .image_processing_service import get_image_processing_service, ImageProcessingService, CropMode
from .ultra_hd_service import get_ultra_hd_service, UltraHDService, UltraHDCodec, UltraHDResolution
from .hdr_processing_service import get_hdr_processing_service, HDRProcessingService, HDRStandard, ToneMappingAlgorithm
from .spherical_video_service import get_spherical_video_service, SphericalVideoService, SphericalProjection, SphericalStereoMode, VRHeadset
from .vr_content_service import VRContentService, VRPlatform, VRContentType, VRRenderMode
from .spatial_audio_service import SpatialAudioService, SpatialAudioFormat, AmbisonicOrder, HRTFProfile, RoomAcoustics
from .live_streaming_service import LiveStreamingService, StreamingProtocol, StreamQuality, StreamCodec, StreamAudioCodec, StreamLatency, DVRMode
from .remote_production_service import RemoteProductionService, RemoteProductionRole, CommunicationChannel, RemoteSourceType, TallyState, ReturnFeedType
from .cloud_switching_service import CloudSwitchingService, SwitchingMode, InputType, OutputFormat, MixEffectType, AudioMixMode, MacroType
from .virtual_studio_service import VirtualStudioService, ChromaKeyMethod, VirtualSetType, TrackingMethod, LightingMode, ARElementType, RenderQuality
from .live_graphics_service import LiveGraphicsService, GraphicsType, AnimationType, DataSourceType, TemplateEngine, PlayoutMode, GraphicsLayer
from ..core.config import settings
from ..core.exceptions import ProxyGenerationError, InvalidMediaError
from ..core.logging import get_logger

logger = get_logger(__name__)


class ProxyProcessor:
    """Main processor for proxy generation jobs"""
    
    def __init__(self):
        self.ffmpeg_service: Optional[FFmpegService] = None
        self.storage_service: Optional[StorageService] = None
        self.image_service: Optional[ImageProcessingService] = None
        self.ultra_hd_service: Optional[UltraHDService] = None
        self.hdr_service: Optional[HDRProcessingService] = None
        self.spherical_service: Optional[SphericalVideoService] = None
        self.vr_content_service: Optional[VRContentService] = None
        self.spatial_audio_service: Optional[SpatialAudioService] = None
        self.live_streaming_service: Optional[LiveStreamingService] = None
        self.remote_production_service: Optional[RemoteProductionService] = None
        self.cloud_switching_service: Optional[CloudSwitchingService] = None
        self.virtual_studio_service: Optional[VirtualStudioService] = None
        self.live_graphics_service: Optional[LiveGraphicsService] = None
        self._temp_dir = None
    
    async def initialize(self):
        """Initialize processor services"""
        self.ffmpeg_service = await get_ffmpeg_service()
        self.storage_service = await get_storage_service()
        self.image_service = await get_image_processing_service()
        self.ultra_hd_service = await get_ultra_hd_service()
        self.hdr_service = await get_hdr_processing_service()
        self.spherical_service = await get_spherical_video_service()
        self.vr_content_service = VRContentService()
        self.spatial_audio_service = SpatialAudioService()
        self.live_streaming_service = LiveStreamingService()
        self.remote_production_service = RemoteProductionService()
        self.cloud_switching_service = CloudSwitchingService()
        self.virtual_studio_service = VirtualStudioService()
        self.live_graphics_service = LiveGraphicsService()
        
        # Create temp directory for processing
        self._temp_dir = tempfile.mkdtemp(prefix="mams_proxy_")
        
        logger.info("proxy_processor_initialized", temp_dir=self._temp_dir)
    
    async def cleanup(self):
        """Cleanup processor resources"""
        if self._temp_dir and os.path.exists(self._temp_dir):
            import shutil
            shutil.rmtree(self._temp_dir)
        
        logger.info("proxy_processor_cleaned_up")
    
    async def process_job(self, job: ProxyJob) -> Dict[str, Any]:
        """Process a proxy generation job"""
        try:
            logger.info(
                "processing_job",
                job_id=job.job_id,
                job_type=job.job_type,
                asset_id=job.asset_id
            )
            
            # Route to appropriate processor
            if job.job_type == "video_proxy":
                return await self._process_video_proxy(job)
            elif job.job_type == "audio_proxy":
                return await self._process_audio_proxy(job)
            elif job.job_type == "thumbnail":
                return await self._process_thumbnail(job)
            elif job.job_type == "thumbnail_batch":
                return await self._process_thumbnail_batch(job)
            elif job.job_type == "thumbnail_single":
                return await self._process_thumbnail_single(job)
            elif job.job_type == "contact_sheet":
                return await self._process_contact_sheet(job)
            elif job.job_type == "waveform":
                return await self._process_waveform(job)
            elif job.job_type == "spectral_waveform":
                return await self._process_spectral_waveform(job)
            elif job.job_type == "vectorscope":
                return await self._process_vectorscope(job)
            elif job.job_type == "image_sequence":
                return await self._process_image_sequence(job)
            elif job.job_type == "adaptive_bitrate":
                return await self._process_adaptive_bitrate(job)
            elif job.job_type == "scene_detection":
                return await self._process_scene_detection(job)
            elif job.job_type == "smart_crop":
                return await self._process_smart_crop(job)
            elif job.job_type == "batch_smart_crop":
                return await self._process_batch_smart_crop(job)
            elif job.job_type == "image_watermark":
                return await self._process_image_watermark(job)
            elif job.job_type == "text_watermark":
                return await self._process_text_watermark(job)
            elif job.job_type == "video_watermark":
                return await self._process_video_watermark(job)
            elif job.job_type == "batch_watermark":
                return await self._process_batch_watermark(job)
            elif job.job_type == "8k_proxy":
                return await self._process_8k_proxy(job)
            elif job.job_type == "8k_proxy_batch":
                return await self._process_8k_proxy_batch(job)
            elif job.job_type == "ultra_hd_analysis":
                return await self._process_ultra_hd_analysis(job)
            elif job.job_type == "hdr_processing":
                return await self._process_hdr_processing(job)
            elif job.job_type == "hdr_analysis":
                return await self._process_hdr_analysis(job)
            elif job.job_type == "hdr_to_sdr":
                return await self._process_hdr_to_sdr(job)
            elif job.job_type == "sdr_to_hdr":
                return await self._process_sdr_to_hdr(job)
            elif job.job_type == "hdr_delivery_optimization":
                return await self._process_hdr_delivery_optimization(job)
            elif job.job_type == "spherical_analysis":
                return await self._process_spherical_analysis(job)
            elif job.job_type == "spherical_conversion":
                return await self._process_spherical_conversion(job)
            elif job.job_type == "vr_optimization":
                return await self._process_vr_optimization(job)
            elif job.job_type == "spatial_metadata":
                return await self._process_spatial_metadata(job)
            elif job.job_type == "vr_content_analysis":
                return await self._process_vr_content_analysis(job)
            elif job.job_type == "vr_content_processing":
                return await self._process_vr_content_processing(job)
            elif job.job_type == "vr_preview":
                return await self._process_vr_preview(job)
            elif job.job_type == "vr_motion_extraction":
                return await self._process_vr_motion_extraction(job)
            elif job.job_type == "vr_streaming_optimization":
                return await self._process_vr_streaming_optimization(job)
            elif job.job_type == "vr_thumbnail_sequence":
                return await self._process_vr_thumbnail_sequence(job)
            elif job.job_type == "spatial_audio_analysis":
                return await self._process_spatial_audio_analysis(job)
            elif job.job_type == "spatial_audio_conversion":
                return await self._process_spatial_audio_conversion(job)
            elif job.job_type == "ambisonic_encoding":
                return await self._process_ambisonic_encoding(job)
            elif job.job_type == "binaural_rendering":
                return await self._process_binaural_rendering(job)
            elif job.job_type == "room_acoustics":
                return await self._process_room_acoustics(job)
            elif job.job_type == "spatial_mix":
                return await self._process_spatial_mix(job)
            elif job.job_type == "live_stream_start":
                return await self._process_live_stream_start(job)
            elif job.job_type == "live_stream_stop":
                return await self._process_live_stream_stop(job)
            elif job.job_type == "adaptive_stream":
                return await self._process_adaptive_stream(job)
            elif job.job_type == "stream_overlay":
                return await self._process_stream_overlay(job)
            elif job.job_type == "stream_recording":
                return await self._process_stream_recording(job)
            elif job.job_type == "remote_production_create":
                return await self._process_remote_production_create(job)
            elif job.job_type == "remote_participant_add":
                return await self._process_remote_participant_add(job)
            elif job.job_type == "remote_source_add":
                return await self._process_remote_source_add(job)
            elif job.job_type == "tally_update":
                return await self._process_tally_update(job)
            elif job.job_type == "return_feed_config":
                return await self._process_return_feed_config(job)
            elif job.job_type == "cloud_switching_create":
                return await self._process_cloud_switching_create(job)
            elif job.job_type == "switching_input_add":
                return await self._process_switching_input_add(job)
            elif job.job_type == "switching_switch":
                return await self._process_switching_switch(job)
            elif job.job_type == "switching_output_config":
                return await self._process_switching_output_config(job)
            elif job.job_type == "switching_macro_create":
                return await self._process_switching_macro_create(job)
            elif job.job_type == "virtual_studio_create":
                return await self._process_virtual_studio_create(job)
            elif job.job_type == "virtual_studio_chroma_config":
                return await self._process_virtual_studio_chroma_config(job)
            elif job.job_type == "virtual_studio_set_load":
                return await self._process_virtual_studio_set_load(job)
            elif job.job_type == "virtual_studio_ar_add":
                return await self._process_virtual_studio_ar_add(job)
            elif job.job_type == "virtual_studio_tracking_update":
                return await self._process_virtual_studio_tracking_update(job)
            elif job.job_type == "live_graphics_create":
                return await self._process_live_graphics_create(job)
            elif job.job_type == "live_graphics_template_load":
                return await self._process_live_graphics_template_load(job)
            elif job.job_type == "live_graphics_show":
                return await self._process_live_graphics_show(job)
            elif job.job_type == "live_graphics_data_update":
                return await self._process_live_graphics_data_update(job)
            elif job.job_type == "live_graphics_playlist_create":
                return await self._process_live_graphics_playlist_create(job)
            else:
                raise ProxyGenerationError(f"Unknown job type: {job.job_type}")
                
        except Exception as e:
            logger.error(
                "job_processing_failed",
                error=str(e),
                job_id=job.job_id,
                job_type=job.job_type
            )
            raise
    
    async def _process_video_proxy(self, job: ProxyJob) -> Dict[str, Any]:
        """Process video proxy generation"""
        temp_output_path = None
        try:
            # Get parameters
            quality = job.parameters.get("quality", "medium")
            format_type = job.parameters.get("format", "mp4")
            
            # Validate input
            media_info = await self.ffmpeg_service.get_media_info(job.input_path)
            
            # Check if video stream exists
            has_video = any(s["codec_type"] == "video" for s in media_info["streams"])
            if not has_video:
                raise InvalidMediaError("No video stream found in input file")
            
            # Generate temporary output path
            temp_output_path = os.path.join(
                self._temp_dir,
                f"{job.job_id}_proxy_{quality}.{format_type}"
            )
            
            # Generate proxy
            result = await self.ffmpeg_service.generate_video_proxy(
                input_path=job.input_path,
                output_path=temp_output_path,
                preset=quality,
                custom_options=job.parameters.get("custom_options")
            )
            
            # Store in storage backend
            storage_key = self.storage_service.generate_storage_key(
                asset_id=job.asset_id,
                proxy_type="video",
                quality=quality,
                extension=format_type
            )
            
            storage_url = await self.storage_service.store_file(
                file_path=temp_output_path,
                storage_key=storage_key,
                metadata={
                    "job_id": job.job_id,
                    "asset_id": job.asset_id,
                    "quality": quality,
                    "format": format_type,
                    "processing_time": str(result["processing_time"]),
                    "original_duration": str(media_info["duration"]),
                    "proxy_duration": str(result["output_duration"])
                }
            )
            
            # Build response
            response = {
                "job_id": job.job_id,
                "asset_id": job.asset_id,
                "proxy_type": "video",
                "quality": quality,
                "format": format_type,
                "storage_key": storage_key,
                "storage_url": storage_url,
                "file_size": result["output_size"],
                "duration": result["output_duration"],
                "processing_time": result["processing_time"],
                "media_info": result["output_info"]
            }
            
            logger.info(
                "video_proxy_completed",
                **response
            )
            
            return response
            
        finally:
            # Cleanup temp file
            if temp_output_path and os.path.exists(temp_output_path):
                os.remove(temp_output_path)
    
    async def _process_audio_proxy(self, job: ProxyJob) -> Dict[str, Any]:
        """Process audio proxy generation"""
        temp_output_path = None
        try:
            # Get parameters
            normalize = job.parameters.get("normalize", True)
            target_level = job.parameters.get("target_level", -23.0)
            format_type = job.parameters.get("format", "mp3")
            
            # Validate input
            media_info = await self.ffmpeg_service.get_media_info(job.input_path)
            
            # Check if audio stream exists
            has_audio = any(s["codec_type"] == "audio" for s in media_info["streams"])
            if not has_audio:
                raise InvalidMediaError("No audio stream found in input file")
            
            # Generate temporary output path
            temp_output_path = os.path.join(
                self._temp_dir,
                f"{job.job_id}_audio.{format_type}"
            )
            
            # Process audio
            if normalize:
                # First normalize, then convert format if needed
                if format_type != "wav":
                    # Normalize to temporary WAV file first
                    temp_wav_path = os.path.join(
                        self._temp_dir,
                        f"{job.job_id}_normalized.wav"
                    )
                    await self.ffmpeg_service.normalize_audio(
                        input_path=job.input_path,
                        output_path=temp_wav_path,
                        target_level=target_level
                    )
                    # Then convert to target format
                    result = await self.ffmpeg_service.convert_audio_format(
                        input_path=temp_wav_path,
                        output_path=temp_output_path,
                        output_format=format_type,
                        bitrate=job.parameters.get("bitrate", "192k"),
                        sample_rate=job.parameters.get("sample_rate"),
                        channels=job.parameters.get("channels")
                    )
                    # Clean up temp file
                    if os.path.exists(temp_wav_path):
                        os.remove(temp_wav_path)
                else:
                    # Direct normalization to WAV
                    result = await self.ffmpeg_service.normalize_audio(
                        input_path=job.input_path,
                        output_path=temp_output_path,
                        target_level=target_level
                    )
            else:
                # Simple format conversion without normalization
                result = await self.ffmpeg_service.convert_audio_format(
                    input_path=job.input_path,
                    output_path=temp_output_path,
                    output_format=format_type,
                    bitrate=job.parameters.get("bitrate", "192k"),
                    sample_rate=job.parameters.get("sample_rate"),
                    channels=job.parameters.get("channels")
                )
            
            # Store in storage backend
            storage_key = self.storage_service.generate_storage_key(
                asset_id=job.asset_id,
                proxy_type="audio",
                quality="normalized" if normalize else "standard",
                extension=format_type
            )
            
            storage_url = await self.storage_service.store_file(
                file_path=temp_output_path,
                storage_key=storage_key,
                metadata={
                    "job_id": job.job_id,
                    "asset_id": job.asset_id,
                    "normalized": str(normalize),
                    "target_level": str(target_level) if normalize else None,
                    "format": format_type
                }
            )
            
            # Build response
            response = {
                "job_id": job.job_id,
                "asset_id": job.asset_id,
                "proxy_type": "audio",
                "format": format_type,
                "normalized": normalize,
                "storage_key": storage_key,
                "storage_url": storage_url,
                "file_size": os.path.getsize(temp_output_path),
                "loudnorm_stats": result.get("loudnorm_stats") if normalize else None
            }
            
            logger.info(
                "audio_proxy_completed",
                **response
            )
            
            return response
            
        finally:
            # Cleanup temp file
            if temp_output_path and os.path.exists(temp_output_path):
                os.remove(temp_output_path)
    
    async def _process_thumbnail(self, job: ProxyJob) -> Dict[str, Any]:
        """Process legacy thumbnail generation"""
        temp_files = []
        try:
            # Get parameters
            time_offsets = job.parameters.get("time_offsets", [0])
            sizes = job.parameters.get("sizes", settings.thumbnail_sizes)
            
            # Validate input
            media_info = await self.ffmpeg_service.get_media_info(job.input_path)
            duration = media_info["duration"]
            
            # Generate thumbnails
            thumbnails = []
            
            for size in sizes:
                for i, time_offset in enumerate(time_offsets):
                    # Ensure time offset is within duration
                    time_offset = min(time_offset, duration - 0.1)
                    time_offset = max(0, time_offset)
                    
                    # Generate temporary output path
                    temp_output_path = os.path.join(
                        self._temp_dir,
                        f"{job.job_id}_thumb_{size['name']}_{i}.jpg"
                    )
                    temp_files.append(temp_output_path)
                    
                    # Generate thumbnail
                    result = await self.ffmpeg_service.generate_thumbnail(
                        input_path=job.input_path,
                        output_path=temp_output_path,
                        time_offset=time_offset,
                        size=size
                    )
                    
                    # Store in storage backend
                    storage_key = self.storage_service.generate_storage_key(
                        asset_id=job.asset_id,
                        proxy_type="thumbnail",
                        quality=f"{size['name']}_{i}",
                        extension="jpg"
                    )
                    
                    storage_url = await self.storage_service.store_file(
                        file_path=temp_output_path,
                        storage_key=storage_key,
                        metadata={
                            "job_id": job.job_id,
                            "asset_id": job.asset_id,
                            "size_name": size['name'],
                            "width": str(size['width']),
                            "height": str(size['height']),
                            "time_offset": str(time_offset),
                            "index": str(i)
                        }
                    )
                    
                    thumbnails.append({
                        "size": size['name'],
                        "width": size['width'],
                        "height": size['height'],
                        "time_offset": time_offset,
                        "storage_key": storage_key,
                        "storage_url": storage_url,
                        "file_size": os.path.getsize(temp_output_path)
                    })
            
            # Build response
            response = {
                "job_id": job.job_id,
                "asset_id": job.asset_id,
                "proxy_type": "thumbnail",
                "thumbnails": thumbnails,
                "total_count": len(thumbnails)
            }
            
            logger.info(
                "thumbnails_completed",
                job_id=job.job_id,
                asset_id=job.asset_id,
                count=len(thumbnails)
            )
            
            return response
            
        finally:
            # Cleanup temp files
            for temp_file in temp_files:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
    
    async def _process_thumbnail_batch(self, job: ProxyJob) -> Dict[str, Any]:
        """Process batch thumbnail generation"""
        temp_files = []
        try:
            # Get parameters
            count = job.parameters.get("count", 10)
            width = job.parameters.get("width", 320)
            height = job.parameters.get("height", 180)
            format_type = job.parameters.get("format", "jpg")
            quality = job.parameters.get("quality", 85)
            start_time = job.parameters.get("start_time", 0)
            duration = job.parameters.get("duration")
            method = job.parameters.get("method", "interval")
            
            # Generate output pattern
            output_pattern = os.path.join(
                self._temp_dir,
                f"{job.job_id}_thumb_%d.{format_type}"
            )
            
            # Generate thumbnails
            result = await self.ffmpeg_service.generate_thumbnails(
                input_path=job.input_path,
                output_pattern=output_pattern,
                count=count,
                width=width,
                height=height,
                format=format_type,
                quality=quality,
                start_time=start_time,
                duration=duration,
                method=method
            )
            
            # Store thumbnails
            stored_thumbnails = []
            for thumb in result["thumbnails"]:
                temp_files.append(thumb["path"])
                
                # Generate storage key
                storage_key = self.storage_service.generate_storage_key(
                    asset_id=job.asset_id,
                    proxy_type="thumbnail",
                    quality=f"{method}_{thumb['index']}",
                    extension=format_type
                )
                
                # Store file
                storage_url = await self.storage_service.store_file(
                    file_path=thumb["path"],
                    storage_key=storage_key,
                    metadata={
                        "job_id": job.job_id,
                        "asset_id": job.asset_id,
                        "method": method,
                        "index": str(thumb["index"]),
                        "width": str(width),
                        "height": str(height),
                        "format": format_type
                    }
                )
                
                stored_thumbnails.append({
                    "index": thumb["index"],
                    "storage_key": storage_key,
                    "storage_url": storage_url,
                    "file_size": thumb["size"]
                })
            
            # Build response
            response = {
                "job_id": job.job_id,
                "asset_id": job.asset_id,
                "proxy_type": "thumbnail_batch",
                "method": method,
                "count": len(stored_thumbnails),
                "thumbnails": stored_thumbnails,
                "total_size": result["total_size"]
            }
            
            logger.info(
                "thumbnail_batch_completed",
                **response
            )
            
            return response
            
        finally:
            # Cleanup temp files
            for temp_file in temp_files:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
    
    async def _process_thumbnail_single(self, job: ProxyJob) -> Dict[str, Any]:
        """Process single thumbnail generation"""
        temp_output_path = None
        try:
            # Get parameters
            time_offset = job.parameters.get("time_offset", "auto")
            width = job.parameters.get("width", 320)
            height = job.parameters.get("height", 180)
            format_type = job.parameters.get("format", "jpg")
            quality = job.parameters.get("quality", 85)
            
            # Generate temporary output path
            temp_output_path = os.path.join(
                self._temp_dir,
                f"{job.job_id}_thumb_single.{format_type}"
            )
            
            # Generate thumbnail
            result = await self.ffmpeg_service.generate_single_thumbnail(
                input_path=job.input_path,
                output_path=temp_output_path,
                time_offset=time_offset,
                width=width,
                height=height,
                format=format_type,
                quality=quality
            )
            
            # Store in storage backend
            storage_key = self.storage_service.generate_storage_key(
                asset_id=job.asset_id,
                proxy_type="thumbnail",
                quality=f"single_{result['time_offset']}",
                extension=format_type
            )
            
            storage_url = await self.storage_service.store_file(
                file_path=temp_output_path,
                storage_key=storage_key,
                metadata={
                    "job_id": job.job_id,
                    "asset_id": job.asset_id,
                    "time_offset": str(result["time_offset"]),
                    "width": str(width),
                    "height": str(height),
                    "format": format_type
                }
            )
            
            # Build response
            response = {
                "job_id": job.job_id,
                "asset_id": job.asset_id,
                "proxy_type": "thumbnail_single",
                "time_offset": result["time_offset"],
                "storage_key": storage_key,
                "storage_url": storage_url,
                "file_size": result["size"],
                "dimensions": {"width": width, "height": height}
            }
            
            logger.info(
                "single_thumbnail_completed",
                **response
            )
            
            return response
            
        finally:
            # Cleanup temp file
            if temp_output_path and os.path.exists(temp_output_path):
                os.remove(temp_output_path)
    
    async def _process_contact_sheet(self, job: ProxyJob) -> Dict[str, Any]:
        """Process contact sheet generation"""
        temp_output_path = None
        try:
            # Get parameters
            grid_size = job.parameters.get("grid_size", [4, 4])
            thumb_width = job.parameters.get("thumb_width", 320)
            thumb_height = job.parameters.get("thumb_height", 180)
            padding = job.parameters.get("padding", 5)
            background_color = job.parameters.get("background_color", "black")
            include_timestamps = job.parameters.get("include_timestamps", True)
            font_size = job.parameters.get("font_size", 12)
            font_color = job.parameters.get("font_color", "white")
            
            # Generate temporary output path
            temp_output_path = os.path.join(
                self._temp_dir,
                f"{job.job_id}_contact_sheet.jpg"
            )
            
            # Generate contact sheet
            result = await self.ffmpeg_service.generate_contact_sheet(
                input_path=job.input_path,
                output_path=temp_output_path,
                grid_size=tuple(grid_size),
                thumb_width=thumb_width,
                thumb_height=thumb_height,
                padding=padding,
                background_color=background_color,
                include_timestamps=include_timestamps,
                font_size=font_size,
                font_color=font_color
            )
            
            # Store in storage backend
            storage_key = self.storage_service.generate_storage_key(
                asset_id=job.asset_id,
                proxy_type="contact_sheet",
                quality=f"{grid_size[0]}x{grid_size[1]}",
                extension="jpg"
            )
            
            storage_url = await self.storage_service.store_file(
                file_path=temp_output_path,
                storage_key=storage_key,
                metadata={
                    "job_id": job.job_id,
                    "asset_id": job.asset_id,
                    "columns": str(grid_size[0]),
                    "rows": str(grid_size[1]),
                    "thumb_width": str(thumb_width),
                    "thumb_height": str(thumb_height),
                    "thumbnail_count": str(result["thumbnail_count"])
                }
            )
            
            # Build response
            response = {
                "job_id": job.job_id,
                "asset_id": job.asset_id,
                "proxy_type": "contact_sheet",
                "grid": result["grid"],
                "dimensions": result["dimensions"],
                "thumbnail_count": result["thumbnail_count"],
                "thumbnail_size": result["thumbnail_size"],
                "storage_key": storage_key,
                "storage_url": storage_url,
                "file_size": result["size"]
            }
            
            logger.info(
                "contact_sheet_completed",
                **response
            )
            
            return response
            
        finally:
            # Cleanup temp file
            if temp_output_path and os.path.exists(temp_output_path):
                os.remove(temp_output_path)
    
    async def _process_waveform(self, job: ProxyJob) -> Dict[str, Any]:
        """Process waveform generation"""
        temp_output_path = None
        try:
            # Get parameters
            width = job.parameters.get("width", settings.waveform_width)
            height = job.parameters.get("height", settings.waveform_height)
            style = job.parameters.get("style", "line")
            colors = job.parameters.get("colors")
            split_channels = job.parameters.get("split_channels", False)
            show_axis = job.parameters.get("show_axis", True)
            logarithmic = job.parameters.get("logarithmic", False)
            
            # Generate temporary output path
            temp_output_path = os.path.join(
                self._temp_dir,
                f"{job.job_id}_waveform.png"
            )
            
            # Generate waveform
            result = await self.ffmpeg_service.generate_waveform(
                input_path=job.input_path,
                output_path=temp_output_path,
                width=width,
                height=height,
                style=style,
                colors=colors,
                split_channels=split_channels,
                show_axis=show_axis,
                logarithmic=logarithmic
            )
            
            # Store in storage backend
            storage_key = self.storage_service.generate_storage_key(
                asset_id=job.asset_id,
                proxy_type="waveform",
                quality=f"{width}x{height}_{style}",
                extension="png"
            )
            
            storage_url = await self.storage_service.store_file(
                file_path=temp_output_path,
                storage_key=storage_key,
                metadata={
                    "job_id": job.job_id,
                    "asset_id": job.asset_id,
                    "width": str(width),
                    "height": str(height),
                    "style": style,
                    "split_channels": str(split_channels),
                    "logarithmic": str(logarithmic)
                }
            )
            
            # Build response
            response = {
                "job_id": job.job_id,
                "asset_id": job.asset_id,
                "proxy_type": "waveform",
                "width": width,
                "height": height,
                "style": style,
                "storage_key": storage_key,
                "storage_url": storage_url,
                "file_size": os.path.getsize(temp_output_path),
                "processing_time": result.get("processing_time")
            }
            
            logger.info(
                "waveform_completed",
                **response
            )
            
            return response
            
        finally:
            # Cleanup temp file
            if temp_output_path and os.path.exists(temp_output_path):
                os.remove(temp_output_path)
    
    async def _process_spectral_waveform(self, job: ProxyJob) -> Dict[str, Any]:
        """Process spectral waveform (spectrogram) generation"""
        temp_output_path = None
        try:
            # Get parameters
            width = job.parameters.get("width", 1920)
            height = job.parameters.get("height", 512)
            color_mode = job.parameters.get("color_mode", "intensity")
            frequency_scale = job.parameters.get("frequency_scale", "lin")
            window_size = job.parameters.get("window_size", 2048)
            overlap = job.parameters.get("overlap", 0.875)
            
            # Generate temporary output path
            temp_output_path = os.path.join(
                self._temp_dir,
                f"{job.job_id}_spectrogram.png"
            )
            
            # Generate spectral waveform
            result = await self.ffmpeg_service.generate_spectral_waveform(
                input_path=job.input_path,
                output_path=temp_output_path,
                width=width,
                height=height,
                color_mode=color_mode,
                frequency_scale=frequency_scale,
                window_size=window_size,
                overlap=overlap
            )
            
            # Store in storage backend
            storage_key = self.storage_service.generate_storage_key(
                asset_id=job.asset_id,
                proxy_type="spectral_waveform",
                quality=f"{width}x{height}_{color_mode}",
                extension="png"
            )
            
            storage_url = await self.storage_service.store_file(
                file_path=temp_output_path,
                storage_key=storage_key,
                metadata={
                    "job_id": job.job_id,
                    "asset_id": job.asset_id,
                    "width": str(width),
                    "height": str(height),
                    "color_mode": color_mode,
                    "frequency_scale": frequency_scale,
                    "window_size": str(window_size),
                    "overlap": str(overlap)
                }
            )
            
            # Build response
            response = {
                "job_id": job.job_id,
                "asset_id": job.asset_id,
                "proxy_type": "spectral_waveform",
                "width": width,
                "height": height,
                "color_mode": color_mode,
                "frequency_scale": frequency_scale,
                "storage_key": storage_key,
                "storage_url": storage_url,
                "file_size": os.path.getsize(temp_output_path),
                "processing_time": result.get("processing_time"),
                "frequency_range": result.get("frequency_range"),
                "time_range": result.get("time_range")
            }
            
            logger.info(
                "spectral_waveform_completed",
                **response
            )
            
            return response
            
        finally:
            # Cleanup temp file
            if temp_output_path and os.path.exists(temp_output_path):
                os.remove(temp_output_path)
    
    async def _process_vectorscope(self, job: ProxyJob) -> Dict[str, Any]:
        """Process vectorscope generation"""
        temp_output_path = None
        try:
            # Get parameters
            width = job.parameters.get("width", 256)
            height = job.parameters.get("height", 256)
            mode = job.parameters.get("mode", "lissajous")
            intensity = job.parameters.get("intensity", 0.04)
            zoom = job.parameters.get("zoom", 1.0)
            
            # Generate temporary output path
            temp_output_path = os.path.join(
                self._temp_dir,
                f"{job.job_id}_vectorscope.png"
            )
            
            # Generate vectorscope
            result = await self.ffmpeg_service.generate_vectorscope(
                input_path=job.input_path,
                output_path=temp_output_path,
                width=width,
                height=height,
                mode=mode,
                intensity=intensity,
                zoom=zoom
            )
            
            # Store in storage backend
            storage_key = self.storage_service.generate_storage_key(
                asset_id=job.asset_id,
                proxy_type="vectorscope",
                quality=f"{width}x{height}_{mode}",
                extension="png"
            )
            
            storage_url = await self.storage_service.store_file(
                file_path=temp_output_path,
                storage_key=storage_key,
                metadata={
                    "job_id": job.job_id,
                    "asset_id": job.asset_id,
                    "width": str(width),
                    "height": str(height),
                    "mode": mode,
                    "intensity": str(intensity),
                    "zoom": str(zoom)
                }
            )
            
            # Build response
            response = {
                "job_id": job.job_id,
                "asset_id": job.asset_id,
                "proxy_type": "vectorscope",
                "width": width,
                "height": height,
                "mode": mode,
                "storage_key": storage_key,
                "storage_url": storage_url,
                "file_size": os.path.getsize(temp_output_path),
                "processing_time": result.get("processing_time"),
                "phase_correlation": result.get("phase_correlation")
            }
            
            logger.info(
                "vectorscope_completed",
                **response
            )
            
            return response
            
        finally:
            # Cleanup temp file
            if temp_output_path and os.path.exists(temp_output_path):
                os.remove(temp_output_path)
    
    async def _process_image_sequence(self, job: ProxyJob) -> Dict[str, Any]:
        """Process image sequence to video/gif conversion"""
        temp_output_path = None
        try:
            # Get parameters
            input_pattern = job.parameters.get("input_pattern", job.input_path)
            output_format = job.parameters.get("output_format", "mp4")
            frame_rate = job.parameters.get("frame_rate", 24)
            quality = job.parameters.get("quality")
            
            # Generate temporary output path
            temp_output_path = os.path.join(
                self._temp_dir,
                f"{job.job_id}_sequence.{output_format}"
            )
            
            # Convert image sequence
            result = await self.ffmpeg_service.convert_image_sequence(
                input_pattern=input_pattern,
                output_path=temp_output_path,
                output_format=output_format,
                frame_rate=frame_rate,
                quality=quality
            )
            
            # Store in storage backend
            storage_key = self.storage_service.generate_storage_key(
                asset_id=job.asset_id,
                proxy_type="image_sequence",
                quality=f"{output_format}_{frame_rate}fps",
                extension=output_format
            )
            
            storage_url = await self.storage_service.store_file(
                file_path=temp_output_path,
                storage_key=storage_key,
                metadata={
                    "job_id": job.job_id,
                    "asset_id": job.asset_id,
                    "input_pattern": input_pattern,
                    "output_format": output_format,
                    "frame_rate": str(frame_rate),
                    "duration": str(result.get("duration", 0))
                }
            )
            
            # Build response
            response = {
                "job_id": job.job_id,
                "asset_id": job.asset_id,
                "proxy_type": "image_sequence",
                "output_format": output_format,
                "frame_rate": frame_rate,
                "duration": result.get("duration"),
                "storage_key": storage_key,
                "storage_url": storage_url,
                "file_size": result["file_size"],
                "processing_time": result["processing_time"]
            }
            
            logger.info(
                "image_sequence_completed",
                **response
            )
            
            return response
            
        finally:
            # Cleanup temp file
            if temp_output_path and os.path.exists(temp_output_path):
                os.remove(temp_output_path)
    
    async def create_job(
        self,
        asset_id: str,
        input_path: str,
        job_type: str,
        parameters: Dict[str, Any],
        priority: str = "normal",
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a new proxy generation job"""
        # Import here to avoid circular dependency
        from .queue_service import get_queue_service
        
        queue_service = await get_queue_service()
        
        job_id = await queue_service.submit_job(
            asset_id=asset_id,
            input_path=input_path,
            job_type=job_type,
            parameters=parameters,
            priority=priority,
            metadata=metadata
        )
        
        return job_id
    
    async def _process_adaptive_bitrate(self, job: ProxyJob) -> Dict[str, Any]:
        """Process adaptive bitrate stream generation"""
        output_dir = None
        try:
            # Get parameters
            stream_formats = job.parameters.get("stream_formats", ["hls", "dash"])
            qualities = job.parameters.get("qualities")
            segment_duration = job.parameters.get("segment_duration", 6)
            playlist_type = job.parameters.get("playlist_type", "vod")
            force_gpu = job.parameters.get("force_gpu", True)
            
            # Validate input
            media_info = await self.ffmpeg_service.get_media_info(job.input_path)
            
            # Check if video stream exists
            has_video = any(s["codec_type"] == "video" for s in media_info["streams"])
            if not has_video:
                raise InvalidMediaError("No video stream found in input file")
            
            # Create output directory for streams
            output_dir = os.path.join(
                self._temp_dir,
                f"{job.job_id}_adaptive_bitrate"
            )
            os.makedirs(output_dir, exist_ok=True)
            
            # Generate adaptive bitrate streams
            result = await self.ffmpeg_service.generate_adaptive_bitrate_stream(
                input_path=job.input_path,
                output_dir=output_dir,
                stream_formats=stream_formats,
                qualities=qualities,
                segment_duration=segment_duration,
                playlist_type=playlist_type,
                force_gpu=force_gpu
            )
            
            # Store stream files in storage backend
            storage_urls = {}
            storage_keys = {}
            
            for stream_format in stream_formats:
                if stream_format in result.get("streams", {}):
                    stream_info = result["streams"][stream_format]
                    format_storage_urls = {}
                    format_storage_keys = {}
                    
                    # Store all files for this stream format
                    for root, dirs, files in os.walk(output_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            relative_path = os.path.relpath(file_path, output_dir)
                            
                            # Create storage key for this file
                            storage_key = self.storage_service.generate_storage_key(
                                asset_id=job.asset_id,
                                proxy_type="adaptive_bitrate",
                                quality=f"{stream_format}_{relative_path.replace('/', '_')}",
                                extension=file.split('.')[-1] if '.' in file else "dat"
                            )
                            
                            # Store the file
                            storage_url = await self.storage_service.store_file(
                                file_path=file_path,
                                storage_key=storage_key,
                                metadata={
                                    "job_id": job.job_id,
                                    "asset_id": job.asset_id,
                                    "stream_format": stream_format,
                                    "file_type": relative_path,
                                    "qualities": [q["name"] for q in result["qualities"]],
                                    "segment_duration": segment_duration,
                                    "playlist_type": playlist_type,
                                    "gpu_acceleration": str(result["gpu_acceleration"])
                                }
                            )
                            
                            format_storage_urls[relative_path] = storage_url
                            format_storage_keys[relative_path] = storage_key
                    
                    storage_urls[stream_format] = format_storage_urls
                    storage_keys[stream_format] = format_storage_keys
            
            # Build response
            response = {
                "job_id": job.job_id,
                "asset_id": job.asset_id,
                "proxy_type": "adaptive_bitrate",
                "stream_formats": stream_formats,
                "qualities": [q["name"] for q in result["qualities"]],
                "segment_duration": segment_duration,
                "playlist_type": playlist_type,
                "storage_keys": storage_keys,
                "storage_urls": storage_urls,
                "total_size": result["total_size"],
                "processing_time": result["processing_time"],
                "gpu_acceleration": result["gpu_acceleration"],
                "streams": result.get("streams", {})
            }
            
            logger.info(
                "adaptive_bitrate_processed",
                job_id=job.job_id,
                asset_id=job.asset_id,
                stream_formats=stream_formats,
                qualities=len(result["qualities"]),
                total_size=result["total_size"],
                processing_time=result["processing_time"]
            )
            
            return response
            
        except Exception as e:
            logger.error(
                "adaptive_bitrate_processing_failed",
                error=str(e),
                job_id=job.job_id,
                asset_id=job.asset_id
            )
            raise ProxyGenerationError(f"Adaptive bitrate processing failed: {str(e)}")
        
        finally:
            # Clean up temporary output directory
            if output_dir and os.path.exists(output_dir):
                import shutil
                shutil.rmtree(output_dir)
    
    async def _process_scene_detection(self, job: ProxyJob) -> Dict[str, Any]:
        """Process scene detection job"""
        try:
            # Get parameters
            threshold = job.parameters.get("threshold", 0.3)
            min_scene_duration = job.parameters.get("min_scene_duration", 1.0)
            output_format = job.parameters.get("output_format", "json")
            save_thumbnails = job.parameters.get("save_thumbnails", False)
            thumbnail_size = job.parameters.get("thumbnail_size", "320x180")
            
            # Validate input
            media_info = await self.ffmpeg_service.get_media_info(job.input_path)
            
            # Check if video stream exists
            has_video = any(s["codec_type"] == "video" for s in media_info["streams"])
            if not has_video:
                raise InvalidMediaError("No video stream found in input file")
            
            # Prepare thumbnail directory if needed
            thumbnail_dir = None
            thumbnail_storage_urls = []
            
            if save_thumbnails:
                thumbnail_dir = os.path.join(
                    self._temp_dir,
                    f"{job.job_id}_scene_thumbnails"
                )
                os.makedirs(thumbnail_dir, exist_ok=True)
            
            # Detect scene changes
            result = await self.ffmpeg_service.detect_scene_changes(
                input_path=job.input_path,
                threshold=threshold,
                min_scene_duration=min_scene_duration,
                output_format=output_format,
                save_thumbnails=save_thumbnails,
                thumbnail_dir=thumbnail_dir,
                thumbnail_size=thumbnail_size
            )
            
            # Store thumbnails if generated
            if save_thumbnails and thumbnail_dir and os.path.exists(thumbnail_dir):
                for file in os.listdir(thumbnail_dir):
                    if file.endswith(('.jpg', '.jpeg', '.png')):
                        file_path = os.path.join(thumbnail_dir, file)
                        
                        # Create storage key for thumbnail
                        storage_key = self.storage_service.generate_storage_key(
                            asset_id=job.asset_id,
                            proxy_type="scene_thumbnail",
                            quality=file.replace('.', '_'),
                            extension=file.split('.')[-1]
                        )
                        
                        # Store the thumbnail
                        storage_url = await self.storage_service.store_file(
                            file_path=file_path,
                            storage_key=storage_key,
                            metadata={
                                "job_id": job.job_id,
                                "asset_id": job.asset_id,
                                "thumbnail_type": "scene_change",
                                "threshold": threshold,
                                "min_scene_duration": min_scene_duration
                            }
                        )
                        
                        thumbnail_storage_urls.append({
                            "filename": file,
                            "storage_key": storage_key,
                            "storage_url": storage_url
                        })
            
            # Store scene detection results as JSON
            if output_format == "json":
                results_json = json.dumps(result, indent=2)
                results_path = os.path.join(self._temp_dir, f"{job.job_id}_scenes.json")
                
                with open(results_path, 'w') as f:
                    f.write(results_json)
                
                # Store results file
                results_storage_key = self.storage_service.generate_storage_key(
                    asset_id=job.asset_id,
                    proxy_type="scene_detection",
                    quality="results",
                    extension="json"
                )
                
                results_storage_url = await self.storage_service.store_file(
                    file_path=results_path,
                    storage_key=results_storage_key,
                    metadata={
                        "job_id": job.job_id,
                        "asset_id": job.asset_id,
                        "detection_type": "scene_change",
                        "threshold": threshold,
                        "total_scenes": result["total_scenes"]
                    }
                )
                
                # Clean up temporary results file
                os.unlink(results_path)
            else:
                results_storage_url = None
                results_storage_key = None
            
            # Build response
            response = {
                "job_id": job.job_id,
                "asset_id": job.asset_id,
                "detection_type": "scene_change",
                "threshold": threshold,
                "min_scene_duration": min_scene_duration,
                "total_scenes": result["total_scenes"],
                "duration": result["duration"],
                "average_scene_duration": result["average_scene_duration"],
                "scenes": result["scenes"],
                "output_format": output_format,
                "thumbnails_saved": result["thumbnails_saved"],
                "thumbnail_urls": thumbnail_storage_urls,
                "results_storage_key": results_storage_key,
                "results_storage_url": results_storage_url,
                "processing_time": result["processing_time"]
            }
            
            logger.info(
                "scene_detection_processed",
                job_id=job.job_id,
                asset_id=job.asset_id,
                total_scenes=result["total_scenes"],
                threshold=threshold,
                processing_time=result["processing_time"]
            )
            
            return response
            
        except Exception as e:
            logger.error(
                "scene_detection_processing_failed",
                error=str(e),
                job_id=job.job_id,
                asset_id=job.asset_id
            )
            raise ProxyGenerationError(f"Scene detection processing failed: {str(e)}")
        
        finally:
            # Clean up temporary thumbnail directory
            if thumbnail_dir and os.path.exists(thumbnail_dir):
                import shutil
                shutil.rmtree(thumbnail_dir)
    
    async def _process_smart_crop(self, job: ProxyJob) -> Dict[str, Any]:
        """Process smart cropping job"""
        try:
            # Get parameters
            output_size = job.parameters.get("output_size", (1280, 720))
            crop_mode = job.parameters.get("crop_mode", "smart")
            quality = job.parameters.get("quality", 95)
            face_padding = job.parameters.get("face_padding", 1.5)
            focus_point = job.parameters.get("focus_point")
            
            # Convert crop mode string to enum
            crop_mode_enum = CropMode(crop_mode)
            
            # Perform smart cropping
            result = await self.image_service.smart_crop(
                input_path=job.input_path,
                output_size=output_size,
                crop_mode=crop_mode_enum,
                quality=quality,
                face_padding=face_padding,
                custom_focus_point=focus_point
            )
            
            # Store cropped image
            storage_key = self.storage_service.generate_storage_key(
                asset_id=job.asset_id,
                proxy_type="smart_crop",
                quality=f"{output_size[0]}x{output_size[1]}_{crop_mode}",
                extension="jpg"
            )
            
            storage_url = await self.storage_service.store_file(
                file_path=result["output_path"],
                storage_key=storage_key,
                metadata={
                    "job_id": job.job_id,
                    "asset_id": job.asset_id,
                    "crop_type": "smart_crop",
                    "original_size": result["original_size"],
                    "output_size": result["output_size"],
                    "crop_mode": crop_mode,
                    "crop_box": result["crop_box"],
                    "quality": quality
                }
            )
            
            # Clean up temporary file
            os.unlink(result["output_path"])
            
            # Build response
            response = {
                "job_id": job.job_id,
                "asset_id": job.asset_id,
                "crop_type": "smart_crop",
                "original_size": result["original_size"],
                "output_size": result["output_size"],
                "crop_mode": crop_mode,
                "crop_box": result["crop_box"],
                "quality": quality,
                "storage_key": storage_key,
                "storage_url": storage_url,
                "processing_time": result["processing_time"]
            }
            
            logger.info(
                "smart_crop_processed",
                job_id=job.job_id,
                asset_id=job.asset_id,
                crop_mode=crop_mode,
                output_size=output_size,
                processing_time=result["processing_time"]
            )
            
            return response
            
        except Exception as e:
            logger.error(
                "smart_crop_processing_failed",
                error=str(e),
                job_id=job.job_id,
                asset_id=job.asset_id
            )
            raise ProxyGenerationError(f"Smart crop processing failed: {str(e)}")
    
    async def _process_batch_smart_crop(self, job: ProxyJob) -> Dict[str, Any]:
        """Process batch smart cropping job"""
        try:
            # Get parameters
            images = job.parameters.get("images", [])
            default_output_size = job.parameters.get("default_output_size", (1280, 720))
            default_crop_mode = job.parameters.get("default_crop_mode", "smart")
            parallel_workers = job.parameters.get("parallel_workers", 4)
            
            # Convert crop mode string to enum
            default_crop_mode_enum = CropMode(default_crop_mode)
            
            # Process images in batch
            results = await self.image_service.batch_smart_crop(
                images=images,
                default_output_size=default_output_size,
                default_crop_mode=default_crop_mode_enum,
                parallel_workers=parallel_workers
            )
            
            # Store successful crops
            stored_results = []
            
            for i, result in enumerate(results):
                if result.get("success"):
                    # Get corresponding image config
                    img_config = images[i]
                    asset_id = img_config.get("asset_id", f"batch_{i}")
                    
                    # Store cropped image
                    output_size = img_config.get("output_size", default_output_size)
                    if isinstance(output_size, list):
                        output_size = tuple(output_size)
                    
                    crop_mode = img_config.get("crop_mode", default_crop_mode)
                    
                    storage_key = self.storage_service.generate_storage_key(
                        asset_id=asset_id,
                        proxy_type="smart_crop",
                        quality=f"{output_size[0]}x{output_size[1]}_{crop_mode}",
                        extension="jpg"
                    )
                    
                    storage_url = await self.storage_service.store_file(
                        file_path=result["output_path"],
                        storage_key=storage_key,
                        metadata={
                            "job_id": job.job_id,
                            "asset_id": asset_id,
                            "batch_job": True,
                            "crop_type": "smart_crop",
                            "original_size": result.get("original_size"),
                            "output_size": result.get("output_size"),
                            "crop_mode": result.get("crop_mode"),
                            "crop_box": result.get("crop_box")
                        }
                    )
                    
                    # Clean up temporary file
                    os.unlink(result["output_path"])
                    
                    stored_results.append({
                        "asset_id": asset_id,
                        "input_path": result["input_path"],
                        "success": True,
                        "storage_key": storage_key,
                        "storage_url": storage_url,
                        "original_size": result.get("original_size"),
                        "output_size": result.get("output_size"),
                        "crop_mode": result.get("crop_mode"),
                        "crop_box": result.get("crop_box"),
                        "processing_time": result.get("processing_time")
                    })
                else:
                    stored_results.append({
                        "asset_id": images[i].get("asset_id", f"batch_{i}"),
                        "input_path": result["input_path"],
                        "success": False,
                        "error": result.get("error")
                    })
            
            # Calculate summary statistics
            successful_count = sum(1 for r in stored_results if r["success"])
            failed_count = len(stored_results) - successful_count
            total_processing_time = sum(
                r.get("processing_time", 0) for r in stored_results if r.get("success")
            )
            
            # Build response
            response = {
                "job_id": job.job_id,
                "batch_type": "smart_crop",
                "total_images": len(images),
                "successful": successful_count,
                "failed": failed_count,
                "results": stored_results,
                "total_processing_time": total_processing_time,
                "parallel_workers": parallel_workers
            }
            
            logger.info(
                "batch_smart_crop_processed",
                job_id=job.job_id,
                total_images=len(images),
                successful=successful_count,
                failed=failed_count,
                processing_time=total_processing_time
            )
            
            return response
            
        except Exception as e:
            logger.error(
                "batch_smart_crop_processing_failed",
                error=str(e),
                job_id=job.job_id,
                batch_size=len(job.parameters.get("images", []))
            )
            raise ProxyGenerationError(f"Batch smart crop processing failed: {str(e)}")
    
    async def _process_image_watermark(self, job: ProxyJob) -> Dict[str, Any]:
        """Process image watermarking job"""
        try:
            # Extract parameters
            watermark_path = job.parameters.get("watermark_path")
            position = job.parameters.get("position", "bottom-right")
            opacity = job.parameters.get("opacity", 0.8)
            scale = job.parameters.get("scale", 0.2)
            margin = job.parameters.get("margin", 20)
            output_format = job.parameters.get("output_format", "same")
            quality = job.parameters.get("quality", 95)
            
            logger.info(
                "processing_image_watermark",
                job_id=job.job_id,
                asset_id=job.asset_id,
                watermark_path=watermark_path,
                position=position
            )
            
            # Process watermark
            result = await self.image_service.add_watermark(
                input_path=job.input_path,
                watermark_path=watermark_path,
                position=position,
                opacity=opacity,
                scale=scale,
                margin=margin,
                output_format=output_format,
                quality=quality
            )
            
            # Store result
            storage_key = self.storage_service.generate_storage_key(
                asset_id=job.asset_id,
                proxy_type="watermarked",
                quality=position,
                extension=output_format if output_format != "same" else "jpg"
            )
            
            storage_url = await self.storage_service.store_file(
                file_path=result["output_path"],
                storage_key=storage_key,
                metadata={
                    **result,
                    "job_id": job.job_id,
                    "asset_id": job.asset_id,
                    "watermark_path": watermark_path
                }
            )
            
            # Clean up temp file
            if os.path.exists(result["output_path"]):
                os.remove(result["output_path"])
            
            response = {
                "job_id": job.job_id,
                "asset_id": job.asset_id,
                "storage_key": storage_key,
                "storage_url": storage_url,
                "watermark_position": result["watermark_position"],
                "processing_time": result["processing_time"]
            }
            
            logger.info(
                "image_watermark_processed",
                job_id=job.job_id,
                asset_id=job.asset_id,
                processing_time=result["processing_time"]
            )
            
            return response
            
        except Exception as e:
            logger.error(
                "image_watermark_processing_failed",
                error=str(e),
                job_id=job.job_id
            )
            raise ProxyGenerationError(f"Image watermark processing failed: {str(e)}")
    
    async def _process_text_watermark(self, job: ProxyJob) -> Dict[str, Any]:
        """Process text watermarking job"""
        try:
            # Extract parameters
            text = job.parameters.get("text")
            font_path = job.parameters.get("font_path")
            font_size = job.parameters.get("font_size", 36)
            font_color = job.parameters.get("font_color", (255, 255, 255, 180))
            position = job.parameters.get("position", "bottom-right")
            margin = job.parameters.get("margin", 20)
            background_color = job.parameters.get("background_color")
            background_padding = job.parameters.get("background_padding", 10)
            output_format = job.parameters.get("output_format", "same")
            quality = job.parameters.get("quality", 95)
            
            logger.info(
                "processing_text_watermark",
                job_id=job.job_id,
                asset_id=job.asset_id,
                text=text,
                position=position
            )
            
            # Process watermark
            result = await self.image_service.add_text_watermark(
                input_path=job.input_path,
                text=text,
                font_path=font_path,
                font_size=font_size,
                font_color=font_color,
                position=position,
                margin=margin,
                background_color=background_color,
                background_padding=background_padding,
                output_format=output_format,
                quality=quality
            )
            
            # Store result
            storage_key = self.storage_service.generate_storage_key(
                asset_id=job.asset_id,
                proxy_type="text_watermarked",
                quality=position,
                extension=output_format if output_format != "same" else "jpg"
            )
            
            storage_url = await self.storage_service.store_file(
                file_path=result["output_path"],
                storage_key=storage_key,
                metadata={
                    **result,
                    "job_id": job.job_id,
                    "asset_id": job.asset_id
                }
            )
            
            # Clean up temp file
            if os.path.exists(result["output_path"]):
                os.remove(result["output_path"])
            
            response = {
                "job_id": job.job_id,
                "asset_id": job.asset_id,
                "storage_key": storage_key,
                "storage_url": storage_url,
                "text": result["text"],
                "text_position": result["text_position"],
                "processing_time": result["processing_time"]
            }
            
            logger.info(
                "text_watermark_processed",
                job_id=job.job_id,
                asset_id=job.asset_id,
                processing_time=result["processing_time"]
            )
            
            return response
            
        except Exception as e:
            logger.error(
                "text_watermark_processing_failed",
                error=str(e),
                job_id=job.job_id
            )
            raise ProxyGenerationError(f"Text watermark processing failed: {str(e)}")
    
    async def _process_video_watermark(self, job: ProxyJob) -> Dict[str, Any]:
        """Process video watermarking job"""
        try:
            # Extract parameters
            watermark_path = job.parameters.get("watermark_path")
            position = job.parameters.get("position", "bottom-right")
            scale = job.parameters.get("scale", 0.2)
            opacity = job.parameters.get("opacity", 0.8)
            margin = job.parameters.get("margin", 20)
            video_codec = job.parameters.get("video_codec")
            audio_codec = job.parameters.get("audio_codec", "copy")
            quality_preset = job.parameters.get("quality_preset", "medium")
            
            logger.info(
                "processing_video_watermark",
                job_id=job.job_id,
                asset_id=job.asset_id,
                watermark_path=watermark_path,
                position=position
            )
            
            # Generate output path
            output_path = os.path.join(
                self._temp_dir,
                f"{job.asset_id}_watermarked.mp4"
            )
            
            # Process watermark
            result = await self.ffmpeg_service.add_video_watermark(
                input_path=job.input_path,
                output_path=output_path,
                watermark_path=watermark_path,
                position=position,
                scale=scale,
                opacity=opacity,
                margin=margin,
                video_codec=video_codec,
                audio_codec=audio_codec,
                quality_preset=quality_preset
            )
            
            # Store result
            storage_key = self.storage_service.generate_storage_key(
                asset_id=job.asset_id,
                proxy_type="video_watermarked",
                quality=quality_preset,
                extension="mp4"
            )
            
            storage_url = await self.storage_service.store_file(
                file_path=result["output_path"],
                storage_key=storage_key,
                metadata={
                    **result,
                    "job_id": job.job_id,
                    "asset_id": job.asset_id,
                    "watermark_path": watermark_path
                }
            )
            
            # Clean up temp file
            if os.path.exists(result["output_path"]):
                os.remove(result["output_path"])
            
            response = {
                "job_id": job.job_id,
                "asset_id": job.asset_id,
                "storage_key": storage_key,
                "storage_url": storage_url,
                "duration": result["duration"],
                "file_size": result["file_size"],
                "encoding_time": result["encoding_time"]
            }
            
            logger.info(
                "video_watermark_processed",
                job_id=job.job_id,
                asset_id=job.asset_id,
                encoding_time=result["encoding_time"]
            )
            
            return response
            
        except Exception as e:
            logger.error(
                "video_watermark_processing_failed",
                error=str(e),
                job_id=job.job_id
            )
            raise ProxyGenerationError(f"Video watermark processing failed: {str(e)}")
    
    async def _process_batch_watermark(self, job: ProxyJob) -> Dict[str, Any]:
        """Process batch watermarking job"""
        try:
            # Extract parameters
            images = job.parameters.get("images", [])
            default_watermark_path = job.parameters.get("default_watermark_path")
            default_position = job.parameters.get("default_position", "bottom-right")
            default_opacity = job.parameters.get("default_opacity", 0.8)
            default_scale = job.parameters.get("default_scale", 0.2)
            parallel_workers = job.parameters.get("parallel_workers", 4)
            
            logger.info(
                "processing_batch_watermark",
                job_id=job.job_id,
                batch_size=len(images),
                parallel_workers=parallel_workers
            )
            
            # Process images with watermarking
            results = await self.image_service.batch_watermark(
                images=images,
                default_watermark_path=default_watermark_path,
                default_position=default_position,
                default_opacity=default_opacity,
                default_scale=default_scale,
                parallel_workers=parallel_workers
            )
            
            # Store successful results
            stored_results = []
            successful_count = 0
            failed_count = 0
            
            for result in results:
                if result.get("success"):
                    try:
                        # Store the watermarked image
                        asset_id = result.get("input_path", "").split("/")[-1].split(".")[0]
                        storage_key = self.storage_service.generate_storage_key(
                            asset_id=asset_id,
                            proxy_type="batch_watermarked",
                            quality=result.get("position", default_position),
                            extension=result.get("output_format", "jpg")
                        )
                        
                        storage_url = await self.storage_service.store_file(
                            file_path=result["output_path"],
                            storage_key=storage_key,
                            metadata={
                                **result,
                                "job_id": job.job_id,
                                "batch_job": True
                            }
                        )
                        
                        # Clean up temp file
                        if os.path.exists(result["output_path"]):
                            os.remove(result["output_path"])
                        
                        stored_results.append({
                            "input_path": result["input_path"],
                            "storage_key": storage_key,
                            "storage_url": storage_url,
                            "success": True,
                            "processing_time": result.get("processing_time", 0)
                        })
                        successful_count += 1
                        
                    except Exception as e:
                        logger.error(f"Failed to store watermarked image: {e}")
                        stored_results.append({
                            "input_path": result["input_path"],
                            "success": False,
                            "error": str(e)
                        })
                        failed_count += 1
                else:
                    stored_results.append(result)
                    failed_count += 1
            
            # Calculate total processing time
            total_processing_time = sum(
                r.get("processing_time", 0) for r in stored_results if r.get("success")
            )
            
            # Build response
            response = {
                "job_id": job.job_id,
                "batch_type": "watermark",
                "total_images": len(images),
                "successful": successful_count,
                "failed": failed_count,
                "results": stored_results,
                "total_processing_time": total_processing_time,
                "parallel_workers": parallel_workers
            }
            
            logger.info(
                "batch_watermark_processed",
                job_id=job.job_id,
                total_images=len(images),
                successful=successful_count,
                failed=failed_count,
                processing_time=total_processing_time
            )
            
            return response
            
        except Exception as e:
            logger.error(
                "batch_watermark_processing_failed",
                error=str(e),
                job_id=job.job_id,
                batch_size=len(job.parameters.get("images", []))
            )
            raise ProxyGenerationError(f"Batch watermark processing failed: {str(e)}")
    
    async def _process_8k_proxy(self, job: ProxyJob) -> Dict[str, Any]:
        """Process 8K video proxy generation"""
        temp_output_path = None
        try:
            # Get parameters
            codec = UltraHDCodec(job.parameters.get("codec", "h265"))
            quality = job.parameters.get("quality", "medium")
            resolution = job.parameters.get("resolution")
            enable_hdr = job.parameters.get("enable_hdr", False)
            format_type = job.parameters.get("format", "mp4")
            
            # Convert resolution string to enum if provided
            if resolution and isinstance(resolution, str):
                try:
                    resolution = UltraHDResolution(resolution)
                except ValueError:
                    logger.warning(f"Invalid resolution: {resolution}, using auto-detection")
                    resolution = None
            
            # Validate input
            media_info = await self.ffmpeg_service.get_media_info(job.input_path)
            
            # Check if video stream exists
            has_video = any(s["codec_type"] == "video" for s in media_info["streams"])
            if not has_video:
                raise InvalidMediaError("No video stream found in input file")
            
            # Generate temporary output path
            temp_output_path = os.path.join(
                self._temp_dir,
                f"{job.job_id}_8k_proxy_{quality}.{format_type}"
            )
            
            logger.info(
                "processing_8k_proxy",
                job_id=job.job_id,
                codec=codec.value,
                quality=quality,
                resolution=resolution.value if resolution else "auto",
                enable_hdr=enable_hdr
            )
            
            # Process with Ultra HD service
            result = await self.ultra_hd_service.process_8k_video(
                input_path=job.input_path,
                output_path=temp_output_path,
                codec=codec,
                quality=quality,
                resolution=resolution,
                enable_hdr=enable_hdr,
                **job.parameters.get("advanced_options", {})
            )
            
            # Store in storage backend
            storage_key = self.storage_service.generate_storage_key(
                asset_id=job.asset_id,
                proxy_type="8k_video",
                quality=quality,
                extension=format_type
            )
            
            uploaded_path = await self.storage_service.upload_file(
                local_path=temp_output_path,
                storage_key=storage_key
            )
            
            # Get output file info
            output_size = os.path.getsize(temp_output_path)
            output_info = await self.ultra_hd_service._analyze_video_properties(temp_output_path)
            
            return {
                "job_id": job.job_id,
                "status": JobStatus.COMPLETED,
                "output_path": uploaded_path,
                "storage_key": storage_key,
                "proxy_type": "8k_video",
                "codec": codec.value,
                "quality": quality,
                "resolution": f"{output_info['width']}x{output_info['height']}",
                "file_size_bytes": output_size,
                "processing_method": result["processing_method"],
                "processing_time_seconds": result["processing_time_seconds"],
                "compression_ratio": result.get("compression_ratio", 1.0),
                "gpu_used": result.get("gpu_used", False),
                "enable_hdr": enable_hdr,
                "ultra_hd_details": result
            }
            
        except Exception as e:
            logger.error(
                "8k_proxy_processing_failed",
                error=str(e),
                job_id=job.job_id,
                codec=job.parameters.get("codec", "h265")
            )
            raise ProxyGenerationError(f"8K proxy processing failed: {str(e)}")
        
        finally:
            # Cleanup temp file
            if temp_output_path and os.path.exists(temp_output_path):
                os.remove(temp_output_path)
    
    async def _process_8k_proxy_batch(self, job: ProxyJob) -> Dict[str, Any]:
        """Process multiple 8K proxy profiles in batch"""
        try:
            # Get parameters
            codec = UltraHDCodec(job.parameters.get("codec", "h265"))
            enable_hdr = job.parameters.get("enable_hdr", False)
            format_type = job.parameters.get("format", "mp4")
            output_dir = job.parameters.get("output_dir", self._temp_dir)
            
            logger.info(
                "processing_8k_proxy_batch",
                job_id=job.job_id,
                codec=codec.value,
                enable_hdr=enable_hdr
            )
            
            # Generate multiple proxy profiles
            result = await self.ultra_hd_service.generate_8k_proxy_profiles(
                input_path=job.input_path,
                output_dir=output_dir
            )
            
            # Upload all generated proxies
            uploaded_results = {}
            total_size = 0
            total_processing_time = 0
            
            for profile_name, profile_result in result.items():
                if profile_result["success"]:
                    output_path = profile_result["output_path"]
                    
                    # Generate storage key
                    storage_key = self.storage_service.generate_storage_key(
                        asset_id=job.asset_id,
                        proxy_type=f"8k_batch_{profile_name}",
                        quality="auto",
                        extension=format_type
                    )
                    
                    # Upload to storage
                    uploaded_path = await self.storage_service.upload_file(
                        local_path=output_path,
                        storage_key=storage_key
                    )
                    
                    file_size = os.path.getsize(output_path)
                    total_size += file_size
                    total_processing_time += profile_result["processing_info"]["processing_time_seconds"]
                    
                    uploaded_results[profile_name] = {
                        "success": True,
                        "output_path": uploaded_path,
                        "storage_key": storage_key,
                        "file_size_bytes": file_size,
                        "processing_info": profile_result["processing_info"]
                    }
                    
                    # Cleanup local file
                    if os.path.exists(output_path):
                        os.remove(output_path)
                else:
                    uploaded_results[profile_name] = profile_result
            
            successful_profiles = sum(1 for r in uploaded_results.values() if r.get("success", False))
            
            return {
                "job_id": job.job_id,
                "status": JobStatus.COMPLETED,
                "proxy_type": "8k_batch",
                "profiles_generated": len(result),
                "profiles_successful": successful_profiles,
                "total_file_size_bytes": total_size,
                "total_processing_time_seconds": total_processing_time,
                "codec": codec.value,
                "enable_hdr": enable_hdr,
                "results": uploaded_results
            }
            
        except Exception as e:
            logger.error(
                "8k_proxy_batch_failed",
                error=str(e),
                job_id=job.job_id
            )
            raise ProxyGenerationError(f"8K proxy batch processing failed: {str(e)}")
    
    async def _process_ultra_hd_analysis(self, job: ProxyJob) -> Dict[str, Any]:
        """Analyze Ultra HD video properties and requirements"""
        try:
            logger.info(
                "processing_ultra_hd_analysis",
                job_id=job.job_id
            )
            
            # Analyze video properties
            properties = await self.ultra_hd_service._analyze_video_properties(job.input_path)
            
            # Determine if this is Ultra HD content
            width = properties["width"]
            height = properties["height"]
            
            is_4k = width >= 3840 and height >= 2160
            is_8k = width >= 7680 and height >= 4320
            
            # Check for HDR characteristics
            has_hdr = (
                properties.get("color_space") == "bt2020nc" or
                properties.get("color_primaries") == "bt2020" or
                properties.get("color_transfer") in ["smpte2084", "arib-std-b67"]
            )
            
            # Assess processing requirements
            file_size_gb = os.path.getsize(job.input_path) / (1024**3)
            duration_minutes = properties["duration"] / 60
            
            # Calculate processing estimates
            processing_capabilities = self.ultra_hd_service.processing_capabilities
            
            if is_8k:
                estimated_time = duration_minutes * 4  # 4x real-time for 8K
                memory_required = processing_capabilities["memory_per_stream_8k"]
                recommended_method = "tiled" if duration_minutes > 5 else "standard"
            elif is_4k:
                estimated_time = duration_minutes * 2  # 2x real-time for 4K
                memory_required = processing_capabilities["memory_per_stream_4k"]
                recommended_method = "chunked" if duration_minutes > 10 else "standard"
            else:
                estimated_time = duration_minutes * 0.5  # 0.5x real-time for HD
                memory_required = 4
                recommended_method = "standard"
            
            # Codec recommendations
            codec_recommendations = []
            if is_8k or is_4k:
                codec_recommendations.extend([
                    {"codec": "h265", "reason": "Best compression efficiency for UHD"},
                    {"codec": "av1", "reason": "Future-proof codec with excellent compression"}
                ])
                if has_hdr:
                    codec_recommendations.append({
                        "codec": "h265", 
                        "reason": "Native HDR support with Main10 profile"
                    })
            else:
                codec_recommendations.append({
                    "codec": "h264", 
                    "reason": "Broad compatibility for standard HD content"
                })
            
            return {
                "job_id": job.job_id,
                "status": JobStatus.COMPLETED,
                "analysis_type": "ultra_hd_analysis",
                "video_properties": properties,
                "ultra_hd_classification": {
                    "is_4k": is_4k,
                    "is_8k": is_8k,
                    "is_ultra_hd": is_4k or is_8k,
                    "has_hdr": has_hdr,
                    "resolution_category": "8K" if is_8k else "4K" if is_4k else "HD"
                },
                "file_info": {
                    "size_gb": round(file_size_gb, 2),
                    "duration_minutes": round(duration_minutes, 2),
                    "bitrate_mbps": round(properties["bitrate"] / 1_000_000, 2)
                },
                "processing_assessment": {
                    "can_process": processing_capabilities["can_process_8k"] if is_8k else True,
                    "optimal_performance": processing_capabilities["optimal_8k_performance"] if is_8k else True,
                    "estimated_processing_time_minutes": round(estimated_time, 2),
                    "memory_required_gb": memory_required,
                    "recommended_method": recommended_method,
                    "system_capabilities": processing_capabilities
                },
                "codec_recommendations": codec_recommendations,
                "proxy_suggestions": [
                    {"type": "8k_preview", "codec": "h265", "quality": "low"},
                    {"type": "4k_proxy", "codec": "h265", "quality": "medium"},
                    {"type": "2k_proxy", "codec": "h264", "quality": "medium"},
                    {"type": "1080p_proxy", "codec": "h264", "quality": "high"}
                ] if is_8k else [
                    {"type": "4k_preview", "codec": "h265", "quality": "low"},
                    {"type": "2k_proxy", "codec": "h264", "quality": "medium"},
                    {"type": "1080p_proxy", "codec": "h264", "quality": "high"}
                ] if is_4k else [
                    {"type": "1080p_proxy", "codec": "h264", "quality": "high"},
                    {"type": "720p_proxy", "codec": "h264", "quality": "medium"}
                ]
            }
            
        except Exception as e:
            logger.error(
                "ultra_hd_analysis_failed",
                error=str(e),
                job_id=job.job_id
            )
            raise ProxyGenerationError(f"Ultra HD analysis failed: {str(e)}")
    
    async def _process_hdr_processing(self, job: ProxyJob) -> Dict[str, Any]:
        """Process HDR video content with tone mapping options"""
        temp_output_path = None
        try:
            # Get parameters
            tone_mapping = job.parameters.get("tone_mapping", "none")  # none, hable, reinhard, mobius
            target_nits = job.parameters.get("target_nits", 100)  # Target luminance
            preserve_hdr = job.parameters.get("preserve_hdr", True)
            output_format = job.parameters.get("format", "mp4")
            
            logger.info(
                "processing_hdr_video",
                job_id=job.job_id,
                tone_mapping=tone_mapping,
                target_nits=target_nits,
                preserve_hdr=preserve_hdr
            )
            
            # Analyze input for HDR characteristics
            properties = await self.ultra_hd_service._analyze_video_properties(job.input_path)
            
            has_hdr = (
                properties.get("color_space") == "bt2020nc" or
                properties.get("color_primaries") == "bt2020" or
                properties.get("color_transfer") in ["smpte2084", "arib-std-b67"]
            )
            
            if not has_hdr:
                logger.warning(f"Input video does not appear to be HDR content: {job.job_id}")
            
            # Generate temporary output path
            temp_output_path = os.path.join(
                self._temp_dir,
                f"{job.job_id}_hdr_{tone_mapping}.{output_format}"
            )
            
            # Build HDR processing command
            cmd = [self.ffmpeg_service.ffmpeg_path, "-i", job.input_path]
            
            # Add HDR processing filters
            video_filters = []
            
            if tone_mapping != "none" and not preserve_hdr:
                # Tone mapping for SDR output
                if tone_mapping == "hable":
                    video_filters.append(f"zscale=t=linear:npl={target_nits}")
                    video_filters.append("format=gbrpf32le")
                    video_filters.append("zscale=p=bt709:t=bt709:m=bt709:r=tv")
                    video_filters.append("format=yuv420p")
                elif tone_mapping == "reinhard":
                    video_filters.append(f"tonemap=tonemap=reinhard:param=0.5:desat=0")
                elif tone_mapping == "mobius":
                    video_filters.append(f"tonemap=tonemap=mobius:param=0.3:desat=0")
                
                # Color space conversion to SDR
                cmd.extend([
                    "-colorspace", "bt709",
                    "-color_primaries", "bt709",
                    "-color_trc", "bt709"
                ])
            
            elif preserve_hdr:
                # Preserve HDR metadata
                cmd.extend([
                    "-colorspace", "bt2020nc",
                    "-color_primaries", "bt2020",
                    "-color_trc", properties.get("color_transfer", "smpte2084")
                ])
            
            # Apply video filters if any
            if video_filters:
                cmd.extend(["-vf", ",".join(video_filters)])
            
            # Codec selection based on HDR requirements
            if preserve_hdr:
                cmd.extend(["-c:v", "libx265", "-profile:v", "main10"])
            else:
                cmd.extend(["-c:v", "libx264", "-profile:v", "high"])
            
            # Audio copy
            cmd.extend(["-c:a", "copy"])
            
            # Output
            cmd.append(temp_output_path)
            
            # Execute processing
            start_time = datetime.now()
            await self.ffmpeg_service.run_ffmpeg_command(cmd)
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Store result
            storage_key = self.storage_service.generate_storage_key(
                asset_id=job.asset_id,
                proxy_type="hdr_processed",
                quality=tone_mapping,
                extension=output_format
            )
            
            uploaded_path = await self.storage_service.upload_file(
                local_path=temp_output_path,
                storage_key=storage_key
            )
            
            # Get output info
            output_size = os.path.getsize(temp_output_path)
            output_properties = await self.ultra_hd_service._analyze_video_properties(temp_output_path)
            
            return {
                "job_id": job.job_id,
                "status": JobStatus.COMPLETED,
                "output_path": uploaded_path,
                "storage_key": storage_key,
                "proxy_type": "hdr_processed",
                "tone_mapping": tone_mapping,
                "target_nits": target_nits,
                "preserve_hdr": preserve_hdr,
                "input_hdr_detected": has_hdr,
                "file_size_bytes": output_size,
                "processing_time_seconds": processing_time,
                "input_properties": properties,
                "output_properties": output_properties
            }
            
        except Exception as e:
            logger.error(
                "hdr_processing_failed",
                error=str(e),
                job_id=job.job_id,
                tone_mapping=job.parameters.get("tone_mapping", "none")
            )
            raise ProxyGenerationError(f"HDR processing failed: {str(e)}")
        
        finally:
            # Cleanup temp file
            if temp_output_path and os.path.exists(temp_output_path):
                os.remove(temp_output_path)
    
    async def _process_hdr_analysis(self, job: ProxyJob) -> Dict[str, Any]:
        """Analyze HDR characteristics of video content"""
        try:
            logger.info(
                "processing_hdr_analysis",
                job_id=job.job_id
            )
            
            # Analyze HDR content
            analysis = await self.hdr_service.analyze_hdr_content(job.input_path)
            
            # Get file info
            file_size_gb = os.path.getsize(job.input_path) / (1024**3)
            
            return {
                "job_id": job.job_id,
                "status": JobStatus.COMPLETED,
                "analysis_type": "hdr_analysis",
                "hdr_analysis": analysis,
                "file_info": {
                    "size_gb": round(file_size_gb, 2),
                    "path": job.input_path
                },
                "processing_capabilities": await self.hdr_service.get_hdr_processing_capabilities()
            }
            
        except Exception as e:
            logger.error(
                "hdr_analysis_failed",
                error=str(e),
                job_id=job.job_id
            )
            raise ProxyGenerationError(f"HDR analysis failed: {str(e)}")
    
    async def _process_hdr_to_sdr(self, job: ProxyJob) -> Dict[str, Any]:
        """Convert HDR content to SDR"""
        temp_output_path = None
        try:
            # Get parameters
            tone_mapping = ToneMappingAlgorithm(job.parameters.get("tone_mapping", "hable"))
            target_nits = job.parameters.get("target_nits", 100)
            preserve_colors = job.parameters.get("preserve_colors", True)
            output_format = job.parameters.get("format", "mp4")
            
            logger.info(
                "processing_hdr_to_sdr",
                job_id=job.job_id,
                tone_mapping=tone_mapping.value,
                target_nits=target_nits
            )
            
            # Generate temporary output path
            temp_output_path = os.path.join(
                self._temp_dir,
                f"{job.job_id}_hdr_to_sdr_{tone_mapping.value}.{output_format}"
            )
            
            # Process with HDR service
            result = await self.hdr_service.convert_hdr_to_sdr(
                input_path=job.input_path,
                output_path=temp_output_path,
                tone_mapping=tone_mapping,
                target_nits=target_nits,
                preserve_colors=preserve_colors,
                **job.parameters.get("advanced_options", {})
            )
            
            # Store in storage backend
            storage_key = self.storage_service.generate_storage_key(
                asset_id=job.asset_id,
                proxy_type="hdr_to_sdr",
                quality=tone_mapping.value,
                extension=output_format
            )
            
            uploaded_path = await self.storage_service.upload_file(
                local_path=temp_output_path,
                storage_key=storage_key
            )
            
            # Get output file info
            output_size = os.path.getsize(temp_output_path)
            
            return {
                "job_id": job.job_id,
                "status": JobStatus.COMPLETED,
                "output_path": uploaded_path,
                "storage_key": storage_key,
                "proxy_type": "hdr_to_sdr",
                "tone_mapping": tone_mapping.value,
                "target_nits": target_nits,
                "preserve_colors": preserve_colors,
                "file_size_bytes": output_size,
                "processing_result": result
            }
            
        except Exception as e:
            logger.error(
                "hdr_to_sdr_failed",
                error=str(e),
                job_id=job.job_id
            )
            raise ProxyGenerationError(f"HDR to SDR conversion failed: {str(e)}")
        
        finally:
            # Cleanup temp file
            if temp_output_path and os.path.exists(temp_output_path):
                os.remove(temp_output_path)
    
    async def _process_sdr_to_hdr(self, job: ProxyJob) -> Dict[str, Any]:
        """Convert SDR content to HDR (upconversion)"""
        temp_output_path = None
        try:
            # Get parameters
            target_standard = HDRStandard(job.parameters.get("target_standard", "hdr10"))
            peak_luminance = job.parameters.get("peak_luminance", 1000)
            output_format = job.parameters.get("format", "mp4")
            
            logger.info(
                "processing_sdr_to_hdr",
                job_id=job.job_id,
                target_standard=target_standard.value,
                peak_luminance=peak_luminance
            )
            
            # Generate temporary output path
            temp_output_path = os.path.join(
                self._temp_dir,
                f"{job.job_id}_sdr_to_hdr_{target_standard.value}.{output_format}"
            )
            
            # Process with HDR service
            result = await self.hdr_service.convert_sdr_to_hdr(
                input_path=job.input_path,
                output_path=temp_output_path,
                target_standard=target_standard,
                peak_luminance=peak_luminance,
                **job.parameters.get("advanced_options", {})
            )
            
            # Store in storage backend
            storage_key = self.storage_service.generate_storage_key(
                asset_id=job.asset_id,
                proxy_type="sdr_to_hdr",
                quality=target_standard.value,
                extension=output_format
            )
            
            uploaded_path = await self.storage_service.upload_file(
                local_path=temp_output_path,
                storage_key=storage_key
            )
            
            # Get output file info
            output_size = os.path.getsize(temp_output_path)
            
            return {
                "job_id": job.job_id,
                "status": JobStatus.COMPLETED,
                "output_path": uploaded_path,
                "storage_key": storage_key,
                "proxy_type": "sdr_to_hdr",
                "target_standard": target_standard.value,
                "peak_luminance": peak_luminance,
                "file_size_bytes": output_size,
                "processing_result": result
            }
            
        except Exception as e:
            logger.error(
                "sdr_to_hdr_failed",
                error=str(e),
                job_id=job.job_id
            )
            raise ProxyGenerationError(f"SDR to HDR conversion failed: {str(e)}")
        
        finally:
            # Cleanup temp file
            if temp_output_path and os.path.exists(temp_output_path):
                os.remove(temp_output_path)
    
    async def _process_hdr_delivery_optimization(self, job: ProxyJob) -> Dict[str, Any]:
        """Create optimized HDR delivery versions"""
        try:
            # Get parameters
            create_sdr_version = job.parameters.get("create_sdr_version", True)
            create_mobile_version = job.parameters.get("create_mobile_version", True)
            output_dir = job.parameters.get("output_dir", self._temp_dir)
            
            logger.info(
                "processing_hdr_delivery_optimization",
                job_id=job.job_id,
                create_sdr_version=create_sdr_version,
                create_mobile_version=create_mobile_version
            )
            
            # Process with HDR service
            result = await self.hdr_service.optimize_hdr_delivery(
                input_path=job.input_path,
                output_dir=output_dir,
                create_sdr_version=create_sdr_version,
                create_mobile_version=create_mobile_version,
                **job.parameters.get("advanced_options", {})
            )
            
            # Upload all generated versions
            uploaded_results = {}
            total_size = 0
            
            for version_name, version_info in result["delivery_versions"].items():
                version_path = version_info["path"]
                
                # Generate storage key
                storage_key = self.storage_service.generate_storage_key(
                    asset_id=job.asset_id,
                    proxy_type=f"hdr_delivery_{version_name}",
                    quality="optimized",
                    extension="mp4"
                )
                
                # Upload to storage
                uploaded_path = await self.storage_service.upload_file(
                    local_path=version_path,
                    storage_key=storage_key
                )
                
                file_size = os.path.getsize(version_path)
                total_size += file_size
                
                uploaded_results[version_name] = {
                    "output_path": uploaded_path,
                    "storage_key": storage_key,
                    "file_size_bytes": file_size,
                    "processing_info": version_info["result"]
                }
                
                # Cleanup local file
                if os.path.exists(version_path):
                    os.remove(version_path)
            
            return {
                "job_id": job.job_id,
                "status": JobStatus.COMPLETED,
                "proxy_type": "hdr_delivery_optimization",
                "total_versions": result["total_versions"],
                "total_file_size_bytes": total_size,
                "input_analysis": result["input_analysis"],
                "delivery_versions": uploaded_results
            }
            
        except Exception as e:
            logger.error(
                "hdr_delivery_optimization_failed",
                error=str(e),
                job_id=job.job_id
            )
            raise ProxyGenerationError(f"HDR delivery optimization failed: {str(e)}")
    
    async def _process_spherical_analysis(self, job: ProxyJob) -> Dict[str, Any]:
        """Analyze 360° video characteristics"""
        try:
            logger.info(
                "processing_spherical_analysis",
                job_id=job.job_id
            )
            
            # Analyze spherical content
            analysis = await self.spherical_service.analyze_spherical_video(job.input_path)
            
            # Get file info
            file_size_gb = os.path.getsize(job.input_path) / (1024**3)
            
            return {
                "job_id": job.job_id,
                "status": JobStatus.COMPLETED,
                "analysis_type": "spherical_analysis",
                "spherical_analysis": analysis,
                "file_info": {
                    "size_gb": round(file_size_gb, 2),
                    "path": job.input_path
                },
                "processing_capabilities": await self.spherical_service.get_spherical_capabilities()
            }
            
        except Exception as e:
            logger.error(
                "spherical_analysis_failed",
                error=str(e),
                job_id=job.job_id
            )
            raise ProxyGenerationError(f"Spherical analysis failed: {str(e)}")
    
    async def _process_spherical_conversion(self, job: ProxyJob) -> Dict[str, Any]:
        """Convert between spherical projections"""
        temp_output_path = None
        try:
            # Get parameters
            input_projection = SphericalProjection(job.parameters.get("input_projection", "equirectangular"))
            output_projection = SphericalProjection(job.parameters.get("output_projection", "cubemap"))
            stereo_mode = SphericalStereoMode(job.parameters.get("stereo_mode", "mono"))
            output_format = job.parameters.get("format", "mp4")
            
            logger.info(
                "processing_spherical_conversion",
                job_id=job.job_id,
                input_projection=input_projection.value,
                output_projection=output_projection.value,
                stereo_mode=stereo_mode.value
            )
            
            # Generate temporary output path
            temp_output_path = os.path.join(
                self._temp_dir,
                f"{job.job_id}_spherical_{output_projection.value}.{output_format}"
            )
            
            # Process with spherical service
            result = await self.spherical_service.convert_spherical_projection(
                input_path=job.input_path,
                output_path=temp_output_path,
                input_projection=input_projection,
                output_projection=output_projection,
                stereo_mode=stereo_mode,
                **job.parameters.get("advanced_options", {})
            )
            
            # Store in storage backend
            storage_key = self.storage_service.generate_storage_key(
                asset_id=job.asset_id,
                proxy_type="spherical_converted",
                quality=output_projection.value,
                extension=output_format
            )
            
            uploaded_path = await self.storage_service.upload_file(
                local_path=temp_output_path,
                storage_key=storage_key
            )
            
            # Get output file info
            output_size = os.path.getsize(temp_output_path)
            
            return {
                "job_id": job.job_id,
                "status": JobStatus.COMPLETED,
                "output_path": uploaded_path,
                "storage_key": storage_key,
                "proxy_type": "spherical_converted",
                "input_projection": input_projection.value,
                "output_projection": output_projection.value,
                "stereo_mode": stereo_mode.value,
                "file_size_bytes": output_size,
                "processing_result": result
            }
            
        except Exception as e:
            logger.error(
                "spherical_conversion_failed",
                error=str(e),
                job_id=job.job_id
            )
            raise ProxyGenerationError(f"Spherical conversion failed: {str(e)}")
        
        finally:
            # Cleanup temp file
            if temp_output_path and os.path.exists(temp_output_path):
                os.remove(temp_output_path)
    
    async def _process_vr_optimization(self, job: ProxyJob) -> Dict[str, Any]:
        """Create VR-optimized versions for different headsets"""
        try:
            # Get parameters
            target_headsets = job.parameters.get("target_headsets", ["generic"])
            target_headsets = [VRHeadset(h) for h in target_headsets]
            output_dir = job.parameters.get("output_dir", self._temp_dir)
            
            logger.info(
                "processing_vr_optimization",
                job_id=job.job_id,
                target_headsets=[h.value for h in target_headsets]
            )
            
            # Process with spherical service
            result = await self.spherical_service.create_vr_optimized_versions(
                input_path=job.input_path,
                output_dir=output_dir,
                target_headsets=target_headsets,
                **job.parameters.get("advanced_options", {})
            )
            
            # Upload all generated versions
            uploaded_results = {}
            total_size = 0
            
            for headset_name, headset_versions in result["headset_versions"].items():
                uploaded_headset = {}
                
                for quality_name, version_info in headset_versions.items():
                    version_path = version_info["path"]
                    
                    # Generate storage key
                    storage_key = self.storage_service.generate_storage_key(
                        asset_id=job.asset_id,
                        proxy_type=f"vr_{headset_name}_{quality_name}",
                        quality="optimized",
                        extension="mp4"
                    )
                    
                    # Upload to storage
                    uploaded_path = await self.storage_service.upload_file(
                        local_path=version_path,
                        storage_key=storage_key
                    )
                    
                    file_size = os.path.getsize(version_path)
                    total_size += file_size
                    
                    uploaded_headset[quality_name] = {
                        "output_path": uploaded_path,
                        "storage_key": storage_key,
                        "file_size_bytes": file_size,
                        "settings": version_info["settings"],
                        "processing_info": version_info["result"]
                    }
                    
                    # Cleanup local file
                    if os.path.exists(version_path):
                        os.remove(version_path)
                
                uploaded_results[headset_name] = uploaded_headset
            
            return {
                "job_id": job.job_id,
                "status": JobStatus.COMPLETED,
                "proxy_type": "vr_optimization",
                "total_versions": result["total_versions"],
                "total_file_size_bytes": total_size,
                "input_analysis": result["input_analysis"],
                "headset_versions": uploaded_results
            }
            
        except Exception as e:
            logger.error(
                "vr_optimization_failed",
                error=str(e),
                job_id=job.job_id
            )
            raise ProxyGenerationError(f"VR optimization failed: {str(e)}")
    
    async def _process_spatial_metadata(self, job: ProxyJob) -> Dict[str, Any]:
        """Add spatial media metadata to video"""
        temp_output_path = None
        try:
            # Get parameters
            projection = SphericalProjection(job.parameters.get("projection", "equirectangular"))
            stereo_mode = SphericalStereoMode(job.parameters.get("stereo_mode", "mono"))
            output_format = job.parameters.get("format", "mp4")
            
            logger.info(
                "processing_spatial_metadata",
                job_id=job.job_id,
                projection=projection.value,
                stereo_mode=stereo_mode.value
            )
            
            # Generate temporary output path
            temp_output_path = os.path.join(
                self._temp_dir,
                f"{job.job_id}_spatial_metadata.{output_format}"
            )
            
            # Process with spherical service
            result = await self.spherical_service.add_spatial_metadata(
                input_path=job.input_path,
                output_path=temp_output_path,
                projection=projection,
                stereo_mode=stereo_mode,
                **job.parameters.get("metadata_options", {})
            )
            
            # Store in storage backend
            storage_key = self.storage_service.generate_storage_key(
                asset_id=job.asset_id,
                proxy_type="spatial_metadata",
                quality=projection.value,
                extension=output_format
            )
            
            uploaded_path = await self.storage_service.upload_file(
                local_path=temp_output_path,
                storage_key=storage_key
            )
            
            # Get output file info
            output_size = os.path.getsize(temp_output_path)
            
            return {
                "job_id": job.job_id,
                "status": JobStatus.COMPLETED,
                "output_path": uploaded_path,
                "storage_key": storage_key,
                "proxy_type": "spatial_metadata",
                "projection": projection.value,
                "stereo_mode": stereo_mode.value,
                "file_size_bytes": output_size,
                "processing_result": result
            }
            
        except Exception as e:
            logger.error(
                "spatial_metadata_failed",
                error=str(e),
                job_id=job.job_id
            )
            raise ProxyGenerationError(f"Spatial metadata processing failed: {str(e)}")
        
        finally:
            # Cleanup temp file
            if temp_output_path and os.path.exists(temp_output_path):
                os.remove(temp_output_path)
    
    async def _process_vr_content_analysis(self, job: ProxyJob) -> Dict[str, Any]:
        """Analyze VR content characteristics"""
        try:
            # Perform VR content analysis
            analysis_result = await self.vr_content_service.analyze_vr_content(
                input_path=job.input_path
            )
            
            return {
                "job_id": job.job_id,
                "status": JobStatus.COMPLETED,
                "asset_id": job.asset_id,
                "analysis_type": "vr_content",
                "content_type": analysis_result["content_type"],
                "render_mode": analysis_result["render_mode"],
                "interaction_mode": analysis_result["interaction_mode"],
                "vr_metadata": analysis_result["vr_metadata"],
                "platform_recommendations": analysis_result["platform_recommendations"],
                "original_properties": analysis_result["original_properties"]
            }
            
        except Exception as e:
            logger.error(
                "vr_content_analysis_failed",
                error=str(e),
                job_id=job.job_id
            )
            raise ProxyGenerationError(f"VR content analysis failed: {str(e)}")
    
    async def _process_vr_content_processing(self, job: ProxyJob) -> Dict[str, Any]:
        """Process VR content for specific platform"""
        temp_output_path = None
        try:
            # Get parameters
            platform_str = job.parameters.get("platform", "oculus_quest")
            platform = VRPlatform(platform_str)
            preset = job.parameters.get("preset", "vr_high")
            custom_params = job.parameters.get("custom_params", {})
            
            # Generate output path
            temp_output_path = os.path.join(
                self._temp_dir,
                f"{job.job_id}_vr_{platform_str}.mp4"
            )
            
            # Process VR content
            result = await self.vr_content_service.process_vr_content(
                input_path=job.input_path,
                output_path=temp_output_path,
                platform=platform,
                preset=preset,
                custom_params=custom_params
            )
            
            # Store in storage backend
            storage_key = self.storage_service.generate_storage_key(
                asset_id=job.asset_id,
                proxy_type="vr_content",
                quality=f"{platform_str}_{preset}",
                extension="mp4"
            )
            
            storage_url = await self.storage_service.store_file(
                file_path=temp_output_path,
                storage_key=storage_key,
                metadata={
                    **result,
                    "job_id": job.job_id,
                    "asset_id": job.asset_id
                }
            )
            
            return {
                "job_id": job.job_id,
                "status": JobStatus.COMPLETED,
                "asset_id": job.asset_id,
                "storage_key": storage_key,
                "storage_url": storage_url,
                "platform": result["platform"],
                "preset": result["preset"],
                "output_resolution": result["output_resolution"],
                "output_fps": result["output_fps"],
                "output_bitrate": result["output_bitrate"],
                "processing_time": result["processing_time"],
                "file_size": result["file_size"]
            }
            
        except Exception as e:
            logger.error(
                "vr_content_processing_failed",
                error=str(e),
                job_id=job.job_id
            )
            raise ProxyGenerationError(f"VR content processing failed: {str(e)}")
        
        finally:
            # Cleanup temp file
            if temp_output_path and os.path.exists(temp_output_path):
                os.remove(temp_output_path)
    
    async def _process_vr_preview(self, job: ProxyJob) -> Dict[str, Any]:
        """Create VR preview for non-VR displays"""
        temp_output_path = None
        try:
            # Get parameters
            preview_type = job.parameters.get("preview_type", "flat")
            duration = job.parameters.get("duration", 30)
            
            # Generate output path
            temp_output_path = os.path.join(
                self._temp_dir,
                f"{job.job_id}_vr_preview_{preview_type}.mp4"
            )
            
            # Create VR preview
            result = await self.vr_content_service.create_vr_preview(
                input_path=job.input_path,
                output_path=temp_output_path,
                preview_type=preview_type,
                duration=duration
            )
            
            # Store in storage backend
            storage_key = self.storage_service.generate_storage_key(
                asset_id=job.asset_id,
                proxy_type="vr_preview",
                quality=preview_type,
                extension="mp4"
            )
            
            storage_url = await self.storage_service.store_file(
                file_path=temp_output_path,
                storage_key=storage_key,
                metadata={
                    **result,
                    "job_id": job.job_id,
                    "asset_id": job.asset_id
                }
            )
            
            return {
                "job_id": job.job_id,
                "status": JobStatus.COMPLETED,
                "asset_id": job.asset_id,
                "storage_key": storage_key,
                "storage_url": storage_url,
                "preview_type": result["preview_type"],
                "duration": result["duration"],
                "file_size": result["file_size"]
            }
            
        except Exception as e:
            logger.error(
                "vr_preview_failed",
                error=str(e),
                job_id=job.job_id
            )
            raise ProxyGenerationError(f"VR preview creation failed: {str(e)}")
        
        finally:
            # Cleanup temp file
            if temp_output_path and os.path.exists(temp_output_path):
                os.remove(temp_output_path)
    
    async def _process_vr_motion_extraction(self, job: ProxyJob) -> Dict[str, Any]:
        """Extract motion and tracking data from VR content"""
        try:
            # Extract VR motion data
            motion_data = await self.vr_content_service.extract_vr_motion_data(
                input_path=job.input_path
            )
            
            return {
                "job_id": job.job_id,
                "status": JobStatus.COMPLETED,
                "asset_id": job.asset_id,
                "motion_data": motion_data,
                "has_head_tracking": len(motion_data["head_tracking"]) > 0,
                "has_controller_tracking": len(motion_data["controller_tracking"]) > 0,
                "has_eye_tracking": len(motion_data["eye_tracking"]) > 0,
                "has_body_tracking": len(motion_data["body_tracking"]) > 0
            }
            
        except Exception as e:
            logger.error(
                "vr_motion_extraction_failed",
                error=str(e),
                job_id=job.job_id
            )
            raise ProxyGenerationError(f"VR motion extraction failed: {str(e)}")
    
    async def _process_vr_streaming_optimization(self, job: ProxyJob) -> Dict[str, Any]:
        """Optimize VR content for streaming"""
        temp_output_base = None
        try:
            # Get parameters
            streaming_type = job.parameters.get("streaming_type", "adaptive")
            
            # Generate output path
            temp_output_base = os.path.join(
                self._temp_dir,
                f"{job.job_id}_vr_streaming"
            )
            
            # Optimize for streaming
            result = await self.vr_content_service.optimize_for_streaming(
                input_path=job.input_path,
                output_path=temp_output_base + ".mp4",
                streaming_type=streaming_type
            )
            
            # Store results based on streaming type
            if streaming_type == "adaptive":
                storage_urls = []
                for quality_level in result["quality_levels"]:
                    storage_key = self.storage_service.generate_storage_key(
                        asset_id=job.asset_id,
                        proxy_type="vr_streaming",
                        quality=f"{streaming_type}_{quality_level['resolution']}",
                        extension="mp4"
                    )
                    
                    storage_url = await self.storage_service.store_file(
                        file_path=quality_level["path"],
                        storage_key=storage_key,
                        metadata={
                            "job_id": job.job_id,
                            "asset_id": job.asset_id,
                            "resolution": quality_level["resolution"],
                            "bitrate": quality_level["bitrate"]
                        }
                    )
                    
                    storage_urls.append({
                        "storage_key": storage_key,
                        "storage_url": storage_url,
                        "resolution": quality_level["resolution"],
                        "bitrate": quality_level["bitrate"]
                    })
                    
                    # Clean up temp file
                    if os.path.exists(quality_level["path"]):
                        os.remove(quality_level["path"])
                
                return {
                    "job_id": job.job_id,
                    "status": JobStatus.COMPLETED,
                    "asset_id": job.asset_id,
                    "streaming_type": streaming_type,
                    "quality_levels": storage_urls
                }
            else:
                # Single output file
                storage_key = self.storage_service.generate_storage_key(
                    asset_id=job.asset_id,
                    proxy_type="vr_streaming",
                    quality=streaming_type,
                    extension="mp4"
                )
                
                storage_url = await self.storage_service.store_file(
                    file_path=result["output_path"],
                    storage_key=storage_key,
                    metadata={
                        **result,
                        "job_id": job.job_id,
                        "asset_id": job.asset_id
                    }
                )
                
                # Clean up temp file
                if os.path.exists(result["output_path"]):
                    os.remove(result["output_path"])
                
                return {
                    "job_id": job.job_id,
                    "status": JobStatus.COMPLETED,
                    "asset_id": job.asset_id,
                    "storage_key": storage_key,
                    "storage_url": storage_url,
                    "streaming_type": streaming_type,
                    "optimizations": result.get("optimizations", [])
                }
                
        except Exception as e:
            logger.error(
                "vr_streaming_optimization_failed",
                error=str(e),
                job_id=job.job_id
            )
            raise ProxyGenerationError(f"VR streaming optimization failed: {str(e)}")
    
    async def _process_vr_thumbnail_sequence(self, job: ProxyJob) -> Dict[str, Any]:
        """Create VR thumbnail sequence"""
        temp_output_dir = None
        try:
            # Get parameters
            count = job.parameters.get("count", 12)
            preview_angles = job.parameters.get("preview_angles")
            
            # Create output directory
            temp_output_dir = os.path.join(
                self._temp_dir,
                f"{job.job_id}_vr_thumbnails"
            )
            
            # Create thumbnail sequence
            result = await self.vr_content_service.create_vr_thumbnail_sequence(
                input_path=job.input_path,
                output_dir=temp_output_dir,
                count=count,
                preview_angles=preview_angles
            )
            
            # Store thumbnails
            storage_urls = []
            for thumbnail in result["thumbnails"]:
                storage_key = self.storage_service.generate_storage_key(
                    asset_id=job.asset_id,
                    proxy_type="vr_thumbnail",
                    quality=f"angle_{thumbnail['index']}",
                    extension="jpg"
                )
                
                storage_url = await self.storage_service.store_file(
                    file_path=thumbnail["path"],
                    storage_key=storage_key,
                    metadata={
                        "job_id": job.job_id,
                        "asset_id": job.asset_id,
                        "yaw": thumbnail["yaw"],
                        "pitch": thumbnail["pitch"],
                        "index": thumbnail["index"]
                    }
                )
                
                storage_urls.append({
                    "storage_key": storage_key,
                    "storage_url": storage_url,
                    "yaw": thumbnail["yaw"],
                    "pitch": thumbnail["pitch"],
                    "index": thumbnail["index"]
                })
            
            return {
                "job_id": job.job_id,
                "status": JobStatus.COMPLETED,
                "asset_id": job.asset_id,
                "count": result["count"],
                "thumbnails": storage_urls
            }
            
        except Exception as e:
            logger.error(
                "vr_thumbnail_sequence_failed",
                error=str(e),
                job_id=job.job_id
            )
            raise ProxyGenerationError(f"VR thumbnail sequence creation failed: {str(e)}")
        
        finally:
            # Cleanup temp directory
            if temp_output_dir and os.path.exists(temp_output_dir):
                import shutil
                shutil.rmtree(temp_output_dir)
    
    async def _process_spatial_audio_analysis(self, job: ProxyJob) -> Dict[str, Any]:
        """Analyze spatial audio characteristics"""
        try:
            # Perform spatial audio analysis
            analysis_result = await self.spatial_audio_service.analyze_spatial_audio(
                input_path=job.input_path
            )
            
            return {
                "job_id": job.job_id,
                "status": JobStatus.COMPLETED,
                "asset_id": job.asset_id,
                "analysis_type": "spatial_audio",
                "format": analysis_result["format"],
                "channels": analysis_result["channels"],
                "channel_layout": analysis_result["channel_layout"],
                "sample_rate": analysis_result["sample_rate"],
                "bit_depth": analysis_result["bit_depth"],
                "duration": analysis_result["duration"],
                "channel_configuration": analysis_result["channel_configuration"],
                "has_object_metadata": analysis_result["has_object_metadata"],
                "object_metadata": analysis_result["object_metadata"],
                "spatial_analysis": analysis_result["spatial_analysis"]
            }
            
        except Exception as e:
            logger.error(
                "spatial_audio_analysis_failed",
                error=str(e),
                job_id=job.job_id
            )
            raise ProxyGenerationError(f"Spatial audio analysis failed: {str(e)}")
    
    async def _process_spatial_audio_conversion(self, job: ProxyJob) -> Dict[str, Any]:
        """Convert audio to spatial format"""
        temp_output_path = None
        try:
            # Get parameters
            target_format_str = job.parameters.get("target_format", "5.1")
            target_format = SpatialAudioFormat(target_format_str)
            codec = job.parameters.get("codec")
            custom_params = job.parameters.get("custom_params", {})
            
            # Generate output path
            temp_output_path = os.path.join(
                self._temp_dir,
                f"{job.job_id}_spatial_{target_format_str.replace('.', '_')}.mp4"
            )
            
            # Convert audio
            result = await self.spatial_audio_service.convert_to_spatial_format(
                input_path=job.input_path,
                output_path=temp_output_path,
                target_format=target_format,
                codec=codec,
                custom_params=custom_params
            )
            
            # Store in storage backend
            storage_key = self.storage_service.generate_storage_key(
                asset_id=job.asset_id,
                proxy_type="spatial_audio",
                quality=target_format_str.replace('.', '_'),
                extension="mp4"
            )
            
            storage_url = await self.storage_service.store_file(
                file_path=temp_output_path,
                storage_key=storage_key,
                metadata={
                    **result,
                    "job_id": job.job_id,
                    "asset_id": job.asset_id
                }
            )
            
            return {
                "job_id": job.job_id,
                "status": JobStatus.COMPLETED,
                "asset_id": job.asset_id,
                "storage_key": storage_key,
                "storage_url": storage_url,
                "target_format": result["target_format"],
                "codec": result["codec"],
                "output_channels": result["output_channels"],
                "output_layout": result["output_layout"],
                "sample_rate": result["sample_rate"],
                "processing_time": result["processing_time"],
                "file_size": result["file_size"]
            }
            
        except Exception as e:
            logger.error(
                "spatial_audio_conversion_failed",
                error=str(e),
                job_id=job.job_id
            )
            raise ProxyGenerationError(f"Spatial audio conversion failed: {str(e)}")
        
        finally:
            # Cleanup temp file
            if temp_output_path and os.path.exists(temp_output_path):
                os.remove(temp_output_path)
    
    async def _process_ambisonic_encoding(self, job: ProxyJob) -> Dict[str, Any]:
        """Encode audio to Ambisonic format"""
        temp_output_path = None
        try:
            # Get parameters
            order_value = job.parameters.get("order", 1)
            order = AmbisonicOrder(order_value)
            normalize = job.parameters.get("normalize", True)
            
            # Generate output path
            temp_output_path = os.path.join(
                self._temp_dir,
                f"{job.job_id}_ambisonic_order{order_value}.wav"
            )
            
            # Encode to Ambisonic
            result = await self.spatial_audio_service.encode_ambisonic(
                input_path=job.input_path,
                output_path=temp_output_path,
                order=order,
                normalize=normalize
            )
            
            # Store in storage backend
            storage_key = self.storage_service.generate_storage_key(
                asset_id=job.asset_id,
                proxy_type="ambisonic",
                quality=f"order{order_value}",
                extension="wav"
            )
            
            storage_url = await self.storage_service.store_file(
                file_path=temp_output_path,
                storage_key=storage_key,
                metadata={
                    **result,
                    "job_id": job.job_id,
                    "asset_id": job.asset_id
                }
            )
            
            return {
                "job_id": job.job_id,
                "status": JobStatus.COMPLETED,
                "asset_id": job.asset_id,
                "storage_key": storage_key,
                "storage_url": storage_url,
                "ambisonic_order": result["ambisonic_order"],
                "channels": result["channels"],
                "normalized": result["normalized"],
                "file_size": result["file_size"]
            }
            
        except Exception as e:
            logger.error(
                "ambisonic_encoding_failed",
                error=str(e),
                job_id=job.job_id
            )
            raise ProxyGenerationError(f"Ambisonic encoding failed: {str(e)}")
        
        finally:
            # Cleanup temp file
            if temp_output_path and os.path.exists(temp_output_path):
                os.remove(temp_output_path)
    
    async def _process_binaural_rendering(self, job: ProxyJob) -> Dict[str, Any]:
        """Render Ambisonic to binaural"""
        temp_output_path = None
        try:
            # Get parameters
            hrtf_profile_str = job.parameters.get("hrtf_profile", "generic")
            hrtf_profile = HRTFProfile(hrtf_profile_str)
            head_tracking = job.parameters.get("head_tracking")
            
            # Generate output path
            temp_output_path = os.path.join(
                self._temp_dir,
                f"{job.job_id}_binaural_{hrtf_profile_str}.mp4"
            )
            
            # Render to binaural
            result = await self.spatial_audio_service.decode_ambisonic_to_binaural(
                input_path=job.input_path,
                output_path=temp_output_path,
                hrtf_profile=hrtf_profile,
                head_tracking=head_tracking
            )
            
            # Store in storage backend
            storage_key = self.storage_service.generate_storage_key(
                asset_id=job.asset_id,
                proxy_type="binaural",
                quality=hrtf_profile_str,
                extension="mp4"
            )
            
            storage_url = await self.storage_service.store_file(
                file_path=temp_output_path,
                storage_key=storage_key,
                metadata={
                    **result,
                    "job_id": job.job_id,
                    "asset_id": job.asset_id
                }
            )
            
            return {
                "job_id": job.job_id,
                "status": JobStatus.COMPLETED,
                "asset_id": job.asset_id,
                "storage_key": storage_key,
                "storage_url": storage_url,
                "hrtf_profile": result["hrtf_profile"],
                "head_tracking_applied": result["head_tracking_applied"],
                "output_format": result["output_format"],
                "file_size": result["file_size"]
            }
            
        except Exception as e:
            logger.error(
                "binaural_rendering_failed",
                error=str(e),
                job_id=job.job_id
            )
            raise ProxyGenerationError(f"Binaural rendering failed: {str(e)}")
        
        finally:
            # Cleanup temp file
            if temp_output_path and os.path.exists(temp_output_path):
                os.remove(temp_output_path)
    
    async def _process_room_acoustics(self, job: ProxyJob) -> Dict[str, Any]:
        """Apply room acoustics simulation"""
        temp_output_path = None
        try:
            # Get parameters
            room_preset_str = job.parameters.get("room_preset", "studio")
            room_preset = RoomAcoustics(room_preset_str)
            custom_params = job.parameters.get("custom_params")
            
            # Generate output path
            temp_output_path = os.path.join(
                self._temp_dir,
                f"{job.job_id}_room_{room_preset_str}.mp4"
            )
            
            # Apply room acoustics
            result = await self.spatial_audio_service.apply_room_acoustics(
                input_path=job.input_path,
                output_path=temp_output_path,
                room_preset=room_preset,
                custom_params=custom_params
            )
            
            # Store in storage backend
            storage_key = self.storage_service.generate_storage_key(
                asset_id=job.asset_id,
                proxy_type="room_acoustics",
                quality=room_preset_str,
                extension="mp4"
            )
            
            storage_url = await self.storage_service.store_file(
                file_path=temp_output_path,
                storage_key=storage_key,
                metadata={
                    **result,
                    "job_id": job.job_id,
                    "asset_id": job.asset_id
                }
            )
            
            return {
                "job_id": job.job_id,
                "status": JobStatus.COMPLETED,
                "asset_id": job.asset_id,
                "storage_key": storage_key,
                "storage_url": storage_url,
                "room_preset": result["room_preset"],
                "reverb_level": result["reverb_level"],
                "room_size": result["room_size"],
                "damping": result["damping"],
                "file_size": result["file_size"]
            }
            
        except Exception as e:
            logger.error(
                "room_acoustics_failed",
                error=str(e),
                job_id=job.job_id
            )
            raise ProxyGenerationError(f"Room acoustics processing failed: {str(e)}")
        
        finally:
            # Cleanup temp file
            if temp_output_path and os.path.exists(temp_output_path):
                os.remove(temp_output_path)
    
    async def _process_spatial_mix(self, job: ProxyJob) -> Dict[str, Any]:
        """Create spatial mix from multiple sources"""
        temp_output_path = None
        try:
            # Get parameters
            input_files = job.parameters.get("input_files", [])
            output_format_str = job.parameters.get("output_format", "5.1")
            output_format = SpatialAudioFormat(output_format_str)
            
            # Generate output path
            temp_output_path = os.path.join(
                self._temp_dir,
                f"{job.job_id}_spatial_mix.mp4"
            )
            
            # Create spatial mix
            result = await self.spatial_audio_service.create_spatial_mix(
                input_files=input_files,
                output_path=temp_output_path,
                output_format=output_format
            )
            
            # Store in storage backend
            storage_key = self.storage_service.generate_storage_key(
                asset_id=job.asset_id,
                proxy_type="spatial_mix",
                quality=output_format_str.replace('.', '_'),
                extension="mp4"
            )
            
            storage_url = await self.storage_service.store_file(
                file_path=temp_output_path,
                storage_key=storage_key,
                metadata={
                    **result,
                    "job_id": job.job_id,
                    "asset_id": job.asset_id
                }
            )
            
            return {
                "job_id": job.job_id,
                "status": JobStatus.COMPLETED,
                "asset_id": job.asset_id,
                "storage_key": storage_key,
                "storage_url": storage_url,
                "sources_count": result["sources_count"],
                "output_format": result["output_format"],
                "file_size": result["file_size"]
            }
            
        except Exception as e:
            logger.error(
                "spatial_mix_failed",
                error=str(e),
                job_id=job.job_id
            )
            raise ProxyGenerationError(f"Spatial mix creation failed: {str(e)}")
        
        finally:
            # Cleanup temp file
            if temp_output_path and os.path.exists(temp_output_path):
                os.remove(temp_output_path)
    
    async def _process_live_stream_start(self, job: ProxyJob) -> Dict[str, Any]:
        """Start a live stream"""
        try:
            # Get parameters
            input_source = job.parameters.get("input_source", job.input_path)
            output_url = job.parameters.get("output_url")
            protocol_str = job.parameters.get("protocol", "hls")
            protocol = StreamingProtocol(protocol_str)
            quality_str = job.parameters.get("quality", "high")
            quality = StreamQuality(quality_str)
            codec_str = job.parameters.get("codec", "h264")
            codec = StreamCodec(codec_str)
            audio_codec_str = job.parameters.get("audio_codec", "aac")
            audio_codec = StreamAudioCodec(audio_codec_str)
            latency_str = job.parameters.get("latency", "low")
            latency = StreamLatency(latency_str)
            dvr_mode_str = job.parameters.get("dvr_mode", "disabled")
            dvr_mode = DVRMode(dvr_mode_str)
            custom_params = job.parameters.get("custom_params")
            
            # Start the live stream
            result = await self.live_streaming_service.start_live_stream(
                input_source=input_source,
                output_url=output_url,
                protocol=protocol,
                quality=quality,
                codec=codec,
                audio_codec=audio_codec,
                latency=latency,
                dvr_mode=dvr_mode,
                custom_params=custom_params
            )
            
            logger.info(
                "live_stream_started",
                job_id=job.job_id,
                stream_id=result["stream_id"],
                protocol=protocol_str
            )
            
            return {
                "job_id": job.job_id,
                "status": JobStatus.COMPLETED,
                "asset_id": job.asset_id,
                "stream_id": result["stream_id"],
                "output_url": result["output_url"],
                "protocol": result["protocol"],
                "quality": result["quality"],
                "dvr_enabled": result["dvr_enabled"],
                "dvr_path": result.get("dvr_path")
            }
            
        except Exception as e:
            logger.error(
                "live_stream_start_failed",
                error=str(e),
                job_id=job.job_id
            )
            raise ProxyGenerationError(f"Live stream start failed: {str(e)}")
    
    async def _process_live_stream_stop(self, job: ProxyJob) -> Dict[str, Any]:
        """Stop a live stream"""
        try:
            # Get stream ID
            stream_id = job.parameters.get("stream_id")
            if not stream_id:
                raise ProxyGenerationError("stream_id is required")
            
            # Stop the stream
            result = await self.live_streaming_service.stop_live_stream(stream_id)
            
            logger.info(
                "live_stream_stopped",
                job_id=job.job_id,
                stream_id=stream_id,
                duration=result["duration"]
            )
            
            return {
                "job_id": job.job_id,
                "status": JobStatus.COMPLETED,
                "asset_id": job.asset_id,
                "stream_id": stream_id,
                "duration": result["duration"],
                "dvr_path": result.get("dvr_path")
            }
            
        except Exception as e:
            logger.error(
                "live_stream_stop_failed",
                error=str(e),
                job_id=job.job_id
            )
            raise ProxyGenerationError(f"Live stream stop failed: {str(e)}")
    
    async def _process_adaptive_stream(self, job: ProxyJob) -> Dict[str, Any]:
        """Create adaptive bitrate stream"""
        try:
            # Get parameters
            input_source = job.parameters.get("input_source", job.input_path)
            output_base_path = job.parameters.get("output_base_path")
            protocol_str = job.parameters.get("protocol", "hls")
            protocol = StreamingProtocol(protocol_str)
            codec_str = job.parameters.get("codec", "h264")
            codec = StreamCodec(codec_str)
            audio_codec_str = job.parameters.get("audio_codec", "aac")
            audio_codec = StreamAudioCodec(audio_codec_str)
            ladder = job.parameters.get("ladder")
            
            # Create adaptive stream
            result = await self.live_streaming_service.create_adaptive_stream(
                input_source=input_source,
                output_base_path=output_base_path,
                protocol=protocol,
                codec=codec,
                audio_codec=audio_codec,
                ladder=ladder
            )
            
            logger.info(
                "adaptive_stream_created",
                job_id=job.job_id,
                stream_id=result["stream_id"],
                qualities=result["qualities"]
            )
            
            return {
                "job_id": job.job_id,
                "status": JobStatus.COMPLETED,
                "asset_id": job.asset_id,
                "stream_id": result["stream_id"],
                "master_playlist": result["master_playlist"],
                "protocol": result["protocol"],
                "qualities": result["qualities"]
            }
            
        except Exception as e:
            logger.error(
                "adaptive_stream_failed",
                error=str(e),
                job_id=job.job_id
            )
            raise ProxyGenerationError(f"Adaptive stream creation failed: {str(e)}")
    
    async def _process_stream_overlay(self, job: ProxyJob) -> Dict[str, Any]:
        """Add overlay to live stream"""
        try:
            # Get parameters
            stream_id = job.parameters.get("stream_id")
            overlay_type = job.parameters.get("overlay_type")
            overlay_data = job.parameters.get("overlay_data", {})
            
            if not stream_id:
                raise ProxyGenerationError("stream_id is required")
            
            # Add overlay
            result = await self.live_streaming_service.add_stream_overlay(
                stream_id=stream_id,
                overlay_type=overlay_type,
                overlay_data=overlay_data
            )
            
            logger.info(
                "stream_overlay_added",
                job_id=job.job_id,
                stream_id=stream_id,
                overlay_type=overlay_type
            )
            
            return {
                "job_id": job.job_id,
                "status": JobStatus.COMPLETED,
                "asset_id": job.asset_id,
                "stream_id": stream_id,
                "overlay_type": overlay_type,
                "total_overlays": result["total_overlays"]
            }
            
        except Exception as e:
            logger.error(
                "stream_overlay_failed",
                error=str(e),
                job_id=job.job_id
            )
            raise ProxyGenerationError(f"Stream overlay failed: {str(e)}")
    
    async def _process_stream_recording(self, job: ProxyJob) -> Dict[str, Any]:
        """Create recording from live stream"""
        try:
            # Get parameters
            stream_id = job.parameters.get("stream_id")
            output_path = job.parameters.get("output_path")
            duration = job.parameters.get("duration")
            
            if not stream_id:
                raise ProxyGenerationError("stream_id is required")
            
            # Create recording
            result = await self.live_streaming_service.create_stream_recording(
                stream_id=stream_id,
                output_path=output_path,
                duration=duration
            )
            
            logger.info(
                "stream_recording_started",
                job_id=job.job_id,
                stream_id=stream_id,
                recording_id=result["recording_id"]
            )
            
            return {
                "job_id": job.job_id,
                "status": JobStatus.COMPLETED,
                "asset_id": job.asset_id,
                "stream_id": stream_id,
                "recording_id": result["recording_id"],
                "output_path": result["output_path"],
                "duration": result.get("duration")
            }
            
        except Exception as e:
            logger.error(
                "stream_recording_failed",
                error=str(e),
                job_id=job.job_id
            )
            raise ProxyGenerationError(f"Stream recording failed: {str(e)}")
    
    async def _process_remote_production_create(self, job: ProxyJob) -> Dict[str, Any]:
        """Create a remote production session"""
        try:
            # Get parameters
            production_id = job.parameters.get("production_id", str(uuid.uuid4()))
            production_name = job.parameters.get("production_name", "Remote Production")
            director_id = job.parameters.get("director_id")
            configuration = job.parameters.get("configuration", {})
            
            # Create remote production
            result = await self.remote_production_service.create_remote_production(
                production_id=production_id,
                production_name=production_name,
                director_id=director_id,
                configuration=configuration
            )
            
            logger.info(
                "remote_production_created",
                job_id=job.job_id,
                production_id=production_id
            )
            
            return {
                "job_id": job.job_id,
                "status": JobStatus.COMPLETED,
                "asset_id": job.asset_id,
                "production_id": production_id,
                "production_name": production_name,
                "join_url": result["join_url"],
                "control_url": result["control_url"]
            }
            
        except Exception as e:
            logger.error(
                "remote_production_create_failed",
                error=str(e),
                job_id=job.job_id
            )
            raise ProxyGenerationError(f"Remote production creation failed: {str(e)}")
    
    async def _process_remote_participant_add(self, job: ProxyJob) -> Dict[str, Any]:
        """Add participant to remote production"""
        try:
            # Get parameters
            production_id = job.parameters.get("production_id")
            participant_id = job.parameters.get("participant_id")
            participant_name = job.parameters.get("participant_name")
            role_str = job.parameters.get("role", "observer")
            role = RemoteProductionRole(role_str)
            capabilities = job.parameters.get("capabilities", {})
            
            if not production_id:
                raise ProxyGenerationError("production_id is required")
            
            # Add participant
            result = await self.remote_production_service.add_remote_participant(
                production_id=production_id,
                participant_id=participant_id,
                participant_name=participant_name,
                role=role,
                capabilities=capabilities
            )
            
            logger.info(
                "remote_participant_added",
                job_id=job.job_id,
                production_id=production_id,
                participant_id=participant_id
            )
            
            return {
                "job_id": job.job_id,
                "status": JobStatus.COMPLETED,
                "asset_id": job.asset_id,
                "participant_id": participant_id,
                "role": result["role"],
                "permissions": result["permissions"],
                "comm_channels": result["comm_channels"]
            }
            
        except Exception as e:
            logger.error(
                "remote_participant_add_failed",
                error=str(e),
                job_id=job.job_id
            )
            raise ProxyGenerationError(f"Remote participant add failed: {str(e)}")
    
    async def _process_remote_source_add(self, job: ProxyJob) -> Dict[str, Any]:
        """Add remote source to production"""
        try:
            # Get parameters
            production_id = job.parameters.get("production_id")
            source_id = job.parameters.get("source_id", str(uuid.uuid4()))
            source_name = job.parameters.get("source_name")
            source_type_str = job.parameters.get("source_type", "srt")
            source_type = RemoteSourceType(source_type_str)
            participant_id = job.parameters.get("participant_id")
            connection_params = job.parameters.get("connection_params", {})
            
            if not production_id:
                raise ProxyGenerationError("production_id is required")
            
            # Add source
            result = await self.remote_production_service.add_remote_source(
                production_id=production_id,
                source_id=source_id,
                source_name=source_name,
                source_type=source_type,
                participant_id=participant_id,
                connection_params=connection_params
            )
            
            logger.info(
                "remote_source_added",
                job_id=job.job_id,
                production_id=production_id,
                source_id=source_id
            )
            
            return {
                "job_id": job.job_id,
                "status": JobStatus.COMPLETED,
                "asset_id": job.asset_id,
                "source_id": source_id,
                "stream_url": result["stream_url"],
                "preview_url": result["preview_url"]
            }
            
        except Exception as e:
            logger.error(
                "remote_source_add_failed",
                error=str(e),
                job_id=job.job_id
            )
            raise ProxyGenerationError(f"Remote source add failed: {str(e)}")
    
    async def _process_tally_update(self, job: ProxyJob) -> Dict[str, Any]:
        """Update tally state for remote source"""
        try:
            # Get parameters
            production_id = job.parameters.get("production_id")
            source_id = job.parameters.get("source_id")
            tally_state_str = job.parameters.get("tally_state", "off")
            tally_state = TallyState(tally_state_str)
            
            if not production_id or not source_id:
                raise ProxyGenerationError("production_id and source_id are required")
            
            # Update tally
            result = await self.remote_production_service.update_tally_state(
                production_id=production_id,
                source_id=source_id,
                tally_state=tally_state
            )
            
            logger.info(
                "tally_updated",
                job_id=job.job_id,
                production_id=production_id,
                source_id=source_id,
                tally_state=tally_state_str
            )
            
            return {
                "job_id": job.job_id,
                "status": JobStatus.COMPLETED,
                "asset_id": job.asset_id,
                "source_id": source_id,
                "tally_state": result["tally_state"]
            }
            
        except Exception as e:
            logger.error(
                "tally_update_failed",
                error=str(e),
                job_id=job.job_id
            )
            raise ProxyGenerationError(f"Tally update failed: {str(e)}")
    
    async def _process_return_feed_config(self, job: ProxyJob) -> Dict[str, Any]:
        """Configure return feed for participant"""
        try:
            # Get parameters
            production_id = job.parameters.get("production_id")
            participant_id = job.parameters.get("participant_id")
            feed_type_str = job.parameters.get("feed_type", "program_clean")
            feed_type = ReturnFeedType(feed_type_str)
            custom_sources = job.parameters.get("custom_sources")
            
            if not production_id or not participant_id:
                raise ProxyGenerationError("production_id and participant_id are required")
            
            # Configure return feed
            result = await self.remote_production_service.configure_return_feed(
                production_id=production_id,
                participant_id=participant_id,
                feed_type=feed_type,
                custom_sources=custom_sources
            )
            
            logger.info(
                "return_feed_configured",
                job_id=job.job_id,
                production_id=production_id,
                participant_id=participant_id
            )
            
            return {
                "job_id": job.job_id,
                "status": JobStatus.COMPLETED,
                "asset_id": job.asset_id,
                "participant_id": participant_id,
                "feed_type": result["feed_type"],
                "stream_url": result["stream_url"]
            }
            
        except Exception as e:
            logger.error(
                "return_feed_config_failed",
                error=str(e),
                job_id=job.job_id
            )
            raise ProxyGenerationError(f"Return feed configuration failed: {str(e)}")
    
    async def _process_cloud_switching_create(self, job: ProxyJob) -> Dict[str, Any]:
        """Create cloud switching session"""
        try:
            # Get parameters
            session_id = job.parameters.get("session_id", str(uuid.uuid4()))
            session_name = job.parameters.get("session_name", f"Switching_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}")
            configuration = job.parameters.get("configuration", {})
            
            # Create switching session
            result = await self.cloud_switching_service.create_switching_session(
                session_id=session_id,
                session_name=session_name,
                configuration=configuration
            )
            
            logger.info(
                "cloud_switching_session_created",
                job_id=job.job_id,
                session_id=session_id
            )
            
            return {
                "job_id": job.job_id,
                "status": JobStatus.COMPLETED,
                "asset_id": job.asset_id,
                "session_id": session_id,
                "control_url": result["control_url"],
                "preview_url": result["preview_url"],
                "program_url": result["program_url"]
            }
            
        except Exception as e:
            logger.error(
                "cloud_switching_create_failed",
                error=str(e),
                job_id=job.job_id
            )
            raise ProxyGenerationError(f"Cloud switching creation failed: {str(e)}")
    
    async def _process_switching_input_add(self, job: ProxyJob) -> Dict[str, Any]:
        """Add input to switching session"""
        try:
            # Get parameters
            session_id = job.parameters.get("session_id")
            input_id = job.parameters.get("input_id", str(uuid.uuid4()))
            input_name = job.parameters.get("input_name", f"Input_{input_id}")
            input_type_str = job.parameters.get("input_type", "live_stream")
            input_type = InputType(input_type_str)
            input_url = job.parameters.get("input_url", "")
            settings = job.parameters.get("settings", {})
            
            if not session_id:
                raise ProxyGenerationError("session_id is required")
            
            # Add input source
            result = await self.cloud_switching_service.add_input_source(
                session_id=session_id,
                input_id=input_id,
                input_name=input_name,
                input_type=input_type,
                input_url=input_url,
                settings=settings
            )
            
            logger.info(
                "switching_input_added",
                job_id=job.job_id,
                session_id=session_id,
                input_id=input_id
            )
            
            return {
                "job_id": job.job_id,
                "status": JobStatus.COMPLETED,
                "asset_id": job.asset_id,
                "session_id": session_id,
                "input_id": input_id,
                "preview_url": result["preview_url"]
            }
            
        except Exception as e:
            logger.error(
                "switching_input_add_failed",
                error=str(e),
                job_id=job.job_id
            )
            raise ProxyGenerationError(f"Switching input add failed: {str(e)}")
    
    async def _process_switching_switch(self, job: ProxyJob) -> Dict[str, Any]:
        """Switch to different input"""
        try:
            # Get parameters
            session_id = job.parameters.get("session_id")
            input_id = job.parameters.get("input_id")
            mix_effect_str = job.parameters.get("mix_effect", "main")
            mix_effect = MixEffectType(mix_effect_str)
            transition_type_str = job.parameters.get("transition_type")
            transition_type = SwitchingMode(transition_type_str) if transition_type_str else None
            transition_duration_ms = job.parameters.get("transition_duration_ms", 0)
            
            if not session_id or not input_id:
                raise ProxyGenerationError("session_id and input_id are required")
            
            # Perform switch
            result = await self.cloud_switching_service.switch_input(
                session_id=session_id,
                input_id=input_id,
                mix_effect=mix_effect,
                transition_type=transition_type,
                transition_duration_ms=transition_duration_ms
            )
            
            logger.info(
                "switching_executed",
                job_id=job.job_id,
                session_id=session_id,
                input_id=input_id
            )
            
            return {
                "job_id": job.job_id,
                "status": JobStatus.COMPLETED,
                "asset_id": job.asset_id,
                "session_id": session_id,
                "program": result["program"],
                "preview": result["preview"],
                "transition": result["transition"]
            }
            
        except Exception as e:
            logger.error(
                "switching_switch_failed",
                error=str(e),
                job_id=job.job_id
            )
            raise ProxyGenerationError(f"Switching switch failed: {str(e)}")
    
    async def _process_switching_output_config(self, job: ProxyJob) -> Dict[str, Any]:
        """Configure switching output"""
        try:
            # Get parameters
            session_id = job.parameters.get("session_id")
            output_id = job.parameters.get("output_id", str(uuid.uuid4()))
            output_format_str = job.parameters.get("output_format", "hls")
            output_format = OutputFormat(output_format_str)
            destination = job.parameters.get("destination", "")
            settings = job.parameters.get("settings", {})
            
            if not session_id or not destination:
                raise ProxyGenerationError("session_id and destination are required")
            
            # Configure output
            result = await self.cloud_switching_service.configure_output(
                session_id=session_id,
                output_id=output_id,
                output_format=output_format,
                destination=destination,
                settings=settings
            )
            
            logger.info(
                "switching_output_configured",
                job_id=job.job_id,
                session_id=session_id,
                output_id=output_id
            )
            
            return {
                "job_id": job.job_id,
                "status": JobStatus.COMPLETED,
                "asset_id": job.asset_id,
                "session_id": session_id,
                "output_id": output_id,
                "stream_url": result["stream_url"]
            }
            
        except Exception as e:
            logger.error(
                "switching_output_config_failed",
                error=str(e),
                job_id=job.job_id
            )
            raise ProxyGenerationError(f"Switching output config failed: {str(e)}")
    
    async def _process_switching_macro_create(self, job: ProxyJob) -> Dict[str, Any]:
        """Create switching macro"""
        try:
            # Get parameters
            session_id = job.parameters.get("session_id")
            macro_id = job.parameters.get("macro_id", str(uuid.uuid4()))
            macro_name = job.parameters.get("macro_name", f"Macro_{macro_id}")
            macro_type_str = job.parameters.get("macro_type", "sequence")
            macro_type = MacroType(macro_type_str)
            actions = job.parameters.get("actions", [])
            
            if not session_id or not actions:
                raise ProxyGenerationError("session_id and actions are required")
            
            # Create macro
            result = await self.cloud_switching_service.create_macro(
                session_id=session_id,
                macro_id=macro_id,
                macro_name=macro_name,
                macro_type=macro_type,
                actions=actions
            )
            
            logger.info(
                "switching_macro_created",
                job_id=job.job_id,
                session_id=session_id,
                macro_id=macro_id
            )
            
            return {
                "job_id": job.job_id,
                "status": JobStatus.COMPLETED,
                "asset_id": job.asset_id,
                "session_id": session_id,
                "macro_id": macro_id,
                "action_count": result["action_count"]
            }
            
        except Exception as e:
            logger.error(
                "switching_macro_create_failed",
                error=str(e),
                job_id=job.job_id
            )
            raise ProxyGenerationError(f"Switching macro creation failed: {str(e)}")
    
    async def _process_virtual_studio_create(self, job: ProxyJob) -> Dict[str, Any]:
        """Create virtual studio session"""
        try:
            # Get parameters
            studio_id = job.parameters.get("studio_id", str(uuid.uuid4()))
            studio_name = job.parameters.get("studio_name", f"Studio_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}")
            configuration = job.parameters.get("configuration", {})
            
            # Create virtual studio
            result = await self.virtual_studio_service.create_virtual_studio(
                studio_id=studio_id,
                studio_name=studio_name,
                configuration=configuration
            )
            
            logger.info(
                "virtual_studio_created",
                job_id=job.job_id,
                studio_id=studio_id
            )
            
            return {
                "job_id": job.job_id,
                "status": JobStatus.COMPLETED,
                "asset_id": job.asset_id,
                "studio_id": studio_id,
                "preview_url": result["preview_url"],
                "output_url": result["output_url"],
                "control_url": result["control_url"]
            }
            
        except Exception as e:
            logger.error(
                "virtual_studio_create_failed",
                error=str(e),
                job_id=job.job_id
            )
            raise ProxyGenerationError(f"Virtual studio creation failed: {str(e)}")
    
    async def _process_virtual_studio_chroma_config(self, job: ProxyJob) -> Dict[str, Any]:
        """Configure virtual studio chroma key"""
        try:
            # Get parameters
            studio_id = job.parameters.get("studio_id")
            method_str = job.parameters.get("method", "green_screen")
            method = ChromaKeyMethod(method_str)
            settings = job.parameters.get("settings", {})
            
            if not studio_id:
                raise ProxyGenerationError("studio_id is required")
            
            # Configure chroma key
            result = await self.virtual_studio_service.configure_chroma_key(
                studio_id=studio_id,
                method=method,
                settings=settings
            )
            
            logger.info(
                "virtual_studio_chroma_configured",
                job_id=job.job_id,
                studio_id=studio_id,
                method=method_str
            )
            
            return {
                "job_id": job.job_id,
                "status": JobStatus.COMPLETED,
                "asset_id": job.asset_id,
                "studio_id": studio_id,
                "chroma_key": result
            }
            
        except Exception as e:
            logger.error(
                "virtual_studio_chroma_config_failed",
                error=str(e),
                job_id=job.job_id
            )
            raise ProxyGenerationError(f"Virtual studio chroma config failed: {str(e)}")
    
    async def _process_virtual_studio_set_load(self, job: ProxyJob) -> Dict[str, Any]:
        """Load virtual set into studio"""
        try:
            # Get parameters
            studio_id = job.parameters.get("studio_id")
            set_id = job.parameters.get("set_id", str(uuid.uuid4()))
            set_type_str = job.parameters.get("set_type", "static_2d")
            set_type = VirtualSetType(set_type_str)
            set_data = job.parameters.get("set_data", {})
            
            if not studio_id:
                raise ProxyGenerationError("studio_id is required")
            
            # Load virtual set
            result = await self.virtual_studio_service.load_virtual_set(
                studio_id=studio_id,
                set_id=set_id,
                set_type=set_type,
                set_data=set_data
            )
            
            logger.info(
                "virtual_studio_set_loaded",
                job_id=job.job_id,
                studio_id=studio_id,
                set_id=set_id
            )
            
            return {
                "job_id": job.job_id,
                "status": JobStatus.COMPLETED,
                "asset_id": job.asset_id,
                "studio_id": studio_id,
                "set_id": set_id,
                "set_type": result["type"]
            }
            
        except Exception as e:
            logger.error(
                "virtual_studio_set_load_failed",
                error=str(e),
                job_id=job.job_id
            )
            raise ProxyGenerationError(f"Virtual studio set load failed: {str(e)}")
    
    async def _process_virtual_studio_ar_add(self, job: ProxyJob) -> Dict[str, Any]:
        """Add AR element to virtual studio"""
        try:
            # Get parameters
            studio_id = job.parameters.get("studio_id")
            element_id = job.parameters.get("element_id", str(uuid.uuid4()))
            element_type_str = job.parameters.get("element_type", "graphic_2d")
            element_type = ARElementType(element_type_str)
            properties = job.parameters.get("properties", {})
            
            if not studio_id:
                raise ProxyGenerationError("studio_id is required")
            
            # Add AR element
            result = await self.virtual_studio_service.add_ar_element(
                studio_id=studio_id,
                element_id=element_id,
                element_type=element_type,
                properties=properties
            )
            
            logger.info(
                "virtual_studio_ar_added",
                job_id=job.job_id,
                studio_id=studio_id,
                element_id=element_id
            )
            
            return {
                "job_id": job.job_id,
                "status": JobStatus.COMPLETED,
                "asset_id": job.asset_id,
                "studio_id": studio_id,
                "element_id": element_id,
                "element_type": result["type"]
            }
            
        except Exception as e:
            logger.error(
                "virtual_studio_ar_add_failed",
                error=str(e),
                job_id=job.job_id
            )
            raise ProxyGenerationError(f"Virtual studio AR add failed: {str(e)}")
    
    async def _process_virtual_studio_tracking_update(self, job: ProxyJob) -> Dict[str, Any]:
        """Update virtual studio tracking"""
        try:
            # Get parameters
            studio_id = job.parameters.get("studio_id")
            tracking_method_str = job.parameters.get("tracking_method", "static")
            tracking_method = TrackingMethod(tracking_method_str)
            tracking_data = job.parameters.get("tracking_data", {})
            
            if not studio_id:
                raise ProxyGenerationError("studio_id is required")
            
            # Update tracking
            result = await self.virtual_studio_service.update_tracking(
                studio_id=studio_id,
                tracking_method=tracking_method,
                tracking_data=tracking_data
            )
            
            logger.info(
                "virtual_studio_tracking_updated",
                job_id=job.job_id,
                studio_id=studio_id,
                method=tracking_method_str
            )
            
            return {
                "job_id": job.job_id,
                "status": JobStatus.COMPLETED,
                "asset_id": job.asset_id,
                "studio_id": studio_id,
                "tracking": result
            }
            
        except Exception as e:
            logger.error(
                "virtual_studio_tracking_update_failed",
                error=str(e),
                job_id=job.job_id
            )
            raise ProxyGenerationError(f"Virtual studio tracking update failed: {str(e)}")
    
    async def _process_live_graphics_create(self, job: ProxyJob) -> Dict[str, Any]:
        """Create live graphics session"""
        try:
            # Get parameters
            session_id = job.parameters.get("session_id", str(uuid.uuid4()))
            session_name = job.parameters.get("session_name", f"Graphics_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}")
            configuration = job.parameters.get("configuration", {})
            
            # Create graphics session
            result = await self.live_graphics_service.create_graphics_session(
                session_id=session_id,
                session_name=session_name,
                configuration=configuration
            )
            
            logger.info(
                "live_graphics_session_created",
                job_id=job.job_id,
                session_id=session_id
            )
            
            return {
                "job_id": job.job_id,
                "status": JobStatus.COMPLETED,
                "asset_id": job.asset_id,
                "session_id": session_id,
                "output_url": result["output_url"],
                "preview_url": result["preview_url"],
                "control_url": result["control_url"]
            }
            
        except Exception as e:
            logger.error(
                "live_graphics_create_failed",
                error=str(e),
                job_id=job.job_id
            )
            raise ProxyGenerationError(f"Live graphics session creation failed: {str(e)}")
    
    async def _process_live_graphics_template_load(self, job: ProxyJob) -> Dict[str, Any]:
        """Load graphics template"""
        try:
            # Get parameters
            session_id = job.parameters.get("session_id")
            template_id = job.parameters.get("template_id", str(uuid.uuid4()))
            template_type_str = job.parameters.get("template_type", "lower_third")
            template_type = GraphicsType(template_type_str)
            template_data = job.parameters.get("template_data", {})
            
            if not session_id:
                raise ProxyGenerationError("session_id is required")
            
            # Load template
            result = await self.live_graphics_service.load_template(
                session_id=session_id,
                template_id=template_id,
                template_type=template_type,
                template_data=template_data
            )
            
            logger.info(
                "live_graphics_template_loaded",
                job_id=job.job_id,
                session_id=session_id,
                template_id=template_id
            )
            
            return {
                "job_id": job.job_id,
                "status": JobStatus.COMPLETED,
                "asset_id": job.asset_id,
                "session_id": session_id,
                "template": result
            }
            
        except Exception as e:
            logger.error(
                "live_graphics_template_load_failed",
                error=str(e),
                job_id=job.job_id
            )
            raise ProxyGenerationError(f"Graphics template load failed: {str(e)}")
    
    async def _process_live_graphics_show(self, job: ProxyJob) -> Dict[str, Any]:
        """Show/hide graphic with animation"""
        try:
            # Get parameters
            session_id = job.parameters.get("session_id")
            graphic_id = job.parameters.get("graphic_id")
            action = job.parameters.get("action", "show")  # show or hide
            animation_str = job.parameters.get("animation")
            duration_ms = job.parameters.get("duration_ms", 500)
            
            if not session_id or not graphic_id:
                raise ProxyGenerationError("session_id and graphic_id are required")
            
            # Convert animation type if provided
            animation = AnimationType(animation_str) if animation_str else None
            
            # Show or hide graphic
            if action == "show":
                result = await self.live_graphics_service.show_graphic(
                    session_id=session_id,
                    graphic_id=graphic_id,
                    animation=animation,
                    duration_ms=duration_ms
                )
            else:
                result = await self.live_graphics_service.hide_graphic(
                    session_id=session_id,
                    graphic_id=graphic_id,
                    animation=animation,
                    duration_ms=duration_ms
                )
            
            logger.info(
                f"live_graphics_{action}",
                job_id=job.job_id,
                session_id=session_id,
                graphic_id=graphic_id
            )
            
            return {
                "job_id": job.job_id,
                "status": JobStatus.COMPLETED,
                "asset_id": job.asset_id,
                "session_id": session_id,
                "graphic": result
            }
            
        except Exception as e:
            logger.error(
                "live_graphics_show_failed",
                error=str(e),
                job_id=job.job_id
            )
            raise ProxyGenerationError(f"Graphics show/hide failed: {str(e)}")
    
    async def _process_live_graphics_data_update(self, job: ProxyJob) -> Dict[str, Any]:
        """Update graphic data dynamically"""
        try:
            # Get parameters
            session_id = job.parameters.get("session_id")
            graphic_id = job.parameters.get("graphic_id")
            data = job.parameters.get("data", {})
            
            if not session_id or not graphic_id:
                raise ProxyGenerationError("session_id and graphic_id are required")
            
            # Update data
            result = await self.live_graphics_service.update_graphic_data(
                session_id=session_id,
                graphic_id=graphic_id,
                data=data
            )
            
            logger.info(
                "live_graphics_data_updated",
                job_id=job.job_id,
                session_id=session_id,
                graphic_id=graphic_id
            )
            
            return {
                "job_id": job.job_id,
                "status": JobStatus.COMPLETED,
                "asset_id": job.asset_id,
                "session_id": session_id,
                "update": result
            }
            
        except Exception as e:
            logger.error(
                "live_graphics_data_update_failed",
                error=str(e),
                job_id=job.job_id
            )
            raise ProxyGenerationError(f"Graphics data update failed: {str(e)}")
    
    async def _process_live_graphics_playlist_create(self, job: ProxyJob) -> Dict[str, Any]:
        """Create graphics playlist"""
        try:
            # Get parameters
            session_id = job.parameters.get("session_id")
            playlist_id = job.parameters.get("playlist_id", str(uuid.uuid4()))
            items = job.parameters.get("items", [])
            
            if not session_id:
                raise ProxyGenerationError("session_id is required")
            
            # Create playlist
            result = await self.live_graphics_service.create_playlist(
                session_id=session_id,
                playlist_id=playlist_id,
                items=items
            )
            
            logger.info(
                "live_graphics_playlist_created",
                job_id=job.job_id,
                session_id=session_id,
                playlist_id=playlist_id
            )
            
            return {
                "job_id": job.job_id,
                "status": JobStatus.COMPLETED,
                "asset_id": job.asset_id,
                "session_id": session_id,
                "playlist": result
            }
            
        except Exception as e:
            logger.error(
                "live_graphics_playlist_create_failed",
                error=str(e),
                job_id=job.job_id
            )
            raise ProxyGenerationError(f"Graphics playlist creation failed: {str(e)}")


# Singleton instance
_proxy_processor: Optional[ProxyProcessor] = None


async def get_proxy_processor() -> ProxyProcessor:
    """Get proxy processor instance"""
    global _proxy_processor
    
    if _proxy_processor is None:
        _proxy_processor = ProxyProcessor()
        await _proxy_processor.initialize()
    
    return _proxy_processor