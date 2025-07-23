"""Tests for rundown service"""

import pytest
from uuid import uuid4
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.schemas import RundownCreate, RundownUpdate, StoryCreate
from src.services.rundown_service import rundown_service
from src.db.models import RundownStatus


@pytest.fixture
def sample_rundown_data():
    """Sample rundown data for testing"""
    return RundownCreate(
        title="Evening News",
        slug="evening-news-2025-01-21",
        show_date=datetime.utcnow() + timedelta(hours=6),
        duration_seconds=1800,
        planned_start=datetime.utcnow() + timedelta(hours=6),
        planned_end=datetime.utcnow() + timedelta(hours=6, minutes=30),
        studio="Studio A",
        metadata={"format": "news", "target_audience": "general"},
        tags=["news", "daily", "prime-time"]
    )


@pytest.fixture
def sample_story_data():
    """Sample story data for testing"""
    return StoryCreate(
        rundown_id=uuid4(),  # Will be set in tests
        slug="lead-story",
        title="Breaking News: Major Development",
        duration_seconds=180,
        position=0,
        metadata={"type": "breaking", "priority": "high"},
        tags=["breaking", "lead"]
    )


@pytest.mark.asyncio
async def test_create_rundown(db_session: AsyncSession, sample_rundown_data):
    """Test creating a rundown"""
    user_id = uuid4()
    
    # Create rundown
    rundown = await rundown_service.create_rundown(db_session, sample_rundown_data, user_id)
    
    assert rundown.id is not None
    assert rundown.title == sample_rundown_data.title
    assert rundown.slug == sample_rundown_data.slug
    assert rundown.status == RundownStatus.DRAFT
    assert rundown.locked is False
    assert rundown.producer_id == user_id


@pytest.mark.asyncio
async def test_create_rundown_duplicate_slug(db_session: AsyncSession, sample_rundown_data):
    """Test creating rundown with duplicate slug fails"""
    user_id = uuid4()
    
    # Create first rundown
    await rundown_service.create_rundown(db_session, sample_rundown_data, user_id)
    
    # Try to create second rundown with same slug
    with pytest.raises(ValueError, match="already exists"):
        await rundown_service.create_rundown(db_session, sample_rundown_data, user_id)


@pytest.mark.asyncio
async def test_get_rundown(db_session: AsyncSession, sample_rundown_data):
    """Test getting a rundown by ID"""
    user_id = uuid4()
    
    # Create rundown
    created = await rundown_service.create_rundown(db_session, sample_rundown_data, user_id)
    
    # Get rundown
    rundown = await rundown_service.get_rundown(db_session, created.id)
    
    assert rundown is not None
    assert rundown.id == created.id
    assert rundown.title == created.title
    assert rundown.story_count == 0


@pytest.mark.asyncio
async def test_get_rundown_not_found(db_session: AsyncSession):
    """Test getting non-existent rundown returns None"""
    rundown = await rundown_service.get_rundown(db_session, uuid4())
    assert rundown is None


@pytest.mark.asyncio
async def test_update_rundown(db_session: AsyncSession, sample_rundown_data):
    """Test updating a rundown"""
    user_id = uuid4()
    
    # Create rundown
    created = await rundown_service.create_rundown(db_session, sample_rundown_data, user_id)
    
    # Update rundown
    update_data = RundownUpdate(
        title="Evening News - Updated",
        duration_seconds=2100
    )
    
    updated = await rundown_service.update_rundown(
        db_session, created.id, update_data, user_id
    )
    
    assert updated is not None
    assert updated.title == "Evening News - Updated"
    assert updated.duration_seconds == 2100
    assert updated.slug == created.slug  # Unchanged


@pytest.mark.asyncio
async def test_update_locked_rundown(db_session: AsyncSession, sample_rundown_data):
    """Test updating locked rundown fails"""
    user_id = uuid4()
    
    # Create and lock rundown
    created = await rundown_service.create_rundown(db_session, sample_rundown_data, user_id)
    await rundown_service.lock_rundown(db_session, created.id, True, user_id)
    
    # Try to update
    update_data = RundownUpdate(title="New Title")
    
    with pytest.raises(ValueError, match="locked"):
        await rundown_service.update_rundown(
            db_session, created.id, update_data, user_id
        )


@pytest.mark.asyncio
async def test_delete_rundown(db_session: AsyncSession, sample_rundown_data):
    """Test deleting a rundown"""
    user_id = uuid4()
    
    # Create rundown
    created = await rundown_service.create_rundown(db_session, sample_rundown_data, user_id)
    
    # Delete rundown
    success = await rundown_service.delete_rundown(db_session, created.id, user_id)
    assert success is True
    
    # Verify deleted
    rundown = await rundown_service.get_rundown(db_session, created.id)
    assert rundown is None


