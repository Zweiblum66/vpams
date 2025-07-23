"""
Ultra HD Video Processing Service for 8K and High Resolution Media
"""

import os
import asyncio
import json
import tempfile
from typing import Dict, List, Optional, Tuple, Any, Union
from pathlib import Path
from enum import Enum
import platform
import psutil
from datetime import datetime

from ..core.config import settings
from ..core.exceptions import FFmpegError, InvalidMediaError, ProcessingTimeoutError
from ..core.logging import get_logger
from .ffmpeg_service import FFmpegService, GPUType, GPUCodec

logger = get_logger(__name__)


class UltraHDResolution(str, Enum):
    """Ultra HD resolution standards"""
    UHD_4K = "3840x2160"      # Standard 4K UHD
    CINEMA_4K = "4096x2160"   # Cinema 4K
    UHD_8K = "7680x4320"      # Standard 8K UHD
    CINEMA_8K = "8192x4320"   # Cinema 8K
    FULL_8K = "8192x8192"     # Full 8K square


class UltraHDCodec(str, Enum):
    """Ultra HD optimized codecs"""
    H264 = "h264"
    H265 = "h265"
    AV1 = "av1"
    VP9 = "vp9"
    PRORES = "prores"
    DNXHD = "dnxhd"
    JPEG2000 = "jpeg2000"


class UltraHDBitrate:
    """Recommended bitrates for Ultra HD content"""
    
    # 8K UHD bitrates (Mbps)
    BITRATES_8K = {
        "h264": {"low": 50, "medium": 100, "high": 200, "max": 400},
        "h265": {"low": 25, "medium": 50, "high": 100, "max": 200},
        "av1": {"low": 20, "medium": 40, "high": 80, "max": 160},
        "vp9": {"low": 30, "medium": 60, "high": 120, "max": 240},
        "prores": {"low": 400, "medium": 800, "high": 1200, "max": 2000},
        "dnxhd": {"low": 300, "medium": 600, "high": 900, "max": 1500}
    }
    
    # 4K UHD bitrates (Mbps)
    BITRATES_4K = {
        "h264": {"low": 15, "medium": 25, "high": 50, "max": 100},
        "h265": {"low": 8, "medium": 15, "high": 25, "max": 50},
        "av1": {"low": 6, "medium": 12, "high": 20, "max": 40},
        "vp9": {"low": 10, "medium": 18, "high": 30, "max": 60},
        "prores": {"low": 150, "medium": 300, "high": 450, "max": 600},
        "dnxhd": {"low": 100, "medium": 200, "high": 300, "max": 500}
    }


