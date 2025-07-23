"""
API Schemas for Plugin Service
"""

from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..core.plugin_base import PluginType, PluginCapability


class PluginMetadataResponse(BaseModel):
    """Plugin metadata response"""
    id: str
    name: str
    version: str
    description: str
    author: str
    author_email: Optional[str] = None
    homepage: Optional[str] = None
    documentation_url: Optional[str] = None
    icon_url: Optional[str] = None
    license: str = "Proprietary"
    min_mams_version: str = "1.0.0"
    max_mams_version: Optional[str] = None
    status: str
    enabled: bool
    capabilities: List[PluginCapability] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class PluginInstallRequest(BaseModel):
    """Plugin installation request"""
    download_url: Optional[str] = Field(None, description="URL to download plugin from")
    config: Dict[str, Any] = Field({}, description="Initial plugin configuration")
    enable: bool = Field(True, description="Enable plugin after installation")


class PluginConfigUpdate(BaseModel):
    """Plugin configuration update"""
    settings: Optional[Dict[str, Any]] = Field(None, description="Plugin-specific settings")
    capabilities: Optional[List[PluginCapability]] = Field(None, description="Plugin capabilities")
    rate_limit: Optional[int] = Field(None, description="Rate limit (requests per minute)")
    timeout: Optional[int] = Field(None, description="Execution timeout in seconds")


class PluginExecuteRequest(BaseModel):
    """Plugin hook execution request"""
    hook_name: str = Field(..., description="Hook name to execute")
    plugin_type: Optional[PluginType] = Field(None, description="Filter by plugin type")
    parameters: Dict[str, Any] = Field({}, description="Hook parameters")
    context_metadata: Dict[str, Any] = Field({}, description="Additional context metadata")
    request_id: Optional[str] = Field(None, description="Request ID for tracking")


class PluginEventRequest(BaseModel):
    """Plugin event broadcast request"""
    event_type: str = Field(..., description="Event type")
    data: Dict[str, Any] = Field(..., description="Event data")


class PluginSearchRequest(BaseModel):
    """Plugin search request"""
    query: Optional[str] = Field(None, description="Search query")
    plugin_type: Optional[PluginType] = Field(None, description="Plugin type filter")
    tags: Optional[List[str]] = Field(None, description="Tag filters")
    author: Optional[str] = Field(None, description="Author filter")
    min_rating: Optional[float] = Field(None, ge=0, le=5, description="Minimum rating")
    max_price: Optional[float] = Field(None, ge=0, description="Maximum price")
    capabilities: Optional[List[PluginCapability]] = Field(None, description="Required capabilities")
    sort_by: str = Field("downloads", description="Sort field")
    ascending: bool = Field(False, description="Sort order")
    limit: int = Field(50, ge=1, le=100, description="Results per page")
    offset: int = Field(0, ge=0, description="Offset for pagination")


class PluginReviewRequest(BaseModel):
    """Plugin review request"""
    rating: float = Field(..., ge=0, le=5, description="Rating (0-5)")
    comment: str = Field(..., description="Review comment")


class PluginHealthResponse(BaseModel):
    """Plugin health response"""
    plugin_id: str
    status: str
    health: Dict[str, Any]
    last_checked: datetime


class MarketplaceStatsResponse(BaseModel):
    """Marketplace statistics response"""
    total_plugins: int
    total_downloads: int
    average_rating: float
    free_plugins: int
    paid_plugins: int
    popular_tags: List[tuple]


class PluginWebhookRequest(BaseModel):
    """Plugin webhook registration request"""
    event_types: List[str] = Field(..., description="Event types to subscribe to")
    url: str = Field(..., description="Webhook URL")
    secret: Optional[str] = Field(None, description="Webhook secret for signature validation")
    retry_count: int = Field(3, ge=0, le=10, description="Number of retry attempts")
    timeout_seconds: int = Field(30, ge=5, le=300, description="Request timeout in seconds")


class DeveloperAccountRequest(BaseModel):
    """Developer account creation request"""
    company_name: Optional[str] = Field(None, description="Company name")
    website: Optional[str] = Field(None, description="Company website")
    support_email: str = Field(..., description="Support email address")


class PluginPublishRequest(BaseModel):
    """Plugin publish request"""
    name: str = Field(..., description="Plugin name")
    version: str = Field(..., description="Plugin version")
    description: str = Field(..., description="Plugin description")
    tags: List[str] = Field([], description="Plugin tags")
    screenshots: List[str] = Field([], description="Screenshot URLs")
    pricing: Dict[str, Any] = Field({"type": "free"}, description="Pricing information")
    requirements: Dict[str, Any] = Field({}, description="Plugin requirements")