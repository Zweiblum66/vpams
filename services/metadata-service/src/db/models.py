"""
MongoDB models for Metadata Service

This module defines the document schemas for MongoDB collections.
"""

from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, validator
from uuid import UUID, uuid4
from bson import ObjectId


class FieldType(str, Enum):
    """Supported metadata field types"""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    ARRAY = "array"
    OBJECT = "object"
    REFERENCE = "reference"  # Reference to another document
    ENUM = "enum"
    BINARY = "binary"
    TEXT = "text"  # Long text field
    URL = "url"
    EMAIL = "email"
    PHONE = "phone"
    JSON = "json"
    # Advanced custom field types
    CURRENCY = "currency"  # Currency amount with code
    PERCENTAGE = "percentage"  # Percentage value (0-100)
    DURATION = "duration"  # Time duration in seconds
    GEOLOCATION = "geolocation"  # GPS coordinates
    COLOR = "color"  # Color value (hex, rgb, etc.)
    RATING = "rating"  # Star rating (1-5)
    TAGS = "tags"  # Tag array with autocomplete
    RICH_TEXT = "rich_text"  # Rich text with formatting
    CODE = "code"  # Code with syntax highlighting
    MARKDOWN = "markdown"  # Markdown text
    TIMECODE = "timecode"  # Video timecode (HH:MM:SS:FF)
    RESOLUTION = "resolution"  # Video/image resolution (1920x1080)
    ASPECT_RATIO = "aspect_ratio"  # Aspect ratio (16:9)
    FILE_SIZE = "file_size"  # File size in bytes
    MIME_TYPE = "mime_type"  # MIME type
    IP_ADDRESS = "ip_address"  # IP address
    MAC_ADDRESS = "mac_address"  # MAC address
    UUID_TYPE = "uuid_type"  # UUID value
    REGEX = "regex"  # Regular expression
    SLIDER = "slider"  # Numeric slider with min/max
    
    
class FieldConstraint(str, Enum):
    """Field constraint types"""
    REQUIRED = "required"
    UNIQUE = "unique"
    MIN_LENGTH = "min_length"
    MAX_LENGTH = "max_length"
    MIN_VALUE = "min_value"
    MAX_VALUE = "max_value"
    PATTERN = "pattern"  # Regex pattern
    ENUM_VALUES = "enum_values"
    

class SchemaStatus(str, Enum):
    """Schema lifecycle status"""
    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class PyObjectId(ObjectId):
    """Custom ObjectId field that validates ObjectId"""
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(cls, schema, handler):
        json_schema = handler(schema)
        json_schema.update(type="string")
        return json_schema


class FieldDefinition(BaseModel):
    """Definition of a metadata field"""
    name: str = Field(..., description="Field name (must be unique within schema)")
    display_name: str = Field(..., description="Human-readable field name")
    description: Optional[str] = Field(None, description="Field description")
    field_type: FieldType = Field(..., description="Data type of the field")
    
    # Constraints
    required: bool = Field(default=False, description="Whether field is required")
    unique: bool = Field(default=False, description="Whether field must be unique")
    searchable: bool = Field(default=True, description="Include in search index")
    facetable: bool = Field(default=False, description="Enable faceted search")
    sortable: bool = Field(default=True, description="Allow sorting by this field")
    
    # Validation rules
    constraints: Dict[str, Any] = Field(default_factory=dict)
    # Examples: 
    # {"min_length": 3, "max_length": 100} for strings
    # {"min_value": 0, "max_value": 100} for numbers
    # {"pattern": "^[A-Z]{3}$"} for regex
    # {"enum_values": ["draft", "published", "archived"]} for enums
    
    # Default value
    default_value: Optional[Any] = None
    
    # UI hints
    ui_component: Optional[str] = Field(None, description="Suggested UI component")
    ui_options: Dict[str, Any] = Field(default_factory=dict)
    
    # Array/Object specific
    array_type: Optional[FieldType] = Field(None, description="Type of array elements")
    object_schema: Optional[List['FieldDefinition']] = Field(None, description="Schema for object fields")
    
    # Reference specific
    reference_collection: Optional[str] = Field(None, description="Collection for reference field")
    reference_field: Optional[str] = Field(None, description="Field to display for reference")
    
    class Config:
        schema_extra = {
            "example": {
                "name": "title",
                "display_name": "Title",
                "description": "Asset title",
                "field_type": "string",
                "required": True,
                "searchable": True,
                "constraints": {
                    "min_length": 1,
                    "max_length": 255
                }
            }
        }


