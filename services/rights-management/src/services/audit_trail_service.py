"""
Rights Management Service - Audit Trail Service
"""

import asyncio
import json
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, asc, update
from sqlalchemy.orm import selectinload
import uuid
import hashlib

from ..models.schemas import User
from ..db.models import License, UsageRecord, ComplianceAlert, AuditLog
from ..core.config import settings
from ..core.exceptions import ValidationError
from ..core.logger import get_logger

logger = get_logger(__name__)


class AuditTrailService:
    """Service for managing audit trails and compliance history"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.event_types = {
            # License events
            "license.created": "License Created",
            "license.updated": "License Updated",
            "license.deleted": "License Deleted",
            "license.activated": "License Activated",
            "license.suspended": "License Suspended",
            "license.expired": "License Expired",
            "license.renewed": "License Renewed",
            
            # Usage events
            "usage.recorded": "Usage Recorded",
            "usage.limit_exceeded": "Usage Limit Exceeded",
            "usage.quota_warning": "Usage Quota Warning",
            "usage.denied": "Usage Denied",
            
            # Compliance events
            "compliance.check_performed": "Compliance Check Performed",
            "compliance.violation_detected": "Compliance Violation Detected",
            "compliance.alert_created": "Compliance Alert Created",
            "compliance.alert_resolved": "Compliance Alert Resolved",
            
            # Rights events
            "rights.party_added": "Rights Party Added",
            "rights.party_removed": "Rights Party Removed",
            "rights.party_updated": "Rights Party Updated",
            "rights.ownership_transferred": "Rights Ownership Transferred",
            
            # Restriction events
            "restriction.applied": "Restriction Applied",
            "restriction.violated": "Restriction Violated",
            "restriction.removed": "Restriction Removed",
            "restriction.geo_block": "Geographic Access Blocked",
            
            # System events
            "system.configuration_changed": "System Configuration Changed",
            "system.integration_activated": "Integration Activated",
            "system.blockchain_sync": "Blockchain Synchronized",
            "system.report_generated": "Report Generated"
        }
    
    async def create_audit_log(
        self,
        event_type: str,
        entity_type: str,
        entity_id: str,
        user: User,
        details: Optional[Dict[str, Any]] = None,
        severity: str = "info",
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> AuditLog:
        """Create a new audit log entry"""
        try:
            logger.info(f"Creating audit log for {event_type} on {entity_type} {entity_id}")
            
            # Validate event type
            if event_type not in self.event_types:
                logger.warning(f"Unknown event type: {event_type}")
            
            # Create audit log entry
            audit_log = AuditLog(
                id=str(uuid.uuid4()),
                event_type=event_type,
                event_description=self.event_types.get(event_type, event_type),
                entity_type=entity_type,
                entity_id=entity_id,
                user_id=user.user_id,
                username=user.username,
                timestamp=datetime.utcnow(),
                details=details or {},
                ip_address=ip_address,
                user_agent=user_agent,
                severity=severity,
                checksum=None  # Will be calculated
            )
            
            # Calculate checksum for integrity
            audit_log.checksum = self._calculate_checksum(audit_log)
            
            # Save to database
            self.db.add(audit_log)
            await self.db.commit()
            
            logger.info(f"Audit log created: {audit_log.id}")
            
            # Handle critical events
            if severity in ["critical", "high"]:
                await self._handle_critical_event(audit_log)
            
            return audit_log
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to create audit log: {str(e)}")
            raise ValidationError(f"Failed to create audit log: {str(e)}")
    
    async def get_audit_trail(
        self,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        user_id: Optional[str] = None,
        event_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        severity: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Get audit trail with filtering options"""
        try:
            # Build query
            query = select(AuditLog)
            filters = []
            
            if entity_type:
                filters.append(AuditLog.entity_type == entity_type)
            if entity_id:
                filters.append(AuditLog.entity_id == entity_id)
            if user_id:
                filters.append(AuditLog.user_id == user_id)
            if event_type:
                filters.append(AuditLog.event_type == event_type)
            if start_date:
                filters.append(AuditLog.timestamp >= start_date)
            if end_date:
                filters.append(AuditLog.timestamp <= end_date)
            if severity:
                filters.append(AuditLog.severity == severity)
            
            if filters:
                query = query.where(and_(*filters))
            
            # Get total count
            count_query = select(func.count()).select_from(AuditLog)
            if filters:
                count_query = count_query.where(and_(*filters))
            
            total_result = await self.db.execute(count_query)
            total_count = total_result.scalar()
            
            # Get paginated results
            query = query.order_by(desc(AuditLog.timestamp))
            query = query.limit(limit).offset(offset)
            
            result = await self.db.execute(query)
            audit_logs = result.scalars().all()
            
            # Verify integrity
            integrity_issues = []
            for log in audit_logs:
                if not await self._verify_integrity(log):
                    integrity_issues.append(log.id)
            
            return {
                "total": total_count,
                "limit": limit,
                "offset": offset,
                "audit_logs": [self._serialize_audit_log(log) for log in audit_logs],
                "integrity_issues": integrity_issues,
                "filters_applied": {
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                    "user_id": user_id,
                    "event_type": event_type,
                    "start_date": start_date.isoformat() if start_date else None,
                    "end_date": end_date.isoformat() if end_date else None,
                    "severity": severity
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get audit trail: {str(e)}")
            raise ValidationError(f"Failed to get audit trail: {str(e)}")
    
    async def get_entity_history(
        self,
        entity_type: str,
        entity_id: str
    ) -> Dict[str, Any]:
        """Get complete history for a specific entity"""
        try:
            # Get all audit logs for the entity
            result = await self.db.execute(
                select(AuditLog)
                .where(
                    and_(
                        AuditLog.entity_type == entity_type,
                        AuditLog.entity_id == entity_id
                    )
                )
                .order_by(desc(AuditLog.timestamp))
            )
            audit_logs = result.scalars().all()
            
            # Group by event type
            event_groups = {}
            for log in audit_logs:
                event_type = log.event_type
                if event_type not in event_groups:
                    event_groups[event_type] = []
                event_groups[event_type].append(self._serialize_audit_log(log))
            
            # Calculate timeline
            timeline = []
            for log in audit_logs:
                timeline.append({
                    "timestamp": log.timestamp.isoformat(),
                    "event": log.event_description,
                    "user": log.username,
                    "severity": log.severity
                })
            
            # Get entity details based on type
            entity_details = await self._get_entity_details(entity_type, entity_id)
            
            return {
                "entity_type": entity_type,
                "entity_id": entity_id,
                "entity_details": entity_details,
                "total_events": len(audit_logs),
                "event_groups": event_groups,
                "timeline": timeline,
                "first_event": timeline[-1] if timeline else None,
                "last_event": timeline[0] if timeline else None
            }
            
        except Exception as e:
            logger.error(f"Failed to get entity history: {str(e)}")
            raise ValidationError(f"Failed to get entity history: {str(e)}")
    
    async def generate_compliance_report(
        self,
        start_date: datetime,
        end_date: datetime,
        report_type: str = "full"
    ) -> Dict[str, Any]:
        """Generate compliance audit report"""
        try:
            logger.info(f"Generating compliance report from {start_date} to {end_date}")
            
            # Get all audit logs in date range
            result = await self.db.execute(
                select(AuditLog)
                .where(
                    and_(
                        AuditLog.timestamp >= start_date,
                        AuditLog.timestamp <= end_date
                    )
                )
                .order_by(AuditLog.timestamp)
            )
            audit_logs = result.scalars().all()
            
            # Analyze events
            event_summary = {}
            severity_summary = {"info": 0, "warning": 0, "high": 0, "critical": 0}
            user_activity = {}
            compliance_violations = []
            
            for log in audit_logs:
                # Count events by type
                event_type = log.event_type
                if event_type not in event_summary:
                    event_summary[event_type] = 0
                event_summary[event_type] += 1
                
                # Count by severity
                severity_summary[log.severity] = severity_summary.get(log.severity, 0) + 1
                
                # Track user activity
                user_id = log.user_id
                if user_id not in user_activity:
                    user_activity[user_id] = {
                        "username": log.username,
                        "event_count": 0,
                        "event_types": set()
                    }
                user_activity[user_id]["event_count"] += 1
                user_activity[user_id]["event_types"].add(event_type)
                
                # Collect compliance violations
                if "violation" in event_type or "denied" in event_type:
                    compliance_violations.append({
                        "timestamp": log.timestamp.isoformat(),
                        "event": log.event_description,
                        "entity_type": log.entity_type,
                        "entity_id": log.entity_id,
                        "user": log.username,
                        "details": log.details
                    })
            
            # Generate report
            report = {
                "report_metadata": {
                    "report_id": str(uuid.uuid4()),
                    "report_type": report_type,
                    "generated_at": datetime.utcnow().isoformat(),
                    "period": {
                        "start": start_date.isoformat(),
                        "end": end_date.isoformat()
                    }
                },
                "summary": {
                    "total_events": len(audit_logs),
                    "unique_users": len(user_activity),
                    "event_types": len(event_summary),
                    "compliance_violations": len(compliance_violations)
                },
                "event_summary": event_summary,
                "severity_summary": severity_summary,
                "compliance_violations": compliance_violations,
                "user_activity": [
                    {
                        "user_id": user_id,
                        "username": data["username"],
                        "event_count": data["event_count"],
                        "event_types": list(data["event_types"])
                    }
                    for user_id, data in user_activity.items()
                ]
            }
            
            # Add detailed analysis for full report
            if report_type == "full":
                report["detailed_analysis"] = await self._generate_detailed_analysis(
                    audit_logs, start_date, end_date
                )
            
            # Log report generation
            await self.create_audit_log(
                event_type="system.report_generated",
                entity_type="compliance_report",
                entity_id=report["report_metadata"]["report_id"],
                user=User(user_id="system", username="system", email="system@mams.com"),
                details={
                    "report_type": report_type,
                    "period": f"{start_date.date()} to {end_date.date()}",
                    "total_events": len(audit_logs)
                }
            )
            
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate compliance report: {str(e)}")
            raise ValidationError(f"Failed to generate compliance report: {str(e)}")
    
    async def export_audit_trail(
        self,
        format: str = "json",
        filters: Optional[Dict[str, Any]] = None
    ) -> Union[str, bytes]:
        """Export audit trail in various formats"""
        try:
            # Get audit logs with filters
            audit_data = await self.get_audit_trail(
                entity_type=filters.get("entity_type") if filters else None,
                entity_id=filters.get("entity_id") if filters else None,
                user_id=filters.get("user_id") if filters else None,
                event_type=filters.get("event_type") if filters else None,
                start_date=filters.get("start_date") if filters else None,
                end_date=filters.get("end_date") if filters else None,
                limit=10000  # Max export limit
            )
            
            if format == "json":
                return json.dumps(audit_data, indent=2, default=str)
            
            elif format == "csv":
                import csv
                import io
                
                output = io.StringIO()
                writer = csv.writer(output)
                
                # Write header
                writer.writerow([
                    "Timestamp", "Event Type", "Event Description", "Entity Type",
                    "Entity ID", "User ID", "Username", "Severity", "IP Address",
                    "Details"
                ])
                
                # Write data
                for log in audit_data["audit_logs"]:
                    writer.writerow([
                        log["timestamp"],
                        log["event_type"],
                        log["event_description"],
                        log["entity_type"],
                        log["entity_id"],
                        log["user_id"],
                        log["username"],
                        log["severity"],
                        log.get("ip_address", ""),
                        json.dumps(log.get("details", {}))
                    ])
                
                return output.getvalue()
            
            else:
                raise ValidationError(f"Unsupported export format: {format}")
            
        except Exception as e:
            logger.error(f"Failed to export audit trail: {str(e)}")
            raise ValidationError(f"Failed to export audit trail: {str(e)}")
    
    async def archive_old_logs(
        self,
        days_to_keep: int = 365,
        archive_location: Optional[str] = None
    ) -> Dict[str, Any]:
        """Archive old audit logs"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
            
            # Get logs to archive
            result = await self.db.execute(
                select(AuditLog)
                .where(AuditLog.timestamp < cutoff_date)
            )
            logs_to_archive = result.scalars().all()
            
            if not logs_to_archive:
                return {
                    "archived_count": 0,
                    "message": "No logs to archive"
                }
            
            # Export logs before deletion
            archived_data = {
                "archive_metadata": {
                    "archive_date": datetime.utcnow().isoformat(),
                    "cutoff_date": cutoff_date.isoformat(),
                    "log_count": len(logs_to_archive)
                },
                "logs": [self._serialize_audit_log(log) for log in logs_to_archive]
            }
            
            # Save to archive location (mock implementation)
            if archive_location:
                archive_filename = f"audit_archive_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
                # In real implementation, save to S3, archive storage, etc.
                logger.info(f"Would archive to {archive_location}/{archive_filename}")
            
            # Delete archived logs
            for log in logs_to_archive:
                await self.db.delete(log)
            
            await self.db.commit()
            
            # Log the archival
            await self.create_audit_log(
                event_type="system.configuration_changed",
                entity_type="audit_archive",
                entity_id=str(uuid.uuid4()),
                user=User(user_id="system", username="system", email="system@mams.com"),
                details={
                    "archived_count": len(logs_to_archive),
                    "cutoff_date": cutoff_date.isoformat(),
                    "days_kept": days_to_keep
                }
            )
            
            return {
                "archived_count": len(logs_to_archive),
                "cutoff_date": cutoff_date.isoformat(),
                "archive_location": archive_location,
                "message": f"Successfully archived {len(logs_to_archive)} audit logs"
            }
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to archive audit logs: {str(e)}")
            raise ValidationError(f"Failed to archive audit logs: {str(e)}")
    
    # Private helper methods
    def _calculate_checksum(self, audit_log: AuditLog) -> str:
        """Calculate checksum for audit log integrity"""
        # Create a string representation of key fields
        checksum_data = f"{audit_log.event_type}|{audit_log.entity_type}|{audit_log.entity_id}|"
        checksum_data += f"{audit_log.user_id}|{audit_log.timestamp.isoformat()}|"
        checksum_data += json.dumps(audit_log.details, sort_keys=True)
        
        # Calculate SHA-256 hash
        return hashlib.sha256(checksum_data.encode()).hexdigest()
    
    async def _verify_integrity(self, audit_log: AuditLog) -> bool:
        """Verify integrity of an audit log entry"""
        expected_checksum = self._calculate_checksum(audit_log)
        return audit_log.checksum == expected_checksum
    
    def _serialize_audit_log(self, audit_log: AuditLog) -> Dict[str, Any]:
        """Serialize audit log to dictionary"""
        return {
            "id": audit_log.id,
            "timestamp": audit_log.timestamp.isoformat(),
            "event_type": audit_log.event_type,
            "event_description": audit_log.event_description,
            "entity_type": audit_log.entity_type,
            "entity_id": audit_log.entity_id,
            "user_id": audit_log.user_id,
            "username": audit_log.username,
            "severity": audit_log.severity,
            "ip_address": audit_log.ip_address,
            "user_agent": audit_log.user_agent,
            "details": audit_log.details,
            "checksum": audit_log.checksum
        }
    
    async def _handle_critical_event(self, audit_log: AuditLog):
        """Handle critical audit events"""
        # In a real implementation, this could:
        # - Send alerts to administrators
        # - Trigger automated responses
        # - Create compliance alerts
        # - Notify external systems
        
        logger.warning(f"Critical event logged: {audit_log.event_type} - {audit_log.event_description}")
        
        # Create compliance alert for critical events
        if "violation" in audit_log.event_type or "denied" in audit_log.event_type:
            from .compliance_service import ComplianceService
            from ..models.schemas import ComplianceAlertCreate
            
            alert_data = ComplianceAlertCreate(
                license_id=audit_log.entity_id if audit_log.entity_type == "license" else None,
                asset_id=audit_log.entity_id if audit_log.entity_type == "asset" else None,
                alert_type="critical_event",
                severity="critical",
                title=f"Critical Event: {audit_log.event_description}",
                description=f"Critical audit event detected: {audit_log.event_type}",
                metadata={
                    "audit_log_id": audit_log.id,
                    "event_details": audit_log.details
                }
            )
            
            compliance_service = ComplianceService(self.db)
            await compliance_service.create_compliance_alert(
                alert_data,
                User(user_id="system", username="audit-system", email="audit@mams.com")
            )
    
    async def _get_entity_details(self, entity_type: str, entity_id: str) -> Dict[str, Any]:
        """Get details about an entity"""
        try:
            if entity_type == "license":
                result = await self.db.execute(
                    select(License).where(License.id == entity_id)
                )
                license = result.scalar_one_or_none()
                if license:
                    return {
                        "license_number": license.license_number,
                        "status": license.status,
                        "asset_id": license.asset_id,
                        "licensor": license.licensor,
                        "licensee": license.licensee
                    }
            
            elif entity_type == "usage_record":
                result = await self.db.execute(
                    select(UsageRecord).where(UsageRecord.id == entity_id)
                )
                usage = result.scalar_one_or_none()
                if usage:
                    return {
                        "license_id": usage.license_id,
                        "usage_type": usage.usage_type,
                        "usage_count": usage.usage_count,
                        "usage_date": usage.usage_date.isoformat()
                    }
            
            elif entity_type == "compliance_alert":
                result = await self.db.execute(
                    select(ComplianceAlert).where(ComplianceAlert.id == entity_id)
                )
                alert = result.scalar_one_or_none()
                if alert:
                    return {
                        "alert_type": alert.alert_type,
                        "severity": alert.severity,
                        "title": alert.title,
                        "is_resolved": alert.is_resolved
                    }
            
            return {}
            
        except Exception as e:
            logger.error(f"Failed to get entity details: {str(e)}")
            return {}
    
    async def _generate_detailed_analysis(
        self,
        audit_logs: List[AuditLog],
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Generate detailed analysis for compliance report"""
        # Analyze patterns
        hourly_distribution = {}
        daily_distribution = {}
        
        for log in audit_logs:
            # Hourly distribution
            hour = log.timestamp.hour
            hourly_distribution[hour] = hourly_distribution.get(hour, 0) + 1
            
            # Daily distribution
            day = log.timestamp.date().isoformat()
            daily_distribution[day] = daily_distribution.get(day, 0) + 1
        
        # Find anomalies (simple spike detection)
        avg_daily_events = len(audit_logs) / ((end_date - start_date).days + 1)
        anomalous_days = [
            day for day, count in daily_distribution.items()
            if count > avg_daily_events * 2  # More than 2x average
        ]
        
        return {
            "hourly_distribution": hourly_distribution,
            "daily_distribution": daily_distribution,
            "average_events_per_day": avg_daily_events,
            "anomalous_days": anomalous_days,
            "peak_hour": max(hourly_distribution.items(), key=lambda x: x[1])[0] if hourly_distribution else None,
            "peak_day": max(daily_distribution.items(), key=lambda x: x[1])[0] if daily_distribution else None
        }