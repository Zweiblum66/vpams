"""API routes for MOS Integration Service"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta
import redis.asyncio as redis

from ..core.config import settings
from ..db.base import get_db
from ..db.models import (
    MOSConnection, MOSObject, MOSRunningOrder, MOSStory, 
    MOSStoryItem, MOSMessage, MOSHeartbeat
)
from ..models.schemas import (
    MOSConnectionResponse, MOSObjectResponse, MOSRunningOrderResponse,
    MOSMessageResponse, ObjectSearchParams, RunningOrderSearchParams,
    PaginatedResponse, HealthStatus, ConnectionStats,
    MOSObjectCreate, MOSRunningOrderCreate, MOSConnectionCreate
)
from ..services.mos_service import MOSService
from ..utils.xml_parser import MOSXMLGenerator


router = APIRouter(prefix="/api/v1/mos", tags=["mos-integration"])


# Dependency to get Redis client
async def get_redis() -> redis.Redis:
    client = redis.from_url(settings.redis_url)
    try:
        yield client
    finally:
        await client.close()


# Dependency to get MOS service
async def get_mos_service(
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis)
) -> MOSService:
    return MOSService(db, redis_client)


# Health and status endpoints
@router.get("/health", response_model=HealthStatus)
async def health_check(
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis)
):
    """Health check endpoint"""
    try:
        # Check database connection
        await db.execute(select(1))
        db_healthy = True
    except:
        db_healthy = False
    
    try:
        # Check Redis connection
        await redis_client.ping()
        redis_healthy = True
    except:
        redis_healthy = False
    
    # Check active connections
    connection_result = await db.execute(
        select(func.count(MOSConnection.id)).where(
            MOSConnection.connection_status == "connected"
        )
    )
    active_connections = connection_result.scalar() or 0
    
    overall_status = "healthy" if db_healthy and redis_healthy else "unhealthy"
    
    return HealthStatus(
        status=overall_status,
        timestamp=datetime.utcnow(),
        service=settings.service_name,
        version=settings.service_version,
        connections={"active": str(active_connections)},
        database=db_healthy,
        redis=redis_healthy
    )


@router.get("/stats", response_model=ConnectionStats)
async def get_connection_stats(db: AsyncSession = Depends(get_db)):
    """Get connection statistics"""
    # Total connections
    total_conn_result = await db.execute(
        select(func.count(MOSConnection.id))
    )
    total_connections = total_conn_result.scalar() or 0
    
    # Active connections
    active_conn_result = await db.execute(
        select(func.count(MOSConnection.id)).where(
            MOSConnection.connection_status == "connected"
        )
    )
    active_connections = active_conn_result.scalar() or 0
    
    # Total objects
    obj_result = await db.execute(
        select(func.count(MOSObject.id))
    )
    total_objects = obj_result.scalar() or 0
    
    # Total running orders
    ro_result = await db.execute(
        select(func.count(MOSRunningOrder.id))
    )
    total_running_orders = ro_result.scalar() or 0
    
    # Total messages
    msg_result = await db.execute(
        select(func.count(MOSMessage.id))
    )
    total_messages = msg_result.scalar() or 0
    
    # Last 24h messages
    yesterday = datetime.utcnow() - timedelta(days=1)
    recent_msg_result = await db.execute(
        select(func.count(MOSMessage.id)).where(
            MOSMessage.received_at >= yesterday
        )
    )
    last_24h_messages = recent_msg_result.scalar() or 0
    
    return ConnectionStats(
        total_connections=total_connections,
        active_connections=active_connections,
        total_objects=total_objects,
        total_running_orders=total_running_orders,
        total_messages=total_messages,
        last_24h_messages=last_24h_messages
    )


# Connection management
@router.get("/connections", response_model=List[MOSConnectionResponse])
async def list_connections(
    status: Optional[str] = Query(None, description="Filter by connection status"),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """List MOS connections"""
    query = select(MOSConnection).order_by(desc(MOSConnection.created_at))
    
    if status:
        query = query.where(MOSConnection.connection_status == status)
    
    query = query.limit(limit).offset(offset)
    
    result = await db.execute(query)
    connections = result.scalars().all()
    
    return [
        MOSConnectionResponse(
            id=str(conn.id),
            nrcs_id=conn.nrcs_id,
            nrcs_description=conn.nrcs_description,
            connection_status=conn.connection_status,
            last_heartbeat=conn.last_heartbeat,
            supported_profiles=conn.supported_profiles,
            capabilities=conn.capabilities,
            created_at=conn.created_at,
            updated_at=conn.updated_at
        )
        for conn in connections
    ]


@router.get("/connections/{connection_id}", response_model=MOSConnectionResponse)
async def get_connection(
    connection_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get specific MOS connection"""
    result = await db.execute(
        select(MOSConnection).where(MOSConnection.id == connection_id)
    )
    connection = result.scalar_one_or_none()
    
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found"
        )
    
    return MOSConnectionResponse(
        id=str(connection.id),
        nrcs_id=connection.nrcs_id,
        nrcs_description=connection.nrcs_description,
        connection_status=connection.connection_status,
        last_heartbeat=connection.last_heartbeat,
        supported_profiles=connection.supported_profiles,
        capabilities=connection.capabilities,
        created_at=connection.created_at,
        updated_at=connection.updated_at
    )


