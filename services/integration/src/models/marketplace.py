"""
Marketplace data models
"""

from sqlalchemy import Column, String, Text, Integer, Float, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from typing import Optional, Dict, Any, List

from ..db.base import Base


class APIListing(Base):
    """API Marketplace Listing"""
    __tablename__ = "api_listings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Basic Information
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    short_description = Column(String(500))
    
    # Provider Information
    provider_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    provider_name = Column(String(255), nullable=False)
    provider_url = Column(String(1024))
    
    # API Details
    api_type = Column(String(50), nullable=False, index=True)  # rest, graphql, grpc, webhook
    category = Column(String(100), nullable=False, index=True)
    version = Column(String(50), nullable=False)
    
    # Configuration
    base_url = Column(String(1024))
    authentication_type = Column(String(50))  # api_key, oauth2, basic, none
    auth_config = Column(JSON)
    config_schema = Column(JSON)  # JSON Schema for configuration
    
    # Documentation
    documentation_url = Column(String(1024))
    openapi_spec = Column(JSON)
    examples = Column(JSON)
    changelog = Column(Text)
    
    # Marketplace Metadata
    featured = Column(Boolean, default=False, index=True)
    status = Column(String(20), default="pending", index=True)  # pending, approved, rejected, deprecated
    tags = Column(JSON)  # List of tags
    pricing_model = Column(String(50))  # free, freemium, paid, usage_based
    pricing_details = Column(JSON)
    
    # Stats
    install_count = Column(Integer, default=0)
    rating_average = Column(Float, default=0.0)
    rating_count = Column(Integer, default=0)
    view_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    published_at = Column(DateTime(timezone=True))
    
    # Relationships
    reviews = relationship("APIListingReview", back_populates="listing", cascade="all, delete-orphan")
    installations = relationship("APIInstallation", back_populates="listing", cascade="all, delete-orphan")


class APIListingReview(Base):
    """API Listing Review"""
    __tablename__ = "api_listing_reviews"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # References
    listing_id = Column(UUID(as_uuid=True), ForeignKey("api_listings.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Review Data
    rating = Column(Integer, nullable=False)  # 1-5 stars
    review_text = Column(Text)
    
    # Metadata
    helpful_count = Column(Integer, default=0)
    verified_user = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    listing = relationship("APIListing", back_populates="reviews")


class APIInstallation(Base):
    """API Installation Record"""
    __tablename__ = "api_installations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # References
    listing_id = Column(UUID(as_uuid=True), ForeignKey("api_listings.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    integration_id = Column(UUID(as_uuid=True), index=True)  # Created integration
    
    # Installation Data
    version = Column(String(50), nullable=False)
    config = Column(JSON)
    status = Column(String(20), default="active", index=True)  # active, inactive, error
    
    # Usage Stats
    api_calls_count = Column(Integer, default=0)
    last_used = Column(DateTime(timezone=True))
    
    # Timestamps
    installed_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    listing = relationship("APIListing", back_populates="installations")


class MarketplaceCategory(Base):
    """Marketplace Category"""
    __tablename__ = "marketplace_categories"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Category Data
    name = Column(String(100), nullable=False, unique=True, index=True)
    description = Column(Text)
    icon = Column(String(255))
    color = Column(String(7))  # Hex color
    
    # Hierarchy
    parent_id = Column(UUID(as_uuid=True), ForeignKey("marketplace_categories.id"), index=True)
    sort_order = Column(Integer, default=0)
    
    # Metadata
    listing_count = Column(Integer, default=0)
    featured = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    parent = relationship("MarketplaceCategory", remote_side=[id])
    children = relationship("MarketplaceCategory")


class APIListingVersion(Base):
    """API Listing Version History"""
    __tablename__ = "api_listing_versions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # References
    listing_id = Column(UUID(as_uuid=True), ForeignKey("api_listings.id"), nullable=False, index=True)
    
    # Version Data
    version = Column(String(50), nullable=False)
    changelog = Column(Text)
    config_schema = Column(JSON)
    openapi_spec = Column(JSON)
    
    # Metadata
    breaking_changes = Column(Boolean, default=False)
    deprecated = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    listing = relationship("APIListing")


# Pydantic models for API requests/responses
from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import Optional, List, Dict, Any


class APIListingBase(BaseModel):
    """Base API Listing model"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    short_description: Optional[str] = Field(None, max_length=500)
    provider_name: str = Field(..., min_length=1, max_length=255)
    provider_url: Optional[str] = None
    api_type: str = Field(..., regex="^(rest|graphql|grpc|webhook)$")
    category: str = Field(..., min_length=1, max_length=100)
    version: str = Field(..., min_length=1, max_length=50)
    base_url: Optional[str] = None
    authentication_type: Optional[str] = Field(None, regex="^(api_key|oauth2|basic|none)$")
    auth_config: Optional[Dict[str, Any]] = None
    config_schema: Optional[Dict[str, Any]] = None
    documentation_url: Optional[str] = None
    openapi_spec: Optional[Dict[str, Any]] = None
    examples: Optional[Dict[str, Any]] = None
    changelog: Optional[str] = None
    tags: Optional[List[str]] = Field(default_factory=list)
    pricing_model: Optional[str] = Field(None, regex="^(free|freemium|paid|usage_based)$")
    pricing_details: Optional[Dict[str, Any]] = None

    @validator('tags')
    def validate_tags(cls, v):
        if v and len(v) > 20:
            raise ValueError('Maximum 20 tags allowed')
        return v


class APIListingCreate(APIListingBase):
    """API Listing creation model"""
    pass


class APIListingUpdate(BaseModel):
    """API Listing update model"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    short_description: Optional[str] = Field(None, max_length=500)
    provider_name: Optional[str] = Field(None, min_length=1, max_length=255)
    provider_url: Optional[str] = None
    version: Optional[str] = Field(None, min_length=1, max_length=50)
    base_url: Optional[str] = None
    authentication_type: Optional[str] = Field(None, regex="^(api_key|oauth2|basic|none)$")
    auth_config: Optional[Dict[str, Any]] = None
    config_schema: Optional[Dict[str, Any]] = None
    documentation_url: Optional[str] = None
    openapi_spec: Optional[Dict[str, Any]] = None
    examples: Optional[Dict[str, Any]] = None
    changelog: Optional[str] = None
    tags: Optional[List[str]] = None
    pricing_model: Optional[str] = Field(None, regex="^(free|freemium|paid|usage_based)$")
    pricing_details: Optional[Dict[str, Any]] = None
    featured: Optional[bool] = None
    status: Optional[str] = Field(None, regex="^(pending|approved|rejected|deprecated)$")


class APIListingOut(APIListingBase):
    """API Listing output model"""
    id: str
    provider_id: str
    featured: bool
    status: str
    install_count: int
    rating_average: float
    rating_count: int
    view_count: int
    created_at: datetime
    updated_at: Optional[datetime]
    published_at: Optional[datetime]

    class Config:
        from_attributes = True


class APIListingReviewCreate(BaseModel):
    """API Listing Review creation model"""
    rating: int = Field(..., ge=1, le=5)
    review_text: Optional[str] = Field(None, max_length=2000)


class APIListingReviewOut(BaseModel):
    """API Listing Review output model"""
    id: str
    listing_id: str
    user_id: str
    rating: int
    review_text: Optional[str]
    helpful_count: int
    verified_user: bool
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True