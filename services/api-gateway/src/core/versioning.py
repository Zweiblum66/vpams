"""
API Versioning System

Provides flexible API versioning support with multiple strategies:
- URL path versioning (default): /api/v1/resource
- Header versioning: API-Version: 1
- Query parameter versioning: ?version=1
- Content negotiation: Accept: application/vnd.mams.v1+json
"""

from typing import Dict, Any, Optional, List, Tuple, Union
from enum import Enum
from fastapi import Request, HTTPException, status
from pydantic import BaseModel, Field
import re
from datetime import datetime, date
import logging

from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class VersioningStrategy(Enum):
    """API versioning strategies"""
    URL_PATH = "url_path"
    HEADER = "header"
    QUERY_PARAM = "query_param"
    ACCEPT_HEADER = "accept_header"


class APIVersion:
    """Represents an API version"""
    
    def __init__(self, version: Union[str, int, float]):
        """
        Initialize API version
        
        Args:
            version: Version string (e.g., "1", "1.0", "v1", "v1.0")
        """
        # Clean and parse version
        version_str = str(version).lower().strip()
        
        # Remove 'v' prefix if present
        if version_str.startswith('v'):
            version_str = version_str[1:]
        
        # Parse version components
        parts = version_str.split('.')
        
        try:
            self.major = int(parts[0])
            self.minor = int(parts[1]) if len(parts) > 1 else 0
            self.patch = int(parts[2]) if len(parts) > 2 else 0
        except (ValueError, IndexError):
            raise ValueError(f"Invalid version format: {version}")
    
    def __str__(self) -> str:
        """String representation"""
        if self.patch > 0:
            return f"v{self.major}.{self.minor}.{self.patch}"
        elif self.minor > 0:
            return f"v{self.major}.{self.minor}"
        else:
            return f"v{self.major}"
    
    def __eq__(self, other) -> bool:
        """Equality comparison"""
        if not isinstance(other, APIVersion):
            return False
        return (self.major == other.major and 
                self.minor == other.minor and 
                self.patch == other.patch)
    
    def __lt__(self, other) -> bool:
        """Less than comparison"""
        if not isinstance(other, APIVersion):
            return NotImplemented
        
        if self.major != other.major:
            return self.major < other.major
        if self.minor != other.minor:
            return self.minor < other.minor
        return self.patch < other.patch
    
    def __le__(self, other) -> bool:
        """Less than or equal comparison"""
        return self == other or self < other
    
    def is_compatible_with(self, other: 'APIVersion') -> bool:
        """
        Check if this version is compatible with another version
        
        Uses semantic versioning rules:
        - Major version must match
        - Minor version can be higher (backwards compatible)
        - Patch version can be higher (bug fixes)
        """
        if self.major != other.major:
            return False
        
        if self.minor < other.minor:
            return False
        
        if self.minor == other.minor and self.patch < other.patch:
            return False
        
        return True


class VersionConfig(BaseModel):
    """Version configuration"""
    version: str = Field(..., description="Version identifier")
    status: str = Field("stable", description="Version status: stable, beta, deprecated")
    deprecated: bool = Field(False, description="Whether version is deprecated")
    deprecation_date: Optional[date] = Field(None, description="Date when version will be removed")
    min_client_version: Optional[str] = Field(None, description="Minimum client version supported")
    features: List[str] = Field(default_factory=list, description="Features available in this version")
    breaking_changes: List[str] = Field(default_factory=list, description="Breaking changes from previous version")


class VersionRegistry:
    """Registry for API versions"""
    
    def __init__(self):
        self.versions: Dict[str, VersionConfig] = {}
        self.current_version: Optional[APIVersion] = None
        self.default_version: Optional[APIVersion] = None
        self.supported_versions: List[APIVersion] = []
        
        # Initialize with default versions
        self._initialize_versions()
    
    def _initialize_versions(self):
        """Initialize default API versions"""
        # Version 1 - Initial release
        self.register_version(VersionConfig(
            version="1",
            status="stable",
            features=[
                "Basic CRUD operations",
                "JWT authentication",
                "Rate limiting",
                "Health checks"
            ]
        ))
        
        # Version 2 - Future release
        self.register_version(VersionConfig(
            version="2",
            status="beta",
            features=[
                "All v1 features",
                "GraphQL support",
                "WebSocket subscriptions",
                "Advanced search"
            ],
            breaking_changes=[
                "Changed authentication header format",
                "Renamed some endpoints",
                "Modified response structure"
            ]
        ))
        
        # Set current and default versions
        self.current_version = APIVersion("2")
        self.default_version = APIVersion("1")
    
    def register_version(self, config: VersionConfig):
        """Register a new API version"""
        version = APIVersion(config.version)
        self.versions[str(version)] = config
        self.supported_versions.append(version)
        self.supported_versions.sort()
    
    def get_version_config(self, version: Union[str, APIVersion]) -> Optional[VersionConfig]:
        """Get configuration for a specific version"""
        if isinstance(version, str):
            version = APIVersion(version)
        return self.versions.get(str(version))
    
    def is_version_supported(self, version: Union[str, APIVersion]) -> bool:
        """Check if a version is supported"""
        if isinstance(version, str):
            try:
                version = APIVersion(version)
            except ValueError:
                return False
        return str(version) in self.versions
    
    def is_version_deprecated(self, version: Union[str, APIVersion]) -> bool:
        """Check if a version is deprecated"""
        config = self.get_version_config(version)
        return config.deprecated if config else False
    
    def get_deprecation_info(self, version: Union[str, APIVersion]) -> Optional[Dict[str, Any]]:
        """Get deprecation information for a version"""
        config = self.get_version_config(version)
        if config and config.deprecated:
            return {
                "deprecated": True,
                "deprecation_date": config.deprecation_date.isoformat() if config.deprecation_date else None,
                "message": f"API version {version} is deprecated and will be removed on {config.deprecation_date}"
            }
        return None


