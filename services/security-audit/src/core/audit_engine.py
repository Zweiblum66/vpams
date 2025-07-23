"""
Security Audit Engine - Orchestrates comprehensive security audits
"""

import asyncio
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import structlog
from pathlib import Path

from .config import Settings
from .security_scanner import CodeScanner, DependencyScanner, WebScanner
from .compliance_checker import ISO27001Checker, GDPRChecker, SOC2Checker
from ..models.schemas import (
    ScanType, ScanStatus, ComplianceStandard, AuditRequest, AuditResult,
    ScanResult, ComplianceResult, Finding, ScanSummary, AuditSummary
)

logger = structlog.get_logger()


class AuditEngine:
    """Orchestrates comprehensive security audits"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.active_audits: Dict[str, Dict[str, Any]] = {}
        
        # Initialize scanners
        self.scanners = {
            ScanType.CODE: CodeScanner(settings),
            ScanType.DEPENDENCY: DependencyScanner(settings),
            ScanType.WEB: WebScanner(settings)
        }
        
        # Initialize compliance checkers
        self.compliance_checkers = {
            ComplianceStandard.ISO27001: ISO27001Checker(settings),
            ComplianceStandard.GDPR: GDPRChecker(settings),
            ComplianceStandard.SOC2: SOC2Checker(settings)
        }
    
    async def start_audit(self, request: AuditRequest) -> str:
        """Start a comprehensive security audit"""
        audit_id = str(uuid.uuid4())
        
        audit_data = {
            "id": audit_id,
            "target": request.target,
            "scans": request.scans,
            "compliance_standards": request.compliance_standards or [],
            "options": request.options,
            "status": ScanStatus.PENDING,
            "started_at": datetime.utcnow(),
            "scan_results": {},
            "compliance_results": {},
            "error_messages": []
        }
        
        self.active_audits[audit_id] = audit_data
        
        # Start audit in background
        asyncio.create_task(self._execute_audit(audit_id))
        
        logger.info("Security audit started", audit_id=audit_id, target=request.target)
        return audit_id
    
    async def get_audit_status(self, audit_id: str) -> Optional[Dict[str, Any]]:
        """Get audit execution status"""
        return self.active_audits.get(audit_id)
    
    async def get_audit_result(self, audit_id: str) -> Optional[AuditResult]:
        """Get complete audit result"""
        audit_data = self.active_audits.get(audit_id)
        if not audit_data:
            return None
        
        # Build scan results
        scan_results = []
        for scan_type, result_data in audit_data["scan_results"].items():
            scan_results.append(self._build_scan_result(scan_type, result_data))
        
        # Build compliance results
        compliance_results = []
        for standard, result_data in audit_data["compliance_results"].items():
            compliance_results.append(self._build_compliance_result(standard, result_data))
        
        # Calculate summary
        summary = self._calculate_audit_summary(scan_results, compliance_results)
        
        return AuditResult(
            id=audit_id,
            target=audit_data["target"],
            started_at=audit_data["started_at"],
            completed_at=audit_data.get("completed_at"),
            duration_seconds=audit_data.get("duration_seconds"),
            scan_results=scan_results,
            compliance_results=compliance_results,
            summary=summary,
            status=audit_data["status"],
            error_message="; ".join(audit_data["error_messages"]) if audit_data["error_messages"] else None
        )
    
    async def _execute_audit(self, audit_id: str) -> None:
        """Execute the audit asynchronously"""
        audit_data = self.active_audits[audit_id]
        
        try:
            audit_data["status"] = ScanStatus.RUNNING
            logger.info("Executing security audit", audit_id=audit_id)
            
            # Execute scans concurrently
            scan_tasks = []
            for scan_type in audit_data["scans"]:
                if scan_type in self.scanners:
                    task = asyncio.create_task(
                        self._execute_scan(audit_id, scan_type, audit_data["target"])
                    )
                    scan_tasks.append(task)
            
            # Execute compliance checks concurrently
            compliance_tasks = []
            for standard in audit_data["compliance_standards"]:
                if standard in self.compliance_checkers:
                    task = asyncio.create_task(
                        self._execute_compliance_check(audit_id, standard, audit_data["target"])
                    )
                    compliance_tasks.append(task)
            
            # Wait for all scans and compliance checks
            if scan_tasks:
                await asyncio.gather(*scan_tasks, return_exceptions=True)
            
            if compliance_tasks:
                await asyncio.gather(*compliance_tasks, return_exceptions=True)
            
            # Mark as completed
            audit_data["completed_at"] = datetime.utcnow()
            audit_data["duration_seconds"] = (
                audit_data["completed_at"] - audit_data["started_at"]
            ).total_seconds()
            audit_data["status"] = ScanStatus.COMPLETED
            
            logger.info("Security audit completed", audit_id=audit_id)
            
        except Exception as e:
            logger.error("Audit execution failed", audit_id=audit_id, error=str(e))
            audit_data["status"] = ScanStatus.FAILED
            audit_data["error_messages"].append(f"Audit execution failed: {str(e)}")
            audit_data["completed_at"] = datetime.utcnow()
            audit_data["duration_seconds"] = (
                audit_data["completed_at"] - audit_data["started_at"]
            ).total_seconds()
    
    async def _execute_scan(self, audit_id: str, scan_type: ScanType, target: str) -> None:
        """Execute a specific security scan"""
        audit_data = self.active_audits[audit_id]
        
        try:
            logger.info("Starting security scan", audit_id=audit_id, scan_type=scan_type)
            
            scanner = self.scanners[scan_type]
            result = await asyncio.wait_for(
                scanner.scan(target),
                timeout=self.settings.scan_timeout_seconds
            )
            
            audit_data["scan_results"][scan_type] = result
            logger.info("Security scan completed", audit_id=audit_id, scan_type=scan_type, 
                       findings=len(result.get("findings", [])))
            
        except asyncio.TimeoutError:
            error_msg = f"Scan {scan_type} timed out"
            logger.error(error_msg, audit_id=audit_id)
            audit_data["error_messages"].append(error_msg)
            
        except Exception as e:
            error_msg = f"Scan {scan_type} failed: {str(e)}"
            logger.error(error_msg, audit_id=audit_id)
            audit_data["error_messages"].append(error_msg)
    
    async def _execute_compliance_check(self, audit_id: str, standard: ComplianceStandard, target: str) -> None:
        """Execute a compliance check"""
        audit_data = self.active_audits[audit_id]
        
        try:
            logger.info("Starting compliance check", audit_id=audit_id, standard=standard)
            
            checker = self.compliance_checkers[standard]
            result = await asyncio.wait_for(
                checker.check(target),
                timeout=self.settings.scan_timeout_seconds
            )
            
            audit_data["compliance_results"][standard] = result
            logger.info("Compliance check completed", audit_id=audit_id, standard=standard,
                       score=result.get("score", 0))
            
        except asyncio.TimeoutError:
            error_msg = f"Compliance check {standard} timed out"
            logger.error(error_msg, audit_id=audit_id)
            audit_data["error_messages"].append(error_msg)
            
        except Exception as e:
            error_msg = f"Compliance check {standard} failed: {str(e)}"
            logger.error(error_msg, audit_id=audit_id)
            audit_data["error_messages"].append(error_msg)
    
    def _build_scan_result(self, scan_type: str, result_data: Dict[str, Any]) -> ScanResult:
        """Build ScanResult from raw scan data"""
        findings = []
        for finding_data in result_data.get("findings", []):
            finding = Finding(
                type=finding_data.get("type", ""),
                scanner=finding_data.get("scanner", ""),
                severity=finding_data.get("severity", "low"),
                confidence=finding_data.get("confidence", ""),
                title=finding_data.get("title", ""),
                description=finding_data.get("description", ""),
                file=finding_data.get("file"),
                line=finding_data.get("line"),
                url=finding_data.get("url"),
                cve=finding_data.get("cve"),
                cvss_score=finding_data.get("cvss_score"),
                owasp=finding_data.get("owasp"),
                cwe_id=finding_data.get("cwe_id"),
                solution=finding_data.get("solution"),
                references=finding_data.get("references")
            )
            findings.append(finding)
        
        summary_data = result_data.get("summary", {})
        summary = ScanSummary(
            total=summary_data.get("total", 0),
            critical=summary_data.get("critical", 0),
            high=summary_data.get("high", 0),
            medium=summary_data.get("medium", 0),
            low=summary_data.get("low", 0),
            info=summary_data.get("info", 0)
        )
        
        return ScanResult(
            id=str(uuid.uuid4()),
            scan_type=scan_type,
            target=result_data.get("target", ""),
            status=ScanStatus.COMPLETED,
            started_at=datetime.fromisoformat(result_data.get("timestamp", datetime.utcnow().isoformat())),
            completed_at=datetime.fromisoformat(result_data.get("timestamp", datetime.utcnow().isoformat())),
            findings=findings,
            summary=summary,
            scanner_version=result_data.get("scanner_version")
        )
    
    def _build_compliance_result(self, standard: str, result_data: Dict[str, Any]) -> ComplianceResult:
        """Build ComplianceResult from raw compliance data"""
        from ..models.schemas import ComplianceControl, ComplianceRequirement
        
        controls = []
        for control_data in result_data.get("controls", []):
            requirements = []
            for req_data in control_data.get("requirements", []):
                requirement = ComplianceRequirement(
                    id=req_data.get("id", ""),
                    description=req_data.get("description", ""),
                    status=req_data.get("status", "fail"),
                    evidence=req_data.get("evidence")
                )
                requirements.append(requirement)
            
            control = ComplianceControl(
                id=control_data.get("id", ""),
                name=control_data.get("name", ""),
                requirements=requirements,
                score=control_data.get("score", 0)
            )
            controls.append(control)
        
        return ComplianceResult(
            id=str(uuid.uuid4()),
            standard=standard,
            target=result_data.get("target", ""),
            timestamp=datetime.fromisoformat(result_data.get("timestamp", datetime.utcnow().isoformat())),
            controls=controls,
            score=result_data.get("score", 0),
            status=result_data.get("status", "non_compliant")
        )
    
    def _calculate_audit_summary(self, scan_results: List[ScanResult], 
                                compliance_results: List[ComplianceResult]) -> AuditSummary:
        """Calculate audit summary statistics"""
        total_scans = len(scan_results)
        successful_scans = sum(1 for scan in scan_results if scan.status == ScanStatus.COMPLETED)
        failed_scans = total_scans - successful_scans
        
        total_findings = sum(scan.summary.total for scan in scan_results)
        critical_findings = sum(scan.summary.critical for scan in scan_results)
        high_findings = sum(scan.summary.high for scan in scan_results)
        
        compliance_score = None
        if compliance_results:
            compliance_score = sum(result.score for result in compliance_results) / len(compliance_results)
        
        return AuditSummary(
            total_scans=total_scans,
            successful_scans=successful_scans,
            failed_scans=failed_scans,
            total_findings=total_findings,
            critical_findings=critical_findings,
            high_findings=high_findings,
            compliance_score=compliance_score
        )
    
    async def cleanup_old_audits(self, max_age_hours: int = 24) -> int:
        """Clean up old audit results from memory"""
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        cleaned_count = 0
        
        audit_ids_to_remove = []
        for audit_id, audit_data in self.active_audits.items():
            if audit_data["started_at"] < cutoff_time:
                audit_ids_to_remove.append(audit_id)
        
        for audit_id in audit_ids_to_remove:
            del self.active_audits[audit_id]
            cleaned_count += 1
        
        if cleaned_count > 0:
            logger.info("Cleaned up old audit results", count=cleaned_count)
        
        return cleaned_count
    
    def get_active_audit_count(self) -> int:
        """Get number of active audits"""
        return len([
            audit for audit in self.active_audits.values() 
            if audit["status"] in [ScanStatus.PENDING, ScanStatus.RUNNING]
        ])
    
    async def cancel_audit(self, audit_id: str) -> bool:
        """Cancel a running audit"""
        audit_data = self.active_audits.get(audit_id)
        if not audit_data:
            return False
        
        if audit_data["status"] in [ScanStatus.PENDING, ScanStatus.RUNNING]:
            audit_data["status"] = ScanStatus.FAILED
            audit_data["completed_at"] = datetime.utcnow()
            audit_data["duration_seconds"] = (
                audit_data["completed_at"] - audit_data["started_at"]
            ).total_seconds()
            audit_data["error_messages"].append("Audit cancelled by user")
            
            logger.info("Security audit cancelled", audit_id=audit_id)
            return True
        
        return False