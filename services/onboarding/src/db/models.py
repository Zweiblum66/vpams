"""
Database models for Onboarding Service
"""
from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Text, JSON,
    ForeignKey, Enum, DECIMAL, Float, UniqueConstraint, Index
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from datetime import datetime
from enum import Enum as PyEnum

from src.db.base import Base


class FlowType(PyEnum):
    """Types of onboarding flows"""
    ORGANIZATION_SETUP = "organization_setup"
    USER_ONBOARDING = "user_onboarding"
    FEATURE_INTRODUCTION = "feature_introduction"
    ROLE_SPECIFIC = "role_specific"
    INTEGRATION_SETUP = "integration_setup"
    CUSTOM = "custom"


class StepType(PyEnum):
    """Types of onboarding steps"""
    INFORMATION = "information"
    FORM = "form"
    TUTORIAL = "tutorial"
    VIDEO = "video"
    INTERACTIVE = "interactive"
    QUIZ = "quiz"
    ACTION = "action"
    EXTERNAL = "external"


class ProgressStatus(PyEnum):
    """Status of onboarding progress"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


class UserRole(PyEnum):
    """User roles for role-specific onboarding"""
    ADMIN = "admin"
    CONTENT_CREATOR = "content_creator"
    EDITOR = "editor"
    VIEWER = "viewer"
    DEVELOPER = "developer"


class OnboardingFlow(Base):
    """Onboarding flow definitions"""
    __tablename__ = "onboarding_flows"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    type = Column(Enum(FlowType), nullable=False)
    
    # Target audience
    target_roles = Column(JSON, default=list)  # List of roles
    is_mandatory = Column(Boolean, default=False)
    
    # Flow configuration
    estimated_duration_minutes = Column(Integer, default=30)
    prerequisites = Column(JSON, default=list)  # List of flow IDs
    
    # Versioning
    version = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    
    # Metadata
    metadata = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    steps = relationship("OnboardingStep", back_populates="flow", order_by="OnboardingStep.order")
    user_progress = relationship("UserOnboardingProgress", back_populates="flow")


class OnboardingStep(Base):
    """Individual steps within an onboarding flow"""
    __tablename__ = "onboarding_steps"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    flow_id = Column(UUID(as_uuid=True), ForeignKey("onboarding_flows.id"), nullable=False)
    
    # Step details
    title = Column(String(255), nullable=False)
    description = Column(Text)
    type = Column(Enum(StepType), nullable=False)
    order = Column(Integer, nullable=False)
    
    # Content
    content = Column(JSON, default=dict)  # Step-specific content
    action_url = Column(String(500))  # URL for action steps
    validation_rules = Column(JSON, default=list)  # For form/quiz steps
    
    # Configuration
    is_optional = Column(Boolean, default=False)
    estimated_duration_minutes = Column(Integer, default=5)
    requires_completion = Column(Boolean, default=True)
    
    # Success criteria
    success_criteria = Column(JSON, default=dict)
    
    # Metadata
    metadata = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    flow = relationship("OnboardingFlow", back_populates="steps")
    step_progress = relationship("StepProgress", back_populates="step")
    
    # Indexes
    __table_args__ = (
        Index('idx_step_flow_order', 'flow_id', 'order'),
    )


class UserOnboardingProgress(Base):
    """Track user progress through onboarding flows"""
    __tablename__ = "user_onboarding_progress"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    organization_id = Column(UUID(as_uuid=True), nullable=False)
    flow_id = Column(UUID(as_uuid=True), ForeignKey("onboarding_flows.id"), nullable=False)
    
    # Progress tracking
    status = Column(Enum(ProgressStatus), default=ProgressStatus.NOT_STARTED)
    current_step_id = Column(UUID(as_uuid=True), ForeignKey("onboarding_steps.id"))
    completed_steps = Column(Integer, default=0)
    total_steps = Column(Integer, nullable=False)
    
    # Timing
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    last_activity_at = Column(DateTime(timezone=True))
    time_spent_minutes = Column(Integer, default=0)
    
    # Completion
    completion_percentage = Column(Float, default=0.0)
    is_completed = Column(Boolean, default=False)
    skipped_reason = Column(Text)
    
    # Metadata
    metadata = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    flow = relationship("OnboardingFlow", back_populates="user_progress")
    step_progress = relationship("StepProgress", back_populates="user_progress")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('user_id', 'flow_id', name='uix_user_flow'),
        Index('idx_user_progress', 'user_id', 'status'),
        Index('idx_org_progress', 'organization_id', 'status'),
    )


class StepProgress(Base):
    """Track progress on individual steps"""
    __tablename__ = "step_progress"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_progress_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("user_onboarding_progress.id"), 
        nullable=False
    )
    step_id = Column(UUID(as_uuid=True), ForeignKey("onboarding_steps.id"), nullable=False)
    
    # Progress
    status = Column(Enum(ProgressStatus), default=ProgressStatus.NOT_STARTED)
    attempts = Column(Integer, default=0)
    
    # Timing
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    time_spent_seconds = Column(Integer, default=0)
    
    # Step-specific data
    response_data = Column(JSON, default=dict)  # For forms/quizzes
    score = Column(Float)  # For quizzes
    
    # Metadata
    metadata = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user_progress = relationship("UserOnboardingProgress", back_populates="step_progress")
    step = relationship("OnboardingStep", back_populates="step_progress")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('user_progress_id', 'step_id', name='uix_progress_step'),
    )


class Tutorial(Base):
    """Interactive tutorials and guides"""
    __tablename__ = "tutorials"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    category = Column(String(100))
    
    # Content
    content_type = Column(String(50))  # video, interactive, article
    content_url = Column(String(500))
    duration_minutes = Column(Integer)
    difficulty_level = Column(String(20))  # beginner, intermediate, advanced
    
    # Targeting
    target_roles = Column(JSON, default=list)
    prerequisites = Column(JSON, default=list)  # Tutorial IDs
    
    # Analytics
    views = Column(Integer, default=0)
    completions = Column(Integer, default=0)
    avg_rating = Column(DECIMAL(3, 2))
    
    # Status
    is_active = Column(Boolean, default=True)
    is_featured = Column(Boolean, default=False)
    
    # Metadata
    tags = Column(JSON, default=list)
    metadata = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    completions = relationship("TutorialCompletion", back_populates="tutorial")


class TutorialCompletion(Base):
    """Track tutorial completions"""
    __tablename__ = "tutorial_completions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    tutorial_id = Column(UUID(as_uuid=True), ForeignKey("tutorials.id"), nullable=False)
    
    # Completion details
    completed_at = Column(DateTime(timezone=True), server_default=func.now())
    time_spent_minutes = Column(Integer)
    rating = Column(Integer)  # 1-5 stars
    feedback = Column(Text)
    
    # Relationships
    tutorial = relationship("Tutorial", back_populates="completions")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('user_id', 'tutorial_id', name='uix_user_tutorial'),
    )


class OnboardingGoal(Base):
    """Define onboarding goals and milestones"""
    __tablename__ = "onboarding_goals"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    
    # Goal configuration
    target_metric = Column(String(100))  # e.g., "flows_completed", "features_used"
    target_value = Column(Integer)
    time_limit_days = Column(Integer)
    
    # Rewards
    reward_type = Column(String(50))  # badge, feature_unlock, certification
    reward_data = Column(JSON, default=dict)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    achievements = relationship("UserAchievement", back_populates="goal")


class UserAchievement(Base):
    """Track user achievements and milestones"""
    __tablename__ = "user_achievements"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    goal_id = Column(UUID(as_uuid=True), ForeignKey("onboarding_goals.id"), nullable=False)
    
    # Achievement details
    achieved_at = Column(DateTime(timezone=True), server_default=func.now())
    progress_data = Column(JSON, default=dict)
    
    # Relationships
    goal = relationship("OnboardingGoal", back_populates="achievements")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('user_id', 'goal_id', name='uix_user_goal'),
    )


class OnboardingAnalytics(Base):
    """Analytics data for onboarding performance"""
    __tablename__ = "onboarding_analytics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    date = Column(DateTime(timezone=True), nullable=False)
    organization_id = Column(UUID(as_uuid=True))
    
    # Metrics
    new_users = Column(Integer, default=0)
    flows_started = Column(Integer, default=0)
    flows_completed = Column(Integer, default=0)
    steps_completed = Column(Integer, default=0)
    avg_completion_time_minutes = Column(Float)
    completion_rate = Column(Float)
    
    # Detailed metrics
    metrics_by_flow = Column(JSON, default=dict)
    metrics_by_role = Column(JSON, default=dict)
    dropout_points = Column(JSON, default=list)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Indexes
    __table_args__ = (
        Index('idx_analytics_date_org', 'date', 'organization_id'),
    )