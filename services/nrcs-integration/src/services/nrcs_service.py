"""Main NRCS integration service"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import logging

from ..db.models import (
    NRCSSystem, NRCSStory, NRCSRundown, NRCSUser, NRCSAssignment,
    NRCSType, ConnectionStatus, SyncStatus, StoryStatus
)
from ..models.schemas import (
    NRCSSystemCreate, NRCSSystemUpdate, NRCSSystemResponse,
    NRCSStoryCreate, NRCSStoryUpdate, NRCSStoryResponse,
    NRCSRundownCreate, NRCSRundownUpdate, NRCSRundownResponse,
    NRCSUserCreate, NRCSUserUpdate, NRCSUserResponse,
    SystemStatusResponse, SearchRequest, SearchResponse
)
from ..adapters.base import NRCSAdapter, GenericNRCSAdapter
from ..core.config import settings

logger = logging.getLogger(__name__)


class NRCSService:
    """Service for managing NRCS integrations"""
    
    def __init__(self):
        self._adapters: Dict[str, NRCSAdapter] = {}
        self._adapter_classes = {
            NRCSType.ENPS: GenericNRCSAdapter,  # Will be replaced with ENPSAdapter
            NRCSType.AVID_INEWS: GenericNRCSAdapter,  # Will be replaced with AvidAdapter
            NRCSType.ROSS_INCEPTION: GenericNRCSAdapter,  # Will be replaced with RossAdapter
            NRCSType.OCTOPUS: GenericNRCSAdapter,  # Will be replaced with OctopusAdapter
            NRCSType.GENERIC: GenericNRCSAdapter,
        }
    
    # NRCS System Management
    async def create_system(
        self,
        db: AsyncSession,
        system_data: NRCSSystemCreate
    ) -> NRCSSystemResponse:
        """Create a new NRCS system"""
        # Check for duplicate slug
        existing = await db.execute(
            select(NRCSSystem).where(NRCSSystem.slug == system_data.slug)
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"NRCS system with slug '{system_data.slug}' already exists")
        
        # Create system
        system_dict = system_data.model_dump(exclude={'username', 'password', 'api_key', 'token'})
        system = NRCSSystem(**system_dict)
        
        # Store credentials securely (should be encrypted in production)
        if system_data.username:
            system.username = system_data.username
        if system_data.password:
            system.password = system_data.password  # TODO: Encrypt
        if system_data.api_key:
            system.api_key = system_data.api_key    # TODO: Encrypt
        if system_data.token:
            system.token = system_data.token        # TODO: Encrypt
        
        db.add(system)
        await db.commit()
        await db.refresh(system)
        
        logger.info(f"Created NRCS system: {system.id} - {system.name}")
        return NRCSSystemResponse.model_validate(system)
    
    async def get_system(
        self,
        db: AsyncSession,
        system_id: UUID
    ) -> Optional[NRCSSystemResponse]:
        """Get an NRCS system by ID"""
        result = await db.execute(
            select(NRCSSystem).where(NRCSSystem.id == system_id)
        )
        system = result.scalar_one_or_none()
        
        if not system:
            return None
        
        return NRCSSystemResponse.model_validate(system)
    
    async def list_systems(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        is_active: Optional[bool] = None,
        system_type: Optional[NRCSType] = None
    ) -> List[NRCSSystemResponse]:
        """List NRCS systems"""
        query = select(NRCSSystem)
        
        # Apply filters
        conditions = []
        if is_active is not None:
            conditions.append(NRCSSystem.is_active == is_active)
        if system_type:
            conditions.append(NRCSSystem.system_type == system_type)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        # Order by name
        query = query.order_by(NRCSSystem.name)
        
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        result = await db.execute(query)
        systems = result.scalars().all()
        
        return [NRCSSystemResponse.model_validate(system) for system in systems]
    
    async def update_system(
        self,
        db: AsyncSession,
        system_id: UUID,
        update_data: NRCSSystemUpdate
    ) -> Optional[NRCSSystemResponse]:
        """Update an NRCS system"""
        result = await db.execute(
            select(NRCSSystem).where(NRCSSystem.id == system_id)
        )
        system = result.scalar_one_or_none()
        
        if not system:
            return None
        
        # Update fields
        update_dict = update_data.model_dump(exclude_unset=True, exclude={'username', 'password', 'api_key', 'token'})
        
        for field, value in update_dict.items():
            setattr(system, field, value)
        
        # Handle credentials
        if update_data.username is not None:
            system.username = update_data.username
        if update_data.password is not None:
            system.password = update_data.password  # TODO: Encrypt
        if update_data.api_key is not None:
            system.api_key = update_data.api_key    # TODO: Encrypt
        if update_data.token is not None:
            system.token = update_data.token        # TODO: Encrypt
        
        system.updated_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(system)
        
        logger.info(f"Updated NRCS system: {system_id}")
        return NRCSSystemResponse.model_validate(system)
    
    async def delete_system(
        self,
        db: AsyncSession,
        system_id: UUID
    ) -> bool:
        """Delete an NRCS system"""
        result = await db.execute(
            select(NRCSSystem).where(NRCSSystem.id == system_id)
        )
        system = result.scalar_one_or_none()
        
        if not system:
            return False
        
        # Disconnect before deleting
        if system_id in self._adapters:
            await self._adapters[system_id].disconnect()
            del self._adapters[system_id]
        
        await db.delete(system)
        await db.commit()
        
        logger.info(f"Deleted NRCS system: {system_id}")
        return True
    
    # Connection Management
    async def connect_system(
        self,
        db: AsyncSession,
        system_id: UUID
    ) -> Dict[str, Any]:
        """Connect to an NRCS system"""
        result = await db.execute(
            select(NRCSSystem).where(NRCSSystem.id == system_id)
        )
        system = result.scalar_one_or_none()
        
        if not system:
            raise ValueError("NRCS system not found")
        
        # Get or create adapter
        adapter = await self._get_adapter(system)
        
        try:
            # Attempt connection
            connected = await adapter.connect()
            
            if connected:
                system.status = ConnectionStatus.CONNECTED
                system.last_connection = datetime.utcnow()
                system.last_heartbeat = datetime.utcnow()
                system.error_count = 0
                system.last_error = None
            else:
                system.status = ConnectionStatus.ERROR
                system.last_error = "Connection failed"
                system.error_count += 1
            
            await db.commit()
            
            return {
                "system_id": system_id,
                "connected": connected,
                "status": system.status.value,
                "message": "Connected successfully" if connected else "Connection failed"
            }
        except Exception as e:
            system.status = ConnectionStatus.ERROR
            system.last_error = str(e)
            system.error_count += 1
            await db.commit()
            
            logger.error(f"Connection failed for system {system_id}: {str(e)}")
            return {
                "system_id": system_id,
                "connected": False,
                "status": ConnectionStatus.ERROR.value,
                "message": str(e)
            }
    
    async def disconnect_system(
        self,
        db: AsyncSession,
        system_id: UUID
    ) -> Dict[str, Any]:
        """Disconnect from an NRCS system"""
        result = await db.execute(
            select(NRCSSystem).where(NRCSSystem.id == system_id)
        )
        system = result.scalar_one_or_none()
        
        if not system:
            raise ValueError("NRCS system not found")
        
        if system_id in self._adapters:
            try:
                await self._adapters[system_id].disconnect()
                del self._adapters[system_id]
                
                system.status = ConnectionStatus.DISCONNECTED
                await db.commit()
                
                return {
                    "system_id": system_id,
                    "disconnected": True,
                    "message": "Disconnected successfully"
                }
            except Exception as e:
                logger.error(f"Disconnection failed for system {system_id}: {str(e)}")
                return {
                    "system_id": system_id,
                    "disconnected": False,
                    "message": str(e)
                }
        
        return {
            "system_id": system_id,
            "disconnected": True,
            "message": "System was not connected"
        }
    
    async def get_system_status(
        self,
        db: AsyncSession,
        system_id: UUID
    ) -> SystemStatusResponse:
        """Get detailed system status"""
        result = await db.execute(
            select(NRCSSystem)
            .options(selectinload(NRCSSystem.stories))
            .where(NRCSSystem.id == system_id)
        )
        system = result.scalar_one_or_none()
        
        if not system:
            raise ValueError("NRCS system not found")
        
        # Get adapter health if connected
        connection_details = {}
        if system_id in self._adapters:
            try:
                adapter = self._adapters[system_id]
                connection_details = await adapter.get_health_status()
            except Exception as e:
                connection_details = {"error": str(e)}
        
        # Get stats
        stats = {
            "total_stories": system.total_stories,
            "total_rundowns": system.total_rundowns,
            "total_users": system.total_users,
            "error_count": system.error_count
        }
        
        # Get recent activity (simplified)
        recent_activity = []
        if system.last_connection:
            recent_activity.append({
                "event": "connection",
                "timestamp": system.last_connection,
                "status": "success"
            })
        
        return SystemStatusResponse(
            system_id=system.id,
            name=system.name,
            system_type=system.system_type,
            status=system.status,
            is_active=system.is_active,
            last_heartbeat=system.last_heartbeat,
            connection_details=connection_details,
            stats=stats,
            recent_activity=recent_activity
        )
    
    # Story Management
    async def sync_stories(
        self,
        db: AsyncSession,
        system_id: UUID,
        force: bool = False
    ) -> Dict[str, Any]:
        """Sync stories from NRCS system"""
        adapter = await self._get_system_adapter(db, system_id)
        
        try:
            # Get stories from NRCS
            external_stories = await adapter.get_stories(limit=1000)
            
            sync_results = {
                "total": len(external_stories),
                "created": 0,
                "updated": 0,
                "errors": 0,
                "error_messages": []
            }
            
            for ext_story in external_stories:
                try:
                    # Check if story exists
                    existing = await db.execute(
                        select(NRCSStory).where(
                            and_(
                                NRCSStory.system_id == system_id,
                                NRCSStory.story_id == ext_story.get('id')
                            )
                        )
                    )
                    story = existing.scalar_one_or_none()
                    
                    if story:
                        # Update existing story
                        story.headline = ext_story.get('headline', story.headline)
                        story.summary = ext_story.get('summary', story.summary)
                        story.body = ext_story.get('body', story.body)
                        story.author = ext_story.get('author', story.author)
                        story.category = ext_story.get('category', story.category)
                        story.last_sync_at = datetime.utcnow()
                        story.sync_status = SyncStatus.COMPLETED
                        story.external_updated_at = datetime.fromisoformat(ext_story.get('updated_at', datetime.utcnow().isoformat()))
                        
                        sync_results["updated"] += 1
                    else:
                        # Create new story
                        story = NRCSStory(
                            system_id=system_id,
                            story_id=ext_story.get('id'),
                            slug=ext_story.get('slug', f"story-{ext_story.get('id')}"),
                            headline=ext_story.get('headline', ''),
                            summary=ext_story.get('summary'),
                            body=ext_story.get('body'),
                            author=ext_story.get('author'),
                            category=ext_story.get('category'),
                            priority=ext_story.get('priority', 0),
                            status=StoryStatus.DRAFT,
                            last_sync_at=datetime.utcnow(),
                            sync_status=SyncStatus.COMPLETED,
                            external_created_at=datetime.fromisoformat(ext_story.get('created_at', datetime.utcnow().isoformat())),
                            external_updated_at=datetime.fromisoformat(ext_story.get('updated_at', datetime.utcnow().isoformat()))
                        )
                        
                        db.add(story)
                        sync_results["created"] += 1
                    
                except Exception as e:
                    sync_results["errors"] += 1
                    sync_results["error_messages"].append(f"Story {ext_story.get('id', 'unknown')}: {str(e)}")
                    logger.error(f"Error syncing story: {e}")
            
            await db.commit()
            
            # Update system stats
            await self._update_system_stats(db, system_id)
            
            logger.info(f"Story sync completed for system {system_id}: {sync_results}")
            return sync_results
            
        except Exception as e:
            logger.error(f"Story sync failed for system {system_id}: {e}")
            return {
                "total": 0,
                "created": 0,
                "updated": 0,
                "errors": 1,
                "error_messages": [str(e)]
            }
    
    # Search functionality
    async def search_content(
        self,
        db: AsyncSession,
        search_request: SearchRequest
    ) -> SearchResponse:
        """Search content across NRCS systems"""
        # Build query
        query = select(NRCSStory)
        conditions = []
        
        # System filter
        if search_request.system_id:
            conditions.append(NRCSStory.system_id == search_request.system_id)
        
        # Text search (simplified)
        if search_request.query:
            search_term = f"%{search_request.query}%"
            conditions.append(
                or_(
                    NRCSStory.headline.ilike(search_term),
                    NRCSStory.summary.ilike(search_term),
                    NRCSStory.body.ilike(search_term)
                )
            )
        
        # Date range
        if search_request.date_from:
            conditions.append(NRCSStory.created_at >= search_request.date_from)
        if search_request.date_to:
            conditions.append(NRCSStory.created_at <= search_request.date_to)
        
        # Author filter
        if search_request.author:
            conditions.append(NRCSStory.author.ilike(f"%{search_request.author}%"))
        
        # Category filter
        if search_request.category:
            conditions.append(NRCSStory.category == search_request.category)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        # Count total results
        count_query = select(func.count(NRCSStory.id))
        if conditions:
            count_query = count_query.where(and_(*conditions))
        
        total_result = await db.execute(count_query)
        total_count = total_result.scalar()
        
        # Apply pagination
        query = query.offset(search_request.offset).limit(search_request.limit)
        
        # Execute query
        start_time = datetime.utcnow()
        result = await db.execute(query)
        stories = result.scalars().all()
        end_time = datetime.utcnow()
        
        # Convert to response format
        results = []
        for story in stories:
            results.append({
                "id": str(story.id),
                "story_id": story.story_id,
                "headline": story.headline,
                "summary": story.summary,
                "author": story.author,
                "category": story.category,
                "created_at": story.created_at.isoformat() if story.created_at else None,
                "system_id": str(story.system_id),
                "type": "story"
            })
        
        took_ms = int((end_time - start_time).total_seconds() * 1000)
        
        return SearchResponse(
            total_results=total_count,
            results=results,
            took_ms=took_ms,
            facets={}  # TODO: Implement facets
        )
    
    # Helper methods
    async def _get_adapter(self, system: NRCSSystem) -> NRCSAdapter:
        """Get or create adapter for system"""
        if system.id not in self._adapters:
            adapter_class = self._adapter_classes.get(system.system_type, GenericNRCSAdapter)
            self._adapters[system.id] = adapter_class(system)
        
        return self._adapters[system.id]
    
    async def _get_system_adapter(self, db: AsyncSession, system_id: UUID) -> NRCSAdapter:
        """Get adapter for system by ID"""
        result = await db.execute(
            select(NRCSSystem).where(NRCSSystem.id == system_id)
        )
        system = result.scalar_one_or_none()
        
        if not system:
            raise ValueError("NRCS system not found")
        
        return await self._get_adapter(system)
    
    async def _update_system_stats(self, db: AsyncSession, system_id: UUID):
        """Update system statistics"""
        # Count stories
        story_count = await db.execute(
            select(func.count(NRCSStory.id)).where(NRCSStory.system_id == system_id)
        )
        
        # Count rundowns  
        rundown_count = await db.execute(
            select(func.count(NRCSRundown.id)).where(NRCSRundown.system_id == system_id)
        )
        
        # Count users
        user_count = await db.execute(
            select(func.count(NRCSUser.id)).where(NRCSUser.system_id == system_id)
        )
        
        # Update system
        result = await db.execute(
            select(NRCSSystem).where(NRCSSystem.id == system_id)
        )
        system = result.scalar_one_or_none()
        
        if system:
            system.total_stories = story_count.scalar()
            system.total_rundowns = rundown_count.scalar()
            system.total_users = user_count.scalar()
            system.updated_at = datetime.utcnow()
            
            await db.commit()


# Create service instance
nrcs_service = NRCSService()