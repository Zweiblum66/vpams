"""
VR Content Service for handling immersive VR/AR content processing
"""

import os
import json
import asyncio
import subprocess
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
from datetime import datetime
import aiofiles
import numpy as np
from pathlib import Path

from ..core.logging import get_logger
from ..core.exceptions import ProxyGenerationError

logger = get_logger(__name__)


class VRContentType(Enum):
    """VR content types"""
    VR_180 = "vr180"
    VR_360 = "vr360"
    AR_OBJECT = "ar_object"
    VOLUMETRIC = "volumetric"
    LIGHT_FIELD = "light_field"
    HOLOGRAPHIC = "holographic"


class VRRenderMode(Enum):
    """VR rendering modes"""
    MONOSCOPIC = "monoscopic"
    STEREOSCOPIC_SBS = "stereoscopic_sbs"  # Side-by-side
    STEREOSCOPIC_TB = "stereoscopic_tb"    # Top-bottom
    STEREOSCOPIC_ANAGLYPH = "anaglyph"    # Red-cyan glasses
    MULTI_VIEW = "multi_view"              # For light field displays


class VRInteractionMode(Enum):
    """VR interaction modes"""
    PASSIVE = "passive"           # Just viewing
    GAZE_BASED = "gaze_based"    # Look to interact
    CONTROLLER = "controller"     # Hand controllers
    HAND_TRACKING = "hand_tracking"  # Optical hand tracking
    FULL_BODY = "full_body"      # Full body tracking


class VRPlatform(Enum):
    """VR/AR platforms"""
    OCULUS_QUEST = "oculus_quest"
    OCULUS_RIFT = "oculus_rift"
    HTC_VIVE = "htc_vive"
    VALVE_INDEX = "valve_index"
    PICO = "pico"
    PLAYSTATION_VR = "playstation_vr"
    WINDOWS_MR = "windows_mr"
    MAGIC_LEAP = "magic_leap"
    HOLOLENS = "hololens"
    APPLE_VISION_PRO = "apple_vision_pro"
    WEB_XR = "web_xr"


class VRCodec(Enum):
    """VR-optimized video codecs"""
    H264_VR = "h264_vr"
    H265_VR = "h265_vr"
    VP9_VR = "vp9_vr"
    AV1_VR = "av1_vr"


