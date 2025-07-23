"""Pydantic schemas for the Partner APIs Service"""

from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from uuid import UUID
import enum

from ..db.models import (
    APIKeyStatusEnum, PartnerTierEnum, APIVersionEnum,
    WebhookStatusEnum, EventTypeEnum, HTTPMethodEnum
)


# Base schemas
class BaseSchema(BaseModel):
    """Base schema with common configuration"""
    
    class Config:
        from_attributes = True
        use_enum_values = True


# API Key schemas
class APIKeyBase(BaseSchema):
    """Base API key schema"""
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    tier: PartnerTierEnum = PartnerTierEnum.BASIC
    scopes: List[str] = Field(default=["read"])
    allowed_features: List[str] = Field(default=["assets"])
    allowed_api_versions: List[str] = Field(default=["v1"])
    allowed_ips: Optional[List[str]] = None
    allowed_domains: Optional[List[str]] = None
    expires_at: Optional[datetime] = None


class APIKeyCreate(APIKeyBase):
    """Schema for creating an API key"""
    partner_id: UUID


class APIKeyUpdate(BaseSchema):
    """Schema for updating an API key"""
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    status: Optional[APIKeyStatusEnum] = None
    tier: Optional[PartnerTierEnum] = None
    scopes: Optional[List[str]] = None
    allowed_features: Optional[List[str]] = None
    allowed_api_versions: Optional[List[str]] = None
    allowed_ips: Optional[List[str]] = None
    allowed_domains: Optional[List[str]] = None
    rate_limit: Optional[str] = None
    burst_limit: Optional[int] = None
    expires_at: Optional[datetime] = None


class APIKeyResponse(APIKeyBase):
    """Schema for API key responses"""
    id: UUID
    partner_id: UUID
    key_id: str
    status: APIKeyStatusEnum
    rate_limit: str
    burst_limit: int
    current_usage: int
    last_reset: datetime
    last_used_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class APIKeyWithSecret(APIKeyResponse):
    """Schema for API key response with secret (only on creation)"""
    api_key: str


# Webhook schemas
class WebhookBase(BaseSchema):
    """Base webhook schema"""
    name: str = Field(..., max_length=255)
    url: str = Field(..., max_length=2000)
    description: Optional[str] = None
    events: List[EventTypeEnum] = Field(..., min_items=1)
    secret: Optional[str] = Field(None, max_length=255)
    timeout_seconds: int = Field(default=30, ge=1, le=300)
    retry_attempts: int = Field(default=3, ge=0, le=10)
    retry_delay_seconds: int = Field(default=60, ge=1, le=3600)
    headers: Optional[Dict[str, str]] = None
    auth_type: Optional[str] = Field(None, max_length=50)
    auth_config: Optional[Dict[str, Any]] = None


class WebhookCreate(WebhookBase):
    """Schema for creating a webhook"""
    pass


class WebhookUpdate(BaseSchema):
    """Schema for updating a webhook"""
    name: Optional[str] = Field(None, max_length=255)
    url: Optional[str] = Field(None, max_length=2000)
    description: Optional[str] = None
    status: Optional[WebhookStatusEnum] = None
    events: Optional[List[EventTypeEnum]] = None
    secret: Optional[str] = Field(None, max_length=255)
    timeout_seconds: Optional[int] = Field(None, ge=1, le=300)
    retry_attempts: Optional[int] = Field(None, ge=0, le=10)
    retry_delay_seconds: Optional[int] = Field(None, ge=1, le=3600)
    headers: Optional[Dict[str, str]] = None
    auth_type: Optional[str] = Field(None, max_length=50)
    auth_config: Optional[Dict[str, Any]] = None


class WebhookResponse(WebhookBase):
    """Schema for webhook responses"""
    id: UUID
    api_key_id: UUID
    status: WebhookStatusEnum
    total_deliveries: int
    successful_deliveries: int
    failed_deliveries: int
    last_delivery_at: Optional[datetime] = None
    last_success_at: Optional[datetime] = None
    last_failure_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


# Usage analytics schemas
class APIUsageStats(BaseSchema):
    """Schema for API usage statistics"""
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_response_time_ms: float
    total_response_size_bytes: int
    unique_endpoints: int
    period_start: datetime
    period_end: datetime


class APIUsageByEndpoint(BaseSchema):
    """Schema for API usage by endpoint"""
    endpoint: str
    method: HTTPMethodEnum
    request_count: int
    avg_response_time_ms: float
    success_rate: float
    last_called: datetime


class APIUsageByDay(BaseSchema):
    """Schema for daily API usage"""
    date: datetime
    request_count: int
    error_count: int
    avg_response_time_ms: float


# Partner API response schemas
class AssetResponse(BaseSchema):
    """Asset response schema"""
    id: UUID
    name: str
    file_path: str
    asset_type: str
    size_bytes: int
    duration_seconds: Optional[float] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class AssetListResponse(BaseSchema):
    """Asset list response schema"""
    items: List[AssetResponse]
    total: int
    page: int
    pages: int
    has_next: bool
    has_prev: bool


