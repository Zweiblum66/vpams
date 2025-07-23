"""Database models for Security Audit Service"""

from sqlalchemy import Column, String, DateTime, Text, JSON, Float, Integer, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import uuid
import enum

Base = declarative_base()


class SeverityLevel(str, enum.Enum):
    """Security severity levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AuditStatus(str, enum.Enum):
    """Audit scan status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ComplianceStandard(str, enum.Enum):
    """Compliance standards"""
    ISO27001 = "ISO27001"
    SOC2 = "SOC2"
    GDPR = "GDPR"
    PCI_DSS = "PCI_DSS"
    HIPAA = "HIPAA"
    NIST_CSF = "NIST_CSF"
    SOX = "SOX"
    FEDRAMP = "FedRAMP"


class VulnerabilityCategory(str, enum.Enum):
    """OWASP vulnerability categories"""
    INJECTION = "injection"
    BROKEN_AUTH = "broken_authentication"
    SENSITIVE_DATA = "sensitive_data_exposure"
    XXE = "xml_external_entities"
    BROKEN_ACCESS = "broken_access_control"
    SECURITY_MISCONFIG = "security_misconfiguration"
    XSS = "cross_site_scripting"
    INSECURE_DESERIALIZATION = "insecure_deserialization"
    COMPONENTS_VULNERABILITIES = "components_with_vulnerabilities"
    INSUFFICIENT_LOGGING = "insufficient_logging"


class SecurityAudit(Base):
    """Security audit scan record"""
    __tablename__ = "security_audits"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    
    # Scan configuration
    scan_type = Column(String(50), nullable=False)  # full, quick, custom
    target_services = Column(JSON)  # List of services to scan
    scan_config = Column(JSON)  # Scan configuration
    
    # Status tracking
    status = Column(SQLEnum(AuditStatus), default=AuditStatus.PENDING, nullable=False)
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    duration_seconds = Column(Integer)
    
    # User who initiated the audit
    initiated_by = Column(UUID(as_uuid=True), nullable=False)
    
    # Results summary
    total_findings = Column(Integer, default=0)
    critical_findings = Column(Integer, default=0)
    high_findings = Column(Integer, default=0)
    medium_findings = Column(Integer, default=0)
    low_findings = Column(Integer, default=0)
    info_findings = Column(Integer, default=0)
    
    # Compliance scores
    compliance_scores = Column(JSON)  # {standard: score}
    overall_risk_score = Column(Float)  # 0-10 scale
    
    # Report paths
    report_path = Column(String(500))
    executive_summary = Column(Text)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    findings = relationship("SecurityFinding", back_populates="audit", cascade="all, delete-orphan")
    compliance_checks = relationship("ComplianceCheck", back_populates="audit", cascade="all, delete-orphan")


class SecurityFinding(Base):
    """Individual security finding/vulnerability"""
    __tablename__ = "security_findings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_id = Column(UUID(as_uuid=True), ForeignKey("security_audits.id"), nullable=False)
    
    # Finding details
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(SQLEnum(SeverityLevel), nullable=False)
    category = Column(SQLEnum(VulnerabilityCategory))
    
    # CVSS scoring
    cvss_score = Column(Float)
    cvss_vector = Column(String(100))
    
    # CVE reference
    cve_id = Column(String(50))
    cwe_id = Column(String(50))
    
    # Location
    service_name = Column(String(100))
    component = Column(String(200))
    file_path = Column(String(500))
    line_number = Column(Integer)
    code_snippet = Column(Text)
    
    # Evidence
    evidence = Column(JSON)  # Screenshots, logs, etc.
    exploit_available = Column(Boolean, default=False)
    
    # Remediation
    remediation = Column(Text)
    remediation_effort = Column(String(50))  # low, medium, high
    references = Column(JSON)  # List of reference URLs
    
    # Status
    false_positive = Column(Boolean, default=False)
    resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime(timezone=True))
    resolved_by = Column(UUID(as_uuid=True))
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    audit = relationship("SecurityAudit", back_populates="findings")


class ComplianceCheck(Base):
    """Compliance standard check result"""
    __tablename__ = "compliance_checks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_id = Column(UUID(as_uuid=True), ForeignKey("security_audits.id"), nullable=False)
    
    # Compliance details
    standard = Column(SQLEnum(ComplianceStandard), nullable=False)
    control_id = Column(String(50), nullable=False)
    control_name = Column(String(255), nullable=False)
    control_description = Column(Text)
    
    # Results
    status = Column(String(50), nullable=False)  # pass, fail, partial, not_applicable
    evidence = Column(JSON)
    findings = Column(Text)
    
    # Scoring
    weight = Column(Float, default=1.0)
    score = Column(Float)  # 0-100
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    audit = relationship("SecurityAudit", back_populates="compliance_checks")


class VulnerabilityDatabase(Base):
    """Known vulnerabilities database"""
    __tablename__ = "vulnerability_database"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Vulnerability identification
    cve_id = Column(String(50), unique=True, nullable=False, index=True)
    cwe_id = Column(String(50))
    
    # Details
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(SQLEnum(SeverityLevel), nullable=False)
    
    # CVSS metrics
    cvss_score = Column(Float)
    cvss_vector = Column(String(100))
    cvss_version = Column(String(10))
    
    # Affected systems
    affected_products = Column(JSON)  # List of CPE strings
    affected_versions = Column(JSON)
    
    # Exploit information
    exploit_available = Column(Boolean, default=False)
    exploit_description = Column(Text)
    
    # References
    references = Column(JSON)
    published_date = Column(DateTime(timezone=True))
    last_modified = Column(DateTime(timezone=True))
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class SecurityCertification(Base):
    """Security certification records"""
    __tablename__ = "security_certifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Certification details
    standard = Column(SQLEnum(ComplianceStandard), nullable=False)
    certificate_number = Column(String(100), unique=True)
    
    # Status
    status = Column(String(50), nullable=False)  # active, expired, revoked
    issued_date = Column(DateTime(timezone=True), nullable=False)
    expiry_date = Column(DateTime(timezone=True), nullable=False)
    
    # Audit information
    last_audit_id = Column(UUID(as_uuid=True))
    last_audit_date = Column(DateTime(timezone=True))
    last_audit_score = Column(Float)
    
    # Certificate files
    certificate_path = Column(String(500))
    audit_report_path = Column(String(500))
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())