"""
Rights Management Service - Pydantic Schemas
"""

from datetime import datetime, date
from typing import List, Optional, Dict, Any, Union
from enum import Enum
from pydantic import BaseModel, Field, validator
import uuid

# Enums
class RightsType(str, Enum):
    """Types of rights"""
    SYNC = "sync"
    MASTER = "master"
    MECHANICAL = "mechanical"
    PERFORMANCE = "performance"
    REPRODUCTION = "reproduction"
    DISTRIBUTION = "distribution"
    DISPLAY = "display"
    ADAPTATION = "adaptation"
    TRANSLATION = "translation"
    BROADCAST = "broadcast"
    STREAMING = "streaming"
    THEATRICAL = "theatrical"
    HOME_VIDEO = "home_video"
    EDUCATIONAL = "educational"
    COMMERCIAL = "commercial"
    MERCHANDISING = "merchandising"


class LicenseStatus(str, Enum):
    """License status"""
    ACTIVE = "active"
    EXPIRED = "expired"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"
    PENDING = "pending"
    DRAFT = "draft"


class UsageType(str, Enum):
    """Usage types"""
    BROADCAST = "broadcast"
    STREAMING = "streaming"
    THEATRICAL = "theatrical"
    HOME_VIDEO = "home_video"
    EDUCATIONAL = "educational"
    COMMERCIAL = "commercial"
    PROMOTIONAL = "promotional"
    INTERNAL = "internal"
    ARCHIVE = "archive"
    DERIVATIVE = "derivative"


class GeographicScope(str, Enum):
    """Geographic scope"""
    WORLDWIDE = "worldwide"
    NORTH_AMERICA = "north_america"
    EUROPE = "europe"
    ASIA = "asia"
    AFRICA = "africa"
    OCEANIA = "oceania"
    COUNTRY_SPECIFIC = "country_specific"
    REGION_SPECIFIC = "region_specific"


class RightsParty(str, Enum):
    """Rights party types"""
    OWNER = "owner"
    LICENSEE = "licensee"
    AGENT = "agent"
    PUBLISHER = "publisher"
    DISTRIBUTOR = "distributor"
    PRODUCTION_COMPANY = "production_company"
    PERFORMER = "performer"
    COMPOSER = "composer"
    WRITER = "writer"
    DIRECTOR = "director"
    PRODUCER = "producer"


# Base Models
class RightsPartyBase(BaseModel):
    """Base rights party model"""
    party_type: RightsParty
    name: str = Field(..., min_length=1, max_length=255)
    legal_name: Optional[str] = Field(None, max_length=255)
    contact_email: Optional[str] = Field(None, max_length=255)
    contact_phone: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = Field(None, max_length=500)
    country: Optional[str] = Field(None, max_length=100)
    tax_id: Optional[str] = Field(None, max_length=50)
    percentage_share: Optional[float] = Field(None, ge=0, le=100)
    is_active: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RightsPartyCreate(RightsPartyBase):
    """Create rights party"""
    pass


class RightsPartyUpdate(BaseModel):
    """Update rights party"""
    party_type: Optional[RightsParty] = None
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    legal_name: Optional[str] = Field(None, max_length=255)
    contact_email: Optional[str] = Field(None, max_length=255)
    contact_phone: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = Field(None, max_length=500)
    country: Optional[str] = Field(None, max_length=100)
    tax_id: Optional[str] = Field(None, max_length=50)
    percentage_share: Optional[float] = Field(None, ge=0, le=100)
    is_active: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None


