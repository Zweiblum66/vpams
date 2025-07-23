"""
Pydantic models for MAMS SDK
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel as PydanticBaseModel, Field


class BaseModel(PydanticBaseModel):
    """Base model for all MAMS entities"""
    id: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        use_enum_values = True
        validate_assignment = True


# Asset Models
class Asset(BaseModel):
    """Asset model"""
    name: str
    type: str  # video, audio, image, document
    file_path: str
    size_bytes: int
    checksum: Optional[str] = None
    mime_type: Optional[str] = None
    
    # Media properties
    duration: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    frame_rate: Optional[float] = None
    bitrate: Optional[int] = None
    
    # Status
    status: str = "active"  # active, archived, deleted
    processing_status: str = "completed"  # pending, processing, completed, failed
    
    # Relationships
    project_id: Optional[str] = None
    parent_id: Optional[str] = None  # For versions
    version: int = 1
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)


class AssetCreate(PydanticBaseModel):
    """Asset creation model"""
    name: str
    type: str
    file_path: Optional[str] = None
    project_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)


class AssetUpdate(PydanticBaseModel):
    """Asset update model"""
    name: Optional[str] = None
    status: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None


# Project Models
class Project(BaseModel):
    """Project model"""
    name: str
    description: Optional[str] = None
    status: str = "active"  # active, archived, completed
    
    # Settings
    frame_rate: float = 25.0
    resolution: str = "1920x1080"
    color_space: str = "Rec.709"
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Relationships
    owner_id: str
    team_members: List[str] = Field(default_factory=list)


class ProjectCreate(PydanticBaseModel):
    """Project creation model"""
    name: str
    description: Optional[str] = None
    frame_rate: float = 25.0
    resolution: str = "1920x1080"
    color_space: str = "Rec.709"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ProjectUpdate(PydanticBaseModel):
    """Project update model"""
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


# Workflow Models
class Workflow(BaseModel):
    """Workflow model"""
    name: str
    description: Optional[str] = None
    status: str = "active"  # active, inactive, deprecated
    
    # Definition
    definition: Dict[str, Any]
    version: int = 1
    
    # Settings
    timeout: Optional[int] = None  # in seconds
    max_retries: int = 3
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Relationships
    created_by: str
    template_id: Optional[str] = None


class WorkflowCreate(PydanticBaseModel):
    """Workflow creation model"""
    name: str
    description: Optional[str] = None
    definition: Dict[str, Any]
    timeout: Optional[int] = None
    max_retries: int = 3
    metadata: Dict[str, Any] = Field(default_factory=dict)


class WorkflowUpdate(PydanticBaseModel):
    """Workflow update model"""
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    definition: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


# Integration Models
class Integration(BaseModel):
    """Integration model"""
    name: str
    type: str  # slack, teams, zapier, webhook, etc.
    status: str = "active"  # active, inactive, error
    
    # Configuration
    config: Dict[str, Any]
    
    # Settings
    enabled: bool = True
    auto_sync: bool = True
    sync_interval: int = 3600  # seconds
    
    # Status
    last_sync: Optional[datetime] = None
    last_error: Optional[str] = None
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Relationships
    created_by: str


class IntegrationCreate(PydanticBaseModel):
    """Integration creation model"""
    name: str
    type: str
    config: Dict[str, Any]
    enabled: bool = True
    auto_sync: bool = True
    sync_interval: int = 3600
    metadata: Dict[str, Any] = Field(default_factory=dict)


class IntegrationUpdate(PydanticBaseModel):
    """Integration update model"""
    name: Optional[str] = None
    status: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    enabled: Optional[bool] = None
    auto_sync: Optional[bool] = None
    sync_interval: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


# User Models
class User(BaseModel):
    """User model"""
    username: str
    email: str
    first_name: str
    last_name: str
    
    # Status
    is_active: bool = True
    is_verified: bool = False
    
    # Profile
    avatar_url: Optional[str] = None
    timezone: str = "UTC"
    language: str = "en"
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Timestamps
    last_login: Optional[datetime] = None


class UserCreate(PydanticBaseModel):
    """User creation model"""
    username: str
    email: str
    first_name: str
    last_name: str
    password: str
    timezone: str = "UTC"
    language: str = "en"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class UserUpdate(PydanticBaseModel):
    """User update model"""
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    avatar_url: Optional[str] = None
    timezone: Optional[str] = None
    language: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


# Response Models
class ListResponse(PydanticBaseModel):
    """Generic list response"""
    data: List[Any]
    meta: Dict[str, Any] = Field(default_factory=dict)
    links: Dict[str, str] = Field(default_factory=dict)


class ErrorResponse(PydanticBaseModel):
    """Error response model"""
    error: Dict[str, Any]