"""
Streaming Protocol Service for HLS, SRT, and other streaming formats
"""

import os
import asyncio
import shutil
from typing import Dict, Optional, List, Union
from pathlib import Path
from datetime import datetime, timedelta
import aiofiles
import structlog
import m3u8
from urllib.parse import urlparse, urljoin

from ..models.schemas import IngestJob, IngestStatus
from ..core.exceptions import StreamingProtocolError
from ..core.config import settings
from ..core.logging import get_logger

logger = get_logger(__name__)


class StreamingProtocolService:
    """Service for handling various streaming protocols"""
    
    def __init__(self):
        self.supported_protocols = {
            'hls': HLSHandler(),
            'srt': SRTHandler(),
            'dash': DASHHandler(),
            'rtmp': RTMPHandler(),
            'rtsp': RTSPHandler()
        }
        
        # Configuration
        self.segment_duration = 10  # seconds
        self.playlist_size = 5  # number of segments in playlist
        self.buffer_size = 1024 * 1024  # 1MB
        self.timeout = 30  # seconds
        
    async def ingest_stream(
        self,
        stream_url: str,
        destination_path: str,
        protocol: Optional[str] = None,
        options: Optional[Dict] = None
    ) -> Dict:
        """Ingest a stream using the appropriate protocol handler"""
        try:
            # Detect protocol if not specified
            if not protocol:
                protocol = self._detect_protocol(stream_url)
            
            if protocol not in self.supported_protocols:
                raise StreamingProtocolError(
                    f"Unsupported protocol: {protocol}",
                    error_code="UNSUPPORTED_PROTOCOL"
                )
            
            handler = self.supported_protocols[protocol]
            
            logger.info(
                "starting_stream_ingest",
                stream_url=stream_url,
                protocol=protocol,
                destination_path=destination_path
            )
            
            # Start ingestion
            result = await handler.ingest(
                stream_url=stream_url,
                destination_path=destination_path,
                options=options or {}
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "stream_ingest_failed",
                error=str(e),
                stream_url=stream_url,
                protocol=protocol
            )
            raise StreamingProtocolError(
                f"Stream ingest failed: {str(e)}",
                error_code="STREAM_INGEST_FAILED"
            )
    
    async def convert_stream_format(
        self,
        source_path: str,
        output_format: str,
        options: Optional[Dict] = None
    ) -> str:
        """Convert between streaming formats"""
        try:
            if output_format not in self.supported_protocols:
                raise StreamingProtocolError(
                    f"Unsupported output format: {output_format}",
                    error_code="UNSUPPORTED_FORMAT"
                )
            
            handler = self.supported_protocols[output_format]
            
            output_path = await handler.convert(
                source_path=source_path,
                options=options or {}
            )
            
            logger.info(
                "stream_format_converted",
                source_path=source_path,
                output_format=output_format,
                output_path=output_path
            )
            
            return output_path
            
        except Exception as e:
            logger.error(
                "stream_conversion_failed",
                error=str(e),
                source_path=source_path,
                output_format=output_format
            )
            raise
    
    def _detect_protocol(self, stream_url: str) -> str:
        """Detect streaming protocol from URL"""
        parsed = urlparse(stream_url)
        
        # Check URL scheme
        if parsed.scheme in ['rtmp', 'rtmps']:
            return 'rtmp'
        elif parsed.scheme in ['rtsp', 'rtsps']:
            return 'rtsp'
        elif parsed.scheme == 'srt':
            return 'srt'
        
        # Check file extension
        if stream_url.endswith('.m3u8'):
            return 'hls'
        elif stream_url.endswith('.mpd'):
            return 'dash'
        
        # Default to HLS for HTTP(S) URLs
        if parsed.scheme in ['http', 'https']:
            return 'hls'
        
        raise StreamingProtocolError(
            f"Cannot detect protocol from URL: {stream_url}",
            error_code="PROTOCOL_DETECTION_FAILED"
        )


