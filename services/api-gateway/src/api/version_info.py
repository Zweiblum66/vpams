"""
API Version Information Endpoints

Provides endpoints for API version discovery and migration guidance.
"""

from typing import Dict, Any, List
from fastapi import APIRouter, Request, Depends
from pydantic import BaseModel, Field

from core.versioning import (
    get_supported_versions,
    get_current_version,
    get_default_version,
    version_registry,
    APIVersion
)
from api.dependencies import get_current_user

router = APIRouter(prefix="/api", tags=["version-info"])


class VersionInfo(BaseModel):
    """Version information model"""
    version: str = Field(..., description="Version identifier")
    status: str = Field(..., description="Version status")
    deprecated: bool = Field(..., description="Whether version is deprecated")
    deprecation_date: str = Field(None, description="Deprecation date")
    features: List[str] = Field(..., description="Features in this version")
    breaking_changes: List[str] = Field(..., description="Breaking changes from previous version")


class VersionResponse(BaseModel):
    """Version information response"""
    current_version: str = Field(..., description="Current API version")
    default_version: str = Field(..., description="Default API version")
    requested_version: str = Field(None, description="Version used for this request")
    supported_versions: List[VersionInfo] = Field(..., description="All supported versions")
    versioning_strategy: str = Field(..., description="How versions are determined")
    documentation_url: str = Field(..., description="Link to versioning documentation")


@router.get("/version", response_model=VersionResponse)
async def get_version_info(request: Request):
    """
    Get API version information
    
    Returns information about all supported API versions,
    the current version, and versioning strategy.
    """
    # Get version from request if available
    requested_version = None
    if hasattr(request.state, 'api_version'):
        requested_version = str(request.state.api_version)
    
    # Build version information
    versions_info = []
    for version in get_supported_versions():
        config = version_registry.get_version_config(version)
        if config:
            versions_info.append(VersionInfo(
                version=version,
                status=config.status,
                deprecated=config.deprecated,
                deprecation_date=config.deprecation_date.isoformat() if config.deprecation_date else None,
                features=config.features,
                breaking_changes=config.breaking_changes
            ))
    
    return VersionResponse(
        current_version=get_current_version(),
        default_version=get_default_version(),
        requested_version=requested_version,
        supported_versions=versions_info,
        versioning_strategy="URL path versioning (/api/v1/, /api/v2/)",
        documentation_url="/docs/api-versioning"
    )


@router.get("/versions")
async def list_versions():
    """
    List all API versions
    
    Simple endpoint that returns a list of supported versions.
    """
    return {
        "versions": get_supported_versions(),
        "current": get_current_version(),
        "default": get_default_version()
    }


@router.get("/version/metrics")
async def get_version_metrics(
    current_user: Dict = Depends(get_current_user)
):
    """
    Get API version usage metrics
    
    Returns metrics about API version usage.
    Requires authentication.
    """
    # Get metrics from versioning middleware
    from main import app
    
    metrics = {
        "message": "Version metrics would be collected from middleware",
        "note": "This would show usage statistics per version"
    }
    
    # Try to get actual metrics if middleware is available
    for middleware in app.middleware:
        if hasattr(middleware, 'get_metrics'):
            metrics.update(middleware.get_metrics())
            break
    
    return metrics


@router.get("/version/migration-guide/{from_version}/{to_version}")
async def get_migration_guide(from_version: str, to_version: str):
    """
    Get migration guide between versions
    
    Provides guidance on migrating from one API version to another.
    """
    try:
        from_ver = APIVersion(from_version)
        to_ver = APIVersion(to_version)
        
        # Validate versions
        if not version_registry.is_version_supported(from_ver):
            return {
                "error": f"Version {from_version} is not supported"
            }
        
        if not version_registry.is_version_supported(to_ver):
            return {
                "error": f"Version {to_version} is not supported"
            }
        
        if from_ver >= to_ver:
            return {
                "error": "Target version must be newer than source version"
            }
        
        # Get configurations
        from_config = version_registry.get_version_config(from_ver)
        to_config = version_registry.get_version_config(to_ver)
        
        # Build migration guide
        guide = {
            "from_version": str(from_ver),
            "to_version": str(to_ver),
            "breaking_changes": [],
            "new_features": [],
            "deprecated_features": [],
            "migration_steps": []
        }
        
        # Add breaking changes
        if to_config and to_config.breaking_changes:
            guide["breaking_changes"] = to_config.breaking_changes
        
        # Add new features
        if to_config and to_config.features:
            # Features that are in to_version but not in from_version
            from_features = set(from_config.features) if from_config else set()
            to_features = set(to_config.features)
            guide["new_features"] = list(to_features - from_features)
        
        # Add migration steps based on version transition
        if str(from_ver) == "v1" and str(to_ver) == "v2":
            guide["migration_steps"] = [
                "Update API endpoints from /api/v1/ to /api/v2/",
                "Update authentication headers from X-Auth-Token to Authorization: Bearer",
                "Update error handling to use new error response format",
                "Test all API integrations with v2 endpoints",
                "Update client libraries to support v2 features"
            ]
        
        guide["documentation_url"] = f"/docs/migration/{from_ver}-to-{to_ver}"
        
        return guide
        
    except ValueError as e:
        return {
            "error": f"Invalid version format: {e}"
        }


@router.get("/version/changelog/{version}")
async def get_version_changelog(version: str):
    """
    Get changelog for a specific version
    
    Returns the changelog entries for a specific API version.
    """
    try:
        api_version = APIVersion(version)
        
        if not version_registry.is_version_supported(api_version):
            return {
                "error": f"Version {version} is not supported"
            }
        
        config = version_registry.get_version_config(api_version)
        
        # Build changelog
        changelog = {
            "version": str(api_version),
            "status": config.status if config else "unknown",
            "release_date": "2024-01-15",  # Would come from actual changelog
            "changes": {
                "features": config.features if config else [],
                "breaking_changes": config.breaking_changes if config else [],
                "bug_fixes": [],
                "improvements": [],
                "security": []
            }
        }
        
        # Add version-specific changelog entries
        if str(api_version) == "v1":
            changelog["changes"]["features"] = [
                "Initial API release",
                "JWT authentication support",
                "Rate limiting",
                "Basic CRUD operations for all resources",
                "Health check endpoints"
            ]
            
        elif str(api_version) == "v2":
            changelog["changes"]["improvements"] = [
                "Enhanced error response format",
                "Better request validation",
                "Performance improvements"
            ]
            changelog["changes"]["security"] = [
                "Improved authentication token handling",
                "Added request signing support"
            ]
        
        return changelog
        
    except ValueError as e:
        return {
            "error": f"Invalid version format: {e}"
        }


# Export router
version_info_router = router