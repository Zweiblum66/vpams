"""
API routes for Security Certification Service.
"""
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import uuid

from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..core.dependencies import get_db, get_current_user
from ..services.security_certification_service import (
    SecurityCertificationService, ComplianceStandard, SecurityLevel,
    SecurityCertificationError
)
from ..db.models import User

router = APIRouter(prefix="/api/v1/security", tags=["security-certification"])

# Pydantic schemas
class SecurityAuditRequest(BaseModel):
    """Schema for security audit requests."""
    target_systems: List[str] = Field(..., min_items=1, description="List of target systems to audit")
    compliance_standards: Optional[List[str]] = Field(default=None, description="Compliance standards to check")
    audit_type: str = Field(default="comprehensive", description="Type of audit to perform")
    priority: str = Field(default="normal", description="Audit priority level")
    description: Optional[str] = Field(None, description="Audit description")


class ComplianceCheckRequest(BaseModel):
    """Schema for compliance check requests."""
    standards: List[str] = Field(..., min_items=1, description="Compliance standards to check")
    scope: Optional[List[str]] = Field(default=None, description="Scope of compliance check")


class CertificationReportRequest(BaseModel):
    """Schema for certification report requests."""
    audit_id: str = Field(..., description="Audit ID to generate report for")
    report_format: str = Field(default="json", description="Report format (json, pdf, html)")
    include_executive_summary: bool = Field(default=True, description="Include executive summary")
    include_detailed_findings: bool = Field(default=True, description="Include detailed findings")
    include_remediation: bool = Field(default=True, description="Include remediation guidance")


class SecurityResponse(BaseModel):
    """Standard security response schema."""
    success: bool
    data: Dict[str, Any]
    message: str = ""


# Initialize service
security_service = SecurityCertificationService()


