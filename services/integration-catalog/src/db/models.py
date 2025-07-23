"""
Database models for Integration Catalog Service
"""

from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, JSON, Text,
    ForeignKey, UniqueConstraint, Index, Float, Enum as SQLEnum
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import uuid
import enum

from .base import Base


class IntegrationTypeEnum(str, enum.Enum):
    """Integration type enum"""
    REST_API = "rest_api"
    GRAPHQL = "graphql"
    WEBHOOK = "webhook"
    SDK = "sdk"
    PLUGIN = "plugin"
    CONNECTOR = "connector"
    MIDDLEWARE = "middleware"


class IntegrationStatusEnum(str, enum.Enum):
    """Integration status enum"""
    DRAFT = "draft"
    PUBLISHED = "published"
    DEPRECATED = "deprecated"
    RETIRED = "retired"


class ProtocolEnum(str, enum.Enum):
    """Protocol enum"""
    HTTP = "http"
    HTTPS = "https"
    WEBSOCKET = "websocket"
    GRPC = "grpc"
    TCP = "tcp"
    UDP = "udp"


class AuthTypeEnum(str, enum.Enum):
    """Authentication type enum"""
    NONE = "none"
    API_KEY = "api_key"
    BEARER_TOKEN = "bearer_token"
    BASIC_AUTH = "basic_auth"
    OAUTH2 = "oauth2"
    JWT = "jwt"
    CUSTOM = "custom"


class Integration(Base):
    """Integration model"""
    __tablename__ = "integrations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Basic Information
    name = Column(String(255), nullable=False, index=True)
    display_name = Column(String(255))
    description = Column(Text)
    short_description = Column(String(500))
    version = Column(String(50), nullable=False)
    
    # Classification
    integration_type = Column(SQLEnum(IntegrationTypeEnum), nullable=False)
    category = Column(String(100), nullable=False)  # storage, ai, communication, analytics, etc.
    subcategory = Column(String(100))
    
    # Provider Information
    provider_name = Column(String(255), nullable=False)
    provider_website = Column(String(500))
    provider_email = Column(String(255))
    provider_support_url = Column(String(500))
    
    # Status and Visibility
    status = Column(SQLEnum(IntegrationStatusEnum), default=IntegrationStatusEnum.DRAFT)
    is_featured = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)
    is_free = Column(Boolean, default=True)
    
    # Technical Details
    protocol = Column(SQLEnum(ProtocolEnum), default=ProtocolEnum.HTTPS)
    base_url = Column(String(500))
    documentation_url = Column(String(500))
    api_reference_url = Column(String(500))
    
    # Authentication
    auth_type = Column(SQLEnum(AuthTypeEnum), default=AuthTypeEnum.API_KEY)
    auth_config = Column(JSON, default=dict)  # Auth configuration details
    
    # API Specification
    openapi_spec = Column(JSON)  # OpenAPI/Swagger specification
    schema_version = Column(String(20), default="3.0.0")
    
    # Capabilities and Features
    supported_operations = Column(JSON, default=list)  # List of supported operations
    data_formats = Column(JSON, default=list)  # Supported data formats (JSON, XML, etc.)
    rate_limits = Column(JSON, default=dict)  # Rate limiting information
    
    # Integration Details
    setup_complexity = Column(String(20), default="medium")  # easy, medium, hard
    setup_time_minutes = Column(Integer)  # Estimated setup time
    prerequisites = Column(JSON, default=list)  # Required prerequisites
    
    # Metadata
    tags = Column(JSON, default=list)
    use_cases = Column(JSON, default=list)
    industries = Column(JSON, default=list)
    
    # Assets
    logo_url = Column(String(500))
    banner_url = Column(String(500))
    screenshots = Column(JSON, default=list)
    video_url = Column(String(500))
    
    # Pricing
    pricing_model = Column(String(50))  # free, freemium, paid, usage_based
    pricing_details = Column(JSON, default=dict)
    
    # Statistics
    install_count = Column(Integer, default=0)
    rating = Column(Float, default=0.0)
    review_count = Column(Integer, default=0)
    
    # Timestamps
    published_at = Column(DateTime(timezone=True))
    deprecated_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    endpoints = relationship("IntegrationEndpoint", back_populates="integration", cascade="all, delete-orphan")
    installations = relationship("IntegrationInstallation", back_populates="integration", cascade="all, delete-orphan")
    reviews = relationship("IntegrationReview", back_populates="integration", cascade="all, delete-orphan")
    tests = relationship("IntegrationTest", back_populates="integration", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_integration_name', 'name'),
        Index('idx_integration_type_category', 'integration_type', 'category'),
        Index('idx_integration_status', 'status'),
        Index('idx_integration_provider', 'provider_name'),
    )


