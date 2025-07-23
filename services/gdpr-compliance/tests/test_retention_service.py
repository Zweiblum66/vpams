"""Tests for Data Retention Service"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import DataRetentionRule, DataCategory
from src.services.retention_service import RetentionService
from src.models.schemas import DataRetentionRuleCreate


@pytest.mark.asyncio
async def test_create_retention_rule(db_session: AsyncSession):
    """Test creating a retention rule"""
    retention_service = RetentionService(db_session)
    
    rule_data = DataRetentionRuleCreate(
        rule_name="Test Rule",
        description="Test retention rule",
        retention_days=30,
        deletion_method="hard_delete",
        run_frequency_days=1,
        is_active=True
    )
    
    rule = await retention_service.create_retention_rule(rule_data, "test_user")
    
    assert rule.rule_name == "Test Rule"
    assert rule.retention_days == 30
    assert rule.deletion_method == "hard_delete"
    assert rule.is_active is True
    assert rule.next_run is not None


@pytest.mark.asyncio
async def test_list_retention_rules(db_session: AsyncSession):
    """Test listing retention rules"""
    retention_service = RetentionService(db_session)
    
    # Create multiple rules
    for i in range(3):
        rule_data = DataRetentionRuleCreate(
            rule_name=f"Test Rule {i}",
            retention_days=30,
            deletion_method="hard_delete",
            is_active=i < 2  # First two active, last one inactive
        )
        await retention_service.create_retention_rule(rule_data, "test_user")
    
    # List all rules
    all_rules = await retention_service.list_retention_rules()
    assert len(all_rules) == 3
    
    # List only active rules
    active_rules = await retention_service.list_retention_rules(active_only=True)
    assert len(active_rules) == 2


@pytest.mark.asyncio
async def test_update_retention_rule(db_session: AsyncSession):
    """Test updating a retention rule"""
    retention_service = RetentionService(db_session)
    
    # Create a rule
    rule_data = DataRetentionRuleCreate(
        rule_name="Update Test",
        retention_days=30,
        deletion_method="hard_delete"
    )
    rule = await retention_service.create_retention_rule(rule_data, "test_user")
    
    # Update the rule
    from src.models.schemas import DataRetentionRuleUpdate
    update_data = DataRetentionRuleUpdate(
        retention_days=60,
        deletion_method="soft_delete",
        is_active=False
    )
    
    updated_rule = await retention_service.update_retention_rule(
        rule.id,
        update_data,
        "test_user"
    )
    
    assert updated_rule.retention_days == 60
    assert updated_rule.deletion_method == "soft_delete"
    assert updated_rule.is_active is False


@pytest.mark.asyncio
async def test_execute_retention_rule_dry_run(db_session: AsyncSession):
    """Test executing a retention rule in dry run mode"""
    retention_service = RetentionService(db_session)
    
    # Create a rule
    rule_data = DataRetentionRuleCreate(
        rule_name="Dry Run Test",
        table_name="test_table",
        retention_days=30,
        deletion_method="hard_delete"
    )
    rule = await retention_service.create_retention_rule(rule_data, "test_user")
    
    # Execute in dry run mode
    result = await retention_service.execute_retention_rule(rule, dry_run=True)
    
    assert result.dry_run is True
    assert result.success is True
    assert result.deleted_records == 0  # No actual deletions in dry run


@pytest.mark.asyncio
async def test_create_default_templates(db_session: AsyncSession):
    """Test creating default retention templates"""
    retention_service = RetentionService(db_session)
    
    created_rules = await retention_service.create_default_templates()
    
    assert len(created_rules) > 0
    
    # Check if templates were created
    all_rules = await retention_service.list_retention_rules()
    rule_names = [r.rule_name for r in all_rules]
    
    assert "GDPR Personal Data - 7 Years" in rule_names
    assert "Session Data - 30 Days" in rule_names
    assert "Audit Logs - 3 Years" in rule_names


@pytest.mark.asyncio
async def test_retention_statistics(db_session: AsyncSession):
    """Test getting retention statistics"""
    retention_service = RetentionService(db_session)
    
    # Create some rules
    for i in range(2):
        rule_data = DataRetentionRuleCreate(
            rule_name=f"Stats Test {i}",
            retention_days=30,
            deletion_method="hard_delete",
            is_active=True
        )
        await retention_service.create_retention_rule(rule_data, "test_user")
    
    # Get statistics
    stats = await retention_service.get_retention_statistics()
    
    assert stats["total_rules"] >= 2
    assert stats["active_rules"] >= 2
    assert "recent_executions" in stats