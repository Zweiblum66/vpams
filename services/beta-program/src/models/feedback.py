"""Feedback models"""

from sqlalchemy import Column, String, DateTime, Boolean, Integer, Text, ForeignKey, JSON, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
import enum

from ..core.database import Base


class FeedbackCategory(str, enum.Enum):
    """Feedback categories"""
    BUG_REPORT = "bug_report"
    FEATURE_REQUEST = "feature_request"
    IMPROVEMENT = "improvement"
    USABILITY = "usability"
    PERFORMANCE = "performance"
    DOCUMENTATION = "documentation"
    OTHER = "other"


class FeedbackStatus(str, enum.Enum):
    """Feedback status"""
    NEW = "new"
    ACKNOWLEDGED = "acknowledged"
    IN_REVIEW = "in_review"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    WONT_FIX = "wont_fix"
    DUPLICATE = "duplicate"


class Feedback(Base):
    """Beta user feedback"""
    __tablename__ = "feedback"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    beta_user_id = Column(UUID(as_uuid=True), ForeignKey("beta_users.id"), nullable=False)
    
    # Feedback details
    category = Column(Enum(FeedbackCategory), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    
    # Context
    feature_id = Column(UUID(as_uuid=True), ForeignKey("feature_flags.id"))
    page_url = Column(String(500))
    user_agent = Column(Text)
    
    # Bug report specific
    severity = Column(String(20))  # low, medium, high, critical
    reproducible = Column(Boolean)
    steps_to_reproduce = Column(Text)
    expected_behavior = Column(Text)
    actual_behavior = Column(Text)
    
    # Feature request specific
    use_case = Column(Text)
    business_value = Column(Text)
    priority_reasoning = Column(Text)
    
    # Attachments
    screenshots = Column(JSON)  # List of screenshot URLs
    logs = Column(JSON)  # List of log file URLs
    attachments = Column(JSON)  # Other attachments
    
    # Status and tracking
    status = Column(Enum(FeedbackStatus), default=FeedbackStatus.NEW)
    priority = Column(Integer, default=3)  # 1-5, 1 being highest
    assigned_to = Column(String(255))
    
    # Resolution
    resolution = Column(Text)
    resolved_at = Column(DateTime(timezone=True))
    resolved_by = Column(String(255))
    
    # Related items
    related_feedback_ids = Column(JSON)  # List of related feedback IDs
    duplicate_of = Column(UUID(as_uuid=True), ForeignKey("feedback.id"))
    github_issue_url = Column(String(500))
    jira_ticket_id = Column(String(50))
    
    # Voting and engagement
    upvotes = Column(Integer, default=0)
    downvotes = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)
    
    # Communication
    user_notified = Column(Boolean, default=False)
    notification_sent_at = Column(DateTime(timezone=True))
    follow_up_required = Column(Boolean, default=False)
    
    # Metadata
    tags = Column(JSON)  # List of tags
    internal_notes = Column(Text)  # Admin notes
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    beta_user = relationship("BetaUser", back_populates="feedback")
    feature = relationship("FeatureFlag")