"""
File validation module for Asset Management Service

This module provides comprehensive file validation functionality.
"""

import os
import magic
import hashlib
import mimetypes
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
import structlog
from pydantic import BaseModel, Field, validator

from .config import get_settings
from .exceptions import ValidationError
from ..services.virus_scanner import get_virus_scanner

logger = structlog.get_logger()


class FileValidationRules(BaseModel):
    """File validation rules configuration"""
    max_file_size: int = Field(default=10 * 1024 * 1024 * 1024)  # 10GB
    min_file_size: int = Field(default=1)  # 1 byte
    allowed_mime_types: List[str] = Field(default_factory=list)
    blocked_mime_types: List[str] = Field(default_factory=list)
    allowed_extensions: List[str] = Field(default_factory=list)
    blocked_extensions: List[str] = Field(default_factory=list)
    require_extension: bool = Field(default=True)
    validate_mime_magic: bool = Field(default=True)
    check_file_signature: bool = Field(default=True)
    enable_virus_scan: bool = Field(default=True)
    
    @validator('allowed_extensions', 'blocked_extensions')
    def normalize_extensions(cls, v):
        """Ensure extensions start with dot"""
        return [ext if ext.startswith('.') else f'.{ext}' for ext in v]


class FileValidator:
    """Comprehensive file validation"""
    
    def __init__(self, rules: Optional[FileValidationRules] = None):
        self.settings = get_settings()
        self.rules = rules or self._get_default_rules()
        self._magic = None
    
    @property
    def magic_detector(self):
        """Lazy load python-magic"""
        if self._magic is None:
            self._magic = magic.Magic(mime=True)
        return self._magic
    
    def _get_default_rules(self) -> FileValidationRules:
        """Get default validation rules from settings"""
        return FileValidationRules(
            max_file_size=self.settings.max_upload_size,
            allowed_mime_types=self.settings.allowed_mime_types,
            allowed_extensions=[
                # Video
                '.mp4', '.mov', '.avi', '.mkv', '.webm', '.mxf', '.mpg', '.mpeg',
                '.m4v', '.wmv', '.flv', '.f4v', '.3gp', '.3g2', '.ts', '.m2ts',
                # Audio
                '.mp3', '.wav', '.aac', '.flac', '.ogg', '.m4a', '.wma', '.aiff',
                '.alac', '.opus', '.ac3', '.dts',
                # Image
                '.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff', '.tif',
                '.svg', '.ico', '.heic', '.heif', '.raw', '.cr2', '.nef', '.arw',
                # Document
                '.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt', '.xls', '.xlsx',
                '.ppt', '.pptx', '.csv',
                # Subtitle
                '.srt', '.vtt', '.sub', '.ass', '.ssa', '.sbv',
                # Project
                '.prproj', '.aep', '.fcpx', '.dproj', '.sesx',
                # Archive
                '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2'
            ],
            blocked_extensions=[
                '.exe', '.bat', '.cmd', '.com', '.scr', '.vbs', '.js', '.jar',
                '.app', '.dmg', '.pkg', '.deb', '.rpm', '.msi', '.ps1'
            ]
        )
    
    async def validate_file(
        self,
        file_path: str,
        original_filename: Optional[str] = None,
        expected_size: Optional[int] = None,
        expected_hash: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Perform comprehensive file validation
        
        Args:
            file_path: Path to the file to validate
            original_filename: Original filename for extension checking
            expected_size: Expected file size in bytes
            expected_hash: Expected file hash (SHA-256)
            
        Returns:
            Validation results dictionary
            
        Raises:
            ValidationError: If validation fails
        """
        results = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "file_info": {}
        }
        
        try:
            # Check file existence
            if not os.path.exists(file_path):
                raise ValidationError(f"File not found: {file_path}")
            
            # Get file info
            file_stat = os.stat(file_path)
            file_size = file_stat.st_size
            
            results["file_info"]["size"] = file_size
            results["file_info"]["path"] = file_path
            
            # Validate file size
            self._validate_file_size(file_size, results)
            
            # Validate filename and extension
            if original_filename:
                self._validate_filename(original_filename, results)
            
            # Detect and validate MIME type
            mime_type = await self._detect_mime_type(file_path)
            results["file_info"]["mime_type"] = mime_type
            self._validate_mime_type(mime_type, results)
            
            # Validate file signature
            if self.rules.check_file_signature:
                await self._validate_file_signature(file_path, mime_type, results)
            
            # Verify expected size
            if expected_size is not None and file_size != expected_size:
                results["errors"].append(
                    f"File size mismatch. Expected: {expected_size}, Actual: {file_size}"
                )
                results["valid"] = False
            
            # Verify checksum
            if expected_hash:
                actual_hash = await self._calculate_file_hash(file_path)
                results["file_info"]["hash"] = actual_hash
                
                if actual_hash.lower() != expected_hash.lower():
                    results["errors"].append("File checksum mismatch")
                    results["valid"] = False
            
            # Check for potential security issues
            await self._security_checks(file_path, original_filename, results)
            
            # Perform virus scan if enabled
            if self.rules.enable_virus_scan:
                await self._virus_scan(file_path, original_filename, results)
            
        except ValidationError:
            raise
        except Exception as e:
            logger.error("file_validation_error", error=str(e), file_path=file_path)
            results["errors"].append(f"Validation error: {str(e)}")
            results["valid"] = False
        
        # Log validation results
        if not results["valid"]:
            logger.warning(
                "file_validation_failed",
                file_path=file_path,
                errors=results["errors"]
            )
        
        return results
    
    def _validate_file_size(self, file_size: int, results: Dict[str, Any]):
        """Validate file size against rules"""
        if file_size < self.rules.min_file_size:
            results["errors"].append(
                f"File too small. Minimum size: {self.rules.min_file_size} bytes"
            )
            results["valid"] = False
        
        if file_size > self.rules.max_file_size:
            results["errors"].append(
                f"File too large. Maximum size: {self.rules.max_file_size} bytes"
            )
            results["valid"] = False
    
    def _validate_filename(self, filename: str, results: Dict[str, Any]):
        """Validate filename and extension"""
        path = Path(filename)
        extension = path.suffix.lower()
        
        results["file_info"]["filename"] = filename
        results["file_info"]["extension"] = extension
        
        # Check for extension
        if self.rules.require_extension and not extension:
            results["errors"].append("File must have an extension")
            results["valid"] = False
            return
        
        # Check allowed extensions
        if self.rules.allowed_extensions and extension not in self.rules.allowed_extensions:
            results["errors"].append(f"File extension '{extension}' is not allowed")
            results["valid"] = False
        
        # Check blocked extensions
        if extension in self.rules.blocked_extensions:
            results["errors"].append(f"File extension '{extension}' is blocked")
            results["valid"] = False
        
        # Check for suspicious patterns
        if '..' in filename or filename.startswith('.'):
            results["warnings"].append("Filename contains suspicious patterns")
        
        # Check for multiple extensions
        parts = path.stem.split('.')
        if len(parts) > 1:
            results["warnings"].append("Filename contains multiple extensions")
    
    async def _detect_mime_type(self, file_path: str) -> str:
        """Detect MIME type using multiple methods"""
        mime_type = None
        
        # Try python-magic first (most reliable)
        if self.rules.validate_mime_magic:
            try:
                mime_type = self.magic_detector.from_file(file_path)
            except Exception as e:
                logger.warning("magic_mime_detection_failed", error=str(e))
        
        # Fallback to mimetypes module
        if not mime_type:
            mime_type, _ = mimetypes.guess_type(file_path)
        
        return mime_type or 'application/octet-stream'
    
    def _validate_mime_type(self, mime_type: str, results: Dict[str, Any]):
        """Validate MIME type against rules"""
        # Check allowed MIME types
        if self.rules.allowed_mime_types:
            # Support wildcard patterns like "video/*"
            allowed = False
            for allowed_type in self.rules.allowed_mime_types:
                if allowed_type.endswith('/*'):
                    prefix = allowed_type[:-2]
                    if mime_type.startswith(prefix):
                        allowed = True
                        break
                elif mime_type == allowed_type:
                    allowed = True
                    break
            
            if not allowed:
                results["errors"].append(f"MIME type '{mime_type}' is not allowed")
                results["valid"] = False
        
        # Check blocked MIME types
        for blocked_type in self.rules.blocked_mime_types:
            if blocked_type.endswith('/*'):
                prefix = blocked_type[:-2]
                if mime_type.startswith(prefix):
                    results["errors"].append(f"MIME type '{mime_type}' is blocked")
                    results["valid"] = False
                    break
            elif mime_type == blocked_type:
                results["errors"].append(f"MIME type '{mime_type}' is blocked")
                results["valid"] = False
                break
    
    async def _validate_file_signature(
        self,
        file_path: str,
        mime_type: str,
        results: Dict[str, Any]
    ):
        """Validate file signature matches MIME type"""
        # Define common file signatures
        signatures = {
            'image/jpeg': [b'\xff\xd8\xff'],
            'image/png': [b'\x89\x50\x4e\x47'],
            'image/gif': [b'GIF87a', b'GIF89a'],
            'application/pdf': [b'%PDF'],
            'video/mp4': [b'\x00\x00\x00\x18\x66\x74\x79\x70', b'\x00\x00\x00\x20\x66\x74\x79\x70'],
            'video/avi': [b'RIFF'],
            'audio/mpeg': [b'\xff\xfb', b'\xff\xf3', b'\xff\xf2', b'ID3'],
            'application/zip': [b'PK\x03\x04', b'PK\x05\x06', b'PK\x07\x08'],
        }
        
        # Get expected signatures for MIME type
        expected_sigs = signatures.get(mime_type, [])
        if not expected_sigs:
            return  # No signature check for this type
        
        # Read file header
        try:
            with open(file_path, 'rb') as f:
                header = f.read(64)  # Read first 64 bytes
            
            # Check if header matches any expected signature
            valid_signature = False
            for sig in expected_sigs:
                if header.startswith(sig):
                    valid_signature = True
                    break
            
            if not valid_signature:
                results["warnings"].append(
                    f"File signature doesn't match MIME type '{mime_type}'"
                )
        except Exception as e:
            logger.warning("file_signature_check_failed", error=str(e))
    
    async def _calculate_file_hash(self, file_path: str, algorithm: str = 'sha256') -> str:
        """Calculate file hash"""
        hash_func = hashlib.new(algorithm)
        
        with open(file_path, 'rb') as f:
            while chunk := f.read(8192):
                hash_func.update(chunk)
        
        return hash_func.hexdigest()
    
    async def _security_checks(
        self,
        file_path: str,
        filename: Optional[str],
        results: Dict[str, Any]
    ):
        """Perform security-related checks"""
        # Check for embedded executables in archives
        if filename and any(filename.lower().endswith(ext) for ext in ['.zip', '.rar', '.7z']):
            results["warnings"].append("Archive files should be scanned for malicious content")
        
        # Check for disguised executables
        if filename:
            # Check for RTLO (Right-to-Left Override) character
            if '\u202e' in filename:
                results["errors"].append("Filename contains RTLO character (potential security risk)")
                results["valid"] = False
            
            # Check for null bytes
            if '\x00' in filename:
                results["errors"].append("Filename contains null bytes")
                results["valid"] = False
        
        # Check file permissions (Unix-like systems)
        try:
            stat_info = os.stat(file_path)
            if stat_info.st_mode & 0o111:  # Check if executable
                results["warnings"].append("File has executable permissions")
        except:
            pass
    
    async def _virus_scan(
        self,
        file_path: str,
        filename: Optional[str],
        results: Dict[str, Any]
    ):
        """Perform virus scan on file"""
        try:
            virus_scanner = get_virus_scanner()
            scan_result = await virus_scanner.scan_file(
                file_path=file_path,
                filename=filename,
                fail_on_error=False  # Don't raise exception, add to validation results
            )
            
            if scan_result:
                results["file_info"]["virus_scan"] = scan_result.to_dict()
                
                if not scan_result.clean:
                    results["errors"].append(
                        f"Virus detected: {scan_result.threat_name} (scanner: {scan_result.scanner_name})"
                    )
                    results["valid"] = False
                else:
                    logger.info(
                        "file_virus_scan_clean",
                        file_path=file_path,
                        scanner=scan_result.scanner_name,
                        scan_time=scan_result.scan_time
                    )
            else:
                results["warnings"].append("Virus scan was skipped or unavailable")
                
        except ValidationError as e:
            # Virus detected
            results["errors"].append(str(e))
            results["valid"] = False
        except Exception as e:
            logger.error("virus_scan_error", error=str(e), file_path=file_path)
            results["warnings"].append(f"Virus scan failed: {str(e)}")


class MediaFileValidator(FileValidator):
    """Specialized validator for media files"""
    
    def __init__(self):
        super().__init__()
        # Add media-specific validation rules
        self.rules.allowed_mime_types = [
            'video/*', 'audio/*', 'image/*'
        ]
    
    async def validate_media_file(
        self,
        file_path: str,
        original_filename: str,
        expected_duration: Optional[float] = None
    ) -> Dict[str, Any]:
        """Validate media file with additional media-specific checks"""
        # Perform base validation
        results = await self.validate_file(file_path, original_filename)
        
        if not results["valid"]:
            return results
        
        # Add media-specific validation
        mime_type = results["file_info"]["mime_type"]
        
        if mime_type.startswith('video/'):
            await self._validate_video_file(file_path, results)
        elif mime_type.startswith('audio/'):
            await self._validate_audio_file(file_path, results)
        elif mime_type.startswith('image/'):
            await self._validate_image_file(file_path, results)
        
        return results
    
    async def _validate_video_file(self, file_path: str, results: Dict[str, Any]):
        """Validate video file properties"""
        # TODO: Use FFprobe to validate video properties
        results["warnings"].append("Video validation pending FFmpeg integration")
    
    async def _validate_audio_file(self, file_path: str, results: Dict[str, Any]):
        """Validate audio file properties"""
        # TODO: Use FFprobe to validate audio properties
        results["warnings"].append("Audio validation pending FFmpeg integration")
    
    async def _validate_image_file(self, file_path: str, results: Dict[str, Any]):
        """Validate image file properties"""
        # TODO: Use PIL/Pillow to validate image properties
        results["warnings"].append("Image validation pending PIL integration")