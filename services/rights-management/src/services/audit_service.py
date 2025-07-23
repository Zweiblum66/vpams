"""
Audit Trail Service for Rights Management
"""

import csv
import json
import uuid
from io import StringIO, BytesIO
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc, asc, String
from sqlalchemy.orm import selectinload
import pandas as pd
import asyncio

from ..models.audit_models import AuditTrail, AuditArchive
from ..models.audit_schemas import (
    AuditTrailCreate, AuditTrailResponse, AuditTrailFilter,
    AuditTrailStats, AuditTrailExport, AuditAction,
    AuditResourceType, AuditContext, AuditDiff,
    AuditBatch, AuditRetentionPolicy
)
from ..core.logging import get_logger
from ..core.exceptions import NotFoundError, ValidationError

logger = get_logger(__name__)


class AuditService:
    """Service for managing audit trails"""
    
    async def create_audit_trail(
        self,
        db: AsyncSession,
        audit_data: AuditTrailCreate
    ) -> AuditTrailResponse:
        """Create a new audit trail entry"""
        try:
            # Determine if this is compliance or security relevant
            audit_data.compliance_relevant = self._is_compliance_relevant(audit_data.action)
            audit_data.security_relevant = self._is_security_relevant(audit_data.action)
            
            # Create the audit trail entry
            audit_trail = AuditTrail(
                action=audit_data.action,
                resource_type=audit_data.resource_type,
                resource_id=audit_data.resource_id,
                user_id=audit_data.user_id,
                user_email=audit_data.user_email,
                user_name=audit_data.user_name,
                user_roles=audit_data.user_roles,
                ip_address=audit_data.ip_address,
                user_agent=audit_data.user_agent,
                session_id=audit_data.session_id,
                old_values=audit_data.old_values,
                new_values=audit_data.new_values,
                changes_summary=audit_data.changes_summary,
                metadata=audit_data.metadata,
                tags=audit_data.tags,
                compliance_relevant=audit_data.compliance_relevant,
                security_relevant=audit_data.security_relevant,
                success=audit_data.success,
                error_message=audit_data.error_message
            )
            
            db.add(audit_trail)
            await db.commit()
            await db.refresh(audit_trail)
            
            # Convert to response
            response = AuditTrailResponse(**audit_trail.to_dict())
            display_names = audit_trail.get_display_names()
            response.action_display_name = display_names["action_display_name"]
            response.resource_display_name = display_names["resource_display_name"]
            
            logger.info(f"Created audit trail entry: {audit_trail.id}")
            return response
            
        except Exception as e:
            logger.error(f"Error creating audit trail: {str(e)}")
            await db.rollback()
            raise
    
    async def create_audit_batch(
        self,
        db: AsyncSession,
        audit_batch: AuditBatch
    ) -> List[AuditTrailResponse]:
        """Create multiple audit trail entries in a batch"""
        try:
            created_entries = []
            
            for entry_data in audit_batch.entries:
                # Add batch metadata to each entry
                entry_data.metadata = entry_data.metadata or {}
                entry_data.metadata["batch_id"] = audit_batch.batch_id
                entry_data.metadata.update(audit_batch.batch_metadata)
                
                # Create the entry
                entry = await self.create_audit_trail(db, entry_data)
                created_entries.append(entry)
            
            logger.info(f"Created batch of {len(created_entries)} audit trail entries")
            return created_entries
            
        except Exception as e:
            logger.error(f"Error creating audit batch: {str(e)}")
            await db.rollback()
            raise
    
    async def get_audit_trails(
        self,
        db: AsyncSession,
        filter_params: AuditTrailFilter,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[AuditTrailResponse], int]:
        """Get audit trails with filtering and pagination"""
        try:
            # Build the query
            query = select(AuditTrail)
            
            # Apply filters
            conditions = []
            
            if filter_params.start_date:
                conditions.append(AuditTrail.timestamp >= filter_params.start_date)
            if filter_params.end_date:
                conditions.append(AuditTrail.timestamp <= filter_params.end_date)
            
            if filter_params.resource_type:
                conditions.append(AuditTrail.resource_type == filter_params.resource_type)
            if filter_params.resource_id:
                conditions.append(AuditTrail.resource_id == filter_params.resource_id)
            if filter_params.resource_ids:
                conditions.append(AuditTrail.resource_id.in_(filter_params.resource_ids))
            
            if filter_params.action:
                conditions.append(AuditTrail.action == filter_params.action)
            if filter_params.actions:
                conditions.append(AuditTrail.action.in_(filter_params.actions))
            
            if filter_params.user_id:
                conditions.append(AuditTrail.user_id == filter_params.user_id)
            if filter_params.user_ids:
                conditions.append(AuditTrail.user_id.in_(filter_params.user_ids))
            if filter_params.user_email:
                conditions.append(AuditTrail.user_email.ilike(f"%{filter_params.user_email}%"))
            
            if filter_params.ip_address:
                conditions.append(AuditTrail.ip_address == filter_params.ip_address)
            if filter_params.session_id:
                conditions.append(AuditTrail.session_id == filter_params.session_id)
            
            if filter_params.success is not None:
                conditions.append(AuditTrail.success == filter_params.success)
            if filter_params.compliance_relevant is not None:
                conditions.append(AuditTrail.compliance_relevant == filter_params.compliance_relevant)
            if filter_params.security_relevant is not None:
                conditions.append(AuditTrail.security_relevant == filter_params.security_relevant)
            
            if filter_params.search_text:
                search_conditions = [
                    AuditTrail.changes_summary.ilike(f"%{filter_params.search_text}%"),
                    func.cast(AuditTrail.metadata, String).ilike(f"%{filter_params.search_text}%")
                ]
                conditions.append(or_(*search_conditions))
            
            if filter_params.tags:
                # Check if any of the tags match
                tag_conditions = []
                for tag in filter_params.tags:
                    tag_conditions.append(func.jsonb_contains(AuditTrail.tags, json.dumps([tag])))
                conditions.append(or_(*tag_conditions))
            
            if conditions:
                query = query.where(and_(*conditions))
            
            # Get total count
            count_query = select(func.count()).select_from(query.subquery())
            total_result = await db.execute(count_query)
            total = total_result.scalar() or 0
            
            # Apply sorting
            sort_field = getattr(AuditTrail, filter_params.sort_by, AuditTrail.timestamp)
            if filter_params.sort_order == "desc":
                query = query.order_by(desc(sort_field))
            else:
                query = query.order_by(asc(sort_field))
            
            # Apply pagination
            query = query.offset(skip).limit(limit)
            
            # Execute query
            result = await db.execute(query)
            audit_trails = result.scalars().all()
            
            # Convert to responses
            responses = []
            for audit_trail in audit_trails:
                response = AuditTrailResponse(**audit_trail.to_dict())
                display_names = audit_trail.get_display_names()
                response.action_display_name = display_names["action_display_name"]
                response.resource_display_name = display_names["resource_display_name"]
                responses.append(response)
            
            return responses, total
            
        except Exception as e:
            logger.error(f"Error getting audit trails: {str(e)}")
            raise
    
    async def get_audit_trail(
        self,
        db: AsyncSession,
        audit_id: str
    ) -> AuditTrailResponse:
        """Get a specific audit trail entry"""
        try:
            query = select(AuditTrail).where(AuditTrail.id == audit_id)
            result = await db.execute(query)
            audit_trail = result.scalar_one_or_none()
            
            if not audit_trail:
                raise NotFoundError(f"Audit trail entry not found: {audit_id}")
            
            response = AuditTrailResponse(**audit_trail.to_dict())
            display_names = audit_trail.get_display_names()
            response.action_display_name = display_names["action_display_name"]
            response.resource_display_name = display_names["resource_display_name"]
            
            return response
            
        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error getting audit trail: {str(e)}")
            raise
    
    async def get_audit_stats(
        self,
        db: AsyncSession,
        filter_params: AuditTrailFilter
    ) -> AuditTrailStats:
        """Get audit trail statistics"""
        try:
            # Build base query with filters
            query = select(AuditTrail)
            conditions = []
            
            if filter_params.start_date:
                conditions.append(AuditTrail.timestamp >= filter_params.start_date)
            if filter_params.end_date:
                conditions.append(AuditTrail.timestamp <= filter_params.end_date)
            
            if conditions:
                query = query.where(and_(*conditions))
            
            # Get total entries
            total_query = select(func.count()).select_from(query.subquery())
            total_result = await db.execute(total_query)
            total_entries = total_result.scalar() or 0
            
            # Get entries by action
            action_query = select(
                AuditTrail.action,
                func.count().label("count")
            ).group_by(AuditTrail.action)
            if conditions:
                action_query = action_query.where(and_(*conditions))
            
            action_result = await db.execute(action_query)
            entries_by_action = {row.action.value: row.count for row in action_result}
            
            # Get entries by resource type
            resource_query = select(
                AuditTrail.resource_type,
                func.count().label("count")
            ).group_by(AuditTrail.resource_type)
            if conditions:
                resource_query = resource_query.where(and_(*conditions))
            
            resource_result = await db.execute(resource_query)
            entries_by_resource_type = {row.resource_type.value: row.count for row in resource_result}
            
            # Get entries by user (top 10)
            user_query = select(
                AuditTrail.user_email,
                func.count().label("count")
            ).group_by(AuditTrail.user_email).order_by(desc("count")).limit(10)
            if conditions:
                user_query = user_query.where(and_(*conditions))
            
            user_result = await db.execute(user_query)
            entries_by_user = {row.user_email: row.count for row in user_result}
            
            # Get compliance and security counts
            compliance_query = select(func.count()).where(
                AuditTrail.compliance_relevant == True
            )
            if conditions:
                compliance_query = compliance_query.where(and_(*conditions))
            
            compliance_result = await db.execute(compliance_query)
            compliance_count = compliance_result.scalar() or 0
            
            security_query = select(func.count()).where(
                AuditTrail.security_relevant == True
            )
            if conditions:
                security_query = security_query.where(and_(*conditions))
            
            security_result = await db.execute(security_query)
            security_count = security_result.scalar() or 0
            
            failed_query = select(func.count()).where(
                AuditTrail.success == False
            )
            if conditions:
                failed_query = failed_query.where(and_(*conditions))
            
            failed_result = await db.execute(failed_query)
            failed_count = failed_result.scalar() or 0
            
            # Get date range
            date_query = select(
                func.min(AuditTrail.timestamp).label("start_date"),
                func.max(AuditTrail.timestamp).label("end_date")
            )
            if conditions:
                date_query = date_query.where(and_(*conditions))
            
            date_result = await db.execute(date_query)
            date_row = date_result.one()
            
            # Get entries by date (last 30 days or specified range)
            end_date = filter_params.end_date or datetime.utcnow()
            start_date = filter_params.start_date or (end_date - timedelta(days=30))
            
            date_entries_query = select(
                func.date_trunc('day', AuditTrail.timestamp).label("date"),
                func.count().label("count")
            ).where(
                and_(
                    AuditTrail.timestamp >= start_date,
                    AuditTrail.timestamp <= end_date
                )
            ).group_by("date").order_by("date")
            
            date_entries_result = await db.execute(date_entries_query)
            entries_by_date = [
                {"date": row.date.isoformat(), "count": row.count}
                for row in date_entries_result
            ]
            
            return AuditTrailStats(
                total_entries=total_entries,
                entries_by_action=entries_by_action,
                entries_by_resource_type=entries_by_resource_type,
                entries_by_user=entries_by_user,
                entries_by_date=entries_by_date,
                compliance_relevant_count=compliance_count,
                security_relevant_count=security_count,
                failed_actions_count=failed_count,
                start_date=date_row.start_date or datetime.utcnow(),
                end_date=date_row.end_date or datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Error getting audit stats: {str(e)}")
            raise
    
    async def export_audit_trails(
        self,
        db: AsyncSession,
        export_params: AuditTrailExport
    ) -> bytes:
        """Export audit trails to specified format"""
        try:
            # Get all audit trails matching the filter
            audit_trails, _ = await self.get_audit_trails(
                db,
                export_params.filter,
                skip=0,
                limit=1000000  # Large limit for export
            )
            
            # Convert to dictionaries
            data = []
            for trail in audit_trails:
                trail_dict = trail.dict()
                
                # Handle field inclusion/exclusion
                if export_params.include_fields:
                    trail_dict = {k: v for k, v in trail_dict.items() if k in export_params.include_fields}
                if export_params.exclude_fields:
                    trail_dict = {k: v for k, v in trail_dict.items() if k not in export_params.exclude_fields}
                
                data.append(trail_dict)
            
            # Export based on format
            if export_params.format == "json":
                return json.dumps(data, indent=2, default=str).encode()
            
            elif export_params.format == "csv":
                if not data:
                    return b""
                
                output = StringIO()
                writer = csv.DictWriter(output, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)
                return output.getvalue().encode()
            
            elif export_params.format == "excel":
                df = pd.DataFrame(data)
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df.to_excel(writer, sheet_name='Audit Trails', index=False)
                return output.getvalue()
            
            else:
                raise ValidationError(f"Unsupported export format: {export_params.format}")
            
        except Exception as e:
            logger.error(f"Error exporting audit trails: {str(e)}")
            raise
    
    async def archive_audit_trails(
        self,
        db: AsyncSession,
        retention_policy: AuditRetentionPolicy
    ) -> int:
        """Archive old audit trails based on retention policy"""
        try:
            # Calculate archive date
            archive_date = datetime.utcnow() - timedelta(days=retention_policy.archive_after_days)
            
            # Build query for records to archive
            query = select(AuditTrail).where(
                AuditTrail.timestamp < archive_date
            )
            
            # Exclude certain actions or resource types if specified
            if retention_policy.exclude_actions:
                query = query.where(~AuditTrail.action.in_(retention_policy.exclude_actions))
            if retention_policy.exclude_resource_types:
                query = query.where(~AuditTrail.resource_type.in_(retention_policy.exclude_resource_types))
            
            # Get records to archive
            result = await db.execute(query)
            audit_trails = result.scalars().all()
            
            # Archive in batches
            batch_id = str(uuid.uuid4())
            archived_count = 0
            
            for audit_trail in audit_trails:
                # Create archive entry
                archive_entry = AuditArchive(
                    id=audit_trail.id,
                    timestamp=audit_trail.timestamp,
                    action=audit_trail.action,
                    resource_type=audit_trail.resource_type,
                    resource_id=audit_trail.resource_id,
                    user_id=audit_trail.user_id,
                    user_email=audit_trail.user_email,
                    user_name=audit_trail.user_name,
                    user_roles=audit_trail.user_roles,
                    ip_address=audit_trail.ip_address,
                    user_agent=audit_trail.user_agent,
                    session_id=audit_trail.session_id,
                    old_values=audit_trail.old_values,
                    new_values=audit_trail.new_values,
                    changes_summary=audit_trail.changes_summary,
                    metadata=audit_trail.metadata,
                    tags=audit_trail.tags,
                    compliance_relevant=audit_trail.compliance_relevant,
                    security_relevant=audit_trail.security_relevant,
                    success=audit_trail.success,
                    error_message=audit_trail.error_message,
                    archive_batch_id=batch_id
                )
                
                db.add(archive_entry)
                
                # Delete from main table
                await db.delete(audit_trail)
                archived_count += 1
            
            await db.commit()
            
            logger.info(f"Archived {archived_count} audit trail entries")
            return archived_count
            
        except Exception as e:
            logger.error(f"Error archiving audit trails: {str(e)}")
            await db.rollback()
            raise
    
    async def cleanup_archived_trails(
        self,
        db: AsyncSession,
        retention_policy: AuditRetentionPolicy
    ) -> int:
        """Delete old archived audit trails based on retention policy"""
        try:
            # Calculate deletion date
            delete_date = datetime.utcnow() - timedelta(days=retention_policy.delete_archived_after_days)
            
            # Special handling for compliance-relevant records
            compliance_delete_date = datetime.utcnow() - timedelta(days=retention_policy.compliance_relevant_retention_days)
            
            # Build query for records to delete
            query = select(AuditArchive).where(
                or_(
                    and_(
                        AuditArchive.compliance_relevant == False,
                        AuditArchive.archived_at < delete_date
                    ),
                    and_(
                        AuditArchive.compliance_relevant == True,
                        AuditArchive.archived_at < compliance_delete_date
                    )
                )
            )
            
            # Get count of records to delete
            count_result = await db.execute(select(func.count()).select_from(query.subquery()))
            delete_count = count_result.scalar() or 0
            
            # Delete records
            if delete_count > 0:
                delete_query = AuditArchive.__table__.delete().where(
                    or_(
                        and_(
                            AuditArchive.compliance_relevant == False,
                            AuditArchive.archived_at < delete_date
                        ),
                        and_(
                            AuditArchive.compliance_relevant == True,
                            AuditArchive.archived_at < compliance_delete_date
                        )
                    )
                )
                await db.execute(delete_query)
                await db.commit()
            
            logger.info(f"Deleted {delete_count} archived audit trail entries")
            return delete_count
            
        except Exception as e:
            logger.error(f"Error cleaning up archived trails: {str(e)}")
            await db.rollback()
            raise
    
    def _is_compliance_relevant(self, action: AuditAction) -> bool:
        """Determine if an action is compliance-relevant"""
        compliance_actions = {
            AuditAction.PARTY_CREATED,
            AuditAction.PARTY_UPDATED,
            AuditAction.PARTY_DELETED,
            AuditAction.LICENSE_CREATED,
            AuditAction.LICENSE_UPDATED,
            AuditAction.LICENSE_APPROVED,
            AuditAction.LICENSE_TERMINATED,
            AuditAction.USAGE_RECORDED,
            AuditAction.USAGE_DELETED,
            AuditAction.COMPLIANCE_CHECK_PERFORMED,
            AuditAction.ACCESS_GRANTED,
            AuditAction.ACCESS_REVOKED,
            AuditAction.PERMISSION_CHANGED,
            AuditAction.DATA_EXPORTED,
            AuditAction.DATA_IMPORTED
        }
        return action in compliance_actions
    
    def _is_security_relevant(self, action: AuditAction) -> bool:
        """Determine if an action is security-relevant"""
        security_actions = {
            AuditAction.ACCESS_GRANTED,
            AuditAction.ACCESS_REVOKED,
            AuditAction.PERMISSION_CHANGED,
            AuditAction.LICENSE_DOWNLOADED,
            AuditAction.DATA_EXPORTED,
            AuditAction.DATA_IMPORTED,
            AuditAction.SETTINGS_CHANGED,
            AuditAction.BULK_OPERATION_PERFORMED
        }
        return action in security_actions
    
    @staticmethod
    def calculate_diff(old_values: Dict[str, Any], new_values: Dict[str, Any]) -> List[AuditDiff]:
        """Calculate differences between old and new values"""
        diffs = []
        
        # Get all keys
        all_keys = set(old_values.keys() if old_values else []) | set(new_values.keys() if new_values else [])
        
        for key in all_keys:
            old_value = old_values.get(key) if old_values else None
            new_value = new_values.get(key) if new_values else None
            
            if old_value != new_value:
                diffs.append(AuditDiff(
                    field=key,
                    old_value=old_value,
                    new_value=new_value
                ))
        
        return diffs
    
    @staticmethod
    def generate_changes_summary(diffs: List[AuditDiff]) -> str:
        """Generate a human-readable summary of changes"""
        if not diffs:
            return "No changes"
        
        summary_parts = []
        for diff in diffs[:5]:  # Limit to first 5 changes
            if diff.old_value is None:
                summary_parts.append(f"Added {diff.field}: {diff.new_value}")
            elif diff.new_value is None:
                summary_parts.append(f"Removed {diff.field}")
            else:
                summary_parts.append(f"Changed {diff.field} from {diff.old_value} to {diff.new_value}")
        
        if len(diffs) > 5:
            summary_parts.append(f"... and {len(diffs) - 5} more changes")
        
        return "; ".join(summary_parts)