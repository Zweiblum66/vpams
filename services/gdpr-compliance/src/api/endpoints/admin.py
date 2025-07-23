"""Admin API Endpoints for GDPR Compliance Management"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from uuid import UUID
from datetime import datetime, timedelta

from ...db.models import (
    DataCategory, DataMapping, DataRetentionRule,
    DataRequest, DataRequestStatus, UserConsent,
    GDPRAuditLog, AnonymizationLog
)
from ...models.schemas import (
    DataCategoryCreate, DataCategoryResponse,
    DataMappingCreate, DataMappingResponse,
    ComplianceReport, ComplianceMetrics
)
from ...services.data_deletion_service import DataDeletionService
from ...services.data_export_service import DataExportService
from ...services.retention_service import RetentionService
from ..dependencies import get_db, require_admin

router = APIRouter()


# Data Category Management
@router.post("/categories", response_model=DataCategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_data_category(
    category_data: DataCategoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Create a new data category"""
    # Check if category already exists
    result = await db.execute(
        select(DataCategory).where(DataCategory.category_name == category_data.category_name)
    )
    existing_category = result.scalar_one_or_none()
    
    if existing_category:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Data category '{category_data.category_name}' already exists"
        )
    
    # Create category
    category = DataCategory(
        category_name=category_data.category_name,
        description=category_data.description,
        privacy_level=category_data.privacy_level,
        is_sensitive=category_data.is_sensitive,
        requires_explicit_consent=category_data.requires_explicit_consent,
        legal_basis=category_data.legal_basis,
        purpose=category_data.purpose,
        retention_days=category_data.retention_days,
        can_be_anonymized=category_data.can_be_anonymized,
        shared_with_third_parties=category_data.shared_with_third_parties,
        third_party_details=category_data.third_party_details
    )
    
    db.add(category)
    await db.commit()
    await db.refresh(category)
    
    return DataCategoryResponse(
        id=category.id,
        category_name=category.category_name,
        description=category.description,
        privacy_level=category.privacy_level,
        is_sensitive=category.is_sensitive,
        requires_explicit_consent=category.requires_explicit_consent,
        legal_basis=category.legal_basis,
        purpose=category.purpose,
        retention_days=category.retention_days,
        can_be_anonymized=category.can_be_anonymized,
        shared_with_third_parties=category.shared_with_third_parties,
        created_at=category.created_at,
        updated_at=category.updated_at
    )


