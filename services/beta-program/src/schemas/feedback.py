"""Feedback schemas"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID

from ..models.feedback import FeedbackCategory, FeedbackStatus


class FeedbackCreate(BaseModel):
    """Create feedback"""
    category: FeedbackCategory
    title: str = Field(..., min_length=5, max_length=255)
    description: str = Field(..., min_length=20)
    
    # Context
    feature_id: Optional[UUID] = None
    page_url: Optional[str] = None
    user_agent: Optional[str] = None
    
    # Bug report specific
    severity: Optional[str] = Field(None, regex="^(low|medium|high|critical)$")
    reproducible: Optional[bool] = None
    steps_to_reproduce: Optional[str] = None
    expected_behavior: Optional[str] = None
    actual_behavior: Optional[str] = None
    
    # Feature request specific
    use_case: Optional[str] = None
    business_value: Optional[str] = None
    priority_reasoning: Optional[str] = None
    
    # Attachments
    screenshots: Optional[List[str]] = Field(default_factory=list)
    logs: Optional[List[str]] = Field(default_factory=list)
    attachments: Optional[List[str]] = Field(default_factory=list)


class FeedbackUpdate(BaseModel):
    """Update feedback"""
    title: Optional[str] = Field(None, min_length=5, max_length=255)
    description: Optional[str] = Field(None, min_length=20)
    
    # Bug report specific
    severity: Optional[str] = None
    reproducible: Optional[bool] = None
    steps_to_reproduce: Optional[str] = None
    expected_behavior: Optional[str] = None
    actual_behavior: Optional[str] = None
    
    # Feature request specific
    use_case: Optional[str] = None
    business_value: Optional[str] = None
    priority_reasoning: Optional[str] = None
    
    # Attachments
    screenshots: Optional[List[str]] = None
    logs: Optional[List[str]] = None
    attachments: Optional[List[str]] = None
    
    # Admin only fields
    status: Optional[FeedbackStatus] = None
    priority: Optional[int] = Field(None, ge=1, le=5)
    assigned_to: Optional[str] = None
    resolution: Optional[str] = None
    github_issue_url: Optional[str] = None
    jira_ticket_id: Optional[str] = None
    internal_notes: Optional[str] = None
    tags: Optional[List[str]] = None


class FeedbackResponse(BaseModel):
    """Feedback response"""
    id: UUID
    beta_user_id: UUID
    category: FeedbackCategory
    title: str
    description: str
    
    # Context
    feature_id: Optional[UUID]
    page_url: Optional[str]
    
    # Bug report specific
    severity: Optional[str]
    reproducible: Optional[bool]
    steps_to_reproduce: Optional[str]
    expected_behavior: Optional[str]
    actual_behavior: Optional[str]
    
    # Feature request specific
    use_case: Optional[str]
    business_value: Optional[str]
    priority_reasoning: Optional[str]
    
    # Attachments
    screenshots: List[str]
    logs: List[str]
    attachments: List[str]
    
    # Status and tracking
    status: FeedbackStatus
    priority: int
    assigned_to: Optional[str]
    
    # Resolution
    resolution: Optional[str]
    resolved_at: Optional[datetime]
    resolved_by: Optional[str]
    
    # Related items
    related_feedback_ids: Optional[List[UUID]]
    duplicate_of: Optional[UUID]
    github_issue_url: Optional[str]
    jira_ticket_id: Optional[str]
    
    # Voting and engagement
    upvotes: int
    downvotes: int
    comment_count: int
    
    # Metadata
    tags: Optional[List[str]]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True


class FeedbackListResponse(BaseModel):
    """Feedback list response"""
    feedback: List[FeedbackResponse]
    total: int
    page: int
    limit: int
    pages: int


class FeedbackVoteRequest(BaseModel):
    """Vote on feedback"""
    vote_type: str = Field(..., regex="^(upvote|downvote)$")