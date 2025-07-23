"""
Pydantic schemas for Onboarding Service
"""
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID
from enum import Enum

from src.db.models import (
    FlowType, StepType, ProgressStatus, UserRole
)


# Base schemas
class OnboardingFlowBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    type: FlowType
    target_roles: List[UserRole] = []
    is_mandatory: bool = False
    estimated_duration_minutes: int = Field(30, ge=1)
    prerequisites: List[UUID] = []


class OnboardingFlowCreate(OnboardingFlowBase):
    metadata: Dict[str, Any] = {}


class OnboardingFlowUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    target_roles: Optional[List[UserRole]] = None
    is_mandatory: Optional[bool] = None
    estimated_duration_minutes: Optional[int] = None
    prerequisites: Optional[List[UUID]] = None
    metadata: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class OnboardingFlowResponse(OnboardingFlowBase):
    id: UUID
    version: int
    is_active: bool
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: Optional[datetime]
    steps: List["OnboardingStepResponse"] = []
    
    class Config:
        orm_mode = True


# Step schemas
class OnboardingStepBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    type: StepType
    order: int = Field(..., ge=0)
    content: Dict[str, Any] = {}
    action_url: Optional[str] = None
    validation_rules: List[Dict[str, Any]] = []
    is_optional: bool = False
    estimated_duration_minutes: int = Field(5, ge=1)
    requires_completion: bool = True
    success_criteria: Dict[str, Any] = {}


class OnboardingStepCreate(OnboardingStepBase):
    flow_id: UUID
    metadata: Dict[str, Any] = {}


class OnboardingStepUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    content: Optional[Dict[str, Any]] = None
    action_url: Optional[str] = None
    validation_rules: Optional[List[Dict[str, Any]]] = None
    is_optional: Optional[bool] = None
    estimated_duration_minutes: Optional[int] = None
    requires_completion: Optional[bool] = None
    success_criteria: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class OnboardingStepResponse(OnboardingStepBase):
    id: UUID
    flow_id: UUID
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        orm_mode = True


# Progress schemas
class UserProgressBase(BaseModel):
    user_id: UUID
    organization_id: UUID
    flow_id: UUID


class UserProgressCreate(UserProgressBase):
    pass


class UserProgressUpdate(BaseModel):
    current_step_id: Optional[UUID] = None
    status: Optional[ProgressStatus] = None
    metadata: Optional[Dict[str, Any]] = None


class UserProgressResponse(UserProgressBase):
    id: UUID
    status: ProgressStatus
    current_step_id: Optional[UUID]
    completed_steps: int
    total_steps: int
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    last_activity_at: Optional[datetime]
    time_spent_minutes: int
    completion_percentage: float
    is_completed: bool
    skipped_reason: Optional[str]
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: Optional[datetime]
    flow: Optional[OnboardingFlowResponse]
    step_progress: List["StepProgressResponse"] = []
    
    class Config:
        orm_mode = True


# Step progress schemas
class StepProgressBase(BaseModel):
    step_id: UUID
    status: ProgressStatus = ProgressStatus.NOT_STARTED
    response_data: Dict[str, Any] = {}


class StepProgressCreate(StepProgressBase):
    user_progress_id: UUID


class StepProgressUpdate(BaseModel):
    status: Optional[ProgressStatus] = None
    response_data: Optional[Dict[str, Any]] = None
    score: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


class StepProgressResponse(StepProgressBase):
    id: UUID
    user_progress_id: UUID
    attempts: int
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    time_spent_seconds: int
    score: Optional[float]
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: Optional[datetime]
    step: Optional[OnboardingStepResponse]
    
    class Config:
        orm_mode = True


# Tutorial schemas
class TutorialBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    category: Optional[str] = None
    content_type: str
    content_url: str
    duration_minutes: Optional[int] = None
    difficulty_level: Optional[str] = None
    target_roles: List[UserRole] = []
    prerequisites: List[UUID] = []


class TutorialCreate(TutorialBase):
    tags: List[str] = []
    metadata: Dict[str, Any] = {}


class TutorialUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    content_url: Optional[str] = None
    duration_minutes: Optional[int] = None
    difficulty_level: Optional[str] = None
    target_roles: Optional[List[UserRole]] = None
    prerequisites: Optional[List[UUID]] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    is_featured: Optional[bool] = None


class TutorialResponse(TutorialBase):
    id: UUID
    views: int
    completions: int
    avg_rating: Optional[float]
    is_active: bool
    is_featured: bool
    tags: List[str]
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        orm_mode = True


# Tutorial completion schemas
class TutorialCompletionCreate(BaseModel):
    user_id: UUID
    tutorial_id: UUID
    time_spent_minutes: Optional[int] = None
    rating: Optional[int] = Field(None, ge=1, le=5)
    feedback: Optional[str] = None


class TutorialCompletionResponse(BaseModel):
    id: UUID
    user_id: UUID
    tutorial_id: UUID
    completed_at: datetime
    time_spent_minutes: Optional[int]
    rating: Optional[int]
    feedback: Optional[str]
    tutorial: Optional[TutorialResponse]
    
    class Config:
        orm_mode = True


# Goal schemas
class OnboardingGoalBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    target_metric: str
    target_value: int = Field(..., ge=1)
    time_limit_days: Optional[int] = None
    reward_type: Optional[str] = None
    reward_data: Dict[str, Any] = {}


class OnboardingGoalCreate(OnboardingGoalBase):
    pass


class OnboardingGoalResponse(OnboardingGoalBase):
    id: UUID
    is_active: bool
    created_at: datetime
    
    class Config:
        orm_mode = True


# Achievement schemas
class UserAchievementResponse(BaseModel):
    id: UUID
    user_id: UUID
    goal_id: UUID
    achieved_at: datetime
    progress_data: Dict[str, Any]
    goal: Optional[OnboardingGoalResponse]
    
    class Config:
        orm_mode = True


# Analytics schemas
class OnboardingAnalyticsResponse(BaseModel):
    id: UUID
    date: datetime
    organization_id: Optional[UUID]
    new_users: int
    flows_started: int
    flows_completed: int
    steps_completed: int
    avg_completion_time_minutes: Optional[float]
    completion_rate: Optional[float]
    metrics_by_flow: Dict[str, Any]
    metrics_by_role: Dict[str, Any]
    dropout_points: List[Dict[str, Any]]
    created_at: datetime
    
    class Config:
        orm_mode = True


class AnalyticsSummary(BaseModel):
    total_users: int
    active_users: int
    completed_users: int
    average_completion_rate: float
    average_time_to_complete: float
    most_completed_flow: Optional[str]
    most_skipped_step: Optional[str]
    completion_by_role: Dict[str, float]
    trend_data: List[Dict[str, Any]]


# Request/Response models
class StartFlowRequest(BaseModel):
    user_id: UUID
    organization_id: UUID


class CompleteStepRequest(BaseModel):
    response_data: Optional[Dict[str, Any]] = {}
    time_spent_seconds: Optional[int] = None


class SkipStepRequest(BaseModel):
    reason: Optional[str] = None


class FlowProgressSummary(BaseModel):
    flow_id: UUID
    flow_name: str
    status: ProgressStatus
    completion_percentage: float
    completed_steps: int
    total_steps: int
    estimated_time_remaining: int
    last_activity: Optional[datetime]


class UserOnboardingSummary(BaseModel):
    user_id: UUID
    total_flows: int
    completed_flows: int
    in_progress_flows: int
    overall_completion: float
    total_time_spent: int
    achievements: List[UserAchievementResponse]
    active_flows: List[FlowProgressSummary]
    recommended_tutorials: List[TutorialResponse]


# Update forward references
OnboardingFlowResponse.update_forward_refs()
UserProgressResponse.update_forward_refs()
StepProgressResponse.update_forward_refs()
TutorialCompletionResponse.update_forward_refs()
UserAchievementResponse.update_forward_refs()