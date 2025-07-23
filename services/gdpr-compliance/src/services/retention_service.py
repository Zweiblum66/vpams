"""Data Retention Service for GDPR Compliance"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, update, text, and_, or_, func
import asyncio

from ..db.models import (
    DataRetentionRule, DataCategory, DataMapping,
    GDPRAuditLog, AnonymizationLog
)
from ..models.schemas import (
    DataRetentionRuleCreate, DataRetentionRuleUpdate,
    DataRetentionRuleResponse, RetentionExecutionResult
)
from ..utils.anonymization import anonymize_data, batch_anonymize
from .audit_service import AuditService
from ..core.config import settings

logger = logging.getLogger(__name__)


class RetentionService:
    """Service for managing and executing data retention policies"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.logger = logging.getLogger(__name__)
        self.audit_service = AuditService(db)
    
    # CRUD Operations for Retention Rules
    
    async def create_retention_rule(
        self,
        rule_data: DataRetentionRuleCreate,
        created_by: str
    ) -> DataRetentionRule:
        """Create a new retention rule"""
        try:
            # Validate category if provided
            if rule_data.data_category_id:
                result = await self.db.execute(
                    select(DataCategory).where(
                        DataCategory.id == rule_data.data_category_id
                    )
                )
                category = result.scalar_one_or_none()
                if not category:
                    raise ValueError(f"Data category {rule_data.data_category_id} not found")
            
            # Create rule
            rule = DataRetentionRule(
                rule_name=rule_data.rule_name,
                description=rule_data.description,
                table_name=rule_data.table_name,
                data_category_id=rule_data.data_category_id,
                condition_sql=rule_data.condition_sql,
                retention_days=rule_data.retention_days,
                deletion_method=rule_data.deletion_method,
                run_frequency_days=rule_data.run_frequency_days,
                is_active=rule_data.is_active,
                next_run=datetime.utcnow() + timedelta(days=rule_data.run_frequency_days)
            )
            
            self.db.add(rule)
            await self.db.commit()
            await self.db.refresh(rule)
            
            # Log audit event
            await self.audit_service.log_event(
                event_type="retention_policy",
                action="rule_created",
                resource_type="retention_rule",
                resource_id=str(rule.id),
                metadata={
                    "rule_name": rule.rule_name,
                    "retention_days": rule.retention_days,
                    "created_by": created_by
                }
            )
            
            return rule
            
        except Exception as e:
            self.logger.error(f"Error creating retention rule: {str(e)}")
            await self.db.rollback()
            raise
    
    async def get_retention_rule(self, rule_id: UUID) -> Optional[DataRetentionRule]:
        """Get a retention rule by ID"""
        result = await self.db.execute(
            select(DataRetentionRule).where(DataRetentionRule.id == rule_id)
        )
        return result.scalar_one_or_none()
    
    async def list_retention_rules(
        self,
        active_only: bool = False,
        category_id: Optional[UUID] = None
    ) -> List[DataRetentionRule]:
        """List all retention rules"""
        query = select(DataRetentionRule)
        
        conditions = []
        if active_only:
            conditions.append(DataRetentionRule.is_active == True)
        if category_id:
            conditions.append(DataRetentionRule.data_category_id == category_id)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        query = query.order_by(DataRetentionRule.rule_name)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def update_retention_rule(
        self,
        rule_id: UUID,
        update_data: DataRetentionRuleUpdate,
        updated_by: str
    ) -> Optional[DataRetentionRule]:
        """Update a retention rule"""
        try:
            rule = await self.get_retention_rule(rule_id)
            if not rule:
                return None
            
            # Track changes for audit
            old_values = {
                "retention_days": rule.retention_days,
                "deletion_method": rule.deletion_method,
                "is_active": rule.is_active
            }
            
            # Update fields
            for field, value in update_data.dict(exclude_unset=True).items():
                setattr(rule, field, value)
            
            # Update next run if frequency changed
            if update_data.run_frequency_days is not None:
                rule.next_run = datetime.utcnow() + timedelta(days=update_data.run_frequency_days)
            
            await self.db.commit()
            await self.db.refresh(rule)
            
            # Log audit event
            new_values = {
                "retention_days": rule.retention_days,
                "deletion_method": rule.deletion_method,
                "is_active": rule.is_active
            }
            
            await self.audit_service.log_event(
                event_type="retention_policy",
                action="rule_updated",
                resource_type="retention_rule",
                resource_id=str(rule.id),
                old_value=old_values,
                new_value=new_values,
                metadata={"updated_by": updated_by}
            )
            
            return rule
            
        except Exception as e:
            self.logger.error(f"Error updating retention rule: {str(e)}")
            await self.db.rollback()
            raise
    
    async def delete_retention_rule(self, rule_id: UUID, deleted_by: str) -> bool:
        """Delete a retention rule"""
        try:
            rule = await self.get_retention_rule(rule_id)
            if not rule:
                return False
            
            await self.db.delete(rule)
            await self.db.commit()
            
            # Log audit event
            await self.audit_service.log_event(
                event_type="retention_policy",
                action="rule_deleted",
                resource_type="retention_rule",
                resource_id=str(rule_id),
                metadata={
                    "rule_name": rule.rule_name,
                    "deleted_by": deleted_by
                }
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error deleting retention rule: {str(e)}")
            await self.db.rollback()
            raise
    
    # Retention Execution
    
    async def execute_retention_rule(
        self,
        rule: DataRetentionRule,
        dry_run: bool = False
    ) -> RetentionExecutionResult:
        """Execute a single retention rule"""
        try:
            self.logger.info(f"Executing retention rule: {rule.rule_name} (dry_run={dry_run})")
            
            # Build the query
            base_query = f"SELECT * FROM {rule.table_name}"
            conditions = []
            
            # Add retention period condition
            retention_date = datetime.utcnow() - timedelta(days=rule.retention_days)
            conditions.append(f"created_at < :retention_date")
            
            # Add custom condition if provided
            if rule.condition_sql:
                conditions.append(f"({rule.condition_sql})")
            
            # Combine conditions
            if conditions:
                query = f"{base_query} WHERE {' AND '.join(conditions)}"
            else:
                query = base_query
            
            # Count affected records
            count_query = query.replace("SELECT *", "SELECT COUNT(*)")
            count_result = await self.db.execute(
                text(count_query),
                {"retention_date": retention_date}
            )
            affected_count = count_result.scalar() or 0
            
            if dry_run:
                return RetentionExecutionResult(
                    rule_id=rule.id,
                    rule_name=rule.rule_name,
                    execution_time=datetime.utcnow(),
                    affected_records=affected_count,
                    deleted_records=0,
                    anonymized_records=0,
                    errors=[],
                    dry_run=True,
                    success=True
                )
            
            # Execute retention based on method
            deleted_count = 0
            anonymized_count = 0
            errors = []
            
            if rule.deletion_method == "hard_delete":
                deleted_count = await self._hard_delete_records(
                    rule.table_name,
                    retention_date,
                    rule.condition_sql
                )
            elif rule.deletion_method == "soft_delete":
                deleted_count = await self._soft_delete_records(
                    rule.table_name,
                    retention_date,
                    rule.condition_sql
                )
            elif rule.deletion_method == "anonymize":
                anonymized_count = await self._anonymize_records(
                    rule.table_name,
                    retention_date,
                    rule.condition_sql,
                    rule.data_category_id
                )
            else:
                errors.append(f"Unknown deletion method: {rule.deletion_method}")
            
            # Update rule statistics
            if not dry_run and not errors:
                rule.last_run = datetime.utcnow()
                rule.next_run = datetime.utcnow() + timedelta(days=rule.run_frequency_days)
                rule.last_run_deleted_count = deleted_count + anonymized_count
                rule.total_deleted_count = (rule.total_deleted_count or 0) + deleted_count + anonymized_count
                await self.db.commit()
            
            # Log execution
            await self.audit_service.log_event(
                event_type="retention_policy",
                action="rule_executed",
                resource_type="retention_rule",
                resource_id=str(rule.id),
                success=len(errors) == 0,
                metadata={
                    "rule_name": rule.rule_name,
                    "affected_records": affected_count,
                    "deleted_records": deleted_count,
                    "anonymized_records": anonymized_count,
                    "dry_run": dry_run
                },
                error_message="; ".join(errors) if errors else None
            )
            
            return RetentionExecutionResult(
                rule_id=rule.id,
                rule_name=rule.rule_name,
                execution_time=datetime.utcnow(),
                affected_records=affected_count,
                deleted_records=deleted_count,
                anonymized_records=anonymized_count,
                errors=errors,
                dry_run=dry_run,
                success=len(errors) == 0
            )
            
        except Exception as e:
            self.logger.error(f"Error executing retention rule {rule.rule_name}: {str(e)}")
            return RetentionExecutionResult(
                rule_id=rule.id,
                rule_name=rule.rule_name,
                execution_time=datetime.utcnow(),
                affected_records=0,
                deleted_records=0,
                anonymized_records=0,
                errors=[str(e)],
                dry_run=dry_run,
                success=False
            )
    
    async def _hard_delete_records(
        self,
        table_name: str,
        retention_date: datetime,
        condition_sql: Optional[str]
    ) -> int:
        """Perform hard deletion of records"""
        delete_query = f"DELETE FROM {table_name} WHERE created_at < :retention_date"
        if condition_sql:
            delete_query += f" AND ({condition_sql})"
        
        result = await self.db.execute(
            text(delete_query),
            {"retention_date": retention_date}
        )
        await self.db.commit()
        
        return result.rowcount
    
    async def _soft_delete_records(
        self,
        table_name: str,
        retention_date: datetime,
        condition_sql: Optional[str]
    ) -> int:
        """Perform soft deletion of records"""
        update_query = f"""
            UPDATE {table_name} 
            SET deleted_at = :deleted_at,
                is_deleted = true
            WHERE created_at < :retention_date
            AND (deleted_at IS NULL OR is_deleted = false)
        """
        if condition_sql:
            update_query += f" AND ({condition_sql})"
        
        result = await self.db.execute(
            text(update_query),
            {
                "retention_date": retention_date,
                "deleted_at": datetime.utcnow()
            }
        )
        await self.db.commit()
        
        return result.rowcount
    
    async def _anonymize_records(
        self,
        table_name: str,
        retention_date: datetime,
        condition_sql: Optional[str],
        category_id: Optional[UUID]
    ) -> int:
        """Anonymize records based on data mappings"""
        # Get anonymization mappings for this table/category
        mappings_query = select(DataMapping).where(
            DataMapping.table_name == table_name
        )
        if category_id:
            mappings_query = mappings_query.where(
                DataMapping.category_id == category_id
            )
        
        result = await self.db.execute(mappings_query)
        mappings = result.scalars().all()
        
        if not mappings:
            self.logger.warning(f"No anonymization mappings found for table {table_name}")
            return 0
        
        # Get records to anonymize
        select_query = f"SELECT * FROM {table_name} WHERE created_at < :retention_date"
        if condition_sql:
            select_query += f" AND ({condition_sql})"
        
        result = await self.db.execute(
            text(select_query),
            {"retention_date": retention_date}
        )
        records = result.fetchall()
        
        if not records:
            return 0
        
        # Convert to dictionaries
        columns = result.keys()
        record_dicts = [dict(zip(columns, row)) for row in records]
        
        # Apply anonymization
        anonymized_count = 0
        for record in record_dicts:
            for mapping in mappings:
                if mapping.anonymization_method and mapping.column_name in record:
                    # Apply anonymization
                    anonymized = anonymize_data(
                        {mapping.column_name: record[mapping.column_name]},
                        mapping.anonymization_method,
                        mapping.anonymization_params
                    )
                    
                    # Update record
                    update_query = f"""
                        UPDATE {table_name}
                        SET {mapping.column_name} = :new_value
                        WHERE id = :record_id
                    """
                    
                    await self.db.execute(
                        text(update_query),
                        {
                            "new_value": anonymized.get(mapping.column_name),
                            "record_id": record.get("id")
                        }
                    )
                    anonymized_count += 1
        
        await self.db.commit()
        
        # Log anonymization
        if anonymized_count > 0:
            anon_log = AnonymizationLog(
                user_id=UUID("00000000-0000-0000-0000-000000000000"),  # System user
                tables_affected={table_name: len(records)},
                total_records=len(records),
                anonymization_method="retention_policy",
                requested_by="System",
                reason=f"Data retention policy"
            )
            self.db.add(anon_log)
            await self.db.commit()
        
        return len(records)
    
    async def execute_all_due_rules(self, dry_run: bool = False) -> List[RetentionExecutionResult]:
        """Execute all retention rules that are due"""
        try:
            # Get all active rules that are due
            result = await self.db.execute(
                select(DataRetentionRule).where(
                    and_(
                        DataRetentionRule.is_active == True,
                        or_(
                            DataRetentionRule.next_run <= datetime.utcnow(),
                            DataRetentionRule.next_run.is_(None)
                        )
                    )
                )
            )
            due_rules = result.scalars().all()
            
            if not due_rules:
                self.logger.info("No retention rules due for execution")
                return []
            
            self.logger.info(f"Found {len(due_rules)} retention rules due for execution")
            
            # Execute each rule
            results = []
            for rule in due_rules:
                result = await self.execute_retention_rule(rule, dry_run)
                results.append(result)
                
                # Add delay between executions to avoid overload
                await asyncio.sleep(1)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error executing retention rules: {str(e)}")
            raise
    
    # Retention Templates
    
    async def create_default_templates(self) -> List[DataRetentionRule]:
        """Create default retention rule templates"""
        templates = [
            {
                "rule_name": "GDPR Personal Data - 7 Years",
                "description": "Retain personal data for 7 years as per GDPR requirements",
                "retention_days": 2555,  # 7 years
                "deletion_method": "anonymize",
                "run_frequency_days": 30
            },
            {
                "rule_name": "Session Data - 30 Days",
                "description": "Remove session data after 30 days",
                "table_name": "user_sessions",
                "retention_days": 30,
                "deletion_method": "hard_delete",
                "run_frequency_days": 1
            },
            {
                "rule_name": "Audit Logs - 3 Years",
                "description": "Retain audit logs for 3 years for compliance",
                "table_name": "gdpr_audit_logs",
                "retention_days": 1095,  # 3 years
                "deletion_method": "soft_delete",
                "run_frequency_days": 30
            },
            {
                "rule_name": "Temporary Files - 7 Days",
                "description": "Clean up temporary files after 7 days",
                "table_name": "temporary_files",
                "retention_days": 7,
                "deletion_method": "hard_delete",
                "run_frequency_days": 1
            },
            {
                "rule_name": "Marketing Data - 2 Years",
                "description": "Anonymize marketing data after 2 years",
                "retention_days": 730,
                "deletion_method": "anonymize",
                "run_frequency_days": 30,
                "condition_sql": "consent_type = 'marketing'"
            }
        ]
        
        created_rules = []
        for template in templates:
            try:
                # Check if rule already exists
                result = await self.db.execute(
                    select(DataRetentionRule).where(
                        DataRetentionRule.rule_name == template["rule_name"]
                    )
                )
                existing_rule = result.scalar_one_or_none()
                
                if not existing_rule:
                    rule_data = DataRetentionRuleCreate(**template)
                    rule = await self.create_retention_rule(rule_data, "System")
                    created_rules.append(rule)
                    self.logger.info(f"Created template rule: {rule.rule_name}")
            except Exception as e:
                self.logger.error(f"Error creating template rule {template['rule_name']}: {str(e)}")
        
        return created_rules
    
    # Reporting
    
    async def get_retention_statistics(self) -> Dict[str, Any]:
        """Get retention policy statistics"""
        try:
            # Get rule counts
            total_rules = await self.db.execute(
                select(func.count(DataRetentionRule.id))
            )
            total_count = total_rules.scalar() or 0
            
            active_rules = await self.db.execute(
                select(func.count(DataRetentionRule.id)).where(
                    DataRetentionRule.is_active == True
                )
            )
            active_count = active_rules.scalar() or 0
            
            # Get execution statistics
            total_deleted = await self.db.execute(
                select(func.sum(DataRetentionRule.total_deleted_count))
            )
            deleted_count = total_deleted.scalar() or 0
            
            # Get overdue rules
            overdue_rules = await self.db.execute(
                select(func.count(DataRetentionRule.id)).where(
                    and_(
                        DataRetentionRule.is_active == True,
                        DataRetentionRule.next_run < datetime.utcnow()
                    )
                )
            )
            overdue_count = overdue_rules.scalar() or 0
            
            # Get recent executions
            recent_executions = await self.db.execute(
                select(DataRetentionRule).where(
                    DataRetentionRule.last_run.isnot(None)
                ).order_by(DataRetentionRule.last_run.desc()).limit(10)
            )
            recent = recent_executions.scalars().all()
            
            return {
                "total_rules": total_count,
                "active_rules": active_count,
                "inactive_rules": total_count - active_count,
                "total_records_processed": deleted_count,
                "overdue_rules": overdue_count,
                "recent_executions": [
                    {
                        "rule_name": r.rule_name,
                        "last_run": r.last_run,
                        "records_processed": r.last_run_deleted_count
                    }
                    for r in recent
                ]
            }
            
        except Exception as e:
            self.logger.error(f"Error getting retention statistics: {str(e)}")
            raise