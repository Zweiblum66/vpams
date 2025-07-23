"""
Live Streaming Service for real-time media production and streaming
"""

import os
import json
import asyncio
import subprocess
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
from datetime import datetime, timedelta
import aiofiles
from pathlib import Path
import uuid
import tempfile
import shutil

from ..core.logging import get_logger
from ..core.exceptions import ProxyGenerationError

logger = get_logger(__name__)


class StreamingProtocol(Enum):
    """Supported streaming protocols"""
    HLS = "hls"
    DASH = "dash"
    RTMP = "rtmp"
    RTSP = "rtsp"
    SRT = "srt"
    WEBRTC = "webrtc"
    RIST = "rist"
    NDI = "ndi"


class StreamQuality(Enum):
    """Stream quality presets"""
    LOW = "low"  # 480p, 1Mbps
    MEDIUM = "medium"  # 720p, 3Mbps
    HIGH = "high"  # 1080p, 6Mbps
    ULTRA = "ultra"  # 4K, 20Mbps
    ADAPTIVE = "adaptive"  # Multiple bitrates
    CUSTOM = "custom"


class StreamCodec(Enum):
    """Supported video codecs for streaming"""
    H264 = "h264"
    H265 = "h265"
    VP8 = "vp8"
    VP9 = "vp9"
    AV1 = "av1"


class StreamAudioCodec(Enum):
    """Supported audio codecs for streaming"""
    AAC = "aac"
    OPUS = "opus"
    MP3 = "mp3"
    FLAC = "flac"


class StreamLatency(Enum):
    """Latency modes for streaming"""
    ULTRA_LOW = "ultra_low"  # < 1 second
    LOW = "low"  # 1-3 seconds
    STANDARD = "standard"  # 3-10 seconds
    HIGH = "high"  # > 10 seconds


class DVRMode(Enum):
    """DVR (Digital Video Recording) modes"""
    DISABLED = "disabled"
    SLIDING_WINDOW = "sliding_window"  # Keep last N minutes
    FULL_RECORDING = "full_recording"  # Record entire stream
    EVENT_BASED = "event_based"  # Record on trigger


