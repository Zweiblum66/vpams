"""
Custom exceptions for the Proxy Generation Service
"""

from typing import Optional, Dict, Any


class ProxyGenerationError(Exception):
    """Base exception for proxy generation errors"""
    
    def __init__(
        self,
        message: str,
        error_code: str = "PROXY_ERROR",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class FFmpegError(ProxyGenerationError):
    """FFmpeg processing error"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="FFMPEG_ERROR",
            status_code=500,
            details=details
        )


class InvalidMediaError(ProxyGenerationError):
    """Invalid media file error"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="INVALID_MEDIA",
            status_code=400,
            details=details
        )


class StorageError(ProxyGenerationError):
    """Storage operation error"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="STORAGE_ERROR",
            status_code=500,
            details=details
        )


class QueueError(ProxyGenerationError):
    """Queue operation error"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="QUEUE_ERROR",
            status_code=500,
            details=details
        )


class ProcessingTimeoutError(ProxyGenerationError):
    """Processing timeout error"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="PROCESSING_TIMEOUT",
            status_code=504,
            details=details
        )