"""Audit Service for GDPR compliance logging"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from ..db.models import GDPRAuditLog
from ..models.schemas import AuditLogEntry, AuditLogResponse, AuditLogQuery, ExportFormat
from ..core.config import settings


class AuditService:
    """Service for GDPR audit logging"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.logger = logging.getLogger(__name__)
    
    async def log_event(
        self,
        event_type: str,
        action: str,
        actor_id: Optional[UUID] = None,
        actor_type: str = "system",
        subject_user_id: Optional[UUID] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        old_value: Optional[Dict[str, Any]] = None,
        new_value: Optional[Dict[str, Any]] = None,
        actor_ip: Optional[str] = None,
        actor_user_agent: Optional[str] = None
    ) -> GDPRAuditLog:
        """Create an audit log entry"""
        try:
            audit_log = GDPRAuditLog(
                event_type=event_type,
                action=action,
                actor_id=actor_id,
                actor_type=actor_type,
                subject_user_id=subject_user_id,
                resource_type=resource_type,
                resource_id=resource_id,
                success=success,
                error_message=error_message,
                metadata=metadata,
                old_value=old_value,
                new_value=new_value,
                actor_ip=actor_ip,
                actor_user_agent=actor_user_agent
            )
            
            self.db.add(audit_log)
            await self.db.commit()
            await self.db.refresh(audit_log)
            
            # Log to system logger as well
            log_message = f"GDPR Audit: {event_type} - {action}"
            if success:
                self.logger.info(log_message, extra={
                    "audit_id": str(audit_log.id),
                    "actor_id": str(actor_id) if actor_id else None,
                    "subject_user_id": str(subject_user_id) if subject_user_id else None
                })
            else:
                self.logger.warning(f"{log_message} - Failed: {error_message}", extra={
                    "audit_id": str(audit_log.id),
                    "actor_id": str(actor_id) if actor_id else None,
                    "subject_user_id": str(subject_user_id) if subject_user_id else None
                })
            
            return audit_log
            
        except Exception as e:
            self.logger.error(f"Failed to create audit log: {str(e)}")
            # Don't raise - audit logging should not break the main flow
            return None
    
    # Convenience methods for common events
    
    async def log_consent_given(
        self,
        user_id: UUID,
        consent_type: str,
        policy_version: str,
        actor_id: Optional[UUID] = None,
        actor_ip: Optional[str] = None
    ) -> None:
        """Log consent given event"""
        await self.log_event(
            event_type="consent",
            action="consent_given",
            actor_id=actor_id or user_id,
            actor_type="user",
            subject_user_id=user_id,
            resource_type="consent",
            resource_id=consent_type,
            metadata={
                "consent_type": consent_type,
                "policy_version": policy_version
            },
            actor_ip=actor_ip
        )
    
    async def log_consent_withdrawn(
        self,
        user_id: UUID,
        consent_type: str,
        reason: Optional[str] = None,
        actor_id: Optional[UUID] = None,
        actor_ip: Optional[str] = None
    ) -> None:
        """Log consent withdrawal event"""
        await self.log_event(
            event_type="consent",
            action="consent_withdrawn",
            actor_id=actor_id or user_id,
            actor_type="user",
            subject_user_id=user_id,
            resource_type="consent",
            resource_id=consent_type,
            metadata={
                "consent_type": consent_type,
                "withdrawal_reason": reason
            },
            actor_ip=actor_ip
        )
    
    async def log_data_request(
        self,
        user_id: UUID,
        request_type: str,
        request_id: str,
        actor_id: Optional[UUID] = None,
        actor_ip: Optional[str] = None
    ) -> None:
        """Log data request creation"""
        await self.log_event(
            event_type="data_request",
            action=f"request_{request_type}",
            actor_id=actor_id or user_id,
            actor_type="user",
            subject_user_id=user_id,
            resource_type="data_request",
            resource_id=request_id,
            metadata={
                "request_type": request_type,
                "request_id": request_id
            },
            actor_ip=actor_ip
        )
    
    async def log_data_export(
        self,
        user_id: UUID,
        categories: List[str],
        format: ExportFormat,
        record_count: int,
        actor_id: Optional[UUID] = None
    ) -> None:
        """Log data export event"""
        await self.log_event(
            event_type="data_export",
            action="export_generated",
            actor_id=actor_id,
            actor_type="system" if actor_id is None else "user",
            subject_user_id=user_id,
            metadata={
                "categories": categories,
                "format": format.value,
                "record_count": record_count
            }
        )
    
    async def log_data_deletion(
        self,
        user_id: UUID,
        tables_affected: Dict[str, int],
        total_records: int,
        actor_id: Optional[UUID] = None
    ) -> None:
        """Log data deletion event"""
        await self.log_event(
            event_type="data_deletion",
            action="data_deleted",
            actor_id=actor_id,
            actor_type="system" if actor_id is None else "admin",
            subject_user_id=user_id,
            metadata={
                "tables_affected": tables_affected,
                "total_records": total_records
            }
        )
    
    async def log_anonymization(
        self,
        user_id: UUID,
        method: str,
        tables_affected: Dict[str, int],
        partial: bool = False
    ) -> None:
        """Log data anonymization event"""
        await self.log_event(
            event_type="anonymization",
            action="data_anonymized",
            actor_id=None,
            actor_type="system",
            subject_user_id=user_id,
            metadata={
                "method": method,
                "tables_affected": tables_affected,
                "partial": partial
            }
        )
    
    async def log_policy_acceptance(
        self,
        user_id: UUID,
        policy_version: str,
        accepted: bool,
        actor_ip: Optional[str] = None
    ) -> None:
        """Log privacy policy acceptance"""
        await self.log_event(
            event_type="privacy_policy",
            action="policy_accepted" if accepted else "policy_rejected",
            actor_id=user_id,
            actor_type="user",
            subject_user_id=user_id,
            resource_type="privacy_policy",
            resource_id=policy_version,
            metadata={
                "policy_version": policy_version,
                "accepted": accepted
            },
            actor_ip=actor_ip
        )
    
    async def log_access_attempt(
        self,
        actor_id: Optional[UUID],
        resource_type: str,
        resource_id: str,
        action: str,
        success: bool,
        reason: Optional[str] = None,
        actor_ip: Optional[str] = None
    ) -> None:
        """Log access attempt to GDPR-protected resource"""
        await self.log_event(
            event_type="access_control",
            action=action,
            actor_id=actor_id,
            actor_type="user" if actor_id else "anonymous",
            resource_type=resource_type,
            resource_id=resource_id,
            success=success,
            error_message=reason if not success else None,
            actor_ip=actor_ip
        )
    
    async def query_logs(
        self,
        query: AuditLogQuery
    ) -> List[AuditLogResponse]:
        """Query audit logs with filters"""
        stmt = select(GDPRAuditLog)
        
        # Apply filters
        conditions = []
        
        if query.event_type:
            conditions.append(GDPRAuditLog.event_type == query.event_type)
        
        if query.actor_id:
            conditions.append(GDPRAuditLog.actor_id == query.actor_id)
        
        if query.subject_user_id:
            conditions.append(GDPRAuditLog.subject_user_id == query.subject_user_id)
        
        if query.start_date:
            conditions.append(GDPRAuditLog.event_timestamp >= query.start_date)
        
        if query.end_date:
            conditions.append(GDPRAuditLog.event_timestamp <= query.end_date)
        
        if conditions:
            stmt = stmt.where(and_(*conditions))
        
        # Apply ordering and pagination
        stmt = stmt.order_by(GDPRAuditLog.event_timestamp.desc())
        stmt = stmt.limit(query.limit).offset(query.offset)
        
        result = await self.db.execute(stmt)
        logs = result.scalars().all()
        
        return [
            AuditLogResponse(
                id=log.id,
                event_type=log.event_type,
                event_timestamp=log.event_timestamp,
                action=log.action,
                actor_id=log.actor_id,
                actor_type=log.actor_type,
                actor_ip=log.actor_ip,
                subject_user_id=log.subject_user_id,
                resource_type=log.resource_type,
                resource_id=log.resource_id,
                success=log.success,
                error_message=log.error_message,
                metadata=log.metadata,
                old_value=log.old_value,
                new_value=log.new_value
            )
            for log in logs
        ]
    
    async def get_user_activity_report(
        self,
        user_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Generate activity report for a specific user"""
        conditions = [
            or_(
                GDPRAuditLog.actor_id == user_id,
                GDPRAuditLog.subject_user_id == user_id
            )
        ]
        
        if start_date:
            conditions.append(GDPRAuditLog.event_timestamp >= start_date)
        if end_date:
            conditions.append(GDPRAuditLog.event_timestamp <= end_date)
        
        stmt = select(GDPRAuditLog).where(and_(*conditions))
        result = await self.db.execute(stmt)
        logs = result.scalars().all()
        
        # Analyze activity
        activity_summary = {
            "total_events": len(logs),
            "events_by_type": {},
            "actions_performed": {},
            "consents": [],
            "data_requests": [],
            "exports": [],
            "policy_acceptances": []
        }
        
        for log in logs:
            # Count by event type
            activity_summary["events_by_type"][log.event_type] = \
                activity_summary["events_by_type"].get(log.event_type, 0) + 1
            
            # Count actions
            activity_summary["actions_performed"][log.action] = \
                activity_summary["actions_performed"].get(log.action, 0) + 1
            
            # Collect specific events
            if log.event_type == "consent":
                activity_summary["consents"].append({
                    "action": log.action,
                    "timestamp": log.event_timestamp,
                    "consent_type": log.metadata.get("consent_type") if log.metadata else None
                })
            elif log.event_type == "data_request":
                activity_summary["data_requests"].append({
                    "action": log.action,
                    "timestamp": log.event_timestamp,
                    "request_type": log.metadata.get("request_type") if log.metadata else None,
                    "request_id": log.resource_id
                })
            elif log.event_type == "data_export":
                activity_summary["exports"].append({
                    "timestamp": log.event_timestamp,
                    "format": log.metadata.get("format") if log.metadata else None,
                    "record_count": log.metadata.get("record_count") if log.metadata else None
                })
            elif log.event_type == "privacy_policy":
                activity_summary["policy_acceptances"].append({
                    "action": log.action,
                    "timestamp": log.event_timestamp,
                    "policy_version": log.resource_id,
                    "accepted": log.metadata.get("accepted") if log.metadata else None
                })
        
        return activity_summary
    
    async def cleanup_old_logs(self, retention_days: int) -> int:
        """Remove old audit logs beyond retention period"""
        cutoff_date = datetime.utcnow().replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        cutoff_date = cutoff_date.replace(day=cutoff_date.day - retention_days)
        
        # Delete old logs
        stmt = select(GDPRAuditLog).where(
            GDPRAuditLog.event_timestamp < cutoff_date
        )
        result = await self.db.execute(stmt)
        old_logs = result.scalars().all()
        
        deleted_count = len(old_logs)
        
        for log in old_logs:
            await self.db.delete(log)
        
        await self.db.commit()
        
        if deleted_count > 0:
            self.logger.info(f"Cleaned up {deleted_count} old audit logs")
        
        return deleted_count