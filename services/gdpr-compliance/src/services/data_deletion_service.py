"""Data Deletion Service for GDPR Right to be Forgotten"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, update, text, and_

from ..db.models import (
    DataRequest, DataRequestStatus, DataMapping,
    DataCategory, AnonymizationLog
)
from ..models.schemas import DataDeletionRequest
from ..utils.anonymization import anonymize_data
from .audit_service import AuditService
from ..core.config import settings

logger = logging.getLogger(__name__)


class DataDeletionService:
    """Service for handling GDPR data deletion requests"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.logger = logging.getLogger(__name__)
        self.audit_service = AuditService(db)
    
    async def process_deletion_request(
        self,
        request_id: str
    ) -> None:
        """Process a data deletion request"""
        try:
            # Get request
            result = await self.db.execute(
                select(DataRequest).where(DataRequest.request_id == request_id)
            )
            data_request = result.scalar_one_or_none()
            
            if not data_request:
                self.logger.error(f"Data request {request_id} not found")
                return
            
            # Update status
            data_request.status = DataRequestStatus.IN_PROGRESS
            data_request.processed_at = datetime.utcnow()
            await self.db.commit()
            
            # Get deletion configuration
            deletion_config = data_request.request_data or {}
            immediate = deletion_config.get("immediate", False)
            categories = deletion_config.get("categories", None)
            
            if immediate:
                # Immediate deletion
                await self._delete_user_data(
                    user_id=data_request.user_id,
                    categories=categories
                )
            else:
                # Schedule deletion after grace period
                deletion_date = datetime.utcnow() + timedelta(
                    days=settings.gdpr_deletion_grace_period_days
                )
                data_request.deletion_scheduled = deletion_date
                await self.db.commit()
                
                self.logger.info(
                    f"Deletion scheduled for user {data_request.user_id} "
                    f"on {deletion_date.isoformat()}"
                )
            
            # Update request status
            data_request.status = DataRequestStatus.COMPLETED
            await self.db.commit()
            
        except Exception as e:
            self.logger.error(f"Error processing deletion request: {str(e)}")
            
            # Update request with error
            if data_request:
                data_request.status = DataRequestStatus.FAILED
                data_request.error_message = str(e)
                await self.db.commit()
    
    async def _delete_user_data(
        self,
        user_id: UUID,
        categories: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Delete or anonymize user data"""
        try:
            # Get data mappings
            mappings = await self._get_deletion_mappings(categories)
            
            tables_affected = {}
            total_records = 0
            
            for mapping in mappings:
                if mapping.category and mapping.category.can_be_anonymized:
                    # Anonymize data
                    count = await self._anonymize_table_data(
                        user_id=user_id,
                        mapping=mapping
                    )
                else:
                    # Hard delete data
                    count = await self._delete_table_data(
                        user_id=user_id,
                        mapping=mapping
                    )
                
                if count > 0:
                    tables_affected[mapping.table_name] = count
                    total_records += count
            
            # Log anonymization
            if total_records > 0:
                anon_log = AnonymizationLog(
                    user_id=user_id,
                    tables_affected=tables_affected,
                    total_records=total_records,
                    anonymization_method="mixed",
                    partial_anonymization=bool(categories),
                    requested_by="GDPR Request",
                    reason="Right to be forgotten"
                )
                self.db.add(anon_log)
                await self.db.commit()
            
            # Log audit event
            await self.audit_service.log_data_deletion(
                user_id=user_id,
                tables_affected=tables_affected,
                total_records=total_records
            )
            
            return {
                "tables_affected": tables_affected,
                "total_records": total_records,
                "deletion_completed": datetime.utcnow()
            }
            
        except Exception as e:
            self.logger.error(f"Error deleting user data: {str(e)}")
            raise
    
    async def _get_deletion_mappings(
        self,
        categories: Optional[List[str]] = None
    ) -> List[DataMapping]:
        """Get data mappings for deletion"""
        query = select(DataMapping).join(DataCategory)
        
        if categories:
            query = query.where(DataCategory.category_name.in_(categories))
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def _delete_table_data(
        self,
        user_id: UUID,
        mapping: DataMapping
    ) -> int:
        """Hard delete data from a table"""
        try:
            # Build delete query
            query = f"DELETE FROM {mapping.table_name} WHERE user_id = :user_id"
            
            # Execute deletion
            result = await self.db.execute(
                text(query),
                {"user_id": str(user_id)}
            )
            
            await self.db.commit()
            return result.rowcount
            
        except Exception as e:
            self.logger.error(
                f"Error deleting from {mapping.table_name}: {str(e)}"
            )
            return 0
    
    async def _anonymize_table_data(
        self,
        user_id: UUID,
        mapping: DataMapping
    ) -> int:
        """Anonymize data in a table"""
        try:
            # Get records to anonymize
            query = f"SELECT * FROM {mapping.table_name} WHERE user_id = :user_id"
            result = await self.db.execute(
                text(query),
                {"user_id": str(user_id)}
            )
            records = result.fetchall()
            
            if not records:
                return 0
            
            # Get column names
            columns = result.keys()
            records_dict = [dict(zip(columns, row)) for row in records]
            
            # Apply anonymization
            anonymized_count = 0
            for record in records_dict:
                # Anonymize based on mapping configuration
                if mapping.anonymization_method:
                    anonymized = anonymize_data(
                        record,
                        mapping.anonymization_method,
                        mapping.anonymization_params
                    )
                    
                    # Update record
                    update_parts = []
                    update_values = {"record_id": record.get("id")}
                    
                    for field, value in anonymized.items():
                        if field != "id" and value != record.get(field):
                            update_parts.append(f"{field} = :{field}")
                            update_values[field] = value
                    
                    if update_parts:
                        update_query = (
                            f"UPDATE {mapping.table_name} "
                            f"SET {', '.join(update_parts)} "
                            f"WHERE id = :record_id"
                        )
                        
                        await self.db.execute(
                            text(update_query),
                            update_values
                        )
                        anonymized_count += 1
            
            await self.db.commit()
            return anonymized_count
            
        except Exception as e:
            self.logger.error(
                f"Error anonymizing {mapping.table_name}: {str(e)}"
            )
            return 0
    
    async def execute_scheduled_deletions(self) -> int:
        """Execute scheduled deletions that are due"""
        try:
            # Find due deletions
            result = await self.db.execute(
                select(DataRequest).where(
                    and_(
                        DataRequest.request_type == "erasure",
                        DataRequest.status == DataRequestStatus.COMPLETED,
                        DataRequest.deletion_scheduled <= datetime.utcnow(),
                        DataRequest.deletion_completed.is_(None)
                    )
                )
            )
            due_requests = result.scalars().all()
            
            deleted_count = 0
            
            for request in due_requests:
                try:
                    # Execute deletion
                    deletion_result = await self._delete_user_data(
                        user_id=request.user_id,
                        categories=request.request_data.get("categories")
                        if request.request_data else None
                    )
                    
                    # Mark as completed
                    request.deletion_completed = datetime.utcnow()
                    request.result_data = deletion_result
                    await self.db.commit()
                    
                    deleted_count += 1
                    
                except Exception as e:
                    self.logger.error(
                        f"Error executing scheduled deletion for request "
                        f"{request.request_id}: {str(e)}"
                    )
            
            return deleted_count
            
        except Exception as e:
            self.logger.error(f"Error executing scheduled deletions: {str(e)}")
            return 0
    
    async def verify_deletion(
        self,
        user_id: UUID,
        sample_tables: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Verify that user data has been deleted/anonymized"""
        verification_results = {
            "verified": True,
            "tables_checked": {},
            "records_found": 0,
            "verification_timestamp": datetime.utcnow()
        }
        
        try:
            # Get mappings to check
            mappings = await self._get_deletion_mappings()
            
            for mapping in mappings:
                if sample_tables and mapping.table_name not in sample_tables:
                    continue
                
                # Check for remaining records
                query = (
                    f"SELECT COUNT(*) as count FROM {mapping.table_name} "
                    f"WHERE user_id = :user_id"
                )
                
                result = await self.db.execute(
                    text(query),
                    {"user_id": str(user_id)}
                )
                count = result.scalar()
                
                if count > 0:
                    verification_results["verified"] = False
                    verification_results["records_found"] += count
                
                verification_results["tables_checked"][mapping.table_name] = count
            
            # Log verification in anonymization log
            result = await self.db.execute(
                select(AnonymizationLog).where(
                    AnonymizationLog.user_id == user_id
                ).order_by(AnonymizationLog.anonymized_at.desc())
            )
            anon_log = result.scalar_one_or_none()
            
            if anon_log:
                anon_log.verified = verification_results["verified"]
                anon_log.verification_method = "table_scan"
                anon_log.verification_timestamp = datetime.utcnow()
                await self.db.commit()
            
            return verification_results
            
        except Exception as e:
            self.logger.error(f"Error verifying deletion: {str(e)}")
            verification_results["verified"] = False
            verification_results["error"] = str(e)
            return verification_results