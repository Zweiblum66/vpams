"""Feature flag schemas"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID


class FeatureFlagCreate(BaseModel):
    """Create feature flag"""
    name: str = Field(..., regex="^[a-z_]+$", description="Lowercase with underscores")
    display_name: str
    description: str
    category: str = Field(..., regex="^(ui|api|processing|experimental)$")
    is_enabled: bool = False
    rollout_percentage: int = Field(0, ge=0, le=100)
    rollout_strategy: str = Field("percentage", regex="^(percentage|whitelist|all_beta|specific_phase)$")
    config: Optional[Dict[str, Any]] = None
    dependencies: Optional[List[str]] = Field(default_factory=list)
    incompatible_features: Optional[List[str]] = Field(default_factory=list)
    available_phases: List[str] = Field(default=["closed_beta"])
    min_access_level: str = Field("standard", regex="^(standard|advanced|full)$")
    risk_level: str = Field("low", regex="^(low|medium|high)$")
    documentation_url: Optional[str] = None


class FeatureFlagUpdate(BaseModel):
    """Update feature flag"""
    display_name: Optional[str] = None
    description: Optional[str] = None
    is_enabled: Optional[bool] = None
    rollout_percentage: Optional[int] = Field(None, ge=0, le=100)
    rollout_strategy: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    dependencies: Optional[List[str]] = None
    incompatible_features: Optional[List[str]] = None
    available_phases: Optional[List[str]] = None
    min_access_level: Optional[str] = None
    risk_level: Optional[str] = None
    stability_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    documentation_url: Optional[str] = None
    known_issues: Optional[List[Dict[str, Any]]] = None
    released_at: Optional[datetime] = None
    deprecated_at: Optional[datetime] = None


class FeatureFlagResponse(BaseModel):
    """Feature flag response"""
    id: UUID
    name: str
    display_name: str
    description: str
    category: str
    is_enabled: bool
    rollout_percentage: int
    rollout_strategy: str
    config: Optional[Dict[str, Any]]
    dependencies: List[str]
    incompatible_features: List[str]
    available_phases: List[str]
    min_access_level: str
    ab_test_enabled: bool
    ab_test_variants: Optional[List[Dict[str, Any]]]
    risk_level: str
    stability_score: float
    documentation_url: Optional[str]
    changelog: Optional[List[Dict[str, Any]]]
    known_issues: Optional[List[Dict[str, Any]]]
    total_users: int
    active_users: int
    error_rate: float
    created_by: Optional[str]
    created_at: datetime
    updated_at: datetime
    released_at: Optional[datetime]
    deprecated_at: Optional[datetime]
    
    class Config:
        orm_mode = True


class FeatureFlagListResponse(BaseModel):
    """Feature flag list response"""
    features: List[FeatureFlagResponse]
    total: int
    page: int
    limit: int
    pages: int


class UserFeatureResponse(BaseModel):
    """User feature access response"""
    feature_id: str
    name: str
    display_name: str
    description: str
    category: str
    is_enabled: bool
    variant: Optional[str]
    config: Optional[Dict[str, Any]]


class FeatureToggleRequest(BaseModel):
    """Toggle feature for user"""
    user_id: UUID
    enabled: bool