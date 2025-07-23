"""
FFmpeg Service for video/audio processing
"""

import os
import asyncio
import json
import platform
from typing import Dict, List, Optional, Tuple, Any, Union
from pathlib import Path
import shutil
import tempfile
from enum import Enum

from ..core.config import settings
from ..core.exceptions import FFmpegError, InvalidMediaError, ProcessingTimeoutError
from ..core.logging import get_logger

logger = get_logger(__name__)


class GPUType(str, Enum):
    """Supported GPU acceleration types"""
    NVIDIA = "nvidia"
    AMD = "amd"
    INTEL = "intel"
    APPLE = "apple"
    NONE = "none"


class GPUCodec:
    """GPU-accelerated codec mappings"""
    NVIDIA = {
        "h264": "h264_nvenc",
        "h265": "hevc_nvenc",
        "av1": "av1_nvenc",
        "vp9": "vp9_nvenc"
    }
    AMD = {
        "h264": "h264_amf",
        "h265": "hevc_amf",
        "av1": "av1_amf"
    }
    INTEL = {
        "h264": "h264_qsv",
        "h265": "hevc_qsv",
        "av1": "av1_qsv",
        "vp9": "vp9_qsv"
    }
    APPLE = {
        "h264": "h264_videotoolbox",
        "h265": "hevc_videotoolbox"
    }


