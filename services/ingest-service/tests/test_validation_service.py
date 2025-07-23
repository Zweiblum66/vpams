"""
Test Validation Service

Tests for file validation functionality in the Ingest Service.
"""

import pytest
import asyncio
import os
import tempfile
import time
import hashlib
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock, call
import magic
import clamd

from src.services.validation_service import ValidationService, get_validation_service
from src.models.schemas import (
    ValidationResult, ValidationRule, ChecksumInfo, FileType
)
from src.core.exceptions import (
    ValidationError, FileNotFoundError, FileSizeError,
    UnsupportedFormatError, VirusDetectedError, ChecksumMismatchError
)
from src.core.config import settings


class TestValidationService:
    """Test cases for ValidationService."""
    
    @pytest.fixture
    def mock_clamd_client(self):
        """Create mock ClamAV client."""
        client = Mock(spec=clamd.ClamdNetworkSocket)
        client.ping = Mock()
        client.scan = Mock(return_value=None)  # Clean scan by default
        return client
    
    @pytest.fixture
    def mock_magic(self):
        """Create mock magic instance."""
        mock = Mock(spec=magic.Magic)
        mock.from_file = Mock(return_value="video/mp4")
        return mock
    
    @pytest.fixture
    def service(self, mock_clamd_client, mock_magic):
        """Create validation service with mocked dependencies."""
        with patch('src.services.validation_service.magic.Magic', return_value=mock_magic):
            with patch('src.services.validation_service.clamd.ClamdNetworkSocket', return_value=mock_clamd_client):
                service = ValidationService()
                service.magic = mock_magic
                service.clamd_client = mock_clamd_client
                return service
    
    @pytest.fixture
    def temp_video_file(self, tmp_path):
        """Create a temporary video file."""
        file_path = tmp_path / "test_video.mp4"
        # Create a file with some content
        file_path.write_bytes(b"fake video content" * 1000)
        return str(file_path)
    
    @pytest.fixture
    def temp_image_file(self, tmp_path):
        """Create a temporary image file."""
        file_path = tmp_path / "test_image.jpg"
        file_path.write_bytes(b"fake image content" * 100)
        return str(file_path)
    
    @pytest.fixture
    def temp_large_file(self, tmp_path):
        """Create a large temporary file."""
        file_path = tmp_path / "large_file.mp4"
        # Create a file larger than max_file_size
        with patch.object(settings, 'max_file_size', 1000):
            file_path.write_bytes(b"x" * 2000)
        return str(file_path)
    
    @pytest.fixture
    def temp_empty_file(self, tmp_path):
        """Create an empty file."""
        file_path = tmp_path / "empty.txt"
        file_path.touch()
        return str(file_path)
    
    async def test_validate_file_success(self, service, temp_video_file, mock_magic):
        """Test successful file validation."""
        mock_magic.from_file.return_value = "video/mp4"
        
        result = await service.validate_file(temp_video_file)
        
        # Assertions
        assert result.is_valid is True
        assert len(result.errors) == 0
        assert result.format_supported is True
        assert result.size_within_limits is True
    
    async def test_validate_file_not_found(self, service):
        """Test validation of non-existent file."""
        result = await service.validate_file("/nonexistent/file.mp4")
        
        assert result.is_valid is False
        assert len(result.errors) > 0
        assert "Validation failed" in result.errors[0]
    
    async def test_validate_file_size_exceeds_limit(self, service, temp_large_file):
        """Test validation when file size exceeds limit."""
        with patch.object(settings, 'max_file_size', 1000):
            result = await service.validate_file(temp_large_file)
            
            assert result.is_valid is False
            assert result.size_within_limits is False
            assert any("exceeds maximum allowed size" in error for error in result.errors)
    
    async def test_validate_empty_file(self, service, temp_empty_file):
        """Test validation of empty file."""
        result = await service.validate_file(temp_empty_file)
        
        assert result.is_valid is False
        assert any("File is empty" in error for error in result.errors)
    
    async def test_validate_file_format_unsupported(self, service, tmp_path):
        """Test validation of unsupported file format."""
        unsupported_file = tmp_path / "test.xyz"
        unsupported_file.write_bytes(b"content")
        
        with patch.object(settings, 'all_allowed_formats', ['mp4', 'jpg', 'pdf']):
            result = await service.validate_file(str(unsupported_file))
            
            assert result.is_valid is False
            assert result.format_supported is False
            assert any("not supported" in error for error in result.errors)
    
    async def test_validate_mime_type_mismatch(self, service, temp_video_file, mock_magic):
        """Test validation when MIME type doesn't match extension."""
        # Make MIME type return image for a video file
        mock_magic.from_file.return_value = "image/jpeg"
        
        result = await service.validate_file(temp_video_file)
        
        # Should warn but not fail
        assert result.is_valid is True
        assert len(result.warnings) > 0
        assert any("MIME type" in warning for warning in result.warnings)
    
    async def test_virus_scan_clean(self, service, temp_video_file, mock_clamd_client):
        """Test virus scanning with clean file."""
        with patch.object(settings, 'enable_virus_scanning', True):
            mock_clamd_client.scan.return_value = None  # Clean
            
            result = await service.validate_file(temp_video_file)
            
            assert result.is_valid is True
            assert result.virus_scan_result == "clean"
            mock_clamd_client.scan.assert_called_once()
    
    async def test_virus_scan_infected(self, service, temp_video_file, mock_clamd_client):
        """Test virus scanning with infected file."""
        with patch.object(settings, 'enable_virus_scanning', True):
            mock_clamd_client.scan.return_value = {
                temp_video_file: ('FOUND', 'Trojan.Test')
            }
            
            result = await service.validate_file(temp_video_file)
            
            assert result.is_valid is False
            assert result.virus_scan_result == "infected: Trojan.Test"
            assert any("Virus detected" in error for error in result.errors)
    
    async def test_virus_scan_failure(self, service, temp_video_file, mock_clamd_client):
        """Test when virus scanning fails."""
        with patch.object(settings, 'enable_virus_scanning', True):
            mock_clamd_client.scan.side_effect = Exception("ClamAV error")
            
            result = await service.validate_file(temp_video_file)
            
            # Should not fail validation, just warn
            assert result.is_valid is True
            assert any("Virus scanning failed" in warning for warning in result.warnings)
    
    async def test_checksum_validation(self, service, temp_video_file):
        """Test checksum calculation."""
        with patch.object(settings, 'enable_checksum_verification', True):
            with patch.object(settings, 'checksum_algorithms', ['md5', 'sha256']):
                result = await service.validate_file(temp_video_file)
                
                assert result.checksum_verified is True
    
    async def test_custom_validation_rules(self, service, temp_video_file):
        """Test applying custom validation rules."""
        # Create custom rules
        rules = [
            ValidationRule(
                rule_type="max_file_size",
                parameters={"max_size": 100000},
                enabled=True,
                error_level="error"
            ),
            ValidationRule(
                rule_type="required_extension",
                parameters={"extension": "mp4"},
                enabled=True,
                error_level="error"
            ),
            ValidationRule(
                rule_type="filename_pattern",
                parameters={"pattern": r"test_.*\.mp4"},
                enabled=True,
                error_level="warning"
            )
        ]
        
        result = await service.validate_file(temp_video_file, rules)
        
        assert result.is_valid is True  # All rules should pass
    
    async def test_custom_rule_max_file_size_failure(self, service, temp_video_file):
        """Test custom max file size rule failure."""
        rule = ValidationRule(
            rule_type="max_file_size",
            parameters={"max_size": 10},  # Very small limit
            enabled=True,
            error_level="error"
        )
        
        result = await service.validate_file(temp_video_file, [rule])
        
        assert result.is_valid is False
        assert any("exceeds limit" in error for error in result.errors)
    
    async def test_custom_rule_required_extension_failure(self, service, temp_video_file):
        """Test custom required extension rule failure."""
        rule = ValidationRule(
            rule_type="required_extension",
            parameters={"extension": "avi"},  # Wrong extension
            enabled=True,
            error_level="error"
        )
        
        result = await service.validate_file(temp_video_file, [rule])
        
        assert result.is_valid is False
        assert any("must be 'avi'" in error for error in result.errors)
    
    async def test_custom_rule_forbidden_extension(self, service, tmp_path):
        """Test custom forbidden extension rule."""
        forbidden_file = tmp_path / "test.exe"
        forbidden_file.write_bytes(b"content")
        
        rule = ValidationRule(
            rule_type="forbidden_extension",
            parameters={"extension": "exe"},
            enabled=True,
            error_level="error"
        )
        
        result = await service.validate_file(str(forbidden_file), [rule])
        
        assert result.is_valid is False
        assert any("not allowed" in error for error in result.errors)
    
    async def test_custom_rule_min_file_size(self, service, temp_video_file):
        """Test custom minimum file size rule."""
        rule = ValidationRule(
            rule_type="min_file_size",
            parameters={"min_size": 100},
            enabled=True,
            error_level="error"
        )
        
        result = await service.validate_file(temp_video_file, [rule])
        
        assert result.is_valid is True  # File should be large enough
    
    async def test_custom_rule_filename_pattern(self, service, temp_video_file):
        """Test custom filename pattern rule."""
        rule = ValidationRule(
            rule_type="filename_pattern",
            parameters={"pattern": r"prod_.*\.mp4"},  # Doesn't match test_video.mp4
            enabled=True,
            error_level="error"
        )
        
        result = await service.validate_file(temp_video_file, [rule])
        
        assert result.is_valid is False
        assert any("does not match required pattern" in error for error in result.errors)
    
    async def test_custom_rule_disabled(self, service, temp_video_file):
        """Test that disabled rules are not applied."""
        rule = ValidationRule(
            rule_type="max_file_size",
            parameters={"max_size": 1},  # Would fail if applied
            enabled=False,
            error_level="error"
        )
        
        result = await service.validate_file(temp_video_file, [rule])
        
        assert result.is_valid is True  # Rule should not be applied
    
    @patch('subprocess.PIPE')
    @patch('asyncio.create_subprocess_exec')
    async def test_video_integrity_validation(self, mock_subprocess, mock_pipe, service, temp_video_file):
        """Test video file integrity validation."""
        # Mock ffprobe process
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = (b"h264\n", b"")
        mock_subprocess.return_value = mock_process
        
        result = await service.validate_file(temp_video_file)
        
        assert result.is_valid is True
        mock_subprocess.assert_called()
    
    @patch('subprocess.PIPE')
    @patch('asyncio.create_subprocess_exec')
    async def test_video_integrity_validation_failure(self, mock_subprocess, mock_pipe, service, temp_video_file):
        """Test video integrity validation when ffprobe fails."""
        # Mock ffprobe process failure
        mock_process = AsyncMock()
        mock_process.returncode = 1
        mock_process.communicate.return_value = (b"", b"error")
        mock_subprocess.return_value = mock_process
        
        result = await service.validate_file(temp_video_file)
        
        # Should warn but not fail
        assert result.is_valid is True
        assert any("may be corrupted" in warning for warning in result.warnings)
    
    @patch('PIL.Image')
    async def test_image_integrity_validation(self, mock_pil, service, temp_image_file):
        """Test image file integrity validation."""
        mock_image = Mock()
        mock_image.verify = Mock()
        mock_pil.open.return_value.__enter__.return_value = mock_image
        
        with patch.object(settings, 'allowed_image_formats', ['jpg', 'png']):
            result = await service.validate_file(temp_image_file)
            
            assert result.is_valid is True
            mock_image.verify.assert_called_once()
    
    @patch('mutagen.File')
    async def test_audio_integrity_validation(self, mock_mutagen, service, tmp_path):
        """Test audio file integrity validation."""
        audio_file = tmp_path / "test.mp3"
        audio_file.write_bytes(b"fake audio")
        
        mock_audio = Mock()
        mock_audio.info.length = 120.0
        mock_mutagen.return_value = mock_audio
        
        with patch.object(settings, 'allowed_audio_formats', ['mp3', 'wav']):
            result = await service.validate_file(str(audio_file))
            
            assert result.is_valid is True
    
    async def test_file_access_validation_permission_denied(self, service, tmp_path):
        """Test file access validation with permission denied."""
        file_path = tmp_path / "no_access.mp4"
        file_path.write_bytes(b"content")
        
        # Mock permission error
        with patch('os.access', return_value=False):
            result = await service.validate_file(str(file_path))
            
            assert result.is_valid is False
            assert any("not readable" in error for error in result.errors)
    
    async def test_calculate_checksum(self, service, temp_video_file):
        """Test checksum calculation."""
        # Calculate expected checksum
        with open(temp_video_file, 'rb') as f:
            expected_md5 = hashlib.md5(f.read()).hexdigest()
        
        checksum = await service._calculate_checksum(temp_video_file, 'md5')
        
        assert checksum == expected_md5
    
    async def test_batch_validate_files(self, service, temp_video_file, temp_image_file):
        """Test batch file validation."""
        file_paths = [temp_video_file, temp_image_file, "/nonexistent/file.txt"]
        
        results = await service.batch_validate_files(file_paths)
        
        assert len(results) == 3
        assert results[0].is_valid is True  # Video file
        assert results[1].is_valid is True  # Image file
        assert results[2].is_valid is False  # Non-existent file
    
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
    
    async def test_warning_for_large_files(self, service, tmp_path):
        """Test warning for files close to size limit."""
        file_path = tmp_path / "large.mp4"
        
        with patch.object(settings, 'max_file_size', 1000):
            # Create file at 85% of max size
            file_path.write_bytes(b"x" * 850)
            
            result = await service.validate_file(str(file_path))
            
            assert result.is_valid is True
            assert any("very large" in warning for warning in result.warnings)
    
    async def test_virus_scanner_initialization_failure(self):
        """Test service initialization when virus scanner fails."""
        with patch.object(settings, 'enable_virus_scanning', True):
            with patch('src.services.validation_service.clamd.ClamdNetworkSocket') as mock_clamd:
                mock_clamd.side_effect = Exception("Connection failed")
                
                service = ValidationService()
                
                assert service.clamd_client is None
    
    async def test_get_validation_service_singleton(self):
        """Test that get_validation_service returns singleton."""
        service1 = await get_validation_service()
        service2 = await get_validation_service()
        
        assert service1 is service2
    
    async def test_concurrent_validations(self, service, temp_video_file):
        """Test concurrent file validations."""
        # Run multiple validations concurrently
        tasks = [service.validate_file(temp_video_file) for _ in range(5)]
        results = await asyncio.gather(*tasks)
        
        # All should succeed
        assert all(result.is_valid for result in results)
        assert len(results) == 5
    
    async def test_mime_type_validation_exception(self, service, temp_video_file, mock_magic):
        """Test MIME type validation when magic fails."""
        mock_magic.from_file.side_effect = Exception("Magic error")
        
        result = await service.validate_file(temp_video_file)
        
        # Should not fail, just warn
        assert result.is_valid is True
        assert any("Could not determine MIME type" in warning for warning in result.warnings)
    
    async def test_file_open_failure(self, service, temp_video_file):
        """Test validation when file cannot be opened."""
        with patch('builtins.open', side_effect=OSError("Cannot open file")):
            result = await service.validate_file(temp_video_file)
            
            assert result.is_valid is False
            assert any("File system error" in error for error in result.errors)