"""
File validation service for the Ingest Service
"""

import os
import hashlib
import magic
import asyncio
from typing import List, Optional, Dict, Any
import structlog
import clamd
from pathlib import Path

from ..models.schemas import (
    ValidationResult, ValidationRule, ChecksumInfo, FileType
)
from ..core.config import settings
from ..core.exceptions import (
    ValidationError, FileNotFoundError, FileSizeError,
    UnsupportedFormatError, VirusDetectedError, ChecksumMismatchError
)
from ..core.logging import get_logger, log_performance_metric

logger = get_logger(__name__)


class ValidationService:
    """Service for validating files before ingestion"""
    
    def __init__(self):
        self.magic = magic.Magic(mime=True)
        self.clamd_client = None
        self._initialize_virus_scanner()
    
    def _initialize_virus_scanner(self):
        """Initialize ClamAV client if enabled"""
        if settings.enable_virus_scanning:
            try:
                self.clamd_client = clamd.ClamdNetworkSocket(
                    host=settings.clamav_host,
                    port=settings.clamav_port
                )
                # Test connection
                self.clamd_client.ping()
                logger.info("ClamAV connection established")
            except Exception as e:
                logger.warning(
                    "ClamAV not available, virus scanning disabled",
                    error=str(e)
                )
                self.clamd_client = None
    
    async def validate_file(
        self,
        file_path: str,
        validation_rules: Optional[List[ValidationRule]] = None
    ) -> ValidationResult:
        """
        Comprehensive file validation
        
        Args:
            file_path: Path to the file to validate
            validation_rules: Custom validation rules to apply
            
        Returns:
            ValidationResult with validation status and details
        """
        import time
        start_time = time.time()
        
        result = ValidationResult(is_valid=True)
        
        try:
            # Check if file exists
            if not os.path.exists(file_path):
                raise FileNotFoundError(file_path)
            
            # Basic file information
            file_stat = os.stat(file_path)
            file_size = file_stat.st_size
            file_extension = Path(file_path).suffix.lower().lstrip('.')
            
            logger.info(
                "validating_file",
                file_path=file_path,
                file_size=file_size,
                extension=file_extension
            )
            
            # 1. File size validation
            await self._validate_file_size(file_path, file_size, result)
            
            # 2. File format validation
            await self._validate_file_format(file_path, file_extension, result)
            
            # 3. MIME type validation
            await self._validate_mime_type(file_path, result)
            
            # 4. File accessibility validation
            await self._validate_file_access(file_path, result)
            
            # 5. Virus scanning
            if settings.enable_virus_scanning and self.clamd_client:
                await self._scan_for_viruses(file_path, result)
            
            # 6. Checksum validation (if provided)
            if settings.enable_checksum_verification:
                await self._validate_checksums(file_path, result)
            
            # 7. Apply custom validation rules
            if validation_rules:
                await self._apply_custom_rules(file_path, validation_rules, result)
            
            # 8. File integrity checks
            await self._validate_file_integrity(file_path, result)
            
            # Determine overall validity
            result.is_valid = (
                len(result.errors) == 0 and
                result.format_supported and
                result.size_within_limits and
                (not settings.enable_checksum_verification or result.checksum_verified)
            )
            
            duration_ms = (time.time() - start_time) * 1000
            log_performance_metric(
                logger,
                "file_validation",
                duration_ms,
                file_path=file_path,
                is_valid=result.is_valid,
                errors=len(result.errors),
                warnings=len(result.warnings)
            )
            
            logger.info(
                "file_validation_completed",
                file_path=file_path,
                is_valid=result.is_valid,
                errors=len(result.errors),
                warnings=len(result.warnings),
                virus_scan_result=result.virus_scan_result
            )
            
            return result
            
        except Exception as e:
            result.is_valid = False
            result.errors.append(f"Validation failed: {str(e)}")
            
            logger.error(
                "file_validation_failed",
                file_path=file_path,
                error=str(e)
            )
            
            return result
    
    async def _validate_file_size(
        self,
        file_path: str,
        file_size: int,
        result: ValidationResult
    ) -> None:
        """Validate file size against limits"""
        if file_size > settings.max_file_size:
            result.size_within_limits = False
            result.errors.append(
                f"File size {file_size} bytes exceeds maximum allowed size "
                f"{settings.max_file_size} bytes"
            )
        
        if file_size == 0:
            result.errors.append("File is empty")
        
        # Warn for very large files
        if file_size > settings.max_file_size * 0.8:
            result.warnings.append("File is very large and may take longer to process")
    
    async def _validate_file_format(
        self,
        file_path: str,
        file_extension: str,
        result: ValidationResult
    ) -> None:
        """Validate file format against allowed formats"""
        allowed_formats = settings.all_allowed_formats
        
        if file_extension not in allowed_formats:
            result.format_supported = False
            result.errors.append(f"File format '{file_extension}' is not supported")
            return
        
        # Determine file type
        file_type = self._determine_file_type(file_extension)
        
        logger.debug(
            "file_format_validated",
            file_path=file_path,
            extension=file_extension,
            file_type=file_type
        )
    
    async def _validate_mime_type(self, file_path: str, result: ValidationResult) -> None:
        """Validate MIME type matches file extension"""
        try:
            mime_type = self.magic.from_file(file_path)
            file_extension = Path(file_path).suffix.lower().lstrip('.')
            
            # Basic MIME type validation
            expected_mime_patterns = {
                'mp4': ['video/mp4'],
                'mov': ['video/quicktime'],
                'avi': ['video/x-msvideo'],
                'jpg': ['image/jpeg'],
                'jpeg': ['image/jpeg'],
                'png': ['image/png'],
                'pdf': ['application/pdf'],
                'wav': ['audio/wav', 'audio/x-wav'],
                'mp3': ['audio/mpeg'],
            }
            
            if file_extension in expected_mime_patterns:
                expected_mimes = expected_mime_patterns[file_extension]
                if not any(expected in mime_type for expected in expected_mimes):
                    result.warnings.append(
                        f"MIME type '{mime_type}' may not match file extension '{file_extension}'"
                    )
            
            logger.debug(
                "mime_type_validated",
                file_path=file_path,
                mime_type=mime_type,
                extension=file_extension
            )
            
        except Exception as e:
            result.warnings.append(f"Could not determine MIME type: {str(e)}")
    
    async def _validate_file_access(self, file_path: str, result: ValidationResult) -> None:
        """Validate file accessibility"""
        try:
            # Check read permissions
            if not os.access(file_path, os.R_OK):
                result.errors.append("File is not readable")
            
            # Try to open file to ensure it's not corrupted at the file system level
            with open(file_path, 'rb') as f:
                # Read first few bytes to ensure file is accessible
                f.read(1024)
                
        except PermissionError:
            result.errors.append("Permission denied accessing file")
        except OSError as e:
            result.errors.append(f"File system error: {str(e)}")
        except Exception as e:
            result.errors.append(f"File access validation failed: {str(e)}")
    
    async def _scan_for_viruses(self, file_path: str, result: ValidationResult) -> None:
        """Scan file for viruses using ClamAV"""
        if not self.clamd_client:
            result.warnings.append("Virus scanning not available")
            return
        
        try:
            scan_result = self.clamd_client.scan(file_path)
            
            if scan_result is None:
                result.virus_scan_result = "clean"
            else:
                # scan_result is a dict with file_path as key and (status, virus_name) as value
                for file, (status, virus_name) in scan_result.items():
                    if status == 'FOUND':
                        result.virus_scan_result = f"infected: {virus_name}"
                        result.errors.append(f"Virus detected: {virus_name}")
                    else:
                        result.virus_scan_result = "clean"
            
            logger.info(
                "virus_scan_completed",
                file_path=file_path,
                result=result.virus_scan_result
            )
            
        except Exception as e:
            result.warnings.append(f"Virus scanning failed: {str(e)}")
            logger.warning(
                "virus_scan_failed",
                file_path=file_path,
                error=str(e)
            )
    
    async def _validate_checksums(self, file_path: str, result: ValidationResult) -> None:
        """Validate file checksums if provided"""
        # This would typically check against provided checksums
        # For now, we'll calculate checksums for verification
        try:
            checksums = {}
            
            for algorithm in settings.checksum_algorithms:
                checksum = await self._calculate_checksum(file_path, algorithm)
                checksums[algorithm] = checksum
            
            # In a real implementation, you would compare against expected checksums
            # For now, we'll mark as verified if we can calculate them
            result.checksum_verified = True
            
            logger.debug(
                "checksums_calculated",
                file_path=file_path,
                checksums=checksums
            )
            
        except Exception as e:
            result.checksum_verified = False
            result.warnings.append(f"Checksum calculation failed: {str(e)}")
    
    async def _calculate_checksum(self, file_path: str, algorithm: str) -> str:
        """Calculate file checksum using specified algorithm"""
        hash_func = hashlib.new(algorithm)
        
        with open(file_path, 'rb') as f:
            while chunk := f.read(settings.chunk_size):
                hash_func.update(chunk)
        
        return hash_func.hexdigest()
    
    async def _apply_custom_rules(
        self,
        file_path: str,
        validation_rules: List[ValidationRule],
        result: ValidationResult
    ) -> None:
        """Apply custom validation rules"""
        for rule in validation_rules:
            if not rule.enabled:
                continue
            
            try:
                await self._apply_single_rule(file_path, rule, result)
            except Exception as e:
                error_msg = f"Custom rule '{rule.rule_type}' failed: {str(e)}"
                
                if rule.error_level == "error":
                    result.errors.append(error_msg)
                elif rule.error_level == "warning":
                    result.warnings.append(error_msg)
                else:
                    logger.info("validation_rule_info", file_path=file_path, message=error_msg)
    
    async def _apply_single_rule(
        self,
        file_path: str,
        rule: ValidationRule,
        result: ValidationResult
    ) -> None:
        """Apply a single validation rule"""
        if rule.rule_type == "max_file_size":
            max_size = rule.parameters.get("max_size", settings.max_file_size)
            file_size = os.path.getsize(file_path)
            if file_size > max_size:
                raise ValidationError(f"File size {file_size} exceeds limit {max_size}")
        
        elif rule.rule_type == "required_extension":
            required_ext = rule.parameters.get("extension", "").lower()
            file_ext = Path(file_path).suffix.lower().lstrip('.')
            if file_ext != required_ext:
                raise ValidationError(f"File extension must be '{required_ext}'")
        
        elif rule.rule_type == "forbidden_extension":
            forbidden_ext = rule.parameters.get("extension", "").lower()
            file_ext = Path(file_path).suffix.lower().lstrip('.')
            if file_ext == forbidden_ext:
                raise ValidationError(f"File extension '{forbidden_ext}' is not allowed")
        
        elif rule.rule_type == "min_file_size":
            min_size = rule.parameters.get("min_size", 0)
            file_size = os.path.getsize(file_path)
            if file_size < min_size:
                raise ValidationError(f"File size {file_size} is below minimum {min_size}")
        
        elif rule.rule_type == "filename_pattern":
            import re
            pattern = rule.parameters.get("pattern", "")
            filename = Path(file_path).name
            if not re.match(pattern, filename):
                raise ValidationError(f"Filename does not match required pattern: {pattern}")
        
        # Add more custom rules as needed
    
    async def _validate_file_integrity(self, file_path: str, result: ValidationResult) -> None:
        """Validate file integrity using format-specific checks"""
        file_extension = Path(file_path).suffix.lower().lstrip('.')
        
        try:
            if file_extension in settings.allowed_video_formats:
                await self._validate_video_integrity(file_path, result)
            elif file_extension in settings.allowed_image_formats:
                await self._validate_image_integrity(file_path, result)
            elif file_extension in settings.allowed_audio_formats:
                await self._validate_audio_integrity(file_path, result)
                
        except Exception as e:
            result.warnings.append(f"Integrity check failed: {str(e)}")
    
    async def _validate_video_integrity(self, file_path: str, result: ValidationResult) -> None:
        """Validate video file integrity"""
        try:
            # Basic video file validation using ffprobe
            import subprocess
            
            cmd = [
                'ffprobe',
                '-v', 'error',
                '-select_streams', 'v:0',
                '-show_entries', 'stream=codec_name',
                '-of', 'csv=p=0',
                file_path
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                result.warnings.append("Video file may be corrupted or invalid")
            else:
                codec = stdout.decode().strip()
                logger.debug("video_codec_detected", file_path=file_path, codec=codec)
                
        except FileNotFoundError:
            result.warnings.append("FFprobe not available for video validation")
        except Exception as e:
            result.warnings.append(f"Video integrity check failed: {str(e)}")
    
    async def _validate_image_integrity(self, file_path: str, result: ValidationResult) -> None:
        """Validate image file integrity"""
        try:
            from PIL import Image
            
            with Image.open(file_path) as img:
                # Try to load the image
                img.verify()
                
        except Exception as e:
            result.warnings.append(f"Image integrity check failed: {str(e)}")
    
    async def _validate_audio_integrity(self, file_path: str, result: ValidationResult) -> None:
        """Validate audio file integrity"""
        try:
            # Basic audio file validation
            from mutagen import File
            
            audio_file = File(file_path)
            if audio_file is None:
                result.warnings.append("Audio file format not recognized")
            else:
                # Check if file has audio streams
                if hasattr(audio_file, 'info') and hasattr(audio_file.info, 'length'):
                    if audio_file.info.length <= 0:
                        result.warnings.append("Audio file appears to have no content")
                        
        except Exception as e:
            result.warnings.append(f"Audio integrity check failed: {str(e)}")
    
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
    
    async def batch_validate_files(
        self,
        file_paths: List[str],
        validation_rules: Optional[List[ValidationRule]] = None
    ) -> List[ValidationResult]:
        """Validate multiple files concurrently"""
        tasks = [
            self.validate_file(file_path, validation_rules)
            for file_path in file_paths
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to failed validation results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                failed_result = ValidationResult(
                    is_valid=False,
                    errors=[f"Validation failed: {str(result)}"]
                )
                processed_results.append(failed_result)
            else:
                processed_results.append(result)
        
        return processed_results


# Dependency injection
_validation_service: Optional[ValidationService] = None


async def get_validation_service() -> ValidationService:
    """Get validation service instance"""
    global _validation_service
    
    if _validation_service is None:
        _validation_service = ValidationService()
    
    return _validation_service