@pytest.mark.asyncio
async def test_delete_on_air_rundown(db_session: AsyncSession, sample_rundown_data):
    """Test deleting on-air rundown fails"""
    user_id = uuid4()
    
    # Create rundown and set to on-air
    created = await rundown_service.create_rundown(db_session, sample_rundown_data, user_id)
    await rundown_service.set_rundown_status(
        db_session, created.id, RundownStatus.READY, user_id
    )
    await rundown_service.set_rundown_status(
        db_session, created.id, RundownStatus.ON_AIR, user_id
    )
    
    # Try to delete
    with pytest.raises(ValueError, match="on air"):
        await rundown_service.delete_rundown(db_session, created.id, user_id)


@pytest.mark.asyncio
async def test_lock_unlock_rundown(db_session: AsyncSession, sample_rundown_data):
    """Test locking and unlocking a rundown"""
    user_id = uuid4()
    
    # Create rundown
    created = await rundown_service.create_rundown(db_session, sample_rundown_data, user_id)
    assert created.locked is False
    
    # Lock rundown
    locked = await rundown_service.lock_rundown(db_session, created.id, True, user_id)
    assert locked.locked is True
    
    # Unlock rundown
    unlocked = await rundown_service.lock_rundown(db_session, created.id, False, user_id)
    assert unlocked.locked is False


@pytest.mark.asyncio
async def test_rundown_status_transitions(db_session: AsyncSession, sample_rundown_data):
    """Test valid rundown status transitions"""
    user_id = uuid4()
    
    # Create rundown (starts as DRAFT)
    created = await rundown_service.create_rundown(db_session, sample_rundown_data, user_id)
    assert created.status == RundownStatus.DRAFT
    
    # DRAFT -> READY
    rundown = await rundown_service.set_rundown_status(
        db_session, created.id, RundownStatus.READY, user_id
    )
    assert rundown.status == RundownStatus.READY
    
    # READY -> ON_AIR
    rundown = await rundown_service.set_rundown_status(
        db_session, created.id, RundownStatus.ON_AIR, user_id
    )
    assert rundown.status == RundownStatus.ON_AIR
    assert rundown.actual_start is not None
    
    # ON_AIR -> COMPLETED
    rundown = await rundown_service.set_rundown_status(
        db_session, created.id, RundownStatus.COMPLETED, user_id
    )
    assert rundown.status == RundownStatus.COMPLETED
    assert rundown.actual_end is not None


@pytest.mark.asyncio
async def test_invalid_status_transition(db_session: AsyncSession, sample_rundown_data):
    """Test invalid status transition fails"""
    user_id = uuid4()
    
    # Create rundown (starts as DRAFT)
    created = await rundown_service.create_rundown(db_session, sample_rundown_data, user_id)
    
    # Try invalid transition DRAFT -> COMPLETED
    with pytest.raises(ValueError, match="Invalid status transition"):
        await rundown_service.set_rundown_status(
            db_session, created.id, RundownStatus.COMPLETED, user_id
        )


@pytest.mark.asyncio
async def test_create_story(db_session: AsyncSession, sample_rundown_data, sample_story_data):
    """Test creating a story in a rundown"""
    user_id = uuid4()
    
    # Create rundown
    rundown = await rundown_service.create_rundown(db_session, sample_rundown_data, user_id)
    
    # Create story
    sample_story_data.rundown_id = rundown.id
    story = await rundown_service.create_story(db_session, sample_story_data, user_id)
    
    assert story.id is not None
    assert story.rundown_id == rundown.id
    assert story.title == sample_story_data.title
    assert story.position == 0
    
    # Check rundown duration updated
    updated_rundown = await rundown_service.get_rundown(db_session, rundown.id)
    assert updated_rundown.story_count == 1


@pytest.mark.asyncio
async def test_create_story_in_locked_rundown(
    db_session: AsyncSession,
    sample_rundown_data,
    sample_story_data
):
    """Test creating story in locked rundown fails"""
    user_id = uuid4()
    
    # Create and lock rundown
    rundown = await rundown_service.create_rundown(db_session, sample_rundown_data, user_id)
    await rundown_service.lock_rundown(db_session, rundown.id, True, user_id)
    
    # Try to create story
    sample_story_data.rundown_id = rundown.id
    
    with pytest.raises(ValueError, match="locked"):
        await rundown_service.create_story(db_session, sample_story_data, user_id)


@pytest.mark.asyncio
async def test_list_rundowns(db_session: AsyncSession, sample_rundown_data):
    """Test listing rundowns with filters"""
    user_id = uuid4()
    
    # Create multiple rundowns
    for i in range(3):
        data = sample_rundown_data.model_copy()
        data.slug = f"news-{i}"
        data.show_date = datetime.utcnow() + timedelta(days=i)
        await rundown_service.create_rundown(db_session, data, user_id)
    
    # List all rundowns
    rundowns = await rundown_service.list_rundowns(db_session)
    assert len(rundowns) >= 3
    
    # List with pagination
    rundowns = await rundown_service.list_rundowns(db_session, skip=0, limit=2)
    assert len(rundowns) == 2
    
    # List with date filter
    tomorrow = datetime.utcnow() + timedelta(days=1)
    rundowns = await rundown_service.list_rundowns(
        db_session,
        show_date_from=tomorrow.replace(hour=0, minute=0),
        show_date_to=tomorrow.replace(hour=23, minute=59)
    )
    assert len(rundowns) >= 1