"""
API routes for Disaster Recovery Service
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db
from ..core.auth import get_current_user
from ..services.disaster_recovery_service import (
    DisasterRecoveryService,
    DisasterType,
    BackupType,
    FailoverMode,
    RecoveryTier
)
from ..models import schemas
from ..core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/disaster-recovery", tags=["disaster-recovery"])

# Initialize service
dr_service = DisasterRecoveryService()


@router.on_event("startup")
async def startup_event():
    """Initialize disaster recovery service on startup"""
    await dr_service.initialize()


# Disaster Recovery Plan Management
@router.post("/plans", response_model=schemas.DisasterRecoveryPlanResponse)
async def create_disaster_recovery_plan(
    plan_data: schemas.DisasterRecoveryPlanCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new disaster recovery plan"""
    try:
        plan = await dr_service.create_disaster_recovery_plan(
            name=plan_data.name,
            description=plan_data.description,
            recovery_tiers=plan_data.recovery_tiers,
            backup_strategies=plan_data.backup_strategies,
            failover_procedures=plan_data.failover_procedures,
            contact_list=plan_data.contact_list,
            metadata=plan_data.metadata
        )
        
        return schemas.DisasterRecoveryPlanResponse(
            id=str(plan.id),
            name=plan.name,
            description=plan.description,
            recovery_tiers=plan.recovery_tiers,
            contact_list=plan.contact_list,
            created_at=plan.created_at,
            is_active=plan.is_active
        )
        
    except Exception as e:
        logger.error(f"Failed to create disaster recovery plan: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/plans", response_model=List[schemas.DisasterRecoveryPlanResponse])
