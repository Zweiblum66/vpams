from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import logging

from ..db.base import get_db
from ..models.schemas import (
    QuantumMetrics, AlgorithmStats, SecurityAssessment,
    MigrationRequest, MigrationResponse
)
from ..services.analytics import QuantumAnalyticsService
from ..services.key_management import KeyManagementService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/quantum/analytics", tags=["quantum-analytics"])

# Service instances
analytics_service = QuantumAnalyticsService()
key_service = KeyManagementService()

# Dependency for user authentication (placeholder)
async def get_current_user():
    # In production, implement proper authentication
    return {"id": "user123", "role": "admin"}

@router.get("/metrics", response_model=QuantumMetrics)
async def get_quantum_metrics(
    owner_id: Optional[str] = Query(None, description="Filter by owner ID"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get comprehensive quantum encryption metrics."""
    try:
        # Non-admin users can only see their own metrics
        if current_user["role"] != "admin":
            owner_id = current_user["id"]
            
        return await analytics_service.get_metrics(db, owner_id)
        
    except Exception as e:
        logger.error(f"Failed to get metrics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get metrics: {str(e)}"
        )

@router.get("/algorithms/stats")
async def get_algorithm_statistics(
    limit: int = Query(10, ge=1, le=50, description="Number of algorithms to return"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get usage statistics for quantum algorithms."""
    try:
        stats = await analytics_service.get_algorithm_stats(db, limit)
        return {"algorithms": stats}
        
    except Exception as e:
        logger.error(f"Failed to get algorithm stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get algorithm stats: {str(e)}"
        )

@router.get("/security/assessment", response_model=SecurityAssessment)
async def get_security_assessment(
    owner_id: Optional[str] = Query(None, description="Filter by owner ID"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get comprehensive security assessment of quantum encryption usage."""
    try:
        # Non-admin users can only see their own assessment
        if current_user["role"] != "admin":
            owner_id = current_user["id"]
            
        return await analytics_service.get_security_assessment(db, owner_id)
        
    except Exception as e:
        logger.error(f"Failed to get security assessment: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get security assessment: {str(e)}"
        )

@router.get("/operations/trends")
async def get_operation_trends(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    operation_type: Optional[str] = Query(None, description="Filter by operation type"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get operation trends over time."""
    try:
        return await analytics_service.get_operation_trends(db, days, operation_type)
        
    except Exception as e:
        logger.error(f"Failed to get operation trends: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get operation trends: {str(e)}"
        )

@router.get("/keys/expiring")
async def get_expiring_keys(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get list of keys nearing expiration."""
    try:
        keys = await key_service.check_key_expiration(db)
        
        # Filter by owner for non-admin users
        if current_user["role"] != "admin":
            keys = [k for k in keys if k.owner_id == current_user["id"]]
            
        return {
            "expiring_keys": [
                {
                    "key_id": k.key_id,
                    "algorithm": k.algorithm,
                    "expires_at": k.expires_at,
                    "days_remaining": (k.expires_at - datetime.utcnow()).days
                }
                for k in keys
            ],
            "total": len(keys)
        }
        
    except Exception as e:
        logger.error(f"Failed to get expiring keys: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get expiring keys: {str(e)}"
        )

@router.get("/keys/metrics")
async def get_key_metrics(
    owner_id: Optional[str] = Query(None, description="Filter by owner ID"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get detailed key management metrics."""
    try:
        # Non-admin users can only see their own metrics
        if current_user["role"] != "admin":
            owner_id = current_user["id"]
            
        return await key_service.get_key_metrics(db, owner_id)
        
    except Exception as e:
        logger.error(f"Failed to get key metrics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get key metrics: {str(e)}"
        )

@router.post("/migration/plan", response_model=MigrationResponse)
async def plan_algorithm_migration(
    request: MigrationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Plan a migration from one algorithm to another."""
    try:
        # Only admins can plan migrations
        if current_user["role"] != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can plan algorithm migrations"
            )
            
        return await key_service.plan_migration(
            db=db,
            source_algorithm=request.source_algorithm,
            target_algorithm=request.target_algorithm,
            key_pattern=request.key_pattern
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to plan migration: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to plan migration: {str(e)}"
        )

@router.post("/cleanup/expired")
async def cleanup_expired_keys(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Mark expired keys as expired."""
    try:
        # Only admins can run cleanup
        if current_user["role"] != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can run key cleanup"
            )
            
        count = await key_service.cleanup_expired_keys(db)
        
        return {
            "message": f"Marked {count} keys as expired",
            "expired_count": count,
            "timestamp": datetime.utcnow()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cleanup expired keys: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cleanup expired keys: {str(e)}"
        )

@router.get("/dashboard/summary")
async def get_dashboard_summary(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get a summary for quantum encryption dashboard."""
    try:
        owner_id = None if current_user["role"] == "admin" else current_user["id"]
        
        # Get various metrics
        metrics = await analytics_service.get_metrics(db, owner_id)
        assessment = await analytics_service.get_security_assessment(db, owner_id)
        key_metrics = await key_service.get_key_metrics(db, owner_id)
        
        return {
            "overview": {
                "total_keys": metrics.total_keys,
                "active_keys": metrics.active_keys,
                "operations_today": metrics.operations_today,
                "quantum_readiness": assessment.quantum_readiness,
                "security_score": assessment.overall_score
            },
            "key_distribution": key_metrics["algorithm_counts"],
            "status_distribution": key_metrics["status_counts"],
            "performance": {
                "average_operation_time_ms": metrics.average_operation_time_ms,
                "most_used_algorithm": metrics.most_used_algorithm
            },
            "compliance": {
                "rotation_compliance": metrics.key_rotation_compliance,
                "keys_expiring_soon": key_metrics["keys_expiring_soon"]
            },
            "alerts": {
                "vulnerabilities": len(assessment.vulnerabilities),
                "recommendations": len(assessment.recommendations)
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get dashboard summary: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get dashboard summary: {str(e)}"
        )