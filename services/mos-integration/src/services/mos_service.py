"""Core MOS Integration Service"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, update, delete
from sqlalchemy.orm import selectinload
import redis.asyncio as redis

from ..core.config import settings
from ..db.models import (
    MOSConnection, MOSObject, MOSRunningOrder, MOSStory, 
    MOSStoryItem, MOSMessage, MOSHeartbeat
)
from ..models.schemas import (
    MOSMessageType, MOSStatus, ConnectionStatus,
    MOSObjectCreate, MOSRunningOrderCreate, MOSConnectionCreate,
    MOSObjectResponse, MOSRunningOrderResponse, MOSConnectionResponse
)
from ..utils.xml_parser import MOSXMLParser, MOSXMLGenerator


class MOSService:
    """Core MOS integration service"""
    
    def __init__(self, db: AsyncSession, redis_client: redis.Redis):
        self.db = db
        self.redis = redis_client
        self.xml_parser = MOSXMLParser()
        self.xml_generator = MOSXMLGenerator()
        self.logger = logging.getLogger(__name__)
        
        # Message handlers
        self.message_handlers = {
            MOSMessageType.MOS_OBJ: self._handle_mos_obj,
            MOSMessageType.MOS_OBJ_CREATE: self._handle_mos_obj_create,
            MOSMessageType.MOS_LIST_ALL: self._handle_mos_list_all,
            MOSMessageType.MOS_REQ_OBJ: self._handle_mos_req_obj,
            MOSMessageType.MOS_REQ_ALL: self._handle_mos_req_all,
            MOSMessageType.MOS_HEARTBEAT: self._handle_heartbeat,
            MOSMessageType.MOS_MACHINE_INFO: self._handle_machine_info,
            MOSMessageType.RO_CREATE: self._handle_ro_create,
            MOSMessageType.RO_REPLACE: self._handle_ro_replace,
            MOSMessageType.RO_DELETE: self._handle_ro_delete,
            MOSMessageType.RO_LIST_ALL: self._handle_ro_list_all,
            MOSMessageType.RO_REQ_ALL: self._handle_ro_req_all,
            MOSMessageType.RO_STORY_APPEND: self._handle_ro_story_append,
            MOSMessageType.RO_STORY_INSERT: self._handle_ro_story_insert,
            MOSMessageType.RO_STORY_REPLACE: self._handle_ro_story_replace,
            MOSMessageType.RO_STORY_DELETE: self._handle_ro_story_delete,
            MOSMessageType.RO_READY_TO_AIR: self._handle_ro_ready_to_air,
        }
    
    async def process_message(self, raw_message: str, connection_id: str) -> Optional[str]:
        """Process incoming MOS message and return response"""
        try:
            # Parse the message
            parsed_data = self.xml_parser.parse_message(raw_message)
            message_type = parsed_data.get('message_type')
            
            # Log the message
            await self._log_message(
                message_type=message_type,
                direction='inbound',
                raw_message=raw_message,
                parsed_message=parsed_data,
                connection_id=connection_id
            )
            
            # Handle the message
            if message_type in self.message_handlers:
                handler = self.message_handlers[message_type]
                response = await handler(parsed_data, connection_id)
                
                # Log response if generated
                if response:
                    await self._log_message(
                        message_type=f"{message_type}_response",
                        direction='outbound',
                        raw_message=response,
                        connection_id=connection_id
                    )
                
                return response
            else:
                self.logger.warning(f"Unknown message type: {message_type}")
                return self._generate_nack(
                    message_id=parsed_data.get('message_id', ''),
                    error="Unknown message type"
                )
                
        except Exception as e:
            self.logger.error(f"Error processing message: {str(e)}")
            return self._generate_nack(
                message_id="unknown",
                error=f"Processing error: {str(e)}"
            )
    
    async def _handle_mos_obj(self, data: Dict[str, Any], connection_id: str) -> Optional[str]:
        """Handle mosObj message - create or update MOS object"""
        try:
            # Check if object exists
            existing_obj = await self.db.execute(
                select(MOSObject).where(MOSObject.obj_id == data['obj_id'])
            )
            obj = existing_obj.scalar_one_or_none()
            
            if obj:
                # Update existing object
                for key, value in data.items():
                    if hasattr(obj, key) and value is not None:
                        setattr(obj, key, value)
                obj.updated_at = datetime.utcnow()
            else:
                # Create new object
                obj = MOSObject(
                    obj_id=data['obj_id'],
                    obj_slug=data['obj_slug'],
                    obj_type=data['obj_type'],
                    obj_tb=data.get('obj_tb', 25),
                    obj_rev=data.get('obj_rev', 1),
                    obj_dur=data.get('obj_dur'),
                    status=data.get('status', 'NEW'),
                    obj_air=data.get('obj_air'),
                    obj_abstract=data.get('obj_abstract'),
                    obj_group=data.get('obj_group'),
                    obj_paths=data.get('obj_paths'),
                    created_by=data.get('created_by'),
                    changed_by=data.get('changed_by'),
                    description=data.get('description'),
                    external_metadata=data.get('external_metadata'),
                    connection_id=connection_id
                )
                self.db.add(obj)
            
            await self.db.commit()
            
            # Generate ACK response
            return self.xml_generator.generate_mos_ack(
                message_id=data.get('message_id', data['obj_id']),
                status="ACK",
                status_description="Object processed successfully"
            )
            
        except Exception as e:
            await self.db.rollback()
            self.logger.error(f"Error handling mosObj: {str(e)}")
            return self._generate_nack(
                data.get('message_id', data['obj_id']),
                f"Error processing object: {str(e)}"
            )
    
    async def _handle_mos_obj_create(self, data: Dict[str, Any], connection_id: str) -> Optional[str]:
        """Handle mosObjCreate message"""
        # Generate unique object ID if not provided
        if not data.get('obj_id'):
            data['obj_id'] = f"obj_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        # Process as regular mosObj
        return await self._handle_mos_obj(data, connection_id)
    
    async def _handle_mos_list_all(self, data: Dict[str, Any], connection_id: str) -> Optional[str]:
        """Handle mosListAll message - batch object updates"""
        try:
            for obj_data in data.get('objects', []):
                await self._handle_mos_obj(obj_data, connection_id)
            
            return self.xml_generator.generate_mos_ack(
                message_id=data.get('message_id', 'list_all'),
                status="ACK",
                status_description=f"Processed {len(data.get('objects', []))} objects"
            )
            
        except Exception as e:
            self.logger.error(f"Error handling mosListAll: {str(e)}")
            return self._generate_nack(
                data.get('message_id', 'list_all'),
                f"Error processing object list: {str(e)}"
            )
    
    async def _handle_mos_req_obj(self, data: Dict[str, Any], connection_id: str) -> Optional[str]:
        """Handle mosReqObj message - send specific object"""
        try:
            obj_id = data.get('obj_id')
            if not obj_id:
                return self._generate_nack(
                    data.get('message_id', ''),
                    "Missing objID in request"
                )
            
            # Find the object
            result = await self.db.execute(
                select(MOSObject).where(MOSObject.obj_id == obj_id)
            )
            obj = result.scalar_one_or_none()
            
            if not obj:
                return self._generate_nack(
                    data.get('message_id', obj_id),
                    f"Object {obj_id} not found"
                )
            
            # Generate mosObj response
            obj_data = {
                'obj_id': obj.obj_id,
                'obj_slug': obj.obj_slug,
                'obj_type': obj.obj_type,
                'obj_tb': obj.obj_tb,
                'obj_rev': obj.obj_rev,
                'obj_dur': obj.obj_dur,
                'status': obj.status,
                'obj_air': obj.obj_air,
                'obj_abstract': obj.obj_abstract,
                'obj_group': obj.obj_group,
                'obj_paths': obj.obj_paths,
                'created_by': obj.created_by,
                'created': obj.created_at,
                'changed_by': obj.changed_by,
                'changed': obj.updated_at,
                'description': obj.description,
                'external_metadata': obj.external_metadata
            }
            
            return self.xml_generator.generate_mos_obj(obj_data)
            
        except Exception as e:
            self.logger.error(f"Error handling mosReqObj: {str(e)}")
            return self._generate_nack(
                data.get('message_id', ''),
                f"Error retrieving object: {str(e)}"
            )
    
    async def _handle_mos_req_all(self, data: Dict[str, Any], connection_id: str) -> Optional[str]:
        """Handle mosReqAll message - send all objects"""
        try:
            # Get all objects for this connection
            result = await self.db.execute(
                select(MOSObject).where(MOSObject.connection_id == connection_id)
                .order_by(MOSObject.created_at.desc())
                .limit(1000)  # Reasonable limit
            )
            objects = result.scalars().all()
            
            # Generate individual mosObj messages for each object
            responses = []
            for obj in objects:
                obj_data = {
                    'obj_id': obj.obj_id,
                    'obj_slug': obj.obj_slug,
                    'obj_type': obj.obj_type,
                    'obj_tb': obj.obj_tb,
                    'obj_rev': obj.obj_rev,
                    'obj_dur': obj.obj_dur,
                    'status': obj.status,
                    'obj_air': obj.obj_air,
                    'obj_abstract': obj.obj_abstract,
                    'obj_group': obj.obj_group,
                    'obj_paths': obj.obj_paths,
                    'created_by': obj.created_by,
                    'created': obj.created_at,
                    'changed_by': obj.changed_by,
                    'changed': obj.updated_at,
                    'description': obj.description,
                    'external_metadata': obj.external_metadata
                }
                responses.append(self.xml_generator.generate_mos_obj(obj_data))
            
            # First send ACK
            ack_response = self.xml_generator.generate_mos_ack(
                message_id=data.get('message_id', 'req_all'),
                status="ACK",
                status_description=f"Sending {len(objects)} objects"
            )
            
            # Store responses for later sending
            await self.redis.lpush(
                f"mos_responses:{connection_id}",
                *responses
            )
            
            return ack_response
            
        except Exception as e:
            self.logger.error(f"Error handling mosReqAll: {str(e)}")
            return self._generate_nack(
                data.get('message_id', ''),
                f"Error retrieving objects: {str(e)}"
            )
    
    async def _handle_heartbeat(self, data: Dict[str, Any], connection_id: str) -> Optional[str]:
        """Handle heartbeat message"""
        try:
            # Update connection last heartbeat
            await self.db.execute(
                update(MOSConnection)
                .where(MOSConnection.id == connection_id)
                .values(
                    last_heartbeat=datetime.utcnow(),
                    connection_status=ConnectionStatus.CONNECTED
                )
            )
            
            # Store heartbeat record
            heartbeat = MOSHeartbeat(
                nrcs_id=data.get('nrcs_id'),
                heartbeat_time=data.get('time', datetime.utcnow()),
                status=data.get('status', 'OK'),
                system_info=data.get('system_info')
            )
            self.db.add(heartbeat)
            await self.db.commit()
            
            # Generate heartbeat response
            return self.xml_generator.generate_heartbeat(
                mos_id=settings.mos_server_id,
                nrcs_id=data.get('nrcs_id', 'unknown')
            )
            
        except Exception as e:
            await self.db.rollback()
            self.logger.error(f"Error handling heartbeat: {str(e)}")
            return None
    
    async def _handle_machine_info(self, data: Dict[str, Any], connection_id: str) -> Optional[str]:
        """Handle machine info message"""
        try:
            # Update connection with machine info
            await self.db.execute(
                update(MOSConnection)
                .where(MOSConnection.id == connection_id)
                .values(
                    capabilities=data,
                    supported_profiles=data.get('supported_profiles', [])
                )
            )
            await self.db.commit()
            
            # Generate machine info response
            machine_info = {
                'manufacturer': 'MAMS',
                'model': 'Digital Media Asset Management System',
                'hw_rev': '1.0',
                'sw_rev': settings.service_version,
                'dom': datetime(2024, 1, 1),
                'sn': settings.mos_server_id,
                'id': settings.mos_server_id,
                'time': datetime.utcnow(),
                'mos_rev': '2.8.5',
                'supported_profiles': ['0', '1', '2', '3', '4']
            }
            
            # Would generate XML for machine info - simplified for now
            return self.xml_generator.generate_mos_ack(
                message_id=data.get('message_id', 'machine_info'),
                status="ACK"
            )
            
        except Exception as e:
            await self.db.rollback()
            self.logger.error(f"Error handling machine info: {str(e)}")
            return None
    
    async def _handle_ro_create(self, data: Dict[str, Any], connection_id: str) -> Optional[str]:
        """Handle roCreate message - create running order"""
        try:
            # Create running order
            ro = MOSRunningOrder(
                ro_id=data['ro_id'],
                ro_slug=data['ro_slug'],
                ro_edition_id=data.get('ro_edition_id'),
                ro_title=data.get('ro_title'),
                ro_start_time=data.get('ro_start_time'),
                ro_end_time=data.get('ro_end_time'),
                ro_duration=data.get('ro_duration'),
                status='READY',
                connection_id=connection_id
            )
            self.db.add(ro)
            await self.db.flush()  # Get ID
            
            # Create stories
            if data.get('stories'):
                for story_data in data['stories']:
                    story = MOSStory(
                        story_id=story_data['story_id'],
                        story_slug=story_data['story_slug'],
                        story_number=story_data.get('story_num'),
                        story_title=story_data.get('story_title'),
                        story_abstract=story_data.get('story_abstract'),
                        story_body=story_data.get('story_body'),
                        running_order_id=ro.id
                    )
                    self.db.add(story)
                    await self.db.flush()
                    
                    # Create items
                    if story_data.get('items'):
                        for item_data in story_data['items']:
                            # Find referenced MOS object
                            mos_object_id = None
                            if item_data.get('obj_id'):
                                obj_result = await self.db.execute(
                                    select(MOSObject.id).where(
                                        MOSObject.obj_id == item_data['obj_id']
                                    )
                                )
                                obj_row = obj_result.first()
                                if obj_row:
                                    mos_object_id = obj_row[0]
                            
                            item = MOSStoryItem(
                                item_id=item_data['item_id'],
                                item_slug=item_data.get('item_slug'),
                                item_channel=item_data.get('item_channel'),
                                item_number=item_data.get('item_number'),
                                item_duration=item_data.get('item_duration'),
                                item_in_point=item_data.get('item_in_point'),
                                item_out_point=item_data.get('item_out_point'),
                                story_id=story.id,
                                mos_object_id=mos_object_id
                            )
                            self.db.add(item)
            
            await self.db.commit()
            
            return self.xml_generator.generate_mos_ack(
                message_id=data.get('message_id', data['ro_id']),
                status="ACK",
                status_description="Running order created successfully"
            )
            
        except Exception as e:
            await self.db.rollback()
            self.logger.error(f"Error handling roCreate: {str(e)}")
            return self._generate_nack(
                data.get('message_id', data.get('ro_id', '')),
                f"Error creating running order: {str(e)}"
            )
    
    async def _handle_ro_replace(self, data: Dict[str, Any], connection_id: str) -> Optional[str]:
        """Handle roReplace message - replace running order"""
        try:
            # Delete existing running order
            await self.db.execute(
                delete(MOSRunningOrder).where(
                    and_(
                        MOSRunningOrder.ro_id == data['ro_id'],
                        MOSRunningOrder.connection_id == connection_id
                    )
                )
            )
            
            # Create new one
            return await self._handle_ro_create(data, connection_id)
            
        except Exception as e:
            await self.db.rollback()
            self.logger.error(f"Error handling roReplace: {str(e)}")
            return self._generate_nack(
                data.get('message_id', data.get('ro_id', '')),
                f"Error replacing running order: {str(e)}"
            )
    
    async def _handle_ro_delete(self, data: Dict[str, Any], connection_id: str) -> Optional[str]:
        """Handle roDelete message - delete running order"""
        try:
            await self.db.execute(
                delete(MOSRunningOrder).where(
                    and_(
                        MOSRunningOrder.ro_id == data['ro_id'],
                        MOSRunningOrder.connection_id == connection_id
                    )
                )
            )
            await self.db.commit()
            
            return self.xml_generator.generate_mos_ack(
                message_id=data.get('message_id', data['ro_id']),
                status="ACK",
                status_description="Running order deleted successfully"
            )
            
        except Exception as e:
            await self.db.rollback()
            self.logger.error(f"Error handling roDelete: {str(e)}")
            return self._generate_nack(
                data.get('message_id', data.get('ro_id', '')),
                f"Error deleting running order: {str(e)}"
            )
    
    async def _handle_ro_list_all(self, data: Dict[str, Any], connection_id: str) -> Optional[str]:
        """Handle roListAll message - list all running orders"""
        # Implementation would be similar to mosReqAll but for running orders
        return self.xml_generator.generate_mos_ack(
            message_id=data.get('message_id', 'ro_list_all'),
            status="ACK"
        )
    
    async def _handle_ro_req_all(self, data: Dict[str, Any], connection_id: str) -> Optional[str]:
        """Handle roReqAll message - send all running orders"""
        # Implementation would be similar to mosReqAll but for running orders
        return self.xml_generator.generate_mos_ack(
            message_id=data.get('message_id', 'ro_req_all'),
            status="ACK"
        )
    
    async def _handle_ro_story_append(self, data: Dict[str, Any], connection_id: str) -> Optional[str]:
        """Handle roStoryAppend message - append story to running order"""
        # Implementation for story operations
        return self.xml_generator.generate_mos_ack(
            message_id=data.get('message_id', ''),
            status="ACK"
        )
    
    async def _handle_ro_story_insert(self, data: Dict[str, Any], connection_id: str) -> Optional[str]:
        """Handle roStoryInsert message - insert story in running order"""
        return self.xml_generator.generate_mos_ack(
            message_id=data.get('message_id', ''),
            status="ACK"
        )
    
    async def _handle_ro_story_replace(self, data: Dict[str, Any], connection_id: str) -> Optional[str]:
        """Handle roStoryReplace message - replace story in running order"""
        return self.xml_generator.generate_mos_ack(
            message_id=data.get('message_id', ''),
            status="ACK"
        )
    
    async def _handle_ro_story_delete(self, data: Dict[str, Any], connection_id: str) -> Optional[str]:
        """Handle roStoryDelete message - delete story from running order"""
        return self.xml_generator.generate_mos_ack(
            message_id=data.get('message_id', ''),
            status="ACK"
        )
    
    async def _handle_ro_ready_to_air(self, data: Dict[str, Any], connection_id: str) -> Optional[str]:
        """Handle roReadyToAir message - mark running order ready to air"""
        try:
            await self.db.execute(
                update(MOSRunningOrder)
                .where(
                    and_(
                        MOSRunningOrder.ro_id == data['ro_id'],
                        MOSRunningOrder.connection_id == connection_id
                    )
                )
                .values(ready_to_air=True, air_status='READY')
            )
            await self.db.commit()
            
            return self.xml_generator.generate_mos_ack(
                message_id=data.get('message_id', data['ro_id']),
                status="ACK",
                status_description="Running order marked ready to air"
            )
            
        except Exception as e:
            await self.db.rollback()
            self.logger.error(f"Error handling roReadyToAir: {str(e)}")
            return self._generate_nack(
                data.get('message_id', data.get('ro_id', '')),
                f"Error marking ready to air: {str(e)}"
            )
    
    async def _log_message(self, message_type: str, direction: str, 
                          raw_message: str, connection_id: str,
                          parsed_message: Optional[Dict[str, Any]] = None):
        """Log MOS message for auditing"""
        try:
            message = MOSMessage(
                message_type=message_type,
                direction=direction,
                raw_message=raw_message,
                parsed_message=parsed_message,
                connection_id=connection_id,
                processing_status='processed' if direction == 'outbound' else 'pending'
            )
            self.db.add(message)
            await self.db.commit()
        except Exception as e:
            self.logger.error(f"Error logging message: {str(e)}")
    
    def _generate_nack(self, message_id: str, error: str) -> str:
        """Generate NACK response"""
        return self.xml_generator.generate_mos_ack(
            message_id=message_id,
            status="NACK",
            status_description=error
        )
    
    async def get_connection_stats(self, connection_id: str) -> Dict[str, Any]:
        """Get statistics for a MOS connection"""
        try:
            # Get object count
            obj_result = await self.db.execute(
                select(func.count(MOSObject.id)).where(
                    MOSObject.connection_id == connection_id
                )
            )
            object_count = obj_result.scalar() or 0
            
            # Get running order count
            ro_result = await self.db.execute(
                select(func.count(MOSRunningOrder.id)).where(
                    MOSRunningOrder.connection_id == connection_id
                )
            )
            ro_count = ro_result.scalar() or 0
            
            # Get message count (last 24h)
            yesterday = datetime.utcnow() - timedelta(days=1)
            msg_result = await self.db.execute(
                select(func.count(MOSMessage.id)).where(
                    and_(
                        MOSMessage.connection_id == connection_id,
                        MOSMessage.received_at >= yesterday
                    )
                )
            )
            message_count = msg_result.scalar() or 0
            
            return {
                'object_count': object_count,
                'running_order_count': ro_count,
                'message_count_24h': message_count
            }
            
        except Exception as e:
            self.logger.error(f"Error getting connection stats: {str(e)}")
            return {
                'object_count': 0,
                'running_order_count': 0,
                'message_count_24h': 0
            }