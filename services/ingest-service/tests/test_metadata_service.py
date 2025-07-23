"""
Test Metadata Service

Tests for metadata extraction functionality in the Ingest Service.
"""

import pytest
import asyncio
import os
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock, call
import subprocess
from datetime import datetime

from src.services.metadata_service import MetadataService, get_metadata_service
from src.models.schemas import FileMetadata, TechnicalMetadata, CameraMetadata, FileType
from src.core.exceptions import MetadataExtractionError
from src.core.config import settings


class TestMetadataService:
    """Test cases for MetadataService."""
    
    @pytest.fixture
    def service(self):
        """Create metadata service instance."""
        return MetadataService()
    
    @pytest.fixture
    def temp_video_file(self, tmp_path):
        """Create a temporary video file."""
        file_path = tmp_path / "test_video.mp4"
        file_path.write_bytes(b"fake video content" * 1000)
        return str(file_path)
    
    @pytest.fixture
    def temp_audio_file(self, tmp_path):
        """Create a temporary audio file."""
        file_path = tmp_path / "test_audio.mp3"
        file_path.write_bytes(b"fake audio content" * 500)
        return str(file_path)
    
    @pytest.fixture
    def temp_image_file(self, tmp_path):
        """Create a temporary image file."""
        file_path = tmp_path / "test_image.jpg"
        file_path.write_bytes(b"fake image content" * 100)
        return str(file_path)
    
    @pytest.fixture
    def temp_document_file(self, tmp_path):
        """Create a temporary document file."""
        file_path = tmp_path / "test_document.pdf"
        file_path.write_bytes(b"fake pdf content" * 200)
        return str(file_path)
    
    async def test_extract_file_metadata_success(self, service, temp_video_file):
        """Test successful file metadata extraction."""
        metadata = await service.extract_file_metadata(temp_video_file)
        
        # Assertions
        assert isinstance(metadata, FileMetadata)
        assert metadata.filename == "test_video.mp4"
        assert metadata.file_size > 0
        assert metadata.extension == "mp4"
        assert metadata.created_date > 0
        assert metadata.modified_date > 0
    
    async def test_extract_file_metadata_video_type(self, service, temp_video_file):
        """Test file type detection for video."""
        with patch.object(settings, 'allowed_video_formats', ['mp4', 'avi', 'mov']):
            metadata = await service.extract_file_metadata(temp_video_file)
            assert metadata.file_type == FileType.VIDEO.value
    
    async def test_extract_file_metadata_audio_type(self, service, temp_audio_file):
        """Test file type detection for audio."""
        with patch.object(settings, 'allowed_audio_formats', ['mp3', 'wav', 'aac']):
            metadata = await service.extract_file_metadata(temp_audio_file)
            assert metadata.file_type == FileType.AUDIO.value
    
    async def test_extract_file_metadata_image_type(self, service, temp_image_file):
        """Test file type detection for image."""
        with patch.object(settings, 'allowed_image_formats', ['jpg', 'png', 'gif']):
            metadata = await service.extract_file_metadata(temp_image_file)
            assert metadata.file_type == FileType.IMAGE.value
    
    async def test_extract_file_metadata_document_type(self, service, temp_document_file):
        """Test file type detection for document."""
        with patch.object(settings, 'allowed_document_formats', ['pdf', 'doc', 'txt']):
            metadata = await service.extract_file_metadata(temp_document_file)
            assert metadata.file_type == FileType.DOCUMENT.value
    
    async def test_extract_file_metadata_unknown_type(self, service, tmp_path):
        """Test file type detection for unknown type."""
        unknown_file = tmp_path / "test.xyz"
        unknown_file.write_bytes(b"content")
        
        with patch.object(settings, 'allowed_video_formats', []):
            with patch.object(settings, 'allowed_audio_formats', []):
                with patch.object(settings, 'allowed_image_formats', []):
                    with patch.object(settings, 'allowed_document_formats', []):
                        metadata = await service.extract_file_metadata(str(unknown_file))
                        assert metadata.file_type == FileType.UNKNOWN.value
    
    async def test_extract_file_metadata_nonexistent_file(self, service):
        """Test metadata extraction for non-existent file."""
        with pytest.raises(MetadataExtractionError, match="Failed to extract file metadata"):
            await service.extract_file_metadata("/nonexistent/file.mp4")
    
    async def test_extract_technical_metadata_video(self, service, temp_video_file):
        """Test technical metadata extraction for video."""
        # Mock ffprobe output
        ffprobe_output = {
            "format": {
                "duration": "120.5",
                "bit_rate": "5000000"
            },
            "streams": [
                {
                    "codec_type": "video",
                    "codec_name": "h264",
                    "width": 1920,
                    "height": 1080,
                    "r_frame_rate": "30/1",
                    "color_space": "yuv420p"
                },
                {
                    "codec_type": "audio",
                    "channels": 2,
                    "sample_rate": "48000"
                }
            ]
        }
        
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = (
            json.dumps(ffprobe_output).encode(),
            b""
        )
        
        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            with patch.object(settings, 'allowed_video_formats', ['mp4']):
                metadata = await service.extract_technical_metadata(temp_video_file)
                
                # Assertions
                assert isinstance(metadata, TechnicalMetadata)
                assert metadata.duration == 120.5
                assert metadata.width == 1920
                assert metadata.height == 1080
                assert metadata.frame_rate == 30.0
                assert metadata.codec == "h264"
                assert metadata.bitrate == 5000000
                assert metadata.audio_channels == 2
                assert metadata.sample_rate == 48000
    
    async def test_extract_technical_metadata_video_no_audio(self, service, temp_video_file):
        """Test video metadata extraction without audio stream."""
        ffprobe_output = {
            "format": {"duration": "60.0", "bit_rate": "2000000"},
            "streams": [{
                "codec_type": "video",
                "codec_name": "h265",
                "width": 3840,
                "height": 2160,
                "r_frame_rate": "60/1"
            }]
        }
        
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = (json.dumps(ffprobe_output).encode(), b"")
        
        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            with patch.object(settings, 'allowed_video_formats', ['mp4']):
                metadata = await service.extract_technical_metadata(temp_video_file)
                
                assert metadata.audio_channels == 0
                assert metadata.sample_rate == 0
    
    async def test_extract_technical_metadata_ffprobe_failure(self, service, temp_video_file):
        """Test video metadata extraction when ffprobe fails."""
        mock_process = AsyncMock()
        mock_process.returncode = 1
        mock_process.communicate.return_value = (b"", b"error")
        
        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            with patch.object(settings, 'allowed_video_formats', ['mp4']):
                metadata = await service.extract_technical_metadata(temp_video_file)
                assert metadata is None
    
    async def test_extract_technical_metadata_audio(self, service, temp_audio_file):
        """Test technical metadata extraction for audio."""
        # Mock mutagen File
        mock_audio = Mock()
        mock_audio.info.length = 180.5
        mock_audio.info.channels = 2
        mock_audio.info.sample_rate = 44100
        mock_audio.info.bitrate = 320000
        mock_audio.info.codec = "mp3"
        
        with patch('src.services.metadata_service.File', return_value=mock_audio):
            with patch.object(settings, 'allowed_audio_formats', ['mp3']):
                metadata = await service.extract_technical_metadata(temp_audio_file)
                
                # Assertions
                assert isinstance(metadata, TechnicalMetadata)
                assert metadata.duration == 180.5
                assert metadata.audio_channels == 2
                assert metadata.sample_rate == 44100
                assert metadata.bitrate == 320000
                assert metadata.codec == "mp3"
                # Audio files don't have video properties
                assert metadata.width == 0
                assert metadata.height == 0
                assert metadata.frame_rate == 0
    
    async def test_extract_technical_metadata_audio_mutagen_failure(self, service, temp_audio_file):
        """Test audio metadata extraction when mutagen fails."""
        with patch('src.services.metadata_service.File', return_value=None):
            with patch.object(settings, 'allowed_audio_formats', ['mp3']):
                metadata = await service.extract_technical_metadata(temp_audio_file)
                assert metadata is None
    
    async def test_extract_technical_metadata_image(self, service, temp_image_file):
        """Test technical metadata extraction for image."""
        # Mock PIL Image
        mock_image = Mock()
        mock_image.size = (1920, 1080)
        mock_image.format = "JPEG"
        mock_image.mode = "RGB"
        mock_image._getexif = Mock(return_value={
            271: "Canon",  # Make
            272: "EOS 5D",  # Model
            274: 1,  # Orientation
            282: (72, 1),  # XResolution
            283: (72, 1)   # YResolution
        })
        
        mock_open = MagicMock()
        mock_open.__enter__.return_value = mock_image
        
        with patch('PIL.Image.open', return_value=mock_open):
            with patch.object(settings, 'allowed_image_formats', ['jpg']):
                metadata = await service.extract_technical_metadata(temp_image_file)
                
                # Assertions
                assert isinstance(metadata, TechnicalMetadata)
                assert metadata.width == 1920
                assert metadata.height == 1080
                assert metadata.codec == "JPEG"
                assert metadata.color_space == "RGB"
                # Images don't have duration or audio properties
                assert metadata.duration == 0
                assert metadata.frame_rate == 0
                assert metadata.audio_channels == 0
    
    async def test_extract_technical_metadata_image_no_exif(self, service, temp_image_file):
        """Test image metadata extraction without EXIF data."""
        mock_image = Mock()
        mock_image.size = (800, 600)
        mock_image.format = "PNG"
        mock_image.mode = "RGBA"
        mock_image._getexif = Mock(return_value=None)
        
        mock_open = MagicMock()
        mock_open.__enter__.return_value = mock_image
        
        with patch('PIL.Image.open', return_value=mock_open):
            with patch.object(settings, 'allowed_image_formats', ['jpg']):
                metadata = await service.extract_technical_metadata(temp_image_file)
                
                assert metadata.metadata == {}
    
    async def test_extract_technical_metadata_unsupported_format(self, service, temp_document_file):
        """Test technical metadata extraction for unsupported format."""
        with patch.object(settings, 'allowed_video_formats', []):
            with patch.object(settings, 'allowed_audio_formats', []):
                with patch.object(settings, 'allowed_image_formats', []):
                    metadata = await service.extract_technical_metadata(temp_document_file)
                    assert metadata is None
    
    async def test_extract_technical_metadata_exception_handling(self, service, temp_video_file):
        """Test exception handling during technical metadata extraction."""
        with patch('asyncio.create_subprocess_exec', side_effect=Exception("Process error")):
            with patch.object(settings, 'allowed_video_formats', ['mp4']):
                metadata = await service.extract_technical_metadata(temp_video_file)
                assert metadata is None
    
    async def test_extract_camera_metadata(self, service, temp_image_file):
        """Test camera metadata extraction (placeholder test)."""
        # Currently returns None as it's a placeholder
        metadata = await service.extract_camera_metadata(temp_image_file)
        assert metadata is None
    
    async def test_determine_file_type(self, service):
        """Test file type determination."""
        with patch.object(settings, 'allowed_video_formats', ['mp4', 'avi']):
            with patch.object(settings, 'allowed_audio_formats', ['mp3', 'wav']):
                with patch.object(settings, 'allowed_image_formats', ['jpg', 'png']):
                    with patch.object(settings, 'allowed_document_formats', ['pdf', 'doc']):
                        assert service._determine_file_type('mp4') == FileType.VIDEO
                        assert service._determine_file_type('mp3') == FileType.AUDIO
                        assert service._determine_file_type('jpg') == FileType.IMAGE
                        assert service._determine_file_type('pdf') == FileType.DOCUMENT
                        assert service._determine_file_type('xyz') == FileType.UNKNOWN
    
    async def test_get_metadata_service_singleton(self):
        """Test that get_metadata_service returns singleton."""
        service1 = await get_metadata_service()
        service2 = await get_metadata_service()
        
        assert service1 is service2
    
    async def test_ffprobe_command_construction(self, service, temp_video_file):
        """Test that ffprobe command is constructed correctly."""
        expected_cmd = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            temp_video_file
        ]
        
        with patch('asyncio.create_subprocess_exec', new_callable=AsyncMock) as mock_exec:
            mock_process = AsyncMock()
            mock_process.returncode = 1  # Make it fail so we don't need full mock
            mock_process.communicate.return_value = (b"", b"")
            mock_exec.return_value = mock_process
            
            with patch.object(settings, 'allowed_video_formats', ['mp4']):
                await service.extract_technical_metadata(temp_video_file)
                
                # Verify command
                mock_exec.assert_called_once_with(
                    *expected_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
    
    async def test_frame_rate_calculation(self, service, temp_video_file):
        """Test frame rate calculation from fraction string."""
        ffprobe_output = {
            "format": {"duration": "10.0"},
            "streams": [{
                "codec_type": "video",
                "r_frame_rate": "24000/1001",  # ~23.976 fps
                "width": 1920,
                "height": 1080
            }]
        }
        
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = (json.dumps(ffprobe_output).encode(), b"")
        
        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            with patch.object(settings, 'allowed_video_formats', ['mp4']):
                metadata = await service.extract_technical_metadata(temp_video_file)
                
                # Should calculate the frame rate correctly
                assert abs(metadata.frame_rate - 23.976) < 0.001
    
    async def test_concurrent_metadata_extraction(self, service, temp_video_file, temp_audio_file, temp_image_file):
        """Test concurrent metadata extraction for multiple files."""
        # Mock different file types
        with patch.object(settings, 'allowed_video_formats', ['mp4']):
            with patch.object(settings, 'allowed_audio_formats', ['mp3']):
                with patch.object(settings, 'allowed_image_formats', ['jpg']):
                    # Run extractions concurrently
                    tasks = [
                        service.extract_file_metadata(temp_video_file),
                        service.extract_file_metadata(temp_audio_file),
                        service.extract_file_metadata(temp_image_file)
                    ]
                    
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    # All should succeed
                    assert all(isinstance(r, FileMetadata) for r in results)
                    assert len(results) == 3
    
    async def test_mutagen_dict_conversion(self, service, temp_audio_file):
        """Test conversion of mutagen file to dict."""
        mock_audio = Mock()
        mock_audio.info.length = 120
        mock_audio.info.channels = 2
        mock_audio.info.sample_rate = 44100
        
        # Mock dict conversion
        mock_audio.__iter__ = Mock(return_value=iter(['title', 'artist']))
        mock_audio.__getitem__ = Mock(side_effect=lambda k: {'title': 'Test Song', 'artist': 'Test Artist'}[k])
        
        with patch('src.services.metadata_service.File', return_value=mock_audio):
            with patch.object(settings, 'allowed_audio_formats', ['mp3']):
                metadata = await service.extract_technical_metadata(temp_audio_file)
                
                assert 'title' in metadata.metadata
                assert 'artist' in metadata.metadata