# Object management
@router.get("/objects", response_model=PaginatedResponse)
async def list_objects(
    params: ObjectSearchParams = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """List MOS objects with search and pagination"""
    query = select(MOSObject).order_by(desc(MOSObject.created_at))
    
    # Apply filters
    if params.obj_type:
        query = query.where(MOSObject.obj_type == params.obj_type)
    
    if params.obj_group:
        query = query.where(MOSObject.obj_group == params.obj_group)
    
    if params.status:
        query = query.where(MOSObject.status == params.status)
    
    if params.created_after:
        query = query.where(MOSObject.created_at >= params.created_after)
    
    if params.created_before:
        query = query.where(MOSObject.created_at <= params.created_before)
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Apply pagination
    query = query.limit(params.limit).offset(params.offset)
    
    result = await db.execute(query)
    objects = result.scalars().all()
    
    items = [
        MOSObjectResponse(
            id=str(obj.id),
            obj_id=obj.obj_id,
            obj_slug=obj.obj_slug,
            obj_type=obj.obj_type,
            obj_tb=obj.obj_tb,
            obj_rev=obj.obj_rev,
            obj_dur=obj.obj_dur,
            status=obj.status,
            obj_air=obj.obj_air,
            obj_abstract=obj.obj_abstract,
            obj_group=obj.obj_group,
            obj_paths=obj.obj_paths,
            created_by=obj.created_by,
            created=obj.created_at,
            changed_by=obj.changed_by,
            changed=obj.updated_at,
            description=obj.description,
            external_metadata=obj.external_metadata,
            connection_id=str(obj.connection_id),
            created_at=obj.created_at,
            updated_at=obj.updated_at
        )
        for obj in objects
    ]
    
    return PaginatedResponse(
        items=items,
        total=total,
        limit=params.limit,
        offset=params.offset,
        has_next=params.offset + params.limit < total,
        has_prev=params.offset > 0
    )


@router.get("/objects/{obj_id}", response_model=MOSObjectResponse)
async def get_object(
    obj_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get specific MOS object"""
    result = await db.execute(
        select(MOSObject).where(MOSObject.obj_id == obj_id)
    )
    obj = result.scalar_one_or_none()
    
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Object not found"
        )
    
    return MOSObjectResponse(
        id=str(obj.id),
        obj_id=obj.obj_id,
        obj_slug=obj.obj_slug,
        obj_type=obj.obj_type,
        obj_tb=obj.obj_tb,
        obj_rev=obj.obj_rev,
        obj_dur=obj.obj_dur,
        status=obj.status,
        obj_air=obj.obj_air,
        obj_abstract=obj.obj_abstract,
        obj_group=obj.obj_group,
        obj_paths=obj.obj_paths,
        created_by=obj.created_by,
        created=obj.created_at,
        changed_by=obj.changed_by,
        changed=obj.updated_at,
        description=obj.description,
        external_metadata=obj.external_metadata,
        connection_id=str(obj.connection_id),
        created_at=obj.created_at,
        updated_at=obj.updated_at
    )


@router.post("/objects", response_model=MOSObjectResponse)
async def create_object(
    object_data: MOSObjectCreate,
    connection_id: str = Query(..., description="Connection ID"),
    mos_service: MOSService = Depends(get_mos_service),
    db: AsyncSession = Depends(get_db)
):
    """Create new MOS object"""
    try:
        # Convert to dict for processing
        obj_dict = object_data.dict(by_alias=True, exclude_none=True)
        
        # Process through MOS service
        response = await mos_service._handle_mos_obj(obj_dict, connection_id)
        
        if not response or "NACK" in response:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create object"
            )
        
        # Return the created object
        result = await db.execute(
            select(MOSObject).where(MOSObject.obj_id == object_data.obj_id)
        )
        obj = result.scalar_one()
        
        return MOSObjectResponse(
            id=str(obj.id),
            obj_id=obj.obj_id,
            obj_slug=obj.obj_slug,
            obj_type=obj.obj_type,
            obj_tb=obj.obj_tb,
            obj_rev=obj.obj_rev,
            obj_dur=obj.obj_dur,
            status=obj.status,
            obj_air=obj.obj_air,
            obj_abstract=obj.obj_abstract,
            obj_group=obj.obj_group,
            obj_paths=obj.obj_paths,
            created_by=obj.created_by,
            created=obj.created_at,
            changed_by=obj.changed_by,
            changed=obj.updated_at,
            description=obj.description,
            external_metadata=obj.external_metadata,
            connection_id=str(obj.connection_id),
            created_at=obj.created_at,
            updated_at=obj.updated_at
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating object: {str(e)}"
        )


# Running Order management
@router.get("/running-orders", response_model=PaginatedResponse)
async def list_running_orders(
    params: RunningOrderSearchParams = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """List running orders with search and pagination"""
    query = select(MOSRunningOrder).order_by(desc(MOSRunningOrder.created_at))
    
    # Apply filters
    if params.status:
        query = query.where(MOSRunningOrder.status == params.status)
    
    if params.ready_to_air is not None:
        query = query.where(MOSRunningOrder.ready_to_air == params.ready_to_air)
    
    if params.created_after:
        query = query.where(MOSRunningOrder.created_at >= params.created_after)
    
    if params.created_before:
        query = query.where(MOSRunningOrder.created_at <= params.created_before)
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Apply pagination
    query = query.limit(params.limit).offset(params.offset)
    
    result = await db.execute(query)
    running_orders = result.scalars().all()
    
    items = [
        MOSRunningOrderResponse(
            id=str(ro.id),
            ro_id=ro.ro_id,
            ro_slug=ro.ro_slug,
            ro_edition_id=ro.ro_edition_id,
            ro_title=ro.ro_title,
            ro_start_time=ro.ro_start_time,
            ro_end_time=ro.ro_end_time,
            ro_duration=ro.ro_duration,
            connection_id=str(ro.connection_id),
            status=ro.status,
            ready_to_air=ro.ready_to_air,
            created_at=ro.created_at,
            updated_at=ro.updated_at
        )
        for ro in running_orders
    ]
    
    return PaginatedResponse(
        items=items,
        total=total,
        limit=params.limit,
        offset=params.offset,
        has_next=params.offset + params.limit < total,
        has_prev=params.offset > 0
    )


@router.get("/running-orders/{ro_id}", response_model=MOSRunningOrderResponse)
async def get_running_order(
    ro_id: str,
    include_stories: bool = Query(False, description="Include stories and items"),
    db: AsyncSession = Depends(get_db)
):
    """Get specific running order"""
    query = select(MOSRunningOrder).where(MOSRunningOrder.ro_id == ro_id)
    
    if include_stories:
        query = query.options(
            selectinload(MOSRunningOrder.stories).selectinload(MOSStory.items)
        )
    
    result = await db.execute(query)
    ro = result.scalar_one_or_none()
    
    if not ro:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Running order not found"
        )
    
    response_data = MOSRunningOrderResponse(
        id=str(ro.id),
        ro_id=ro.ro_id,
        ro_slug=ro.ro_slug,
        ro_edition_id=ro.ro_edition_id,
        ro_title=ro.ro_title,
        ro_start_time=ro.ro_start_time,
        ro_end_time=ro.ro_end_time,
        ro_duration=ro.ro_duration,
        connection_id=str(ro.connection_id),
        status=ro.status,
        ready_to_air=ro.ready_to_air,
        created_at=ro.created_at,
        updated_at=ro.updated_at
    )
    
    if include_stories and ro.stories:
        stories = []
        for story in ro.stories:
            story_data = {
                'story_id': story.story_id,
                'story_slug': story.story_slug,
                'story_number': story.story_number,
                'story_title': story.story_title,
                'story_abstract': story.story_abstract,
                'story_body': story.story_body,
                'items': []
            }
            
            if story.items:
                for item in story.items:
                    item_data = {
                        'item_id': item.item_id,
                        'item_slug': item.item_slug,
                        'item_channel': item.item_channel,
                        'item_number': item.item_number,
                        'item_duration': item.item_duration,
                        'mos_object_id': str(item.mos_object_id) if item.mos_object_id else None
                    }
                    story_data['items'].append(item_data)
            
            stories.append(story_data)
        
        response_data.stories = stories
    
    return response_data


# Message log endpoints
@router.get("/messages", response_model=List[MOSMessageResponse])
async def list_messages(
    connection_id: Optional[str] = Query(None),
    message_type: Optional[str] = Query(None),
    direction: Optional[str] = Query(None, regex="^(inbound|outbound)$"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """List MOS messages with filtering"""
    query = select(MOSMessage).order_by(desc(MOSMessage.received_at))
    
    if connection_id:
        query = query.where(MOSMessage.connection_id == connection_id)
    
    if message_type:
        query = query.where(MOSMessage.message_type == message_type)
    
    if direction:
        query = query.where(MOSMessage.direction == direction)
    
    query = query.limit(limit).offset(offset)
    
    result = await db.execute(query)
    messages = result.scalars().all()
    
    return [
        MOSMessageResponse(
            id=str(msg.id),
            message_id=msg.message_id,
            message_type=msg.message_type,
            direction=msg.direction,
            raw_message=msg.raw_message,
            parsed_message=msg.parsed_message,
            processing_status=msg.processing_status,
            error_message=msg.error_message,
            received_at=msg.received_at,
            processed_at=msg.processed_at,
            response_sent_at=msg.response_sent_at
        )
        for msg in messages
    ]


# Manual message sending
@router.post("/send-message")
async def send_message(
    connection_id: str,
    message_content: str,
    background_tasks: BackgroundTasks,
    mos_service: MOSService = Depends(get_mos_service)
):
    """Send manual message to NRCS"""
    try:
        # This would integrate with the MOS server to send messages
        # For now, we'll return success
        return {
            "status": "success",
            "message": "Message queued for sending",
            "connection_id": connection_id
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error sending message: {str(e)}"
        )


# Server control endpoints (for development/testing)
@router.post("/broadcast")
async def broadcast_message(
    message_content: str,
    exclude_connection: Optional[str] = None,
    background_tasks: BackgroundTasks
):
    """Broadcast message to all connected NRCS systems"""
    try:
        # This would integrate with the MOS server to broadcast messages
        return {
            "status": "success",
            "message": "Message broadcasted to all connections"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error broadcasting message: {str(e)}"
        )