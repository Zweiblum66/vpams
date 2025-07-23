"""
Database models for Security Certification Service.
"""
from datetime import datetime, timezone
from typing import Optional
from enum import Enum as PyEnum
import uuid

from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Text, 
    ForeignKey, Numeric, JSON, Enum, UniqueConstraint, Index
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class AuditStatus(PyEnum):
    """Audit status enumeration."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SecurityLevel(PyEnum):
    """Security level enumeration."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class FindingStatus(PyEnum):
    """Security finding status."""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    MITIGATED = "mitigated"
    FIXED = "fixed"
    FALSE_POSITIVE = "false_positive"
    ACCEPTED_RISK = "accepted_risk"


class ComplianceStatus(PyEnum):
    """Compliance check status."""
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    PARTIAL = "partial"
    NOT_APPLICABLE = "not_applicable"
    PENDING = "pending"


class VulnerabilityCategory(PyEnum):
    """Vulnerability categories based on OWASP Top 10."""
    INJECTION = "injection"
    BROKEN_AUTH = "broken_authentication"
    SENSITIVE_DATA = "sensitive_data_exposure"
    XML_EXTERNAL = "xml_external_entities"
    BROKEN_ACCESS = "broken_access_control"
    SECURITY_MISCONFIG = "security_misconfiguration"
    XSS = "cross_site_scripting"
    INSECURE_DESERIALIZATION = "insecure_deserialization"
    VULNERABLE_COMPONENTS = "vulnerable_components"
    INSUFFICIENT_LOGGING = "insufficient_logging"


class ComplianceStandard(PyEnum):
    """Supported compliance standards."""
    ISO27001 = "iso27001"
    SOC2_TYPE2 = "soc2_type2"
    GDPR = "gdpr"
    HIPAA = "hipaa"
    PCI_DSS = "pci_dss"
    NIST_CSF = "nist_csf"
    SOX = "sox"
    FEDRAMP = "fedramp"


class CertificationStatus(PyEnum):
    """Certification status."""
    CERTIFIED = "certified"
    CONDITIONAL = "conditional"
    NOT_CERTIFIED = "not_certified"
    EXPIRED = "expired"
    REVOKED = "revoked"


