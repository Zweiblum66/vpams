"""
Metadata extraction service for the Ingest Service
"""

import os
import asyncio
import json
from typing import Optional, Dict, Any
from pathlib import Path
import structlog

from ..models.schemas import FileMetadata, TechnicalMetadata, CameraMetadata, FileType
from ..core.config import settings
from ..core.exceptions import MetadataExtractionError
from ..core.logging import get_logger

logger = get_logger(__name__)


class MetadataService:
    """Service for extracting metadata from files"""
    
    def __init__(self):
        pass
    
    async def extract_file_metadata(self, file_path: str) -> FileMetadata:
        """Extract basic file metadata"""
        try:
            file_stat = os.stat(file_path)
            file_name = Path(file_path).name
            file_extension = Path(file_path).suffix.lower().lstrip('.')
            
            # Determine file type
            file_type = self._determine_file_type(file_extension)
            
            metadata = FileMetadata(
                filename=file_name,
                file_size=file_stat.st_size,
                file_type=file_type.value if isinstance(file_type, FileType) else str(file_type),
                extension=file_extension,
                created_date=file_stat.st_ctime,
                modified_date=file_stat.st_mtime,
                checksum="",  # Will be calculated if needed
                mime_type="",  # Will be detected if needed
                metadata={}
            )
            
            return metadata
            
        except Exception as e:
            logger.error(
                "file_metadata_extraction_failed",
                error=str(e),
                file_path=file_path
            )
            raise MetadataExtractionError(f"Failed to extract file metadata: {str(e)}")
    
    async def extract_technical_metadata(self, file_path: str) -> Optional[TechnicalMetadata]:
        """Extract technical metadata for media files"""
        try:
            file_extension = Path(file_path).suffix.lower().lstrip('.')
            
            if file_extension in settings.allowed_video_formats:
                return await self._extract_video_metadata(file_path)
            elif file_extension in settings.allowed_audio_formats:
                return await self._extract_audio_metadata(file_path)
            elif file_extension in settings.allowed_image_formats:
                return await self._extract_image_metadata(file_path)
            
            return None
            
        except Exception as e:
            logger.error(
                "technical_metadata_extraction_failed",
                error=str(e),
                file_path=file_path
            )
            return None
    
    async def extract_camera_metadata(self, file_path: str) -> Optional[CameraMetadata]:
        """Extract camera metadata from media files"""
        try:
            # This would use EXIF data for images or embedded metadata for videos
            # Placeholder implementation
            return None
            
        except Exception as e:
            logger.error(
                "camera_metadata_extraction_failed",
                error=str(e),
                file_path=file_path
            )
            return None
    
    async def _extract_video_metadata(self, file_path: str) -> Optional[TechnicalMetadata]:
        """Extract video metadata using FFprobe"""
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                file_path
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                data = json.loads(stdout.decode())
                
                # Extract video stream info
                video_stream = next(
                    (s for s in data.get('streams', []) if s.get('codec_type') == 'video'),
                    None
                )
                
                if video_stream:
                    metadata = TechnicalMetadata(
                        duration=float(data.get('format', {}).get('duration', 0)),
                        width=video_stream.get('width', 0),
                        height=video_stream.get('height', 0),
                        frame_rate=eval(video_stream.get('r_frame_rate', '0/1')),
                        codec=video_stream.get('codec_name', ''),
                        bitrate=int(data.get('format', {}).get('bit_rate', 0)),
                        color_space=video_stream.get('color_space', ''),
                        audio_channels=0,
                        sample_rate=0,
                        metadata=data
                    )
                    
                    # Add audio info if present
                    audio_stream = next(
                        (s for s in data.get('streams', []) if s.get('codec_type') == 'audio'),
                        None
                    )
                    
                    if audio_stream:
                        metadata.audio_channels = audio_stream.get('channels', 0)
                        metadata.sample_rate = int(audio_stream.get('sample_rate', 0))
                    
                    return metadata
            
            return None
            
        except Exception as e:
            logger.warning(
                "video_metadata_extraction_failed",
                error=str(e),
                file_path=file_path
            )
            return None
    
    async def _extract_audio_metadata(self, file_path: str) -> Optional[TechnicalMetadata]:
        """Extract audio metadata"""
        try:
            # Using mutagen for audio metadata
            from mutagen import File
            
            audio_file = File(file_path)
            if audio_file is None:
                return None
            
            metadata = TechnicalMetadata(
                duration=getattr(audio_file.info, 'length', 0),
                width=0,
                height=0,
                frame_rate=0,
                codec=getattr(audio_file.info, 'codec', ''),
                bitrate=getattr(audio_file.info, 'bitrate', 0),
                color_space='',
                audio_channels=getattr(audio_file.info, 'channels', 0),
                sample_rate=getattr(audio_file.info, 'sample_rate', 0),
                metadata=dict(audio_file) if audio_file else {}
            )
            
            return metadata
            
        except Exception as e:
            logger.warning(
                "audio_metadata_extraction_failed",
                error=str(e),
                file_path=file_path
            )
            return None
    
    async def _extract_image_metadata(self, file_path: str) -> Optional[TechnicalMetadata]:
        """Extract image metadata"""
        try:
            from PIL import Image
            from PIL.ExifTags import TAGS
            
            with Image.open(file_path) as img:
                width, height = img.size
                
                # Extract EXIF data
                exif_data = {}
                if hasattr(img, '_getexif') and img._getexif():
                    exif = img._getexif()
                    for tag_id, value in exif.items():
                        tag = TAGS.get(tag_id, tag_id)
                        exif_data[tag] = str(value)
                
                metadata = TechnicalMetadata(
                    duration=0,
                    width=width,
                    height=height,
                    frame_rate=0,
                    codec=img.format,
                    bitrate=0,
                    color_space=img.mode,
                    audio_channels=0,
                    sample_rate=0,
                    metadata=exif_data
                )
                
                return metadata
            
        except Exception as e:
            logger.warning(
                "image_metadata_extraction_failed",
                error=str(e),
                file_path=file_path
            )
            return None
    
    def _determine_file_type(self, file_extension: str) -> FileType:
        """Determine file type from extension"""
        if file_extension in settings.allowed_video_formats:
            return FileType.VIDEO
        elif file_extension in settings.allowed_audio_formats:
            return FileType.AUDIO
        elif file_extension in settings.allowed_image_formats:
            return FileType.IMAGE
        elif file_extension in settings.allowed_document_formats:
            return FileType.DOCUMENT
        else:
            return FileType.UNKNOWN


# Dependency injection
_metadata_service: Optional[MetadataService] = None


async def get_metadata_service() -> MetadataService:
    """Get metadata service instance"""
    global _metadata_service
    
    if _metadata_service is None:
        _metadata_service = MetadataService()
    
    return _metadata_service