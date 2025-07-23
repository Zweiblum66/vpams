"""
Pydantic schemas for Security Audit Service
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class ScanType(str, Enum):
    """Types of security scans"""
    CODE = "code"
    DEPENDENCY = "dependency"
    WEB = "web"
    NETWORK = "network"
    COMPLIANCE = "compliance"


class ScanStatus(str, Enum):
    """Scan execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class SeverityLevel(str, Enum):
    """Vulnerability severity levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ComplianceStandard(str, Enum):
    """Supported compliance standards"""
    ISO27001 = "iso27001"
    GDPR = "gdpr"
    SOC2 = "soc2"
    PCI_DSS = "pci_dss"


# Request schemas
class ScanRequest(BaseModel):
    """Base scan request"""
    target: str = Field(..., description="Target to scan (URL, file path, etc.)")
    scan_type: ScanType = Field(..., description="Type of scan to perform")
    options: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Scan-specific options")


class CodeScanRequest(ScanRequest):
    """Code security scan request"""
    scan_type: ScanType = Field(default=ScanType.CODE, const=True)
    include_patterns: Optional[List[str]] = Field(default=None, description="File patterns to include")
    exclude_patterns: Optional[List[str]] = Field(default=None, description="File patterns to exclude")
    scanners: Optional[List[str]] = Field(default=["bandit", "semgrep"], description="Scanners to use")


class DependencyScanRequest(ScanRequest):
    """Dependency scan request"""
    scan_type: ScanType = Field(default=ScanType.DEPENDENCY, const=True)
    requirements_files: Optional[List[str]] = Field(default=None, description="Specific requirements files")
    scanners: Optional[List[str]] = Field(default=["safety", "pip-audit"], description="Scanners to use")


class WebScanRequest(ScanRequest):
    """Web application scan request"""
    scan_type: ScanType = Field(default=ScanType.WEB, const=True)
    spider_enabled: bool = Field(default=True, description="Enable spider scanning")
    active_scan: bool = Field(default=True, description="Enable active vulnerability scanning")
    authentication: Optional[Dict[str, str]] = Field(default=None, description="Authentication details")


class ComplianceScanRequest(ScanRequest):
    """Compliance check request"""
    scan_type: ScanType = Field(default=ScanType.COMPLIANCE, const=True)
    standards: List[ComplianceStandard] = Field(..., description="Compliance standards to check")


# Response schemas
class Finding(BaseModel):
    """Security finding"""
    id: Optional[str] = Field(default=None, description="Finding identifier")
    type: str = Field(..., description="Type of finding")
    scanner: str = Field(..., description="Scanner that found the issue")
    severity: SeverityLevel = Field(..., description="Severity level")
    confidence: str = Field(..., description="Confidence level")
    title: str = Field(..., description="Finding title")
    description: str = Field(..., description="Detailed description")
    
    # Location information
    file: Optional[str] = Field(default=None, description="File path")
    line: Optional[int] = Field(default=None, description="Line number")
    url: Optional[str] = Field(default=None, description="URL")
    
    # Additional details
    cve: Optional[str] = Field(default=None, description="CVE identifier")
    cvss_score: Optional[float] = Field(default=None, description="CVSS score")
    owasp: Optional[List[str]] = Field(default=None, description="OWASP categories")
    cwe_id: Optional[str] = Field(default=None, description="CWE identifier")
    
    # Fix information
    solution: Optional[str] = Field(default=None, description="Recommended solution")
    references: Optional[List[str]] = Field(default=None, description="Reference links")


class ScanSummary(BaseModel):
    """Scan results summary"""
    total: int = Field(..., description="Total findings")
    critical: int = Field(default=0, description="Critical findings")
    high: int = Field(default=0, description="High severity findings")
    medium: int = Field(default=0, description="Medium severity findings")
    low: int = Field(default=0, description="Low severity findings")
    info: int = Field(default=0, description="Informational findings")


class ScanResult(BaseModel):
    """Scan execution result"""
    id: str = Field(..., description="Scan result identifier")
    scan_type: ScanType = Field(..., description="Type of scan")
    target: str = Field(..., description="Scan target")
    status: ScanStatus = Field(..., description="Scan status")
    
    # Timing
    started_at: datetime = Field(..., description="Scan start time")
    completed_at: Optional[datetime] = Field(default=None, description="Scan completion time")
    duration_seconds: Optional[float] = Field(default=None, description="Scan duration")
    
    # Results
    findings: List[Finding] = Field(default_factory=list, description="Security findings")
    summary: ScanSummary = Field(..., description="Results summary")
    
    # Metadata
    scanner_version: Optional[str] = Field(default=None, description="Scanner version")
    options: Optional[Dict[str, Any]] = Field(default=None, description="Scan options used")
    error_message: Optional[str] = Field(default=None, description="Error message if failed")


# Compliance schemas
class ComplianceRequirement(BaseModel):
    """Individual compliance requirement"""
    id: str = Field(..., description="Requirement identifier")
    description: str = Field(..., description="Requirement description")
    status: str = Field(..., description="Compliance status (pass/fail)")
    evidence: Optional[str] = Field(default=None, description="Evidence or explanation")
    severity: Optional[SeverityLevel] = Field(default=None, description="Non-compliance severity")


class ComplianceControl(BaseModel):
    """Compliance control or principle"""
    id: str = Field(..., description="Control identifier")
    name: str = Field(..., description="Control name")
    requirements: List[ComplianceRequirement] = Field(..., description="Control requirements")
    score: float = Field(..., description="Compliance score (0-1)")


class ComplianceResult(BaseModel):
    """Compliance check result"""
    id: str = Field(..., description="Compliance result identifier")
    standard: ComplianceStandard = Field(..., description="Compliance standard")
    target: str = Field(..., description="Target assessed")
    
    # Timing
    timestamp: datetime = Field(..., description="Assessment timestamp")
    
    # Results
    controls: List[ComplianceControl] = Field(..., description="Control assessments")
    score: float = Field(..., description="Overall compliance score (0-1)")
    status: str = Field(..., description="Overall status (compliant/non_compliant)")
    
    # Recommendations
    recommendations: Optional[List[str]] = Field(default=None, description="Improvement recommendations")


# Audit schemas
class AuditRequest(BaseModel):
    """Security audit request"""
    target: str = Field(..., description="Audit target")
    scans: List[ScanType] = Field(default_factory=lambda: [ScanType.CODE, ScanType.DEPENDENCY], description="Scans to include")
    compliance_standards: Optional[List[ComplianceStandard]] = Field(default=None, description="Compliance standards to check")
    options: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Audit options")


class AuditSummary(BaseModel):
    """Audit execution summary"""
    total_scans: int = Field(..., description="Total scans performed")
    successful_scans: int = Field(..., description="Successful scans")
    failed_scans: int = Field(..., description="Failed scans")
    total_findings: int = Field(..., description="Total findings")
    critical_findings: int = Field(..., description="Critical findings")
    high_findings: int = Field(..., description="High severity findings")
    compliance_score: Optional[float] = Field(default=None, description="Overall compliance score")


class AuditResult(BaseModel):
    """Complete audit result"""
    id: str = Field(..., description="Audit identifier")
    target: str = Field(..., description="Audit target")
    
    # Timing
    started_at: datetime = Field(..., description="Audit start time")
    completed_at: Optional[datetime] = Field(default=None, description="Audit completion time")
    duration_seconds: Optional[float] = Field(default=None, description="Audit duration")
    
    # Results
    scan_results: List[ScanResult] = Field(default_factory=list, description="Individual scan results")
    compliance_results: List[ComplianceResult] = Field(default_factory=list, description="Compliance check results")
    summary: AuditSummary = Field(..., description="Audit summary")
    
    # Status
    status: ScanStatus = Field(..., description="Audit status")
    error_message: Optional[str] = Field(default=None, description="Error message if failed")


# List responses
class ScanListResponse(BaseModel):
    """List of scan results"""
    scans: List[ScanResult] = Field(..., description="Scan results")
    total: int = Field(..., description="Total count")
    page: int = Field(default=1, description="Current page")
    limit: int = Field(default=20, description="Page size")


class AuditListResponse(BaseModel):
    """List of audit results"""
    audits: List[AuditResult] = Field(..., description="Audit results")
    total: int = Field(..., description="Total count")
    page: int = Field(default=1, description="Current page")
    limit: int = Field(default=20, description="Page size")


# Configuration schemas
class ScannerConfig(BaseModel):
    """Scanner configuration"""
    name: str = Field(..., description="Scanner name")
    enabled: bool = Field(default=True, description="Whether scanner is enabled")
    options: Dict[str, Any] = Field(default_factory=dict, description="Scanner-specific options")


class SecurityAuditConfig(BaseModel):
    """Security audit service configuration"""
    scanners: List[ScannerConfig] = Field(..., description="Available scanners")
    compliance_standards: List[ComplianceStandard] = Field(..., description="Supported compliance standards")
    default_scan_timeout: int = Field(default=300, description="Default scan timeout in seconds")
    max_concurrent_scans: int = Field(default=5, description="Maximum concurrent scans")


# Health check schema
class HealthStatus(BaseModel):
    """Service health status"""
    status: str = Field(..., description="Service status")
    timestamp: datetime = Field(..., description="Check timestamp")
    version: str = Field(..., description="Service version")
    uptime_seconds: float = Field(..., description="Service uptime in seconds")
    database_connected: bool = Field(..., description="Database connection status")
    redis_connected: bool = Field(..., description="Redis connection status")
    active_scans: int = Field(..., description="Number of active scans")