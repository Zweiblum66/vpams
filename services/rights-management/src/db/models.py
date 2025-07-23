"""
Rights Management Service - Database Models
"""

from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Date, Text, ForeignKey, Table, Index, CheckConstraint, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
import uuid

# Import audit enums for database column definitions
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models.audit_schemas import AuditAction, AuditResourceType

Base = declarative_base()

# Association tables for many-to-many relationships
license_usage_types = Table(
    'license_usage_types',
    Base.metadata,
    Column('license_id', UUID(as_uuid=True), ForeignKey('licenses.id'), primary_key=True),
    Column('usage_type', String(50), primary_key=True)
)

license_countries = Table(
    'license_countries',
    Base.metadata,
    Column('license_id', UUID(as_uuid=True), ForeignKey('licenses.id'), primary_key=True),
    Column('country_code', String(3), primary_key=True)
)

asset_rights_parties = Table(
    'asset_rights_parties',
    Base.metadata,
    Column('asset_id', UUID(as_uuid=True), primary_key=True),
    Column('rights_party_id', UUID(as_uuid=True), ForeignKey('rights_parties.id'), primary_key=True),
    Column('rights_type', String(50), nullable=False),
    Column('percentage_share', Float),
    Column('created_at', DateTime(timezone=True), server_default=func.now()),
    Column('updated_at', DateTime(timezone=True), onupdate=func.now())
)


class RightsParty(Base):
    """Rights party model (licensors, licensees, agents, etc.)"""
    __tablename__ = 'rights_parties'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    party_type = Column(String(50), nullable=False)  # owner, licensee, agent, etc.
    name = Column(String(255), nullable=False)
    legal_name = Column(String(255))
    
    # Contact information
    contact_email = Column(String(255))
    contact_phone = Column(String(50))
    address = Column(Text)
    country = Column(String(100))
    
    # Business information
    tax_id = Column(String(50))
    percentage_share = Column(Float)  # For co-ownership scenarios
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Metadata
    metadata = Column(JSONB)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    licenses_as_licensor = relationship("License", foreign_keys="License.licensor_id", back_populates="licensor")
    licenses_as_licensee = relationship("License", foreign_keys="License.licensee_id", back_populates="licensee")
    
    # Indexes
    __table_args__ = (
        Index('idx_rights_parties_party_type', 'party_type'),
        Index('idx_rights_parties_name', 'name'),
        Index('idx_rights_parties_email', 'contact_email'),
        Index('idx_rights_parties_active', 'is_active'),
        Index('idx_rights_parties_country', 'country'),
        CheckConstraint('percentage_share >= 0 AND percentage_share <= 100', name='chk_percentage_share_range')
    )


class License(Base):
    """License model"""
    __tablename__ = 'licenses'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    license_number = Column(String(100), nullable=False, unique=True)
    license_type = Column(String(50), nullable=False)  # sync, master, mechanical, etc.
    status = Column(String(20), nullable=False, default='active')
    
    # Basic information
    title = Column(String(255), nullable=False)
    description = Column(Text)
    
    # Parties
    asset_id = Column(UUID(as_uuid=True), nullable=False)  # Reference to asset service
    licensor_id = Column(UUID(as_uuid=True), ForeignKey('rights_parties.id'), nullable=False)
    licensee_id = Column(UUID(as_uuid=True), ForeignKey('rights_parties.id'), nullable=False)
    
    # Dates
    start_date = Column(Date, nullable=False)
    end_date = Column(Date)
    signed_date = Column(Date)
    
    # Geographic scope
    geographic_scope = Column(String(50), nullable=False, default='worldwide')
    countries = Column(ARRAY(String(3)))  # ISO country codes
    
    # Financial terms
    license_fee = Column(Float)
    currency = Column(String(3), default='USD')
    royalty_rate = Column(Float)  # Percentage
    minimum_guarantee = Column(Float)
    
    # Usage restrictions
    max_usage_count = Column(Integer)
    max_duration_seconds = Column(Integer)
    exclusivity = Column(Boolean, default=False, nullable=False)
    sublicensing_allowed = Column(Boolean, default=False, nullable=False)
    
    # Metadata
    metadata = Column(JSONB)
    notes = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    licensor = relationship("RightsParty", foreign_keys=[licensor_id], back_populates="licenses_as_licensor")
    licensee = relationship("RightsParty", foreign_keys=[licensee_id], back_populates="licenses_as_licensee")
    usage_records = relationship("UsageRecord", back_populates="license", cascade="all, delete-orphan")
    compliance_alerts = relationship("ComplianceAlert", back_populates="license", cascade="all, delete-orphan")
    
    # Many-to-many relationships
    usage_types = relationship("UsageType", secondary=license_usage_types, back_populates="licenses")
    
    # Indexes
    __table_args__ = (
        Index('idx_licenses_license_number', 'license_number'),
        Index('idx_licenses_asset_id', 'asset_id'),
        Index('idx_licenses_licensor_id', 'licensor_id'),
        Index('idx_licenses_licensee_id', 'licensee_id'),
        Index('idx_licenses_status', 'status'),
        Index('idx_licenses_license_type', 'license_type'),
        Index('idx_licenses_start_date', 'start_date'),
        Index('idx_licenses_end_date', 'end_date'),
        Index('idx_licenses_geographic_scope', 'geographic_scope'),
        Index('idx_licenses_currency', 'currency'),
        Index('idx_licenses_exclusivity', 'exclusivity'),
        CheckConstraint('royalty_rate >= 0 AND royalty_rate <= 100', name='chk_royalty_rate_range'),
        CheckConstraint('license_fee >= 0', name='chk_license_fee_positive'),
        CheckConstraint('minimum_guarantee >= 0', name='chk_minimum_guarantee_positive'),
        CheckConstraint('max_usage_count >= 0', name='chk_max_usage_count_positive'),
        CheckConstraint('max_duration_seconds >= 0', name='chk_max_duration_positive'),
        CheckConstraint('end_date IS NULL OR end_date >= start_date', name='chk_end_date_after_start')
    )


class UsageRecord(Base):
    """Usage record model"""
    __tablename__ = 'usage_records'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    license_id = Column(UUID(as_uuid=True), ForeignKey('licenses.id'), nullable=False)
    asset_id = Column(UUID(as_uuid=True), nullable=False)  # Reference to asset service
    user_id = Column(UUID(as_uuid=True), nullable=False)  # Reference to user service
    
    # Usage details
    usage_type = Column(String(50), nullable=False)  # broadcast, streaming, etc.
    usage_date = Column(DateTime(timezone=True), nullable=False)
    duration_seconds = Column(Integer)
    usage_count = Column(Integer, default=1, nullable=False)
    
    # Context
    platform = Column(String(100))
    channel = Column(String(100))
    program_title = Column(String(255))
    episode_title = Column(String(255))
    
    # Geographic
    country = Column(String(100))
    region = Column(String(100))
    
    # Financial
    revenue_generated = Column(Float)
    royalty_due = Column(Float)
    
    # Metadata
    metadata = Column(JSONB)
    notes = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    license = relationship("License", back_populates="usage_records")
    
    # Indexes
    __table_args__ = (
        Index('idx_usage_records_license_id', 'license_id'),
        Index('idx_usage_records_asset_id', 'asset_id'),
        Index('idx_usage_records_user_id', 'user_id'),
        Index('idx_usage_records_usage_type', 'usage_type'),
        Index('idx_usage_records_usage_date', 'usage_date'),
        Index('idx_usage_records_platform', 'platform'),
        Index('idx_usage_records_country', 'country'),
        Index('idx_usage_records_revenue', 'revenue_generated'),
        Index('idx_usage_records_royalty', 'royalty_due'),
        CheckConstraint('usage_count >= 1', name='chk_usage_count_positive'),
        CheckConstraint('duration_seconds >= 0', name='chk_duration_positive'),
        CheckConstraint('revenue_generated >= 0', name='chk_revenue_positive'),
        CheckConstraint('royalty_due >= 0', name='chk_royalty_due_positive')
    )


class ComplianceAlert(Base):
    """Compliance alert model"""
    __tablename__ = 'compliance_alerts'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    license_id = Column(UUID(as_uuid=True), ForeignKey('licenses.id'))
    asset_id = Column(UUID(as_uuid=True))
    usage_record_id = Column(UUID(as_uuid=True), ForeignKey('usage_records.id'))
    
    # Alert details
    alert_type = Column(String(100), nullable=False)  # expiration, usage_limit, etc.
    severity = Column(String(20), nullable=False)  # low, medium, high, critical
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    
    # Status
    is_resolved = Column(Boolean, default=False, nullable=False)
    resolved_at = Column(DateTime(timezone=True))
    resolved_by = Column(UUID(as_uuid=True))  # User who resolved
    resolution_notes = Column(Text)
    
    # Metadata
    metadata = Column(JSONB)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    license = relationship("License", back_populates="compliance_alerts")
    usage_record = relationship("UsageRecord")
    
    # Indexes
    __table_args__ = (
        Index('idx_compliance_alerts_license_id', 'license_id'),
        Index('idx_compliance_alerts_asset_id', 'asset_id'),
        Index('idx_compliance_alerts_usage_record_id', 'usage_record_id'),
        Index('idx_compliance_alerts_alert_type', 'alert_type'),
        Index('idx_compliance_alerts_severity', 'severity'),
        Index('idx_compliance_alerts_resolved', 'is_resolved'),
        Index('idx_compliance_alerts_resolved_by', 'resolved_by'),
        Index('idx_compliance_alerts_created_at', 'created_at')
    )


