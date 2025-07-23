"""Rundown management service"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import logging

from ..db.models import Rundown, Story, RundownStatus, StoryStatus, RundownTemplate
from ..models.schemas import (
    RundownCreate, RundownUpdate, RundownResponse, RundownWithStories,
    StoryCreate, StoryUpdate, StoryResponse, StoryReorder
)
from ..core.config import settings

logger = logging.getLogger(__name__)


class RundownService:
    """Service for managing broadcast rundowns"""
    
    async def create_rundown(
        self,
        db: AsyncSession,
        rundown_data: RundownCreate,
        user_id: UUID
    ) -> RundownResponse:
        """Create a new rundown"""
        # Check for duplicate slug
        existing = await db.execute(
            select(Rundown).where(Rundown.slug == rundown_data.slug)
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"Rundown with slug '{rundown_data.slug}' already exists")
        
        # Create rundown
        rundown = Rundown(**rundown_data.model_dump())
        rundown.producer_id = user_id
        
        db.add(rundown)
        await db.commit()
        await db.refresh(rundown)
        
        logger.info(f"Created rundown: {rundown.id} - {rundown.title}")
        return RundownResponse.model_validate(rundown)
    
    async def get_rundown(
        self,
        db: AsyncSession,
        rundown_id: UUID,
        include_stories: bool = False
    ) -> Optional[RundownResponse]:
        """Get a rundown by ID"""
        query = select(Rundown).where(Rundown.id == rundown_id)
        
        if include_stories:
            query = query.options(selectinload(Rundown.stories))
        
        result = await db.execute(query)
        rundown = result.scalar_one_or_none()
        
        if not rundown:
            return None
        
        if include_stories:
            response = RundownWithStories.model_validate(rundown)
            response.story_count = len(rundown.stories)
            return response
        
        response = RundownResponse.model_validate(rundown)
        
        # Get story count
        story_count = await db.execute(
            select(func.count(Story.id)).where(Story.rundown_id == rundown_id)
        )
        response.story_count = story_count.scalar()
        
        return response
    
    async def list_rundowns(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        show_date_from: Optional[datetime] = None,
        show_date_to: Optional[datetime] = None,
        status: Optional[RundownStatus] = None,
        newsroom_system: Optional[str] = None,
        producer_id: Optional[UUID] = None,
        studio: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> List[RundownResponse]:
        """List rundowns with filters"""
        query = select(Rundown)
        
        # Apply filters
        conditions = []
        
        if show_date_from:
            conditions.append(Rundown.show_date >= show_date_from)
        if show_date_to:
            conditions.append(Rundown.show_date <= show_date_to)
        if status:
            conditions.append(Rundown.status == status)
        if newsroom_system:
            conditions.append(Rundown.newsroom_system == newsroom_system)
        if producer_id:
            conditions.append(Rundown.producer_id == producer_id)
        if studio:
            conditions.append(Rundown.studio == studio)
        if tags:
            # Filter by tags (JSONB contains)
            for tag in tags:
                conditions.append(Rundown.tags.contains([tag]))
        
        if conditions:
            query = query.where(and_(*conditions))
        
        # Order by show date descending
        query = query.order_by(Rundown.show_date.desc())
        
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        result = await db.execute(query)
        rundowns = result.scalars().all()
        
        # Get story counts
        responses = []
        for rundown in rundowns:
            response = RundownResponse.model_validate(rundown)
            
            story_count = await db.execute(
                select(func.count(Story.id)).where(Story.rundown_id == rundown.id)
            )
            response.story_count = story_count.scalar()
            
            responses.append(response)
        
        return responses
    
    async def update_rundown(
        self,
        db: AsyncSession,
        rundown_id: UUID,
        update_data: RundownUpdate,
        user_id: UUID
    ) -> Optional[RundownResponse]:
        """Update a rundown"""
        # Get rundown
        result = await db.execute(
            select(Rundown).where(Rundown.id == rundown_id)
        )
        rundown = result.scalar_one_or_none()
        
        if not rundown:
            return None
        
        # Check if locked
        if rundown.locked and not update_data.locked:
            raise ValueError("Rundown is locked and cannot be edited")
        
        # Check for slug uniqueness if updating
        if update_data.slug and update_data.slug != rundown.slug:
            existing = await db.execute(
                select(Rundown).where(
                    and_(
                        Rundown.slug == update_data.slug,
                        Rundown.id != rundown_id
                    )
                )
            )
            if existing.scalar_one_or_none():
                raise ValueError(f"Rundown with slug '{update_data.slug}' already exists")
        
        # Update fields
        update_dict = update_data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(rundown, field, value)
        
        rundown.updated_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(rundown)
        
        logger.info(f"Updated rundown: {rundown_id}")
        return RundownResponse.model_validate(rundown)
    
    async def delete_rundown(
        self,
        db: AsyncSession,
        rundown_id: UUID,
        user_id: UUID
    ) -> bool:
        """Delete a rundown"""
        # Get rundown
        result = await db.execute(
            select(Rundown).where(Rundown.id == rundown_id)
        )
        rundown = result.scalar_one_or_none()
        
        if not rundown:
            return False
        
        # Check if locked
        if rundown.locked:
            raise ValueError("Rundown is locked and cannot be deleted")
        
        # Check if on air
        if rundown.status == RundownStatus.ON_AIR:
            raise ValueError("Cannot delete rundown that is currently on air")
        
        # Delete rundown (stories will be cascade deleted)
        await db.delete(rundown)
        await db.commit()
        
        logger.info(f"Deleted rundown: {rundown_id}")
        return True
    
    async def lock_rundown(
        self,
        db: AsyncSession,
        rundown_id: UUID,
        locked: bool,
        user_id: UUID
    ) -> Optional[RundownResponse]:
        """Lock or unlock a rundown"""
        # Get rundown
        result = await db.execute(
            select(Rundown).where(Rundown.id == rundown_id)
        )
        rundown = result.scalar_one_or_none()
        
        if not rundown:
            return None
        
        rundown.locked = locked
        rundown.updated_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(rundown)
        
        logger.info(f"{'Locked' if locked else 'Unlocked'} rundown: {rundown_id}")
        return RundownResponse.model_validate(rundown)
    
    async def set_rundown_status(
        self,
        db: AsyncSession,
        rundown_id: UUID,
        status: RundownStatus,
        user_id: UUID
    ) -> Optional[RundownResponse]:
        """Set rundown status"""
        # Get rundown
        result = await db.execute(
            select(Rundown).where(Rundown.id == rundown_id)
        )
        rundown = result.scalar_one_or_none()
        
        if not rundown:
            return None
        
        # Validate status transitions
        current_status = rundown.status
        valid_transitions = {
            RundownStatus.DRAFT: [RundownStatus.READY],
            RundownStatus.READY: [RundownStatus.ON_AIR, RundownStatus.DRAFT],
            RundownStatus.ON_AIR: [RundownStatus.COMPLETED],
            RundownStatus.COMPLETED: [RundownStatus.ARCHIVED],
            RundownStatus.ARCHIVED: []
        }
        
        if status not in valid_transitions.get(current_status, []):
            raise ValueError(f"Invalid status transition from {current_status} to {status}")
        
        # Update status
        rundown.status = status
        rundown.updated_at = datetime.utcnow()
        
        # Set timestamps based on status
        if status == RundownStatus.ON_AIR:
            rundown.actual_start = datetime.utcnow()
        elif status == RundownStatus.COMPLETED:
            rundown.actual_end = datetime.utcnow()
        elif status == RundownStatus.ARCHIVED:
            rundown.archived_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(rundown)
        
        logger.info(f"Set rundown {rundown_id} status to {status}")
        return RundownResponse.model_validate(rundown)
    
    async def create_story(
        self,
        db: AsyncSession,
        story_data: StoryCreate,
        user_id: UUID
    ) -> StoryResponse:
        """Create a new story in a rundown"""
        # Check rundown exists and is not locked
        rundown_result = await db.execute(
            select(Rundown).where(Rundown.id == story_data.rundown_id)
        )
        rundown = rundown_result.scalar_one_or_none()
        
        if not rundown:
            raise ValueError("Rundown not found")
        
        if rundown.locked:
            raise ValueError("Rundown is locked and cannot be edited")
        
        # Check position
        if story_data.position < 0:
            raise ValueError("Position must be non-negative")
        
        # Adjust positions of existing stories
        await db.execute(
            Story.__table__.update()
            .where(
                and_(
                    Story.rundown_id == story_data.rundown_id,
                    Story.position >= story_data.position
                )
            )
            .values(position=Story.position + 1)
        )
        
        # Create story
        story = Story(**story_data.model_dump())
        
        db.add(story)
        await db.commit()
        await db.refresh(story)
        
        # Update rundown duration
        await self._update_rundown_duration(db, story_data.rundown_id)
        
        logger.info(f"Created story: {story.id} in rundown {story_data.rundown_id}")
        return StoryResponse.model_validate(story)
    
    async def update_story(
        self,
        db: AsyncSession,
        story_id: UUID,
        update_data: StoryUpdate,
        user_id: UUID
    ) -> Optional[StoryResponse]:
        """Update a story"""
        # Get story with rundown
        result = await db.execute(
            select(Story)
            .options(selectinload(Story.rundown))
            .where(Story.id == story_id)
        )
        story = result.scalar_one_or_none()
        
        if not story:
            return None
        
        # Check if rundown is locked
        if story.rundown.locked:
            raise ValueError("Rundown is locked and cannot be edited")
        
        # Handle position change
        if update_data.position is not None and update_data.position != story.position:
            await self._reorder_story(db, story, update_data.position)
        
        # Update fields
        update_dict = update_data.model_dump(exclude_unset=True, exclude={"position"})
        for field, value in update_dict.items():
            setattr(story, field, value)
        
        story.updated_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(story)
        
        # Update rundown duration if duration changed
        if update_data.duration_seconds is not None:
            await self._update_rundown_duration(db, story.rundown_id)
        
        logger.info(f"Updated story: {story_id}")
        return StoryResponse.model_validate(story)
    
    async def delete_story(
        self,
        db: AsyncSession,
        story_id: UUID,
        user_id: UUID
    ) -> bool:
        """Delete a story"""
        # Get story with rundown
        result = await db.execute(
            select(Story)
            .options(selectinload(Story.rundown))
            .where(Story.id == story_id)
        )
        story = result.scalar_one_or_none()
        
        if not story:
            return False
        
        # Check if rundown is locked
        if story.rundown.locked:
            raise ValueError("Rundown is locked and cannot be edited")
        
        # Check if story is on air
        if story.on_air:
            raise ValueError("Cannot delete story that is currently on air")
        
        rundown_id = story.rundown_id
        position = story.position
        
        # Delete story
        await db.delete(story)
        
        # Adjust positions of remaining stories
        await db.execute(
            Story.__table__.update()
            .where(
                and_(
                    Story.rundown_id == rundown_id,
                    Story.position > position
                )
            )
            .values(position=Story.position - 1)
        )
        
        await db.commit()
        
        # Update rundown duration
        await self._update_rundown_duration(db, rundown_id)
        
        logger.info(f"Deleted story: {story_id}")
        return True
    
    async def reorder_stories(
        self,
        db: AsyncSession,
        rundown_id: UUID,
        reorder_data: StoryReorder,
        user_id: UUID
    ) -> List[StoryResponse]:
        """Reorder stories in a rundown"""
        # Check rundown exists and is not locked
        rundown_result = await db.execute(
            select(Rundown).where(Rundown.id == rundown_id)
        )
        rundown = rundown_result.scalar_one_or_none()
        
        if not rundown:
            raise ValueError("Rundown not found")
        
        if rundown.locked:
            raise ValueError("Rundown is locked and cannot be edited")
        
        # Update story positions
        for item in reorder_data.story_positions:
            await db.execute(
                Story.__table__.update()
                .where(
                    and_(
                        Story.id == item["story_id"],
                        Story.rundown_id == rundown_id
                    )
                )
                .values(position=item["position"])
            )
        
        await db.commit()
        
        # Get updated stories
        result = await db.execute(
            select(Story)
            .where(Story.rundown_id == rundown_id)
            .order_by(Story.position)
        )
        stories = result.scalars().all()
        
        logger.info(f"Reordered stories in rundown: {rundown_id}")
        return [StoryResponse.model_validate(story) for story in stories]
    
    async def _reorder_story(
        self,
        db: AsyncSession,
        story: Story,
        new_position: int
    ) -> None:
        """Helper to reorder a single story"""
        old_position = story.position
        
        if new_position == old_position:
            return
        
        if new_position < old_position:
            # Moving up - shift stories down
            await db.execute(
                Story.__table__.update()
                .where(
                    and_(
                        Story.rundown_id == story.rundown_id,
                        Story.position >= new_position,
                        Story.position < old_position,
                        Story.id != story.id
                    )
                )
                .values(position=Story.position + 1)
            )
        else:
            # Moving down - shift stories up
            await db.execute(
                Story.__table__.update()
                .where(
                    and_(
                        Story.rundown_id == story.rundown_id,
                        Story.position > old_position,
                        Story.position <= new_position,
                        Story.id != story.id
                    )
                )
                .values(position=Story.position - 1)
            )
        
        story.position = new_position
    
    async def _update_rundown_duration(
        self,
        db: AsyncSession,
        rundown_id: UUID
    ) -> None:
        """Update total duration of a rundown"""
        # Calculate total duration
        result = await db.execute(
            select(func.sum(Story.duration_seconds))
            .where(Story.rundown_id == rundown_id)
        )
        total_duration = result.scalar() or 0
        
        # Update rundown
        await db.execute(
            Rundown.__table__.update()
            .where(Rundown.id == rundown_id)
            .values(
                duration_seconds=total_duration,
                updated_at=datetime.utcnow()
            )
        )
    
    async def apply_template(
        self,
        db: AsyncSession,
        rundown_id: UUID,
        template_id: UUID,
        user_id: UUID
    ) -> RundownWithStories:
        """Apply a template to a rundown"""
        # Get rundown and template
        rundown_result = await db.execute(
            select(Rundown).where(Rundown.id == rundown_id)
        )
        rundown = rundown_result.scalar_one_or_none()
        
        if not rundown:
            raise ValueError("Rundown not found")
        
        if rundown.locked:
            raise ValueError("Rundown is locked and cannot be edited")
        
        template_result = await db.execute(
            select(RundownTemplate).where(
                and_(
                    RundownTemplate.id == template_id,
                    RundownTemplate.active == True
                )
            )
        )
        template = template_result.scalar_one_or_none()
        
        if not template:
            raise ValueError("Template not found or inactive")
        
        # Apply template structure
        if template.duration_minutes:
            rundown.duration_seconds = template.duration_minutes * 60
        
        # Create default stories from template
        position = 0
        for story_template in template.default_stories:
            story = Story(
                rundown_id=rundown_id,
                position=position,
                slug=story_template.get("slug", f"story-{position + 1}"),
                title=story_template.get("title", f"Story {position + 1}"),
                duration_seconds=story_template.get("duration_seconds", 0),
                metadata=story_template.get("metadata", {})
            )
            db.add(story)
            position += 1
        
        await db.commit()
        await db.refresh(rundown)
        
        # Get rundown with stories
        result = await db.execute(
            select(Rundown)
            .options(selectinload(Rundown.stories))
            .where(Rundown.id == rundown_id)
        )
        rundown = result.scalar_one()
        
        logger.info(f"Applied template {template_id} to rundown {rundown_id}")
        return RundownWithStories.model_validate(rundown)


# Create service instance
rundown_service = RundownService()