class IntegrationEndpoint(Base):
    """Integration API endpoints"""
    __tablename__ = "integration_endpoints"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    integration_id = Column(UUID(as_uuid=True), ForeignKey("integrations.id", ondelete="CASCADE"), nullable=False)
    
    # Endpoint Information
    path = Column(String(500), nullable=False)
    method = Column(String(10), nullable=False)  # GET, POST, PUT, DELETE, PATCH
    operation_id = Column(String(255))
    summary = Column(String(255))
    description = Column(Text)
    
    # Request/Response
    parameters = Column(JSON, default=list)  # Query, path, header parameters
    request_body = Column(JSON)  # Request body schema
    responses = Column(JSON, default=dict)  # Response schemas
    
    # Configuration
    requires_auth = Column(Boolean, default=True)
    rate_limit = Column(JSON)  # Endpoint-specific rate limits
    
    # Examples
    examples = Column(JSON, default=list)  # Request/response examples
    
    # Metadata
    tags = Column(JSON, default=list)
    is_deprecated = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    integration = relationship("Integration", back_populates="endpoints")
    
    __table_args__ = (
        Index('idx_endpoint_integration', 'integration_id'),
        Index('idx_endpoint_method_path', 'method', 'path'),
    )


class IntegrationInstallation(Base):
    """Integration installations by organizations"""
    __tablename__ = "integration_installations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    integration_id = Column(UUID(as_uuid=True), ForeignKey("integrations.id", ondelete="CASCADE"), nullable=False)
    
    # Installation Details
    organization_id = Column(String(255), nullable=False)
    user_id = Column(String(255), nullable=False)
    environment = Column(String(50), default="production")  # development, staging, production
    
    # Configuration
    config = Column(JSON, default=dict)  # Installation-specific configuration
    credentials = Column(JSON)  # Encrypted credentials (if stored)
    
    # Status
    status = Column(String(50), default="active")  # active, suspended, disabled
    last_used_at = Column(DateTime(timezone=True))
    
    # Health Monitoring
    health_status = Column(String(50), default="healthy")  # healthy, warning, error, unknown
    last_health_check = Column(DateTime(timezone=True))
    health_details = Column(JSON)
    
    # Usage Statistics
    total_requests = Column(Integer, default=0)
    last_request_at = Column(DateTime(timezone=True))
    error_count = Column(Integer, default=0)
    
    # Timestamps
    installed_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    integration = relationship("Integration", back_populates="installations")
    
    __table_args__ = (
        Index('idx_installation_integration', 'integration_id'),
        Index('idx_installation_org', 'organization_id'),
        Index('idx_installation_status', 'status'),
        UniqueConstraint('integration_id', 'organization_id', 'environment', name='uq_integration_org_env'),
    )


class IntegrationReview(Base):
    """Integration reviews and ratings"""
    __tablename__ = "integration_reviews"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    integration_id = Column(UUID(as_uuid=True), ForeignKey("integrations.id", ondelete="CASCADE"), nullable=False)
    
    # Review Information
    user_id = Column(String(255), nullable=False)
    organization_id = Column(String(255))
    rating = Column(Integer, nullable=False)  # 1-5 stars
    title = Column(String(255))
    comment = Column(Text)
    
    # Review Categories
    ease_of_use = Column(Integer)  # 1-5 rating
    documentation_quality = Column(Integer)  # 1-5 rating
    support_quality = Column(Integer)  # 1-5 rating
    reliability = Column(Integer)  # 1-5 rating
    
    # Verification
    verified_installation = Column(Boolean, default=False)
    
    # Moderation
    is_approved = Column(Boolean, default=True)
    moderator_notes = Column(Text)
    
    # Helpfulness
    helpful_count = Column(Integer, default=0)
    unhelpful_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    integration = relationship("Integration", back_populates="reviews")
    
    __table_args__ = (
        Index('idx_review_integration', 'integration_id'),
        Index('idx_review_rating', 'rating'),
        Index('idx_review_user', 'user_id'),
        UniqueConstraint('integration_id', 'user_id', name='uq_integration_user_review'),
    )