class HLSHandler:
    """Handler for HTTP Live Streaming (HLS) protocol"""
    
    async def ingest(
        self,
        stream_url: str,
        destination_path: str,
        options: Dict
    ) -> Dict:
        """Ingest HLS stream"""
        try:
            # Create destination directory
            dest_dir = Path(destination_path).parent
            dest_dir.mkdir(parents=True, exist_ok=True)
            
            # Parse playlist
            playlist = m3u8.load(stream_url)
            
            if playlist.is_variant:
                # Handle master playlist
                return await self._ingest_variant_playlist(
                    playlist=playlist,
                    stream_url=stream_url,
                    destination_path=destination_path,
                    options=options
                )
            else:
                # Handle media playlist
                return await self._ingest_media_playlist(
                    playlist=playlist,
                    stream_url=stream_url,
                    destination_path=destination_path,
                    options=options
                )
                
        except Exception as e:
            logger.error(
                "hls_ingest_failed",
                error=str(e),
                stream_url=stream_url
            )
            raise StreamingProtocolError(
                f"HLS ingest failed: {str(e)}",
                error_code="HLS_INGEST_FAILED"
            )
    
    async def _ingest_variant_playlist(
        self,
        playlist: m3u8.M3U8,
        stream_url: str,
        destination_path: str,
        options: Dict
    ) -> Dict:
        """Handle variant (master) playlist"""
        # Select best quality variant
        best_variant = max(
            playlist.playlists,
            key=lambda x: x.stream_info.bandwidth if x.stream_info else 0
        )
        
        # Build absolute URL for variant
        variant_url = urljoin(stream_url, best_variant.uri)
        
        logger.info(
            "selected_hls_variant",
            variant_url=variant_url,
            bandwidth=best_variant.stream_info.bandwidth if best_variant.stream_info else None
        )
        
        # Load and ingest the selected variant
        variant_playlist = m3u8.load(variant_url)
        
        return await self._ingest_media_playlist(
            playlist=variant_playlist,
            stream_url=variant_url,
            destination_path=destination_path,
            options=options
        )
    
    async def _ingest_media_playlist(
        self,
        playlist: m3u8.M3U8,
        stream_url: str,
        destination_path: str,
        options: Dict
    ) -> Dict:
        """Handle media playlist with segments"""
        segments_dir = Path(destination_path).parent / "segments"
        segments_dir.mkdir(parents=True, exist_ok=True)
        
        downloaded_segments = []
        total_duration = 0
        
        for segment in playlist.segments:
            # Build absolute URL for segment
            segment_url = urljoin(stream_url, segment.uri)
            
            # Download segment
            segment_path = segments_dir / Path(segment.uri).name
            
            success = await self._download_segment(
                segment_url=segment_url,
                destination=str(segment_path)
            )
            
            if success:
                downloaded_segments.append({
                    'path': str(segment_path),
                    'duration': segment.duration,
                    'url': segment_url
                })
                total_duration += segment.duration
        
        # Concatenate segments if requested
        if options.get('concatenate', True):
            await self._concatenate_segments(
                segments=downloaded_segments,
                output_path=destination_path
            )
        
        return {
            'protocol': 'hls',
            'segments_count': len(downloaded_segments),
            'total_duration': total_duration,
            'output_path': destination_path,
            'segments': downloaded_segments
        }
    
    async def _download_segment(self, segment_url: str, destination: str) -> bool:
        """Download a single segment"""
        try:
            import httpx
            
            async with httpx.AsyncClient() as client:
                response = await client.get(segment_url, timeout=30.0)
                response.raise_for_status()
                
                async with aiofiles.open(destination, 'wb') as f:
                    await f.write(response.content)
                
                return True
                
        except Exception as e:
            logger.error(
                "segment_download_failed",
                error=str(e),
                segment_url=segment_url
            )
            return False
    
    async def _concatenate_segments(
        self,
        segments: List[Dict],
        output_path: str
    ):
        """Concatenate segments into a single file"""
        try:
            # Create concat file for FFmpeg
            concat_file = Path(output_path).parent / "concat.txt"
            
            async with aiofiles.open(concat_file, 'w') as f:
                for segment in segments:
                    await f.write(f"file '{segment['path']}'\n")
            
            # Use FFmpeg to concatenate
            import subprocess
            
            cmd = [
                'ffmpeg',
                '-f', 'concat',
                '-safe', '0',
                '-i', str(concat_file),
                '-c', 'copy',
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
                raise StreamingProtocolError(
                    f"FFmpeg concatenation failed: {stderr.decode()}",
                    error_code="CONCAT_FAILED"
                )
            
            # Clean up
            concat_file.unlink()
            
        except Exception as e:
            logger.error(
                "segment_concatenation_failed",
                error=str(e),
                output_path=output_path
            )
            raise
    
    async def convert(self, source_path: str, options: Dict) -> str:
        """Convert video to HLS format"""
        try:
            output_dir = Path(source_path).parent / "hls_output"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            playlist_path = output_dir / "playlist.m3u8"
            
            # FFmpeg command for HLS conversion
            cmd = [
                'ffmpeg',
                '-i', source_path,
                '-c:v', options.get('video_codec', 'libx264'),
                '-c:a', options.get('audio_codec', 'aac'),
                '-hls_time', str(options.get('segment_duration', 10)),
                '-hls_playlist_type', options.get('playlist_type', 'vod'),
                '-hls_segment_filename', str(output_dir / 'segment_%03d.ts'),
                '-y',
                str(playlist_path)
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise StreamingProtocolError(
                    f"HLS conversion failed: {stderr.decode()}",
                    error_code="HLS_CONVERSION_FAILED"
                )
            
            return str(playlist_path)
            
        except Exception as e:
            logger.error(
                "hls_conversion_failed",
                error=str(e),
                source_path=source_path
            )
            raise


class SRTHandler:
    """Handler for Secure Reliable Transport (SRT) protocol"""
    
    async def ingest(
        self,
        stream_url: str,
        destination_path: str,
        options: Dict
    ) -> Dict:
        """Ingest SRT stream"""
        try:
            # FFmpeg command for SRT ingestion
            cmd = [
                'ffmpeg',
                '-i', stream_url,
                '-c', 'copy',
                '-f', 'mp4',
                '-movflags', 'frag_keyframe+empty_moov',
                '-y',
                destination_path
            ]
            
            # Add SRT-specific options
            if 'latency' in options:
                cmd.extend(['-latency', str(options['latency'])])
            
            if 'passphrase' in options:
                cmd.extend(['-passphrase', options['passphrase']])
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Monitor the process
            start_time = datetime.utcnow()
            
            # Wait for process with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=options.get('timeout', 3600)  # 1 hour default
                )
            except asyncio.TimeoutError:
                process.terminate()
                await process.wait()
                
                duration = (datetime.utcnow() - start_time).total_seconds()
                
                return {
                    'protocol': 'srt',
                    'status': 'timeout',
                    'duration': duration,
                    'output_path': destination_path
                }
            
            if process.returncode != 0:
                raise StreamingProtocolError(
                    f"SRT ingest failed: {stderr.decode()}",
                    error_code="SRT_INGEST_FAILED"
                )
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            return {
                'protocol': 'srt',
                'status': 'completed',
                'duration': duration,
                'output_path': destination_path
            }
            
        except Exception as e:
            logger.error(
                "srt_ingest_failed",
                error=str(e),
                stream_url=stream_url
            )
            raise
    
    async def convert(self, source_path: str, options: Dict) -> str:
        """Convert to SRT streaming format"""
        # SRT is typically used for live streaming, not file conversion
        raise StreamingProtocolError(
            "SRT is for live streaming only",
            error_code="SRT_CONVERSION_NOT_SUPPORTED"
        )


class DASHHandler:
    """Handler for Dynamic Adaptive Streaming over HTTP (DASH)"""
    
    async def ingest(
        self,
        stream_url: str,
        destination_path: str,
        options: Dict
    ) -> Dict:
        """Ingest DASH stream"""
        try:
            # For DASH, we would parse the MPD manifest
            # This is a simplified implementation
            cmd = [
                'ffmpeg',
                '-i', stream_url,
                '-c', 'copy',
                '-y',
                destination_path
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise StreamingProtocolError(
                    f"DASH ingest failed: {stderr.decode()}",
                    error_code="DASH_INGEST_FAILED"
                )
            
            return {
                'protocol': 'dash',
                'status': 'completed',
                'output_path': destination_path
            }
            
        except Exception as e:
            logger.error(
                "dash_ingest_failed",
                error=str(e),
                stream_url=stream_url
            )
            raise
    
    async def convert(self, source_path: str, options: Dict) -> str:
        """Convert video to DASH format"""
        try:
            output_dir = Path(source_path).parent / "dash_output"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            manifest_path = output_dir / "manifest.mpd"
            
            # FFmpeg command for DASH conversion
            cmd = [
                'ffmpeg',
                '-i', source_path,
                '-c:v', options.get('video_codec', 'libx264'),
                '-c:a', options.get('audio_codec', 'aac'),
                '-seg_duration', str(options.get('segment_duration', 10)),
                '-use_template', '1',
                '-use_timeline', '1',
                '-f', 'dash',
                '-y',
                str(manifest_path)
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise StreamingProtocolError(
                    f"DASH conversion failed: {stderr.decode()}",
                    error_code="DASH_CONVERSION_FAILED"
                )
            
            return str(manifest_path)
            
        except Exception as e:
            logger.error(
                "dash_conversion_failed",
                error=str(e),
                source_path=source_path
            )
            raise


class RTMPHandler:
    """Handler for Real-Time Messaging Protocol (RTMP)"""
    
    async def ingest(
        self,
        stream_url: str,
        destination_path: str,
        options: Dict
    ) -> Dict:
        """Ingest RTMP stream"""
        try:
            # FFmpeg command for RTMP ingestion
            cmd = [
                'ffmpeg',
                '-i', stream_url,
                '-c', 'copy',
                '-f', 'flv',
                '-y',
                destination_path
            ]
            
            # Add authentication if provided
            if 'username' in options and 'password' in options:
                auth_url = stream_url.replace(
                    'rtmp://',
                    f"rtmp://{options['username']}:{options['password']}@"
                )
                cmd[2] = auth_url
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # For live streams, we might want to run this in background
            if options.get('live', False):
                return {
                    'protocol': 'rtmp',
                    'status': 'streaming',
                    'process_id': process.pid,
                    'output_path': destination_path
                }
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise StreamingProtocolError(
                    f"RTMP ingest failed: {stderr.decode()}",
                    error_code="RTMP_INGEST_FAILED"
                )
            
            return {
                'protocol': 'rtmp',
                'status': 'completed',
                'output_path': destination_path
            }
            
        except Exception as e:
            logger.error(
                "rtmp_ingest_failed",
                error=str(e),
                stream_url=stream_url
            )
            raise
    
    async def convert(self, source_path: str, options: Dict) -> str:
        """RTMP is for streaming, not conversion"""
        raise StreamingProtocolError(
            "RTMP is for live streaming only",
            error_code="RTMP_CONVERSION_NOT_SUPPORTED"
        )


class RTSPHandler:
    """Handler for Real Time Streaming Protocol (RTSP)"""
    
    async def ingest(
        self,
        stream_url: str,
        destination_path: str,
        options: Dict
    ) -> Dict:
        """Ingest RTSP stream"""
        try:
            # FFmpeg command for RTSP ingestion
            cmd = [
                'ffmpeg',
                '-rtsp_transport', options.get('transport', 'tcp'),
                '-i', stream_url,
                '-c', 'copy',
                '-f', 'mp4',
                '-y',
                destination_path
            ]
            
            # Add authentication if provided
            if 'username' in options and 'password' in options:
                auth_url = stream_url.replace(
                    'rtsp://',
                    f"rtsp://{options['username']}:{options['password']}@"
                )
                cmd[4] = auth_url
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # For security cameras, might want continuous recording
            if options.get('continuous', False):
                return {
                    'protocol': 'rtsp',
                    'status': 'recording',
                    'process_id': process.pid,
                    'output_path': destination_path
                }
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise StreamingProtocolError(
                    f"RTSP ingest failed: {stderr.decode()}",
                    error_code="RTSP_INGEST_FAILED"
                )
            
            return {
                'protocol': 'rtsp',
                'status': 'completed',
                'output_path': destination_path
            }
            
        except Exception as e:
            logger.error(
                "rtsp_ingest_failed",
                error=str(e),
                stream_url=stream_url
            )
            raise
    
    async def convert(self, source_path: str, options: Dict) -> str:
        """RTSP is for streaming, not conversion"""
        raise StreamingProtocolError(
            "RTSP is for live streaming only",
            error_code="RTSP_CONVERSION_NOT_SUPPORTED"
        )


# Dependency injection
_streaming_protocol_service: Optional[StreamingProtocolService] = None


async def get_streaming_protocol_service() -> StreamingProtocolService:
    """Get streaming protocol service instance"""
    global _streaming_protocol_service
    
    if _streaming_protocol_service is None:
        _streaming_protocol_service = StreamingProtocolService()
    
    return _streaming_protocol_service