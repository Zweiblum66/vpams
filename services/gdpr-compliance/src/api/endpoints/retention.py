"""Data Retention Policy API Endpoints"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from datetime import datetime

from ...db.models import DataRetentionRule
from ...models.schemas import (
    DataRetentionRuleCreate, DataRetentionRuleUpdate,
    DataRetentionRuleResponse, RetentionExecutionResult,
    RetentionStatistics
)
from ...services.retention_service import RetentionService
from ..dependencies import get_db, get_current_user, require_admin

router = APIRouter()


@router.post("/rules", response_model=DataRetentionRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_retention_rule(
    rule_data: DataRetentionRuleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Create a new data retention rule (admin only)"""
    retention_service = RetentionService(db)
    
    try:
        rule = await retention_service.create_retention_rule(
            rule_data,
            created_by=current_user.get("email", "admin")
        )
        
        return DataRetentionRuleResponse(
            id=rule.id,
            rule_name=rule.rule_name,
            description=rule.description,
            table_name=rule.table_name,
            data_category_id=rule.data_category_id,
            condition_sql=rule.condition_sql,
            retention_days=rule.retention_days,
            deletion_method=rule.deletion_method,
            run_frequency_days=rule.run_frequency_days,
            is_active=rule.is_active,
            last_run=rule.last_run,
            next_run=rule.next_run,
            last_run_deleted_count=rule.last_run_deleted_count,
            total_deleted_count=rule.total_deleted_count,
            created_at=rule.created_at,
            updated_at=rule.updated_at
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create retention rule"
        )


@router.get("/rules", response_model=List[DataRetentionRuleResponse])
async def list_retention_rules(
    active_only: bool = Query(False, description="Filter only active rules"),
    category_id: Optional[UUID] = Query(None, description="Filter by data category"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """List all data retention rules (admin only)"""
    retention_service = RetentionService(db)
    
    rules = await retention_service.list_retention_rules(
        active_only=active_only,
        category_id=category_id
    )
    
    return [
        DataRetentionRuleResponse(
            id=rule.id,
            rule_name=rule.rule_name,
            description=rule.description,
            table_name=rule.table_name,
            data_category_id=rule.data_category_id,
            condition_sql=rule.condition_sql,
            retention_days=rule.retention_days,
            deletion_method=rule.deletion_method,
            run_frequency_days=rule.run_frequency_days,
            is_active=rule.is_active,
            last_run=rule.last_run,
            next_run=rule.next_run,
            last_run_deleted_count=rule.last_run_deleted_count,
            total_deleted_count=rule.total_deleted_count,
            created_at=rule.created_at,
            updated_at=rule.updated_at
        )
        for rule in rules
    ]


@router.get("/rules/{rule_id}", response_model=DataRetentionRuleResponse)
async def get_retention_rule(
    rule_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Get a specific retention rule (admin only)"""
    retention_service = RetentionService(db)
    
    rule = await retention_service.get_retention_rule(rule_id)
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Retention rule not found"
        )
    
    return DataRetentionRuleResponse(
        id=rule.id,
        rule_name=rule.rule_name,
        description=rule.description,
        table_name=rule.table_name,
        data_category_id=rule.data_category_id,
        condition_sql=rule.condition_sql,
        retention_days=rule.retention_days,
        deletion_method=rule.deletion_method,
        run_frequency_days=rule.run_frequency_days,
        is_active=rule.is_active,
        last_run=rule.last_run,
        next_run=rule.next_run,
        last_run_deleted_count=rule.last_run_deleted_count,
        total_deleted_count=rule.total_deleted_count,
        created_at=rule.created_at,
        updated_at=rule.updated_at
    )


@router.patch("/rules/{rule_id}", response_model=DataRetentionRuleResponse)
async def update_retention_rule(
    rule_id: UUID,
    update_data: DataRetentionRuleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Update a retention rule (admin only)"""
    retention_service = RetentionService(db)
    
    rule = await retention_service.update_retention_rule(
        rule_id,
        update_data,
        updated_by=current_user.get("email", "admin")
    )
    
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Retention rule not found"
        )
    
    return DataRetentionRuleResponse(
        id=rule.id,
        rule_name=rule.rule_name,
        description=rule.description,
        table_name=rule.table_name,
        data_category_id=rule.data_category_id,
        condition_sql=rule.condition_sql,
        retention_days=rule.retention_days,
        deletion_method=rule.deletion_method,
        run_frequency_days=rule.run_frequency_days,
        is_active=rule.is_active,
        last_run=rule.last_run,
        next_run=rule.next_run,
        last_run_deleted_count=rule.last_run_deleted_count,
        total_deleted_count=rule.total_deleted_count,
        created_at=rule.created_at,
        updated_at=rule.updated_at
    )


@router.delete("/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_retention_rule(
    rule_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Delete a retention rule (admin only)"""
    retention_service = RetentionService(db)
    
    deleted = await retention_service.delete_retention_rule(
        rule_id,
        deleted_by=current_user.get("email", "admin")
    )
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Retention rule not found"
        )
    
    return None


@router.post("/rules/{rule_id}/execute", response_model=RetentionExecutionResult)
async def execute_retention_rule(
    rule_id: UUID,
    dry_run: bool = Query(True, description="Perform dry run without actual deletion"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Execute a specific retention rule (admin only)"""
    retention_service = RetentionService(db)
    
    # Get the rule
    rule = await retention_service.get_retention_rule(rule_id)
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Retention rule not found"
        )
    
    # Execute the rule
    result = await retention_service.execute_retention_rule(rule, dry_run=dry_run)
    
    return result


@router.post("/execute-all", response_model=List[RetentionExecutionResult])
async def execute_all_due_rules(
    dry_run: bool = Query(True, description="Perform dry run without actual deletion"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Execute all due retention rules (admin only)"""
    retention_service = RetentionService(db)
    
    results = await retention_service.execute_all_due_rules(dry_run=dry_run)
    
    return results


@router.post("/templates", response_model=List[DataRetentionRuleResponse])
async def create_default_templates(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Create default retention rule templates (admin only)"""
    retention_service = RetentionService(db)
    
    created_rules = await retention_service.create_default_templates()
    
    return [
        DataRetentionRuleResponse(
            id=rule.id,
            rule_name=rule.rule_name,
            description=rule.description,
            table_name=rule.table_name,
            data_category_id=rule.data_category_id,
            condition_sql=rule.condition_sql,
            retention_days=rule.retention_days,
            deletion_method=rule.deletion_method,
            run_frequency_days=rule.run_frequency_days,
            is_active=rule.is_active,
            last_run=rule.last_run,
            next_run=rule.next_run,
            last_run_deleted_count=rule.last_run_deleted_count,
            total_deleted_count=rule.total_deleted_count,
            created_at=rule.created_at,
            updated_at=rule.updated_at
        )
        for rule in created_rules
    ]


@router.get("/statistics", response_model=RetentionStatistics)
async def get_retention_statistics(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Get retention policy statistics (admin only)"""
    retention_service = RetentionService(db)
    
    stats = await retention_service.get_retention_statistics()
    
    return RetentionStatistics(**stats)