# Allow recursive definition
FieldDefinition.update_forward_refs()


class MetadataSchema(BaseModel):
    """Schema definition for metadata"""
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    schema_id: UUID = Field(default_factory=uuid4, description="Unique schema identifier")
    name: str = Field(..., description="Schema name (unique)")
    display_name: str = Field(..., description="Human-readable schema name")
    description: Optional[str] = Field(None, description="Schema description")
    version: int = Field(default=1, description="Schema version")
    
    # Schema type/category
    category: str = Field(..., description="Schema category (e.g., 'video', 'image', 'document')")
    asset_types: List[str] = Field(default_factory=list, description="Compatible asset types")
    
    # Field definitions
    fields: List[FieldDefinition] = Field(..., description="Field definitions")
    
    # Inheritance
    parent_schema_id: Optional[UUID] = Field(None, description="Parent schema for inheritance")
    inherit_fields: bool = Field(default=True, description="Whether to inherit parent fields")
    
    # Status and lifecycle
    status: SchemaStatus = Field(default=SchemaStatus.DRAFT)
    is_system: bool = Field(default=False, description="System-defined schema (non-editable)")
    is_default: bool = Field(default=False, description="Default schema for category")
    
    # Metadata
    created_by: UUID = Field(..., description="User who created the schema")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_by: Optional[UUID] = None
    updated_at: Optional[datetime] = None
    
    # Settings
    allow_custom_fields: bool = Field(default=True, description="Allow custom fields beyond schema")
    strict_mode: bool = Field(default=False, description="Reject metadata that doesn't match schema")
    
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        schema_extra = {
            "example": {
                "name": "video_technical",
                "display_name": "Video Technical Metadata",
                "category": "video",
                "fields": [
                    {
                        "name": "duration",
                        "display_name": "Duration",
                        "field_type": "float",
                        "required": True,
                        "searchable": True,
                        "sortable": True
                    }
                ]
            }
        }