class RightsPartyResponse(RightsPartyBase):
    """Rights party response"""
    id: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class LicenseBase(BaseModel):
    """Base license model"""
    license_number: str = Field(..., min_length=1, max_length=100)
    license_type: RightsType
    status: LicenseStatus = LicenseStatus.ACTIVE
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    
    # Dates
    start_date: date
    end_date: Optional[date] = None
    signed_date: Optional[date] = None
    
    # Geographic and usage scope
    geographic_scope: GeographicScope = GeographicScope.WORLDWIDE
    countries: List[str] = Field(default_factory=list)
    usage_types: List[UsageType] = Field(default_factory=list)
    
    # Financial terms
    license_fee: Optional[float] = Field(None, ge=0)
    currency: str = Field("USD", max_length=3)
    royalty_rate: Optional[float] = Field(None, ge=0, le=100)
    minimum_guarantee: Optional[float] = Field(None, ge=0)
    
    # Restrictions
    max_usage_count: Optional[int] = Field(None, ge=0)
    max_duration_seconds: Optional[int] = Field(None, ge=0)
    exclusivity: bool = False
    sublicensing_allowed: bool = False
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    notes: Optional[str] = Field(None, max_length=2000)
    
    @validator('end_date')
    def validate_end_date(cls, v, values):
        if v and 'start_date' in values and v <= values['start_date']:
            raise ValueError('End date must be after start date')
        return v
    
    @validator('countries')
    def validate_countries(cls, v, values):
        if values.get('geographic_scope') == GeographicScope.COUNTRY_SPECIFIC and not v:
            raise ValueError('Countries must be specified for country-specific scope')
        return v


class LicenseCreate(LicenseBase):
    """Create license"""
    asset_id: str = Field(..., min_length=1)
    licensor_id: str = Field(..., min_length=1)
    licensee_id: str = Field(..., min_length=1)


class LicenseUpdate(BaseModel):
    """Update license"""
    license_number: Optional[str] = Field(None, min_length=1, max_length=100)
    license_type: Optional[RightsType] = None
    status: Optional[LicenseStatus] = None
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    
    # Dates
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    signed_date: Optional[date] = None
    
    # Geographic and usage scope
    geographic_scope: Optional[GeographicScope] = None
    countries: Optional[List[str]] = None
    usage_types: Optional[List[UsageType]] = None
    
    # Financial terms
    license_fee: Optional[float] = Field(None, ge=0)
    currency: Optional[str] = Field(None, max_length=3)
    royalty_rate: Optional[float] = Field(None, ge=0, le=100)
    minimum_guarantee: Optional[float] = Field(None, ge=0)
    
    # Restrictions
    max_usage_count: Optional[int] = Field(None, ge=0)
    max_duration_seconds: Optional[int] = Field(None, ge=0)
    exclusivity: Optional[bool] = None
    sublicensing_allowed: Optional[bool] = None
    
    # Metadata
    metadata: Optional[Dict[str, Any]] = None
    notes: Optional[str] = Field(None, max_length=2000)


class LicenseResponse(LicenseBase):
    """License response"""
    id: str
    asset_id: str
    licensor_id: str
    licensee_id: str
    created_at: datetime
    updated_at: datetime
    
    # Related objects
    licensor: Optional[RightsPartyResponse] = None
    licensee: Optional[RightsPartyResponse] = None
    
    class Config:
        from_attributes = True


class UsageRecordBase(BaseModel):
    """Base usage record model"""
    usage_type: UsageType
    usage_date: datetime
    duration_seconds: Optional[int] = Field(None, ge=0)
    usage_count: int = Field(1, ge=1)
    
    # Context
    platform: Optional[str] = Field(None, max_length=100)
    channel: Optional[str] = Field(None, max_length=100)
    program_title: Optional[str] = Field(None, max_length=255)
    episode_title: Optional[str] = Field(None, max_length=255)
    
    # Geographic
    country: Optional[str] = Field(None, max_length=100)
    region: Optional[str] = Field(None, max_length=100)
    
    # Financial
    revenue_generated: Optional[float] = Field(None, ge=0)
    royalty_due: Optional[float] = Field(None, ge=0)
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    notes: Optional[str] = Field(None, max_length=1000)


class UsageRecordCreate(UsageRecordBase):
    """Create usage record"""
    license_id: str = Field(..., min_length=1)
    asset_id: str = Field(..., min_length=1)
    user_id: str = Field(..., min_length=1)


