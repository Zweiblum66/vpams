"""
Spherical Video Service for 360° and VR Video Processing
"""

import os
import asyncio
import json
import tempfile
import math
from typing import Dict, List, Optional, Tuple, Any, Union
from pathlib import Path
from enum import Enum
from datetime import datetime

from ..core.config import settings
from ..core.exceptions import FFmpegError, InvalidMediaError, ProcessingTimeoutError
from ..core.logging import get_logger
from .ffmpeg_service import FFmpegService

logger = get_logger(__name__)


class SphericalProjection(str, Enum):
    """Spherical video projection types"""
    EQUIRECTANGULAR = "equirectangular"
    CUBEMAP = "cubemap"
    CUBEMAP_32 = "cubemap32"  # 3x2 layout
    CUBEMAP_EAC = "eac"  # Equi-Angular Cubemap
    OCTAHEDRON = "octahedron"
    PERSPECTIVE = "perspective"


class SphericalStereoMode(str, Enum):
    """Stereoscopic modes for VR"""
    MONO = "mono"
    SIDE_BY_SIDE = "side_by_side"
    TOP_BOTTOM = "top_bottom"


class VRHeadset(str, Enum):
    """VR headset optimization profiles"""
    OCULUS_QUEST = "oculus_quest"
    OCULUS_RIFT = "oculus_rift"
    HTC_VIVE = "htc_vive"
    PICO = "pico"
    GENERIC = "generic"


class SphericalQuality(str, Enum):
    """Quality presets for 360° video"""
    LOW = "low"          # 2K, mobile VR
    MEDIUM = "medium"    # 4K, standalone VR
    HIGH = "high"        # 6K, PC VR
    ULTRA = "ultra"      # 8K, high-end VR