class MetadataDocument(BaseModel):
    """Metadata document stored in MongoDB"""
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    asset_id: UUID = Field(..., description="Associated asset ID")
    schema_id: UUID = Field(..., description="Schema used for this metadata")
    schema_version: int = Field(..., description="Version of schema used")
    
    # Core metadata fields (schema-defined)
    metadata: Dict[str, Any] = Field(..., description="Metadata values")
    
    # Custom fields (if allowed by schema)
    custom_fields: Dict[str, Any] = Field(default_factory=dict)
    
    # Validation status
    is_valid: bool = Field(default=True, description="Whether metadata passes schema validation")
    validation_errors: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Versioning
    version: int = Field(default=1, description="Document version")
    is_current: bool = Field(default=True, description="Whether this is the current version")
    parent_version_id: Optional[PyObjectId] = Field(None, description="ID of parent version")
    
    # Metadata about metadata
    created_by: UUID
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_by: Optional[UUID] = None
    updated_at: Optional[datetime] = None
    
    # Source information
    source: str = Field(default="manual", description="Source of metadata (manual, extracted, imported)")
    source_details: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class TechnicalMetadata(BaseModel):
    """Technical metadata extracted from files"""
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    asset_id: UUID = Field(..., description="Associated asset ID")
    
    # File information
    file_info: Dict[str, Any] = Field(..., description="Basic file information")
    # Example: {"size": 1234567, "mime_type": "video/mp4", "created": "2024-01-01T00:00:00Z"}
    
    # Format-specific metadata
    format_metadata: Dict[str, Any] = Field(default_factory=dict)
    # Video: {"codec": "h264", "bitrate": 5000000, "resolution": "1920x1080", "fps": 25}
    # Audio: {"codec": "aac", "bitrate": 192000, "sample_rate": 48000, "channels": 2}
    # Image: {"resolution": "3840x2160", "color_space": "sRGB", "bit_depth": 8}
    
    # Streams (for video/audio)
    streams: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Extracted metadata
    exif_data: Optional[Dict[str, Any]] = Field(None, description="EXIF data for images")
    xmp_data: Optional[Dict[str, Any]] = Field(None, description="XMP metadata")
    iptc_data: Optional[Dict[str, Any]] = Field(None, description="IPTC metadata")
    id3_data: Optional[Dict[str, Any]] = Field(None, description="ID3 tags for audio")
    
    # Extraction information
    extracted_at: datetime = Field(default_factory=datetime.utcnow)
    extraction_tool: str = Field(..., description="Tool used for extraction")
    extraction_version: str = Field(..., description="Version of extraction tool")
    extraction_errors: List[str] = Field(default_factory=list)
    
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class MetadataTemplate(BaseModel):
    """Reusable metadata template"""
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    template_id: UUID = Field(default_factory=uuid4)
    name: str = Field(..., description="Template name")
    description: Optional[str] = None
    
    # Schema and values
    schema_id: UUID = Field(..., description="Schema this template is based on")
    default_values: Dict[str, Any] = Field(..., description="Default metadata values")
    
    # Usage
    category: str = Field(..., description="Template category")
    tags: List[str] = Field(default_factory=list)
    
    # Ownership
    is_public: bool = Field(default=False)
    owner_id: UUID
    shared_with: List[UUID] = Field(default_factory=list)
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    usage_count: int = Field(default=0)
    
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class ExtractionTask(BaseModel):
    """Metadata extraction task"""
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    task_id: UUID = Field(default_factory=uuid4)
    asset_id: UUID = Field(..., description="Asset to extract metadata from")
    
    # Task configuration
    extraction_types: List[str] = Field(..., description="Types of extraction to perform")
    # Options: "technical", "exif", "xmp", "iptc", "id3", "ai_tags", "transcription"
    
    # File information
    file_path: str = Field(..., description="Path to file for extraction")
    file_size: int = Field(..., description="File size in bytes")
    mime_type: str = Field(..., description="MIME type of file")
    
    # Task status
    status: str = Field(default="pending")  # pending, processing, completed, failed
    progress: float = Field(default=0.0, ge=0.0, le=100.0)
    
    # Results
    results: Dict[str, Any] = Field(default_factory=dict)
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Timing
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    processing_time: Optional[float] = None  # seconds
    
    # Processing information
    worker_id: Optional[str] = None
    retry_count: int = Field(default=0)
    max_retries: int = Field(default=3)
    
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


# Indexes to create
INDEXES = [
    # MetadataSchema indexes
    ("metadata_schemas", [("schema_id", 1)], {"unique": True}),
    ("metadata_schemas", [("name", 1)], {"unique": True}),
    ("metadata_schemas", [("category", 1), ("status", 1)]),
    ("metadata_schemas", [("created_at", -1)]),
    
    # MetadataDocument indexes
    ("metadata_documents", [("asset_id", 1)]),
    ("metadata_documents", [("schema_id", 1), ("asset_id", 1)]),
    ("metadata_documents", [("asset_id", 1), ("is_current", 1)]),
    ("metadata_documents", [("asset_id", 1), ("version", -1)]),
    ("metadata_documents", [("parent_version_id", 1)]),
    ("metadata_documents", [("created_at", -1)]),
    ("metadata_documents", [("metadata.title", "text"), ("metadata.description", "text")]),  # Text search
    
    # TechnicalMetadata indexes
    ("technical_metadata", [("asset_id", 1)], {"unique": True}),
    ("technical_metadata", [("extracted_at", -1)]),
    
    # MetadataTemplate indexes
    ("metadata_templates", [("template_id", 1)], {"unique": True}),
    ("metadata_templates", [("name", 1), ("owner_id", 1)], {"unique": True}),
    ("metadata_templates", [("category", 1), ("is_public", 1)]),
    
    # ExtractionTask indexes
    ("extraction_tasks", [("task_id", 1)], {"unique": True}),
    ("extraction_tasks", [("asset_id", 1), ("status", 1)]),
    ("extraction_tasks", [("status", 1), ("created_at", 1)]),
    ("extraction_tasks", [("created_at", -1)]),
]