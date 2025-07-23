"""
Unit tests for file validation system
"""

import pytest
import tempfile
import os
from pathlib import Path

from src.core.validators import FileValidator, MediaFileValidator, FileValidationRules


class TestFileValidator:
    """Test FileValidator class"""
    
    @pytest.fixture
    def validator(self):
        """Create a FileValidator instance"""
        return FileValidator()
    
    @pytest.fixture
    def temp_file(self):
        """Create a temporary file for testing"""
        fd, path = tempfile.mkstemp()
        with os.fdopen(fd, 'w') as f:
            f.write("Test content")
        yield path
        os.unlink(path)
    
    def test_validate_file_size_too_large(self, validator):
        """Test validation fails for files exceeding size limit"""
        rules = FileValidationRules(max_file_size=100)
        validator = FileValidator(rules)
        results = {"valid": True, "errors": [], "warnings": []}
        
        validator._validate_file_size(1000, results)
        
        assert not results["valid"]
        assert len(results["errors"]) == 1
        assert "File too large" in results["errors"][0]
    
    def test_validate_file_size_too_small(self, validator):
        """Test validation fails for files below minimum size"""
        rules = FileValidationRules(min_file_size=100)
        validator = FileValidator(rules)
        results = {"valid": True, "errors": [], "warnings": []}
        
        validator._validate_file_size(10, results)
        
        assert not results["valid"]
        assert len(results["errors"]) == 1
        assert "File too small" in results["errors"][0]
    
    def test_validate_filename_blocked_extension(self, validator):
        """Test validation fails for blocked extensions"""
        results = {"valid": True, "errors": [], "warnings": [], "file_info": {}}
        
        validator._validate_filename("malware.exe", results)
        
        assert not results["valid"]
        assert "blocked" in results["errors"][0]
    
    def test_validate_filename_allowed_extension(self, validator):
        """Test validation passes for allowed extensions"""
        results = {"valid": True, "errors": [], "warnings": [], "file_info": {}}
        
        validator._validate_filename("video.mp4", results)
        
        assert results["valid"]
        assert results["file_info"]["extension"] == ".mp4"
    
    def test_validate_filename_suspicious_patterns(self, validator):
        """Test warning for suspicious filename patterns"""
        results = {"valid": True, "errors": [], "warnings": [], "file_info": {}}
        
        validator._validate_filename("..hidden.txt", results)
        
        assert len(results["warnings"]) > 0
        assert "suspicious" in results["warnings"][0].lower()
    
    def test_validate_filename_rtlo_character(self, validator):
        """Test validation fails for RTLO character"""
        results = {"valid": True, "errors": [], "warnings": [], "file_info": {}}
        filename = "test\u202etxt.exe"  # RTLO character
        
        # Security check should catch this
        validator._security_checks("", filename, results)
        
        assert not results["valid"]
        assert "RTLO" in results["errors"][0]
    
    def test_validate_mime_type_allowed(self, validator):
        """Test MIME type validation for allowed types"""
        results = {"valid": True, "errors": [], "warnings": []}
        
        validator._validate_mime_type("video/mp4", results)
        
        assert results["valid"]
    
    def test_validate_mime_type_wildcard(self, validator):
        """Test MIME type validation with wildcard patterns"""
        results = {"valid": True, "errors": [], "warnings": []}
        
        validator._validate_mime_type("video/quicktime", results)
        
        assert results["valid"]  # Should match video/*
    
    def test_validate_mime_type_blocked(self, validator):
        """Test MIME type validation for blocked types"""
        rules = FileValidationRules(
            allowed_mime_types=["image/*"],
            blocked_mime_types=["application/x-executable"]
        )
        validator = FileValidator(rules)
        results = {"valid": True, "errors": [], "warnings": []}
        
        validator._validate_mime_type("application/x-executable", results)
        
        assert not results["valid"]
        assert "blocked" in results["errors"][0]
    
    @pytest.mark.asyncio
    async def test_validate_file_complete(self, validator, temp_file):
        """Test complete file validation"""
        results = await validator.validate_file(
            file_path=temp_file,
            original_filename="test.txt"
        )
        
        assert results["valid"]
        assert results["file_info"]["size"] > 0
        assert "mime_type" in results["file_info"]
    
    @pytest.mark.asyncio
    async def test_validate_file_not_exists(self, validator):
        """Test validation fails for non-existent file"""
        with pytest.raises(Exception) as exc_info:
            await validator.validate_file("/path/does/not/exist.txt")
        
        assert "not found" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_calculate_file_hash(self, validator, temp_file):
        """Test file hash calculation"""
        hash_value = await validator._calculate_file_hash(temp_file)
        
        assert len(hash_value) == 64  # SHA-256 produces 64 hex characters
        assert all(c in '0123456789abcdef' for c in hash_value.lower())


class TestMediaFileValidator:
    """Test MediaFileValidator class"""
    
    @pytest.fixture
    def validator(self):
        """Create a MediaFileValidator instance"""
        return MediaFileValidator()
    
    def test_media_validator_mime_types(self, validator):
        """Test MediaFileValidator only allows media MIME types"""
        assert "video/*" in validator.rules.allowed_mime_types
        assert "audio/*" in validator.rules.allowed_mime_types
        assert "image/*" in validator.rules.allowed_mime_types
    
    @pytest.mark.asyncio
    async def test_validate_media_file(self, validator):
        """Test media file validation"""
        fd, path = tempfile.mkstemp(suffix=".mp4")
        with os.fdopen(fd, 'w') as f:
            f.write("Fake video content")
        
        try:
            results = await validator.validate_media_file(
                file_path=path,
                original_filename="video.mp4"
            )
            
            # Should have warnings about pending validation
            assert len(results["warnings"]) > 0
            assert "pending" in results["warnings"][0].lower()
        finally:
            os.unlink(path)


class TestFileValidationRules:
    """Test FileValidationRules model"""
    
    def test_normalize_extensions(self):
        """Test extension normalization"""
        rules = FileValidationRules(
            allowed_extensions=["mp4", ".jpg"],
            blocked_extensions=["exe", ".bat"]
        )
        
        assert ".mp4" in rules.allowed_extensions
        assert ".jpg" in rules.allowed_extensions
        assert ".exe" in rules.blocked_extensions
        assert ".bat" in rules.blocked_extensions
    
    def test_default_values(self):
        """Test default validation rules"""
        rules = FileValidationRules()
        
        assert rules.max_file_size == 10 * 1024 * 1024 * 1024  # 10GB
        assert rules.min_file_size == 1
        assert rules.require_extension is True
        assert rules.validate_mime_magic is True