class AssetCreate(BaseSchema):
    """Asset creation schema"""
    name: str = Field(..., max_length=255)
    file_path: str = Field(..., max_length=1024)
    asset_type: str = Field(..., max_length=50)
    project_id: Optional[UUID] = None
    metadata: Optional[Dict[str, Any]] = None


class AssetUpdate(BaseSchema):
    """Asset update schema"""
    name: Optional[str] = Field(None, max_length=255)
    metadata: Optional[Dict[str, Any]] = None


class ProjectResponse(BaseSchema):
    """Project response schema"""
    id: UUID
    name: str
    description: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None


class ProjectListResponse(BaseSchema):
    """Project list response schema"""
    items: List[ProjectResponse]
    total: int
    page: int
    pages: int
    has_next: bool
    has_prev: bool


class ProjectCreate(BaseSchema):
    """Project creation schema"""
    name: str = Field(..., max_length=255)
    description: Optional[str] = None


class ProjectUpdate(BaseSchema):
    """Project update schema"""
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    status: Optional[str] = None


class SearchRequest(BaseSchema):
    """Search request schema"""
    query: str = Field(..., max_length=500)
    filters: Optional[Dict[str, Any]] = None
    sort: Optional[str] = None
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class SearchResult(BaseSchema):
    """Search result item schema"""
    id: UUID
    type: str
    name: str
    description: Optional[str] = None
    score: float
    metadata: Dict[str, Any]


class SearchResponse(BaseSchema):
    """Search response schema"""
    results: List[SearchResult]
    total: int
    query: str
    took_ms: int


class WorkflowResponse(BaseSchema):
    """Workflow response schema"""
    id: UUID
    name: str
    description: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None


class WorkflowListResponse(BaseSchema):
    """Workflow list response schema"""
    items: List[WorkflowResponse]
    total: int
    page: int
    pages: int
    has_next: bool
    has_prev: bool


class WorkflowTriggerRequest(BaseSchema):
    """Workflow trigger request schema"""
    input_data: Optional[Dict[str, Any]] = None
    priority: Optional[str] = "normal"


class UserResponse(BaseSchema):
    """User response schema"""
    id: UUID
    email: str
    first_name: str
    last_name: str
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None


class UserListResponse(BaseSchema):
    """User list response schema"""
    items: List[UserResponse]
    total: int
    page: int
    pages: int
    has_next: bool
    has_prev: bool


# Standard response schemas
class StandardResponse(BaseSchema):
    """Standard API response"""
    message: str
    success: bool = True
    data: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseSchema):
    """Error response schema"""
    error: Dict[str, Any]


# Pagination schemas
class PaginationParams(BaseSchema):
    """Pagination parameters"""
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)
    sort_by: Optional[str] = Field(default="created_at")
    sort_order: Optional[str] = Field(default="desc", regex="^(asc|desc)$")


class PaginatedResponse(BaseSchema):
    """Paginated response wrapper"""
    items: List[Any]
    total: int
    page: int
    pages: int
    has_next: bool
    has_prev: bool


# Webhook delivery schemas
class WebhookDeliveryResponse(BaseSchema):
    """Webhook delivery response schema"""
    id: UUID
    webhook_id: UUID
    event_type: EventTypeEnum
    event_id: str
    attempt_number: int
    status_code: Optional[int] = None
    success: bool
    error_message: Optional[str] = None
    duration_ms: Optional[int] = None
    delivered_at: datetime


class WebhookTestRequest(BaseSchema):
    """Webhook test request schema"""
    event_type: EventTypeEnum
    test_data: Optional[Dict[str, Any]] = None


# Configuration schemas
class PartnerAPIConfigResponse(BaseSchema):
    """Partner API configuration response"""
    partner_id: UUID
    enabled_api_versions: List[str]
    enabled_features: List[str]
    custom_rate_limits: Dict[str, str]
    max_webhooks: int
    allowed_webhook_events: List[str]
    webhook_timeout_override: Optional[int] = None
    enable_sandbox: bool
    enable_webhooks: bool
    enable_analytics: bool
    enable_rate_limiting: bool
    created_at: datetime
    updated_at: Optional[datetime] = None


class PartnerAPIConfigUpdate(BaseSchema):
    """Partner API configuration update schema"""
    enabled_api_versions: Optional[List[str]] = None
    enabled_features: Optional[List[str]] = None
    custom_rate_limits: Optional[Dict[str, str]] = None
    max_webhooks: Optional[int] = None
    allowed_webhook_events: Optional[List[str]] = None
    webhook_timeout_override: Optional[int] = None
    enable_sandbox: Optional[bool] = None
    enable_webhooks: Optional[bool] = None
    enable_analytics: Optional[bool] = None
    enable_rate_limiting: Optional[bool] = None