class User(Base):
    """User model (simplified for security service)."""
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), nullable=False, unique=True, index=True)
    full_name = Column(String(255), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    
    # Relationships
    audits_initiated = relationship("SecurityAudit", back_populates="initiated_by")
    findings_assigned = relationship("SecurityFinding", back_populates="assigned_to")


class SecurityAudit(Base):
    """Security audit records."""
    __tablename__ = "security_audits"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_id = Column(String(100), nullable=False, unique=True, index=True)
    
    # Audit details
    audit_type = Column(String(50), nullable=False, default="comprehensive")
    status = Column(Enum(AuditStatus), nullable=False, default=AuditStatus.PENDING)
    priority = Column(String(20), nullable=False, default="normal")
    description = Column(Text, nullable=True)
    
    # Target information
    target_systems = Column(JSON, nullable=False)  # List of target systems
    scope = Column(Text, nullable=True)
    
    # Compliance requirements
    compliance_standards = Column(JSON, nullable=True)  # List of standards
    compliance_scope = Column(JSON, nullable=True)
    
    # Results summary
    total_findings = Column(Integer, nullable=False, default=0)
    critical_findings = Column(Integer, nullable=False, default=0)
    high_findings = Column(Integer, nullable=False, default=0)
    medium_findings = Column(Integer, nullable=False, default=0)
    low_findings = Column(Integer, nullable=False, default=0)
    info_findings = Column(Integer, nullable=False, default=0)
    
    # Compliance summary
    total_controls = Column(Integer, nullable=False, default=0)
    compliant_controls = Column(Integer, nullable=False, default=0)
    compliance_score = Column(Numeric(5, 2), nullable=True)
    
    # Security metrics
    security_posture_score = Column(Numeric(5, 2), nullable=True)
    coverage_percentage = Column(Numeric(5, 2), nullable=True)
    risk_score = Column(Numeric(5, 2), nullable=True)
    
    # Audit lifecycle
    initiated_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    assigned_to_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    
    # Timestamps
    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Audit configuration
    configuration = Column(JSON, nullable=True)
    
    # Relationships
    initiated_by = relationship("User", foreign_keys=[initiated_by_id], back_populates="audits_initiated")
    assigned_to = relationship("User", foreign_keys=[assigned_to_id])
    findings = relationship("SecurityFinding", back_populates="audit", cascade="all, delete-orphan")
    compliance_checks = relationship("ComplianceCheck", back_populates="audit", cascade="all, delete-orphan")
    certifications = relationship("SecurityCertification", back_populates="audit")
    
    __table_args__ = (
        Index('idx_security_audit_status', 'status', 'created_at'),
        Index('idx_security_audit_type', 'audit_type', 'status'),
        Index('idx_security_audit_initiated', 'initiated_by_id', 'created_at'),
    )


class SecurityFinding(Base):
    """Security findings from audits."""
    __tablename__ = "security_findings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_id = Column(UUID(as_uuid=True), ForeignKey("security_audits.id"), nullable=False)
    
    # Finding identification
    finding_id = Column(String(100), nullable=False, index=True)
    external_id = Column(String(100), nullable=True)  # External scanner ID
    
    # Finding details
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(Enum(SecurityLevel), nullable=False, index=True)
    category = Column(Enum(VulnerabilityCategory), nullable=False, index=True)
    status = Column(Enum(FindingStatus), nullable=False, default=FindingStatus.OPEN)
    
    # Vulnerability information
    cve_id = Column(String(50), nullable=True, index=True)
    cvss_score = Column(Numeric(3, 1), nullable=True)
    cvss_vector = Column(String(200), nullable=True)
    cwe_id = Column(String(50), nullable=True)
    
    # Affected components
    affected_components = Column(JSON, nullable=True)  # List of affected systems/components
    affected_urls = Column(JSON, nullable=True)  # List of affected URLs
    affected_files = Column(JSON, nullable=True)  # List of affected files
    
    # Technical details
    technical_details = Column(JSON, nullable=True)
    proof_of_concept = Column(Text, nullable=True)
    attack_vector = Column(String(100), nullable=True)
    
    # Remediation
    remediation = Column(Text, nullable=True)
    remediation_effort = Column(String(50), nullable=True)  # low, medium, high
    remediation_priority = Column(Integer, nullable=True)
    
    # References
    references = Column(JSON, nullable=True)  # List of reference URLs
    tags = Column(JSON, nullable=True)  # List of tags
    
    # Assignment and tracking
    assigned_to_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    due_date = Column(DateTime(timezone=True), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    
    # Risk assessment
    business_impact = Column(String(50), nullable=True)
    likelihood = Column(String(50), nullable=True)
    risk_rating = Column(String(50), nullable=True)
    
    # Timestamps
    discovered_at = Column(DateTime(timezone=True), nullable=False)
    first_seen = Column(DateTime(timezone=True), nullable=True)
    last_seen = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    audit = relationship("SecurityAudit", back_populates="findings")
    assigned_to = relationship("User", back_populates="findings_assigned")
    
    __table_args__ = (
        UniqueConstraint('audit_id', 'finding_id', name='uq_security_finding_audit'),
        Index('idx_security_finding_severity', 'severity', 'status'),
        Index('idx_security_finding_category', 'category', 'severity'),
        Index('idx_security_finding_cve', 'cve_id'),
        Index('idx_security_finding_due', 'due_date', 'status'),
    )


class ComplianceCheck(Base):
    """Compliance check results."""
    __tablename__ = "compliance_checks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_id = Column(UUID(as_uuid=True), ForeignKey("security_audits.id"), nullable=False)
    
    # Check identification
    check_id = Column(String(100), nullable=False, index=True)
    standard = Column(Enum(ComplianceStandard), nullable=False, index=True)
    control_id = Column(String(50), nullable=False)
    control_family = Column(String(100), nullable=True)
    
    # Check details
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    requirement = Column(Text, nullable=True)
    status = Column(Enum(ComplianceStatus), nullable=False, index=True)
    
    # Assessment details
    assessment_method = Column(String(100), nullable=True)
    testing_procedure = Column(Text, nullable=True)
    evidence_required = Column(JSON, nullable=True)
    
    # Results
    evidence_collected = Column(JSON, nullable=True)  # List of evidence
    gaps_identified = Column(JSON, nullable=True)  # List of gaps
    findings = Column(JSON, nullable=True)  # Related security findings
    
    # Remediation
    remediation_steps = Column(JSON, nullable=True)  # List of remediation steps
    remediation_owner = Column(String(255), nullable=True)
    remediation_timeline = Column(String(100), nullable=True)
    
    # Risk and impact
    risk_level = Column(String(50), nullable=True)
    business_impact = Column(Text, nullable=True)
    regulatory_impact = Column(Text, nullable=True)
    
    # Assessment tracking
    assessor = Column(String(255), nullable=True)
    assessment_date = Column(DateTime(timezone=True), nullable=True)
    last_reviewed = Column(DateTime(timezone=True), nullable=True)
    next_review_due = Column(DateTime(timezone=True), nullable=True)
    review_frequency = Column(String(50), nullable=True)  # annual, semi-annual, quarterly
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    audit = relationship("SecurityAudit", back_populates="compliance_checks")
    
    __table_args__ = (
        UniqueConstraint('audit_id', 'check_id', name='uq_compliance_check_audit'),
        Index('idx_compliance_check_standard', 'standard', 'status'),
        Index('idx_compliance_check_control', 'control_id', 'standard'),
        Index('idx_compliance_check_review', 'next_review_due', 'status'),
    )


class SecurityCertification(Base):
    """Security certifications."""
    __tablename__ = "security_certifications"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_id = Column(UUID(as_uuid=True), ForeignKey("security_audits.id"), nullable=False)
    
    # Certification details
    certification_id = Column(String(100), nullable=False, unique=True, index=True)
    certification_type = Column(String(100), nullable=False)
    status = Column(Enum(CertificationStatus), nullable=False, index=True)
    
    # Standards covered
    compliance_standards = Column(JSON, nullable=False)  # List of standards
    scope = Column(Text, nullable=True)
    exclusions = Column(JSON, nullable=True)
    
    # Certification body
    issued_by = Column(String(255), nullable=False)
    issuer_accreditation = Column(String(255), nullable=True)
    auditor_name = Column(String(255), nullable=True)
    auditor_credentials = Column(JSON, nullable=True)
    
    # Validity
    issued_date = Column(DateTime(timezone=True), nullable=False)
    valid_from = Column(DateTime(timezone=True), nullable=False)
    valid_until = Column(DateTime(timezone=True), nullable=False)
    
    # Certification details
    certificate_number = Column(String(100), nullable=True)
    certificate_url = Column(String(500), nullable=True)
    public_certificate = Column(Boolean, nullable=False, default=False)
    
    # Conditions and requirements
    conditions = Column(JSON, nullable=True)  # List of certification conditions
    requirements = Column(JSON, nullable=True)  # Ongoing requirements
    
    # Surveillance and maintenance
    surveillance_required = Column(Boolean, nullable=False, default=True)
    next_surveillance_date = Column(DateTime(timezone=True), nullable=True)
    surveillance_frequency = Column(String(50), nullable=True)
    
    # Renewal information
    renewal_required = Column(Boolean, nullable=False, default=True)
    renewal_notice_period = Column(Integer, nullable=True)  # Days before expiry
    renewal_started = Column(Boolean, nullable=False, default=False)
    
    # Status tracking
    suspended = Column(Boolean, nullable=False, default=False)
    suspension_reason = Column(Text, nullable=True)
    suspension_date = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    audit = relationship("SecurityAudit", back_populates="certifications")
    
    __table_args__ = (
        Index('idx_security_cert_status', 'status', 'valid_until'),
        Index('idx_security_cert_type', 'certification_type', 'status'),
        Index('idx_security_cert_validity', 'valid_from', 'valid_until'),
        Index('idx_security_cert_surveillance', 'next_surveillance_date', 'status'),
    )


class SecurityMetrics(Base):
    """Security metrics and KPIs."""
    __tablename__ = "security_metrics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Metrics period
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)
    period_type = Column(String(20), nullable=False)  # daily, weekly, monthly, quarterly
    
    # Finding metrics
    total_findings = Column(Integer, nullable=False, default=0)
    new_findings = Column(Integer, nullable=False, default=0)
    resolved_findings = Column(Integer, nullable=False, default=0)
    critical_findings = Column(Integer, nullable=False, default=0)
    high_findings = Column(Integer, nullable=False, default=0)
    medium_findings = Column(Integer, nullable=False, default=0)
    low_findings = Column(Integer, nullable=False, default=0)
    
    # Compliance metrics
    total_controls = Column(Integer, nullable=False, default=0)
    compliant_controls = Column(Integer, nullable=False, default=0)
    non_compliant_controls = Column(Integer, nullable=False, default=0)
    compliance_score = Column(Numeric(5, 2), nullable=True)
    
    # Security posture metrics
    security_posture_score = Column(Numeric(5, 2), nullable=True)
    risk_score = Column(Numeric(5, 2), nullable=True)
    coverage_percentage = Column(Numeric(5, 2), nullable=True)
    
    # Performance metrics
    mean_time_to_detect = Column(Numeric(10, 2), nullable=True)  # Hours
    mean_time_to_respond = Column(Numeric(10, 2), nullable=True)  # Hours
    mean_time_to_remediate = Column(Numeric(10, 2), nullable=True)  # Hours
    
    # Audit metrics
    audits_conducted = Column(Integer, nullable=False, default=0)
    audit_coverage = Column(Numeric(5, 2), nullable=True)
    audit_effectiveness = Column(Numeric(5, 2), nullable=True)
    
    # Certification metrics
    active_certifications = Column(Integer, nullable=False, default=0)
    expiring_certifications = Column(Integer, nullable=False, default=0)
    certification_compliance_rate = Column(Numeric(5, 2), nullable=True)
    
    # Trend indicators
    finding_trend = Column(String(20), nullable=True)  # increasing, decreasing, stable
    compliance_trend = Column(String(20), nullable=True)
    risk_trend = Column(String(20), nullable=True)
    
    # Timestamps
    calculated_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        UniqueConstraint('period_start', 'period_type', name='uq_security_metrics_period'),
        Index('idx_security_metrics_period', 'period_type', 'period_start'),
        Index('idx_security_metrics_calculated', 'calculated_at'),
    )


class AuditLog(Base):
    """Audit log for security certification activities."""
    __tablename__ = "audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Log details
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(50), nullable=False)
    resource_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Actor information
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    user_email = Column(String(255), nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    
    # Change details
    old_values = Column(JSON, nullable=True)
    new_values = Column(JSON, nullable=True)
    changes = Column(JSON, nullable=True)
    
    # Context
    session_id = Column(String(100), nullable=True)
    correlation_id = Column(String(100), nullable=True)
    metadata = Column(JSON, nullable=True)
    
    # Result
    result = Column(String(20), nullable=False)  # success, failure, error
    error_message = Column(Text, nullable=True)
    
    # Timestamps
    occurred_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User")
    
    __table_args__ = (
        Index('idx_audit_log_action', 'action', 'occurred_at'),
        Index('idx_audit_log_user', 'user_id', 'occurred_at'),
        Index('idx_audit_log_resource', 'resource_type', 'resource_id'),
        Index('idx_audit_log_correlation', 'correlation_id'),
    )