class VersionExtractor:
    """Extract API version from requests"""
    
    def __init__(self, strategy: VersioningStrategy = VersioningStrategy.URL_PATH):
        self.strategy = strategy
        self.header_name = settings.api_version_header if hasattr(settings, 'api_version_header') else "API-Version"
        self.query_param = settings.api_version_param if hasattr(settings, 'api_version_param') else "version"
        self.accept_pattern = re.compile(r'application/vnd\.mams\.v(\d+(?:\.\d+)?)\+json')
    
    async def extract_version(self, request: Request) -> Optional[APIVersion]:
        """
        Extract API version from request
        
        Args:
            request: FastAPI request object
            
        Returns:
            Extracted API version or None
        """
        version_str = None
        
        if self.strategy == VersioningStrategy.URL_PATH:
            version_str = self._extract_from_url(request)
        
        elif self.strategy == VersioningStrategy.HEADER:
            version_str = self._extract_from_header(request)
        
        elif self.strategy == VersioningStrategy.QUERY_PARAM:
            version_str = self._extract_from_query(request)
        
        elif self.strategy == VersioningStrategy.ACCEPT_HEADER:
            version_str = self._extract_from_accept_header(request)
        
        if version_str:
            try:
                return APIVersion(version_str)
            except ValueError:
                logger.warning(f"Invalid version format: {version_str}")
                return None
        
        return None
    
    def _extract_from_url(self, request: Request) -> Optional[str]:
        """Extract version from URL path"""
        # Match patterns like /api/v1/... or /v1/...
        path = request.url.path
        
        # Try /api/vX pattern
        match = re.search(r'/api/v(\d+(?:\.\d+)?)', path)
        if match:
            return match.group(1)
        
        # Try /vX pattern
        match = re.search(r'^/v(\d+(?:\.\d+)?)', path)
        if match:
            return match.group(1)
        
        return None
    
    def _extract_from_header(self, request: Request) -> Optional[str]:
        """Extract version from custom header"""
        return request.headers.get(self.header_name)
    
    def _extract_from_query(self, request: Request) -> Optional[str]:
        """Extract version from query parameter"""
        return request.query_params.get(self.query_param)
    
    def _extract_from_accept_header(self, request: Request) -> Optional[str]:
        """Extract version from Accept header using content negotiation"""
        accept_header = request.headers.get("Accept", "")
        match = self.accept_pattern.search(accept_header)
        
        if match:
            return match.group(1)
        
        return None


class VersionRouter:
    """Route requests to version-specific handlers"""
    
    def __init__(self, registry: VersionRegistry):
        self.registry = registry
        self.version_handlers: Dict[str, Dict[str, Any]] = {}
    
    def register_handler(
        self,
        version: Union[str, APIVersion],
        path: str,
        handler: callable,
        methods: List[str] = None
    ):
        """Register a version-specific handler"""
        if isinstance(version, str):
            version = APIVersion(version)
        
        version_str = str(version)
        
        if version_str not in self.version_handlers:
            self.version_handlers[version_str] = {}
        
        key = f"{path}:{','.join(methods or ['*'])}"
        self.version_handlers[version_str][key] = handler
    
    async def route_request(
        self,
        request: Request,
        version: APIVersion,
        path: str
    ) -> Any:
        """Route request to appropriate version handler"""
        # Check if version is supported
        if not self.registry.is_version_supported(version):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"API version {version} is not supported"
            )
        
        # Check if version is deprecated
        deprecation_info = self.registry.get_deprecation_info(version)
        if deprecation_info:
            # Add deprecation headers to response
            request.state.deprecation_warning = deprecation_info["message"]
        
        # Find handler for this version
        version_str = str(version)
        
        # Look for exact match first
        if version_str in self.version_handlers:
            handlers = self.version_handlers[version_str]
            
            # Try to find matching handler
            for key, handler in handlers.items():
                handler_path, handler_methods = key.split(':')
                
                if self._path_matches(path, handler_path):
                    if handler_methods == '*' or request.method in handler_methods.split(','):
                        return await handler(request)
        
        # If no exact match, try to find compatible version
        for v in reversed(self.registry.supported_versions):
            if v <= version and str(v) in self.version_handlers:
                # Found a compatible older version
                return await self.route_request(request, v, path)
        
        # No handler found
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No handler found for {request.method} {path} in API version {version}"
        )
    
    def _path_matches(self, request_path: str, handler_path: str) -> bool:
        """Check if request path matches handler path pattern"""
        # Simple exact match for now
        # TODO: Implement pattern matching for parametrized paths
        return request_path == handler_path


# Global instances
version_registry = VersionRegistry()
version_extractor = VersionExtractor()
version_router = VersionRouter(version_registry)


# Convenience functions
def get_supported_versions() -> List[str]:
    """Get list of supported API versions"""
    return [str(v) for v in version_registry.supported_versions]


def get_current_version() -> str:
    """Get current API version"""
    return str(version_registry.current_version)


def get_default_version() -> str:
    """Get default API version"""
    return str(version_registry.default_version)


async def extract_request_version(request: Request) -> APIVersion:
    """Extract API version from request with fallback to default"""
    version = await version_extractor.extract_version(request)
    
    if version is None:
        version = version_registry.default_version
    
    return version