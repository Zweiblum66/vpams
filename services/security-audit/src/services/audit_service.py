"""
Audit Service - Business logic for security audits
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
import structlog
import uuid

from ..models.database import (
    AuditResult as DBAuditResult, ScanResult as DBScanResult, 
    Finding as DBFinding, ComplianceResult as DBComplianceResult,
    SecurityMetric, ScanTemplate
)
from ..models.schemas import (
    AuditRequest, AuditResult, ScanResult, Finding, ComplianceResult,
    ScanType, SeverityLevel, ComplianceStandard
)

logger = structlog.get_logger()


class AuditService:
    """Service for managing audit operations"""
    
    async def create_audit_record(
        self, 
        audit_id: str, 
        request: AuditRequest, 
        db: AsyncSession
    ) -> DBAuditResult:
        """Create audit record in database"""
        try:
            audit_record = DBAuditResult(
                id=uuid.UUID(audit_id),
                target=request.target,
                status="pending",
                requested_scans=[scan.value for scan in request.scans],
                requested_standards=[std.value for std in (request.compliance_standards or [])],
                options=request.options
            )
            
            db.add(audit_record)
            await db.commit()
            await db.refresh(audit_record)
            
            logger.info("Audit record created", audit_id=audit_id)
            return audit_record
            
        except Exception as e:
            await db.rollback()
            logger.error("Failed to create audit record", audit_id=audit_id, error=str(e))
            raise
    
    async def update_audit_status(
        self, 
        audit_id: str, 
        status: str, 
        db: AsyncSession,
        error_message: Optional[str] = None
    ) -> None:
        """Update audit status in database"""
        try:
            stmt = select(DBAuditResult).where(DBAuditResult.id == uuid.UUID(audit_id))
            result = await db.execute(stmt)
            audit_record = result.scalar_one_or_none()
            
            if audit_record:
                audit_record.status = status
                if error_message:
                    audit_record.error_message = error_message
                if status == "completed":
                    audit_record.completed_at = datetime.utcnow()
                    if audit_record.started_at:
                        audit_record.duration_seconds = (
                            audit_record.completed_at - audit_record.started_at
                        ).total_seconds()
                
                await db.commit()
                logger.info("Audit status updated", audit_id=audit_id, status=status)
            
        except Exception as e:
            await db.rollback()
            logger.error("Failed to update audit status", audit_id=audit_id, error=str(e))
            raise
    
    async def save_scan_result(
        self, 
        scan_result: ScanResult, 
        audit_id: Optional[str],
        db: AsyncSession
    ) -> DBScanResult:
        """Save scan result to database"""
        try:
            # Create scan result record
            db_scan = DBScanResult(
                id=uuid.UUID(scan_result.id) if scan_result.id else uuid.uuid4(),
                scan_type=scan_result.scan_type.value,
                target=scan_result.target,
                status=scan_result.status.value,
                started_at=scan_result.started_at,
                completed_at=scan_result.completed_at,
                duration_seconds=scan_result.duration_seconds,
                findings_count=scan_result.summary.total,
                critical_count=scan_result.summary.critical,
                high_count=scan_result.summary.high,
                medium_count=scan_result.summary.medium,
                low_count=scan_result.summary.low,
                info_count=scan_result.summary.info,
                scanner_version=scan_result.scanner_version,
                options=scan_result.options,
                error_message=scan_result.error_message
            )
            
            db.add(db_scan)
            
            # Save findings
            for finding in scan_result.findings:
                db_finding = DBFinding(
                    scan_result_id=db_scan.id,
                    type=finding.type,
                    scanner=finding.scanner,
                    severity=finding.severity.value,
                    confidence=finding.confidence,
                    title=finding.title,
                    description=finding.description,
                    file_path=finding.file,
                    line_number=finding.line,
                    url=finding.url,
                    cve=finding.cve,
                    cvss_score=finding.cvss_score,
                    cwe_id=finding.cwe_id,
                    owasp_categories=finding.owasp,
                    solution=finding.solution,
                    references=finding.references
                )
                db.add(db_finding)
            
            await db.commit()
            await db.refresh(db_scan)
            
            logger.info("Scan result saved", scan_id=str(db_scan.id), findings=len(scan_result.findings))
            return db_scan
            
        except Exception as e:
            await db.rollback()
            logger.error("Failed to save scan result", error=str(e))
            raise
    
    async def save_compliance_result(
        self, 
        compliance_result: ComplianceResult, 
        audit_id: Optional[str],
        db: AsyncSession
    ) -> DBComplianceResult:
        """Save compliance result to database"""
        try:
            # Serialize controls data
            controls_data = {
                "controls": [
                    {
                        "id": control.id,
                        "name": control.name,
                        "score": control.score,
                        "requirements": [
                            {
                                "id": req.id,
                                "description": req.description,
                                "status": req.status,
                                "evidence": req.evidence,
                                "severity": req.severity.value if req.severity else None
                            }
                            for req in control.requirements
                        ]
                    }
                    for control in compliance_result.controls
                ]
            }
            
            db_compliance = DBComplianceResult(
                id=uuid.UUID(compliance_result.id) if compliance_result.id else uuid.uuid4(),
                standard=compliance_result.standard.value,
                target=compliance_result.target,
                overall_score=compliance_result.score,
                status=compliance_result.status,
                controls_data=controls_data,
                recommendations=compliance_result.recommendations,
                timestamp=compliance_result.timestamp
            )
            
            db.add(db_compliance)
            await db.commit()
            await db.refresh(db_compliance)
            
            logger.info("Compliance result saved", 
                       compliance_id=str(db_compliance.id),
                       standard=compliance_result.standard.value,
                       score=compliance_result.score)
            return db_compliance
            
        except Exception as e:
            await db.rollback()
            logger.error("Failed to save compliance result", error=str(e))
            raise
    
    async def list_audits(
        self, 
        db: AsyncSession,
        page: int = 1,
        limit: int = 20,
        target: Optional[str] = None,
        status: Optional[str] = None
    ) -> Tuple[List[AuditResult], int]:
        """List audit results with pagination"""
        try:
            # Build query
            query = select(DBAuditResult)
            
            # Apply filters
            filters = []
            if target:
                filters.append(DBAuditResult.target.ilike(f"%{target}%"))
            if status:
                filters.append(DBAuditResult.status == status)
            
            if filters:
                query = query.where(and_(*filters))
            
            # Get total count
            count_query = select(func.count()).select_from(query.subquery())
            count_result = await db.execute(count_query)
            total = count_result.scalar()
            
            # Apply pagination and ordering
            query = query.order_by(DBAuditResult.created_at.desc())
            query = query.offset((page - 1) * limit).limit(limit)
            
            # Load with relationships
            query = query.options(
                selectinload(DBAuditResult.audit_scans).selectinload(AuditScan.scan_result),
                selectinload(DBAuditResult.audit_compliance).selectinload(AuditCompliance.compliance_result)
            )
            
            result = await db.execute(query)
            audit_records = result.scalars().all()
            
            # Convert to response models
            audits = []
            for record in audit_records:
                audit = await self._convert_audit_record(record)
                audits.append(audit)
            
            return audits, total
            
        except Exception as e:
            logger.error("Failed to list audits", error=str(e))
            raise
    
    async def list_scans(
        self, 
        db: AsyncSession,
        page: int = 1,
        limit: int = 20,
        scan_type: Optional[ScanType] = None,
        severity: Optional[str] = None
    ) -> Tuple[List[ScanResult], int]:
        """List scan results with pagination"""
        try:
            # Build query
            query = select(DBScanResult)
            
            # Apply filters
            filters = []
            if scan_type:
                filters.append(DBScanResult.scan_type == scan_type.value)
            if severity:
                # Filter by minimum severity level
                severity_order = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}
                min_severity_value = severity_order.get(severity, 0)
                if min_severity_value >= 4:
                    filters.append(DBScanResult.critical_count > 0)
                elif min_severity_value >= 3:
                    filters.append(or_(DBScanResult.critical_count > 0, DBScanResult.high_count > 0))
                elif min_severity_value >= 2:
                    filters.append(or_(
                        DBScanResult.critical_count > 0,
                        DBScanResult.high_count > 0,
                        DBScanResult.medium_count > 0
                    ))
            
            if filters:
                query = query.where(and_(*filters))
            
            # Get total count
            count_query = select(func.count()).select_from(query.subquery())
            count_result = await db.execute(count_query)
            total = count_result.scalar()
            
            # Apply pagination and ordering
            query = query.order_by(DBScanResult.created_at.desc())
            query = query.offset((page - 1) * limit).limit(limit)
            
            # Load with findings
            query = query.options(selectinload(DBScanResult.findings))
            
            result = await db.execute(query)
            scan_records = result.scalars().all()
            
            # Convert to response models
            scans = []
            for record in scan_records:
                scan = await self._convert_scan_record(record)
                scans.append(scan)
            
            return scans, total
            
        except Exception as e:
            logger.error("Failed to list scans", error=str(e))
            raise
    
    async def list_compliance_results(
        self, 
        db: AsyncSession,
        page: int = 1,
        limit: int = 20,
        standard: Optional[ComplianceStandard] = None,
        min_score: Optional[float] = None
    ) -> List[ComplianceResult]:
        """List compliance results with pagination"""
        try:
            # Build query
            query = select(DBComplianceResult)
            
            # Apply filters
            filters = []
            if standard:
                filters.append(DBComplianceResult.standard == standard.value)
            if min_score is not None:
                filters.append(DBComplianceResult.overall_score >= min_score)
            
            if filters:
                query = query.where(and_(*filters))
            
            # Apply pagination and ordering
            query = query.order_by(DBComplianceResult.created_at.desc())
            query = query.offset((page - 1) * limit).limit(limit)
            
            result = await db.execute(query)
            compliance_records = result.scalars().all()
            
            # Convert to response models
            results = []
            for record in compliance_records:
                compliance = await self._convert_compliance_record(record)
                results.append(compliance)
            
            return results
            
        except Exception as e:
            logger.error("Failed to list compliance results", error=str(e))
            raise
    
    async def get_audit_analytics(self, db: AsyncSession, days: int = 30) -> Dict[str, Any]:
        """Get audit analytics and metrics"""
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # Basic audit statistics
            audit_stats_query = select(
                func.count(DBAuditResult.id).label("total_audits"),
                func.count(DBAuditResult.id).filter(DBAuditResult.status == "completed").label("completed_audits"),
                func.count(DBAuditResult.id).filter(DBAuditResult.status == "failed").label("failed_audits"),
                func.avg(DBAuditResult.duration_seconds).label("avg_duration")
            ).where(DBAuditResult.created_at >= start_date)
            
            audit_stats_result = await db.execute(audit_stats_query)
            audit_stats = audit_stats_result.first()
            
            # Scan statistics
            scan_stats_query = select(
                func.count(DBScanResult.id).label("total_scans"),
                func.sum(DBScanResult.findings_count).label("total_findings"),
                func.sum(DBScanResult.critical_count).label("critical_findings"),
                func.sum(DBScanResult.high_count).label("high_findings"),
                func.avg(DBScanResult.duration_seconds).label("avg_scan_duration")
            ).where(DBScanResult.created_at >= start_date)
            
            scan_stats_result = await db.execute(scan_stats_query)
            scan_stats = scan_stats_result.first()
            
            # Top vulnerabilities
            top_vulns_query = select(
                DBFinding.title,
                func.count(DBFinding.id).label("count")
            ).join(DBScanResult).where(
                DBScanResult.created_at >= start_date
            ).group_by(DBFinding.title).order_by(
                func.count(DBFinding.id).desc()
            ).limit(10)
            
            top_vulns_result = await db.execute(top_vulns_query)
            top_vulnerabilities = [
                {"title": row.title, "count": row.count}
                for row in top_vulns_result
            ]
            
            # Compliance scores
            compliance_scores_query = select(
                DBComplianceResult.standard,
                func.avg(DBComplianceResult.overall_score).label("avg_score")
            ).where(
                DBComplianceResult.created_at >= start_date
            ).group_by(DBComplianceResult.standard)
            
            compliance_scores_result = await db.execute(compliance_scores_query)
            compliance_scores = {
                row.standard: float(row.avg_score)
                for row in compliance_scores_result
            }
            
            return {
                "period_days": days,
                "audit_statistics": {
                    "total_audits": audit_stats.total_audits or 0,
                    "completed_audits": audit_stats.completed_audits or 0,
                    "failed_audits": audit_stats.failed_audits or 0,
                    "success_rate": (
                        (audit_stats.completed_audits or 0) / max(audit_stats.total_audits or 1, 1)
                    ) * 100,
                    "average_duration_seconds": float(audit_stats.avg_duration or 0)
                },
                "scan_statistics": {
                    "total_scans": scan_stats.total_scans or 0,
                    "total_findings": scan_stats.total_findings or 0,
                    "critical_findings": scan_stats.critical_findings or 0,
                    "high_findings": scan_stats.high_findings or 0,
                    "average_scan_duration_seconds": float(scan_stats.avg_scan_duration or 0)
                },
                "top_vulnerabilities": top_vulnerabilities,
                "compliance_scores": compliance_scores,
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Failed to get audit analytics", error=str(e))
            raise
    
    async def export_findings(
        self, 
        db: AsyncSession,
        format: str = "json",
        scan_ids: Optional[List[str]] = None,
        severity: Optional[str] = None
    ) -> Any:
        """Export security findings"""
        try:
            # Build query
            query = select(DBFinding).join(DBScanResult)
            
            # Apply filters
            filters = []
            if scan_ids:
                filters.append(DBScanResult.id.in_([uuid.UUID(id) for id in scan_ids]))
            if severity:
                severity_order = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}
                min_severity_value = severity_order.get(severity, 0)
                if min_severity_value > 0:
                    valid_severities = [k for k, v in severity_order.items() if v >= min_severity_value]
                    filters.append(DBFinding.severity.in_(valid_severities))
            
            if filters:
                query = query.where(and_(*filters))
            
            query = query.order_by(DBFinding.created_at.desc())
            
            result = await db.execute(query)
            findings = result.scalars().all()
            
            # Convert to export format
            if format == "json":
                return [
                    {
                        "id": str(finding.id),
                        "type": finding.type,
                        "scanner": finding.scanner,
                        "severity": finding.severity,
                        "confidence": finding.confidence,
                        "title": finding.title,
                        "description": finding.description,
                        "file_path": finding.file_path,
                        "line_number": finding.line_number,
                        "url": finding.url,
                        "cve": finding.cve,
                        "cvss_score": finding.cvss_score,
                        "cwe_id": finding.cwe_id,
                        "solution": finding.solution,
                        "created_at": finding.created_at.isoformat()
                    }
                    for finding in findings
                ]
            elif format == "csv":
                # Return CSV data as string
                import csv
                import io
                
                output = io.StringIO()
                writer = csv.writer(output)
                
                # Write header
                writer.writerow([
                    "ID", "Type", "Scanner", "Severity", "Confidence", "Title",
                    "Description", "File", "Line", "URL", "CVE", "CVSS Score",
                    "CWE ID", "Solution", "Created At"
                ])
                
                # Write data
                for finding in findings:
                    writer.writerow([
                        str(finding.id), finding.type, finding.scanner,
                        finding.severity, finding.confidence, finding.title,
                        finding.description, finding.file_path, finding.line_number,
                        finding.url, finding.cve, finding.cvss_score,
                        finding.cwe_id, finding.solution, finding.created_at.isoformat()
                    ])
                
                return output.getvalue()
            
            else:
                raise ValueError(f"Unsupported export format: {format}")
            
        except Exception as e:
            logger.error("Failed to export findings", error=str(e))
            raise
    
    async def _convert_audit_record(self, record: DBAuditResult) -> AuditResult:
        """Convert database audit record to response model"""
        # This would need to be implemented based on the relationships
        # For now, return a simplified version
        from ..models.schemas import AuditSummary
        
        return AuditResult(
            id=str(record.id),
            target=record.target,
            started_at=record.started_at,
            completed_at=record.completed_at,
            duration_seconds=record.duration_seconds,
            scan_results=[],  # Would need to populate from relationships
            compliance_results=[],  # Would need to populate from relationships
            summary=AuditSummary(
                total_scans=record.total_scans,
                successful_scans=record.successful_scans,
                failed_scans=record.failed_scans,
                total_findings=record.total_findings,
                critical_findings=record.critical_findings,
                high_findings=record.high_findings,
                compliance_score=record.compliance_score
            ),
            status=record.status,
            error_message=record.error_message
        )
    
    async def _convert_scan_record(self, record: DBScanResult) -> ScanResult:
        """Convert database scan record to response model"""
        from ..models.schemas import ScanSummary
        
        # Convert findings
        findings = []
        for db_finding in record.findings:
            finding = Finding(
                id=str(db_finding.id),
                type=db_finding.type,
                scanner=db_finding.scanner,
                severity=db_finding.severity,
                confidence=db_finding.confidence,
                title=db_finding.title,
                description=db_finding.description,
                file=db_finding.file_path,
                line=db_finding.line_number,
                url=db_finding.url,
                cve=db_finding.cve,
                cvss_score=db_finding.cvss_score,
                owasp=db_finding.owasp_categories,
                cwe_id=db_finding.cwe_id,
                solution=db_finding.solution,
                references=db_finding.references
            )
            findings.append(finding)
        
        return ScanResult(
            id=str(record.id),
            scan_type=record.scan_type,
            target=record.target,
            status=record.status,
            started_at=record.started_at,
            completed_at=record.completed_at,
            duration_seconds=record.duration_seconds,
            findings=findings,
            summary=ScanSummary(
                total=record.findings_count,
                critical=record.critical_count,
                high=record.high_count,
                medium=record.medium_count,
                low=record.low_count,
                info=record.info_count
            ),
            scanner_version=record.scanner_version,
            options=record.options,
            error_message=record.error_message
        )
    
    async def _convert_compliance_record(self, record: DBComplianceResult) -> ComplianceResult:
        """Convert database compliance record to response model"""
        from ..models.schemas import ComplianceControl, ComplianceRequirement
        
        # Convert controls data
        controls = []
        for control_data in record.controls_data.get("controls", []):
            requirements = []
            for req_data in control_data.get("requirements", []):
                requirement = ComplianceRequirement(
                    id=req_data["id"],
                    description=req_data["description"],
                    status=req_data["status"],
                    evidence=req_data.get("evidence"),
                    severity=req_data.get("severity")
                )
                requirements.append(requirement)
            
            control = ComplianceControl(
                id=control_data["id"],
                name=control_data["name"],
                requirements=requirements,
                score=control_data["score"]
            )
            controls.append(control)
        
        return ComplianceResult(
            id=str(record.id),
            standard=record.standard,
            target=record.target,
            timestamp=record.timestamp,
            controls=controls,
            score=record.overall_score,
            status=record.status,
            recommendations=record.recommendations
        )