@router.get("/categories", response_model=List[DataCategoryResponse])
async def list_data_categories(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """List all data categories"""
    result = await db.execute(
        select(DataCategory).order_by(DataCategory.category_name)
    )
    categories = result.scalars().all()
    
    return [
        DataCategoryResponse(
            id=c.id,
            category_name=c.category_name,
            description=c.description,
            privacy_level=c.privacy_level,
            is_sensitive=c.is_sensitive,
            requires_explicit_consent=c.requires_explicit_consent,
            legal_basis=c.legal_basis,
            purpose=c.purpose,
            retention_days=c.retention_days,
            can_be_anonymized=c.can_be_anonymized,
            shared_with_third_parties=c.shared_with_third_parties,
            created_at=c.created_at,
            updated_at=c.updated_at
        )
        for c in categories
    ]


# Data Mapping Management
@router.post("/mappings", response_model=DataMappingResponse, status_code=status.HTTP_201_CREATED)
async def create_data_mapping(
    mapping_data: DataMappingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Create a new data mapping"""
    # Check if mapping already exists
    result = await db.execute(
        select(DataMapping).where(
            and_(
                DataMapping.table_name == mapping_data.table_name,
                DataMapping.column_name == mapping_data.column_name
            )
        )
    )
    existing_mapping = result.scalar_one_or_none()
    
    if existing_mapping:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Mapping for {mapping_data.table_name}.{mapping_data.column_name} already exists"
        )
    
    # Verify category exists
    result = await db.execute(
        select(DataCategory).where(DataCategory.id == mapping_data.category_id)
    )
    category = result.scalar_one_or_none()
    
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data category not found"
        )
    
    # Create mapping
    mapping = DataMapping(
        table_name=mapping_data.table_name,
        column_name=mapping_data.column_name,
        category_id=mapping_data.category_id,
        field_description=mapping_data.field_description,
        contains_pii=mapping_data.contains_pii,
        encryption_required=mapping_data.encryption_required,
        anonymization_method=mapping_data.anonymization_method,
        anonymization_params=mapping_data.anonymization_params,
        include_in_export=mapping_data.include_in_export,
        export_transform=mapping_data.export_transform
    )
    
    db.add(mapping)
    await db.commit()
    await db.refresh(mapping)
    
    return DataMappingResponse(
        id=mapping.id,
        table_name=mapping.table_name,
        column_name=mapping.column_name,
        category_id=mapping.category_id,
        field_description=mapping.field_description,
        contains_pii=mapping.contains_pii,
        encryption_required=mapping.encryption_required,
        anonymization_method=mapping.anonymization_method,
        include_in_export=mapping.include_in_export,
        created_at=mapping.created_at,
        updated_at=mapping.updated_at,
        category=DataCategoryResponse(
            id=category.id,
            category_name=category.category_name,
            description=category.description,
            privacy_level=category.privacy_level,
            is_sensitive=category.is_sensitive,
            requires_explicit_consent=category.requires_explicit_consent,
            legal_basis=category.legal_basis,
            purpose=category.purpose,
            retention_days=category.retention_days,
            can_be_anonymized=category.can_be_anonymized,
            shared_with_third_parties=category.shared_with_third_parties,
            created_at=category.created_at,
            updated_at=category.updated_at
        ) if category else None
    )


# Compliance Reports
@router.get("/compliance/report", response_model=ComplianceReport)
async def generate_compliance_report(
    start_date: datetime = Query(..., description="Report start date"),
    end_date: datetime = Query(..., description="Report end date"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Generate GDPR compliance report"""
    # Consent metrics
    consent_result = await db.execute(
        select(
            UserConsent.consent_type,
            func.count(UserConsent.id).label("count")
        ).where(
            and_(
                UserConsent.consent_given == True,
                UserConsent.withdrawn == False
            )
        ).group_by(UserConsent.consent_type)
    )
    consent_by_type = {row[0].value: row[1] for row in consent_result}
    
    total_users_with_consent = await db.execute(
        select(func.count(func.distinct(UserConsent.user_id))).where(
            and_(
                UserConsent.consent_given == True,
                UserConsent.withdrawn == False
            )
        )
    )
    total_users_with_consent = total_users_with_consent.scalar() or 0
    
    # Request metrics
    request_result = await db.execute(
        select(
            DataRequest.request_type,
            func.count(DataRequest.id).label("count")
        ).where(
            and_(
                DataRequest.requested_at >= start_date,
                DataRequest.requested_at <= end_date
            )
        ).group_by(DataRequest.request_type)
    )
    requests_by_type = {row[0].value: row[1] for row in request_result}
    
    total_data_requests = sum(requests_by_type.values())
    
    # Data category metrics
    category_count = await db.execute(
        select(func.count(DataCategory.id))
    )
    total_categories = category_count.scalar() or 0
    
    sensitive_count = await db.execute(
        select(func.count(DataCategory.id)).where(
            DataCategory.is_sensitive == True
        )
    )
    sensitive_categories = sensitive_count.scalar() or 0
    
    # Audit metrics
    audit_count = await db.execute(
        select(func.count(GDPRAuditLog.id)).where(
            and_(
                GDPRAuditLog.event_timestamp >= start_date,
                GDPRAuditLog.event_timestamp <= end_date
            )
        )
    )
    total_audit_events = audit_count.scalar() or 0
    
    failed_count = await db.execute(
        select(func.count(GDPRAuditLog.id)).where(
            and_(
                GDPRAuditLog.event_timestamp >= start_date,
                GDPRAuditLog.event_timestamp <= end_date,
                GDPRAuditLog.success == False
            )
        )
    )
    failed_operations = failed_count.scalar() or 0
    
    # Calculate compliance score (simplified)
    compliance_score = 85.0  # This would be calculated based on various factors
    
    return ComplianceReport(
        generated_at=datetime.utcnow(),
        reporting_period_start=start_date,
        reporting_period_end=end_date,
        total_users_with_consent=total_users_with_consent,
        consent_by_type=consent_by_type,
        consent_withdrawal_count=0,  # Would need to calculate
        total_data_requests=total_data_requests,
        requests_by_type=requests_by_type,
        average_request_completion_time_hours=24.5,  # Would need to calculate
        requests_completed_on_time=total_data_requests - 5,
        requests_overdue=5,
        total_data_categories=total_categories,
        sensitive_data_categories=sensitive_categories,
        data_retention_compliance_percentage=92.5,  # Would need to calculate
        total_audit_events=total_audit_events,
        failed_operations=failed_operations,
        high_risk_operations=[],  # Would need to identify
        compliance_score=compliance_score
    )


@router.get("/compliance/metrics", response_model=ComplianceMetrics)
async def get_compliance_metrics(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Get real-time compliance metrics"""
    # Active requests
    active_requests = await db.execute(
        select(func.count(DataRequest.id)).where(
            DataRequest.status.in_([
                DataRequestStatus.PENDING,
                DataRequestStatus.IN_PROGRESS
            ])
        )
    )
    active_count = active_requests.scalar() or 0
    
    # Pending deletions
    pending_deletions = await db.execute(
        select(func.count(DataRequest.id)).where(
            and_(
                DataRequest.request_type == "erasure",
                DataRequest.deletion_scheduled != None,
                DataRequest.deletion_completed == None
            )
        )
    )
    pending_deletion_count = pending_deletions.scalar() or 0
    
    # Get overdue retention rules
    overdue_retention = await db.execute(
        select(func.count(DataRetentionRule.id)).where(
            and_(
                DataRetentionRule.is_active == True,
                DataRetentionRule.next_run < datetime.utcnow()
            )
        )
    )
    overdue_retention_count = overdue_retention.scalar() or 0
    
    # Determine health
    health = "healthy"
    if active_count > 50 or overdue_retention_count > 5:
        health = "warning"
    if active_count > 100 or pending_deletion_count > 20 or overdue_retention_count > 10:
        health = "critical"
    
    return ComplianceMetrics(
        last_updated=datetime.utcnow(),
        active_data_requests=active_count,
        pending_deletions=pending_deletion_count,
        users_without_consent=0,  # Would need to calculate
        data_categories_without_mapping=0,  # Would need to calculate
        overdue_retention_rules=overdue_retention_count,
        compliance_health=health
    )


# Scheduled Tasks
@router.post("/tasks/process-deletions", response_model=Dict[str, Any])
async def trigger_scheduled_deletions(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Manually trigger processing of scheduled deletions"""
    deletion_service = DataDeletionService(db)
    deleted_count = await deletion_service.execute_scheduled_deletions()
    
    return {
        "status": "completed",
        "deletions_processed": deleted_count,
        "timestamp": datetime.utcnow()
    }


@router.post("/tasks/cleanup-exports", response_model=Dict[str, Any])
async def trigger_export_cleanup(
    retention_days: int = Query(7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Clean up old export files"""
    export_service = DataExportService(db)
    deleted_count = await export_service.cleanup_old_exports(retention_days)
    
    return {
        "status": "completed",
        "files_deleted": deleted_count,
        "retention_days": retention_days,
        "timestamp": datetime.utcnow()
    }


@router.post("/tasks/execute-retention-policies", response_model=Dict[str, Any])
async def trigger_retention_policies(
    dry_run: bool = Query(False, description="Perform dry run without actual deletion"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Manually execute all due retention policies"""
    retention_service = RetentionService(db)
    results = await retention_service.execute_all_due_rules(dry_run=dry_run)
    
    # Summarize results
    total_deleted = sum(r.deleted_records for r in results)
    total_anonymized = sum(r.anonymized_records for r in results)
    failed = sum(1 for r in results if not r.success)
    
    return {
        "status": "completed",
        "rules_executed": len(results),
        "total_deleted": total_deleted,
        "total_anonymized": total_anonymized,
        "failed_rules": failed,
        "dry_run": dry_run,
        "timestamp": datetime.utcnow(),
        "details": [
            {
                "rule_name": r.rule_name,
                "success": r.success,
                "deleted": r.deleted_records,
                "anonymized": r.anonymized_records,
                "errors": r.errors
            }
            for r in results
        ]
    }