class UltraHDService:
    """Service for processing Ultra HD (4K/8K) video content"""
    
    def __init__(self, ffmpeg_service: FFmpegService):
        self.ffmpeg_service = ffmpeg_service
        self.system_info = self._get_system_info()
        self.processing_capabilities = self._assess_processing_capabilities()
        
        # 8K processing requires specific optimizations
        self.chunk_processing_enabled = self._should_use_chunk_processing()
        self.tile_processing_enabled = self._should_use_tile_processing()
        
        logger.info(
            "ultra_hd_service_initialized",
            system_memory_gb=self.system_info["memory_gb"],
            cpu_cores=self.system_info["cpu_cores"],
            gpu_enabled=self.ffmpeg_service.enable_gpu,
            chunk_processing=self.chunk_processing_enabled,
            tile_processing=self.tile_processing_enabled
        )
    
    def _get_system_info(self) -> Dict[str, Any]:
        """Get system information for processing optimization"""
        return {
            "memory_gb": round(psutil.virtual_memory().total / (1024**3), 2),
            "cpu_cores": psutil.cpu_count(),
            "cpu_logical": psutil.cpu_count(logical=True),
            "platform": platform.system(),
            "architecture": platform.machine()
        }
    
    def _assess_processing_capabilities(self) -> Dict[str, Any]:
        """Assess system capabilities for Ultra HD processing"""
        memory_gb = self.system_info["memory_gb"]
        cpu_cores = self.system_info["cpu_cores"]
        
        # Minimum requirements for 8K processing
        min_memory_8k = 32  # GB
        min_cores_8k = 8
        
        # Recommended for optimal 8K processing
        recommended_memory_8k = 64  # GB
        recommended_cores_8k = 16
        
        can_process_8k = memory_gb >= min_memory_8k and cpu_cores >= min_cores_8k
        optimal_8k = memory_gb >= recommended_memory_8k and cpu_cores >= recommended_cores_8k
        
        return {
            "can_process_8k": can_process_8k,
            "optimal_8k_performance": optimal_8k,
            "max_concurrent_8k": max(1, min(cpu_cores // 4, memory_gb // 16)),
            "max_concurrent_4k": max(1, min(cpu_cores // 2, memory_gb // 8)),
            "recommended_tile_size": self._calculate_optimal_tile_size(),
            "memory_per_stream_8k": min(16, memory_gb // 4),  # GB per stream
            "memory_per_stream_4k": min(8, memory_gb // 8)    # GB per stream
        }
    
    def _should_use_chunk_processing(self) -> bool:
        """Determine if chunk processing should be used for large files"""
        # Use chunk processing for systems with limited memory
        return self.system_info["memory_gb"] < 64
    
    def _should_use_tile_processing(self) -> bool:
        """Determine if tile-based processing should be used"""
        # Use tile processing for very high resolution content
        return True  # Always beneficial for 8K content
    
    def _calculate_optimal_tile_size(self) -> Tuple[int, int]:
        """Calculate optimal tile size for processing"""
        memory_gb = self.system_info["memory_gb"]
        
        if memory_gb >= 64:
            return (1920, 1080)  # Large tiles for high-memory systems
        elif memory_gb >= 32:
            return (1280, 720)   # Medium tiles
        else:
            return (960, 540)    # Small tiles for limited memory
    
    async def process_8k_video(
        self,
        input_path: str,
        output_path: str,
        codec: UltraHDCodec = UltraHDCodec.H265,
        quality: str = "medium",
        resolution: Optional[UltraHDResolution] = None,
        enable_hdr: bool = False,
        preserve_metadata: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """Process 8K video with optimizations"""
        
        try:
            # Validate input
            input_info = await self._analyze_video_properties(input_path)
            
            if not self.processing_capabilities["can_process_8k"]:
                raise ProcessingTimeoutError(
                    "System does not meet minimum requirements for 8K processing"
                )
            
            # Determine processing method
            if input_info["width"] >= 7680 or input_info["height"] >= 4320:
                if self.tile_processing_enabled and input_info["duration"] > 300:  # 5+ minutes
                    return await self._process_8k_tiled(
                        input_path, output_path, codec, quality, resolution, enable_hdr, **kwargs
                    )
                elif self.chunk_processing_enabled and input_info["duration"] > 60:  # 1+ minutes
                    return await self._process_8k_chunked(
                        input_path, output_path, codec, quality, resolution, enable_hdr, **kwargs
                    )
            
            # Standard processing for smaller files or high-end systems
            return await self._process_8k_standard(
                input_path, output_path, codec, quality, resolution, enable_hdr, **kwargs
            )
            
        except Exception as e:
            logger.error("8k_processing_failed", error=str(e), input_path=input_path)
            raise
    
    async def _process_8k_standard(
        self,
        input_path: str,
        output_path: str,
        codec: UltraHDCodec,
        quality: str,
        resolution: Optional[UltraHDResolution],
        enable_hdr: bool,
        **kwargs
    ) -> Dict[str, Any]:
        """Standard 8K processing for optimal systems"""
        
        # Build FFmpeg command
        cmd_args = await self._build_8k_ffmpeg_command(
            input_path, output_path, codec, quality, resolution, enable_hdr, **kwargs
        )
        
        # Execute with extended timeout for 8K
        timeout = kwargs.get("timeout", 7200)  # 2 hours default for 8K
        
        start_time = datetime.utcnow()
        result = await self.ffmpeg_service.run_ffmpeg_command(cmd_args, timeout=timeout)
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        # Analyze output
        output_info = await self._analyze_video_properties(output_path)
        
        return {
            "processing_method": "standard",
            "processing_time_seconds": processing_time,
            "input_size_mb": os.path.getsize(input_path) / (1024 * 1024),
            "output_size_mb": os.path.getsize(output_path) / (1024 * 1024),
            "compression_ratio": os.path.getsize(input_path) / os.path.getsize(output_path),
            "output_properties": output_info,
            "gpu_used": self.ffmpeg_service.enable_gpu,
            "codec_used": codec,
            "quality_setting": quality
        }
    
    async def _process_8k_chunked(
        self,
        input_path: str,
        output_path: str,
        codec: UltraHDCodec,
        quality: str,
        resolution: Optional[UltraHDResolution],
        enable_hdr: bool,
        **kwargs
    ) -> Dict[str, Any]:
        """Process 8K video in temporal chunks to manage memory"""
        
        input_info = await self._analyze_video_properties(input_path)
        duration = input_info["duration"]
        
        # Calculate chunk duration based on system capabilities
        chunk_duration = self._calculate_chunk_duration(duration)
        chunks_info = []
        
        # Create temporary directory for chunks
        with tempfile.TemporaryDirectory(prefix="mams_8k_chunks_") as temp_dir:
            temp_path = Path(temp_dir)
            
            # Split into chunks
            chunk_files = []
            current_time = 0
            chunk_index = 0
            
            while current_time < duration:
                remaining_time = duration - current_time
                actual_chunk_duration = min(chunk_duration, remaining_time)
                
                chunk_input = temp_path / f"chunk_{chunk_index:04d}_input.mkv"
                chunk_output = temp_path / f"chunk_{chunk_index:04d}_output.mkv"
                
                # Extract chunk
                extract_cmd = [
                    self.ffmpeg_service.ffmpeg_path,
                    "-i", input_path,
                    "-ss", str(current_time),
                    "-t", str(actual_chunk_duration),
                    "-c", "copy",
                    "-avoid_negative_ts", "make_zero",
                    str(chunk_input)
                ]
                
                await self.ffmpeg_service.run_ffmpeg_command(extract_cmd)
                
                # Process chunk
                chunk_cmd = await self._build_8k_ffmpeg_command(
                    str(chunk_input), str(chunk_output), codec, quality, resolution, enable_hdr, **kwargs
                )
                
                chunk_start = datetime.utcnow()
                await self.ffmpeg_service.run_ffmpeg_command(chunk_cmd)
                chunk_time = (datetime.utcnow() - chunk_start).total_seconds()
                
                chunks_info.append({
                    "index": chunk_index,
                    "start_time": current_time,
                    "duration": actual_chunk_duration,
                    "processing_time": chunk_time,
                    "input_size_mb": os.path.getsize(chunk_input) / (1024 * 1024),
                    "output_size_mb": os.path.getsize(chunk_output) / (1024 * 1024)
                })
                
                chunk_files.append(str(chunk_output))
                current_time += actual_chunk_duration
                chunk_index += 1
            
            # Concatenate chunks
            concat_list_file = temp_path / "concat_list.txt"
            with open(concat_list_file, 'w') as f:
                for chunk_file in chunk_files:
                    f.write(f"file '{chunk_file}'\n")
            
            concat_cmd = [
                self.ffmpeg_service.ffmpeg_path,
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_list_file),
                "-c", "copy",
                output_path
            ]
            
            await self.ffmpeg_service.run_ffmpeg_command(concat_cmd)
        
        # Calculate totals
        total_processing_time = sum(chunk["processing_time"] for chunk in chunks_info)
        total_input_size = sum(chunk["input_size_mb"] for chunk in chunks_info)
        total_output_size = sum(chunk["output_size_mb"] for chunk in chunks_info)
        
        return {
            "processing_method": "chunked",
            "processing_time_seconds": total_processing_time,
            "chunk_count": len(chunks_info),
            "chunk_duration_seconds": chunk_duration,
            "chunks_info": chunks_info,
            "input_size_mb": total_input_size,
            "output_size_mb": total_output_size,
            "compression_ratio": total_input_size / total_output_size if total_output_size > 0 else 0,
            "codec_used": codec,
            "quality_setting": quality
        }
    
    async def _process_8k_tiled(
        self,
        input_path: str,
        output_path: str,
        codec: UltraHDCodec,
        quality: str,
        resolution: Optional[UltraHDResolution],
        enable_hdr: bool,
        **kwargs
    ) -> Dict[str, Any]:
        """Process 8K video using spatial tiling for memory efficiency"""
        
        input_info = await self._analyze_video_properties(input_path)
        tile_width, tile_height = self.processing_capabilities["recommended_tile_size"]
        
        # Calculate tile grid
        video_width = input_info["width"]
        video_height = input_info["height"]
        
        tiles_x = (video_width + tile_width - 1) // tile_width
        tiles_y = (video_height + tile_height - 1) // tile_height
        
        tiles_info = []
        
        # Create temporary directory for tiles
        with tempfile.TemporaryDirectory(prefix="mams_8k_tiles_") as temp_dir:
            temp_path = Path(temp_dir)
            
            # Process each tile
            tile_files = []
            
            for y in range(tiles_y):
                for x in range(tiles_x):
                    tile_x = x * tile_width
                    tile_y = y * tile_height
                    
                    # Calculate actual tile dimensions (handle edge tiles)
                    actual_width = min(tile_width, video_width - tile_x)
                    actual_height = min(tile_height, video_height - tile_y)
                    
                    tile_input = temp_path / f"tile_{y:02d}_{x:02d}_input.mkv"
                    tile_output = temp_path / f"tile_{y:02d}_{x:02d}_output.mkv"
                    
                    # Extract tile
                    crop_filter = f"crop={actual_width}:{actual_height}:{tile_x}:{tile_y}"
                    
                    extract_cmd = [
                        self.ffmpeg_service.ffmpeg_path,
                        "-i", input_path,
                        "-vf", crop_filter,
                        "-c:a", "copy",
                        str(tile_input)
                    ]
                    
                    await self.ffmpeg_service.run_ffmpeg_command(extract_cmd)
                    
                    # Process tile
                    tile_cmd = await self._build_8k_ffmpeg_command(
                        str(tile_input), str(tile_output), codec, quality, None, enable_hdr, **kwargs
                    )
                    
                    tile_start = datetime.utcnow()
                    await self.ffmpeg_service.run_ffmpeg_command(tile_cmd)
                    tile_time = (datetime.utcnow() - tile_start).total_seconds()
                    
                    tiles_info.append({
                        "x": x, "y": y,
                        "tile_x": tile_x, "tile_y": tile_y,
                        "width": actual_width, "height": actual_height,
                        "processing_time": tile_time,
                        "input_size_mb": os.path.getsize(tile_input) / (1024 * 1024),
                        "output_size_mb": os.path.getsize(tile_output) / (1024 * 1024)
                    })
                    
                    tile_files.append({
                        "file": str(tile_output),
                        "x": x, "y": y,
                        "tile_x": tile_x, "tile_y": tile_y,
                        "width": actual_width, "height": actual_height
                    })
            
            # Reassemble tiles using complex filter
            await self._reassemble_tiles(tile_files, output_path, video_width, video_height)
        
        # Calculate totals
        total_processing_time = sum(tile["processing_time"] for tile in tiles_info)
        total_input_size = sum(tile["input_size_mb"] for tile in tiles_info)
        total_output_size = sum(tile["output_size_mb"] for tile in tiles_info)
        
        return {
            "processing_method": "tiled",
            "processing_time_seconds": total_processing_time,
            "tile_count": len(tiles_info),
            "tile_grid": f"{tiles_x}x{tiles_y}",
            "tile_size": f"{tile_width}x{tile_height}",
            "tiles_info": tiles_info,
            "input_size_mb": total_input_size,
            "output_size_mb": total_output_size,
            "compression_ratio": total_input_size / total_output_size if total_output_size > 0 else 0,
            "codec_used": codec,
            "quality_setting": quality
        }
    
    async def _reassemble_tiles(
        self,
        tile_files: List[Dict],
        output_path: str,
        video_width: int,
        video_height: int
    ):
        """Reassemble processed tiles into final video"""
        
        # Build complex filter for tile reassembly
        inputs = []
        filter_complex = []
        
        # Add all tile inputs
        for i, tile in enumerate(tile_files):
            inputs.extend(["-i", tile["file"]])
        
        # Build overlay filter chain
        if len(tile_files) == 1:
            # Single tile, just copy
            filter_complex = ["[0:v]copy[output]"]
        else:
            # Create base canvas
            filter_complex.append(f"color=black:{video_width}x{video_height}:duration=1[base]")
            
            # Overlay each tile
            current_input = "[base]"
            for i, tile in enumerate(tile_files):
                if i == len(tile_files) - 1:
                    output_label = "[output]"
                else:
                    output_label = f"[tmp{i}]"
                
                overlay_filter = f"{current_input}[{i}:v]overlay={tile['tile_x']}:{tile['tile_y']}{output_label}"
                filter_complex.append(overlay_filter)
                current_input = f"[tmp{i}]"
        
        # Build reassembly command
        cmd = [
            self.ffmpeg_service.ffmpeg_path,
            *inputs,
            "-filter_complex", ";".join(filter_complex),
            "-map", "[output]",
            "-map", "0:a?",  # Copy audio from first input if available
            "-c:a", "copy",
            output_path
        ]
        
        await self.ffmpeg_service.run_ffmpeg_command(cmd)
    
    async def _build_8k_ffmpeg_command(
        self,
        input_path: str,
        output_path: str,
        codec: UltraHDCodec,
        quality: str,
        resolution: Optional[UltraHDResolution],
        enable_hdr: bool,
        **kwargs
    ) -> List[str]:
        """Build optimized FFmpeg command for 8K processing"""
        
        # Get GPU-accelerated codec if available
        encoder = self._get_optimal_encoder(codec)
        bitrate = self._get_bitrate_for_quality(codec, quality, resolution)
        
        cmd = [
            self.ffmpeg_service.ffmpeg_path,
            "-i", input_path
        ]
        
        # Hardware acceleration
        if self.ffmpeg_service.enable_gpu and self.ffmpeg_service.gpu_type != GPUType.NONE:
            cmd.extend(self._get_gpu_acceleration_args())
        
        # Video encoding settings
        video_args = [
            "-c:v", encoder,
            "-b:v", f"{bitrate}M",
            "-maxrate", f"{int(bitrate * 1.5)}M",
            "-bufsize", f"{int(bitrate * 2)}M"
        ]
        
        # Codec-specific optimizations
        if codec == UltraHDCodec.H265:
            video_args.extend([
                "-preset", "slower" if quality in ["high", "max"] else "medium",
                "-profile:v", "main10" if enable_hdr else "main",
                "-level", "6.2",  # Support for 8K
                "-tier", "high",
                "-x265-params", "pools=none:frame-threads=1"  # Optimize for 8K
            ])
        elif codec == UltraHDCodec.AV1:
            video_args.extend([
                "-cpu-used", "2" if quality in ["high", "max"] else "4",
                "-row-mt", "1",
                "-tile-columns", "2",
                "-tile-rows", "1"
            ])
        elif codec == UltraHDCodec.H264:
            video_args.extend([
                "-preset", "slower" if quality in ["high", "max"] else "medium",
                "-profile:v", "high",
                "-level", "6.2"
            ])
        
        # Resolution scaling if specified
        if resolution:
            video_args.extend(["-s", resolution.value])
        
        # HDR settings
        if enable_hdr:
            video_args.extend(self._get_hdr_args(codec))
        
        # Audio settings
        audio_args = [
            "-c:a", kwargs.get("audio_codec", "aac"),
            "-b:a", kwargs.get("audio_bitrate", "256k")
        ]
        
        # Performance optimizations
        performance_args = [
            "-threads", str(self.ffmpeg_service.threads),
            "-avoid_negative_ts", "make_zero"
        ]
        
        cmd.extend(video_args + audio_args + performance_args + [output_path])
        
        return cmd
    
    def _get_optimal_encoder(self, codec: UltraHDCodec) -> str:
        """Get the optimal encoder for the codec"""
        if not self.ffmpeg_service.enable_gpu:
            return self._get_software_encoder(codec)
        
        # Try GPU encoders first
        gpu_encoders = {
            GPUType.NVIDIA: GPUCodec.NVIDIA,
            GPUType.AMD: GPUCodec.AMD,
            GPUType.INTEL: GPUCodec.INTEL,
            GPUType.APPLE: GPUCodec.APPLE
        }
        
        if self.ffmpeg_service.gpu_type in gpu_encoders:
            gpu_codec_map = gpu_encoders[self.ffmpeg_service.gpu_type]
            if codec.value in gpu_codec_map:
                return gpu_codec_map[codec.value]
        
        return self._get_software_encoder(codec)
    
    def _get_software_encoder(self, codec: UltraHDCodec) -> str:
        """Get software encoder for codec"""
        encoders = {
            UltraHDCodec.H264: "libx264",
            UltraHDCodec.H265: "libx265",
            UltraHDCodec.AV1: "libaom-av1",
            UltraHDCodec.VP9: "libvpx-vp9",
            UltraHDCodec.PRORES: "prores_ks",
            UltraHDCodec.DNXHD: "dnxhd",
            UltraHDCodec.JPEG2000: "libopenjpeg"
        }
        return encoders.get(codec, "libx265")  # Default to H.265
    
    def _get_bitrate_for_quality(self, codec: UltraHDCodec, quality: str, resolution: Optional[UltraHDResolution]) -> int:
        """Get appropriate bitrate for quality and resolution"""
        # Determine if this is 8K or 4K
        is_8k = resolution and ("8k" in resolution.value.lower() or "8192" in resolution.value or "7680" in resolution.value)
        
        bitrates = UltraHDBitrate.BITRATES_8K if is_8k else UltraHDBitrate.BITRATES_4K
        codec_bitrates = bitrates.get(codec.value, bitrates["h265"])
        
        return codec_bitrates.get(quality, codec_bitrates["medium"])
    
    def _get_gpu_acceleration_args(self) -> List[str]:
        """Get GPU acceleration arguments"""
        if self.ffmpeg_service.gpu_type == GPUType.NVIDIA:
            return ["-hwaccel", "cuda", "-hwaccel_output_format", "cuda"]
        elif self.ffmpeg_service.gpu_type == GPUType.AMD:
            return ["-hwaccel", "d3d11va"]
        elif self.ffmpeg_service.gpu_type == GPUType.INTEL:
            return ["-hwaccel", "qsv"]
        elif self.ffmpeg_service.gpu_type == GPUType.APPLE:
            return ["-hwaccel", "videotoolbox"]
        return []
    
    def _get_hdr_args(self, codec: UltraHDCodec) -> List[str]:
        """Get HDR encoding arguments"""
        if codec in [UltraHDCodec.H265, UltraHDCodec.AV1]:
            return [
                "-colorspace", "bt2020nc",
                "-color_primaries", "bt2020",
                "-color_trc", "smpte2084",
                "-color_range", "tv"
            ]
        return []
    
    def _calculate_chunk_duration(self, total_duration: float) -> float:
        """Calculate optimal chunk duration based on system capabilities"""
        memory_gb = self.system_info["memory_gb"]
        
        if memory_gb >= 64:
            return min(600, total_duration / 4)  # 10 minutes max, or 1/4 of video
        elif memory_gb >= 32:
            return min(300, total_duration / 6)  # 5 minutes max, or 1/6 of video
        else:
            return min(120, total_duration / 10)  # 2 minutes max, or 1/10 of video
    
    async def _analyze_video_properties(self, video_path: str) -> Dict[str, Any]:
        """Analyze video properties using FFprobe"""
        cmd = [
            self.ffmpeg_service.ffprobe_path,
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            video_path
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
        
        return {
            "width": int(video_stream.get("width", 0)),
            "height": int(video_stream.get("height", 0)),
            "duration": float(probe_data.get("format", {}).get("duration", 0)),
            "bitrate": int(probe_data.get("format", {}).get("bit_rate", 0)),
            "codec": video_stream.get("codec_name"),
            "profile": video_stream.get("profile"),
            "level": video_stream.get("level"),
            "pixel_format": video_stream.get("pix_fmt"),
            "frame_rate": eval(video_stream.get("r_frame_rate", "0/1")),
            "color_space": video_stream.get("color_space"),
            "color_primaries": video_stream.get("color_primaries"),
            "color_transfer": video_stream.get("color_trc")
        }
    
    async def generate_8k_proxy_profiles(self, input_path: str, output_dir: str) -> Dict[str, Any]:
        """Generate multiple proxy profiles optimized for 8K content"""
        
        profiles = {
            "8k_preview": {
                "resolution": UltraHDResolution.UHD_8K,
                "codec": UltraHDCodec.H265,
                "quality": "low",
                "suffix": "_8k_preview"
            },
            "4k_proxy": {
                "resolution": UltraHDResolution.UHD_4K,
                "codec": UltraHDCodec.H265,
                "quality": "medium",
                "suffix": "_4k_proxy"
            },
            "2k_proxy": {
                "resolution": "2560x1440",
                "codec": UltraHDCodec.H264,
                "quality": "medium",
                "suffix": "_2k_proxy"
            },
            "1080p_proxy": {
                "resolution": "1920x1080",
                "codec": UltraHDCodec.H264,
                "quality": "high",
                "suffix": "_1080p_proxy"
            },
            "720p_proxy": {
                "resolution": "1280x720",
                "codec": UltraHDCodec.H264,
                "quality": "high",
                "suffix": "_720p_proxy"
            }
        }
        
        results = {}
        base_name = Path(input_path).stem
        
        for profile_name, profile_config in profiles.items():
            output_path = f"{output_dir}/{base_name}{profile_config['suffix']}.mp4"
            
            try:
                result = await self.process_8k_video(
                    input_path=input_path,
                    output_path=output_path,
                    codec=profile_config["codec"],
                    quality=profile_config["quality"],
                    resolution=profile_config.get("resolution")
                )
                
                results[profile_name] = {
                    "success": True,
                    "output_path": output_path,
                    "processing_info": result
                }
                
            except Exception as e:
                results[profile_name] = {
                    "success": False,
                    "error": str(e)
                }
                logger.error(f"Failed to generate {profile_name}", error=str(e))
        
        return results


# Service instance
_ultra_hd_service: Optional[UltraHDService] = None


async def get_ultra_hd_service() -> UltraHDService:
    """Get or create Ultra HD service instance"""
    global _ultra_hd_service
    
    if _ultra_hd_service is None:
        from .ffmpeg_service import get_ffmpeg_service
        ffmpeg_service = await get_ffmpeg_service()
        _ultra_hd_service = UltraHDService(ffmpeg_service)
    
    return _ultra_hd_service