class UsageRecordUpdate(BaseModel):
    """Update usage record"""
    usage_type: Optional[UsageType] = None
    usage_date: Optional[datetime] = None
    duration_seconds: Optional[int] = Field(None, ge=0)
    usage_count: Optional[int] = Field(None, ge=1)
    
    # Context
    platform: Optional[str] = Field(None, max_length=100)
    channel: Optional[str] = Field(None, max_length=100)
    program_title: Optional[str] = Field(None, max_length=255)
    episode_title: Optional[str] = Field(None, max_length=255)
    
    # Geographic
    country: Optional[str] = Field(None, max_length=100)
    region: Optional[str] = Field(None, max_length=100)
    
    # Financial
    revenue_generated: Optional[float] = Field(None, ge=0)
    royalty_due: Optional[float] = Field(None, ge=0)
    
    # Metadata
    metadata: Optional[Dict[str, Any]] = None
    notes: Optional[str] = Field(None, max_length=1000)


class UsageRecordResponse(UsageRecordBase):
    """Usage record response"""
    id: str
    license_id: str
    asset_id: str
    user_id: str
    created_at: datetime
    updated_at: datetime
    
    # Related objects
    license: Optional[LicenseResponse] = None
    
    class Config:
        from_attributes = True


class ComplianceAlertBase(BaseModel):
    """Base compliance alert model"""
    alert_type: str = Field(..., max_length=100)
    severity: str = Field(..., max_length=20)  # low, medium, high, critical
    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1, max_length=2000)
    
    # Status
    is_resolved: bool = False
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    resolution_notes: Optional[str] = Field(None, max_length=2000)
    
    # Context
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ComplianceAlertCreate(ComplianceAlertBase):
    """Create compliance alert"""
    license_id: Optional[str] = None
    asset_id: Optional[str] = None
    usage_record_id: Optional[str] = None


class ComplianceAlertUpdate(BaseModel):
    """Update compliance alert"""
    alert_type: Optional[str] = Field(None, max_length=100)
    severity: Optional[str] = Field(None, max_length=20)
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, min_length=1, max_length=2000)
    
    # Status
    is_resolved: Optional[bool] = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    resolution_notes: Optional[str] = Field(None, max_length=2000)
    
    # Context
    metadata: Optional[Dict[str, Any]] = None


class ComplianceAlertResponse(ComplianceAlertBase):
    """Compliance alert response"""
    id: str
    license_id: Optional[str] = None
    asset_id: Optional[str] = None
    usage_record_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    # Related objects
    license: Optional[LicenseResponse] = None
    
    class Config:
        from_attributes = True


class RightsReportBase(BaseModel):
    """Base rights report model"""
    report_type: str = Field(..., max_length=100)
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    
    # Time range
    start_date: date
    end_date: date
    
    # Filters
    filters: Dict[str, Any] = Field(default_factory=dict)
    
    # Status
    status: str = Field("pending", max_length=20)  # pending, processing, completed, failed
    file_path: Optional[str] = Field(None, max_length=500)
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RightsReportCreate(RightsReportBase):
    """Create rights report"""
    pass


class RightsReportUpdate(BaseModel):
    """Update rights report"""
    report_type: Optional[str] = Field(None, max_length=100)
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    
    # Time range
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    
    # Filters
    filters: Optional[Dict[str, Any]] = None
    
    # Status
    status: Optional[str] = Field(None, max_length=20)
    file_path: Optional[str] = Field(None, max_length=500)
    
    # Metadata
    metadata: Optional[Dict[str, Any]] = None


class RightsReportResponse(RightsReportBase):
    """Rights report response"""
    id: str
    created_by: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Analytics Models
class UsageAnalytics(BaseModel):
    """Usage analytics response"""
    total_usage_count: int
    total_duration_seconds: int
    total_revenue: float
    total_royalties: float
    
    # By type
    usage_by_type: Dict[str, int]
    revenue_by_type: Dict[str, float]
    
    # By geographic
    usage_by_country: Dict[str, int]
    revenue_by_country: Dict[str, float]
    
    # By platform
    usage_by_platform: Dict[str, int]
    revenue_by_platform: Dict[str, float]
    
    # Time series
    usage_over_time: List[Dict[str, Any]]
    revenue_over_time: List[Dict[str, Any]]


