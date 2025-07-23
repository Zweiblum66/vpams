"""
Database models for Security Audit Service
"""

from sqlalchemy import Column, String, DateTime, Float, Integer, Text, JSON, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

Base = declarative_base()


class ScanResult(Base):
    """Security scan result model"""
    __tablename__ = "scan_results"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_type = Column(String(50), nullable=False, index=True)
    target = Column(String(1024), nullable=False)
    status = Column(String(20), nullable=False, index=True)
    
    # Timing
    started_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Float, nullable=True)
    
    # Results
    findings_count = Column(Integer, default=0)
    critical_count = Column(Integer, default=0)
    high_count = Column(Integer, default=0)
    medium_count = Column(Integer, default=0)
    low_count = Column(Integer, default=0)
    info_count = Column(Integer, default=0)
    
    # Metadata
    scanner_version = Column(String(100), nullable=True)
    options = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Audit trail
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    findings = relationship("Finding", back_populates="scan_result", cascade="all, delete-orphan")
    audit_scans = relationship("AuditScan", back_populates="scan_result")


class Finding(Base):
    """Security finding model"""
    __tablename__ = "findings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_result_id = Column(UUID(as_uuid=True), ForeignKey("scan_results.id"), nullable=False)
    
    # Basic information
    type = Column(String(100), nullable=False)
    scanner = Column(String(50), nullable=False)
    severity = Column(String(20), nullable=False, index=True)
    confidence = Column(String(20), nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    
    # Location information
    file_path = Column(String(1024), nullable=True)
    line_number = Column(Integer, nullable=True)
    url = Column(String(1024), nullable=True)
    
    # Security identifiers
    cve = Column(String(50), nullable=True, index=True)
    cvss_score = Column(Float, nullable=True)
    cwe_id = Column(String(50), nullable=True)
    owasp_categories = Column(JSON, nullable=True)
    
    # Fix information
    solution = Column(Text, nullable=True)
    references = Column(JSON, nullable=True)
    
    # Additional data
    evidence = Column(Text, nullable=True)
    attack_vector = Column(String(500), nullable=True)
    
    # Status tracking
    is_false_positive = Column(Boolean, default=False)
    is_suppressed = Column(Boolean, default=False)
    suppression_reason = Column(Text, nullable=True)
    
    # Audit trail
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    
    # Relationships
    scan_result = relationship("ScanResult", back_populates="findings")


class ComplianceResult(Base):
    """Compliance check result model"""
    __tablename__ = "compliance_results"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    standard = Column(String(50), nullable=False, index=True)
    target = Column(String(1024), nullable=False)
    
    # Results
    overall_score = Column(Float, nullable=False)
    status = Column(String(20), nullable=False)
    controls_data = Column(JSON, nullable=False)  # Serialized controls and requirements
    
    # Recommendations
    recommendations = Column(JSON, nullable=True)
    
    # Audit trail
    timestamp = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    
    # Relationships
    audit_compliance = relationship("AuditCompliance", back_populates="compliance_result")


class AuditResult(Base):
    """Security audit result model"""
    __tablename__ = "audit_results"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    target = Column(String(1024), nullable=False)
    
    # Timing
    started_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Float, nullable=True)
    
    # Summary statistics
    total_scans = Column(Integer, default=0)
    successful_scans = Column(Integer, default=0)
    failed_scans = Column(Integer, default=0)
    total_findings = Column(Integer, default=0)
    critical_findings = Column(Integer, default=0)
    high_findings = Column(Integer, default=0)
    compliance_score = Column(Float, nullable=True)
    
    # Status
    status = Column(String(20), nullable=False, index=True)
    error_message = Column(Text, nullable=True)
    
    # Configuration
    requested_scans = Column(JSON, nullable=False)  # List of scan types requested
    requested_standards = Column(JSON, nullable=True)  # List of compliance standards
    options = Column(JSON, nullable=True)
    
    # Audit trail
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    audit_scans = relationship("AuditScan", back_populates="audit_result", cascade="all, delete-orphan")
    audit_compliance = relationship("AuditCompliance", back_populates="audit_result", cascade="all, delete-orphan")


class AuditScan(Base):
    """Junction table linking audits to scan results"""
    __tablename__ = "audit_scans"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_result_id = Column(UUID(as_uuid=True), ForeignKey("audit_results.id"), nullable=False)
    scan_result_id = Column(UUID(as_uuid=True), ForeignKey("scan_results.id"), nullable=False)
    
    # Audit trail
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    
    # Relationships
    audit_result = relationship("AuditResult", back_populates="audit_scans")
    scan_result = relationship("ScanResult", back_populates="audit_scans")


class AuditCompliance(Base):
    """Junction table linking audits to compliance results"""
    __tablename__ = "audit_compliance"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_result_id = Column(UUID(as_uuid=True), ForeignKey("audit_results.id"), nullable=False)
    compliance_result_id = Column(UUID(as_uuid=True), ForeignKey("compliance_results.id"), nullable=False)
    
    # Audit trail
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    
    # Relationships
    audit_result = relationship("AuditResult", back_populates="audit_compliance")
    compliance_result = relationship("ComplianceResult", back_populates="audit_compliance")


class ScanTemplate(Base):
    """Reusable scan templates"""
    __tablename__ = "scan_templates"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    
    # Template configuration
    scan_types = Column(JSON, nullable=False)  # List of scan types
    compliance_standards = Column(JSON, nullable=True)  # List of compliance standards
    options = Column(JSON, nullable=True)  # Default options
    
    # Usage tracking
    usage_count = Column(Integer, default=0)
    last_used = Column(DateTime(timezone=True), nullable=True)
    
    # Audit trail
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(100), nullable=True)  # User who created the template


class SecurityMetric(Base):
    """Security metrics and KPIs"""
    __tablename__ = "security_metrics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    metric_name = Column(String(100), nullable=False, index=True)
    metric_value = Column(Float, nullable=False)
    metric_unit = Column(String(50), nullable=True)
    
    # Context
    target = Column(String(1024), nullable=True)
    scan_type = Column(String(50), nullable=True)
    time_period = Column(String(50), nullable=True)  # daily, weekly, monthly
    
    # Metadata
    additional_data = Column(JSON, nullable=True)
    
    # Timing
    timestamp = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class ScanSchedule(Base):
    """Scheduled security scans"""
    __tablename__ = "scan_schedules"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    target = Column(String(1024), nullable=False)
    
    # Schedule configuration
    cron_expression = Column(String(100), nullable=False)  # Cron expression for scheduling
    scan_types = Column(JSON, nullable=False)  # List of scan types
    compliance_standards = Column(JSON, nullable=True)  # List of compliance standards
    options = Column(JSON, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    last_run = Column(DateTime(timezone=True), nullable=True)
    next_run = Column(DateTime(timezone=True), nullable=True)
    failure_count = Column(Integer, default=0)
    
    # Notifications
    notification_emails = Column(JSON, nullable=True)  # List of emails for notifications
    notification_webhooks = Column(JSON, nullable=True)  # List of webhooks for notifications
    
    # Audit trail
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(100), nullable=True)