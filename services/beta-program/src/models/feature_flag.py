"""Feature flag models"""

from sqlalchemy import Column, String, DateTime, Boolean, Integer, Text, ForeignKey, JSON, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime

from ..core.database import Base


class FeatureFlag(Base):
    """Beta feature flags"""
    __tablename__ = "feature_flags"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False, index=True)
    display_name = Column(String(255), nullable=False)
    description = Column(Text)
    category = Column(String(50))  # ui, api, processing, experimental
    
    # Feature status
    is_enabled = Column(Boolean, default=False)
    rollout_percentage = Column(Integer, default=0)  # 0-100
    rollout_strategy = Column(String(50), default="percentage")  # percentage, whitelist, all_beta, specific_phase
    
    # Configuration
    config = Column(JSON)  # Feature-specific configuration
    dependencies = Column(JSON)  # List of required features
    incompatible_features = Column(JSON)  # List of incompatible features
    
    # Beta phases
    available_phases = Column(JSON, default=["closed_beta"])  # closed_beta, open_beta, release_candidate
    min_access_level = Column(String(50), default="standard")  # standard, advanced, full
    
    # A/B testing
    ab_test_enabled = Column(Boolean, default=False)
    ab_test_variants = Column(JSON)  # List of variants with percentages
    ab_test_metrics = Column(JSON)  # Metrics to track
    
    # Risk and stability
    risk_level = Column(String(20), default="low")  # low, medium, high
    stability_score = Column(Float, default=1.0)  # 0.0-1.0
    
    # Documentation
    documentation_url = Column(String(500))
    changelog = Column(JSON)  # List of changes with dates
    known_issues = Column(JSON)  # List of known issues
    
    # Metrics
    total_users = Column(Integer, default=0)
    active_users = Column(Integer, default=0)
    error_rate = Column(Float, default=0.0)
    
    # Metadata
    created_by = Column(String(255))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    released_at = Column(DateTime(timezone=True))
    deprecated_at = Column(DateTime(timezone=True))
    
    # Relationships
    user_access = relationship("UserFeatureAccess", back_populates="feature", cascade="all, delete-orphan")


class UserFeatureAccess(Base):
    """User access to beta features"""
    __tablename__ = "user_feature_access"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    beta_user_id = Column(UUID(as_uuid=True), ForeignKey("beta_users.id"), nullable=False)
    feature_id = Column(UUID(as_uuid=True), ForeignKey("feature_flags.id"), nullable=False)
    
    # Access details
    is_enabled = Column(Boolean, default=True)
    enabled_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    disabled_at = Column(DateTime(timezone=True))
    
    # A/B testing
    variant = Column(String(50))  # Control, variant_a, variant_b, etc.
    variant_assigned_at = Column(DateTime(timezone=True))
    
    # Usage metrics
    first_used_at = Column(DateTime(timezone=True))
    last_used_at = Column(DateTime(timezone=True))
    usage_count = Column(Integer, default=0)
    
    # Feedback
    satisfaction_score = Column(Integer)  # 1-5
    feedback_provided = Column(Boolean, default=False)
    
    # Metadata
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    beta_user = relationship("BetaUser", back_populates="feature_access")
    feature = relationship("FeatureFlag", back_populates="user_access")