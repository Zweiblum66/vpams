"""
Rights Management Service API Routes
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
from datetime import date, datetime
import uuid

from ..core.database import get_db
from ..core.auth import get_current_user
from ..core.logger import get_logger
from ..models.schemas import (
    # Rights Party
    RightsPartyCreate, RightsPartyUpdate, RightsPartyResponse,
    
    # License
    LicenseCreate, LicenseUpdate, LicenseResponse, LicenseFilter,
    
    # Usage Record
    UsageRecordCreate, UsageRecordUpdate, UsageRecordResponse, UsageRecordFilter,
    
    # Compliance Alert
    ComplianceAlertCreate, ComplianceAlertUpdate, ComplianceAlertResponse,
    
    # Rights Report
    RightsReportCreate, RightsReportUpdate, RightsReportResponse,
    
    # Analytics
    UsageAnalytics, LicenseAnalytics,
    
    # Compliance
    RightsComplianceCheck, RightsComplianceResult,
    
    # Bulk Operations
    BulkLicenseCreate, BulkLicenseUpdate, BulkUsageRecordCreate, BulkOperationResult,
    
    # Pagination
    PaginatedResponse,
    
    # User
    User
)
from ..models.audit_schemas import (
    AuditTrailCreate, AuditTrailResponse, AuditTrailFilter,
    AuditTrailStats, AuditTrailExport, AuditContext,
    AuditRetentionPolicy, AuditBatch
)
from ..services.rights_service import RightsService
from ..services.compliance_service import ComplianceService
from ..services.analytics_service import AnalyticsService
from ..services.report_service import ReportService
from ..services.audit_service import AuditService

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/rights", tags=["rights"])

# Rights Party routes
@router.post("/parties", response_model=RightsPartyResponse, status_code=status.HTTP_201_CREATED)
async def create_rights_party(
    party: RightsPartyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new rights party"""
    try:
        logger.info(f"Creating rights party: {party.name}")
        
        rights_service = RightsService(db)
        result = await rights_service.create_rights_party(party, current_user)
        
        logger.info(f"Rights party created: {result.id}")
        return result
        
    except Exception as e:
        logger.error(f"Failed to create rights party: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create rights party: {str(e)}"
        )


@router.get("/parties", response_model=PaginatedResponse)
async def get_rights_parties(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    party_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get rights parties with pagination and filtering"""
    try:
        rights_service = RightsService(db)
        result = await rights_service.get_rights_parties(
            page=page,
            limit=limit,
            party_type=party_type,
            search=search,
            is_active=is_active
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to get rights parties: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get rights parties: {str(e)}"
        )


@router.get("/parties/{party_id}", response_model=RightsPartyResponse)
async def get_rights_party(
    party_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific rights party"""
    try:
        rights_service = RightsService(db)
        result = await rights_service.get_rights_party(party_id)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Rights party not found"
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get rights party: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get rights party: {str(e)}"
        )


@router.put("/parties/{party_id}", response_model=RightsPartyResponse)
async def update_rights_party(
    party_id: str,
    party_update: RightsPartyUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a rights party"""
    try:
        rights_service = RightsService(db)
        result = await rights_service.update_rights_party(party_id, party_update, current_user)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Rights party not found"
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update rights party: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update rights party: {str(e)}"
        )


@router.delete("/parties/{party_id}")
async def delete_rights_party(
    party_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a rights party"""
    try:
        rights_service = RightsService(db)
        result = await rights_service.delete_rights_party(party_id, current_user)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Rights party not found"
            )
        
        return {"message": "Rights party deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete rights party: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete rights party: {str(e)}"
        )