class FFmpegService:
    """Service for FFmpeg-based media processing with GPU acceleration"""
    
    def __init__(self):
        self.ffmpeg_path = settings.ffmpeg_path
        self.ffprobe_path = settings.ffprobe_path
        self.threads = settings.ffmpeg_threads
        self.enable_gpu = settings.enable_gpu_acceleration
        self.gpu_device = settings.gpu_device
        
        # GPU detection
        self.gpu_type = GPUType.NONE
        self.gpu_info = {}
        self.available_gpu_codecs = []
        
        # Verify FFmpeg installation
        self._verify_ffmpeg()
        
        # Detect GPU capabilities if enabled
        if self.enable_gpu:
            self._detect_gpu_capabilities()
    
    def _verify_ffmpeg(self):
        """Verify FFmpeg and FFprobe are available"""
        for tool, path in [("FFmpeg", self.ffmpeg_path), ("FFprobe", self.ffprobe_path)]:
            if not shutil.which(path):
                raise FFmpegError(f"{tool} not found at path: {path}")
    
    def _detect_gpu_capabilities(self):
        """Detect available GPU acceleration capabilities"""
        system = platform.system().lower()
        
        # Try to detect GPU type and capabilities
        if system == "darwin":  # macOS
            self._detect_apple_gpu()
        elif system == "linux":
            self._detect_linux_gpu()
        elif system == "windows":
            self._detect_windows_gpu()
        
        # Get available encoders from FFmpeg
        self._detect_ffmpeg_encoders()
        
        logger.info(
            "gpu_capabilities_detected",
            gpu_type=self.gpu_type,
            gpu_info=self.gpu_info,
            available_codecs=self.available_gpu_codecs
        )
    
    def _detect_apple_gpu(self):
        """Detect Apple GPU (VideoToolbox)"""
        try:
            # Check if VideoToolbox is available
            import subprocess
            result = subprocess.run(
                [self.ffmpeg_path, '-encoders'],
                capture_output=True,
                text=True
            )
            
            if 'h264_videotoolbox' in result.stdout:
                self.gpu_type = GPUType.APPLE
                self.gpu_info = {
                    "type": "Apple VideoToolbox",
                    "available": True
                }
        except Exception as e:
            logger.debug(f"Apple GPU detection failed: {e}")
    
    def _detect_linux_gpu(self):
        """Detect GPU on Linux (NVIDIA, AMD, Intel)"""
        # Try NVIDIA first
        if self._detect_nvidia_gpu():
            return
        
        # Try Intel
        if self._detect_intel_gpu():
            return
        
        # Try AMD
        if self._detect_amd_gpu():
            return
    
    def _detect_windows_gpu(self):
        """Detect GPU on Windows"""
        # Similar to Linux, try each vendor
        if self._detect_nvidia_gpu():
            return
        
        if self._detect_intel_gpu():
            return
        
        if self._detect_amd_gpu():
            return
    
    def _detect_nvidia_gpu(self) -> bool:
        """Detect NVIDIA GPU"""
        try:
            import subprocess
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=name,memory.total,driver_version', '--format=csv,noheader'],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                gpu_info = result.stdout.strip().split(', ')
                self.gpu_type = GPUType.NVIDIA
                self.gpu_info = {
                    "name": gpu_info[0],
                    "memory": gpu_info[1],
                    "driver_version": gpu_info[2] if len(gpu_info) > 2 else "unknown",
                    "device": self.gpu_device or "0"
                }
                return True
        except Exception as e:
            logger.debug(f"NVIDIA GPU detection failed: {e}")
        
        return False
    
    def _detect_intel_gpu(self) -> bool:
        """Detect Intel GPU (Quick Sync)"""
        try:
            # Check for Intel GPU by looking for Quick Sync support
            import subprocess
            
            # Check if vainfo is available (Linux)
            if shutil.which('vainfo'):
                result = subprocess.run(['vainfo'], capture_output=True, text=True)
                if result.returncode == 0 and 'Intel' in result.stdout:
                    self.gpu_type = GPUType.INTEL
                    self.gpu_info = {
                        "name": "Intel Quick Sync",
                        "available": True
                    }
                    return True
            
            # Check FFmpeg for QSV support
            result = subprocess.run(
                [self.ffmpeg_path, '-encoders'],
                capture_output=True,
                text=True
            )
            
            if 'h264_qsv' in result.stdout:
                self.gpu_type = GPUType.INTEL
                self.gpu_info = {
                    "name": "Intel Quick Sync",
                    "available": True
                }
                return True
                
        except Exception as e:
            logger.debug(f"Intel GPU detection failed: {e}")
        
        return False
    
    def _detect_amd_gpu(self) -> bool:
        """Detect AMD GPU"""
        try:
            # Check for AMD GPU
            import subprocess
            
            # Try rocm-smi for AMD GPUs (Linux)
            if shutil.which('rocm-smi'):
                result = subprocess.run(['rocm-smi', '--showproductname'], capture_output=True, text=True)
                if result.returncode == 0:
                    self.gpu_type = GPUType.AMD
                    self.gpu_info = {
                        "name": "AMD GPU",
                        "available": True
                    }
                    return True
            
            # Check FFmpeg for AMF support
            result = subprocess.run(
                [self.ffmpeg_path, '-encoders'],
                capture_output=True,
                text=True
            )
            
            if 'h264_amf' in result.stdout:
                self.gpu_type = GPUType.AMD
                self.gpu_info = {
                    "name": "AMD AMF",
                    "available": True
                }
                return True
                
        except Exception as e:
            logger.debug(f"AMD GPU detection failed: {e}")
        
        return False
    
    def _detect_ffmpeg_encoders(self):
        """Detect available GPU encoders in FFmpeg"""
        try:
            import subprocess
            result = subprocess.run(
                [self.ffmpeg_path, '-encoders'],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                output = result.stdout
                
                # Check for available GPU encoders
                gpu_encoders = {
                    "h264_nvenc": "NVIDIA H.264",
                    "hevc_nvenc": "NVIDIA H.265/HEVC",
                    "av1_nvenc": "NVIDIA AV1",
                    "h264_amf": "AMD H.264",
                    "hevc_amf": "AMD H.265/HEVC",
                    "h264_qsv": "Intel H.264",
                    "hevc_qsv": "Intel H.265/HEVC",
                    "h264_videotoolbox": "Apple H.264",
                    "hevc_videotoolbox": "Apple H.265/HEVC"
                }
                
                for encoder, name in gpu_encoders.items():
                    if encoder in output:
                        self.available_gpu_codecs.append({
                            "encoder": encoder,
                            "name": name
                        })
                        
        except Exception as e:
            logger.error(f"Failed to detect FFmpeg encoders: {e}")
    
    async def get_media_info(self, input_path: str) -> Dict[str, Any]:
        """Get detailed media information using ffprobe"""
        try:
            cmd = [
                self.ffprobe_path,
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                input_path
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise FFmpegError(
                    f"FFprobe failed: {stderr.decode()}",
                    details={"returncode": process.returncode}
                )
            
            media_info = json.loads(stdout.decode())
            
            # Extract key information
            result = {
                "format": media_info.get("format", {}),
                "duration": float(media_info.get("format", {}).get("duration", 0)),
                "size": int(media_info.get("format", {}).get("size", 0)),
                "bit_rate": int(media_info.get("format", {}).get("bit_rate", 0)),
                "streams": []
            }
            
            # Process streams
            for stream in media_info.get("streams", []):
                stream_info = {
                    "index": stream.get("index"),
                    "codec_type": stream.get("codec_type"),
                    "codec_name": stream.get("codec_name"),
                    "codec_long_name": stream.get("codec_long_name")
                }
                
                if stream.get("codec_type") == "video":
                    stream_info.update({
                        "width": stream.get("width"),
                        "height": stream.get("height"),
                        "aspect_ratio": stream.get("display_aspect_ratio"),
                        "frame_rate": stream.get("r_frame_rate"),
                        "bit_rate": stream.get("bit_rate"),
                        "pix_fmt": stream.get("pix_fmt")
                    })
                elif stream.get("codec_type") == "audio":
                    stream_info.update({
                        "sample_rate": stream.get("sample_rate"),
                        "channels": stream.get("channels"),
                        "channel_layout": stream.get("channel_layout"),
                        "bit_rate": stream.get("bit_rate")
                    })
                
                result["streams"].append(stream_info)
            
            # Validate media
            if not result["streams"]:
                raise InvalidMediaError("No valid streams found in media file")
            
            return result
            
        except json.JSONDecodeError as e:
            raise FFmpegError(f"Failed to parse ffprobe output: {str(e)}")
        except Exception as e:
            if isinstance(e, (FFmpegError, InvalidMediaError)):
                raise
            raise FFmpegError(f"Failed to get media info: {str(e)}")
    
    def _get_gpu_encoder(self, codec_name: str) -> Optional[str]:
        """Get GPU encoder for given codec based on detected GPU type"""
        if self.gpu_type == GPUType.NONE:
            return None
        
        # Map generic codec names to specific formats
        codec_map = {
            "h264": "h264",
            "libx264": "h264",
            "h265": "h265",
            "libx265": "h265",
            "hevc": "h265",
            "av1": "av1",
            "vp9": "vp9"
        }
        
        # Get base codec
        base_codec = codec_map.get(codec_name.lower(), codec_name.lower())
        
        # Get GPU-specific encoder
        gpu_codecs = {
            GPUType.NVIDIA: GPUCodec.NVIDIA,
            GPUType.AMD: GPUCodec.AMD,
            GPUType.INTEL: GPUCodec.INTEL,
            GPUType.APPLE: GPUCodec.APPLE
        }
        
        codec_mapping = gpu_codecs.get(self.gpu_type, {})
        gpu_encoder = codec_mapping.get(base_codec)
        
        # Check if encoder is available
        if gpu_encoder:
            for available in self.available_gpu_codecs:
                if available["encoder"] == gpu_encoder:
                    return gpu_encoder
        
        return None
    
    def _get_gpu_acceleration_params(self) -> List[str]:
        """Get GPU acceleration parameters based on detected GPU"""
        params = []
        
        if self.gpu_type == GPUType.NVIDIA:
            params.extend(['-hwaccel', 'cuda'])
            if self.gpu_device:
                params.extend(['-hwaccel_device', self.gpu_device])
            params.extend(['-hwaccel_output_format', 'cuda'])
            
        elif self.gpu_type == GPUType.INTEL:
            params.extend(['-hwaccel', 'qsv'])
            params.extend(['-hwaccel_output_format', 'qsv'])
            
        elif self.gpu_type == GPUType.AMD:
            # AMD uses different acceleration methods depending on platform
            if platform.system().lower() == "windows":
                params.extend(['-hwaccel', 'd3d11va'])
            else:
                params.extend(['-hwaccel', 'vaapi'])
                
        elif self.gpu_type == GPUType.APPLE:
            params.extend(['-hwaccel', 'videotoolbox'])
            params.extend(['-hwaccel_output_format', 'videotoolbox_vld'])
        
        return params
    
    def _get_gpu_scaling_filter(self, width: int, height: int) -> str:
        """Get GPU-optimized scaling filter based on GPU type"""
        if self.gpu_type == GPUType.NVIDIA:
            # Use CUDA scaling
            return f'scale_cuda={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black'
        elif self.gpu_type == GPUType.INTEL:
            # Use QSV scaling
            return f'scale_qsv={width}:{height}:mode=hq'
        elif self.gpu_type == GPUType.AMD:
            # Use standard scaling (AMF doesn't have special scaling)
            return f'scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2'
        elif self.gpu_type == GPUType.APPLE:
            # Use VideoToolbox scaling
            return f'scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2'
        else:
            # Fallback to software scaling
            return f'scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2'
    
    async def generate_video_proxy(
        self,
        input_path: str,
        output_path: str,
        preset: str = "medium",
        custom_options: Optional[Dict[str, Any]] = None,
        force_gpu: bool = True
    ) -> Dict[str, Any]:
        """Generate video proxy with GPU acceleration support"""
        try:
            # Get preset configuration
            preset_config = settings.video_presets.get(preset, settings.video_presets["medium"])
            
            # Build FFmpeg command
            cmd = [self.ffmpeg_path]
            
            # Add hardware acceleration if enabled and available
            use_gpu = False
            if self.enable_gpu and self.gpu_type != GPUType.NONE and force_gpu:
                gpu_params = self._get_gpu_acceleration_params()
                cmd.extend(gpu_params)
                use_gpu = True
            
            # Input file
            cmd.extend(['-i', input_path])
            
            # Video codec and settings
            video_codec = preset_config.get("video_codec", settings.default_video_codec)
            
            # Try to use GPU encoder if available
            gpu_encoder = None
            if use_gpu:
                gpu_encoder = self._get_gpu_encoder(video_codec)
                if gpu_encoder:
                    video_codec = gpu_encoder
                    logger.info(f"Using GPU encoder: {gpu_encoder}")
                else:
                    logger.info(f"GPU encoder not available for {video_codec}, falling back to software encoding")
            
            cmd.extend(['-c:v', video_codec])
            
            # GPU-specific encoding parameters
            if gpu_encoder:
                if self.gpu_type == GPUType.NVIDIA:
                    # NVIDIA NVENC specific options
                    cmd.extend([
                        '-preset', preset_config.get("gpu_preset", "p4"),  # p1-p7, higher = better quality
                        '-tune', 'hq',  # High quality tuning
                        '-rc', 'vbr',  # Variable bitrate
                        '-cq', '23',  # Constant quality (like CRF)
                        '-b:v', preset_config.get("video_bitrate", "2M"),
                        '-maxrate', preset_config.get("max_bitrate", "3M"),
                        '-bufsize', preset_config.get("buffer_size", "4M")
                    ])
                elif self.gpu_type == GPUType.INTEL:
                    # Intel QSV specific options
                    cmd.extend([
                        '-preset', preset_config.get("gpu_preset", "medium"),
                        '-global_quality', '23',
                        '-look_ahead', '1'
                    ])
                elif self.gpu_type == GPUType.AMD:
                    # AMD AMF specific options
                    cmd.extend([
                        '-quality', preset_config.get("gpu_preset", "balanced"),
                        '-rc', 'vbr_peak',
                        '-b:v', preset_config.get("video_bitrate", "2M")
                    ])
                elif self.gpu_type == GPUType.APPLE:
                    # Apple VideoToolbox specific options
                    cmd.extend([
                        '-profile:v', 'high',
                        '-b:v', preset_config.get("video_bitrate", "2M")
                    ])
            else:
                # Software encoding options
                if "video_bitrate" in preset_config:
                    cmd.extend(['-b:v', preset_config["video_bitrate"]])
                
                # Encoding preset for software encoders
                if "preset" in preset_config and video_codec in ['libx264', 'libx265']:
                    cmd.extend(['-preset', preset_config["preset"]])
            
            # Resolution with GPU-optimized scaling
            if preset_config.get("width") and preset_config.get("height"):
                if use_gpu and gpu_encoder:
                    scale_filter = self._get_gpu_scaling_filter(
                        preset_config["width"],
                        preset_config["height"]
                    )
                else:
                    scale_filter = f'scale={preset_config["width"]}:{preset_config["height"]}:force_original_aspect_ratio=decrease,pad={preset_config["width"]}:{preset_config["height"]}:(ow-iw)/2:(oh-ih)/2'
                
                cmd.extend(['-vf', scale_filter])
            
            # Framerate
            if preset_config.get("framerate"):
                cmd.extend(['-r', str(preset_config["framerate"])])
            
            # Audio codec and settings
            cmd.extend(['-c:a', settings.default_audio_codec])
            if "audio_bitrate" in preset_config:
                cmd.extend(['-b:a', preset_config["audio_bitrate"]])
            
            # Threading (for CPU operations)
            if self.threads and not use_gpu:
                cmd.extend(['-threads', str(self.threads)])
            
            # Apply custom options
            if custom_options:
                for key, value in custom_options.items():
                    cmd.extend([f'-{key}', str(value)])
            
            # Output options
            cmd.extend([
                '-movflags', '+faststart',  # Enable streaming
                '-y',  # Overwrite output
                output_path
            ])
            
            # Log command
            logger.info(
                "generating_video_proxy",
                input_path=input_path,
                output_path=output_path,
                preset=preset,
                command=' '.join(cmd)
            )
            
            # Execute FFmpeg
            start_time = asyncio.get_event_loop().time()
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Wait for completion with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=settings.processing_timeout
                )
            except asyncio.TimeoutError:
                process.terminate()
                await process.wait()
                raise ProcessingTimeoutError(
                    f"Video proxy generation timed out after {settings.processing_timeout} seconds"
                )
            
            processing_time = asyncio.get_event_loop().time() - start_time
            
            if process.returncode != 0:
                raise FFmpegError(
                    f"FFmpeg failed: {stderr.decode()}",
                    details={"returncode": process.returncode, "stderr": stderr.decode()}
                )
            
            # Get output file info
            output_info = await self.get_media_info(output_path)
            
            result = {
                "input_path": input_path,
                "output_path": output_path,
                "preset": preset,
                "processing_time": processing_time,
                "output_size": output_info["size"],
                "output_duration": output_info["duration"],
                "output_info": output_info
            }
            
            logger.info(
                "video_proxy_generated",
                **result
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "video_proxy_generation_failed",
                error=str(e),
                input_path=input_path,
                preset=preset
            )
            if isinstance(e, (FFmpegError, ProcessingTimeoutError)):
                raise
            raise FFmpegError(f"Video proxy generation failed: {str(e)}")
    
    async def generate_thumbnail(
        self,
        input_path: str,
        output_path: str,
        time_offset: float = 0,
        size: Optional[Dict[str, int]] = None
    ) -> Dict[str, Any]:
        """Generate thumbnail from video at specified time"""
        try:
            if not size:
                size = settings.thumbnail_sizes[0]  # Use small size by default
            
            cmd = [
                self.ffmpeg_path,
                '-ss', str(time_offset),
                '-i', input_path,
                '-vf', f'scale={size["width"]}:{size["height"]}:force_original_aspect_ratio=decrease,pad={size["width"]}:{size["height"]}:(ow-iw)/2:(oh-ih)/2',
                '-vframes', '1',
                '-f', 'image2',
                '-y',
                output_path
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise FFmpegError(
                    f"Thumbnail generation failed: {stderr.decode()}",
                    details={"returncode": process.returncode}
                )
            
            return {
                "input_path": input_path,
                "output_path": output_path,
                "time_offset": time_offset,
                "size": size
            }
            
        except Exception as e:
            logger.error(
                "thumbnail_generation_failed",
                error=str(e),
                input_path=input_path
            )
            if isinstance(e, FFmpegError):
                raise
            raise FFmpegError(f"Thumbnail generation failed: {str(e)}")
    
    async def generate_contact_sheet(
        self,
        input_path: str,
        output_path: str,
        columns: int = None,
        rows: int = None
    ) -> Dict[str, Any]:
        """Generate contact sheet (sprite) from video"""
        try:
            columns = columns or settings.contact_sheet_columns
            rows = rows or settings.contact_sheet_rows
            
            # Get video duration
            media_info = await self.get_media_info(input_path)
            duration = media_info["duration"]
            
            if duration <= 0:
                raise InvalidMediaError("Invalid video duration")
            
            # Calculate interval between frames
            total_frames = columns * rows
            interval = duration / (total_frames + 1)
            
            # Create temporary directory for individual frames
            with tempfile.TemporaryDirectory() as temp_dir:
                # Extract frames
                frame_paths = []
                for i in range(total_frames):
                    time_offset = interval * (i + 1)
                    frame_path = os.path.join(temp_dir, f"frame_{i:04d}.jpg")
                    
                    await self.generate_thumbnail(
                        input_path,
                        frame_path,
                        time_offset=time_offset,
                        size={"width": 320, "height": 180}
                    )
                    frame_paths.append(frame_path)
                
                # Create montage using FFmpeg
                filter_complex = f"tile={columns}x{rows}"
                
                cmd = [
                    self.ffmpeg_path,
                    '-pattern_type', 'glob',
                    '-i', os.path.join(temp_dir, 'frame_*.jpg'),
                    '-filter_complex', filter_complex,
                    '-y',
                    output_path
                ]
                
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await process.communicate()
                
                if process.returncode != 0:
                    raise FFmpegError(
                        f"Contact sheet generation failed: {stderr.decode()}",
                        details={"returncode": process.returncode}
                    )
            
            return {
                "input_path": input_path,
                "output_path": output_path,
                "columns": columns,
                "rows": rows,
                "total_frames": total_frames,
                "duration": duration
            }
            
        except Exception as e:
            logger.error(
                "contact_sheet_generation_failed",
                error=str(e),
                input_path=input_path
            )
            if isinstance(e, (FFmpegError, InvalidMediaError)):
                raise
            raise FFmpegError(f"Contact sheet generation failed: {str(e)}")
    
    async def generate_waveform(
        self,
        input_path: str,
        output_path: str,
        width: int = None,
        height: int = None,
        style: str = "line",  # line, fill, cline
        colors: Optional[Dict[str, str]] = None,
        split_channels: bool = False,
        show_axis: bool = True,
        logarithmic: bool = False
    ) -> Dict[str, Any]:
        """
        Generate audio waveform visualization
        
        Args:
            input_path: Path to input audio/video file
            output_path: Output waveform image path
            width: Image width (default from settings)
            height: Image height (default from settings)
            style: Waveform style - line, fill, or cline (centered line)
            colors: Custom colors dict with background, waveform, axis keys
            split_channels: Show stereo channels separately
            show_axis: Show axis lines and labels
            logarithmic: Use logarithmic scale
        
        Returns:
            Dict with waveform generation results
        """
        try:
            # Get media info to validate audio stream
            media_info = await self.get_media_info(input_path)
            has_audio = any(s["codec_type"] == "audio" for s in media_info["streams"])
            if not has_audio:
                raise InvalidMediaError("No audio stream found in input file")
            
            # Get audio stream info
            audio_stream = next(s for s in media_info["streams"] if s["codec_type"] == "audio")
            channels = audio_stream.get("channels", 2)
            sample_rate = int(audio_stream.get("sample_rate", 48000))
            duration = float(media_info.get("duration", 0))
            
            width = width or settings.waveform_width
            height = height or settings.waveform_height
            
            if colors is None:
                colors = settings.waveform_colors
            
            # Map style to FFmpeg draw parameter
            draw_style = {
                "line": "line",
                "fill": "full", 
                "cline": "cline"
            }.get(style, "line")
            
            # Build filter for waveform generation
            scale_type = "log" if logarithmic else "lin"
            
            if split_channels and channels > 1:
                # Generate split channel waveform
                channel_height = height // channels
                filters = []
                
                for i in range(channels):
                    filter_str = (
                        f"[0:a]channelsplit=channel_layout=stereo[ch{i}];"
                        f"[ch{i}]showwavespic="
                        f"s={width}x{channel_height}:"
                        f"colors={colors.get('waveform', '#0066cc')}:"
                        f"scale={scale_type}:"
                        f"draw={draw_style}"
                        f"[wave{i}]"
                    )
                    filters.append(filter_str)
                
                # Stack waveforms vertically
                stack_inputs = "".join(f"[wave{i}]" for i in range(channels))
                filter_complex = ";".join(filters) + f";{stack_inputs}vstack={channels}"
            else:
                # Single waveform for all channels
                filter_complex = (
                    f"[0:a]showwavespic="
                    f"s={width}x{height}:"
                    f"colors={colors.get('waveform', '#0066cc')}:"
                    f"scale={scale_type}:"
                    f"draw={draw_style}"
                )
                
                # Add background color if specified
                if colors.get('background'):
                    bg_color = colors['background'].lstrip('#')
                    filter_complex = (
                        f"color=c=0x{bg_color}:s={width}x{height}[bg];"
                        f"{filter_complex}[fg];"
                        f"[bg][fg]overlay=0:0"
                    )
            
            # Add axis overlay if requested
            if show_axis:
                # Create axis overlay filter
                axis_filter = self._create_waveform_axis_filter(
                    width, height, duration, sample_rate, colors.get('axis', '#333333')
                )
                if axis_filter:
                    filter_complex += f";{axis_filter}"
            
            cmd = [
                self.ffmpeg_path,
                '-i', input_path,
                '-filter_complex', filter_complex,
                '-frames:v', '1',
                '-y',
                output_path
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.processing_timeout
            )
            
            if process.returncode != 0:
                raise FFmpegError(
                    f"Waveform generation failed",
                    details={"stderr": stderr.decode(), "returncode": process.returncode}
                )
            
            # Get output file size
            import os
            file_size = os.path.getsize(output_path)
            
            return {
                "input_path": input_path,
                "output_path": output_path,
                "width": width,
                "height": height,
                "style": style,
                "channels": channels,
                "sample_rate": sample_rate,
                "duration": duration,
                "file_size": file_size
            }
            
        except asyncio.TimeoutError:
            raise FFmpegError(
                "Waveform generation timeout",
                details={"timeout": self.processing_timeout}
            )
        except Exception as e:
            logger.error(
                "waveform_generation_failed",
                error=str(e),
                input_path=input_path
            )
            if isinstance(e, (FFmpegError, InvalidMediaError)):
                raise
            raise FFmpegError(f"Waveform generation failed: {str(e)}")
    
    def _create_waveform_axis_filter(
        self,
        width: int,
        height: int,
        duration: float,
        sample_rate: int,
        axis_color: str
    ) -> str:
        """Create filter for adding axis lines and labels to waveform"""
        # For now, return empty string - axis overlay can be complex
        # This would typically use drawtext and drawbox filters
        # Could be enhanced in future to add time markers, db scale, etc.
        return ""
    
    async def generate_spectral_waveform(
        self,
        input_path: str,
        output_path: str,
        width: int = None,
        height: int = None,
        color_mode: str = "intensity",  # intensity, rainbow, fire, cool
        frequency_scale: str = "lin",  # lin, log, sqrt
        window_size: int = 2048,
        overlap: float = 0.875
    ) -> Dict[str, Any]:
        """
        Generate spectral waveform (spectrogram) visualization
        
        Args:
            input_path: Path to input audio/video file
            output_path: Output spectrogram image path
            width: Image width
            height: Image height  
            color_mode: Color scheme for frequency intensity
            frequency_scale: Frequency axis scale
            window_size: FFT window size
            overlap: Window overlap (0-1)
        
        Returns:
            Dict with spectrogram generation results
        """
        try:
            # Validate audio stream
            media_info = await self.get_media_info(input_path)
            has_audio = any(s["codec_type"] == "audio" for s in media_info["streams"])
            if not has_audio:
                raise InvalidMediaError("No audio stream found in input file")
            
            width = width or settings.waveform_width
            height = height or settings.waveform_height or 512
            
            # Map color modes to FFmpeg parameters
            color_map = {
                "intensity": "intensity",
                "rainbow": "rainbow", 
                "fire": "fire",
                "cool": "cool",
                "channel": "channel",
                "moreland": "moreland",
                "nebulae": "nebulae",
                "fruit": "fruit"
            }
            
            color_param = color_map.get(color_mode, "intensity")
            
            # Calculate hop size from overlap
            hop_size = int(window_size * (1 - overlap))
            
            # Build spectrogram filter
            filter_complex = (
                f"[0:a]showspectrumpic="
                f"s={width}x{height}:"
                f"legend=disabled:"
                f"scale={frequency_scale}:"
                f"color={color_param}:"
                f"win_size={window_size}:"
                f"hop_size={hop_size}"
            )
            
            cmd = [
                self.ffmpeg_path,
                '-i', input_path,
                '-filter_complex', filter_complex,
                '-frames:v', '1',
                '-y',
                output_path
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.processing_timeout
            )
            
            if process.returncode != 0:
                raise FFmpegError(
                    f"Spectrogram generation failed",
                    details={"stderr": stderr.decode(), "returncode": process.returncode}
                )
            
            # Get output file size
            import os
            file_size = os.path.getsize(output_path)
            
            return {
                "input_path": input_path,
                "output_path": output_path,
                "width": width,
                "height": height,
                "color_mode": color_mode,
                "frequency_scale": frequency_scale,
                "window_size": window_size,
                "overlap": overlap,
                "file_size": file_size
            }
            
        except asyncio.TimeoutError:
            raise FFmpegError(
                "Spectrogram generation timeout",
                details={"timeout": self.processing_timeout}
            )
        except Exception as e:
            logger.error(
                "spectrogram_generation_failed",
                error=str(e),
                input_path=input_path
            )
            if isinstance(e, (FFmpegError, InvalidMediaError)):
                raise
            raise FFmpegError(f"Spectrogram generation failed: {str(e)}")
    
    async def generate_vectorscope(
        self,
        input_path: str,
        output_path: str,
        width: int = 256,
        height: int = 256,
        mode: str = "lissajous",  # lissajous, lissajous_xy
        intensity: float = 0.04,
        zoom: float = 1.0
    ) -> Dict[str, Any]:
        """
        Generate audio vectorscope visualization (stereo phase meter)
        
        Args:
            input_path: Path to input audio file
            output_path: Output vectorscope image path
            width: Image width
            height: Image height
            mode: Vectorscope mode
            intensity: Point intensity
            zoom: Zoom factor
        
        Returns:
            Dict with vectorscope generation results
        """
        try:
            # Build vectorscope filter
            filter_complex = (
                f"[0:a]avectorscope="
                f"s={width}x{height}:"
                f"mode={mode}:"
                f"draw=dot:"
                f"scale=lin:"
                f"zoom={zoom}:"
                f"r=25:"  # Frame rate
                f"rc=40:"  # Contrast
                f"gc=160:"  # Gamma correction  
                f"bc=10"  # Brightness correction
            )
            
            # Generate single frame
            cmd = [
                self.ffmpeg_path,
                '-i', input_path,
                '-filter_complex', filter_complex,
                '-frames:v', '1',
                '-y',
                output_path
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.processing_timeout
            )
            
            if process.returncode != 0:
                raise FFmpegError(
                    f"Vectorscope generation failed",
                    details={"stderr": stderr.decode(), "returncode": process.returncode}
                )
            
            import os
            file_size = os.path.getsize(output_path)
            
            return {
                "input_path": input_path,
                "output_path": output_path,
                "width": width,
                "height": height,
                "mode": mode,
                "file_size": file_size
            }
            
        except Exception as e:
            logger.error(
                "vectorscope_generation_failed",
                error=str(e),
                input_path=input_path
            )
            if isinstance(e, FFmpegError):
                raise
            raise FFmpegError(f"Vectorscope generation failed: {str(e)}")
    
    async def normalize_audio(
        self,
        input_path: str,
        output_path: str,
        target_level: float = -23.0
    ) -> Dict[str, Any]:
        """Normalize audio levels"""
        try:
            # First pass - analyze audio
            analyze_cmd = [
                self.ffmpeg_path,
                '-i', input_path,
                '-af', f'loudnorm=I={target_level}:print_format=json',
                '-f', 'null',
                '-'
            ]
            
            process = await asyncio.create_subprocess_exec(
                *analyze_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            # Extract loudnorm stats from stderr
            stderr_text = stderr.decode()
            stats_start = stderr_text.rfind('{')
            stats_end = stderr_text.rfind('}') + 1
            
            if stats_start == -1 or stats_end == 0:
                raise FFmpegError("Failed to extract loudnorm statistics")
            
            try:
                stats = json.loads(stderr_text[stats_start:stats_end])
            except json.JSONDecodeError:
                raise FFmpegError("Failed to parse loudnorm statistics")
            
            # Second pass - apply normalization
            normalize_cmd = [
                self.ffmpeg_path,
                '-i', input_path,
                '-af', f'loudnorm=I={target_level}:'
                       f'measured_I={stats["input_i"]}:'
                       f'measured_LRA={stats["input_lra"]}:'
                       f'measured_TP={stats["input_tp"]}:'
                       f'measured_thresh={stats["input_thresh"]}:'
                       f'offset={stats["target_offset"]}',
                '-c:v', 'copy',  # Copy video stream
                '-y',
                output_path
            ]
            
            process = await asyncio.create_subprocess_exec(
                *normalize_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise FFmpegError(
                    f"Audio normalization failed: {stderr.decode()}",
                    details={"returncode": process.returncode}
                )
            
            return {
                "input_path": input_path,
                "output_path": output_path,
                "target_level": target_level,
                "loudnorm_stats": stats
            }
            
        except Exception as e:
            logger.error(
                "audio_normalization_failed",
                error=str(e),
                input_path=input_path
            )
            if isinstance(e, FFmpegError):
                raise
            raise FFmpegError(f"Audio normalization failed: {str(e)}")
    
    async def detect_audio_peaks(
        self,
        input_path: str,
        threshold: float = -20.0,  # dB
        min_duration: float = 0.1,  # seconds
        channel: Optional[int] = None  # None = all channels
    ) -> Dict[str, Any]:
        """
        Detect audio peaks/clipping in audio file
        
        Args:
            input_path: Path to input audio/video file
            threshold: Peak threshold in dB
            min_duration: Minimum duration for peak detection
            channel: Specific channel to analyze (None = all)
        
        Returns:
            Dict with peak detection results
        """
        try:
            # Build filter for peak detection
            filters = []
            
            # Channel selection if specified
            if channel is not None:
                filters.append(f"channelselect={channel}")
            
            # Peak detection filter
            filters.append(f"astats=metadata=1:reset=1")
            
            filter_str = ",".join(filters) if filters else "anull"
            
            cmd = [
                self.ffmpeg_path,
                '-i', input_path,
                '-af', filter_str,
                '-f', 'null',
                '-'
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.processing_timeout
            )
            
            # Parse audio statistics from stderr
            stderr_text = stderr.decode()
            
            # Extract peak levels and other stats
            peaks = []
            max_peak = -float('inf')
            rms_levels = []
            
            for line in stderr_text.split('\n'):
                if 'lavfi.astats.Overall.Peak_level' in line:
                    try:
                        peak_db = float(line.split('=')[1].strip())
                        if peak_db > threshold:
                            peaks.append({
                                "level_db": peak_db,
                                "threshold_exceeded": True
                            })
                        max_peak = max(max_peak, peak_db)
                    except (IndexError, ValueError):
                        pass
                elif 'lavfi.astats.Overall.RMS_level' in line:
                    try:
                        rms_db = float(line.split('=')[1].strip())
                        rms_levels.append(rms_db)
                    except (IndexError, ValueError):
                        pass
            
            # Get overall statistics
            media_info = await self.get_media_info(input_path)
            duration = float(media_info.get("duration", 0))
            
            # Calculate average RMS
            avg_rms = sum(rms_levels) / len(rms_levels) if rms_levels else -float('inf')
            
            return {
                "input_path": input_path,
                "duration": duration,
                "threshold_db": threshold,
                "max_peak_db": max_peak,
                "average_rms_db": avg_rms,
                "peak_count": len(peaks),
                "peaks_detected": peaks,
                "clipping_detected": max_peak > -0.1  # Near 0 dB indicates clipping
            }
            
        except asyncio.TimeoutError:
            raise FFmpegError(
                "Peak detection timeout",
                details={"timeout": self.processing_timeout}
            )
        except Exception as e:
            logger.error(
                "peak_detection_failed",
                error=str(e),
                input_path=input_path
            )
            if isinstance(e, FFmpegError):
                raise
            raise FFmpegError(f"Peak detection failed: {str(e)}")
    
    async def extract_audio_levels(
        self,
        input_path: str,
        interval: float = 0.1  # Sample every 100ms
    ) -> Dict[str, Any]:
        """
        Extract audio levels over time for level meter visualization
        
        Args:
            input_path: Path to input audio/video file
            interval: Sampling interval in seconds
        
        Returns:
            Dict with time-based audio levels
        """
        try:
            # Use ebur128 filter for loudness measurement
            filter_str = f"ebur128=framelog=verbose:peak=true"
            
            cmd = [
                self.ffmpeg_path,
                '-i', input_path,
                '-af', filter_str,
                '-f', 'null',
                '-'
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.processing_timeout
            )
            
            # Parse frame-by-frame loudness data
            stderr_text = stderr.decode()
            levels = []
            
            for line in stderr_text.split('\n'):
                if 'pts_time' in line and 'I:' in line:
                    try:
                        # Extract timestamp and momentary loudness
                        parts = line.split()
                        time_idx = next(i for i, p in enumerate(parts) if p.startswith('pts_time:'))
                        time_val = float(parts[time_idx].split(':')[1])
                        
                        loudness_idx = next(i for i, p in enumerate(parts) if p.startswith('I:'))
                        loudness_val = float(parts[loudness_idx].split(':')[1])
                        
                        levels.append({
                            "time": time_val,
                            "loudness": loudness_val
                        })
                    except (IndexError, ValueError, StopIteration):
                        pass
            
            # Get media info
            media_info = await self.get_media_info(input_path)
            duration = float(media_info.get("duration", 0))
            
            return {
                "input_path": input_path,
                "duration": duration,
                "sample_interval": interval,
                "sample_count": len(levels),
                "levels": levels
            }
            
        except asyncio.TimeoutError:
            raise FFmpegError(
                "Audio level extraction timeout", 
                details={"timeout": self.processing_timeout}
            )
        except Exception as e:
            logger.error(
                "audio_level_extraction_failed",
                error=str(e),
                input_path=input_path
            )
            if isinstance(e, FFmpegError):
                raise
            raise FFmpegError(f"Audio level extraction failed: {str(e)}")
    
    async def convert_audio_format(
        self,
        input_path: str,
        output_path: str,
        output_format: str = "mp3",
        codec: Optional[str] = None,
        bitrate: Optional[str] = None,
        sample_rate: Optional[int] = None,
        channels: Optional[int] = None,
        extra_options: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Convert audio to different format
        
        Args:
            input_path: Path to input audio/video file
            output_path: Path to output audio file
            output_format: Target format (mp3, aac, flac, wav, opus, etc.)
            codec: Audio codec to use (auto-selected if None)
            bitrate: Target bitrate (e.g., "192k", "320k")
            sample_rate: Target sample rate (e.g., 44100, 48000)
            channels: Number of output channels (1=mono, 2=stereo)
            extra_options: Additional FFmpeg options
            
        Returns:
            Dict with conversion details
        """
        try:
            start_time = asyncio.get_event_loop().time()
            
            # Build command
            cmd = [
                self.ffmpeg_path,
                '-i', input_path,
                '-vn'  # No video
            ]
            
            # Auto-select codec based on format if not specified
            if codec is None:
                codec_map = {
                    "mp3": "libmp3lame",
                    "aac": "aac",
                    "m4a": "aac",
                    "flac": "flac",
                    "wav": "pcm_s16le",
                    "opus": "libopus",
                    "ogg": "libvorbis",
                    "ac3": "ac3",
                    "wma": "wmav2"
                }
                codec = codec_map.get(output_format.lower(), "copy")
            
            cmd.extend(['-c:a', codec])
            
            # Add bitrate if specified
            if bitrate:
                cmd.extend(['-b:a', bitrate])
            else:
                # Default bitrates for lossy formats
                default_bitrates = {
                    "mp3": "192k",
                    "aac": "192k",
                    "m4a": "192k",
                    "opus": "128k",
                    "ogg": "192k",
                    "ac3": "384k",
                    "wma": "192k"
                }
                if output_format.lower() in default_bitrates and codec != "copy":
                    cmd.extend(['-b:a', default_bitrates[output_format.lower()]])
            
            # Add sample rate if specified
            if sample_rate:
                cmd.extend(['-ar', str(sample_rate)])
            
            # Add channel configuration if specified
            if channels:
                cmd.extend(['-ac', str(channels)])
            
            # Add any extra options
            if extra_options:
                for key, value in extra_options.items():
                    if value:
                        cmd.extend([f'-{key}', str(value)])
                    else:
                        cmd.append(f'-{key}')
            
            # Output file
            cmd.extend(['-y', output_path])
            
            logger.info(
                "audio_format_conversion_started",
                input_path=input_path,
                output_path=output_path,
                format=output_format,
                codec=codec,
                command=" ".join(cmd)
            )
            
            # Execute conversion
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.processing_timeout
            )
            
            if process.returncode != 0:
                raise FFmpegError(
                    f"Audio format conversion failed: {stderr.decode()}",
                    details={"returncode": process.returncode}
                )
            
            # Get output file info
            output_info = await self.get_media_info(output_path)
            processing_time = asyncio.get_event_loop().time() - start_time
            
            # Extract audio stream info
            audio_stream = next(
                (s for s in output_info.get("streams", []) if s.get("codec_type") == "audio"),
                {}
            )
            
            return {
                "input_path": input_path,
                "output_path": output_path,
                "output_format": output_format,
                "codec": audio_stream.get("codec_name", codec),
                "bitrate": audio_stream.get("bit_rate"),
                "sample_rate": audio_stream.get("sample_rate"),
                "channels": audio_stream.get("channels"),
                "duration": output_info.get("duration"),
                "file_size": os.path.getsize(output_path),
                "processing_time": processing_time
            }
            
        except asyncio.TimeoutError:
            raise FFmpegError(
                "Audio format conversion timeout", 
                details={"timeout": self.processing_timeout}
            )
        except Exception as e:
            logger.error(
                "audio_format_conversion_failed",
                error=str(e),
                input_path=input_path,
                output_format=output_format
            )
            if isinstance(e, FFmpegError):
                raise
            raise FFmpegError(f"Audio format conversion failed: {str(e)}")
    
    async def convert_image_format(
        self,
        input_path: str,
        output_path: str,
        output_format: str = "jpg",
        width: Optional[int] = None,
        height: Optional[int] = None,
        quality: Optional[int] = None,
        preserve_aspect_ratio: bool = True,
        extra_options: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Convert image to different format with optional resizing
        
        Args:
            input_path: Path to input image file
            output_path: Path to output image file
            output_format: Target format (jpg, png, webp, bmp, tiff, etc.)
            width: Target width (None to keep original)
            height: Target height (None to keep original)
            quality: Quality for lossy formats (1-100)
            preserve_aspect_ratio: Maintain aspect ratio when resizing
            extra_options: Additional FFmpeg options
            
        Returns:
            Dict with conversion details
        """
        try:
            start_time = asyncio.get_event_loop().time()
            
            # Build command
            cmd = [
                self.ffmpeg_path,
                '-i', input_path,
                '-frames:v', '1'  # Ensure single frame for image
            ]
            
            # Build filter chain
            filters = []
            
            # Add scaling if dimensions specified
            if width or height:
                if preserve_aspect_ratio:
                    # Use -1 to maintain aspect ratio
                    w = width if width else -1
                    h = height if height else -1
                    filters.append(f"scale={w}:{h}")
                else:
                    # Force exact dimensions
                    if width and height:
                        filters.append(f"scale={width}:{height}")
                    elif width:
                        filters.append(f"scale={width}:ih")
                    elif height:
                        filters.append(f"scale=iw:{height}")
            
            # Apply filters if any
            if filters:
                filter_str = ",".join(filters)
                cmd.extend(['-vf', filter_str])
            
            # Format-specific options
            if output_format.lower() in ["jpg", "jpeg"]:
                if quality:
                    cmd.extend(['-q:v', str(int((100 - quality) * 31 / 99) + 1)])  # FFmpeg uses 1-31 scale (1=best)
                else:
                    cmd.extend(['-q:v', '2'])  # High quality default
            elif output_format.lower() == "png":
                if quality:
                    # PNG compression level 0-9 (0=no compression, 9=max compression)
                    compression = int((100 - quality) * 9 / 99)
                    cmd.extend(['-compression_level', str(compression)])
            elif output_format.lower() == "webp":
                if quality:
                    cmd.extend(['-quality', str(quality)])
                else:
                    cmd.extend(['-quality', '85'])
                cmd.extend(['-lossless', '0'])  # Use lossy compression
            elif output_format.lower() == "webp-lossless":
                cmd.extend(['-lossless', '1'])  # Use lossless compression
            elif output_format.lower() == "tiff":
                cmd.extend(['-compression_algo', 'lzw'])  # Use LZW compression for TIFF
            elif output_format.lower() == "bmp":
                # BMP has no quality settings
                pass
            
            # Add any extra options
            if extra_options:
                for key, value in extra_options.items():
                    if value:
                        cmd.extend([f'-{key}', str(value)])
                    else:
                        cmd.append(f'-{key}')
            
            # Output file
            cmd.extend(['-y', output_path])
            
            logger.info(
                "image_format_conversion_started",
                input_path=input_path,
                output_path=output_path,
                format=output_format,
                command=" ".join(cmd)
            )
            
            # Execute conversion
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.processing_timeout
            )
            
            if process.returncode != 0:
                raise FFmpegError(
                    f"Image format conversion failed: {stderr.decode()}",
                    details={"returncode": process.returncode}
                )
            
            # Get output file info
            output_info = await self.get_media_info(output_path)
            processing_time = asyncio.get_event_loop().time() - start_time
            
            # Extract video/image stream info
            image_stream = next(
                (s for s in output_info.get("streams", []) if s.get("codec_type") == "video"),
                {}
            )
            
            return {
                "input_path": input_path,
                "output_path": output_path,
                "output_format": output_format,
                "width": image_stream.get("width"),
                "height": image_stream.get("height"),
                "codec": image_stream.get("codec_name"),
                "pixel_format": image_stream.get("pix_fmt"),
                "file_size": os.path.getsize(output_path),
                "processing_time": processing_time
            }
            
        except asyncio.TimeoutError:
            raise FFmpegError(
                "Image format conversion timeout", 
                details={"timeout": self.processing_timeout}
            )
        except Exception as e:
            logger.error(
                "image_format_conversion_failed",
                error=str(e),
                input_path=input_path,
                output_format=output_format
            )
            if isinstance(e, FFmpegError):
                raise
            raise FFmpegError(f"Image format conversion failed: {str(e)}")
    
    async def convert_image_sequence(
        self,
        input_pattern: str,
        output_path: str,
        output_format: str = "mp4",
        frame_rate: int = 24,
        video_codec: Optional[str] = None,
        quality: Optional[str] = None,
        extra_options: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Convert image sequence to video or animated format
        
        Args:
            input_pattern: Input pattern (e.g., "frame_%04d.png")
            output_path: Output video/gif path
            output_format: Target format (mp4, gif, webm, etc.)
            frame_rate: Output frame rate
            video_codec: Video codec to use (auto-selected if None)
            quality: Quality setting (format-specific)
            extra_options: Additional FFmpeg options
            
        Returns:
            Dict with conversion details
        """
        try:
            start_time = asyncio.get_event_loop().time()
            
            # Build command
            cmd = [
                self.ffmpeg_path,
                '-framerate', str(frame_rate),
                '-i', input_pattern,
                '-r', str(frame_rate)  # Output frame rate
            ]
            
            # Format-specific settings
            if output_format.lower() == "gif":
                # Generate optimized GIF with palette
                palette_cmd = [
                    self.ffmpeg_path,
                    '-i', input_pattern,
                    '-vf', f'fps={frame_rate},scale=320:-1:flags=lanczos,palettegen',
                    '-y', '/tmp/palette.png'
                ]
                
                # Generate palette first
                palette_process = await asyncio.create_subprocess_exec(
                    *palette_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await palette_process.communicate()
                
                # Use palette for GIF generation
                cmd = [
                    self.ffmpeg_path,
                    '-framerate', str(frame_rate),
                    '-i', input_pattern,
                    '-i', '/tmp/palette.png',
                    '-lavfi', f'fps={frame_rate},scale=320:-1:flags=lanczos[x];[x][1:v]paletteuse',
                ]
            else:
                # Video format settings
                if video_codec is None:
                    codec_map = {
                        "mp4": "libx264",
                        "webm": "libvpx-vp9",
                        "avi": "mpeg4",
                        "mov": "libx264"
                    }
                    video_codec = codec_map.get(output_format.lower(), "libx264")
                
                cmd.extend(['-c:v', video_codec])
                
                # Quality settings
                if quality:
                    if video_codec == "libx264":
                        cmd.extend(['-crf', quality])  # 0-51, lower is better
                    elif video_codec == "libvpx-vp9":
                        cmd.extend(['-crf', quality, '-b:v', '0'])
                else:
                    # Default quality
                    if video_codec == "libx264":
                        cmd.extend(['-crf', '23'])
                    elif video_codec == "libvpx-vp9":
                        cmd.extend(['-crf', '30', '-b:v', '0'])
                
                # Pixel format for compatibility
                cmd.extend(['-pix_fmt', 'yuv420p'])
            
            # Add any extra options
            if extra_options:
                for key, value in extra_options.items():
                    if value:
                        cmd.extend([f'-{key}', str(value)])
                    else:
                        cmd.append(f'-{key}')
            
            # Output file
            cmd.extend(['-y', output_path])
            
            logger.info(
                "image_sequence_conversion_started",
                input_pattern=input_pattern,
                output_path=output_path,
                format=output_format,
                command=" ".join(cmd)
            )
            
            # Execute conversion
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.processing_timeout
            )
            
            if process.returncode != 0:
                raise FFmpegError(
                    f"Image sequence conversion failed: {stderr.decode()}",
                    details={"returncode": process.returncode}
                )
            
            # Clean up palette file if it exists
            if output_format.lower() == "gif" and os.path.exists('/tmp/palette.png'):
                os.remove('/tmp/palette.png')
            
            # Get output file info
            output_info = await self.get_media_info(output_path)
            processing_time = asyncio.get_event_loop().time() - start_time
            
            return {
                "input_pattern": input_pattern,
                "output_path": output_path,
                "output_format": output_format,
                "frame_rate": frame_rate,
                "duration": output_info.get("duration"),
                "codec": video_codec if output_format.lower() != "gif" else "gif",
                "file_size": os.path.getsize(output_path),
                "processing_time": processing_time
            }
            
        except asyncio.TimeoutError:
            raise FFmpegError(
                "Image sequence conversion timeout", 
                details={"timeout": self.processing_timeout}
            )
        except Exception as e:
            logger.error(
                "image_sequence_conversion_failed",
                error=str(e),
                input_pattern=input_pattern,
                output_format=output_format
            )
            if isinstance(e, FFmpegError):
                raise
            raise FFmpegError(f"Image sequence conversion failed: {str(e)}")
    
    async def generate_thumbnails(
        self,
        input_path: str,
        output_pattern: str,
        count: int = 10,
        width: int = 320,
        height: int = 180,
        format: str = "jpg",
        quality: int = 85,
        start_time: float = 0,
        duration: Optional[float] = None,
        method: str = "interval"  # interval, scene, keyframe
    ) -> Dict[str, Any]:
        """
        Generate multiple thumbnails from video
        
        Args:
            input_path: Path to input video
            output_pattern: Output pattern with %d placeholder (e.g., "thumb_%d.jpg")
            count: Number of thumbnails to generate
            width: Thumbnail width
            height: Thumbnail height
            format: Output format (jpg, png, webp)
            quality: Quality for lossy formats (1-100)
            start_time: Start time in seconds
            duration: Duration to sample from (None = entire video)
            method: Thumbnail selection method
        
        Returns:
            Dict with thumbnail paths and metadata
        """
        try:
            # Get video info
            media_info = await self.get_media_info(input_path)
            if not media_info:
                raise FFmpegError("Failed to get media info")
            
            video_duration = media_info.get("duration", 0)
            if not video_duration:
                raise FFmpegError("Cannot determine video duration")
            
            # Calculate sampling duration
            if duration:
                sample_duration = min(duration, video_duration - start_time)
            else:
                sample_duration = video_duration - start_time
            
            # Build FFmpeg command based on method
            if method == "interval":
                # Generate thumbnails at regular intervals
                interval = sample_duration / count
                
                cmd = [self.ffmpeg_path, "-i", input_path]
                
                # Add GPU acceleration if available
                if self.enable_gpu and self.gpu_type != GPUType.NONE:
                    cmd.extend(self._get_gpu_acceleration_params())
                
                # Add filter for frame selection and scaling
                fps_filter = f"fps=1/{interval}"
                scale_filter = self._get_gpu_scaling_filter(width, height) if self.enable_gpu else f"scale={width}:{height}"
                
                cmd.extend([
                    "-ss", str(start_time),
                    "-t", str(sample_duration),
                    "-vf", f"{fps_filter},{scale_filter}",
                    "-frames:v", str(count),
                ])
                
            elif method == "scene":
                # Generate thumbnails at scene changes
                cmd = [self.ffmpeg_path, "-i", input_path]
                
                if self.enable_gpu and self.gpu_type != GPUType.NONE:
                    cmd.extend(self._get_gpu_acceleration_params())
                
                # Scene detection filter
                scene_filter = f"select='gt(scene,0.3)',showinfo"
                scale_filter = self._get_gpu_scaling_filter(width, height) if self.enable_gpu else f"scale={width}:{height}"
                
                cmd.extend([
                    "-ss", str(start_time),
                    "-t", str(sample_duration),
                    "-vf", f"{scene_filter},{scale_filter}",
                    "-frames:v", str(count),
                ])
                
            elif method == "keyframe":
                # Generate thumbnails at keyframes
                cmd = [self.ffmpeg_path, "-i", input_path]
                
                if self.enable_gpu and self.gpu_type != GPUType.NONE:
                    cmd.extend(self._get_gpu_acceleration_params())
                
                # Keyframe selection filter
                keyframe_filter = "select='eq(pict_type,I)'"
                scale_filter = self._get_gpu_scaling_filter(width, height) if self.enable_gpu else f"scale={width}:{height}"
                
                cmd.extend([
                    "-ss", str(start_time),
                    "-t", str(sample_duration),
                    "-vf", f"{keyframe_filter},{scale_filter}",
                    "-frames:v", str(count),
                ])
            
            # Add output format options
            if format == "jpg" or format == "jpeg":
                cmd.extend(["-q:v", str(int((100 - quality) / 100 * 31) + 1)])  # Convert to FFmpeg scale
            elif format == "png":
                cmd.extend(["-compression_level", "6"])
            elif format == "webp":
                cmd.extend(["-quality", str(quality)])
            
            # Add output pattern
            cmd.extend(["-y", output_pattern])
            
            # Execute command
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.processing_timeout
            )
            
            if process.returncode != 0:
                raise FFmpegError(
                    f"Thumbnail generation failed",
                    details={"stderr": stderr.decode(), "returncode": process.returncode}
                )
            
            # Parse generated files
            import os
            import glob
            
            output_dir = os.path.dirname(output_pattern)
            output_base = os.path.basename(output_pattern).replace("%d", "*")
            thumbnail_files = sorted(glob.glob(os.path.join(output_dir, output_base)))
            
            # Get file sizes
            thumbnails = []
            for idx, path in enumerate(thumbnail_files):
                thumbnails.append({
                    "path": path,
                    "index": idx,
                    "size": os.path.getsize(path),
                    "width": width,
                    "height": height,
                    "format": format
                })
            
            return {
                "count": len(thumbnails),
                "thumbnails": thumbnails,
                "method": method,
                "total_size": sum(t["size"] for t in thumbnails)
            }
            
        except asyncio.TimeoutError:
            raise FFmpegError(
                "Thumbnail generation timeout",
                details={"timeout": self.processing_timeout}
            )
        except Exception as e:
            logger.error(
                "thumbnail_generation_failed",
                error=str(e),
                input_path=input_path
            )
            if isinstance(e, FFmpegError):
                raise
            raise FFmpegError(f"Thumbnail generation failed: {str(e)}")
    
    async def generate_single_thumbnail(
        self,
        input_path: str,
        output_path: str,
        time_offset: Union[float, str] = "auto",
        width: int = 320,
        height: int = 180,
        format: str = "jpg",
        quality: int = 85
    ) -> Dict[str, Any]:
        """
        Generate a single thumbnail from video
        
        Args:
            input_path: Path to input video
            output_path: Output thumbnail path
            time_offset: Time offset in seconds or "auto" for automatic selection
            width: Thumbnail width
            height: Thumbnail height
            format: Output format (jpg, png, webp)
            quality: Quality for lossy formats (1-100)
        
        Returns:
            Dict with thumbnail metadata
        """
        try:
            # Get video info
            media_info = await self.get_media_info(input_path)
            if not media_info:
                raise FFmpegError("Failed to get media info")
            
            video_duration = media_info.get("duration", 0)
            
            # Determine time offset
            if time_offset == "auto":
                # Use 10% of video duration or 10 seconds, whichever is smaller
                offset = min(video_duration * 0.1, 10.0)
            else:
                offset = float(time_offset)
            
            # Build FFmpeg command
            cmd = [self.ffmpeg_path, "-i", input_path]
            
            # Add GPU acceleration if available
            if self.enable_gpu and self.gpu_type != GPUType.NONE:
                cmd.extend(self._get_gpu_acceleration_params())
            
            # Add seeking and scaling
            scale_filter = self._get_gpu_scaling_filter(width, height) if self.enable_gpu else f"scale={width}:{height}"
            
            cmd.extend([
                "-ss", str(offset),
                "-vf", scale_filter,
                "-frames:v", "1",
            ])
            
            # Add output format options
            if format == "jpg" or format == "jpeg":
                cmd.extend(["-q:v", str(int((100 - quality) / 100 * 31) + 1)])
            elif format == "png":
                cmd.extend(["-compression_level", "6"])
            elif format == "webp":
                cmd.extend(["-quality", str(quality)])
            
            # Add output path
            cmd.extend(["-y", output_path])
            
            # Execute command
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=30  # Shorter timeout for single thumbnail
            )
            
            if process.returncode != 0:
                raise FFmpegError(
                    f"Thumbnail generation failed",
                    details={"stderr": stderr.decode(), "returncode": process.returncode}
                )
            
            # Get file info
            import os
            file_size = os.path.getsize(output_path)
            
            return {
                "path": output_path,
                "time_offset": offset,
                "size": file_size,
                "width": width,
                "height": height,
                "format": format
            }
            
        except asyncio.TimeoutError:
            raise FFmpegError("Thumbnail generation timeout")
        except Exception as e:
            logger.error(
                "single_thumbnail_failed",
                error=str(e),
                input_path=input_path
            )
            if isinstance(e, FFmpegError):
                raise
            raise FFmpegError(f"Thumbnail generation failed: {str(e)}")
    
    async def generate_contact_sheet(
        self,
        input_path: str,
        output_path: str,
        grid_size: Tuple[int, int] = (4, 4),
        thumb_width: int = 320,
        thumb_height: int = 180,
        padding: int = 5,
        background_color: str = "black",
        include_timestamps: bool = True,
        font_size: int = 12,
        font_color: str = "white"
    ) -> Dict[str, Any]:
        """
        Generate a contact sheet (sprite/mosaic) from video
        
        Args:
            input_path: Path to input video
            output_path: Output contact sheet path
            grid_size: Grid dimensions (columns, rows)
            thumb_width: Individual thumbnail width
            thumb_height: Individual thumbnail height
            padding: Padding between thumbnails
            background_color: Background color
            include_timestamps: Include timestamp overlay
            font_size: Font size for timestamps
            font_color: Font color for timestamps
        
        Returns:
            Dict with contact sheet metadata
        """
        try:
            # Get video info
            media_info = await self.get_media_info(input_path)
            if not media_info:
                raise FFmpegError("Failed to get media info")
            
            video_duration = media_info.get("duration", 0)
            if not video_duration:
                raise FFmpegError("Cannot determine video duration")
            
            cols, rows = grid_size
            total_thumbs = cols * rows
            interval = video_duration / total_thumbs
            
            # Calculate output dimensions
            output_width = (thumb_width * cols) + (padding * (cols + 1))
            output_height = (thumb_height * rows) + (padding * (rows + 1))
            
            # Build complex filter
            filter_parts = []
            
            # Generate thumbnails at intervals
            for i in range(total_thumbs):
                timestamp = i * interval
                row = i // cols
                col = i % cols
                x = padding + (col * (thumb_width + padding))
                y = padding + (row * (thumb_height + padding))
                
                # Extract frame
                filter_parts.append(f"[0:v]select='gte(t,{timestamp})',setpts=PTS-STARTPTS,scale={thumb_width}:{thumb_height}[thumb{i}]")
                
                # Add timestamp if requested
                if include_timestamps:
                    time_str = f"{int(timestamp//60):02d}:{int(timestamp%60):02d}"
                    filter_parts.append(
                        f"[thumb{i}]drawtext=text='{time_str}':fontsize={font_size}:"
                        f"fontcolor={font_color}:x=5:y=h-th-5:shadowcolor=black:shadowx=1:shadowy=1[thumb{i}t]"
                    )
                    thumb_ref = f"thumb{i}t"
                else:
                    thumb_ref = f"thumb{i}"
                
                # Position thumbnail
                if i == 0:
                    filter_parts.append(f"color={background_color}:s={output_width}x{output_height}[base]")
                    filter_parts.append(f"[base][{thumb_ref}]overlay={x}:{y}[out0]")
                else:
                    filter_parts.append(f"[out{i-1}][{thumb_ref}]overlay={x}:{y}[out{i}]")
            
            # Final output
            filter_complex = ";".join(filter_parts) + f",[out{total_thumbs-1}]trim=duration=0.04"
            
            # Build FFmpeg command
            cmd = [
                self.ffmpeg_path,
                "-i", input_path,
                "-filter_complex", filter_complex,
                "-frames:v", "1",
                "-y", output_path
            ]
            
            # Execute command
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.processing_timeout
            )
            
            if process.returncode != 0:
                raise FFmpegError(
                    f"Contact sheet generation failed",
                    details={"stderr": stderr.decode(), "returncode": process.returncode}
                )
            
            # Get file info
            import os
            file_size = os.path.getsize(output_path)
            
            return {
                "path": output_path,
                "size": file_size,
                "dimensions": {"width": output_width, "height": output_height},
                "grid": {"columns": cols, "rows": rows},
                "thumbnail_count": total_thumbs,
                "thumbnail_size": {"width": thumb_width, "height": thumb_height}
            }
            
        except asyncio.TimeoutError:
            raise FFmpegError(
                "Contact sheet generation timeout",
                details={"timeout": self.processing_timeout}
            )
        except Exception as e:
            logger.error(
                "contact_sheet_failed",
                error=str(e),
                input_path=input_path
            )
            if isinstance(e, FFmpegError):
                raise
            raise FFmpegError(f"Contact sheet generation failed: {str(e)}")
    
    def get_gpu_info(self) -> Dict[str, Any]:
        """Get comprehensive GPU information"""
        info = {
            "gpu_enabled": self.enable_gpu,
            "gpu_type": self.gpu_type.value,
            "gpu_info": self.gpu_info,
            "available_encoders": self.available_gpu_codecs,
            "performance_metrics": {}
        }
        
        if self.gpu_type == GPUType.NVIDIA:
            # Get additional NVIDIA metrics
            try:
                import subprocess
                result = subprocess.run(
                    ['nvidia-smi', '--query-gpu=utilization.gpu,utilization.memory,temperature.gpu,power.draw', '--format=csv,noheader'],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    metrics = result.stdout.strip().split(', ')
                    info["performance_metrics"] = {
                        "gpu_utilization": metrics[0] if len(metrics) > 0 else "N/A",
                        "memory_utilization": metrics[1] if len(metrics) > 1 else "N/A",
                        "temperature": metrics[2] if len(metrics) > 2 else "N/A",
                        "power_draw": metrics[3] if len(metrics) > 3 else "N/A"
                    }
            except Exception as e:
                logger.debug(f"Failed to get NVIDIA performance metrics: {e}")
        
        return info
    
    async def benchmark_gpu_performance(self, test_file: Optional[str] = None) -> Dict[str, Any]:
        """Benchmark GPU encoding performance"""
        if self.gpu_type == GPUType.NONE:
            return {"error": "No GPU detected"}
        
        results = {}
        
        # Create a test file if not provided
        if not test_file:
            # Generate a 10-second test video
            test_file = "/tmp/gpu_test_input.mp4"
            try:
                cmd = [
                    self.ffmpeg_path,
                    '-f', 'lavfi',
                    '-i', 'testsrc2=duration=10:size=1920x1080:rate=30',
                    '-f', 'lavfi',
                    '-i', 'sine=frequency=1000:duration=10',
                    '-c:v', 'libx264',
                    '-preset', 'ultrafast',
                    '-c:a', 'aac',
                    '-y',
                    test_file
                ]
                
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await process.communicate()
            except Exception as e:
                return {"error": f"Failed to create test file: {e}"}
        
        # Test different encoders
        test_configs = [
            {"name": "1080p_h264", "width": 1920, "height": 1080, "codec": "h264"},
            {"name": "720p_h264", "width": 1280, "height": 720, "codec": "h264"},
            {"name": "1080p_h265", "width": 1920, "height": 1080, "codec": "h265"},
        ]
        
        for config in test_configs:
            output_file = f"/tmp/gpu_test_{config['name']}.mp4"
            
            try:
                # Test with GPU
                start_time = asyncio.get_event_loop().time()
                await self.generate_video_proxy(
                    test_file,
                    output_file,
                    custom_options={
                        "t": "10"  # Limit to 10 seconds
                    },
                    force_gpu=True
                )
                gpu_time = asyncio.get_event_loop().time() - start_time
                
                # Test without GPU
                start_time = asyncio.get_event_loop().time()
                await self.generate_video_proxy(
                    test_file,
                    output_file + "_cpu",
                    custom_options={
                        "t": "10"
                    },
                    force_gpu=False
                )
                cpu_time = asyncio.get_event_loop().time() - start_time
                
                results[config['name']] = {
                    "gpu_time": gpu_time,
                    "cpu_time": cpu_time,
                    "speedup": cpu_time / gpu_time if gpu_time > 0 else 0,
                    "gpu_fps": 10 / gpu_time if gpu_time > 0 else 0,
                    "cpu_fps": 10 / cpu_time if cpu_time > 0 else 0
                }
                
                # Cleanup
                os.remove(output_file)
                os.remove(output_file + "_cpu")
                
            except Exception as e:
                results[config['name']] = {"error": str(e)}
        
        # Cleanup test file
        if not test_file or test_file.startswith("/tmp/"):
            try:
                os.remove(test_file)
            except:
                pass
        
        return {
            "gpu_type": self.gpu_type.value,
            "gpu_info": self.gpu_info,
            "benchmark_results": results
        }
    
    async def generate_adaptive_bitrate_stream(
        self,
        input_path: str,
        output_dir: str,
        stream_formats: List[str] = None,
        qualities: List[Dict[str, Any]] = None,
        segment_duration: int = 6,
        playlist_type: str = "vod",
        force_gpu: bool = True,
        custom_options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate adaptive bitrate streams (HLS and/or DASH) for video content
        
        Args:
            input_path: Path to input video file
            output_dir: Directory to store output files
            stream_formats: List of streaming formats to generate ['hls', 'dash']
            qualities: List of quality configurations with width, height, bitrate
            segment_duration: Duration of each segment in seconds
            playlist_type: Type of playlist ('vod' or 'live')
            force_gpu: Use GPU acceleration if available
            custom_options: Additional FFmpeg options
            
        Returns:
            Dict with streaming information and file paths
        """
        try:
            start_time = asyncio.get_event_loop().time()
            
            # Default streaming formats
            if stream_formats is None:
                stream_formats = ["hls", "dash"]
            
            # Default quality configurations
            if qualities is None:
                qualities = [
                    {"name": "360p", "width": 640, "height": 360, "bitrate": "800k", "audio_bitrate": "128k"},
                    {"name": "480p", "width": 854, "height": 480, "bitrate": "1400k", "audio_bitrate": "128k"},
                    {"name": "720p", "width": 1280, "height": 720, "bitrate": "2800k", "audio_bitrate": "192k"},
                    {"name": "1080p", "width": 1920, "height": 1080, "bitrate": "5000k", "audio_bitrate": "192k"}
                ]
            
            # Ensure output directory exists
            os.makedirs(output_dir, exist_ok=True)
            
            # Get media info to determine optimal qualities
            media_info = await self.get_media_info(input_path)
            video_stream = next((s for s in media_info["streams"] if s["codec_type"] == "video"), None)
            
            if not video_stream:
                raise InvalidMediaError("No video stream found in input file")
            
            input_width = video_stream.get("width", 1920)
            input_height = video_stream.get("height", 1080)
            
            # Filter qualities based on input resolution
            filtered_qualities = []
            for quality in qualities:
                if quality["width"] <= input_width and quality["height"] <= input_height:
                    filtered_qualities.append(quality)
            
            if not filtered_qualities:
                # Add at least one quality that matches input
                filtered_qualities = [{
                    "name": "source",
                    "width": input_width,
                    "height": input_height,
                    "bitrate": "5000k",
                    "audio_bitrate": "192k"
                }]
            
            # Build FFmpeg command
            cmd = [self.ffmpeg_path]
            
            # Add hardware acceleration if enabled
            use_gpu = False
            if self.enable_gpu and self.gpu_type != GPUType.NONE and force_gpu:
                gpu_params = self._get_gpu_acceleration_params()
                cmd.extend(gpu_params)
                use_gpu = True
            
            # Input file
            cmd.extend(['-i', input_path])
            
            # Build filter complex for multiple outputs
            filter_complex = []
            output_maps = []
            
            # Create video variants
            for i, quality in enumerate(filtered_qualities):
                # Video scaling filter
                if use_gpu:
                    scale_filter = self._get_gpu_scaling_filter(quality["width"], quality["height"])
                else:
                    scale_filter = f'scale={quality["width"]}:{quality["height"]}:force_original_aspect_ratio=decrease,pad={quality["width"]}:{quality["height"]}:(ow-iw)/2:(oh-ih)/2'
                
                filter_complex.append(f'[0:v]{scale_filter}[v{i}]')
                output_maps.extend([f'-map', f'[v{i}]'])
                
                # Video codec and settings
                video_codec = settings.default_video_codec
                if use_gpu:
                    gpu_encoder = self._get_gpu_encoder(video_codec)
                    if gpu_encoder:
                        video_codec = gpu_encoder
                
                cmd.extend([f'-c:v:{i}', video_codec])
                cmd.extend([f'-b:v:{i}', quality["bitrate"]])
                
                # GPU-specific settings
                if use_gpu and gpu_encoder:
                    if self.gpu_type == GPUType.NVIDIA:
                        cmd.extend([f'-preset:v:{i}', 'p4'])
                        cmd.extend([f'-tune:v:{i}', 'hq'])
                        cmd.extend([f'-rc:v:{i}', 'vbr'])
                        cmd.extend([f'-cq:v:{i}', '23'])
                    elif self.gpu_type == GPUType.INTEL:
                        cmd.extend([f'-preset:v:{i}', 'medium'])
                        cmd.extend([f'-global_quality:v:{i}', '23'])
                    elif self.gpu_type == GPUType.AMD:
                        cmd.extend([f'-quality:v:{i}', 'balanced'])
                        cmd.extend([f'-rc:v:{i}', 'vbr_peak'])
                    elif self.gpu_type == GPUType.APPLE:
                        cmd.extend([f'-profile:v:{i}', 'high'])
                else:
                    # Software encoding options
                    if video_codec in ['libx264', 'libx265']:
                        cmd.extend([f'-preset:v:{i}', 'medium'])
                        cmd.extend([f'-crf:v:{i}', '23'])
                
                # Audio streams (copy for each variant)
                output_maps.extend(['-map', '0:a'])
                cmd.extend([f'-c:a:{i}', 'aac'])
                cmd.extend([f'-b:a:{i}', quality["audio_bitrate"]])
            
            # Add filter complex
            if filter_complex:
                cmd.extend(['-filter_complex', ';'.join(filter_complex)])
            
            # Add output mapping
            cmd.extend(output_maps)
            
            # Add custom options
            if custom_options:
                for key, value in custom_options.items():
                    cmd.extend([f'-{key}', str(value)])
            
            results = {}
            
            # Generate HLS if requested
            if "hls" in stream_formats:
                hls_output = os.path.join(output_dir, "playlist.m3u8")
                hls_cmd = cmd + [
                    '-f', 'hls',
                    '-hls_time', str(segment_duration),
                    '-hls_playlist_type', playlist_type,
                    '-hls_segment_filename', os.path.join(output_dir, 'segment_%v_%03d.ts'),
                    '-master_pl_name', 'master.m3u8',
                    '-var_stream_map', ' '.join([f'v:{i},a:{i}' for i in range(len(filtered_qualities))]),
                    '-y',
                    hls_output
                ]
                
                logger.info(
                    "generating_hls_stream",
                    input_path=input_path,
                    output_dir=output_dir,
                    qualities=len(filtered_qualities),
                    command=' '.join(hls_cmd[:20])  # Log first 20 args
                )
                
                process = await asyncio.create_subprocess_exec(
                    *hls_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=settings.processing_timeout
                )
                
                if process.returncode != 0:
                    raise FFmpegError(
                        f"HLS generation failed: {stderr.decode()}",
                        details={"returncode": process.returncode}
                    )
                
                results["hls"] = {
                    "master_playlist": os.path.join(output_dir, "master.m3u8"),
                    "playlist": hls_output,
                    "segment_duration": segment_duration,
                    "playlist_type": playlist_type
                }
            
            # Generate DASH if requested
            if "dash" in stream_formats:
                dash_output = os.path.join(output_dir, "manifest.mpd")
                dash_cmd = cmd + [
                    '-f', 'dash',
                    '-seg_duration', str(segment_duration),
                    '-init_seg_name', 'init_$RepresentationID$.$ext$',
                    '-media_seg_name', 'chunk_$RepresentationID$_$Number%05d$.$ext$',
                    '-adaptation_sets', 'id=0,streams=v id=1,streams=a',
                    '-y',
                    dash_output
                ]
                
                logger.info(
                    "generating_dash_stream",
                    input_path=input_path,
                    output_dir=output_dir,
                    qualities=len(filtered_qualities),
                    command=' '.join(dash_cmd[:20])
                )
                
                process = await asyncio.create_subprocess_exec(
                    *dash_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=settings.processing_timeout
                )
                
                if process.returncode != 0:
                    raise FFmpegError(
                        f"DASH generation failed: {stderr.decode()}",
                        details={"returncode": process.returncode}
                    )
                
                results["dash"] = {
                    "manifest": dash_output,
                    "segment_duration": segment_duration
                }
            
            processing_time = asyncio.get_event_loop().time() - start_time
            
            # Calculate total output size
            total_size = 0
            for root, dirs, files in os.walk(output_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    total_size += os.path.getsize(file_path)
            
            final_result = {
                "input_path": input_path,
                "output_dir": output_dir,
                "stream_formats": stream_formats,
                "qualities": filtered_qualities,
                "segment_duration": segment_duration,
                "playlist_type": playlist_type,
                "total_size": total_size,
                "processing_time": processing_time,
                "gpu_acceleration": use_gpu,
                "streams": results
            }
            
            logger.info(
                "adaptive_bitrate_stream_generated",
                **final_result
            )
            
            return final_result
            
        except asyncio.TimeoutError:
            raise ProcessingTimeoutError(
                f"Adaptive bitrate generation timed out after {settings.processing_timeout} seconds"
            )
        except Exception as e:
            logger.error(
                "adaptive_bitrate_generation_failed",
                error=str(e),
                input_path=input_path,
                output_dir=output_dir
            )
            if isinstance(e, (FFmpegError, InvalidMediaError, ProcessingTimeoutError)):
                raise
            raise FFmpegError(f"Adaptive bitrate generation failed: {str(e)}")

    async def detect_scene_changes(
        self,
        input_path: str,
        threshold: float = 0.3,
        min_scene_duration: float = 1.0,
        output_format: str = "json",
        save_thumbnails: bool = False,
        thumbnail_dir: Optional[str] = None,
        thumbnail_size: str = "320x180",
        custom_options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Detect scene changes in a video file
        
        Args:
            input_path: Path to input video file
            threshold: Scene change detection threshold (0.0-1.0, default 0.3)
            min_scene_duration: Minimum duration for a scene in seconds
            output_format: Output format ('json', 'csv', 'timestamps')
            save_thumbnails: Whether to save thumbnails at scene changes
            thumbnail_dir: Directory to save thumbnails (if save_thumbnails=True)
            thumbnail_size: Size of thumbnails (e.g., "320x180")
            custom_options: Additional FFmpeg options
            
        Returns:
            Dict containing scene change information
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Validate input
            if not os.path.exists(input_path):
                raise InvalidMediaError(f"Input file not found: {input_path}")
            
            # Validate threshold
            if not 0.0 <= threshold <= 1.0:
                raise InvalidMediaError(f"Threshold must be between 0.0 and 1.0, got {threshold}")
            
            # Get media info
            media_info = await self.get_media_info(input_path)
            if not any(s.get("codec_type") == "video" for s in media_info.get("streams", [])):
                raise InvalidMediaError("No video stream found in input file")
            
            # Create temporary directory for processing
            with tempfile.TemporaryDirectory() as temp_dir:
                # First pass: detect scene changes and extract metadata
                scene_data = await self._detect_scenes_with_metadata(
                    input_path,
                    threshold,
                    min_scene_duration,
                    temp_dir
                )
                
                # Process thumbnails if requested
                if save_thumbnails and thumbnail_dir:
                    os.makedirs(thumbnail_dir, exist_ok=True)
                    await self._extract_scene_thumbnails(
                        input_path,
                        scene_data["scenes"],
                        thumbnail_dir,
                        thumbnail_size
                    )
                
                # Format output based on requested format
                if output_format == "csv":
                    formatted_output = self._format_scenes_as_csv(scene_data["scenes"])
                elif output_format == "timestamps":
                    formatted_output = [s["timestamp"] for s in scene_data["scenes"]]
                else:  # json
                    formatted_output = scene_data["scenes"]
                
                processing_time = asyncio.get_event_loop().time() - start_time
                
                logger.info(
                    "scene_detection_completed",
                    input_path=input_path,
                    scenes_detected=len(scene_data["scenes"]),
                    threshold=threshold,
                    processing_time=processing_time
                )
                
                return {
                    "input_path": input_path,
                    "threshold": threshold,
                    "min_scene_duration": min_scene_duration,
                    "total_scenes": len(scene_data["scenes"]),
                    "duration": media_info.get("duration", 0),
                    "scenes": formatted_output,
                    "average_scene_duration": scene_data.get("average_scene_duration", 0),
                    "processing_time": processing_time,
                    "output_format": output_format,
                    "thumbnails_saved": save_thumbnails and thumbnail_dir is not None
                }
                
        except asyncio.TimeoutError:
            raise ProcessingTimeoutError(
                f"Scene detection timed out after {settings.processing_timeout} seconds"
            )
        except Exception as e:
            logger.error(
                "scene_detection_failed",
                error=str(e),
                input_path=input_path,
                threshold=threshold
            )
            if isinstance(e, (FFmpegError, InvalidMediaError, ProcessingTimeoutError)):
                raise
            raise FFmpegError(f"Scene detection failed: {str(e)}")
    
    async def _detect_scenes_with_metadata(
        self,
        input_path: str,
        threshold: float,
        min_scene_duration: float,
        temp_dir: str
    ) -> Dict[str, Any]:
        """Detect scenes and extract metadata using FFmpeg"""
        scenes = []
        
        # Build FFmpeg command for scene detection
        # Use the select filter with scene detection and showinfo for metadata
        filter_complex = (
            f"select='gt(scene,{threshold})',showinfo,"
            f"metadata=print:file='{temp_dir}/scene_metadata.txt'"
        )
        
        cmd = [
            self.ffmpeg_path,
            "-i", input_path,
            "-vf", filter_complex,
            "-f", "null",
            "-"
        ]
        
        # Add hardware decoding if available
        if self.enable_gpu and self.gpu_type != GPUType.NONE:
            hw_params = self._get_hardware_decode_params()
            if hw_params:
                cmd = cmd[:1] + hw_params + cmd[1:]
        
        # Run FFmpeg and capture output
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=settings.processing_timeout
        )
        
        if process.returncode != 0:
            raise FFmpegError(
                f"Scene detection failed",
                details={"stderr": stderr.decode(), "cmd": " ".join(cmd)}
            )
        
        # Parse showinfo output from stderr
        stderr_text = stderr.decode()
        current_scene_start = 0.0
        
        for line in stderr_text.split('\n'):
            if 'showinfo' in line and 'pts_time' in line:
                # Extract timestamp from showinfo output
                import re
                pts_match = re.search(r'pts_time:(\d+\.?\d*)', line)
                if pts_match:
                    timestamp = float(pts_match.group(1))
                    
                    # Check minimum scene duration
                    if timestamp - current_scene_start >= min_scene_duration:
                        # Extract additional metadata
                        scene_info = {
                            "timestamp": timestamp,
                            "scene_start": current_scene_start,
                            "scene_end": timestamp,
                            "duration": timestamp - current_scene_start,
                            "frame_number": None
                        }
                        
                        # Try to extract frame number
                        n_match = re.search(r'n:(\d+)', line)
                        if n_match:
                            scene_info["frame_number"] = int(n_match.group(1))
                        
                        scenes.append(scene_info)
                        current_scene_start = timestamp
        
        # Calculate average scene duration
        if scenes:
            total_duration = sum(s["duration"] for s in scenes)
            average_duration = total_duration / len(scenes)
        else:
            average_duration = 0
        
        return {
            "scenes": scenes,
            "average_scene_duration": average_duration
        }
    
    async def _extract_scene_thumbnails(
        self,
        input_path: str,
        scenes: List[Dict[str, Any]],
        output_dir: str,
        size: str
    ):
        """Extract thumbnails at scene change points"""
        tasks = []
        
        for i, scene in enumerate(scenes):
            timestamp = scene["timestamp"]
            output_path = os.path.join(output_dir, f"scene_{i:04d}_{timestamp:.2f}s.jpg")
            
            cmd = [
                self.ffmpeg_path,
                "-ss", str(timestamp),
                "-i", input_path,
                "-vframes", "1",
                "-vf", f"scale={size}",
                "-y", output_path
            ]
            
            # Add hardware decoding if available
            if self.enable_gpu and self.gpu_type != GPUType.NONE:
                hw_params = self._get_hardware_decode_params()
                if hw_params:
                    cmd = cmd[:1] + hw_params + cmd[1:]
            
            task = asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            tasks.append(task)
        
        # Process thumbnails in parallel
        processes = await asyncio.gather(*tasks)
        
        # Wait for all to complete
        for process in processes:
            await process.communicate()
    
    def _format_scenes_as_csv(self, scenes: List[Dict[str, Any]]) -> str:
        """Format scene data as CSV"""
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=["timestamp", "scene_start", "scene_end", "duration", "frame_number"]
        )
        writer.writeheader()
        writer.writerows(scenes)
        
        return output.getvalue()
    
    async def add_video_watermark(
        self,
        input_path: str,
        output_path: str,
        watermark_path: str,
        position: str = "bottom-right",
        scale: float = 0.2,
        opacity: float = 0.8,
        margin: int = 20,
        video_codec: Optional[str] = None,
        audio_codec: str = "copy",
        quality_preset: str = "medium",
        custom_options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Add watermark to a video file
        
        Args:
            input_path: Path to input video
            output_path: Path for output video
            watermark_path: Path to watermark image
            position: Watermark position (top-left, top-right, bottom-left, bottom-right, center)
            scale: Scale factor for watermark relative to video (0.0-1.0)
            opacity: Watermark opacity (0.0-1.0)
            margin: Margin from edges in pixels
            video_codec: Video codec to use (None = auto-select)
            audio_codec: Audio codec ("copy" to keep original)
            quality_preset: Quality preset name
            custom_options: Additional FFmpeg options
            
        Returns:
            Dict containing processing information
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Validate inputs
            if not os.path.exists(input_path):
                raise InvalidMediaError(f"Input file not found: {input_path}")
            if not os.path.exists(watermark_path):
                raise InvalidMediaError(f"Watermark file not found: {watermark_path}")
            
            # Get video info
            media_info = await self.get_media_info(input_path)
            video_stream = next((s for s in media_info["streams"] if s["codec_type"] == "video"), None)
            
            if not video_stream:
                raise InvalidMediaError("No video stream found in input file")
            
            video_width = video_stream.get("width", 1920)
            video_height = video_stream.get("height", 1080)
            
            # Calculate watermark overlay filter
            overlay_filter = self._build_watermark_filter(
                video_width,
                video_height,
                position,
                scale,
                margin,
                opacity
            )
            
            # Build FFmpeg command
            cmd = [self.ffmpeg_path, "-i", input_path, "-i", watermark_path]
            
            # Add hardware decoding if available
            if self.enable_gpu and self.gpu_type != GPUType.NONE:
                hw_params = self._get_hardware_decode_params()
                if hw_params:
                    cmd = cmd[:1] + hw_params + cmd[1:]
            
            # Build filter complex
            filter_complex = f"[1:v]scale=iw*{scale}:ih*{scale}[watermark];[0:v][watermark]{overlay_filter}"
            
            cmd.extend(["-filter_complex", filter_complex])
            
            # Video codec
            if not video_codec:
                video_codec = self._get_video_codec(quality_preset)
            
            if self.enable_gpu and video_codec in ["h264", "h265", "hevc"]:
                gpu_codec = self._get_gpu_encoder(video_codec)
                if gpu_codec:
                    cmd.extend(["-c:v", gpu_codec])
                    cmd.extend(self._get_gpu_encoding_params(gpu_codec, quality_preset))
                else:
                    cmd.extend(["-c:v", f"lib{video_codec}"])
                    cmd.extend(self._get_quality_params(quality_preset))
            else:
                cmd.extend(["-c:v", video_codec])
                cmd.extend(self._get_quality_params(quality_preset))
            
            # Audio codec
            cmd.extend(["-c:a", audio_codec])
            
            # Add custom options
            if custom_options:
                for key, value in custom_options.items():
                    cmd.extend([f"-{key}", str(value)])
            
            # Output file
            cmd.extend(["-y", output_path])
            
            # Run FFmpeg
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=settings.processing_timeout
            )
            
            if process.returncode != 0:
                raise FFmpegError(
                    f"Video watermarking failed",
                    details={"stderr": stderr.decode(), "cmd": " ".join(cmd)}
                )
            
            # Get output file info
            output_info = await self.get_media_info(output_path)
            processing_time = asyncio.get_event_loop().time() - start_time
            
            logger.info(
                "video_watermark_added",
                input_path=input_path,
                output_path=output_path,
                watermark_path=watermark_path,
                position=position,
                scale=scale,
                opacity=opacity,
                processing_time=processing_time
            )
            
            return {
                "input_path": input_path,
                "output_path": output_path,
                "watermark_path": watermark_path,
                "position": position,
                "scale": scale,
                "opacity": opacity,
                "duration": output_info.get("duration", 0),
                "size": output_info.get("size", 0),
                "video_codec": video_codec,
                "processing_time": processing_time,
                "gpu_accelerated": self.enable_gpu and self.gpu_type != GPUType.NONE
            }
            
        except asyncio.TimeoutError:
            raise ProcessingTimeoutError(
                f"Video watermarking timed out after {settings.processing_timeout} seconds"
            )
        except Exception as e:
            logger.error(
                "video_watermark_failed",
                error=str(e),
                input_path=input_path,
                watermark_path=watermark_path
            )
            if isinstance(e, (FFmpegError, InvalidMediaError, ProcessingTimeoutError)):
                raise
            raise FFmpegError(f"Video watermarking failed: {str(e)}")
    
    def _build_watermark_filter(
        self,
        video_width: int,
        video_height: int,
        position: str,
        scale: float,
        margin: int,
        opacity: float
    ) -> str:
        """Build overlay filter for watermark positioning"""
        # Calculate watermark size (will be scaled by FFmpeg)
        wm_width = f"overlay_w"
        wm_height = f"overlay_h"
        
        # Position calculations
        if position == "top-left":
            x = margin
            y = margin
        elif position == "top-right":
            x = f"main_w-{wm_width}-{margin}"
            y = margin
        elif position == "bottom-left":
            x = margin
            y = f"main_h-{wm_height}-{margin}"
        elif position == "bottom-right":
            x = f"main_w-{wm_width}-{margin}"
            y = f"main_h-{wm_height}-{margin}"
        elif position == "center":
            x = f"(main_w-{wm_width})/2"
            y = f"(main_h-{wm_height})/2"
        else:
            # Default to bottom-right
            x = f"main_w-{wm_width}-{margin}"
            y = f"main_h-{wm_height}-{margin}"
        
        # Build overlay filter with opacity
        if opacity < 1.0:
            return f"overlay={x}:{y}:format=auto:alpha={opacity}"
        else:
            return f"overlay={x}:{y}"
    
    async def add_text_watermark_to_video(
        self,
        input_path: str,
        output_path: str,
        text: str,
        font_file: Optional[str] = None,
        font_size: int = 48,
        font_color: str = "white",
        position: str = "bottom-right",
        margin: int = 20,
        opacity: float = 0.8,
        background_color: Optional[str] = None,
        background_padding: int = 10,
        video_codec: Optional[str] = None,
        audio_codec: str = "copy",
        quality_preset: str = "medium",
        custom_options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Add text watermark to a video
        
        Args:
            input_path: Path to input video
            output_path: Path for output video
            text: Text to use as watermark
            font_file: Path to font file (optional)
            font_size: Font size
            font_color: Font color (e.g., "white", "black", "#FFFFFF")
            position: Text position
            margin: Margin from edges
            opacity: Text opacity (0.0-1.0)
            background_color: Optional background color for text
            background_padding: Padding around text background
            video_codec: Video codec to use
            audio_codec: Audio codec
            quality_preset: Quality preset
            custom_options: Additional options
            
        Returns:
            Dict containing processing information
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Validate input
            if not os.path.exists(input_path):
                raise InvalidMediaError(f"Input file not found: {input_path}")
            
            # Get video info
            media_info = await self.get_media_info(input_path)
            video_stream = next((s for s in media_info["streams"] if s["codec_type"] == "video"), None)
            
            if not video_stream:
                raise InvalidMediaError("No video stream found in input file")
            
            video_width = video_stream.get("width", 1920)
            video_height = video_stream.get("height", 1080)
            
            # Build drawtext filter
            drawtext_filter = self._build_drawtext_filter(
                text,
                font_file,
                font_size,
                font_color,
                position,
                margin,
                opacity,
                background_color,
                background_padding,
                video_width,
                video_height
            )
            
            # Build FFmpeg command
            cmd = [self.ffmpeg_path, "-i", input_path]
            
            # Add hardware decoding if available
            if self.enable_gpu and self.gpu_type != GPUType.NONE:
                hw_params = self._get_hardware_decode_params()
                if hw_params:
                    cmd = cmd[:1] + hw_params + cmd[1:]
            
            # Add drawtext filter
            cmd.extend(["-vf", drawtext_filter])
            
            # Video codec
            if not video_codec:
                video_codec = self._get_video_codec(quality_preset)
            
            if self.enable_gpu and video_codec in ["h264", "h265", "hevc"]:
                gpu_codec = self._get_gpu_encoder(video_codec)
                if gpu_codec:
                    cmd.extend(["-c:v", gpu_codec])
                    cmd.extend(self._get_gpu_encoding_params(gpu_codec, quality_preset))
                else:
                    cmd.extend(["-c:v", f"lib{video_codec}"])
                    cmd.extend(self._get_quality_params(quality_preset))
            else:
                cmd.extend(["-c:v", video_codec])
                cmd.extend(self._get_quality_params(quality_preset))
            
            # Audio codec
            cmd.extend(["-c:a", audio_codec])
            
            # Add custom options
            if custom_options:
                for key, value in custom_options.items():
                    cmd.extend([f"-{key}", str(value)])
            
            # Output file
            cmd.extend(["-y", output_path])
            
            # Run FFmpeg
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=settings.processing_timeout
            )
            
            if process.returncode != 0:
                raise FFmpegError(
                    f"Text watermarking failed",
                    details={"stderr": stderr.decode(), "cmd": " ".join(cmd)}
                )
            
            # Get output file info
            output_info = await self.get_media_info(output_path)
            processing_time = asyncio.get_event_loop().time() - start_time
            
            logger.info(
                "text_watermark_added_to_video",
                input_path=input_path,
                output_path=output_path,
                text=text,
                position=position,
                font_size=font_size,
                processing_time=processing_time
            )
            
            return {
                "input_path": input_path,
                "output_path": output_path,
                "text": text,
                "position": position,
                "font_size": font_size,
                "font_color": font_color,
                "opacity": opacity,
                "duration": output_info.get("duration", 0),
                "size": output_info.get("size", 0),
                "video_codec": video_codec,
                "processing_time": processing_time,
                "gpu_accelerated": self.enable_gpu and self.gpu_type != GPUType.NONE
            }
            
        except asyncio.TimeoutError:
            raise ProcessingTimeoutError(
                f"Text watermarking timed out after {settings.processing_timeout} seconds"
            )
        except Exception as e:
            logger.error(
                "text_watermark_video_failed",
                error=str(e),
                input_path=input_path,
                text=text
            )
            if isinstance(e, (FFmpegError, InvalidMediaError, ProcessingTimeoutError)):
                raise
            raise FFmpegError(f"Text watermarking failed: {str(e)}")
    
    def _build_drawtext_filter(
        self,
        text: str,
        font_file: Optional[str],
        font_size: int,
        font_color: str,
        position: str,
        margin: int,
        opacity: float,
        background_color: Optional[str],
        background_padding: int,
        video_width: int,
        video_height: int
    ) -> str:
        """Build drawtext filter for text watermarking"""
        # Escape special characters in text
        escaped_text = text.replace("'", "\\'").replace(":", "\\:")
        
        # Base filter
        filter_parts = [f"drawtext=text='{escaped_text}'"]
        
        # Font settings
        if font_file and os.path.exists(font_file):
            filter_parts.append(f"fontfile='{font_file}'")
        filter_parts.append(f"fontsize={font_size}")
        
        # Font color with opacity
        if opacity < 1.0:
            # Convert opacity to hex (00-FF)
            opacity_hex = format(int(opacity * 255), '02x')
            filter_parts.append(f"fontcolor={font_color}@{opacity}")
        else:
            filter_parts.append(f"fontcolor={font_color}")
        
        # Position calculations
        if position == "top-left":
            x = margin
            y = margin
        elif position == "top-right":
            x = f"w-text_w-{margin}"
            y = margin
        elif position == "bottom-left":
            x = margin
            y = f"h-text_h-{margin}"
        elif position == "bottom-right":
            x = f"w-text_w-{margin}"
            y = f"h-text_h-{margin}"
        elif position == "center":
            x = "(w-text_w)/2"
            y = "(h-text_h)/2"
        else:
            # Default to bottom-right
            x = f"w-text_w-{margin}"
            y = f"h-text_h-{margin}"
        
        filter_parts.append(f"x={x}")
        filter_parts.append(f"y={y}")
        
        # Background box if specified
        if background_color:
            filter_parts.append("box=1")
            filter_parts.append(f"boxcolor={background_color}")
            filter_parts.append(f"boxborderw={background_padding}")
        
        return ":".join(filter_parts)


# Singleton instance
_ffmpeg_service: Optional[FFmpegService] = None


async def get_ffmpeg_service() -> FFmpegService:
    """Get FFmpeg service instance"""
    global _ffmpeg_service
    
    if _ffmpeg_service is None:
        _ffmpeg_service = FFmpegService()
    
    return _ffmpeg_service