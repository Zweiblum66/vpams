"""Beta user schemas"""

from pydantic import BaseModel, Field, EmailStr, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID


class BetaRegistrationRequest(BaseModel):
    """Beta registration request"""
    user_id: UUID
    email: EmailStr
    full_name: str
    company: Optional[str] = None
    role: Optional[str] = None
    use_case: Optional[str] = None
    interested_features: Optional[List[str]] = Field(default_factory=list)
    technical_level: Optional[str] = Field(None, regex="^(beginner|intermediate|advanced)$")
    invitation_code: Optional[str] = None
    
    @validator('interested_features')
    def limit_features(cls, v):
        if v and len(v) > 10:
            raise ValueError("Maximum 10 features can be selected")
        return v


class BetaRegistrationResponse(BaseModel):
    """Beta registration response"""
    success: bool
    message: str
    beta_user_id: str
    beta_phase: str
    feature_access_level: str


class BetaUserCreate(BaseModel):
    """Create beta user"""
    user_id: UUID
    email: EmailStr
    full_name: str
    company: Optional[str] = None
    role: Optional[str] = None
    beta_phase: str = "closed_beta"
    feature_access_level: str = "standard"
    email_updates: bool = True
    feature_announcements: bool = True
    survey_participation: bool = True
    use_case: Optional[str] = None
    interested_features: Optional[List[str]] = Field(default_factory=list)
    technical_level: Optional[str] = None


class BetaUserUpdate(BaseModel):
    """Update beta user"""
    full_name: Optional[str] = None
    company: Optional[str] = None
    role: Optional[str] = None
    email_updates: Optional[bool] = None
    feature_announcements: Optional[bool] = None
    survey_participation: Optional[bool] = None
    use_case: Optional[str] = None
    interested_features: Optional[List[str]] = None
    technical_level: Optional[str] = None
    
    # Admin only fields
    is_active: Optional[bool] = None
    feature_access_level: Optional[str] = None
    beta_phase: Optional[str] = None
    engagement_score: Optional[int] = Field(None, ge=0, le=100)
    notes: Optional[str] = None
    tags: Optional[List[str]] = None


class BetaUserResponse(BaseModel):
    """Beta user response"""
    id: UUID
    user_id: UUID
    email: str
    full_name: Optional[str]
    company: Optional[str]
    role: Optional[str]
    joined_at: datetime
    beta_phase: str
    is_active: bool
    last_active: Optional[datetime]
    feature_access_level: str
    email_updates: bool
    feature_announcements: bool
    survey_participation: bool
    use_case: Optional[str]
    interested_features: List[str]
    technical_level: Optional[str]
    feedback_count: int
    bug_reports_count: int
    feature_requests_count: int
    engagement_score: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True


class BetaUserListResponse(BaseModel):
    """Beta user list response"""
    users: List[BetaUserResponse]
    total: int
    page: int
    limit: int
    pages: int


class BetaInvitationCreate(BaseModel):
    """Create beta invitation"""
    email: EmailStr
    invitation_type: str = "standard"
    valid_until: Optional[datetime] = None
    max_uses: int = 1
    notes: Optional[str] = None


class BetaInvitationResponse(BaseModel):
    """Beta invitation response"""
    id: UUID
    code: str
    email: str
    invitation_type: str
    valid_until: Optional[datetime]
    created_at: datetime
    
    class Config:
        orm_mode = True