# License routes
@router.post("/licenses", response_model=LicenseResponse, status_code=status.HTTP_201_CREATED)
async def create_license(
    license_data: LicenseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new license"""
    try:
        logger.info(f"Creating license: {license_data.license_number}")
        
        rights_service = RightsService(db)
        result = await rights_service.create_license(license_data, current_user)
        
        logger.info(f"License created: {result.id}")
        return result
        
    except Exception as e:
        logger.error(f"Failed to create license: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create license: {str(e)}"
        )


@router.get("/licenses", response_model=PaginatedResponse)
async def get_licenses(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    license_filter: LicenseFilter = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get licenses with pagination and filtering"""
    try:
        rights_service = RightsService(db)
        result = await rights_service.get_licenses(
            page=page,
            limit=limit,
            license_filter=license_filter
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to get licenses: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get licenses: {str(e)}"
        )


@router.get("/licenses/{license_id}", response_model=LicenseResponse)
async def get_license(
    license_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific license"""
    try:
        rights_service = RightsService(db)
        result = await rights_service.get_license(license_id)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="License not found"
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get license: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get license: {str(e)}"
        )


@router.put("/licenses/{license_id}", response_model=LicenseResponse)
async def update_license(
    license_id: str,
    license_update: LicenseUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a license"""
    try:
        rights_service = RightsService(db)
        result = await rights_service.update_license(license_id, license_update, current_user)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="License not found"
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update license: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update license: {str(e)}"
        )


@router.delete("/licenses/{license_id}")
async def delete_license(
    license_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a license"""
    try:
        rights_service = RightsService(db)
        result = await rights_service.delete_license(license_id, current_user)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="License not found"
            )
        
        return {"message": "License deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete license: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete license: {str(e)}"
        )


# Usage Record routes
@router.post("/usage", response_model=UsageRecordResponse, status_code=status.HTTP_201_CREATED)
async def create_usage_record(
    usage_data: UsageRecordCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new usage record"""
    try:
        logger.info(f"Creating usage record for license: {usage_data.license_id}")
        
        rights_service = RightsService(db)
        result = await rights_service.create_usage_record(usage_data, current_user)
        
        logger.info(f"Usage record created: {result.id}")
        return result
        
    except Exception as e:
        logger.error(f"Failed to create usage record: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create usage record: {str(e)}"
        )


@router.get("/usage", response_model=PaginatedResponse)
async def get_usage_records(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    usage_filter: UsageRecordFilter = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get usage records with pagination and filtering"""
    try:
        rights_service = RightsService(db)
        result = await rights_service.get_usage_records(
            page=page,
            limit=limit,
            usage_filter=usage_filter
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to get usage records: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get usage records: {str(e)}"
        )


@router.get("/usage/{usage_id}", response_model=UsageRecordResponse)
async def get_usage_record(
    usage_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific usage record"""
    try:
        rights_service = RightsService(db)
        result = await rights_service.get_usage_record(usage_id)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usage record not found"
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get usage record: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get usage record: {str(e)}"
        )


# Compliance routes
@router.post("/compliance/check", response_model=RightsComplianceResult)
async def check_compliance(
    compliance_check: RightsComplianceCheck,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Check compliance for a specific usage"""
    try:
        compliance_service = ComplianceService(db)
        result = await compliance_service.check_compliance(compliance_check)
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to check compliance: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check compliance: {str(e)}"
        )


@router.get("/compliance/alerts", response_model=PaginatedResponse)
async def get_compliance_alerts(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    severity: Optional[str] = Query(None),
    is_resolved: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get compliance alerts"""
    try:
        compliance_service = ComplianceService(db)
        result = await compliance_service.get_compliance_alerts(
            page=page,
            limit=limit,
            severity=severity,
            is_resolved=is_resolved
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to get compliance alerts: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get compliance alerts: {str(e)}"
        )


@router.put("/compliance/alerts/{alert_id}/resolve")
async def resolve_compliance_alert(
    alert_id: str,
    resolution_notes: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Resolve a compliance alert"""
    try:
        compliance_service = ComplianceService(db)
        result = await compliance_service.resolve_alert(alert_id, resolution_notes, current_user)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Compliance alert not found"
            )
        
        return {"message": "Compliance alert resolved successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resolve compliance alert: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resolve compliance alert: {str(e)}"
        )


# Analytics routes
@router.get("/analytics/usage", response_model=UsageAnalytics)
async def get_usage_analytics(
    start_date: date = Query(...),
    end_date: date = Query(...),
    asset_id: Optional[str] = Query(None),
    license_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get usage analytics"""
    try:
        analytics_service = AnalyticsService(db)
        result = await analytics_service.get_usage_analytics(
            start_date=start_date,
            end_date=end_date,
            asset_id=asset_id,
            license_id=license_id
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to get usage analytics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get usage analytics: {str(e)}"
        )


@router.get("/analytics/licenses", response_model=LicenseAnalytics)
async def get_license_analytics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get license analytics"""
    try:
        analytics_service = AnalyticsService(db)
        result = await analytics_service.get_license_analytics()
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to get license analytics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get license analytics: {str(e)}"
        )


# Report routes
@router.post("/reports", response_model=RightsReportResponse, status_code=status.HTTP_201_CREATED)
async def create_report(
    report_data: RightsReportCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new rights report"""
    try:
        report_service = ReportService(db)
        result = await report_service.create_report(report_data, current_user)
        
        # Generate report in background
        background_tasks.add_task(
            report_service.generate_report,
            result.id,
            current_user
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to create report: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create report: {str(e)}"
        )


@router.get("/reports", response_model=PaginatedResponse)
async def get_reports(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    report_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get rights reports"""
    try:
        report_service = ReportService(db)
        result = await report_service.get_reports(
            page=page,
            limit=limit,
            report_type=report_type,
            status=status,
            created_by=current_user.user_id
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to get reports: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get reports: {str(e)}"
        )


@router.get("/reports/{report_id}", response_model=RightsReportResponse)
async def get_report(
    report_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific rights report"""
    try:
        report_service = ReportService(db)
        result = await report_service.get_report(report_id)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Report not found"
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get report: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get report: {str(e)}"
        )


@router.get("/reports/{report_id}/download")
async def download_report(
    report_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Download a rights report file"""
    try:
        report_service = ReportService(db)
        result = await report_service.download_report(report_id, current_user)
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to download report: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to download report: {str(e)}"
        )


# Bulk Operations
@router.post("/bulk/licenses", response_model=BulkOperationResult)
async def bulk_create_licenses(
    bulk_data: BulkLicenseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Bulk create licenses"""
    try:
        rights_service = RightsService(db)
        result = await rights_service.bulk_create_licenses(bulk_data, current_user)
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to bulk create licenses: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to bulk create licenses: {str(e)}"
        )


@router.put("/bulk/licenses", response_model=BulkOperationResult)
async def bulk_update_licenses(
    bulk_data: BulkLicenseUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Bulk update licenses"""
    try:
        rights_service = RightsService(db)
        result = await rights_service.bulk_update_licenses(bulk_data, current_user)
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to bulk update licenses: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to bulk update licenses: {str(e)}"
        )


@router.post("/bulk/usage", response_model=BulkOperationResult)
async def bulk_create_usage_records(
    bulk_data: BulkUsageRecordCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Bulk create usage records"""
    try:
        rights_service = RightsService(db)
        result = await rights_service.bulk_create_usage_records(bulk_data, current_user)
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to bulk create usage records: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to bulk create usage records: {str(e)}"
        )


# Health check
@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "rights-management",
        "version": "1.0.0"
    }


# Asset-specific routes
@router.get("/assets/{asset_id}/licenses", response_model=List[LicenseResponse])
async def get_asset_licenses(
    asset_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all licenses for a specific asset"""
    try:
        rights_service = RightsService(db)
        result = await rights_service.get_asset_licenses(asset_id)
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to get asset licenses: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get asset licenses: {str(e)}"
        )


@router.get("/assets/{asset_id}/usage", response_model=List[UsageRecordResponse])
async def get_asset_usage(
    asset_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all usage records for a specific asset"""
    try:
        rights_service = RightsService(db)
        result = await rights_service.get_asset_usage(asset_id)
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to get asset usage: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get asset usage: {str(e)}"
        )


@router.get("/assets/{asset_id}/compliance", response_model=RightsComplianceResult)
async def check_asset_compliance(
    asset_id: str,
    usage_type: str = Query(...),
    country: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Check compliance for an asset"""
    try:
        compliance_check = RightsComplianceCheck(
            asset_id=asset_id,
            usage_type=usage_type,
            usage_date=datetime.utcnow(),
            country=country
        )
        
        compliance_service = ComplianceService(db)
        result = await compliance_service.check_compliance(compliance_check)
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to check asset compliance: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check asset compliance: {str(e)}"
        )


# Audit Trail routes
@router.get("/audit", response_model=List[AuditTrailResponse])
async def get_audit_trails(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    filter_params: AuditTrailFilter = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get audit trails with filtering and pagination"""
    try:
        audit_service = AuditService()
        audit_trails, total = await audit_service.get_audit_trails(
            db, filter_params, skip=skip, limit=limit
        )
        
        # Add pagination headers
        return audit_trails
        
    except Exception as e:
        logger.error(f"Failed to get audit trails: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get audit trails: {str(e)}"
        )


@router.get("/audit/{audit_id}", response_model=AuditTrailResponse)
async def get_audit_trail(
    audit_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific audit trail entry"""
    try:
        audit_service = AuditService()
        audit_trail = await audit_service.get_audit_trail(db, audit_id)
        
        return audit_trail
        
    except Exception as e:
        logger.error(f"Failed to get audit trail: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get audit trail: {str(e)}"
        )


@router.post("/audit/batch", response_model=List[AuditTrailResponse])
async def create_audit_batch(
    audit_batch: AuditBatch,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create multiple audit trail entries in a batch"""
    try:
        audit_service = AuditService()
        audit_trails = await audit_service.create_audit_batch(db, audit_batch)
        
        return audit_trails
        
    except Exception as e:
        logger.error(f"Failed to create audit batch: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create audit batch: {str(e)}"
        )


@router.get("/audit/stats", response_model=AuditTrailStats)
async def get_audit_stats(
    filter_params: AuditTrailFilter = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get audit trail statistics"""
    try:
        audit_service = AuditService()
        stats = await audit_service.get_audit_stats(db, filter_params)
        
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get audit stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get audit stats: {str(e)}"
        )


@router.post("/audit/export")
async def export_audit_trails(
    export_params: AuditTrailExport,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Export audit trails to specified format"""
    try:
        audit_service = AuditService()
        export_data = await audit_service.export_audit_trails(db, export_params)
        
        # Determine content type based on format
        content_type_map = {
            "csv": "text/csv",
            "json": "application/json",
            "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        }
        content_type = content_type_map.get(export_params.format, "application/octet-stream")
        
        # Determine filename
        filename = f"audit_trails_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.{export_params.format}"
        if export_params.format == "excel":
            filename = filename.replace(".excel", ".xlsx")
        
        from fastapi.responses import Response
        return Response(
            content=export_data,
            media_type=content_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to export audit trails: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export audit trails: {str(e)}"
        )


@router.post("/audit/archive")
async def archive_audit_trails(
    retention_policy: AuditRetentionPolicy,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Archive old audit trails based on retention policy"""
    try:
        # Check if user has admin permissions
        if "admin" not in current_user.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin permission required for archiving"
            )
        
        audit_service = AuditService()
        archived_count = await audit_service.archive_audit_trails(db, retention_policy)
        
        return {
            "message": f"Successfully archived {archived_count} audit trail entries",
            "archived_count": archived_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to archive audit trails: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to archive audit trails: {str(e)}"
        )


@router.delete("/audit/archive/cleanup")
async def cleanup_archived_trails(
    retention_policy: AuditRetentionPolicy,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete old archived audit trails based on retention policy"""
    try:
        # Check if user has admin permissions
        if "admin" not in current_user.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin permission required for cleanup"
            )
        
        audit_service = AuditService()
        deleted_count = await audit_service.cleanup_archived_trails(db, retention_policy)
        
        return {
            "message": f"Successfully deleted {deleted_count} archived audit trail entries",
            "deleted_count": deleted_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cleanup archived trails: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cleanup archived trails: {str(e)}"
        )