class LicenseAnalytics(BaseModel):
    """License analytics response"""
    total_licenses: int
    active_licenses: int
    expired_licenses: int
    expiring_soon: int  # within 30 days
    
    # By type
    licenses_by_type: Dict[str, int]
    
    # By geographic scope
    licenses_by_geography: Dict[str, int]
    
    # Financial
    total_license_fees: float
    total_minimum_guarantees: float
    average_royalty_rate: float
    
    # Compliance
    compliance_alerts: int
    resolved_alerts: int
    critical_alerts: int


class RightsComplianceCheck(BaseModel):
    """Rights compliance check"""
    asset_id: str
    usage_type: UsageType
    usage_date: datetime
    duration_seconds: Optional[int] = None
    country: Optional[str] = None
    platform: Optional[str] = None


class RightsComplianceResult(BaseModel):
    """Rights compliance result"""
    is_compliant: bool
    applicable_licenses: List[str]
    violations: List[str]
    warnings: List[str]
    recommendations: List[str]
    
    # Usage limits
    remaining_usage_count: Optional[int] = None
    remaining_duration_seconds: Optional[int] = None
    
    # Financial
    royalty_due: Optional[float] = None
    minimum_fee: Optional[float] = None


# Bulk Operations
class BulkLicenseCreate(BaseModel):
    """Bulk license creation"""
    licenses: List[LicenseCreate]
    validate_only: bool = False


class BulkLicenseUpdate(BaseModel):
    """Bulk license update"""
    license_ids: List[str]
    updates: LicenseUpdate
    validate_only: bool = False


class BulkUsageRecordCreate(BaseModel):
    """Bulk usage record creation"""
    usage_records: List[UsageRecordCreate]
    validate_only: bool = False


class BulkOperationResult(BaseModel):
    """Bulk operation result"""
    total_processed: int
    successful: int
    failed: int
    errors: List[Dict[str, str]]
    created_ids: List[str] = Field(default_factory=list)
    updated_ids: List[str] = Field(default_factory=list)


# Search and Filter Models
class LicenseFilter(BaseModel):
    """License filter"""
    license_type: Optional[RightsType] = None
    status: Optional[LicenseStatus] = None
    geographic_scope: Optional[GeographicScope] = None
    usage_types: Optional[List[UsageType]] = None
    countries: Optional[List[str]] = None
    licensor_id: Optional[str] = None
    licensee_id: Optional[str] = None
    asset_id: Optional[str] = None
    
    # Date ranges
    start_date_from: Optional[date] = None
    start_date_to: Optional[date] = None
    end_date_from: Optional[date] = None
    end_date_to: Optional[date] = None
    
    # Financial
    license_fee_min: Optional[float] = None
    license_fee_max: Optional[float] = None
    
    # Text search
    search_text: Optional[str] = None


class UsageRecordFilter(BaseModel):
    """Usage record filter"""
    license_id: Optional[str] = None
    asset_id: Optional[str] = None
    user_id: Optional[str] = None
    usage_type: Optional[UsageType] = None
    platform: Optional[str] = None
    country: Optional[str] = None
    
    # Date range
    usage_date_from: Optional[datetime] = None
    usage_date_to: Optional[datetime] = None
    
    # Financial
    revenue_min: Optional[float] = None
    revenue_max: Optional[float] = None
    
    # Text search
    search_text: Optional[str] = None


# Pagination
class PaginatedResponse(BaseModel):
    """Paginated response"""
    items: List[Any]
    total: int
    page: int
    limit: int
    pages: int
    
    class Config:
        arbitrary_types_allowed = True


# User model (for dependencies)
class User(BaseModel):
    """User model for authentication"""
    user_id: str
    username: str
    email: str
    is_active: bool = True
    roles: List[str] = Field(default_factory=list)