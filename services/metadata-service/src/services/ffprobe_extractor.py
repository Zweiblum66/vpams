"""
FFprobe Video Metadata Extractor

This module provides functionality for extracting metadata from video files using FFprobe.
"""

import os
import json
import asyncio
import subprocess
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime, timedelta
import structlog
import ffmpeg

from ..core.exceptions import ExtractionError

logger = structlog.get_logger()


class FFprobeExtractor:
    """Extracts metadata from video/audio files using FFprobe"""
    
    def __init__(self, ffprobe_path: str = "ffprobe"):
        self.ffprobe_path = ffprobe_path
        self.supported_formats = {
            # Video formats
            'MP4', 'AVI', 'MOV', 'MKV', 'WMV', 'FLV', 'WEBM', 'M4V', 'MPG', 'MPEG',
            'VOB', 'OGV', 'ASF', 'RM', 'RMVB', 'F4V', 'SWF', 'MTS', 'M2TS', 'TS',
            # Audio formats
            'MP3', 'AAC', 'WAV', 'FLAC', 'OGG', 'WMA', 'M4A', 'AIFF', 'AU', 'AC3',
            'DTS', 'OPUS', 'AMR', 'APE', 'MKA'
        }
        
        # Common metadata field mappings
        self.metadata_mapping = {
            'title': 'title',
            'artist': 'artist',
            'album': 'album',
            'album_artist': 'album_artist',
            'composer': 'composer',
            'genre': 'genre',
            'date': 'date',
            'creation_time': 'creation_time',
            'comment': 'comment',
            'description': 'description',
            'synopsis': 'synopsis',
            'copyright': 'copyright',
            'publisher': 'publisher',
            'language': 'language',
            'track': 'track',
            'disc': 'disc',
            'encoder': 'encoder',
            'encoded_by': 'encoded_by',
            'location': 'location',
            'show': 'show',
            'episode_id': 'episode_id',
            'season_number': 'season_number',
            'episode_sort': 'episode_sort',
            'year': 'year',
            'rating': 'rating',
            'grouping': 'grouping',
            'artwork': 'artwork',
            'lyrics': 'lyrics'
        }
    
    def is_supported_format(self, file_path: str) -> bool:
        """Check if file format is supported for FFprobe extraction"""
        extension = Path(file_path).suffix.upper().lstrip('.')
        return extension in self.supported_formats
    
    async def check_ffprobe_availability(self) -> bool:
        """Check if FFprobe is available on the system"""
        try:
            result = await asyncio.create_subprocess_exec(
                self.ffprobe_path, '-version',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await result.wait()
            return result.returncode == 0
        except Exception:
            return False
    
    async def extract_video_metadata(self, file_path: str) -> Dict[str, Any]:
        """
        Extract video metadata using FFprobe
        
        Args:
            file_path: Path to video file
            
        Returns:
            Dictionary containing extracted video metadata
        """
        try:
            if not os.path.exists(file_path):
                raise ExtractionError(f"File not found: {file_path}")
            
            if not self.is_supported_format(file_path):
                extension = Path(file_path).suffix
                raise ExtractionError(f"Unsupported file format: {extension}")
            
            # Check if FFprobe is available
            if not await self.check_ffprobe_availability():
                raise ExtractionError("FFprobe not available on system")
            
            # Run extraction in thread pool to avoid blocking
            metadata = await asyncio.get_event_loop().run_in_executor(
                None, self._extract_metadata_sync, file_path
            )
            
            logger.info(
                "ffprobe_extraction_completed",
                file_path=file_path,
                streams_count=len(metadata.get('streams', [])),
                duration=metadata.get('format', {}).get('duration')
            )
            
            return metadata
            
        except Exception as e:
            logger.error(
                "ffprobe_extraction_failed",
                file_path=file_path,
                error=str(e)
            )
            raise ExtractionError(f"Failed to extract video metadata: {str(e)}")
    
    def _extract_metadata_sync(self, file_path: str) -> Dict[str, Any]:
        """Synchronous metadata extraction using FFprobe"""
        try:
            # Use ffmpeg-python to probe the file
            probe_result = ffmpeg.probe(file_path)
            
            # Extract basic file info
            file_info = {
                'file_path': file_path,
                'file_size': os.path.getsize(file_path),
                'extracted_at': datetime.utcnow().isoformat(),
                'extraction_tool': 'ffprobe',
                'extraction_method': 'ffmpeg-python'
            }
            
            # Process format information
            format_info = self._process_format_info(probe_result.get('format', {}))
            
            # Process streams
            streams = self._process_streams(probe_result.get('streams', []))
            
            # Process chapters if available
            chapters = self._process_chapters(probe_result.get('chapters', []))
            
            # Categorize streams
            video_streams = [s for s in streams if s.get('codec_type') == 'video']
            audio_streams = [s for s in streams if s.get('codec_type') == 'audio']
            subtitle_streams = [s for s in streams if s.get('codec_type') == 'subtitle']
            
            # Calculate derived information
            derived_info = self._calculate_derived_info(format_info, video_streams, audio_streams)
            
            return {
                'file_info': file_info,
                'format': format_info,
                'streams': streams,
                'video_streams': video_streams,
                'audio_streams': audio_streams,
                'subtitle_streams': subtitle_streams,
                'chapters': chapters,
                'derived_info': derived_info,
                'technical_summary': self._create_technical_summary(format_info, streams)
            }
            
        except Exception as e:
            logger.error("ffprobe_sync_extraction_failed", error=str(e))
            raise ExtractionError(f"FFprobe extraction failed: {str(e)}")
    
    def _process_format_info(self, format_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process format information from FFprobe output"""
        format_info = {
            'filename': format_data.get('filename'),
            'nb_streams': format_data.get('nb_streams', 0),
            'nb_programs': format_data.get('nb_programs', 0),
            'format_name': format_data.get('format_name'),
            'format_long_name': format_data.get('format_long_name'),
            'start_time': self._safe_float(format_data.get('start_time')),
            'duration': self._safe_float(format_data.get('duration')),
            'size': self._safe_int(format_data.get('size')),
            'bit_rate': self._safe_int(format_data.get('bit_rate')),
            'probe_score': format_data.get('probe_score')
        }
        
        # Process tags/metadata
        tags = format_data.get('tags', {})
        format_info['metadata'] = self._process_metadata_tags(tags)
        
        return format_info
    
    def _process_streams(self, streams_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process streams information from FFprobe output"""
        processed_streams = []
        
        for stream in streams_data:
            stream_info = {
                'index': stream.get('index'),
                'codec_name': stream.get('codec_name'),
                'codec_long_name': stream.get('codec_long_name'),
                'profile': stream.get('profile'),
                'codec_type': stream.get('codec_type'),
                'codec_tag_string': stream.get('codec_tag_string'),
                'codec_tag': stream.get('codec_tag'),
                'time_base': stream.get('time_base'),
                'start_pts': stream.get('start_pts'),
                'start_time': self._safe_float(stream.get('start_time')),
                'duration_ts': stream.get('duration_ts'),
                'duration': self._safe_float(stream.get('duration')),
                'bit_rate': self._safe_int(stream.get('bit_rate')),
                'nb_frames': self._safe_int(stream.get('nb_frames')),
                'disposition': stream.get('disposition', {}),
                'tags': stream.get('tags', {})
            }
            
            # Add codec-specific information
            if stream_info['codec_type'] == 'video':
                stream_info.update(self._process_video_stream(stream))
            elif stream_info['codec_type'] == 'audio':
                stream_info.update(self._process_audio_stream(stream))
            elif stream_info['codec_type'] == 'subtitle':
                stream_info.update(self._process_subtitle_stream(stream))
            
            processed_streams.append(stream_info)
        
        return processed_streams
    
    def _process_video_stream(self, stream: Dict[str, Any]) -> Dict[str, Any]:
        """Process video stream specific information"""
        video_info = {
            'width': stream.get('width'),
            'height': stream.get('height'),
            'coded_width': stream.get('coded_width'),
            'coded_height': stream.get('coded_height'),
            'closed_captions': stream.get('closed_captions'),
            'film_grain': stream.get('film_grain'),
            'has_b_frames': stream.get('has_b_frames'),
            'sample_aspect_ratio': stream.get('sample_aspect_ratio'),
            'display_aspect_ratio': stream.get('display_aspect_ratio'),
            'pix_fmt': stream.get('pix_fmt'),
            'level': stream.get('level'),
            'color_range': stream.get('color_range'),
            'color_space': stream.get('color_space'),
            'color_transfer': stream.get('color_transfer'),
            'color_primaries': stream.get('color_primaries'),
            'chroma_location': stream.get('chroma_location'),
            'field_order': stream.get('field_order'),
            'refs': stream.get('refs'),
            'r_frame_rate': stream.get('r_frame_rate'),
            'avg_frame_rate': stream.get('avg_frame_rate'),
            'time_base': stream.get('time_base')
        }
        
        # Calculate derived video information
        if video_info['width'] and video_info['height']:
            video_info['resolution'] = f"{video_info['width']}x{video_info['height']}"
            video_info['aspect_ratio'] = round(video_info['width'] / video_info['height'], 2)
        
        # Parse frame rates
        if video_info['r_frame_rate']:
            video_info['frame_rate'] = self._parse_frame_rate(video_info['r_frame_rate'])
        
        # Calculate total pixels
        if video_info['width'] and video_info['height']:
            video_info['total_pixels'] = video_info['width'] * video_info['height']
        
        return video_info
    
    def _process_audio_stream(self, stream: Dict[str, Any]) -> Dict[str, Any]:
        """Process audio stream specific information"""
        audio_info = {
            'sample_fmt': stream.get('sample_fmt'),
            'sample_rate': self._safe_int(stream.get('sample_rate')),
            'channels': stream.get('channels'),
            'channel_layout': stream.get('channel_layout'),
            'bits_per_sample': stream.get('bits_per_sample'),
            'bits_per_raw_sample': stream.get('bits_per_raw_sample'),
            'max_bit_rate': self._safe_int(stream.get('max_bit_rate'))
        }
        
        return audio_info
    
    def _process_subtitle_stream(self, stream: Dict[str, Any]) -> Dict[str, Any]:
        """Process subtitle stream specific information"""
        subtitle_info = {
            'subtitle_type': stream.get('subtitle_type'),
            'forced': stream.get('disposition', {}).get('forced', 0) == 1,
            'default': stream.get('disposition', {}).get('default', 0) == 1,
            'language': stream.get('tags', {}).get('language')
        }
        
        return subtitle_info
    
    def _process_chapters(self, chapters_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process chapters information"""
        chapters = []
        
        for chapter in chapters_data:
            chapter_info = {
                'id': chapter.get('id'),
                'time_base': chapter.get('time_base'),
                'start': chapter.get('start'),
                'start_time': self._safe_float(chapter.get('start_time')),
                'end': chapter.get('end'),
                'end_time': self._safe_float(chapter.get('end_time')),
                'tags': chapter.get('tags', {})
            }
            
            # Calculate duration
            if chapter_info['end_time'] and chapter_info['start_time']:
                chapter_info['duration'] = chapter_info['end_time'] - chapter_info['start_time']
            
            chapters.append(chapter_info)
        
        return chapters
    
    def _process_metadata_tags(self, tags: Dict[str, Any]) -> Dict[str, Any]:
        """Process metadata tags using the mapping"""
        processed_metadata = {}
        
        for tag_key, tag_value in tags.items():
            # Convert to lowercase for consistent mapping
            normalized_key = tag_key.lower()
            
            # Use mapping if available, otherwise use original key
            mapped_key = self.metadata_mapping.get(normalized_key, normalized_key)
            processed_metadata[mapped_key] = tag_value
        
        # Process special date fields
        if 'creation_time' in processed_metadata:
            processed_metadata['creation_time'] = self._parse_creation_time(
                processed_metadata['creation_time']
            )
        
        return processed_metadata
    
    def _calculate_derived_info(self, format_info: Dict[str, Any], 
                               video_streams: List[Dict[str, Any]], 
                               audio_streams: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate derived information from format and streams"""
        derived = {
            'is_video': len(video_streams) > 0,
            'is_audio_only': len(video_streams) == 0 and len(audio_streams) > 0,
            'has_audio': len(audio_streams) > 0,
            'has_video': len(video_streams) > 0,
            'stream_count': {
                'video': len(video_streams),
                'audio': len(audio_streams),
                'total': format_info.get('nb_streams', 0)
            }
        }
        
        # Primary video stream information
        if video_streams:
            primary_video = video_streams[0]
            derived['primary_video'] = {
                'codec': primary_video.get('codec_name'),
                'resolution': primary_video.get('resolution'),
                'frame_rate': primary_video.get('frame_rate'),
                'aspect_ratio': primary_video.get('aspect_ratio'),
                'duration': primary_video.get('duration') or format_info.get('duration')
            }
        
        # Primary audio stream information
        if audio_streams:
            primary_audio = audio_streams[0]
            derived['primary_audio'] = {
                'codec': primary_audio.get('codec_name'),
                'sample_rate': primary_audio.get('sample_rate'),
                'channels': primary_audio.get('channels'),
                'bit_rate': primary_audio.get('bit_rate')
            }
        
        # Duration formatting
        if format_info.get('duration'):
            derived['duration_formatted'] = self._format_duration(format_info['duration'])
        
        # File size formatting
        if format_info.get('size'):
            derived['size_formatted'] = self._format_file_size(format_info['size'])
        
        return derived
    
    def _create_technical_summary(self, format_info: Dict[str, Any], 
                                 streams: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create a technical summary of the media file"""
        video_streams = [s for s in streams if s.get('codec_type') == 'video']
        audio_streams = [s for s in streams if s.get('codec_type') == 'audio']
        
        summary = {
            'container': format_info.get('format_name'),
            'duration': format_info.get('duration'),
            'size': format_info.get('size'),
            'bit_rate': format_info.get('bit_rate'),
            'streams': len(streams)
        }
        
        if video_streams:
            video = video_streams[0]
            summary['video'] = {
                'codec': video.get('codec_name'),
                'resolution': video.get('resolution'),
                'frame_rate': video.get('frame_rate'),
                'bit_rate': video.get('bit_rate')
            }
        
        if audio_streams:
            audio = audio_streams[0]
            summary['audio'] = {
                'codec': audio.get('codec_name'),
                'sample_rate': audio.get('sample_rate'),
                'channels': audio.get('channels'),
                'bit_rate': audio.get('bit_rate')
            }
        
        return summary
    
    def _safe_float(self, value: Any) -> Optional[float]:
        """Safely convert value to float"""
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def _safe_int(self, value: Any) -> Optional[int]:
        """Safely convert value to int"""
        if value is None:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None
    
    def _parse_frame_rate(self, frame_rate_str: str) -> Optional[float]:
        """Parse frame rate string (e.g., '30/1' -> 30.0)"""
        try:
            if '/' in frame_rate_str:
                numerator, denominator = frame_rate_str.split('/')
                return float(numerator) / float(denominator)
            else:
                return float(frame_rate_str)
        except (ValueError, ZeroDivisionError):
            return None
    
    def _parse_creation_time(self, creation_time_str: str) -> Optional[str]:
        """Parse creation time string to ISO format"""
        try:
            # Common format: 2024-01-01T12:00:00.000000Z
            if 'T' in creation_time_str:
                return creation_time_str.replace('Z', '+00:00')
            else:
                # Try to parse as regular datetime
                dt = datetime.fromisoformat(creation_time_str)
                return dt.isoformat()
        except (ValueError, TypeError):
            return creation_time_str
    
    def _format_duration(self, duration_seconds: float) -> str:
        """Format duration in seconds to HH:MM:SS"""
        try:
            duration = timedelta(seconds=duration_seconds)
            total_seconds = int(duration.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        except (ValueError, TypeError):
            return "00:00:00"
    
    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in bytes to human readable format"""
        try:
            for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                if size_bytes < 1024.0:
                    return f"{size_bytes:.1f} {unit}"
                size_bytes /= 1024.0
            return f"{size_bytes:.1f} PB"
        except (ValueError, TypeError):
            return "0 B"
    
    async def extract_batch(self, file_paths: List[str]) -> Dict[str, Dict[str, Any]]:
        """Extract metadata from multiple video files in batch"""
        results = {}
        
        for file_path in file_paths:
            try:
                results[file_path] = await self.extract_video_metadata(file_path)
            except Exception as e:
                logger.error(
                    "batch_ffprobe_extraction_failed",
                    file_path=file_path,
                    error=str(e)
                )
                results[file_path] = {
                    'error': str(e),
                    'file_info': {
                        'extracted_at': datetime.utcnow().isoformat(),
                        'extraction_tool': 'ffprobe',
                        'file_path': file_path,
                        'success': False
                    }
                }
        
        return results
    
    async def get_video_thumbnail(self, file_path: str, timestamp: float = 1.0) -> Optional[str]:
        """Extract thumbnail from video at specified timestamp"""
        try:
            # This would be implemented to extract thumbnails
            # For now, return None as placeholder
            return None
        except Exception as e:
            logger.error("thumbnail_extraction_failed", error=str(e))
            return None