"""
API Key Pydantic Schemas

Defines request and response models for API key operations.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, validator


class APIKeyBase(BaseModel):
    """Base schema for API key"""
    name: str = Field(..., min_length=3, max_length=255, description="API key name")
    description: Optional[str] = Field(None, max_length=1000, description="API key description")
    scopes: List[str] = Field(default_factory=lambda: ["read"], description="List of permission scopes")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class APIKeyCreate(APIKeyBase):
    """Schema for creating an API key"""
    application_id: Optional[str] = Field(None, description="Optional application ID")
    expires_in_days: Optional[int] = Field(None, ge=1, le=3650, description="Expiration in days")
    rate_limit_override: Optional[int] = Field(None, ge=1, description="Custom rate limit per minute")
    
    @validator('scopes')
    def validate_scopes(cls, v):
        """Validate that scopes are from allowed list"""
        allowed_scopes = ["read", "write", "admin", "upload", "download", "delete"]
        for scope in v:
            if scope not in allowed_scopes:
                raise ValueError(f"Invalid scope: {scope}. Allowed: {allowed_scopes}")
        return v


class APIKeyUpdate(BaseModel):
    """Schema for updating an API key"""
    name: Optional[str] = Field(None, min_length=3, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    scopes: Optional[List[str]] = Field(None)
    rate_limit_override: Optional[int] = Field(None, ge=1)
    metadata: Optional[Dict[str, Any]] = Field(None)
    
    @validator('scopes')
    def validate_scopes(cls, v):
        """Validate that scopes are from allowed list"""
        if v is not None:
            allowed_scopes = ["read", "write", "admin", "upload", "download", "delete"]
            for scope in v:
                if scope not in allowed_scopes:
                    raise ValueError(f"Invalid scope: {scope}. Allowed: {allowed_scopes}")
        return v


class APIKeyResponse(BaseModel):
    """Schema for API key response"""
    model_config = ConfigDict(from_attributes=True)
    
    id: str = Field(..., description="API key ID")
    key: Optional[str] = Field(None, description="Raw API key (only returned on creation)")
    name: str = Field(..., description="API key name")
    description: Optional[str] = Field(None, description="API key description")
    prefix: str = Field(..., description="API key prefix")
    last_four: str = Field(..., description="Last four characters of key")
    scopes: List[str] = Field(..., description="Permission scopes")
    expires_at: Optional[datetime] = Field(None, description="Expiration timestamp")
    is_active: bool = Field(..., description="Whether key is active")
    created_at: datetime = Field(..., description="Creation timestamp")
    last_used_at: Optional[datetime] = Field(None, description="Last usage timestamp")
    usage_count: int = Field(..., description="Total usage count")
    user_id: Optional[str] = Field(None, description="Associated user ID")
    application_id: Optional[str] = Field(None, description="Associated application ID")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class APIKeyListResponse(BaseModel):
    """Schema for paginated API key list response"""
    items: List[APIKeyResponse] = Field(..., description="List of API keys")
    total: int = Field(..., description="Total number of items")
    skip: int = Field(..., description="Number of items skipped")
    limit: int = Field(..., description="Maximum number of items returned")
    
    @property
    def has_next(self) -> bool:
        """Check if there are more items"""
        return self.skip + self.limit < self.total
    
    @property
    def has_previous(self) -> bool:
        """Check if there are previous items"""
        return self.skip > 0


class APIKeyRotateResponse(BaseModel):
    """Schema for API key rotation response"""
    old_key_id: str = Field(..., description="ID of the old key")
    old_key_revoked: bool = Field(..., description="Whether the old key was revoked")
    new_key: APIKeyResponse = Field(..., description="New API key details")


class APIKeyUsageStats(BaseModel):
    """Schema for API key usage statistics"""
    total_requests: int = Field(..., description="Total number of requests")
    successful_requests: int = Field(..., description="Number of successful requests")
    failed_requests: int = Field(..., description="Number of failed requests")
    success_rate: float = Field(..., description="Success rate percentage")
    status_codes: Dict[int, int] = Field(..., description="Breakdown by status code")
    average_response_time_ms: float = Field(..., description="Average response time in milliseconds")
    period_days: int = Field(..., description="Period in days")
    since: str = Field(..., description="Start date of the period")
    
    @validator('success_rate')
    def round_success_rate(cls, v):
        """Round success rate to 2 decimal places"""
        return round(v, 2)
    
    @validator('average_response_time_ms')
    def round_response_time(cls, v):
        """Round response time to 2 decimal places"""
        return round(v, 2)


class APIKeyHealthCheck(BaseModel):
    """Schema for API key health check response"""
    is_valid: bool = Field(..., description="Whether the API key is valid")
    key_id: Optional[str] = Field(None, description="API key ID if valid")
    expires_at: Optional[datetime] = Field(None, description="Expiration timestamp")
    scopes: Optional[List[str]] = Field(None, description="Available scopes")
    rate_limit_remaining: Optional[int] = Field(None, description="Remaining rate limit")
    message: Optional[str] = Field(None, description="Additional message")
