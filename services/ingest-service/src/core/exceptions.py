"""
Custom exceptions for the Ingest Service
"""

from typing import Optional, Dict, Any


class IngestServiceError(Exception):
    """Base exception for Ingest Service"""
    
    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: str = "INGEST_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(IngestServiceError):
    """Raised when file validation fails"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=400,
            error_code="VALIDATION_ERROR",
            details=details
        )


class FileNotFoundError(IngestServiceError):
    """Raised when a file cannot be found"""
    
    def __init__(self, file_path: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"File not found: {file_path}",
            status_code=404,
            error_code="FILE_NOT_FOUND",
            details=details
        )


class FileAccessError(IngestServiceError):
    """Raised when file access is denied"""
    
    def __init__(self, file_path: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Access denied to file: {file_path}",
            status_code=403,
            error_code="FILE_ACCESS_DENIED",
            details=details
        )


class FileSizeError(IngestServiceError):
    """Raised when file size exceeds limits"""
    
    def __init__(self, file_size: int, max_size: int, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"File size {file_size} exceeds maximum allowed size {max_size}",
            status_code=413,
            error_code="FILE_SIZE_EXCEEDED",
            details=details
        )


class UnsupportedFormatError(IngestServiceError):
    """Raised when file format is not supported"""
    
    def __init__(self, file_format: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Unsupported file format: {file_format}",
            status_code=415,
            error_code="UNSUPPORTED_FORMAT",
            details=details
        )


class VirusDetectedError(IngestServiceError):
    """Raised when a virus is detected in a file"""
    
    def __init__(self, file_path: str, virus_name: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Virus detected in file {file_path}: {virus_name}",
            status_code=422,
            error_code="VIRUS_DETECTED",
            details=details
        )


class ChecksumMismatchError(IngestServiceError):
    """Raised when file checksum verification fails"""
    
    def __init__(self, expected: str, actual: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Checksum mismatch - expected: {expected}, actual: {actual}",
            status_code=422,
            error_code="CHECKSUM_MISMATCH",
            details=details
        )


class StorageError(IngestServiceError):
    """Raised when storage operations fail"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Storage error: {message}",
            status_code=502,
            error_code="STORAGE_ERROR",
            details=details
        )


class MetadataExtractionError(IngestServiceError):
    """Raised when metadata extraction fails"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Metadata extraction error: {message}",
            status_code=422,
            error_code="METADATA_EXTRACTION_ERROR",
            details=details
        )


class ProcessingError(IngestServiceError):
    """Raised when file processing fails"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Processing error: {message}",
            status_code=422,
            error_code="PROCESSING_ERROR",
            details=details
        )


class QueueError(IngestServiceError):
    """Raised when message queue operations fail"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Queue error: {message}",
            status_code=502,
            error_code="QUEUE_ERROR",
            details=details
        )


class CameraCardError(IngestServiceError):
    """Raised when camera card processing fails"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Camera card error: {message}",
            status_code=422,
            error_code="CAMERA_CARD_ERROR",
            details=details
        )


class SpannedClipError(IngestServiceError):
    """Raised when spanned clip processing fails"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Spanned clip error: {message}",
            status_code=422,
            error_code="SPANNED_CLIP_ERROR",
            details=details
        )


class LiveIngestError(IngestServiceError):
    """Raised when live ingest operations fail"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Live ingest error: {message}",
            status_code=422,
            error_code="LIVE_INGEST_ERROR",
            details=details
        )


class WatchFolderError(IngestServiceError):
    """Raised when watch folder operations fail"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Watch folder error: {message}",
            status_code=422,
            error_code="WATCH_FOLDER_ERROR",
            details=details
        )


class HotFolderError(IngestServiceError):
    """Raised when hot folder operations fail"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Hot folder error: {message}",
            status_code=422,
            error_code="HOT_FOLDER_ERROR",
            details=details
        )


class SchedulerError(IngestServiceError):
    """Raised when scheduler operations fail"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Scheduler error: {message}",
            status_code=422,
            error_code="SCHEDULER_ERROR",
            details=details
        )