async def list_disaster_recovery_plans(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    is_active: Optional[bool] = Query(None),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all disaster recovery plans"""
    try:
        # In production, implement proper database query
        # This is a simplified example
        plans = []  # Fetch from database
        
        return plans
        
    except Exception as e:
        logger.error(f"Failed to list disaster recovery plans: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/plans/{plan_id}", response_model=schemas.DisasterRecoveryPlanDetail)
async def get_disaster_recovery_plan(
    plan_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed information about a disaster recovery plan"""
    try:
        plan = await dr_service._get_disaster_recovery_plan(plan_id)
        
        if not plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Disaster recovery plan {plan_id} not found"
            )
        
        # Get associated strategies and procedures
        backup_strategies = await dr_service._get_backup_strategies(plan_id)
        failover_procedures = await dr_service._get_failover_procedures(plan_id)
        recovery_metrics = await dr_service._get_recovery_metrics(plan_id)
        
        return schemas.DisasterRecoveryPlanDetail(
            id=str(plan.id),
            name=plan.name,
            description=plan.description,
            recovery_tiers=plan.recovery_tiers,
            contact_list=plan.contact_list,
            backup_strategies=backup_strategies,
            failover_procedures=failover_procedures,
            recovery_metrics=recovery_metrics,
            created_at=plan.created_at,
            updated_at=plan.updated_at,
            is_active=plan.is_active
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get disaster recovery plan: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# Backup Operations
@router.post("/backup/execute", response_model=schemas.BackupJobResponse)
async def execute_backup(
    backup_request: schemas.BackupExecuteRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Execute a backup for a specific service"""
    try:
        backup_job = await dr_service.execute_backup(
            plan_id=backup_request.plan_id,
            service_name=backup_request.service_name,
            backup_type=backup_request.backup_type
        )
        
        return schemas.BackupJobResponse(
            id=str(backup_job.id),
            plan_id=backup_job.plan_id,
            service_name=backup_job.service_name,
            backup_type=backup_job.backup_type,
            status=backup_job.status,
            start_time=backup_job.start_time,
            end_time=backup_job.end_time,
            storage_location=backup_job.storage_location,
            size_bytes=backup_job.size_bytes,
            metadata=backup_job.metadata
        )
        
    except Exception as e:
        logger.error(f"Failed to execute backup: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/backup/status/{plan_id}", response_model=schemas.BackupStatusResponse)
async def get_backup_status(
    plan_id: str,
    service_name: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get backup status for a plan or specific service"""
    try:
        backup_status = await dr_service._get_backup_status(plan_id, service_name)
        
        return schemas.BackupStatusResponse(
            plan_id=plan_id,
            service_name=service_name,
            last_backup_time=backup_status.get('last_backup_time'),
            next_backup_time=backup_status.get('next_backup_time'),
            backup_success_rate=backup_status.get('success_rate', 0),
            compliance_rate=backup_status.get('compliance_rate', 0),
            recent_backups=backup_status.get('recent_backups', [])
        )
        
    except Exception as e:
        logger.error(f"Failed to get backup status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/backup/restore", response_model=schemas.RestoreJobResponse)
async def restore_backup(
    restore_request: schemas.BackupRestoreRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Restore from a backup"""
    try:
        restore_job = await dr_service.restore_backup(
            backup_id=restore_request.backup_id,
            target_environment=restore_request.target_environment,
            validation_required=restore_request.validation_required
        )
        
        return schemas.RestoreJobResponse(
            id=str(restore_job.id),
            backup_id=restore_job.backup_id,
            status=restore_job.status,
            start_time=restore_job.start_time,
            end_time=restore_job.end_time,
            validation_results=restore_job.validation_results
        )
        
    except Exception as e:
        logger.error(f"Failed to restore backup: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# Failover Operations
@router.post("/failover/execute", response_model=schemas.FailoverEventResponse)
async def execute_failover(
    failover_request: schemas.FailoverExecuteRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Execute failover for a service"""
    try:
        failover_event = await dr_service.execute_failover(
            plan_id=failover_request.plan_id,
            service_name=failover_request.service_name,
            disaster_type=failover_request.disaster_type,
            target_region=failover_request.target_region,
            automatic=False
        )
        
        return schemas.FailoverEventResponse(
            id=str(failover_event.id),
            plan_id=failover_event.plan_id,
            service_name=failover_event.service_name,
            disaster_type=failover_event.disaster_type,
            failover_mode=failover_event.failover_mode,
            source_region=failover_event.source_region,
            target_region=failover_event.target_region,
            status=failover_event.status,
            start_time=failover_event.start_time,
            end_time=failover_event.end_time,
            steps_completed=failover_event.steps_completed
        )
        
    except Exception as e:
        logger.error(f"Failed to execute failover: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/failover/rollback/{failover_id}", response_model=schemas.RollbackResponse)
async def rollback_failover(
    failover_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Rollback a failover operation"""
    try:
        rollback_result = await dr_service.rollback_failover(failover_id)
        
        return schemas.RollbackResponse(
            failover_id=failover_id,
            status=rollback_result['status'],
            rollback_steps_completed=rollback_result['steps_completed'],
            original_state_restored=rollback_result['original_state_restored']
        )
        
    except Exception as e:
        logger.error(f"Failed to rollback failover: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# Recovery Testing
@router.post("/tests/conduct", response_model=schemas.RecoveryTestResponse)
async def conduct_recovery_test(
    test_request: schemas.RecoveryTestRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Conduct a disaster recovery test"""
    try:
        recovery_test = await dr_service.conduct_recovery_test(
            plan_id=test_request.plan_id,
            test_type=test_request.test_type,
            services=test_request.services,
            scenario=test_request.scenario
        )
        
        return schemas.RecoveryTestResponse(
            id=str(recovery_test.id),
            plan_id=recovery_test.plan_id,
            test_type=recovery_test.test_type,
            services_tested=recovery_test.services_tested,
            status=recovery_test.status,
            start_time=recovery_test.start_time,
            end_time=recovery_test.end_time,
            success_rate=recovery_test.success_rate,
            issues_found=recovery_test.issues_found,
            recommendations=recovery_test.recommendations,
            report_url=recovery_test.metadata.get('report_url')
        )
        
    except Exception as e:
        logger.error(f"Failed to conduct recovery test: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/tests/history/{plan_id}", response_model=List[schemas.RecoveryTestSummary])
async def get_test_history(
    plan_id: str,
    test_type: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get recovery test history for a plan"""
    try:
        test_history = await dr_service._get_test_history(
            plan_id,
            test_type,
            limit
        )
        
        return [
            schemas.RecoveryTestSummary(
                id=str(test.id),
                test_type=test.test_type,
                services_tested=test.services_tested,
                status=test.status,
                start_time=test.start_time,
                success_rate=test.success_rate,
                issues_count=len(test.issues_found) if test.issues_found else 0
            )
            for test in test_history
        ]
        
    except Exception as e:
        logger.error(f"Failed to get test history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# Business Continuity
@router.post("/business-continuity/plans", response_model=schemas.BusinessContinuityPlanResponse)
async def create_business_continuity_plan(
    bcp_data: schemas.BusinessContinuityPlanCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a business continuity plan"""
    try:
        bcp = await dr_service.create_business_continuity_plan(
            dr_plan_id=bcp_data.dr_plan_id,
            critical_functions=bcp_data.critical_functions,
            communication_plan=bcp_data.communication_plan,
            emergency_procedures=bcp_data.emergency_procedures,
            resource_requirements=bcp_data.resource_requirements
        )
        
        return schemas.BusinessContinuityPlanResponse(
            id=str(bcp.id),
            dr_plan_id=bcp.dr_plan_id,
            critical_functions=bcp.critical_functions,
            activation_criteria=bcp.activation_criteria,
            created_at=bcp.created_at,
            is_active=bcp.is_active
        )
        
    except Exception as e:
        logger.error(f"Failed to create business continuity plan: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# Monitoring and Dashboard
@router.get("/dashboard/{plan_id}", response_model=schemas.RecoveryDashboardResponse)
async def get_recovery_dashboard(
    plan_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get comprehensive recovery dashboard data"""
    try:
        dashboard_data = await dr_service.get_recovery_dashboard(plan_id)
        
        return schemas.RecoveryDashboardResponse(
            plan_id=dashboard_data['plan_id'],
            plan_name=dashboard_data['plan_name'],
            service_health=dashboard_data['service_health'],
            backup_status=dashboard_data['backup_status'],
            recovery_metrics=dashboard_data['recovery_metrics'],
            recent_events=dashboard_data['recent_events'],
            readiness_score=dashboard_data['readiness_score'],
            compliance_status=dashboard_data['compliance_status']
        )
        
    except Exception as e:
        logger.error(f"Failed to get recovery dashboard: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/health/{service_name}", response_model=schemas.ServiceHealthResponse)
async def get_service_health(
    service_name: str,
    current_user: dict = Depends(get_current_user)
):
    """Get health status of a specific service"""
    try:
        health_status = await dr_service._get_service_health_status(service_name)
        
        return schemas.ServiceHealthResponse(
            service_name=service_name,
            status=health_status['status'],
            last_check_time=health_status['last_check_time'],
            metrics=health_status.get('metrics', {}),
            issues=health_status.get('issues', [])
        )
        
    except Exception as e:
        logger.error(f"Failed to get service health: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# Recovery Runbooks
@router.post("/runbooks/generate", response_model=schemas.RecoveryRunbookResponse)
async def generate_recovery_runbook(
    runbook_request: schemas.RecoveryRunbookRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Generate a recovery runbook for a specific disaster scenario"""
    try:
        runbook = await dr_service.generate_recovery_runbook(
            plan_id=runbook_request.plan_id,
            disaster_type=runbook_request.disaster_type,
            affected_services=runbook_request.affected_services
        )
        
        return schemas.RecoveryRunbookResponse(
            id=runbook['id'],
            plan_id=runbook['plan_id'],
            disaster_type=runbook['disaster_type'],
            affected_services=runbook['affected_services'],
            steps=runbook['steps'],
            estimated_recovery_time_hours=runbook['estimated_recovery_time_hours'],
            printable_url=runbook['printable_url'],
            generated_at=runbook['generated_at']
        )
        
    except Exception as e:
        logger.error(f"Failed to generate recovery runbook: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/runbooks/{plan_id}", response_model=List[schemas.RecoveryRunbookSummary])
async def list_recovery_runbooks(
    plan_id: str,
    disaster_type: Optional[DisasterType] = Query(None),
    limit: int = Query(10, ge=1, le=50),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List available recovery runbooks for a plan"""
    try:
        runbooks = await dr_service._list_recovery_runbooks(
            plan_id,
            disaster_type,
            limit
        )
        
        return [
            schemas.RecoveryRunbookSummary(
                id=str(runbook.id),
                disaster_type=runbook.disaster_type,
                affected_services=runbook.affected_services,
                estimated_recovery_time_hours=runbook.estimated_recovery_time_hours,
                generated_at=runbook.generated_at
            )
            for runbook in runbooks
        ]
        
    except Exception as e:
        logger.error(f"Failed to list recovery runbooks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# Disaster Events
@router.post("/events/report", response_model=schemas.DisasterEventResponse)
async def report_disaster_event(
    event_data: schemas.DisasterEventReport,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Report a disaster event"""
    try:
        disaster_event = await dr_service.report_disaster_event(
            plan_id=event_data.plan_id,
            disaster_type=event_data.disaster_type,
            severity=event_data.severity,
            affected_services=event_data.affected_services,
            impact_description=event_data.impact_description
        )
        
        return schemas.DisasterEventResponse(
            id=str(disaster_event.id),
            plan_id=disaster_event.plan_id,
            disaster_type=disaster_event.disaster_type,
            severity=disaster_event.severity,
            affected_services=disaster_event.affected_services,
            status=disaster_event.status,
            start_time=disaster_event.start_time,
            detection_time=disaster_event.detection_time
        )
        
    except Exception as e:
        logger.error(f"Failed to report disaster event: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/events/active", response_model=List[schemas.DisasterEventSummary])
async def get_active_disaster_events(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all active disaster events"""
    try:
        active_events = await dr_service._get_active_disaster_events()
        
        return [
            schemas.DisasterEventSummary(
                id=str(event.id),
                disaster_type=event.disaster_type,
                severity=event.severity,
                affected_services=event.affected_services,
                status=event.status,
                start_time=event.start_time,
                time_to_detection=(event.detection_time - event.start_time).seconds if event.detection_time else None,
                time_to_response=(event.response_time - event.detection_time).seconds if event.response_time and event.detection_time else None
            )
            for event in active_events
        ]
        
    except Exception as e:
        logger.error(f"Failed to get active disaster events: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# Recovery Metrics
@router.get("/metrics/{plan_id}", response_model=schemas.RecoveryMetricsResponse)
async def get_recovery_metrics(
    plan_id: str,
    service_name: Optional[str] = Query(None),
    time_range_days: int = Query(30, ge=1, le=365),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get recovery metrics for a plan or specific service"""
    try:
        metrics = await dr_service._get_detailed_recovery_metrics(
            plan_id,
            service_name,
            time_range_days
        )
        
        return schemas.RecoveryMetricsResponse(
            plan_id=plan_id,
            service_name=service_name,
            time_range_days=time_range_days,
            rto_compliance=metrics['rto_compliance'],
            rpo_compliance=metrics['rpo_compliance'],
            backup_success_rate=metrics['backup_success_rate'],
            test_success_rate=metrics['test_success_rate'],
            mean_time_to_recovery=metrics['mttr'],
            service_availability=metrics['availability'],
            compliance_trends=metrics['compliance_trends']
        )
        
    except Exception as e:
        logger.error(f"Failed to get recovery metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )