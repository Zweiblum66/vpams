"""
Database models for provenance tracking functionality.
"""
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from enum import Enum as PyEnum
import uuid

from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Text, 
    ForeignKey, Numeric, JSON, Enum, UniqueConstraint, Index
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .models import Base, NetworkType


class ProvenanceEventType(PyEnum):
    """Types of provenance events."""
    CREATED = "created"
    MODIFIED = "modified"
    TRANSFERRED = "transferred"
    VERIFIED = "verified"
    LICENSED = "licensed"
    ARCHIVED = "archived"
    DELETED = "deleted"
    ACCESSED = "accessed"
    DERIVED = "derived"
    MERGED = "merged"
    SPLIT = "split"
    CONVERTED = "converted"


class ProvenanceStatus(PyEnum):
    """Provenance tracking status."""
    ACTIVE = "active"
    COMPLETED = "completed"
    DISPUTED = "disputed"
    ARCHIVED = "archived"


class VerificationType(PyEnum):
    """Types of verification."""
    AUTHENTICITY = "authenticity"
    OWNERSHIP = "ownership"
    QUALITY = "quality"
    COMPLIANCE = "compliance"
    INTEGRITY = "integrity"
    SOURCE = "source"


class ProvenanceAsset(Base):
    """Assets tracked for provenance."""
    __tablename__ = "provenance_assets"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Asset identification
    asset_id = Column(UUID(as_uuid=True), nullable=False, index=True)  # Reference to main asset
    blockchain_asset_id = Column(Integer, nullable=True, index=True)  # On-chain asset ID
    content_hash = Column(String(64), nullable=False, index=True)
    
    # Asset details
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    asset_type = Column(String(100), nullable=False)
    file_format = Column(String(50), nullable=True)
    file_size = Column(Integer, nullable=True)
    
    # Technical metadata
    duration = Column(Numeric(10, 3), nullable=True)  # For video/audio
    resolution = Column(String(50), nullable=True)
    codec = Column(String(50), nullable=True)
    frame_rate = Column(Numeric(8, 3), nullable=True)
    bitrate = Column(Integer, nullable=True)
    
    # Provenance details
    creator_address = Column(String(42), nullable=False, index=True)
    current_owner_address = Column(String(42), nullable=False, index=True)
    status = Column(Enum(ProvenanceStatus), nullable=False, default=ProvenanceStatus.ACTIVE)
    verified = Column(Boolean, nullable=False, default=False)
    
    # Blockchain information
    network = Column(Enum(NetworkType), nullable=False)
    contract_address = Column(String(42), nullable=True)
    registration_transaction_hash = Column(String(66), nullable=True, index=True)
    registration_block_number = Column(Integer, nullable=True)
    
    # IPFS metadata
    metadata_ipfs_hash = Column(String(255), nullable=True)
    metadata_uri = Column(String(512), nullable=True)
    
    # Location and context
    creation_location = Column(JSON, nullable=True)  # GPS coordinates, address
    camera_model = Column(String(100), nullable=True)
    capture_settings = Column(JSON, nullable=True)
    
    # Additional metadata
    custom_metadata = Column(JSON, nullable=True)
    tags = Column(JSON, nullable=True)  # Array of tags
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    registered_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    events = relationship("ProvenanceEvent", back_populates="asset", cascade="all, delete-orphan")
    verifications = relationship("ProvenanceVerification", back_populates="asset", cascade="all, delete-orphan")
    licenses = relationship("ProvenanceLicense", back_populates="asset", cascade="all, delete-orphan")
    
    __table_args__ = (
        UniqueConstraint('content_hash', 'network', name='uq_provenance_content_network'),
        Index('idx_provenance_asset_owner', 'current_owner_address', 'network'),
        Index('idx_provenance_asset_creator', 'creator_address', 'status'),
    )


class ProvenanceEvent(Base):
    """Individual provenance events."""
    __tablename__ = "provenance_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id = Column(UUID(as_uuid=True), ForeignKey("provenance_assets.id"), nullable=False)
    
    # Event identification
    blockchain_event_id = Column(Integer, nullable=True, index=True)  # On-chain event ID
    event_type = Column(Enum(ProvenanceEventType), nullable=False, index=True)
    event_hash = Column(String(64), nullable=False, index=True)
    
    # Actor information
    actor_address = Column(String(42), nullable=False, index=True)
    actor_name = Column(String(255), nullable=True)
    actor_role = Column(String(100), nullable=True)
    
    # Event details
    description = Column(Text, nullable=False)
    event_data = Column(JSON, nullable=True)  # Event-specific data
    previous_event_hash = Column(String(64), nullable=True, index=True)
    
    # Location and context
    location = Column(String(255), nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(512), nullable=True)
    
    # Blockchain information
    transaction_hash = Column(String(66), nullable=True, index=True)
    block_number = Column(Integer, nullable=True)
    block_timestamp = Column(DateTime(timezone=True), nullable=True)
    
    # IPFS metadata
    metadata_ipfs_hash = Column(String(255), nullable=True)
    metadata_uri = Column(String(512), nullable=True)
    
    # Verification
    signature = Column(Text, nullable=True)  # Digital signature
    signature_verified = Column(Boolean, nullable=False, default=False)
    
    # Timestamps
    occurred_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    asset = relationship("ProvenanceAsset", back_populates="events")
    
    __table_args__ = (
        Index('idx_provenance_event_type_time', 'event_type', 'occurred_at'),
        Index('idx_provenance_event_actor_time', 'actor_address', 'occurred_at'),
        Index('idx_provenance_event_hash_chain', 'event_hash', 'previous_event_hash'),
    )


class ProvenanceChain(Base):
    """Provenance chain relationships and lineage."""
    __tablename__ = "provenance_chains"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Chain identification
    source_asset_id = Column(UUID(as_uuid=True), ForeignKey("provenance_assets.id"), nullable=False)
    target_asset_id = Column(UUID(as_uuid=True), ForeignKey("provenance_assets.id"), nullable=False)
    chain_type = Column(String(50), nullable=False, index=True)  # derived, merged, split, etc.
    
    # Relationship details
    relationship_strength = Column(Numeric(3, 2), nullable=False, default=1.0)  # 0.0 to 1.0
    transformation_type = Column(String(100), nullable=True)
    transformation_metadata = Column(JSON, nullable=True)
    
    # Chain integrity
    verified = Column(Boolean, nullable=False, default=False)
    integrity_score = Column(Numeric(3, 2), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    verified_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    source_asset = relationship("ProvenanceAsset", foreign_keys=[source_asset_id])
    target_asset = relationship("ProvenanceAsset", foreign_keys=[target_asset_id])
    
    __table_args__ = (
        UniqueConstraint('source_asset_id', 'target_asset_id', 'chain_type', name='uq_provenance_chain'),
        Index('idx_provenance_chain_source', 'source_asset_id', 'chain_type'),
        Index('idx_provenance_chain_target', 'target_asset_id', 'chain_type'),
    )


class ProvenanceVerification(Base):
    """Asset verifications and attestations."""
    __tablename__ = "provenance_verifications"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id = Column(UUID(as_uuid=True), ForeignKey("provenance_assets.id"), nullable=False)
    
    # Verification details
    verification_type = Column(Enum(VerificationType), nullable=False, index=True)
    verified = Column(Boolean, nullable=False)
    confidence_score = Column(Numeric(3, 2), nullable=True)  # 0.0 to 1.0
    
    # Verifier information
    verifier_address = Column(String(42), nullable=False, index=True)
    verifier_name = Column(String(255), nullable=True)
    verifier_organization = Column(String(255), nullable=True)
    verifier_credentials = Column(JSON, nullable=True)
    
    # Evidence
    evidence_description = Column(Text, nullable=True)
    evidence_files = Column(JSON, nullable=True)  # Array of file hashes/URIs
    evidence_ipfs_hash = Column(String(255), nullable=True)
    
    # Verification process
    verification_method = Column(String(100), nullable=True)
    verification_tools = Column(JSON, nullable=True)
    verification_criteria = Column(JSON, nullable=True)
    
    # Blockchain information
    transaction_hash = Column(String(66), nullable=True, index=True)
    block_number = Column(Integer, nullable=True)
    
    # Validity
    valid_from = Column(DateTime(timezone=True), nullable=True)
    valid_until = Column(DateTime(timezone=True), nullable=True)
    revoked = Column(Boolean, nullable=False, default=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    revocation_reason = Column(Text, nullable=True)
    
    # Timestamps
    verified_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    asset = relationship("ProvenanceAsset", back_populates="verifications")
    
    __table_args__ = (
        Index('idx_provenance_verification_type', 'verification_type', 'verified'),
        Index('idx_provenance_verification_verifier', 'verifier_address', 'verified_at'),
        Index('idx_provenance_verification_validity', 'valid_from', 'valid_until'),
    )


class ProvenanceLicense(Base):
    """Licensing information for provenance-tracked assets."""
    __tablename__ = "provenance_licenses"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id = Column(UUID(as_uuid=True), ForeignKey("provenance_assets.id"), nullable=False)
    
    # License details
    license_type = Column(String(100), nullable=False, index=True)
    license_name = Column(String(255), nullable=True)
    license_url = Column(String(512), nullable=True)
    license_text = Column(Text, nullable=True)
    
    # Parties
    licensor_address = Column(String(42), nullable=False, index=True)
    licensee_address = Column(String(42), nullable=True, index=True)
    
    # Terms
    commercial_use = Column(Boolean, nullable=False, default=False)
    derivative_works = Column(Boolean, nullable=False, default=False)
    distribution = Column(Boolean, nullable=False, default=True)
    attribution_required = Column(Boolean, nullable=False, default=True)
    
    # Geographic and temporal restrictions
    territories = Column(JSON, nullable=True)  # Array of allowed territories
    languages = Column(JSON, nullable=True)  # Array of allowed languages
    valid_from = Column(DateTime(timezone=True), nullable=True)
    valid_until = Column(DateTime(timezone=True), nullable=True)
    
    # Usage tracking
    max_uses = Column(Integer, nullable=True)
    current_uses = Column(Integer, nullable=False, default=0)
    
    # Financial terms
    license_fee = Column(Numeric(18, 8), nullable=True)
    currency = Column(String(10), nullable=True)
    royalty_percentage = Column(Numeric(5, 2), nullable=True)
    
    # Blockchain information
    transaction_hash = Column(String(66), nullable=True, index=True)
    block_number = Column(Integer, nullable=True)
    
    # Status
    active = Column(Boolean, nullable=False, default=True)
    revoked = Column(Boolean, nullable=False, default=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    revocation_reason = Column(Text, nullable=True)
    
    # Timestamps
    granted_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    asset = relationship("ProvenanceAsset", back_populates="licenses")
    
    __table_args__ = (
        Index('idx_provenance_license_type', 'license_type', 'active'),
        Index('idx_provenance_license_parties', 'licensor_address', 'licensee_address'),
        Index('idx_provenance_license_validity', 'valid_from', 'valid_until'),
    )


class ProvenanceReport(Base):
    """Generated provenance reports."""
    __tablename__ = "provenance_reports"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id = Column(UUID(as_uuid=True), ForeignKey("provenance_assets.id"), nullable=False)
    
    # Report details
    report_type = Column(String(100), nullable=False, index=True)  # full, summary, audit, etc.
    report_format = Column(String(50), nullable=False)  # json, pdf, xml
    
    # Report content
    report_data = Column(JSON, nullable=False)
    report_hash = Column(String(64), nullable=False, index=True)
    
    # IPFS storage
    ipfs_hash = Column(String(255), nullable=True)
    report_uri = Column(String(512), nullable=True)
    
    # Metadata
    generated_by = Column(String(42), nullable=False)
    requester = Column(String(42), nullable=True)
    purpose = Column(String(255), nullable=True)
    
    # Integrity and verification
    integrity_score = Column(Numeric(3, 2), nullable=True)
    verification_count = Column(Integer, nullable=False, default=0)
    event_count = Column(Integer, nullable=False, default=0)
    
    # Access control
    public = Column(Boolean, nullable=False, default=False)
    access_key = Column(String(64), nullable=True)
    
    # Timestamps
    generated_at = Column(DateTime(timezone=True), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    asset = relationship("ProvenanceAsset")
    
    __table_args__ = (
        Index('idx_provenance_report_type', 'report_type', 'generated_at'),
        Index('idx_provenance_report_requester', 'requester', 'generated_at'),
        Index('idx_provenance_report_hash', 'report_hash'),
    )


class ProvenanceAuditLog(Base):
    """Audit log for provenance operations."""
    __tablename__ = "provenance_audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Operation details
    operation = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(50), nullable=False)
    resource_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Actor information
    actor_address = Column(String(42), nullable=False, index=True)
    actor_ip = Column(String(45), nullable=True)
    user_agent = Column(String(512), nullable=True)
    
    # Operation context
    operation_data = Column(JSON, nullable=True)
    result = Column(String(50), nullable=False)  # success, failure, error
    error_message = Column(Text, nullable=True)
    
    # Blockchain context
    network = Column(Enum(NetworkType), nullable=True)
    transaction_hash = Column(String(66), nullable=True, index=True)
    gas_used = Column(Integer, nullable=True)
    
    # Timestamps
    occurred_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('idx_provenance_audit_operation', 'operation', 'occurred_at'),
        Index('idx_provenance_audit_actor', 'actor_address', 'occurred_at'),
        Index('idx_provenance_audit_resource', 'resource_type', 'resource_id'),
    )


class ProvenanceStatistics(Base):
    """Aggregated statistics for provenance tracking."""
    __tablename__ = "provenance_statistics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Statistics period
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)
    period_type = Column(String(20), nullable=False)  # daily, weekly, monthly
    
    # Asset statistics
    total_assets = Column(Integer, nullable=False, default=0)
    new_assets = Column(Integer, nullable=False, default=0)
    verified_assets = Column(Integer, nullable=False, default=0)
    disputed_assets = Column(Integer, nullable=False, default=0)
    
    # Event statistics
    total_events = Column(Integer, nullable=False, default=0)
    creation_events = Column(Integer, nullable=False, default=0)
    modification_events = Column(Integer, nullable=False, default=0)
    transfer_events = Column(Integer, nullable=False, default=0)
    verification_events = Column(Integer, nullable=False, default=0)
    
    # Network statistics
    ethereum_transactions = Column(Integer, nullable=False, default=0)
    polygon_transactions = Column(Integer, nullable=False, default=0)
    total_gas_used = Column(Integer, nullable=False, default=0)
    average_gas_price = Column(Numeric(12, 0), nullable=True)
    
    # Quality metrics
    average_integrity_score = Column(Numeric(3, 2), nullable=True)
    verification_rate = Column(Numeric(3, 2), nullable=True)  # % of assets verified
    dispute_rate = Column(Numeric(3, 2), nullable=True)  # % of assets disputed
    
    # Timestamps
    calculated_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        UniqueConstraint('period_start', 'period_type', name='uq_provenance_stats_period'),
        Index('idx_provenance_stats_period', 'period_type', 'period_start'),
    )