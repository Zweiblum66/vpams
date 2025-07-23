"""
Pydantic Schemas for Plugin Service
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

from ..core.plugin_base import PluginType, PluginStatus, PluginCapability


# Base Schemas
class PluginMetadataBase(BaseModel):
    """Base plugin metadata"""
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


class PluginConfigBase(BaseModel):
    """Base plugin configuration"""
    enabled: bool = True
    settings: Dict[str, Any] = Field(default_factory=dict)
    capabilities: List[PluginCapability] = Field(default_factory=list)
    api_key: Optional[str] = None
    webhook_url: Optional[str] = None
    rate_limit: Optional[int] = None
    timeout: int = 30
    retry_count: int = 3
    priority: int = 0


# Request Schemas
class PluginInstallRequest(BaseModel):
    """Plugin installation request"""
    url: Optional[str] = Field(None, description="URL to download plugin from")
    config: Optional[PluginConfigBase] = None


class PluginConfigUpdate(BaseModel):
    """Plugin configuration update"""
    settings: Dict[str, Any]
    reload: bool = False


class PluginExecuteRequest(BaseModel):
    """Plugin execution request"""
    hook_name: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    context_metadata: Dict[str, Any] = Field(default_factory=dict)
    capability: Optional[PluginCapability] = None


class PluginSearchRequest(BaseModel):
    """Plugin search request"""
    query: Optional[str] = None
    plugin_type: Optional[PluginType] = None
    tags: Optional[List[str]] = None
    min_rating: Optional[float] = Field(None, ge=0, le=5)
    max_price: Optional[float] = Field(None, ge=0)
    capabilities: Optional[List[PluginCapability]] = None


class PluginReviewRequest(BaseModel):
    """Plugin review request"""
    rating: float = Field(..., ge=0, le=5)
    comment: str = Field(..., min_length=10, max_length=1000)


class WebhookRequest(BaseModel):
    """Webhook registration request"""
    plugin_id: str
    event_types: List[str]
    url: str


# Response Schemas
class PluginMetadataResponse(PluginMetadataBase):
    """Plugin metadata response"""
    status: PluginStatus
    created_at: datetime
    updated_at: datetime
    
    @classmethod
    def from_plugin(cls, plugin):
        """Create from plugin instance"""
        return cls(
            id=plugin.metadata.id,
            name=plugin.metadata.name,
            version=plugin.metadata.version,
            description=plugin.metadata.description,
            author=plugin.metadata.author,
            author_email=plugin.metadata.author_email,
            homepage=plugin.metadata.homepage,
            documentation_url=plugin.metadata.documentation_url,
            icon_url=plugin.metadata.icon_url,
            license=plugin.metadata.license,
            min_mams_version=plugin.metadata.min_mams_version,
            max_mams_version=plugin.metadata.max_mams_version,
            status=plugin.status,
            created_at=plugin.metadata.created_at,
            updated_at=plugin.metadata.updated_at
        )
    
    @classmethod
    def from_metadata(cls, metadata, status=PluginStatus.INSTALLED):
        """Create from metadata"""
        return cls(
            id=metadata.id,
            name=metadata.name,
            version=metadata.version,
            description=metadata.description,
            author=metadata.author,
            author_email=metadata.author_email,
            homepage=metadata.homepage,
            documentation_url=metadata.documentation_url,
            icon_url=metadata.icon_url,
            license=metadata.license,
            min_mams_version=metadata.min_mams_version,
            max_mams_version=metadata.max_mams_version,
            status=status,
            created_at=metadata.created_at,
            updated_at=metadata.updated_at
        )
    
    class Config:
        use_enum_values = True


class PluginListResponse(BaseModel):
    """Plugin list response"""
    plugins: List[PluginMetadataResponse]
    total: int
    page: int
    limit: int


class PluginHealthResponse(BaseModel):
    """Plugin health response"""
    plugin_id: str
    status: str
    health: Dict[str, Any]


class PluginExecuteResponse(BaseModel):
    """Plugin execution response"""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PluginRegistryResponse(BaseModel):
    """Plugin registry entry response"""
    metadata: Dict[str, Any]
    download_url: str
    screenshots: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    pricing: Dict[str, Any] = Field(default_factory=dict)
    requirements: Dict[str, Any] = Field(default_factory=dict)
    registered_at: str
    updated_at: str
    downloads: int = 0
    rating: float = 0.0
    reviews: List[Dict[str, Any]] = Field(default_factory=list)


class DeveloperAccountResponse(BaseModel):
    """Developer account response"""
    id: str
    user_id: str
    company_name: Optional[str] = None
    website: Optional[str] = None
    support_email: Optional[str] = None
    verified: bool = False
    verification_date: Optional[datetime] = None
    revenue_share_percent: float = 70.0
    total_revenue: float = 0.0
    pending_payout: float = 0.0
    api_key: str
    api_key_created_at: datetime
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        orm_mode = True


class WebhookResponse(BaseModel):
    """Webhook response"""
    id: str
    plugin_id: str
    tenant_id: str
    event_types: List[str]
    url: str
    secret: str
    active: bool = True
    retry_count: int = 3
    timeout_seconds: int = 30
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    last_call_at: Optional[datetime] = None
    last_error: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        orm_mode = True


# Plugin Stats
class PluginStatsResponse(BaseModel):
    """Plugin statistics response"""
    total_plugins: int
    total_downloads: int
    average_rating: float
    free_plugins: int
    paid_plugins: int
    popular_tags: List[tuple[str, int]]


# Plugin Event
class PluginEventSchema(BaseModel):
    """Plugin event schema"""
    event_type: str
    data: Dict[str, Any]
    timestamp: datetime
    event_id: str
    plugin_id: Optional[str] = None
    tenant_id: Optional[str] = None


# Plugin Development
class PluginTemplateResponse(BaseModel):
    """Plugin template response"""
    name: str
    description: str
    plugin_type: PluginType
    template_url: str
    documentation_url: Optional[str] = None
    example_url: Optional[str] = None


class PluginValidationResponse(BaseModel):
    """Plugin validation response"""
    valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)


# Marketplace Schemas
class PluginMarketplaceResponse(BaseModel):
    """Plugin marketplace entry response"""
    id: str
    name: str
    description: str
    version: str
    author: str
    rating: float
    download_count: int
    category: str
    plugin_type: str
    price: float = 0.0
    screenshots: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: Optional[datetime] = None
    featured: bool = False


class PluginInstallationResponse(BaseModel):
    """Plugin installation response"""
    id: str
    plugin_id: str
    tenant_id: str
    status: str
    installed_at: Optional[datetime] = None
    last_used: Optional[datetime] = None
    config: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
    
    class Config:
        orm_mode = True


class MarketplaceSearchRequest(BaseModel):
    """Marketplace search request"""
    query: Optional[str] = None
    category: Optional[str] = None
    plugin_type: Optional[str] = None
    min_rating: Optional[float] = Field(None, ge=0, le=5)
    max_price: Optional[float] = Field(None, ge=0)
    free_only: bool = False
    sort_by: str = Field("relevance", regex="^(relevance|rating|downloads|newest|oldest|price)$")
    page: int = Field(1, ge=1)
    limit: int = Field(20, ge=1, le=100)


# Revenue Sharing Schemas
class PluginSaleResponse(BaseModel):
    """Plugin sale response"""
    id: str
    plugin_id: str
    customer_id: str
    sale_price: float
    revenue_share_amount: float
    revenue_share_percent: float
    platform_fee_amount: float
    platform_fee_percent: float
    payment_method: str
    transaction_id: str
    status: str
    created_at: datetime
    
    class Config:
        orm_mode = True


class RevenueShareResponse(BaseModel):
    """Revenue share response"""
    total_revenue: float
    revenue_share_amount: float
    revenue_share_percent: float
    platform_fee_amount: float
    platform_fee_percent: float
    currency: str = "USD"


class PayoutResponse(BaseModel):
    """Payout response"""
    id: str
    developer_id: str
    amount: float
    currency: str
    payout_method: str
    status: str
    status_message: Optional[str] = None
    processed_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        orm_mode = True


class PayoutRequestResponse(BaseModel):
    """Payout request response"""
    payout_id: str
    amount: float
    status: str
    estimated_processing_time: str
    message: str


class SalesReportResponse(BaseModel):
    """Sales report response"""
    period_start: datetime
    period_end: datetime
    total_sales: int
    total_revenue: float
    developer_revenue: float
    platform_fees: float
    average_sale_price: float
    top_selling_plugins: List[Dict[str, Any]] = Field(default_factory=list)


class PaymentMethodRequest(BaseModel):
    """Payment method request"""
    method_type: str = Field(..., regex="^(paypal|bank_transfer|stripe)$")
    payment_details: Dict[str, str]
    is_primary: bool = False


class PaymentMethodResponse(BaseModel):
    """Payment method response"""
    id: str
    developer_id: str
    method_type: str
    is_primary: bool
    is_verified: bool
    verification_status: str
    created_at: datetime
    
    class Config:
        orm_mode = True


class TaxReportResponse(BaseModel):
    """Tax report response"""
    year: int
    total_revenue: float
    total_payouts: float
    net_pending: float
    currency: str = "USD"
    monthly_breakdown: List[Dict[str, Any]] = Field(default_factory=list)
    generated_at: datetime