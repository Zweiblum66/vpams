"""
Media Processing Utilities

Handles video, audio, and image processing tasks.
"""

import asyncio
import subprocess
import json
from typing import Dict, Any, Optional, Callable, List
from pathlib import Path
import structlog
import cv2
import numpy as np
from PIL import Image
import re

from ..core.config import settings
from ..models.schemas import TranscodeParameters, ImageProcessingParameters


logger = structlog.get_logger()


class MediaProcessor:
    """Handles media processing tasks"""
    
    def __init__(self):
        self.ffmpeg_path = "ffmpeg"
        self.ffprobe_path = "ffprobe"
        self.hardware_accel = settings.ENABLE_HARDWARE_ACCELERATION
    
    async def initialize(self):
        """Initialize media processor"""
        # Check FFmpeg availability
        try:
            result = await self._run_command([self.ffmpeg_path, "-version"])
            logger.info("FFmpeg available", version=result.split('\n')[0])
        except Exception as e:
            logger.error("FFmpeg not available", error=str(e))
            raise
    
    async def cleanup(self):
        """Cleanup media processor"""
        pass
    
    async def transcode_video(
        self,
        input_path: Path,
        output_path: Path,
        params: TranscodeParameters,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """Transcode video file"""
        logger.info(
            "Transcoding video",
            input=str(input_path),
            output=str(output_path),
            params=params.dict()
        )
        
        # Build FFmpeg command
        cmd = [self.ffmpeg_path, "-i", str(input_path)]
        
        # Hardware acceleration
        if params.hardware_acceleration and self.hardware_accel:
            # Try to use NVENC for NVIDIA GPUs
            if params.video_codec == "h264":
                cmd.extend(["-c:v", "h264_nvenc"])
            elif params.video_codec == "h265":
                cmd.extend(["-c:v", "hevc_nvenc"])
            else:
                cmd.extend(["-c:v", params.video_codec or "libx264"])
        else:
            cmd.extend(["-c:v", params.video_codec or "libx264"])
        
        # Audio codec
        if params.audio_codec:
            cmd.extend(["-c:a", params.audio_codec])
        
        # Resolution
        if params.resolution:
            cmd.extend(["-s", params.resolution])
        
        # Bitrate
        if params.bitrate:
            cmd.extend(["-b:v", params.bitrate])
        
        # Frame rate
        if params.fps:
            cmd.extend(["-r", str(params.fps)])
        
        # Encoding preset
        cmd.extend(["-preset", params.preset])
        
        # Two-pass encoding
        if params.two_pass:
            # First pass
            pass1_cmd = cmd + ["-pass", "1", "-f", "null", "-y", "/dev/null"]
            await self._run_ffmpeg_with_progress(pass1_cmd, progress_callback, 50)
            
            # Second pass
            cmd.extend(["-pass", "2"])
        
        # Output file
        cmd.extend(["-y", str(output_path)])
        
        # Run transcoding
        duration = await self._get_video_duration(input_path)
        await self._run_ffmpeg_with_progress(
            cmd,
            progress_callback,
            100 if not params.two_pass else 50,
            duration
        )
        
        # Get output file info
        output_info = await self.extract_metadata(output_path)
        
        return {
            "success": True,
            "output_format": params.output_format,
            "output_size": output_path.stat().st_size,
            "output_info": output_info
        }
    
    async def process_image(
        self,
        input_path: Path,
        output_path: Path,
        params: ImageProcessingParameters
    ) -> Dict[str, Any]:
        """Process image file"""
        logger.info(
            "Processing image",
            input=str(input_path),
            output=str(output_path),
            params=params.dict()
        )
        
        # Open image
        img = Image.open(input_path)
        
        # Get original dimensions
        orig_width, orig_height = img.size
        
        # Process based on operation
        if params.operation == "resize":
            if params.width and params.height:
                if params.maintain_aspect_ratio:
                    img.thumbnail((params.width, params.height), Image.Resampling.LANCZOS)
                else:
                    img = img.resize((params.width, params.height), Image.Resampling.LANCZOS)
            elif params.width:
                ratio = params.width / orig_width
                new_height = int(orig_height * ratio)
                img = img.resize((params.width, new_height), Image.Resampling.LANCZOS)
            elif params.height:
                ratio = params.height / orig_height
                new_width = int(orig_width * ratio)
                img = img.resize((new_width, params.height), Image.Resampling.LANCZOS)
        
        elif params.operation == "crop":
            if params.width and params.height:
                # Center crop
                left = (orig_width - params.width) // 2
                top = (orig_height - params.height) // 2
                right = left + params.width
                bottom = top + params.height
                img = img.crop((left, top, right, bottom))
        
        elif params.operation == "rotate":
            angle = params.metadata.get("angle", 90)
            img = img.rotate(angle, expand=True)
        
        # Convert format if needed
        if params.format:
            # Handle format conversion
            if params.format.lower() == "jpg":
                params.format = "jpeg"
            
            # Convert RGBA to RGB for JPEG
            if params.format.lower() == "jpeg" and img.mode == "RGBA":
                background = Image.new("RGB", img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[3])
                img = background
        
        # Save with quality setting
        save_kwargs = {"quality": params.quality}
        if params.format:
            save_kwargs["format"] = params.format.upper()
        
        img.save(output_path, **save_kwargs)
        
        # Get output dimensions
        output_img = Image.open(output_path)
        new_width, new_height = output_img.size
        
        return {
            "success": True,
            "original_size": {"width": orig_width, "height": orig_height},
            "output_size": {"width": new_width, "height": new_height},
            "output_format": params.format or input_path.suffix[1:],
            "file_size": output_path.stat().st_size
        }
    
    async def generate_thumbnail(
        self,
        input_path: Path,
        output_path: Path,
        time_offset: float = 0,
        width: int = 320,
        height: int = 180
    ) -> Dict[str, Any]:
        """Generate thumbnail from video"""
        logger.info(
            "Generating thumbnail",
            input=str(input_path),
            time_offset=time_offset
        )
        
        # Use FFmpeg to extract frame
        cmd = [
            self.ffmpeg_path,
            "-ss", str(time_offset),
            "-i", str(input_path),
            "-vframes", "1",
            "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2",
            "-y", str(output_path)
        ]
        
        await self._run_command(cmd)
        
        return {
            "success": True,
            "width": width,
            "height": height,
            "time_offset": time_offset,
            "file_size": output_path.stat().st_size
        }
    
    async def extract_audio(
        self,
        input_path: Path,
        output_path: Path,
        format: str = "wav"
    ) -> Dict[str, Any]:
        """Extract audio from video"""
        cmd = [
            self.ffmpeg_path,
            "-i", str(input_path),
            "-vn",  # No video
            "-acodec", "pcm_s16le" if format == "wav" else "copy",
            "-y", str(output_path)
        ]
        
        await self._run_command(cmd)
        
        return {
            "success": True,
            "format": format,
            "file_size": output_path.stat().st_size
        }
    
    async def normalize_audio(
        self,
        input_path: Path,
        output_path: Path,
        target_level: float = -20
    ) -> Dict[str, Any]:
        """Normalize audio levels"""
        # Use FFmpeg loudnorm filter
        cmd = [
            self.ffmpeg_path,
            "-i", str(input_path),
            "-af", f"loudnorm=I={target_level}:TP=-1.5:LRA=11",
            "-y", str(output_path)
        ]
        
        await self._run_command(cmd)
        
        return {
            "success": True,
            "target_level": target_level,
            "file_size": output_path.stat().st_size
        }
    
    async def extract_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Extract metadata from media file"""
        cmd = [
            self.ffprobe_path,
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            str(file_path)
        ]
        
        output = await self._run_command(cmd)
        metadata = json.loads(output)
        
        # Process metadata
        result = {
            "format": metadata.get("format", {}).get("format_name"),
            "duration": float(metadata.get("format", {}).get("duration", 0)),
            "size": int(metadata.get("format", {}).get("size", 0)),
            "bit_rate": int(metadata.get("format", {}).get("bit_rate", 0)),
            "streams": []
        }
        
        # Process streams
        for stream in metadata.get("streams", []):
            stream_info = {
                "type": stream.get("codec_type"),
                "codec": stream.get("codec_name"),
            }
            
            if stream.get("codec_type") == "video":
                stream_info.update({
                    "width": stream.get("width"),
                    "height": stream.get("height"),
                    "fps": eval(stream.get("r_frame_rate", "0/1")),
                    "pixel_format": stream.get("pix_fmt")
                })
            elif stream.get("codec_type") == "audio":
                stream_info.update({
                    "channels": stream.get("channels"),
                    "sample_rate": int(stream.get("sample_rate", 0)),
                    "channel_layout": stream.get("channel_layout")
                })
            
            result["streams"].append(stream_info)
        
        return result
    
    async def _get_video_duration(self, file_path: Path) -> float:
        """Get video duration in seconds"""
        metadata = await self.extract_metadata(file_path)
        return metadata.get("duration", 0)
    
    async def _run_command(self, cmd: List[str]) -> str:
        """Run command and return output"""
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise RuntimeError(f"Command failed: {stderr.decode()}")
        
        return stdout.decode()
    
    async def _run_ffmpeg_with_progress(
        self,
        cmd: List[str],
        progress_callback: Optional[Callable],
        progress_offset: float = 0,
        total_duration: Optional[float] = None
    ):
        """Run FFmpeg command with progress tracking"""
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Read stderr for progress
        while True:
            line = await process.stderr.readline()
            if not line:
                break
            
            line = line.decode().strip()
            
            # Parse progress
            if progress_callback and total_duration and "time=" in line:
                match = re.search(r'time=(\d+):(\d+):(\d+\.\d+)', line)
                if match:
                    hours, minutes, seconds = match.groups()
                    current_time = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
                    progress = (current_time / total_duration) * (100 - progress_offset) + progress_offset
                    await progress_callback(min(progress, 100))
        
        # Wait for completion
        await process.wait()
        
        if process.returncode != 0:
            stderr = await process.stderr.read()
            raise RuntimeError(f"FFmpeg failed: {stderr.decode()}")