class RightsReport(Base):
    """Rights report model"""
    __tablename__ = 'rights_reports'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_type = Column(String(100), nullable=False)  # usage, revenue, compliance, etc.
    title = Column(String(255), nullable=False)
    description = Column(Text)
    
    # Time range
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    
    # Filters
    filters = Column(JSONB)
    
    # Status
    status = Column(String(20), nullable=False, default='pending')  # pending, processing, completed, failed
    file_path = Column(String(500))
    
    # Metadata
    metadata = Column(JSONB)
    
    # User
    created_by = Column(UUID(as_uuid=True), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Indexes
    __table_args__ = (
        Index('idx_rights_reports_report_type', 'report_type'),
        Index('idx_rights_reports_status', 'status'),
        Index('idx_rights_reports_created_by', 'created_by'),
        Index('idx_rights_reports_start_date', 'start_date'),
        Index('idx_rights_reports_end_date', 'end_date'),
        Index('idx_rights_reports_created_at', 'created_at'),
        CheckConstraint('end_date >= start_date', name='chk_report_end_date_after_start')
    )


class LicenseAuditLog(Base):
    """License audit log model"""
    __tablename__ = 'license_audit_logs'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    license_id = Column(UUID(as_uuid=True), ForeignKey('licenses.id'), nullable=False)
    
    # Audit details
    action = Column(String(50), nullable=False)  # created, updated, deleted, etc.
    user_id = Column(UUID(as_uuid=True), nullable=False)
    
    # Changes
    old_values = Column(JSONB)
    new_values = Column(JSONB)
    changed_fields = Column(ARRAY(String(100)))
    
    # Context
    ip_address = Column(String(45))
    user_agent = Column(String(500))
    
    # Metadata
    metadata = Column(JSONB)
    
    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    license = relationship("License")
    
    # Indexes
    __table_args__ = (
        Index('idx_license_audit_logs_license_id', 'license_id'),
        Index('idx_license_audit_logs_action', 'action'),
        Index('idx_license_audit_logs_user_id', 'user_id'),
        Index('idx_license_audit_logs_created_at', 'created_at')
    )


class UsageType(Base):
    """Usage type model for many-to-many with licenses"""
    __tablename__ = 'usage_types'
    
    id = Column(String(50), primary_key=True)  # broadcast, streaming, etc.
    name = Column(String(100), nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Metadata
    metadata = Column(JSONB)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    licenses = relationship("License", secondary=license_usage_types, back_populates="usage_types")
    
    # Indexes
    __table_args__ = (
        Index('idx_usage_types_name', 'name'),
        Index('idx_usage_types_active', 'is_active')
    )


class RightsTemplate(Base):
    """Rights template model for common license patterns"""
    __tablename__ = 'rights_templates'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    category = Column(String(100))  # broadcast, streaming, sync, etc.
    
    # Template configuration
    template_config = Column(JSONB, nullable=False)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_public = Column(Boolean, default=False, nullable=False)
    
    # User
    created_by = Column(UUID(as_uuid=True), nullable=False)
    
    # Metadata
    metadata = Column(JSONB)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Indexes
    __table_args__ = (
        Index('idx_rights_templates_name', 'name'),
        Index('idx_rights_templates_category', 'category'),
        Index('idx_rights_templates_active', 'is_active'),
        Index('idx_rights_templates_public', 'is_public'),
        Index('idx_rights_templates_created_by', 'created_by')
    )


class RightsCalculation(Base):
    """Rights calculation model for complex royalty calculations"""
    __tablename__ = 'rights_calculations'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    license_id = Column(UUID(as_uuid=True), ForeignKey('licenses.id'), nullable=False)
    usage_record_id = Column(UUID(as_uuid=True), ForeignKey('usage_records.id'), nullable=False)
    
    # Calculation details
    calculation_type = Column(String(50), nullable=False)  # royalty, fee, etc.
    base_amount = Column(Float, nullable=False)
    percentage = Column(Float)
    calculated_amount = Column(Float, nullable=False)
    
    # Calculation factors
    factors = Column(JSONB)  # Store complex calculation factors
    
    # Status
    status = Column(String(20), nullable=False, default='pending')  # pending, approved, paid
    
    # Metadata
    metadata = Column(JSONB)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    license = relationship("License")
    usage_record = relationship("UsageRecord")
    
    # Indexes
    __table_args__ = (
        Index('idx_rights_calculations_license_id', 'license_id'),
        Index('idx_rights_calculations_usage_record_id', 'usage_record_id'),
        Index('idx_rights_calculations_calculation_type', 'calculation_type'),
        Index('idx_rights_calculations_status', 'status'),
        Index('idx_rights_calculations_created_at', 'created_at'),
        CheckConstraint('base_amount >= 0', name='chk_base_amount_positive'),
        CheckConstraint('calculated_amount >= 0', name='chk_calculated_amount_positive'),
        CheckConstraint('percentage IS NULL OR (percentage >= 0 AND percentage <= 100)', name='chk_percentage_range')
    )


class RightsMetadata(Base):
    """Rights metadata model for flexible metadata storage"""
    __tablename__ = 'rights_metadata'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_type = Column(String(50), nullable=False)  # license, usage_record, etc.
    entity_id = Column(UUID(as_uuid=True), nullable=False)
    
    # Metadata
    key = Column(String(255), nullable=False)
    value = Column(JSONB)
    data_type = Column(String(50))  # string, number, boolean, date, etc.
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Indexes
    __table_args__ = (
        Index('idx_rights_metadata_entity', 'entity_type', 'entity_id'),
        Index('idx_rights_metadata_key', 'key'),
        Index('idx_rights_metadata_data_type', 'data_type'),
        Index('idx_rights_metadata_created_at', 'created_at')
    )


class AuditLog(Base):
    """Audit log model for tracking all system events"""
    __tablename__ = 'audit_logs'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Event information
    event_type = Column(String(100), nullable=False)
    event_description = Column(String(500), nullable=False)
    entity_type = Column(String(50), nullable=False)  # license, usage_record, alert, etc.
    entity_id = Column(String(100), nullable=False)
    
    # User information
    user_id = Column(String(100), nullable=False)
    username = Column(String(100), nullable=False)
    ip_address = Column(String(45))  # IPv4 or IPv6
    user_agent = Column(Text)
    
    # Event details
    timestamp = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    severity = Column(String(20), nullable=False, default='info')  # info, warning, high, critical
    details = Column(JSONB)
    
    # Integrity
    checksum = Column(String(64))  # SHA-256 hash for integrity verification
    
    # Indexes
    __table_args__ = (
        Index('idx_audit_logs_event_type', 'event_type'),
        Index('idx_audit_logs_entity', 'entity_type', 'entity_id'),
        Index('idx_audit_logs_user', 'user_id'),
        Index('idx_audit_logs_timestamp', 'timestamp'),
        Index('idx_audit_logs_severity', 'severity'),
        CheckConstraint("severity IN ('info', 'warning', 'high', 'critical')", name='chk_audit_severity')
    )


class AuditTrail(Base):
    """Comprehensive audit trail model for rights management actions"""
    __tablename__ = 'audit_trails'
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=func.now())
    
    # Action and resource
    action = Column(SQLEnum(AuditAction), nullable=False)
    resource_type = Column(SQLEnum(AuditResourceType), nullable=False)
    resource_id = Column(String(255), nullable=False)
    
    # User information
    user_id = Column(String(255), nullable=False)
    user_email = Column(String(255), nullable=False)
    user_name = Column(String(255))
    user_roles = Column(JSONB, default=list)
    
    # Context information
    ip_address = Column(String(45))  # Supports IPv6
    user_agent = Column(String(500))
    session_id = Column(String(100))
    
    # Change details
    old_values = Column(JSONB)
    new_values = Column(JSONB)
    changes_summary = Column(Text)
    
    # Additional metadata
    metadata = Column(JSONB, default=dict)
    tags = Column(JSONB, default=list)
    
    # Compliance and security
    compliance_relevant = Column(Boolean, default=False, nullable=False)
    security_relevant = Column(Boolean, default=False, nullable=False)
    
    # Status
    success = Column(Boolean, default=True, nullable=False)
    error_message = Column(Text)
    
    # Indexes for performance
    __table_args__ = (
        Index("idx_audit_trail_timestamp", "timestamp"),
        Index("idx_audit_trail_user_id", "user_id"),
        Index("idx_audit_trail_resource", "resource_type", "resource_id"),
        Index("idx_audit_trail_action", "action"),
        Index("idx_audit_trail_compliance", "compliance_relevant"),
        Index("idx_audit_trail_security", "security_relevant"),
        Index("idx_audit_trail_session", "session_id"),
        Index("idx_audit_trail_timestamp_user", "timestamp", "user_id"),
        Index("idx_audit_trail_timestamp_resource", "timestamp", "resource_type", "resource_id"),
    )


class AuditArchive(Base):
    """Archived audit trail entries for long-term storage"""
    __tablename__ = 'audit_archives'
    
    # Same structure as AuditTrail but for archived data
    id = Column(UUID(as_uuid=True), primary_key=True)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    
    # Action and resource
    action = Column(SQLEnum(AuditAction), nullable=False)
    resource_type = Column(SQLEnum(AuditResourceType), nullable=False)
    resource_id = Column(String(255), nullable=False)
    
    # User information
    user_id = Column(String(255), nullable=False)
    user_email = Column(String(255), nullable=False)
    user_name = Column(String(255))
    user_roles = Column(JSONB, default=list)
    
    # Context information
    ip_address = Column(String(45))
    user_agent = Column(String(500))
    session_id = Column(String(100))
    
    # Change details
    old_values = Column(JSONB)
    new_values = Column(JSONB)
    changes_summary = Column(Text)
    
    # Additional metadata
    metadata = Column(JSONB, default=dict)
    tags = Column(JSONB, default=list)
    
    # Compliance and security
    compliance_relevant = Column(Boolean, default=False, nullable=False)
    security_relevant = Column(Boolean, default=False, nullable=False)
    
    # Status
    success = Column(Boolean, default=True, nullable=False)
    error_message = Column(Text)
    
    # Archive metadata
    archived_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    archive_batch_id = Column(String(100))
    
    # Indexes for archived data (fewer indexes for storage efficiency)
    __table_args__ = (
        Index("idx_archive_timestamp", "timestamp"),
        Index("idx_archive_archived_at", "archived_at"),
        Index("idx_archive_user_id", "user_id"),
        Index("idx_archive_resource", "resource_type", "resource_id"),
    )