class IntegrationTest(Base):
    """Integration API tests"""
    __tablename__ = "integration_tests"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    integration_id = Column(UUID(as_uuid=True), ForeignKey("integrations.id", ondelete="CASCADE"), nullable=False)
    
    # Test Information
    test_name = Column(String(255), nullable=False)
    test_type = Column(String(50), nullable=False)  # connectivity, auth, functionality, performance
    endpoint_path = Column(String(500))
    
    # Test Configuration
    test_config = Column(JSON, default=dict)  # Test parameters and configuration
    expected_results = Column(JSON)  # Expected test results
    
    # Test Results
    status = Column(String(50), default="pending")  # pending, running, passed, failed, error
    result = Column(JSON)  # Test execution results
    error_message = Column(Text)
    
    # Performance Metrics
    response_time_ms = Column(Integer)
    status_code = Column(Integer)
    
    # Scheduling
    is_scheduled = Column(Boolean, default=False)
    schedule_cron = Column(String(100))
    
    # Timestamps
    last_run_at = Column(DateTime(timezone=True))
    next_run_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    integration = relationship("Integration", back_populates="tests")
    
    __table_args__ = (
        Index('idx_test_integration', 'integration_id'),
        Index('idx_test_type', 'test_type'),
        Index('idx_test_status', 'status'),
        Index('idx_test_scheduled', 'is_scheduled', 'next_run_at'),
    )


class IntegrationCategory(Base):
    """Integration categories for organization"""
    __tablename__ = "integration_categories"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Category Information
    name = Column(String(100), unique=True, nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    display_name = Column(String(255))
    description = Column(Text)
    
    # Hierarchy
    parent_id = Column(UUID(as_uuid=True), ForeignKey("integration_categories.id"))
    
    # Display
    icon = Column(String(100))  # Icon name or URL
    color = Column(String(7))  # Hex color code
    display_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    
    # Statistics
    integration_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    children = relationship("IntegrationCategory", backref="parent", remote_side=[id])
    
    __table_args__ = (
        Index('idx_category_name', 'name'),
        Index('idx_category_parent', 'parent_id'),
        Index('idx_category_active', 'is_active'),
    )


class IntegrationCollection(Base):
    """Curated collections of integrations"""
    __tablename__ = "integration_collections"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Collection Information
    name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False)
    description = Column(Text)
    
    # Curation
    curator_id = Column(String(255))  # User who created the collection
    is_featured = Column(Boolean, default=False)
    is_public = Column(Boolean, default=True)
    
    # Display
    banner_url = Column(String(500))
    tags = Column(JSON, default=list)
    
    # Statistics
    integration_count = Column(Integer, default=0)
    view_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_collection_slug', 'slug'),
        Index('idx_collection_featured', 'is_featured'),
        Index('idx_collection_public', 'is_public'),
    )


class IntegrationCollectionItem(Base):
    """Items in integration collections"""
    __tablename__ = "integration_collection_items"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    collection_id = Column(UUID(as_uuid=True), ForeignKey("integration_collections.id", ondelete="CASCADE"), nullable=False)
    integration_id = Column(UUID(as_uuid=True), ForeignKey("integrations.id", ondelete="CASCADE"), nullable=False)
    
    # Ordering
    display_order = Column(Integer, default=0)
    
    # Metadata
    added_by = Column(String(255))
    notes = Column(Text)
    
    # Timestamps
    added_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    collection = relationship("IntegrationCollection")
    integration = relationship("Integration")
    
    __table_args__ = (
        Index('idx_collection_item_collection', 'collection_id'),
        Index('idx_collection_item_integration', 'integration_id'),
        Index('idx_collection_item_order', 'collection_id', 'display_order'),
        UniqueConstraint('collection_id', 'integration_id', name='uq_collection_integration'),
    )