"""
Custom exceptions for the Search Engine Service
"""

from datetime import datetime
from typing import Any, Dict, Optional


class SearchEngineError(Exception):
    """Base exception for search engine errors"""
    
    def __init__(
        self,
        message: str,
        error_code: str = "SEARCH_ENGINE_ERROR",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        self.timestamp = datetime.utcnow()
        super().__init__(self.message)


class IndexError(SearchEngineError):
    """Exception raised for index-related errors"""
    
    def __init__(self, message: str, index_name: str = None, **kwargs):
        super().__init__(
            message=message,
            error_code="INDEX_ERROR",
            status_code=500,
            **kwargs
        )
        if index_name:
            self.details["index_name"] = index_name


class IndexNotFoundError(IndexError):
    """Exception raised when an index is not found"""
    
    def __init__(self, index_name: str, **kwargs):
        super().__init__(
            message=f"Index '{index_name}' not found",
            error_code="INDEX_NOT_FOUND",
            status_code=404,
            index_name=index_name,
            **kwargs
        )


class IndexAlreadyExistsError(IndexError):
    """Exception raised when trying to create an existing index"""
    
    def __init__(self, index_name: str, **kwargs):
        super().__init__(
            message=f"Index '{index_name}' already exists",
            error_code="INDEX_ALREADY_EXISTS",
            status_code=409,
            index_name=index_name,
            **kwargs
        )


class SearchError(SearchEngineError):
    """Exception raised for search-related errors"""
    
    def __init__(self, message: str, query: str = None, **kwargs):
        super().__init__(
            message=message,
            error_code="SEARCH_ERROR",
            status_code=400,
            **kwargs
        )
        if query:
            self.details["query"] = query


class SearchTimeoutError(SearchError):
    """Exception raised when search times out"""
    
    def __init__(self, query: str = None, timeout: int = None, **kwargs):
        message = "Search request timed out"
        if timeout:
            message += f" after {timeout} seconds"
        
        super().__init__(
            message=message,
            error_code="SEARCH_TIMEOUT",
            status_code=408,
            query=query,
            **kwargs
        )
        if timeout:
            self.details["timeout"] = timeout


class InvalidQueryError(SearchError):
    """Exception raised for invalid search queries"""
    
    def __init__(self, message: str, query: str = None, **kwargs):
        super().__init__(
            message=message,
            error_code="INVALID_QUERY",
            status_code=400,
            query=query,
            **kwargs
        )


class IndexingError(SearchEngineError):
    """Exception raised for indexing errors"""
    
    def __init__(self, message: str, document_id: str = None, **kwargs):
        super().__init__(
            message=message,
            error_code="INDEXING_ERROR",
            status_code=500,
            **kwargs
        )
        if document_id:
            self.details["document_id"] = document_id


class BulkIndexingError(IndexingError):
    """Exception raised for bulk indexing errors"""
    
    def __init__(self, message: str, failed_count: int = None, **kwargs):
        super().__init__(
            message=message,
            error_code="BULK_INDEXING_ERROR",
            status_code=500,
            **kwargs
        )
        if failed_count is not None:
            self.details["failed_count"] = failed_count


class ConnectionError(SearchEngineError):
    """Exception raised for OpenSearch connection errors"""
    
    def __init__(self, message: str, host: str = None, **kwargs):
        super().__init__(
            message=message,
            error_code="CONNECTION_ERROR",
            status_code=503,
            **kwargs
        )
        if host:
            self.details["host"] = host


class AuthenticationError(SearchEngineError):
    """Exception raised for authentication errors"""
    
    def __init__(self, message: str = "Authentication failed", **kwargs):
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_ERROR",
            status_code=401,
            **kwargs
        )


class AuthorizationError(SearchEngineError):
    """Exception raised for authorization errors"""
    
    def __init__(self, message: str = "Access denied", **kwargs):
        super().__init__(
            message=message,
            error_code="AUTHORIZATION_ERROR",
            status_code=403,
            **kwargs
        )


class ValidationError(SearchEngineError):
    """Exception raised for validation errors"""
    
    def __init__(self, message: str, field: str = None, **kwargs):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            status_code=422,
            **kwargs
        )
        if field:
            self.details["field"] = field


class NotFoundError(SearchEngineError):
    """Exception raised when a resource is not found"""
    
    def __init__(self, message: str, resource_id: str = None, **kwargs):
        super().__init__(
            message=message,
            error_code="NOT_FOUND",
            status_code=404,
            **kwargs
        )
        if resource_id:
            self.details["resource_id"] = resource_id


class ConfigurationError(SearchEngineError):
    """Exception raised for configuration errors"""
    
    def __init__(self, message: str, setting: str = None, **kwargs):
        super().__init__(
            message=message,
            error_code="CONFIGURATION_ERROR",
            status_code=500,
            **kwargs
        )
        if setting:
            self.details["setting"] = setting