"""Beta user models"""

from sqlalchemy import Column, String, DateTime, Boolean, Integer, Text, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime

from ..core.database import Base


class BetaUser(Base):
    """Beta program user"""
    __tablename__ = "beta_users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, unique=True, index=True)
    email = Column(String(255), nullable=False, index=True)
    full_name = Column(String(255))
    company = Column(String(255))
    role = Column(String(100))  # developer, designer, product_manager, etc.
    
    # Beta program details
    joined_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    invitation_code = Column(String(100), index=True)
    referred_by = Column(UUID(as_uuid=True), ForeignKey("beta_users.id"))
    beta_phase = Column(String(50), default="closed_beta")  # closed_beta, open_beta, release_candidate
    
    # Access and activity
    is_active = Column(Boolean, default=True)
    last_active = Column(DateTime(timezone=True))
    feature_access_level = Column(String(50), default="standard")  # standard, advanced, full
    
    # Communication preferences
    email_updates = Column(Boolean, default=True)
    feature_announcements = Column(Boolean, default=True)
    survey_participation = Column(Boolean, default=True)
    
    # Profile and interests
    use_case = Column(Text)  # How they plan to use MAMS
    interested_features = Column(JSON)  # List of features they're interested in
    technical_level = Column(String(50))  # beginner, intermediate, advanced
    
    # Metrics
    feedback_count = Column(Integer, default=0)
    bug_reports_count = Column(Integer, default=0)
    feature_requests_count = Column(Integer, default=0)
    engagement_score = Column(Integer, default=0)  # 0-100
    
    # Metadata
    notes = Column(Text)  # Admin notes
    tags = Column(JSON)  # Admin tags for segmentation
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    feature_access = relationship("UserFeatureAccess", back_populates="beta_user", cascade="all, delete-orphan")
    feedback = relationship("Feedback", back_populates="beta_user", cascade="all, delete-orphan")
    referrals = relationship("BetaUser", backref="referrer", remote_side=[id])
    

class BetaInvitation(Base):
    """Beta program invitations"""
    __tablename__ = "beta_invitations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), nullable=False, index=True)
    
    # Invitation details
    invited_by = Column(UUID(as_uuid=True), ForeignKey("beta_users.id"))
    invitation_type = Column(String(50), default="standard")  # standard, vip, partner
    
    # Usage
    is_used = Column(Boolean, default=False)
    used_by = Column(UUID(as_uuid=True), ForeignKey("beta_users.id"))
    used_at = Column(DateTime(timezone=True))
    
    # Validity
    valid_from = Column(DateTime(timezone=True), default=datetime.utcnow)
    valid_until = Column(DateTime(timezone=True))
    max_uses = Column(Integer, default=1)
    current_uses = Column(Integer, default=0)
    
    # Metadata
    notes = Column(Text)
    metadata = Column(JSON)  # Additional invitation data
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)