@router.post("/audit/start", response_model=SecurityResponse)
async def start_security_audit(
    request: SecurityAuditRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Start a comprehensive security audit."""
    try:
        # Convert compliance standards
        compliance_standards = []
        if request.compliance_standards:
            for standard in request.compliance_standards:
                try:
                    compliance_standards.append(ComplianceStandard(standard.lower()))
                except ValueError:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid compliance standard: {standard}"
                    )
        
        # Start audit as background task
        audit_id = f"audit_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        
        background_tasks.add_task(
            _perform_audit_background,
            audit_id,
            request.target_systems,
            compliance_standards,
            current_user.id
        )
        
        return SecurityResponse(
            success=True,
            data={
                "audit_id": audit_id,
                "status": "started",
                "target_systems": request.target_systems,
                "compliance_standards": request.compliance_standards,
                "started_by": str(current_user.id),
                "started_at": datetime.now(timezone.utc).isoformat(),
                "estimated_completion": "30-60 minutes"
            },
            message="Security audit started successfully"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start security audit: {str(e)}"
        )


@router.get("/audit/{audit_id}/status", response_model=SecurityResponse)
async def get_audit_status(
    audit_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get security audit status."""
    try:
        # In a real implementation, this would check database/cache for status
        # For demo purposes, returning a mock status
        return SecurityResponse(
            success=True,
            data={
                "audit_id": audit_id,
                "status": "in_progress",
                "progress": 75,
                "current_phase": "vulnerability_scanning",
                "completed_phases": ["configuration_audit", "network_scan"],
                "remaining_phases": ["compliance_check", "report_generation"],
                "estimated_remaining": "15 minutes"
            },
            message="Audit status retrieved successfully"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get audit status: {str(e)}"
        )


@router.get("/audit/{audit_id}/results", response_model=SecurityResponse)
async def get_audit_results(
    audit_id: str,
    include_details: bool = Query(default=True, description="Include detailed findings"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get security audit results."""
    try:
        # Perform a quick audit for demonstration
        target_systems = ["https://api.mams.example.com", "https://app.mams.example.com"]
        compliance_standards = [ComplianceStandard.ISO27001, ComplianceStandard.SOC2_TYPE2]
        
        audit_results = await security_service.perform_comprehensive_audit(
            target_systems=target_systems,
            compliance_standards=compliance_standards
        )
        
        if not include_details:
            # Remove detailed findings for summary view
            audit_results["findings"] = audit_results["findings"][:5]  # Top 5 only
        
        return SecurityResponse(
            success=True,
            data=audit_results,
            message="Audit results retrieved successfully"
        )
        
    except SecurityCertificationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get audit results: {str(e)}"
        )


@router.post("/compliance/check", response_model=SecurityResponse)
async def perform_compliance_check(
    request: ComplianceCheckRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Perform compliance check for specific standards."""
    try:
        # Convert compliance standards
        compliance_standards = []
        for standard in request.standards:
            try:
                compliance_standards.append(ComplianceStandard(standard.lower()))
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid compliance standard: {standard}"
                )
        
        # Perform compliance checks
        all_checks = []
        for standard in compliance_standards:
            checks = await security_service._perform_compliance_check(standard)
            all_checks.extend(checks)
        
        # Calculate compliance scores
        total_checks = len(all_checks)
        compliant_checks = len([c for c in all_checks if c.status == "compliant"])
        compliance_score = (compliant_checks / total_checks * 100) if total_checks > 0 else 100
        
        return SecurityResponse(
            success=True,
            data={
                "compliance_checks": [
                    {
                        "check_id": c.check_id,
                        "standard": c.standard.value,
                        "control_id": c.control_id,
                        "title": c.title,
                        "status": c.status,
                        "last_assessed": c.last_assessed
                    } for c in all_checks
                ],
                "summary": {
                    "total_checks": total_checks,
                    "compliant": compliant_checks,
                    "non_compliant": len([c for c in all_checks if c.status == "non_compliant"]),
                    "partial": len([c for c in all_checks if c.status == "partial"]),
                    "not_applicable": len([c for c in all_checks if c.status == "not_applicable"]),
                    "compliance_score": compliance_score
                },
                "checked_at": datetime.now(timezone.utc).isoformat()
            },
            message="Compliance check completed successfully"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to perform compliance check: {str(e)}"
        )


@router.post("/certification/report", response_model=SecurityResponse)
async def generate_certification_report(
    request: CertificationReportRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Generate security certification report."""
    try:
        # Get audit results (mock for demonstration)
        target_systems = ["https://api.mams.example.com", "https://app.mams.example.com"]
        compliance_standards = [ComplianceStandard.ISO27001, ComplianceStandard.SOC2_TYPE2]
        
        audit_results = await security_service.perform_comprehensive_audit(
            target_systems=target_systems,
            compliance_standards=compliance_standards
        )
        
        # Generate certification report
        report = await security_service.generate_certification_report(
            audit_results=audit_results,
            report_format=request.report_format
        )
        
        return SecurityResponse(
            success=True,
            data=report,
            message="Certification report generated successfully"
        )
        
    except SecurityCertificationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate certification report: {str(e)}"
        )


@router.get("/findings", response_model=SecurityResponse)
async def get_security_findings(
    severity: Optional[str] = Query(None, description="Filter by severity level"),
    category: Optional[str] = Query(None, description="Filter by vulnerability category"),
    status: Optional[str] = Query(None, description="Filter by finding status"),
    limit: int = Query(50, ge=1, le=200, description="Number of findings to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get security findings with filtering and pagination."""
    try:
        # Perform a quick audit to get findings
        target_systems = ["https://api.mams.example.com"]
        audit_results = await security_service.perform_comprehensive_audit(target_systems)
        
        findings = audit_results.get("findings", [])
        
        # Apply filters
        if severity:
            findings = [f for f in findings if f.get("severity") == severity.lower()]
        if category:
            findings = [f for f in findings if f.get("category") == category.lower()]
        if status:
            findings = [f for f in findings if f.get("status") == status.lower()]
        
        # Apply pagination
        total_findings = len(findings)
        paginated_findings = findings[offset:offset + limit]
        
        return SecurityResponse(
            success=True,
            data={
                "findings": paginated_findings,
                "pagination": {
                    "total": total_findings,
                    "limit": limit,
                    "offset": offset,
                    "has_more": offset + limit < total_findings
                },
                "filters_applied": {
                    "severity": severity,
                    "category": category,
                    "status": status
                }
            },
            message="Security findings retrieved successfully"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get security findings: {str(e)}"
        )


@router.get("/metrics", response_model=SecurityResponse)
async def get_security_metrics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get security metrics and KPIs."""
    try:
        # Calculate security metrics
        metrics = await security_service._calculate_security_metrics()
        
        return SecurityResponse(
            success=True,
            data={
                "security_metrics": {
                    "total_findings": metrics.total_findings,
                    "critical_findings": metrics.critical_findings,
                    "high_findings": metrics.high_findings,
                    "medium_findings": metrics.medium_findings,
                    "low_findings": metrics.low_findings,
                    "info_findings": metrics.info_findings,
                    "compliance_score": metrics.compliance_score,
                    "security_posture_score": metrics.security_posture_score,
                    "coverage_percentage": metrics.coverage_percentage,
                    "last_assessment": metrics.last_assessment
                },
                "trend_data": {
                    "findings_over_time": [],  # Would contain historical data
                    "compliance_trend": [],    # Would contain compliance score history
                    "remediation_rate": 85.5   # Percentage of findings remediated
                },
                "risk_summary": {
                    "high_risk_assets": 2,
                    "medium_risk_assets": 5,
                    "low_risk_assets": 15,
                    "total_assets": 22
                }
            },
            message="Security metrics retrieved successfully"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get security metrics: {str(e)}"
        )


@router.get("/standards", response_model=SecurityResponse)
async def get_supported_compliance_standards(
    current_user: User = Depends(get_current_user)
):
    """Get list of supported compliance standards."""
    try:
        standards = [
            {
                "id": "iso27001",
                "name": "ISO 27001",
                "description": "Information Security Management System",
                "version": "2013",
                "controls": 114
            },
            {
                "id": "soc2_type2",
                "name": "SOC 2 Type II",
                "description": "Service Organization Control 2",
                "version": "2017",
                "controls": 64
            },
            {
                "id": "gdpr",
                "name": "GDPR",
                "description": "General Data Protection Regulation",
                "version": "2018",
                "controls": 47
            },
            {
                "id": "pci_dss",
                "name": "PCI DSS",
                "description": "Payment Card Industry Data Security Standard",
                "version": "4.0",
                "controls": 12
            },
            {
                "id": "nist_csf",
                "name": "NIST Cybersecurity Framework",
                "description": "NIST Cybersecurity Framework",
                "version": "1.1",
                "controls": 108
            }
        ]
        
        return SecurityResponse(
            success=True,
            data={
                "supported_standards": standards,
                "total_standards": len(standards)
            },
            message="Supported compliance standards retrieved successfully"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get compliance standards: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """Health check endpoint for security certification service."""
    return {
        "status": "healthy",
        "service": "security-certification",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0"
    }


async def _perform_audit_background(
    audit_id: str,
    target_systems: List[str],
    compliance_standards: List[ComplianceStandard],
    user_id: uuid.UUID
):
    """Background task to perform security audit."""
    try:
        # This would perform the actual audit and store results
        # For now, we'll simulate the audit completion
        audit_results = await security_service.perform_comprehensive_audit(
            target_systems=target_systems,
            compliance_standards=compliance_standards
        )
        
        # Store results in database/cache for later retrieval
        # Implementation would depend on the specific storage mechanism
        
    except Exception as e:
        # Log error and update audit status
        print(f"Background audit {audit_id} failed: {e}")