class VRContentService:
    """Service for processing VR/AR content"""
    
    def __init__(self):
        self.ffmpeg_path = "ffmpeg"
        self.ffprobe_path = "ffprobe"
        
        # VR platform specifications
        self.platform_specs = {
            VRPlatform.OCULUS_QUEST: {
                "max_resolution": "8192x4096",
                "preferred_fps": [72, 90, 120],
                "max_bitrate": 50000000,  # 50 Mbps
                "audio_channels": 8,       # Spatial audio
                "codec": VRCodec.H265_VR,
                "fov": 110,
                "ipd_range": (58, 72)      # Inter-pupillary distance in mm
            },
            VRPlatform.HTC_VIVE: {
                "max_resolution": "4096x4096",
                "preferred_fps": [90],
                "max_bitrate": 40000000,
                "audio_channels": 8,
                "codec": VRCodec.H264_VR,
                "fov": 110,
                "ipd_range": (60, 74)
            },
            VRPlatform.VALVE_INDEX: {
                "max_resolution": "8192x4096",
                "preferred_fps": [80, 90, 120, 144],
                "max_bitrate": 60000000,
                "audio_channels": 8,
                "codec": VRCodec.H265_VR,
                "fov": 130,
                "ipd_range": (58, 70)
            },
            VRPlatform.APPLE_VISION_PRO: {
                "max_resolution": "8192x4096",
                "preferred_fps": [90, 96],
                "max_bitrate": 100000000,  # 100 Mbps
                "audio_channels": 16,       # Advanced spatial audio
                "codec": VRCodec.H265_VR,
                "fov": 120,
                "ipd_range": (51, 75)
            }
        }
        
        # VR content presets
        self.vr_presets = {
            "vr_low": {
                "resolution": "2880x1440",
                "fps": 60,
                "bitrate": 10000000,
                "quality": "good"
            },
            "vr_medium": {
                "resolution": "4096x2048",
                "fps": 72,
                "bitrate": 20000000,
                "quality": "better"
            },
            "vr_high": {
                "resolution": "5760x2880",
                "fps": 90,
                "bitrate": 40000000,
                "quality": "best"
            },
            "vr_ultra": {
                "resolution": "8192x4096",
                "fps": 120,
                "bitrate": 80000000,
                "quality": "best"
            }
        }
    
    async def analyze_vr_content(self, input_path: str) -> Dict[str, Any]:
        """
        Analyze VR content and detect its properties
        
        Args:
            input_path: Path to VR content file
            
        Returns:
            Analysis results with VR content properties
        """
        try:
            # Get basic media info
            media_info = await self._get_media_info(input_path)
            
            # Detect VR content type
            content_type = await self._detect_vr_content_type(media_info)
            
            # Detect render mode (mono/stereo)
            render_mode = await self._detect_render_mode(media_info)
            
            # Analyze VR-specific metadata
            vr_metadata = await self._extract_vr_metadata(input_path)
            
            # Detect interaction requirements
            interaction_mode = await self._detect_interaction_mode(vr_metadata)
            
            # Calculate optimal platform settings
            platform_recommendations = await self._calculate_platform_recommendations(
                media_info, content_type
            )
            
            return {
                "content_type": content_type.value,
                "render_mode": render_mode.value,
                "interaction_mode": interaction_mode.value,
                "vr_metadata": vr_metadata,
                "platform_recommendations": platform_recommendations,
                "original_properties": {
                    "resolution": f"{media_info['width']}x{media_info['height']}",
                    "fps": media_info.get("fps", 30),
                    "duration": media_info.get("duration", 0),
                    "bitrate": media_info.get("bitrate", 0)
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze VR content: {e}")
            raise ProxyGenerationError(
                "VR_ANALYSIS_FAILED",
                f"Failed to analyze VR content: {str(e)}"
            )
    
    async def process_vr_content(
        self,
        input_path: str,
        output_path: str,
        platform: VRPlatform,
        preset: str = "vr_high",
        custom_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process VR content for specific platform
        
        Args:
            input_path: Path to input VR content
            output_path: Path for processed output
            platform: Target VR platform
            preset: Quality preset
            custom_params: Custom processing parameters
            
        Returns:
            Processing results
        """
        try:
            # Get platform specifications
            platform_spec = self.platform_specs.get(platform)
            if not platform_spec:
                raise ValueError(f"Unsupported platform: {platform}")
            
            # Get preset configuration
            preset_config = self.vr_presets.get(preset, self.vr_presets["vr_high"])
            
            # Merge custom parameters
            if custom_params:
                preset_config.update(custom_params)
            
            # Build FFmpeg command
            cmd = await self._build_vr_processing_command(
                input_path, output_path, platform_spec, preset_config
            )
            
            # Execute processing
            start_time = datetime.utcnow()
            await self._execute_ffmpeg_command(cmd)
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Add VR metadata
            await self._inject_vr_metadata(output_path, platform, preset_config)
            
            # Verify output
            output_info = await self._get_media_info(output_path)
            
            return {
                "platform": platform.value,
                "preset": preset,
                "output_resolution": f"{output_info['width']}x{output_info['height']}",
                "output_fps": output_info.get("fps", preset_config["fps"]),
                "output_bitrate": output_info.get("bitrate", preset_config["bitrate"]),
                "processing_time": processing_time,
                "file_size": os.path.getsize(output_path)
            }
            
        except Exception as e:
            logger.error(f"Failed to process VR content: {e}")
            raise ProxyGenerationError(
                "VR_PROCESSING_FAILED",
                f"Failed to process VR content: {str(e)}"
            )
    
    async def create_vr_preview(
        self,
        input_path: str,
        output_path: str,
        preview_type: str = "flat",
        duration: int = 30
    ) -> Dict[str, Any]:
        """
        Create preview of VR content for non-VR displays
        
        Args:
            input_path: Path to VR content
            output_path: Path for preview output
            preview_type: Type of preview (flat, little_planet, etc.)
            duration: Preview duration in seconds
            
        Returns:
            Preview creation results
        """
        try:
            preview_commands = {
                "flat": [
                    "-vf", "v360=input=e:output=flat:pitch=-10:yaw=0:roll=0:w=1920:h=1080"
                ],
                "little_planet": [
                    "-vf", "v360=input=e:output=sg:w=1920:h=1080"
                ],
                "panoramic": [
                    "-vf", "v360=input=e:output=pannini:w=2560:h=1440"
                ],
                "cube_map": [
                    "-vf", "v360=input=e:output=c3x2:w=3840:h=2560"
                ]
            }
            
            filters = preview_commands.get(preview_type, preview_commands["flat"])
            
            cmd = [
                self.ffmpeg_path,
                "-i", input_path,
                "-t", str(duration),
                *filters,
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "23",
                "-c:a", "aac",
                "-b:a", "128k",
                "-movflags", "+faststart",
                "-y", output_path
            ]
            
            await self._execute_ffmpeg_command(cmd)
            
            return {
                "preview_type": preview_type,
                "duration": duration,
                "output_path": output_path,
                "file_size": os.path.getsize(output_path)
            }
            
        except Exception as e:
            logger.error(f"Failed to create VR preview: {e}")
            raise ProxyGenerationError(
                "VR_PREVIEW_FAILED",
                f"Failed to create VR preview: {str(e)}"
            )
    
    async def extract_vr_motion_data(self, input_path: str) -> Dict[str, Any]:
        """
        Extract motion and tracking data from VR content
        
        Args:
            input_path: Path to VR content
            
        Returns:
            Motion data including head tracking, controller data, etc.
        """
        try:
            # Extract metadata tracks
            cmd = [
                self.ffprobe_path,
                "-v", "quiet",
                "-print_format", "json",
                "-show_streams",
                "-show_data",
                input_path
            ]
            
            result = await self._execute_command(cmd)
            probe_data = json.loads(result)
            
            motion_data = {
                "head_tracking": [],
                "controller_tracking": [],
                "eye_tracking": [],
                "body_tracking": []
            }
            
            # Parse data streams for motion information
            for stream in probe_data.get("streams", []):
                if stream.get("codec_type") == "data":
                    codec_name = stream.get("codec_name", "")
                    
                    if "head" in codec_name.lower():
                        motion_data["head_tracking"].append({
                            "stream_index": stream.get("index"),
                            "codec": codec_name,
                            "tags": stream.get("tags", {})
                        })
                    elif "controller" in codec_name.lower():
                        motion_data["controller_tracking"].append({
                            "stream_index": stream.get("index"),
                            "codec": codec_name,
                            "tags": stream.get("tags", {})
                        })
                    elif "eye" in codec_name.lower():
                        motion_data["eye_tracking"].append({
                            "stream_index": stream.get("index"),
                            "codec": codec_name,
                            "tags": stream.get("tags", {})
                        })
            
            return motion_data
            
        except Exception as e:
            logger.error(f"Failed to extract VR motion data: {e}")
            return {
                "head_tracking": [],
                "controller_tracking": [],
                "eye_tracking": [],
                "body_tracking": []
            }
    
    async def optimize_for_streaming(
        self,
        input_path: str,
        output_path: str,
        streaming_type: str = "adaptive"
    ) -> Dict[str, Any]:
        """
        Optimize VR content for streaming
        
        Args:
            input_path: Path to VR content
            output_path: Path for optimized output
            streaming_type: Type of streaming (adaptive, low_latency, etc.)
            
        Returns:
            Optimization results
        """
        try:
            if streaming_type == "adaptive":
                # Create multiple quality levels for adaptive streaming
                quality_levels = [
                    {"resolution": "2880x1440", "bitrate": 8000000},
                    {"resolution": "4096x2048", "bitrate": 16000000},
                    {"resolution": "5760x2880", "bitrate": 32000000}
                ]
                
                outputs = []
                for i, level in enumerate(quality_levels):
                    level_output = output_path.replace(".mp4", f"_{i}.mp4")
                    
                    cmd = [
                        self.ffmpeg_path,
                        "-i", input_path,
                        "-vf", f"scale={level['resolution']}",
                        "-c:v", "libx265",
                        "-preset", "fast",
                        "-b:v", str(level["bitrate"]),
                        "-c:a", "aac",
                        "-b:a", "256k",
                        "-movflags", "+faststart",
                        "-y", level_output
                    ]
                    
                    await self._execute_ffmpeg_command(cmd)
                    outputs.append({
                        "path": level_output,
                        "resolution": level["resolution"],
                        "bitrate": level["bitrate"]
                    })
                
                return {
                    "streaming_type": streaming_type,
                    "quality_levels": outputs
                }
                
            elif streaming_type == "low_latency":
                # Optimize for low latency streaming
                cmd = [
                    self.ffmpeg_path,
                    "-i", input_path,
                    "-c:v", "libx264",
                    "-preset", "ultrafast",
                    "-tune", "zerolatency",
                    "-b:v", "20M",
                    "-c:a", "aac",
                    "-b:a", "256k",
                    "-f", "mp4",
                    "-movflags", "+faststart+frag_keyframe+empty_moov",
                    "-y", output_path
                ]
                
                await self._execute_ffmpeg_command(cmd)
                
                return {
                    "streaming_type": streaming_type,
                    "output_path": output_path,
                    "optimizations": ["zero_latency", "fast_start", "fragmented"]
                }
            
            else:
                raise ValueError(f"Unknown streaming type: {streaming_type}")
                
        except Exception as e:
            logger.error(f"Failed to optimize for streaming: {e}")
            raise ProxyGenerationError(
                "VR_STREAMING_OPTIMIZATION_FAILED",
                f"Failed to optimize for streaming: {str(e)}"
            )
    
    async def create_vr_thumbnail_sequence(
        self,
        input_path: str,
        output_dir: str,
        count: int = 12,
        preview_angles: Optional[List[Tuple[float, float]]] = None
    ) -> Dict[str, Any]:
        """
        Create thumbnail sequence showing different viewpoints
        
        Args:
            input_path: Path to VR content
            output_dir: Directory for thumbnail outputs
            count: Number of thumbnails
            preview_angles: List of (yaw, pitch) angles
            
        Returns:
            Thumbnail creation results
        """
        try:
            os.makedirs(output_dir, exist_ok=True)
            
            # Default preview angles if not specified
            if not preview_angles:
                preview_angles = [
                    (0, 0),      # Front
                    (90, 0),     # Right
                    (180, 0),    # Back
                    (270, 0),    # Left
                    (0, 45),     # Up
                    (0, -45),    # Down
                    (45, 0),     # Front-right
                    (135, 0),    # Back-right
                    (225, 0),    # Back-left
                    (315, 0),    # Front-left
                    (0, 90),     # Top
                    (0, -90)     # Bottom
                ][:count]
            
            thumbnails = []
            for i, (yaw, pitch) in enumerate(preview_angles):
                output_path = os.path.join(output_dir, f"thumb_{i:03d}.jpg")
                
                cmd = [
                    self.ffmpeg_path,
                    "-i", input_path,
                    "-ss", "00:00:05",  # Skip first 5 seconds
                    "-vframes", "1",
                    "-vf", f"v360=input=e:output=flat:yaw={yaw}:pitch={pitch}:w=640:h=360",
                    "-q:v", "2",
                    "-y", output_path
                ]
                
                await self._execute_ffmpeg_command(cmd)
                
                thumbnails.append({
                    "path": output_path,
                    "yaw": yaw,
                    "pitch": pitch,
                    "index": i
                })
            
            return {
                "count": len(thumbnails),
                "thumbnails": thumbnails,
                "output_dir": output_dir
            }
            
        except Exception as e:
            logger.error(f"Failed to create VR thumbnail sequence: {e}")
            raise ProxyGenerationError(
                "VR_THUMBNAIL_FAILED",
                f"Failed to create VR thumbnail sequence: {str(e)}"
            )
    
    async def _detect_vr_content_type(self, media_info: Dict[str, Any]) -> VRContentType:
        """Detect type of VR content"""
        width = media_info.get("width", 0)
        height = media_info.get("height", 0)
        
        # Check aspect ratio
        if width and height:
            aspect_ratio = width / height
            
            if aspect_ratio >= 1.9:  # Close to 2:1
                return VRContentType.VR_360
            elif 0.9 <= aspect_ratio <= 1.1:  # Close to 1:1
                return VRContentType.VR_180
        
        # Check metadata for clues
        metadata = media_info.get("metadata", {})
        if "spherical" in str(metadata).lower():
            return VRContentType.VR_360
        elif "volumetric" in str(metadata).lower():
            return VRContentType.VOLUMETRIC
        
        # Default to VR 360
        return VRContentType.VR_360
    
    async def _detect_render_mode(self, media_info: Dict[str, Any]) -> VRRenderMode:
        """Detect rendering mode (mono/stereo)"""
        height = media_info.get("height", 0)
        
        # Check for stereoscopic indicators
        metadata = media_info.get("metadata", {})
        if "stereo" in str(metadata).lower():
            if "side" in str(metadata).lower():
                return VRRenderMode.STEREOSCOPIC_SBS
            elif "top" in str(metadata).lower():
                return VRRenderMode.STEREOSCOPIC_TB
        
        # Check resolution patterns
        if height and height % 2 == 0:
            # Could be top-bottom stereo
            test_height = height // 2
            if test_height in [1080, 1440, 2160, 2880]:
                return VRRenderMode.STEREOSCOPIC_TB
        
        return VRRenderMode.MONOSCOPIC
    
    async def _extract_vr_metadata(self, input_path: str) -> Dict[str, Any]:
        """Extract VR-specific metadata"""
        try:
            cmd = [
                self.ffprobe_path,
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                input_path
            ]
            
            result = await self._execute_command(cmd)
            probe_data = json.loads(result)
            
            vr_metadata = {}
            
            # Extract format metadata
            format_tags = probe_data.get("format", {}).get("tags", {})
            for key, value in format_tags.items():
                if any(vr_key in key.lower() for vr_key in ["spherical", "stereo", "projection", "vr"]):
                    vr_metadata[key] = value
            
            # Extract stream metadata
            for stream in probe_data.get("streams", []):
                stream_tags = stream.get("tags", {})
                for key, value in stream_tags.items():
                    if any(vr_key in key.lower() for vr_key in ["spherical", "stereo", "projection", "vr"]):
                        vr_metadata[f"stream_{stream['index']}_{key}"] = value
            
            return vr_metadata
            
        except Exception as e:
            logger.error(f"Failed to extract VR metadata: {e}")
            return {}
    
    async def _detect_interaction_mode(self, metadata: Dict[str, Any]) -> VRInteractionMode:
        """Detect required interaction mode"""
        metadata_str = str(metadata).lower()
        
        if "hand_tracking" in metadata_str:
            return VRInteractionMode.HAND_TRACKING
        elif "controller" in metadata_str:
            return VRInteractionMode.CONTROLLER
        elif "gaze" in metadata_str or "eye" in metadata_str:
            return VRInteractionMode.GAZE_BASED
        elif "body" in metadata_str:
            return VRInteractionMode.FULL_BODY
        
        return VRInteractionMode.PASSIVE
    
    async def _calculate_platform_recommendations(
        self,
        media_info: Dict[str, Any],
        content_type: VRContentType
    ) -> Dict[str, Any]:
        """Calculate recommendations for different VR platforms"""
        recommendations = {}
        
        for platform, spec in self.platform_specs.items():
            # Check resolution compatibility
            max_res = spec["max_resolution"].split("x")
            max_width = int(max_res[0])
            max_height = int(max_res[1])
            
            current_width = media_info.get("width", 0)
            current_height = media_info.get("height", 0)
            
            if current_width <= max_width and current_height <= max_height:
                compatibility = "full"
            else:
                compatibility = "requires_downscale"
            
            # Find best matching FPS
            current_fps = media_info.get("fps", 30)
            best_fps = min(spec["preferred_fps"], key=lambda x: abs(x - current_fps))
            
            recommendations[platform.value] = {
                "compatibility": compatibility,
                "recommended_fps": best_fps,
                "recommended_codec": spec["codec"].value,
                "max_bitrate": spec["max_bitrate"],
                "audio_channels": spec["audio_channels"]
            }
        
        return recommendations
    
    async def _build_vr_processing_command(
        self,
        input_path: str,
        output_path: str,
        platform_spec: Dict[str, Any],
        preset_config: Dict[str, Any]
    ) -> List[str]:
        """Build FFmpeg command for VR processing"""
        codec = platform_spec["codec"].value
        
        # Base command
        cmd = [
            self.ffmpeg_path,
            "-i", input_path,
            "-map", "0:v:0",  # Video stream
            "-map", "0:a?",   # Audio streams (if present)
            "-map", "0:d?",   # Data streams (motion data)
        ]
        
        # Video encoding parameters
        if "h264" in codec:
            cmd.extend([
                "-c:v", "libx264",
                "-preset", "slow",
                "-profile:v", "high",
                "-level", "5.2"
            ])
        elif "h265" in codec:
            cmd.extend([
                "-c:v", "libx265",
                "-preset", "slow",
                "-profile:v", "main",
                "-level", "5.1"
            ])
        elif "vp9" in codec:
            cmd.extend([
                "-c:v", "libvpx-vp9",
                "-quality", "good",
                "-speed", "1"
            ])
        elif "av1" in codec:
            cmd.extend([
                "-c:v", "libsvtav1",
                "-preset", "4",
                "-crf", "30"
            ])
        
        # Resolution and framerate
        cmd.extend([
            "-vf", f"scale={preset_config['resolution']}:flags=lanczos",
            "-r", str(preset_config["fps"]),
            "-b:v", str(preset_config["bitrate"])
        ])
        
        # Audio encoding - spatial audio support
        audio_channels = platform_spec.get("audio_channels", 2)
        if audio_channels > 2:
            cmd.extend([
                "-c:a", "libopus",
                "-b:a", "256k",
                "-ac", str(audio_channels),
                "-mapping_family", "1"  # Ambisonic mapping for spatial audio
            ])
        else:
            cmd.extend([
                "-c:a", "aac",
                "-b:a", "192k",
                "-ac", "2"
            ])
        
        # Data stream passthrough (for motion data)
        cmd.extend(["-c:d", "copy"])
        
        # Output flags
        cmd.extend([
            "-movflags", "+faststart",
            "-y", output_path
        ])
        
        return cmd
    
    async def _inject_vr_metadata(
        self,
        file_path: str,
        platform: VRPlatform,
        config: Dict[str, Any]
    ) -> None:
        """Inject VR metadata into file"""
        try:
            # Create metadata file
            metadata = {
                "vr_platform": platform.value,
                "resolution": config["resolution"],
                "fps": config["fps"],
                "bitrate": config["bitrate"],
                "processed_date": datetime.utcnow().isoformat(),
                "mams_vr_version": "1.0"
            }
            
            metadata_file = file_path + ".vr_meta"
            async with aiofiles.open(metadata_file, 'w') as f:
                await f.write(json.dumps(metadata, indent=2))
            
            # For MP4 files, we could also inject metadata atoms
            # This would require additional tools or libraries
            
        except Exception as e:
            logger.warning(f"Failed to inject VR metadata: {e}")
    
    async def _get_media_info(self, file_path: str) -> Dict[str, Any]:
        """Get media file information"""
        cmd = [
            self.ffprobe_path,
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            file_path
        ]
        
        result = await self._execute_command(cmd)
        probe_data = json.loads(result)
        
        # Extract relevant information
        video_stream = next(
            (s for s in probe_data.get("streams", []) if s["codec_type"] == "video"),
            {}
        )
        
        format_info = probe_data.get("format", {})
        
        # Calculate FPS
        fps = 30  # Default
        if "r_frame_rate" in video_stream:
            try:
                num, den = map(int, video_stream["r_frame_rate"].split("/"))
                fps = num / den if den > 0 else 30
            except:
                pass
        
        return {
            "width": video_stream.get("width", 0),
            "height": video_stream.get("height", 0),
            "fps": fps,
            "duration": float(format_info.get("duration", 0)),
            "bitrate": int(format_info.get("bit_rate", 0)),
            "format": format_info.get("format_name", ""),
            "metadata": {**format_info.get("tags", {}), **video_stream.get("tags", {})}
        }
    
    async def _execute_command(self, cmd: List[str]) -> str:
        """Execute command and return output"""
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise RuntimeError(f"Command failed: {stderr.decode()}")
        
        return stdout.decode()
    
    async def _execute_ffmpeg_command(self, cmd: List[str]) -> None:
        """Execute FFmpeg command"""
        logger.info(f"Executing FFmpeg command: {' '.join(cmd)}")
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            error_msg = stderr.decode()
            logger.error(f"FFmpeg command failed: {error_msg}")
            raise RuntimeError(f"FFmpeg failed: {error_msg}")
        
        logger.info("FFmpeg command completed successfully")