class SphericalVideoMetadata:
    """360° video metadata management"""
    
    @staticmethod
    def create_spatial_media_metadata(
        projection: SphericalProjection,
        stereo_mode: SphericalStereoMode = SphericalStereoMode.MONO,
        initial_view_heading: float = 0.0,
        initial_view_pitch: float = 0.0,
        initial_view_roll: float = 0.0,
        source_count: int = 1,
        timestamp: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create Google Spatial Media metadata"""
        
        return {
            "spherical": {
                "Spherical": True,
                "Stitched": True,
                "StitchingSoftware": "MAMS Spherical Video Service",
                "ProjectionType": projection.value,
                "StereoMode": stereo_mode.value,
                "SourceCount": source_count,
                "InitialViewHeadingDegrees": initial_view_heading,
                "InitialViewPitchDegrees": initial_view_pitch,
                "InitialViewRollDegrees": initial_view_roll,
                "Timestamp": timestamp or datetime.utcnow().isoformat(),
                "CroppedAreaImageWidthPixels": None,  # Will be set based on video
                "CroppedAreaImageHeightPixels": None,
                "CroppedAreaLeftPixels": 0,
                "CroppedAreaTopPixels": 0,
                "FullPanoWidthPixels": None,
                "FullPanoHeightPixels": None
            }
        }
    
    @staticmethod
    def create_vr_metadata(
        headset: VRHeadset,
        field_of_view: float = 110.0,
        interpupillary_distance: float = 64.0,
        tracking_type: str = "6dof"
    ) -> Dict[str, Any]:
        """Create VR-specific metadata"""
        
        return {
            "vr": {
                "target_headset": headset.value,
                "field_of_view": field_of_view,
                "interpupillary_distance": interpupillary_distance,
                "tracking_type": tracking_type,
                "comfort_settings": {
                    "motion_blur_reduction": True,
                    "frame_interpolation": True,
                    "stabilization": True
                }
            }
        }


class SphericalVideoService:
    """Service for 360° and VR video processing"""
    
    def __init__(self, ffmpeg_service: FFmpegService):
        self.ffmpeg_service = ffmpeg_service
        
        # Check for 360° video processing capabilities
        self.has_v360_filter = self._check_v360_filter_support()
        self.has_spatial_media = self._check_spatial_media_support()
        
        logger.info(
            "spherical_video_service_initialized",
            has_v360_filter=self.has_v360_filter,
            has_spatial_media=self.has_spatial_media
        )
    
    def _check_v360_filter_support(self) -> bool:
        """Check if FFmpeg has v360 filter support"""
        try:
            # This would check if v360 filter is available
            # For now, assume it's available in modern FFmpeg builds
            return True
        except Exception:
            return False
    
    def _check_spatial_media_support(self) -> bool:
        """Check if spatial media tools are available"""
        try:
            # This would check for Google's spatial media tools
            return True
        except Exception:
            return False
    
    async def analyze_spherical_video(self, input_path: str) -> Dict[str, Any]:
        """Analyze 360° video characteristics"""
        try:
            # Get basic media info
            cmd = [
                self.ffmpeg_service.ffprobe_path,
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                input_path
            ]
            
            result = await self.ffmpeg_service.run_ffmpeg_command(cmd)
            probe_data = json.loads(result.stdout)
            
            # Find video stream
            video_stream = None
            for stream in probe_data.get("streams", []):
                if stream.get("codec_type") == "video":
                    video_stream = stream
                    break
            
            if not video_stream:
                raise InvalidMediaError("No video stream found")
            
            # Extract video properties
            width = int(video_stream.get("width", 0))
            height = int(video_stream.get("height", 0))
            aspect_ratio = width / height if height > 0 else 0
            
            # Analyze spherical characteristics
            analysis = {
                "is_spherical": False,
                "detected_projection": None,
                "stereo_mode": SphericalStereoMode.MONO,
                "width": width,
                "height": height,
                "aspect_ratio": aspect_ratio,
                "bitrate": int(video_stream.get("bit_rate", 0)),
                "frame_rate": self._parse_frame_rate(video_stream.get("r_frame_rate")),
                "duration": float(probe_data.get("format", {}).get("duration", 0)),
                "spherical_metadata": None,
                "recommendations": []
            }
            
            # Detect spherical format based on aspect ratio and metadata
            analysis["is_spherical"], analysis["detected_projection"] = self._detect_spherical_format(
                width, height, probe_data
            )
            
            # Detect stereoscopic mode
            analysis["stereo_mode"] = self._detect_stereo_mode(width, height)
            
            # Extract existing spherical metadata
            if analysis["is_spherical"]:
                analysis["spherical_metadata"] = await self._extract_spherical_metadata(input_path)
            
            # Generate processing recommendations
            analysis["recommendations"] = self._generate_spherical_recommendations(analysis)
            
            return analysis
            
        except Exception as e:
            logger.error("spherical_analysis_failed", error=str(e), input_path=input_path)
            raise
    
    def _parse_frame_rate(self, frame_rate_str: str) -> float:
        """Parse frame rate from FFprobe string"""
        try:
            if "/" in frame_rate_str:
                num, denom = frame_rate_str.split("/")
                return float(num) / float(denom)
            return float(frame_rate_str)
        except (ValueError, ZeroDivisionError):
            return 30.0  # Default
    
    def _detect_spherical_format(self, width: int, height: int, probe_data: Dict) -> Tuple[bool, Optional[SphericalProjection]]:
        """Detect if video is spherical and what projection type"""
        
        aspect_ratio = width / height if height > 0 else 0
        
        # Check for existing spherical metadata in format tags
        format_tags = probe_data.get("format", {}).get("tags", {})
        if any("spherical" in key.lower() for key in format_tags.keys()):
            return True, SphericalProjection.EQUIRECTANGULAR
        
        # Detect based on common aspect ratios
        if abs(aspect_ratio - 2.0) < 0.1:  # 2:1 ratio
            return True, SphericalProjection.EQUIRECTANGULAR
        elif abs(aspect_ratio - 1.5) < 0.1:  # 3:2 ratio
            return True, SphericalProjection.CUBEMAP_32
        elif abs(aspect_ratio - 1.0) < 0.1:  # 1:1 ratio
            return True, SphericalProjection.CUBEMAP
        elif width >= 7680 and height >= 3840:  # 8K+ with 2:1 ratio
            return True, SphericalProjection.EQUIRECTANGULAR
        elif width >= 3840 and height >= 1920:  # 4K+ with 2:1 ratio
            return True, SphericalProjection.EQUIRECTANGULAR
        
        return False, None
    
    def _detect_stereo_mode(self, width: int, height: int) -> SphericalStereoMode:
        """Detect stereoscopic mode"""
        aspect_ratio = width / height if height > 0 else 0
        
        # Common stereo formats
        if abs(aspect_ratio - 1.0) < 0.1:  # Square suggests top-bottom stereo
            return SphericalStereoMode.TOP_BOTTOM
        elif abs(aspect_ratio - 4.0) < 0.1:  # 4:1 suggests side-by-side stereo
            return SphericalStereoMode.SIDE_BY_SIDE
        
        return SphericalStereoMode.MONO
    
    async def _extract_spherical_metadata(self, input_path: str) -> Dict[str, Any]:
        """Extract existing spherical metadata"""
        metadata = {}
        
        try:
            # Use ffprobe to extract metadata
            cmd = [
                self.ffmpeg_service.ffprobe_path,
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                input_path
            ]
            
            result = await self.ffmpeg_service.run_ffmpeg_command(cmd)
            probe_data = json.loads(result.stdout)
            
            # Extract relevant metadata from format tags
            format_tags = probe_data.get("format", {}).get("tags", {})
            for key, value in format_tags.items():
                if "spherical" in key.lower() or "spatial" in key.lower():
                    metadata[key] = value
            
        except Exception as e:
            logger.warning("spherical_metadata_extraction_failed", error=str(e))
        
        return metadata
    
    def _generate_spherical_recommendations(self, analysis: Dict[str, Any]) -> List[Dict[str, str]]:
        """Generate processing recommendations"""
        recommendations = []
        
        if not analysis["is_spherical"]:
            recommendations.append({
                "type": "info",
                "message": "Content does not appear to be spherical. Consider standard video processing."
            })
            return recommendations
        
        # Resolution recommendations
        if analysis["width"] < 3840:
            recommendations.append({
                "type": "quality",
                "message": "Consider upscaling to 4K minimum for VR viewing comfort."
            })
        elif analysis["width"] >= 7680:
            recommendations.append({
                "type": "performance",
                "message": "8K+ content detected. Use tiled processing for memory efficiency."
            })
        
        # Frame rate recommendations
        if analysis["frame_rate"] < 60:
            recommendations.append({
                "type": "vr_comfort",
                "message": "Consider 60fps minimum for VR to reduce motion sickness."
            })
        
        # Projection recommendations
        if analysis["detected_projection"] == SphericalProjection.EQUIRECTANGULAR:
            recommendations.extend([
                {
                    "type": "processing",
                    "message": "Equirectangular format detected. Good for general 360° playback."
                },
                {
                    "type": "optimization",
                    "message": "Consider cubemap conversion for VR headset optimization."
                }
            ])
        
        # Stereo recommendations
        if analysis["stereo_mode"] != SphericalStereoMode.MONO:
            recommendations.append({
                "type": "vr",
                "message": f"Stereoscopic content detected ({analysis['stereo_mode'].value}). Ensure proper VR metadata."
            })
        
        return recommendations
    
    async def convert_spherical_projection(
        self,
        input_path: str,
        output_path: str,
        input_projection: SphericalProjection,
        output_projection: SphericalProjection,
        stereo_mode: SphericalStereoMode = SphericalStereoMode.MONO,
        **kwargs
    ) -> Dict[str, Any]:
        """Convert between spherical projections"""
        
        try:
            start_time = datetime.utcnow()
            
            # Build FFmpeg command
            cmd = [self.ffmpeg_service.ffmpeg_path, "-i", input_path]
            
            # Add hardware acceleration if available
            if self.ffmpeg_service.enable_gpu:
                cmd.extend(self._get_gpu_args())
            
            # Build v360 filter chain
            v360_params = [
                f"input={input_projection.value}",
                f"output={output_projection.value}"
            ]
            
            # Add interpolation method
            interpolation = kwargs.get("interpolation", "cubic")
            v360_params.append(f"interp_method={interpolation}")
            
            # Add field of view adjustments if converting to perspective
            if output_projection == SphericalProjection.PERSPECTIVE:
                h_fov = kwargs.get("h_fov", 90)
                v_fov = kwargs.get("v_fov", 90)
                v360_params.extend([f"h_fov={h_fov}", f"v_fov={v_fov}"])
            
            # Add stereo handling
            if stereo_mode != SphericalStereoMode.MONO:
                if stereo_mode == SphericalStereoMode.SIDE_BY_SIDE:
                    v360_params.append("stereo=sbs")
                elif stereo_mode == SphericalStereoMode.TOP_BOTTOM:
                    v360_params.append("stereo=tb")
            
            # Apply v360 filter
            filter_chain = f"v360={':'.join(v360_params)}"
            cmd.extend(["-vf", filter_chain])
            
            # Codec settings
            codec = kwargs.get("codec", "libx264")
            cmd.extend(["-c:v", codec])
            
            if codec == "libx264":
                cmd.extend(["-preset", kwargs.get("preset", "medium")])
                cmd.extend(["-crf", str(kwargs.get("crf", 20))])
            elif codec == "libx265":
                cmd.extend(["-preset", kwargs.get("preset", "medium")])
                cmd.extend(["-crf", str(kwargs.get("crf", 18))])
            
            # Audio settings
            cmd.extend(["-c:a", kwargs.get("audio_codec", "aac")])
            
            cmd.append(output_path)
            
            # Execute conversion
            await self.ffmpeg_service.run_ffmpeg_command(cmd)
            
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Analyze output
            output_analysis = await self.analyze_spherical_video(output_path)
            
            return {
                "processing_time_seconds": processing_time,
                "input_projection": input_projection.value,
                "output_projection": output_projection.value,
                "stereo_mode": stereo_mode.value,
                "input_size_mb": os.path.getsize(input_path) / (1024 * 1024),
                "output_size_mb": os.path.getsize(output_path) / (1024 * 1024),
                "compression_ratio": os.path.getsize(input_path) / os.path.getsize(output_path),
                "output_analysis": output_analysis
            }
            
        except Exception as e:
            logger.error("spherical_conversion_failed", error=str(e))
            raise
    
    async def create_vr_optimized_versions(
        self,
        input_path: str,
        output_dir: str,
        target_headsets: List[VRHeadset] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Create VR-optimized versions for different headsets"""
        
        if target_headsets is None:
            target_headsets = [VRHeadset.GENERIC]
        
        try:
            results = {}
            base_name = Path(input_path).stem
            
            # Analyze input
            input_analysis = await self.analyze_spherical_video(input_path)
            
            if not input_analysis["is_spherical"]:
                raise InvalidMediaError("Input must be spherical video")
            
            for headset in target_headsets:
                headset_results = {}
                
                # Get headset-specific settings
                settings_map = self._get_headset_settings(headset)
                
                for quality, settings in settings_map.items():
                    output_filename = f"{base_name}_{headset.value}_{quality}.mp4"
                    output_path = os.path.join(output_dir, output_filename)
                    
                    # Convert with headset-specific settings
                    result = await self._create_vr_version(
                        input_path,
                        output_path,
                        settings,
                        input_analysis,
                        **kwargs
                    )
                    
                    headset_results[quality] = {
                        "path": output_path,
                        "settings": settings,
                        "result": result
                    }
                
                results[headset.value] = headset_results
            
            return {
                "input_analysis": input_analysis,
                "headset_versions": results,
                "total_versions": sum(len(versions) for versions in results.values())
            }
            
        except Exception as e:
            logger.error("vr_optimization_failed", error=str(e))
            raise
    
    def _get_headset_settings(self, headset: VRHeadset) -> Dict[str, Dict[str, Any]]:
        """Get headset-specific optimization settings"""
        
        base_settings = {
            "low": {"width": 3840, "height": 1920, "bitrate": "15M", "fps": 60},
            "medium": {"width": 5120, "height": 2560, "bitrate": "25M", "fps": 60},
            "high": {"width": 7680, "height": 3840, "bitrate": "40M", "fps": 90}
        }
        
        if headset == VRHeadset.OCULUS_QUEST:
            # Optimize for mobile processing
            return {
                "mobile": {"width": 3072, "height": 1536, "bitrate": "12M", "fps": 72},
                "performance": {"width": 3840, "height": 1920, "bitrate": "18M", "fps": 90}
            }
        elif headset == VRHeadset.OCULUS_RIFT:
            return {
                "comfort": {"width": 4096, "height": 2048, "bitrate": "20M", "fps": 90},
                "quality": {"width": 5760, "height": 2880, "bitrate": "35M", "fps": 90}
            }
        elif headset == VRHeadset.HTC_VIVE:
            return {
                "standard": {"width": 4320, "height": 2160, "bitrate": "22M", "fps": 90},
                "premium": {"width": 6480, "height": 3240, "bitrate": "38M", "fps": 120}
            }
        else:
            return base_settings
    
    async def _create_vr_version(
        self,
        input_path: str,
        output_path: str,
        settings: Dict[str, Any],
        input_analysis: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """Create a VR-optimized version"""
        
        start_time = datetime.utcnow()
        
        cmd = [self.ffmpeg_service.ffmpeg_path, "-i", input_path]
        
        # Add hardware acceleration if available
        if self.ffmpeg_service.enable_gpu:
            cmd.extend(self._get_gpu_args())
        
        # Video scaling and processing
        filters = []
        
        # Scale to target resolution
        target_width = settings["width"]
        target_height = settings["height"]
        filters.append(f"scale={target_width}:{target_height}")
        
        # Add frame rate conversion if needed
        target_fps = settings["fps"]
        if target_fps != input_analysis["frame_rate"]:
            filters.append(f"fps={target_fps}")
        
        # Apply filters
        if filters:
            cmd.extend(["-vf", ",".join(filters)])
        
        # Video codec settings
        cmd.extend([
            "-c:v", "libx264",
            "-profile:v", "high",
            "-level", "5.1",
            "-b:v", settings["bitrate"],
            "-maxrate", settings["bitrate"],
            "-bufsize", f"{int(settings['bitrate'][:-1]) * 2}M",
            "-preset", "slow",
            "-tune", "film"
        ])
        
        # Audio settings
        cmd.extend(["-c:a", "aac", "-b:a", "256k"])
        
        # VR-specific optimizations
        cmd.extend([
            "-movflags", "+faststart",  # Enable fast start for streaming
            "-avoid_negative_ts", "make_zero"
        ])
        
        cmd.append(output_path)
        
        # Execute processing
        await self.ffmpeg_service.run_ffmpeg_command(cmd)
        
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        return {
            "processing_time_seconds": processing_time,
            "target_resolution": f"{target_width}x{target_height}",
            "target_fps": target_fps,
            "target_bitrate": settings["bitrate"],
            "output_size_mb": os.path.getsize(output_path) / (1024 * 1024)
        }
    
    async def add_spatial_metadata(
        self,
        input_path: str,
        output_path: str,
        projection: SphericalProjection,
        stereo_mode: SphericalStereoMode = SphericalStereoMode.MONO,
        **kwargs
    ) -> Dict[str, Any]:
        """Add spatial media metadata to video"""
        
        try:
            start_time = datetime.utcnow()
            
            # Create spatial metadata
            spatial_metadata = SphericalVideoMetadata.create_spatial_media_metadata(
                projection=projection,
                stereo_mode=stereo_mode,
                **kwargs
            )
            
            # Copy video with metadata injection
            cmd = [
                self.ffmpeg_service.ffmpeg_path,
                "-i", input_path,
                "-c", "copy",  # Copy streams without re-encoding
                "-movflags", "+faststart"
            ]
            
            # Add spherical metadata
            if projection == SphericalProjection.EQUIRECTANGULAR:
                cmd.extend([
                    "-metadata:s:v:0", f"spherical-video=1",
                    "-metadata:s:v:0", f"projection=equirectangular"
                ])
            
            cmd.append(output_path)
            
            # Execute metadata injection
            await self.ffmpeg_service.run_ffmpeg_command(cmd)
            
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            return {
                "processing_time_seconds": processing_time,
                "spatial_metadata": spatial_metadata,
                "projection": projection.value,
                "stereo_mode": stereo_mode.value,
                "output_size_mb": os.path.getsize(output_path) / (1024 * 1024)
            }
            
        except Exception as e:
            logger.error("spatial_metadata_injection_failed", error=str(e))
            raise
    
    def _get_gpu_args(self) -> List[str]:
        """Get GPU acceleration arguments for spherical processing"""
        if self.ffmpeg_service.gpu_type.value == "nvidia":
            return ["-hwaccel", "cuda", "-hwaccel_output_format", "cuda"]
        elif self.ffmpeg_service.gpu_type.value == "intel":
            return ["-hwaccel", "qsv"]
        elif self.ffmpeg_service.gpu_type.value == "amd":
            return ["-hwaccel", "d3d11va"]
        else:
            return []
    
    async def get_spherical_capabilities(self) -> Dict[str, Any]:
        """Get spherical video processing capabilities"""
        return {
            "supported_projections": [p.value for p in SphericalProjection],
            "supported_stereo_modes": [s.value for s in SphericalStereoMode],
            "supported_headsets": [h.value for h in VRHeadset],
            "quality_presets": [q.value for q in SphericalQuality],
            "has_v360_filter": self.has_v360_filter,
            "has_spatial_media": self.has_spatial_media,
            "gpu_acceleration": self.ffmpeg_service.enable_gpu,
            "features": {
                "projection_conversion": True,
                "vr_optimization": True,
                "spatial_metadata": True,
                "stereoscopic_support": True,
                "content_analysis": True
            },
            "interpolation_methods": ["nearest", "bilinear", "bicubic", "lanczos"],
            "max_resolution": "8K (7680x3840)",
            "recommended_fps": [60, 90, 120]
        }


# Service instance
_spherical_video_service: Optional[SphericalVideoService] = None


async def get_spherical_video_service() -> SphericalVideoService:
    """Get or create spherical video service instance"""
    global _spherical_video_service
    
    if _spherical_video_service is None:
        from .ffmpeg_service import get_ffmpeg_service
        ffmpeg_service = await get_ffmpeg_service()
        _spherical_video_service = SphericalVideoService(ffmpeg_service)
    
    return _spherical_video_service