class LiveStreamingService:
    """Service for managing live streaming operations"""
    
    def __init__(self):
        self.ffmpeg_path = "ffmpeg"
        self.ffprobe_path = "ffprobe"
        self.nginx_rtmp_path = "/usr/local/nginx"  # For RTMP server
        self.srt_live_server_path = "srt-live-server"  # For SRT
        
        # Quality presets
        self.quality_presets = {
            StreamQuality.LOW: {
                "resolution": "854x480",
                "video_bitrate": "1000k",
                "audio_bitrate": "96k",
                "framerate": 30
            },
            StreamQuality.MEDIUM: {
                "resolution": "1280x720",
                "video_bitrate": "3000k",
                "audio_bitrate": "128k",
                "framerate": 30
            },
            StreamQuality.HIGH: {
                "resolution": "1920x1080",
                "video_bitrate": "6000k",
                "audio_bitrate": "192k",
                "framerate": 30
            },
            StreamQuality.ULTRA: {
                "resolution": "3840x2160",
                "video_bitrate": "20000k",
                "audio_bitrate": "256k",
                "framerate": 60
            }
        }
        
        # Adaptive bitrate ladder
        self.abr_ladder = [
            {"name": "360p", "resolution": "640x360", "bitrate": "500k", "framerate": 30},
            {"name": "480p", "resolution": "854x480", "bitrate": "1000k", "framerate": 30},
            {"name": "720p", "resolution": "1280x720", "bitrate": "3000k", "framerate": 30},
            {"name": "1080p", "resolution": "1920x1080", "bitrate": "6000k", "framerate": 30},
            {"name": "1440p", "resolution": "2560x1440", "bitrate": "10000k", "framerate": 60},
            {"name": "2160p", "resolution": "3840x2160", "bitrate": "20000k", "framerate": 60}
        ]
        
        # Active streams tracking
        self.active_streams = {}
    
    async def start_live_stream(
        self,
        input_source: str,
        output_url: str,
        protocol: StreamingProtocol,
        quality: StreamQuality = StreamQuality.HIGH,
        codec: StreamCodec = StreamCodec.H264,
        audio_codec: StreamAudioCodec = StreamAudioCodec.AAC,
        latency: StreamLatency = StreamLatency.LOW,
        dvr_mode: DVRMode = DVRMode.DISABLED,
        custom_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Start a live stream from input source to output destination
        
        Args:
            input_source: Input URL or device (e.g., rtmp://input, /dev/video0)
            output_url: Output streaming URL
            protocol: Streaming protocol to use
            quality: Stream quality preset
            codec: Video codec for encoding
            audio_codec: Audio codec for encoding
            latency: Target latency mode
            dvr_mode: DVR recording mode
            custom_params: Custom FFmpeg parameters
        
        Returns:
            Stream information including stream ID and status
        """
        try:
            stream_id = str(uuid.uuid4())
            
            # Build FFmpeg command based on protocol
            if protocol == StreamingProtocol.HLS:
                cmd = await self._build_hls_command(
                    input_source, output_url, quality, codec, audio_codec, latency, custom_params
                )
            elif protocol == StreamingProtocol.DASH:
                cmd = await self._build_dash_command(
                    input_source, output_url, quality, codec, audio_codec, latency, custom_params
                )
            elif protocol == StreamingProtocol.RTMP:
                cmd = await self._build_rtmp_command(
                    input_source, output_url, quality, codec, audio_codec, custom_params
                )
            elif protocol == StreamingProtocol.SRT:
                cmd = await self._build_srt_command(
                    input_source, output_url, quality, codec, audio_codec, latency, custom_params
                )
            elif protocol == StreamingProtocol.RTSP:
                cmd = await self._build_rtsp_command(
                    input_source, output_url, quality, codec, audio_codec, custom_params
                )
            else:
                raise ProxyGenerationError(f"Unsupported streaming protocol: {protocol}")
            
            # Start the streaming process
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Set up DVR if enabled
            dvr_path = None
            if dvr_mode != DVRMode.DISABLED:
                dvr_path = await self._setup_dvr(stream_id, input_source, dvr_mode)
            
            # Track active stream
            self.active_streams[stream_id] = {
                "process": process,
                "start_time": datetime.utcnow(),
                "input_source": input_source,
                "output_url": output_url,
                "protocol": protocol.value,
                "quality": quality.value,
                "codec": codec.value,
                "audio_codec": audio_codec.value,
                "latency": latency.value,
                "dvr_mode": dvr_mode.value,
                "dvr_path": dvr_path,
                "status": "active"
            }
            
            logger.info(
                "live_stream_started",
                stream_id=stream_id,
                protocol=protocol.value,
                quality=quality.value
            )
            
            return {
                "stream_id": stream_id,
                "status": "active",
                "output_url": output_url,
                "protocol": protocol.value,
                "quality": quality.value,
                "start_time": self.active_streams[stream_id]["start_time"].isoformat(),
                "dvr_enabled": dvr_mode != DVRMode.DISABLED,
                "dvr_path": dvr_path
            }
            
        except Exception as e:
            logger.error(f"Failed to start live stream: {str(e)}")
            raise ProxyGenerationError(f"Live stream start failed: {str(e)}")
    
    async def stop_live_stream(self, stream_id: str) -> Dict[str, Any]:
        """Stop an active live stream"""
        if stream_id not in self.active_streams:
            raise ProxyGenerationError(f"Stream {stream_id} not found")
        
        stream_info = self.active_streams[stream_id]
        process = stream_info["process"]
        
        try:
            # Gracefully terminate the process
            process.terminate()
            await asyncio.wait_for(process.wait(), timeout=10.0)
        except asyncio.TimeoutError:
            # Force kill if graceful termination fails
            process.kill()
            await process.wait()
        
        # Calculate stream duration
        duration = (datetime.utcnow() - stream_info["start_time"]).total_seconds()
        
        # Update stream status
        stream_info["status"] = "stopped"
        stream_info["stop_time"] = datetime.utcnow()
        stream_info["duration"] = duration
        
        # Clean up from active streams
        del self.active_streams[stream_id]
        
        logger.info(
            "live_stream_stopped",
            stream_id=stream_id,
            duration=duration
        )
        
        return {
            "stream_id": stream_id,
            "status": "stopped",
            "duration": duration,
            "dvr_path": stream_info.get("dvr_path")
        }
    
    async def get_stream_status(self, stream_id: str) -> Dict[str, Any]:
        """Get status of a live stream"""
        if stream_id not in self.active_streams:
            return {"stream_id": stream_id, "status": "not_found"}
        
        stream_info = self.active_streams[stream_id]
        process = stream_info["process"]
        
        # Check if process is still running
        if process.returncode is not None:
            stream_info["status"] = "error"
            stream_info["error_code"] = process.returncode
        
        duration = (datetime.utcnow() - stream_info["start_time"]).total_seconds()
        
        return {
            "stream_id": stream_id,
            "status": stream_info["status"],
            "duration": duration,
            "input_source": stream_info["input_source"],
            "output_url": stream_info["output_url"],
            "protocol": stream_info["protocol"],
            "quality": stream_info["quality"],
            "start_time": stream_info["start_time"].isoformat()
        }
    
    async def create_adaptive_stream(
        self,
        input_source: str,
        output_base_path: str,
        protocol: StreamingProtocol = StreamingProtocol.HLS,
        codec: StreamCodec = StreamCodec.H264,
        audio_codec: StreamAudioCodec = StreamAudioCodec.AAC,
        ladder: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Create an adaptive bitrate stream with multiple quality levels
        
        Args:
            input_source: Input stream URL or device
            output_base_path: Base path for output files
            protocol: Streaming protocol (HLS or DASH)
            codec: Video codec
            audio_codec: Audio codec
            ladder: Custom ABR ladder (uses default if not provided)
        
        Returns:
            Stream information including master playlist URL
        """
        if protocol not in [StreamingProtocol.HLS, StreamingProtocol.DASH]:
            raise ProxyGenerationError("Adaptive streaming only supports HLS and DASH")
        
        stream_id = str(uuid.uuid4())
        ladder = ladder or self.abr_ladder
        
        # Create output directory
        output_dir = Path(output_base_path) / stream_id
        output_dir.mkdir(parents=True, exist_ok=True)
        
        if protocol == StreamingProtocol.HLS:
            cmd = await self._build_adaptive_hls_command(
                input_source, str(output_dir), codec, audio_codec, ladder
            )
            master_playlist = str(output_dir / "master.m3u8")
        else:  # DASH
            cmd = await self._build_adaptive_dash_command(
                input_source, str(output_dir), codec, audio_codec, ladder
            )
            master_playlist = str(output_dir / "manifest.mpd")
        
        # Start the adaptive streaming process
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # Track the stream
        self.active_streams[stream_id] = {
            "process": process,
            "start_time": datetime.utcnow(),
            "input_source": input_source,
            "output_dir": str(output_dir),
            "master_playlist": master_playlist,
            "protocol": protocol.value,
            "type": "adaptive",
            "ladder": ladder,
            "status": "active"
        }
        
        logger.info(
            "adaptive_stream_started",
            stream_id=stream_id,
            protocol=protocol.value,
            qualities=[q["name"] for q in ladder]
        )
        
        return {
            "stream_id": stream_id,
            "status": "active",
            "master_playlist": master_playlist,
            "protocol": protocol.value,
            "type": "adaptive",
            "qualities": [q["name"] for q in ladder],
            "start_time": self.active_streams[stream_id]["start_time"].isoformat()
        }
    
    async def add_stream_overlay(
        self,
        stream_id: str,
        overlay_type: str,
        overlay_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Add overlay to an active stream (logo, text, graphics)
        
        Args:
            stream_id: ID of the active stream
            overlay_type: Type of overlay (logo, text, lower_third, etc.)
            overlay_data: Overlay configuration data
        
        Returns:
            Updated stream information
        """
        if stream_id not in self.active_streams:
            raise ProxyGenerationError(f"Stream {stream_id} not found")
        
        # This would typically involve modifying the FFmpeg filter graph
        # For now, we'll store the overlay configuration
        if "overlays" not in self.active_streams[stream_id]:
            self.active_streams[stream_id]["overlays"] = []
        
        overlay = {
            "type": overlay_type,
            "data": overlay_data,
            "added_at": datetime.utcnow().isoformat()
        }
        
        self.active_streams[stream_id]["overlays"].append(overlay)
        
        logger.info(
            "stream_overlay_added",
            stream_id=stream_id,
            overlay_type=overlay_type
        )
        
        return {
            "stream_id": stream_id,
            "overlay_added": True,
            "overlay_type": overlay_type,
            "total_overlays": len(self.active_streams[stream_id]["overlays"])
        }
    
    async def create_stream_recording(
        self,
        stream_id: str,
        output_path: str,
        duration: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Create a recording from an active stream
        
        Args:
            stream_id: ID of the active stream
            output_path: Path to save the recording
            duration: Recording duration in seconds (None for continuous)
        
        Returns:
            Recording information
        """
        if stream_id not in self.active_streams:
            raise ProxyGenerationError(f"Stream {stream_id} not found")
        
        stream_info = self.active_streams[stream_id]
        input_source = stream_info["output_url"]
        
        # Build recording command
        cmd = [
            self.ffmpeg_path,
            "-i", input_source,
            "-c", "copy"  # Copy without re-encoding
        ]
        
        if duration:
            cmd.extend(["-t", str(duration)])
        
        cmd.append(output_path)
        
        # Start recording process
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        recording_id = str(uuid.uuid4())
        
        # Track the recording
        if "recordings" not in stream_info:
            stream_info["recordings"] = {}
        
        stream_info["recordings"][recording_id] = {
            "process": process,
            "output_path": output_path,
            "start_time": datetime.utcnow(),
            "duration": duration,
            "status": "recording"
        }
        
        logger.info(
            "stream_recording_started",
            stream_id=stream_id,
            recording_id=recording_id,
            duration=duration
        )
        
        return {
            "stream_id": stream_id,
            "recording_id": recording_id,
            "status": "recording",
            "output_path": output_path,
            "duration": duration
        }
    
    async def get_stream_statistics(self, stream_id: str) -> Dict[str, Any]:
        """Get real-time statistics for an active stream"""
        if stream_id not in self.active_streams:
            raise ProxyGenerationError(f"Stream {stream_id} not found")
        
        stream_info = self.active_streams[stream_id]
        
        # In a real implementation, this would parse FFmpeg's stderr output
        # or use a monitoring solution to get real-time stats
        duration = (datetime.utcnow() - stream_info["start_time"]).total_seconds()
        
        stats = {
            "stream_id": stream_id,
            "duration": duration,
            "status": stream_info["status"],
            "input": {
                "source": stream_info["input_source"],
                "codec": "unknown",  # Would be parsed from stream
                "bitrate": 0,
                "fps": 0
            },
            "output": {
                "url": stream_info.get("output_url"),
                "codec": stream_info["codec"],
                "quality": stream_info["quality"],
                "bitrate": 0,  # Would be calculated
                "fps": 30  # Based on quality preset
            },
            "network": {
                "bytes_sent": 0,  # Would be tracked
                "dropped_frames": 0,
                "latency_ms": 0
            },
            "viewers": {
                "current": 0,  # Would require viewer tracking
                "peak": 0,
                "total": 0
            }
        }
        
        return stats
    
    async def _build_hls_command(
        self,
        input_source: str,
        output_url: str,
        quality: StreamQuality,
        codec: StreamCodec,
        audio_codec: StreamAudioCodec,
        latency: StreamLatency,
        custom_params: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """Build FFmpeg command for HLS streaming"""
        preset = self.quality_presets[quality]
        
        cmd = [
            self.ffmpeg_path,
            "-re",  # Read input at native frame rate
            "-i", input_source
        ]
        
        # Video encoding
        if codec == StreamCodec.H264:
            cmd.extend([
                "-c:v", "libx264",
                "-preset", "veryfast" if latency == StreamLatency.ULTRA_LOW else "medium",
                "-tune", "zerolatency" if latency in [StreamLatency.ULTRA_LOW, StreamLatency.LOW] else "film"
            ])
        elif codec == StreamCodec.H265:
            cmd.extend(["-c:v", "libx265", "-preset", "fast"])
        
        # Video parameters
        cmd.extend([
            "-s", preset["resolution"],
            "-b:v", preset["video_bitrate"],
            "-r", str(preset["framerate"]),
            "-g", str(preset["framerate"] * 2),  # GOP size
            "-keyint_min", str(preset["framerate"])
        ])
        
        # Audio encoding
        if audio_codec == StreamAudioCodec.AAC:
            cmd.extend(["-c:a", "aac", "-b:a", preset["audio_bitrate"]])
        elif audio_codec == StreamAudioCodec.OPUS:
            cmd.extend(["-c:a", "libopus", "-b:a", preset["audio_bitrate"]])
        
        # HLS specific parameters
        hls_time = 2 if latency == StreamLatency.ULTRA_LOW else 6
        cmd.extend([
            "-f", "hls",
            "-hls_time", str(hls_time),
            "-hls_list_size", "10",
            "-hls_flags", "delete_segments+append_list",
            "-hls_segment_type", "mpegts"
        ])
        
        # Low latency HLS
        if latency in [StreamLatency.ULTRA_LOW, StreamLatency.LOW]:
            cmd.extend([
                "-hls_flags", "delete_segments+append_list+program_date_time+independent_segments",
                "-hls_segment_type", "fmp4",
                "-hls_fmp4_init_filename", "init.mp4"
            ])
        
        # Apply custom parameters
        if custom_params:
            for key, value in custom_params.items():
                cmd.extend([f"-{key}", str(value)])
        
        cmd.append(output_url)
        
        return cmd
    
    async def _build_dash_command(
        self,
        input_source: str,
        output_url: str,
        quality: StreamQuality,
        codec: StreamCodec,
        audio_codec: StreamAudioCodec,
        latency: StreamLatency,
        custom_params: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """Build FFmpeg command for DASH streaming"""
        preset = self.quality_presets[quality]
        
        cmd = [
            self.ffmpeg_path,
            "-re",
            "-i", input_source
        ]
        
        # Video encoding (similar to HLS)
        if codec == StreamCodec.H264:
            cmd.extend([
                "-c:v", "libx264",
                "-preset", "veryfast" if latency == StreamLatency.ULTRA_LOW else "medium"
            ])
        
        cmd.extend([
            "-s", preset["resolution"],
            "-b:v", preset["video_bitrate"],
            "-r", str(preset["framerate"])
        ])
        
        # Audio encoding
        if audio_codec == StreamAudioCodec.AAC:
            cmd.extend(["-c:a", "aac", "-b:a", preset["audio_bitrate"]])
        
        # DASH specific parameters
        segment_duration = 2 if latency == StreamLatency.ULTRA_LOW else 4
        cmd.extend([
            "-f", "dash",
            "-seg_duration", str(segment_duration),
            "-window_size", "5",
            "-use_template", "1",
            "-use_timeline", "1"
        ])
        
        # Low latency DASH
        if latency in [StreamLatency.ULTRA_LOW, StreamLatency.LOW]:
            cmd.extend([
                "-ldash", "1",
                "-streaming", "1",
                "-adaptation_sets", "id=0,streams=v id=1,streams=a"
            ])
        
        if custom_params:
            for key, value in custom_params.items():
                cmd.extend([f"-{key}", str(value)])
        
        cmd.append(output_url)
        
        return cmd
    
    async def _build_rtmp_command(
        self,
        input_source: str,
        output_url: str,
        quality: StreamQuality,
        codec: StreamCodec,
        audio_codec: StreamAudioCodec,
        custom_params: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """Build FFmpeg command for RTMP streaming"""
        preset = self.quality_presets[quality]
        
        cmd = [
            self.ffmpeg_path,
            "-re",
            "-i", input_source,
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-tune", "zerolatency",
            "-s", preset["resolution"],
            "-b:v", preset["video_bitrate"],
            "-r", str(preset["framerate"]),
            "-g", str(preset["framerate"] * 2),
            "-keyint_min", str(preset["framerate"]),
            "-c:a", "aac",
            "-b:a", preset["audio_bitrate"],
            "-ar", "44100",
            "-f", "flv"
        ]
        
        if custom_params:
            for key, value in custom_params.items():
                cmd.extend([f"-{key}", str(value)])
        
        cmd.append(output_url)
        
        return cmd
    
    async def _build_srt_command(
        self,
        input_source: str,
        output_url: str,
        quality: StreamQuality,
        codec: StreamCodec,
        audio_codec: StreamAudioCodec,
        latency: StreamLatency,
        custom_params: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """Build FFmpeg command for SRT streaming"""
        preset = self.quality_presets[quality]
        
        cmd = [
            self.ffmpeg_path,
            "-re",
            "-i", input_source
        ]
        
        # Video encoding
        if codec == StreamCodec.H264:
            cmd.extend([
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-tune", "zerolatency"
            ])
        
        cmd.extend([
            "-s", preset["resolution"],
            "-b:v", preset["video_bitrate"],
            "-r", str(preset["framerate"]),
            "-g", str(preset["framerate"])
        ])
        
        # Audio encoding
        if audio_codec == StreamAudioCodec.AAC:
            cmd.extend(["-c:a", "aac", "-b:a", preset["audio_bitrate"]])
        
        # SRT specific parameters
        latency_ms = {
            StreamLatency.ULTRA_LOW: 20,
            StreamLatency.LOW: 120,
            StreamLatency.STANDARD: 1000,
            StreamLatency.HIGH: 2000
        }.get(latency, 120)
        
        # Format output URL with SRT parameters
        srt_params = f"?mode=caller&latency={latency_ms}"
        if "?" in output_url:
            output_url += f"&latency={latency_ms}"
        else:
            output_url += srt_params
        
        cmd.extend(["-f", "mpegts"])
        
        if custom_params:
            for key, value in custom_params.items():
                cmd.extend([f"-{key}", str(value)])
        
        cmd.append(output_url)
        
        return cmd
    
    async def _build_rtsp_command(
        self,
        input_source: str,
        output_url: str,
        quality: StreamQuality,
        codec: StreamCodec,
        audio_codec: StreamAudioCodec,
        custom_params: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """Build FFmpeg command for RTSP streaming"""
        preset = self.quality_presets[quality]
        
        cmd = [
            self.ffmpeg_path,
            "-re",
            "-i", input_source,
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-tune", "zerolatency",
            "-s", preset["resolution"],
            "-b:v", preset["video_bitrate"],
            "-r", str(preset["framerate"]),
            "-c:a", "aac",
            "-b:a", preset["audio_bitrate"],
            "-rtsp_transport", "tcp",
            "-f", "rtsp"
        ]
        
        if custom_params:
            for key, value in custom_params.items():
                cmd.extend([f"-{key}", str(value)])
        
        cmd.append(output_url)
        
        return cmd
    
    async def _build_adaptive_hls_command(
        self,
        input_source: str,
        output_dir: str,
        codec: StreamCodec,
        audio_codec: StreamAudioCodec,
        ladder: List[Dict[str, Any]]
    ) -> List[str]:
        """Build FFmpeg command for adaptive HLS streaming"""
        cmd = [
            self.ffmpeg_path,
            "-re",
            "-i", input_source
        ]
        
        # Build filter complex for multiple outputs
        filter_complex = []
        map_commands = []
        var_stream_map = []
        
        for i, quality in enumerate(ladder):
            # Scale filter for each quality
            filter_complex.append(f"[0:v]scale={quality['resolution']}[v{i}]")
            
            # Map video stream
            map_commands.extend(["-map", f"[v{i}]", "-map", "0:a"])
            
            # Video encoding parameters for this quality
            cmd.extend([
                f"-c:v:{i}", "libx264" if codec == StreamCodec.H264 else "libx265",
                f"-b:v:{i}", quality['bitrate'],
                f"-r:v:{i}", str(quality['framerate']),
                f"-g:{i}", str(quality['framerate'] * 2),
                f"-preset:v:{i}", "veryfast"
            ])
            
            # Audio encoding (same for all qualities)
            cmd.extend([
                f"-c:a:{i}", "aac" if audio_codec == StreamAudioCodec.AAC else "libopus",
                f"-b:a:{i}", "128k"
            ])
            
            # Add to variant stream map
            var_stream_map.append(f"v:{i},a:{i},name:{quality['name']}")
        
        # Add filter complex
        cmd.extend(["-filter_complex", ";".join(filter_complex)])
        
        # Add all map commands
        cmd.extend(map_commands)
        
        # HLS parameters
        cmd.extend([
            "-f", "hls",
            "-hls_time", "6",
            "-hls_list_size", "10",
            "-hls_flags", "delete_segments+independent_segments",
            "-hls_segment_type", "mpegts",
            "-master_pl_name", "master.m3u8",
            "-var_stream_map", " ".join(var_stream_map),
            f"{output_dir}/stream_%v.m3u8"
        ])
        
        return cmd
    
    async def _build_adaptive_dash_command(
        self,
        input_source: str,
        output_dir: str,
        codec: StreamCodec,
        audio_codec: StreamAudioCodec,
        ladder: List[Dict[str, Any]]
    ) -> List[str]:
        """Build FFmpeg command for adaptive DASH streaming"""
        cmd = [
            self.ffmpeg_path,
            "-re",
            "-i", input_source
        ]
        
        # Build filter complex for multiple outputs
        filter_complex = []
        map_commands = []
        
        for i, quality in enumerate(ladder):
            # Scale filter for each quality
            filter_complex.append(f"[0:v]scale={quality['resolution']}[v{i}]")
            
            # Map video stream
            map_commands.extend(["-map", f"[v{i}]"])
            
            # Video encoding parameters for this quality
            cmd.extend([
                f"-c:v:{i}", "libx264" if codec == StreamCodec.H264 else "libx265",
                f"-b:v:{i}", quality['bitrate'],
                f"-r:v:{i}", str(quality['framerate']),
                f"-g:{i}", str(quality['framerate'] * 2),
                f"-preset:v:{i}", "veryfast"
            ])
        
        # Add audio mapping and encoding
        map_commands.extend(["-map", "0:a"])
        cmd.extend([
            "-c:a", "aac" if audio_codec == StreamAudioCodec.AAC else "libopus",
            "-b:a", "128k"
        ])
        
        # Add filter complex
        cmd.extend(["-filter_complex", ";".join(filter_complex)])
        
        # Add all map commands
        cmd.extend(map_commands)
        
        # DASH parameters
        cmd.extend([
            "-f", "dash",
            "-seg_duration", "4",
            "-window_size", "5",
            "-use_template", "1",
            "-use_timeline", "1",
            "-adaptation_sets", f"id=0,streams=0-{len(ladder)-1} id=1,streams=a",
            f"{output_dir}/manifest.mpd"
        ])
        
        return cmd
    
    async def _setup_dvr(
        self,
        stream_id: str,
        input_source: str,
        dvr_mode: DVRMode
    ) -> str:
        """Set up DVR recording for a stream"""
        dvr_dir = Path(tempfile.gettempdir()) / "mams_dvr" / stream_id
        dvr_dir.mkdir(parents=True, exist_ok=True)
        
        if dvr_mode == DVRMode.SLIDING_WINDOW:
            # Record in segments, keep last N minutes
            dvr_path = str(dvr_dir / "dvr_%03d.ts")
            # Additional logic would manage segment cleanup
        elif dvr_mode == DVRMode.FULL_RECORDING:
            # Record entire stream
            dvr_path = str(dvr_dir / "recording.mp4")
        else:
            # Event-based recording
            dvr_path = str(dvr_dir / "events")
            Path(dvr_path).mkdir(exist_ok=True)
        
        return dvr_path
    
    def get_streaming_capabilities(self) -> Dict[str, Any]:
        """Get supported streaming capabilities"""
        return {
            "protocols": [p.value for p in StreamingProtocol],
            "qualities": [q.value for q in StreamQuality],
            "video_codecs": [c.value for c in StreamCodec],
            "audio_codecs": [c.value for c in StreamAudioCodec],
            "latency_modes": [l.value for l in StreamLatency],
            "dvr_modes": [d.value for d in DVRMode],
            "features": {
                "adaptive_bitrate": True,
                "live_recording": True,
                "overlays": True,
                "statistics": True,
                "multi_protocol": True,
                "low_latency": True,
                "dvr": True
            },
            "quality_presets": {
                k.value: v for k, v in self.quality_presets.items()
            },
            "abr_ladder": self.abr_ladder
        }