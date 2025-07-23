"""
Pydantic schemas for API request/response models
"""

from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, field_validator, ConfigDict
from enum import Enum

from ..db.models import (
    FieldType, FieldDefinition, SchemaStatus, 
    MetadataSchema, MetadataDocument
)


class PaginationParams(BaseModel):
    """Pagination parameters"""
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)
    
    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class PaginatedResponse(BaseModel):
    """Paginated response wrapper"""
    items: List[Any]
    total: int
    page: int
    page_size: int
    pages: int


# Schema Models
class SchemaCreate(BaseModel):
    """Create a new metadata schema"""
    name: str = Field(..., min_length=1, max_length=100)
    display_name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    category: str = Field(..., min_length=1, max_length=50)
    asset_types: List[str] = Field(default_factory=list)
    fields: List[FieldDefinition] = Field(..., min_items=1)
    parent_schema_id: Optional[UUID] = None
    inherit_fields: bool = Field(default=True)
    allow_custom_fields: bool = Field(default=True)
    strict_mode: bool = Field(default=False)
    
    @field_validator('name')
    def validate_name(cls, v):
        """Ensure name is valid identifier"""
        import re
        if not re.match(r'^[a-z][a-z0-9_]*$', v):
            raise ValueError('Name must start with lowercase letter and contain only lowercase letters, numbers, and underscores')
        return v
    
    @field_validator('fields')
    def validate_fields(cls, v):
        """Ensure field names are unique"""
        names = [f.name for f in v]
        if len(names) != len(set(names)):
            raise ValueError('Field names must be unique')
        return v


class SchemaUpdate(BaseModel):
    """Update metadata schema"""
    display_name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    asset_types: Optional[List[str]] = None
    fields: Optional[List[FieldDefinition]] = None
    allow_custom_fields: Optional[bool] = None
    strict_mode: Optional[bool] = None
    status: Optional[SchemaStatus] = None
    
    @field_validator('fields')
    def validate_fields(cls, v):
        """Ensure field names are unique if provided"""
        if v is not None:
            names = [f.name for f in v]
            if len(names) != len(set(names)):
                raise ValueError('Field names must be unique')
        return v


class SchemaResponse(BaseModel):
    """Schema response model"""
    id: str
    schema_id: UUID
    name: str
    display_name: str
    description: Optional[str]
    version: int
    category: str
    asset_types: List[str]
    fields: List[FieldDefinition]
    all_fields: List[FieldDefinition]  # Including inherited fields
    parent_schema_id: Optional[UUID]
    inherit_fields: bool
    status: SchemaStatus
    is_system: bool
    is_default: bool
    created_by: UUID
    created_at: datetime
    updated_by: Optional[UUID]
    updated_at: Optional[datetime]
    allow_custom_fields: bool
    strict_mode: bool
    
    model_config = ConfigDict(from_attributes=True)


# Metadata Models
class MetadataCreate(BaseModel):
    """Create metadata for an asset"""
    asset_id: UUID
    schema_id: UUID
    metadata: Dict[str, Any]
    custom_fields: Optional[Dict[str, Any]] = None
    source: str = Field(default="manual")
    source_details: Optional[Dict[str, Any]] = None


class MetadataUpdate(BaseModel):
    """Update metadata"""
    metadata: Optional[Dict[str, Any]] = None
    custom_fields: Optional[Dict[str, Any]] = None
    merge: bool = Field(default=True, description="Merge with existing data or replace")


class MetadataResponse(BaseModel):
    """Metadata response model"""
    id: str
    asset_id: UUID
    schema_id: UUID
    schema_version: int
    metadata: Dict[str, Any]
    custom_fields: Dict[str, Any]
    is_valid: bool
    validation_errors: List[Dict[str, Any]]
    version: int = Field(default=1, description="Document version")
    is_current: bool = Field(default=True, description="Whether this is the current version")
    parent_version_id: Optional[str] = Field(None, description="ID of parent version")
    created_by: UUID
    created_at: datetime
    updated_by: Optional[UUID]
    updated_at: Optional[datetime]
    source: str
    source_details: Dict[str, Any]
    
    model_config = ConfigDict(from_attributes=True)


# Extraction Models
class ExtractionType(str, Enum):
    """Types of metadata extraction"""
    TECHNICAL = "technical"
    EXIF = "exif"
    XMP = "xmp"
    IPTC = "iptc"
    ID3 = "id3"
    AI_TAGS = "ai_tags"
    TRANSCRIPTION = "transcription"
    OCR = "ocr"
    FACE_DETECTION = "face_detection"


class ExtractionRequest(BaseModel):
    """Request metadata extraction"""
    extraction_types: List[ExtractionType]
    overwrite: bool = Field(default=False, description="Overwrite existing metadata")
    options: Optional[Dict[str, Any]] = Field(default_factory=dict)


class ExtractionStatus(BaseModel):
    """Extraction task status"""
    task_id: UUID
    asset_id: UUID
    status: str
    progress: float
    extraction_types: List[str]
    results: Optional[Dict[str, Any]]
    errors: List[Dict[str, Any]]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    processing_time: Optional[float]


# Validation Models
class ValidationResult(BaseModel):
    """Metadata validation result"""
    valid: bool
    errors: List[Dict[str, Any]]
    warnings: List[Dict[str, Any]]
    validated_data: Dict[str, Any]
    custom_fields: Dict[str, Any]


# Search Models
class SearchQuery(BaseModel):
    """Metadata search query"""
    query: Dict[str, Any]
    schema_ids: Optional[List[UUID]] = None
    asset_types: Optional[List[str]] = None
    sort_by: Optional[str] = None
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")


class SearchResult(BaseModel):
    """Search result item"""
    asset_id: UUID
    metadata_id: str
    schema_id: UUID
    schema_name: str
    metadata: Dict[str, Any]
    highlights: Optional[Dict[str, List[str]]] = None
    score: Optional[float] = None


# Template Models
class TemplateCreate(BaseModel):
    """Create metadata template"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    schema_id: UUID
    default_values: Dict[str, Any]
    category: str
    tags: List[str] = Field(default_factory=list)
    is_public: bool = Field(default=False)
    shared_with: List[UUID] = Field(default_factory=list)


class TemplateResponse(BaseModel):
    """Template response model"""
    id: str
    template_id: UUID
    name: str
    description: Optional[str]
    schema_id: UUID
    default_values: Dict[str, Any]
    category: str
    tags: List[str]
    is_public: bool
    owner_id: UUID
    shared_with: List[UUID]
    created_at: datetime
    updated_at: Optional[datetime]
    usage_count: int
    
    model_config = ConfigDict(from_attributes=True)


# Error Response
class ErrorResponse(BaseModel):
    """Standard error response"""
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: Optional[str] = None