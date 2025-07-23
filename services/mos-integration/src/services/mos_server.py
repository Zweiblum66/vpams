"""MOS TCP Server for handling NRCS connections"""

import asyncio
import logging
import uuid
from typing import Dict, Optional, Set
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
import redis.asyncio as redis

from ..core.config import settings
from ..db.base import AsyncSessionLocal
from ..db.models import MOSConnection
from ..models.schemas import ConnectionStatus
from .mos_service import MOSService


class MOSConnectionHandler:
    """Handler for individual MOS connections"""
    
    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter,
                 server: 'MOSServer'):
        self.reader = reader
        self.writer = writer
        self.server = server
        self.connection_id = str(uuid.uuid4())
        self.nrcs_id: Optional[str] = None
        self.logger = logging.getLogger(f"{__name__}.{self.connection_id}")
        self.is_connected = True
        self.last_activity = datetime.utcnow()
        
        # Get client address
        try:
            self.client_address = self.writer.get_extra_info('peername')
        except:
            self.client_address = ('unknown', 0)
        
        self.logger.info(f"New connection from {self.client_address}")
    
    async def handle(self):
        """Handle the MOS connection"""
        try:
            # Register connection
            await self._register_connection()
            
            # Start heartbeat task
            heartbeat_task = asyncio.create_task(self._heartbeat_monitor())
            
            # Main message processing loop
            while self.is_connected:
                try:
                    # Read message length (MOS protocol uses length-prefixed messages)
                    length_data = await asyncio.wait_for(
                        self.reader.read(4), 
                        timeout=settings.mos_timeout
                    )
                    
                    if not length_data:
                        break
                    
                    # Parse message length (big-endian 32-bit integer)
                    message_length = int.from_bytes(length_data, byteorder='big')
                    
                    if message_length > settings.max_file_size_mb * 1024 * 1024:
                        self.logger.error(f"Message too large: {message_length} bytes")
                        break
                    
                    # Read the actual message
                    message_data = await asyncio.wait_for(
                        self.reader.read(message_length),
                        timeout=settings.mos_timeout
                    )
                    
                    if len(message_data) != message_length:
                        self.logger.error("Incomplete message received")
                        break
                    
                    # Decode message
                    try:
                        message = message_data.decode('utf-8')
                    except UnicodeDecodeError:
                        message = message_data.decode('latin-1')
                    
                    self.last_activity = datetime.utcnow()
                    
                    # Process the message
                    await self._process_message(message)
                    
                except asyncio.TimeoutError:
                    self.logger.warning("Connection timeout")
                    break
                except Exception as e:
                    self.logger.error(f"Error processing message: {str(e)}")
                    break
            
            # Cancel heartbeat task
            heartbeat_task.cancel()
            
        except Exception as e:
            self.logger.error(f"Connection error: {str(e)}")
        finally:
            await self._cleanup()
    
    async def _register_connection(self):
        """Register the connection in the database"""
        try:
            async with AsyncSessionLocal() as db:
                # Create connection record
                connection = MOSConnection(
                    id=self.connection_id,
                    nrcs_id=f"nrcs_{self.client_address[0]}_{self.client_address[1]}",
                    nrcs_description=f"NRCS connection from {self.client_address[0]}",
                    connection_status=ConnectionStatus.CONNECTED,
                    last_heartbeat=datetime.utcnow()
                )
                
                db.add(connection)
                await db.commit()
                
                # Add to server's connection tracking
                self.server.active_connections[self.connection_id] = self
                
        except Exception as e:
            self.logger.error(f"Error registering connection: {str(e)}")
    
    async def _process_message(self, message: str):
        """Process incoming MOS message"""
        try:
            async with AsyncSessionLocal() as db:
                redis_client = redis.from_url(settings.redis_url)
                
                try:
                    mos_service = MOSService(db, redis_client)
                    response = await mos_service.process_message(message, self.connection_id)
                    
                    # Send response if generated
                    if response:
                        await self._send_message(response)
                        
                finally:
                    await redis_client.close()
                    
        except Exception as e:
            self.logger.error(f"Error processing message: {str(e)}")
    
    async def _send_message(self, message: str):
        """Send message to NRCS"""
        try:
            message_bytes = message.encode('utf-8')
            message_length = len(message_bytes)
            
            # Send length prefix
            length_bytes = message_length.to_bytes(4, byteorder='big')
            self.writer.write(length_bytes)
            
            # Send message
            self.writer.write(message_bytes)
            await self.writer.drain()
            
            self.logger.debug(f"Sent message: {len(message_bytes)} bytes")
            
        except Exception as e:
            self.logger.error(f"Error sending message: {str(e)}")
            self.is_connected = False
    
    async def _heartbeat_monitor(self):
        """Monitor connection health with heartbeats"""
        try:
            while self.is_connected:
                await asyncio.sleep(settings.mos_heartbeat_interval)
                
                # Check if connection is still alive
                current_time = datetime.utcnow()
                inactive_time = (current_time - self.last_activity).total_seconds()
                
                if inactive_time > settings.mos_timeout:
                    self.logger.warning("Connection inactive, closing")
                    self.is_connected = False
                    break
                
                # Update last heartbeat in database
                try:
                    async with AsyncSessionLocal() as db:
                        await db.execute(
                            update(MOSConnection)
                            .where(MOSConnection.id == self.connection_id)
                            .values(last_heartbeat=current_time)
                        )
                        await db.commit()
                except Exception as e:
                    self.logger.error(f"Error updating heartbeat: {str(e)}")
                    
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.logger.error(f"Heartbeat monitor error: {str(e)}")
    
    async def _cleanup(self):
        """Clean up connection resources"""
        try:
            self.is_connected = False
            
            # Close writer
            if self.writer and not self.writer.is_closing():
                self.writer.close()
                await self.writer.wait_closed()
            
            # Update connection status in database
            async with AsyncSessionLocal() as db:
                await db.execute(
                    update(MOSConnection)
                    .where(MOSConnection.id == self.connection_id)
                    .values(connection_status=ConnectionStatus.DISCONNECTED)
                )
                await db.commit()
            
            # Remove from server tracking
            if self.connection_id in self.server.active_connections:
                del self.server.active_connections[self.connection_id]
            
            self.logger.info(f"Connection closed: {self.client_address}")
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {str(e)}")


class MOSServer:
    """MOS TCP Server"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.active_connections: Dict[str, MOSConnectionHandler] = {}
        self.server: Optional[asyncio.Server] = None
        self.is_running = False
    
    async def start(self):
        """Start the MOS server"""
        try:
            self.logger.info(f"Starting MOS server on port {settings.mos_listen_port}")
            
            self.server = await asyncio.start_server(
                self._handle_connection,
                host='0.0.0.0',
                port=settings.mos_listen_port,
                reuse_address=True,
                reuse_port=True
            )
            
            self.is_running = True
            self.logger.info(f"MOS server started on {settings.mos_listen_port}")
            
            # Start monitoring task
            asyncio.create_task(self._monitor_connections())
            
            async with self.server:
                await self.server.serve_forever()
                
        except Exception as e:
            self.logger.error(f"Error starting MOS server: {str(e)}")
            raise
    
    async def stop(self):
        """Stop the MOS server"""
        try:
            self.logger.info("Stopping MOS server")
            self.is_running = False
            
            # Close all active connections
            for connection_id, handler in list(self.active_connections.items()):
                handler.is_connected = False
                if handler.writer and not handler.writer.is_closing():
                    handler.writer.close()
                    await handler.writer.wait_closed()
            
            # Stop server
            if self.server:
                self.server.close()
                await self.server.wait_closed()
            
            self.logger.info("MOS server stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping MOS server: {str(e)}")
    
    async def _handle_connection(self, reader: asyncio.StreamReader, 
                                writer: asyncio.StreamWriter):
        """Handle new MOS connection"""
        handler = MOSConnectionHandler(reader, writer, self)
        await handler.handle()
    
    async def _monitor_connections(self):
        """Monitor active connections and clean up stale ones"""
        while self.is_running:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                current_time = datetime.utcnow()
                stale_connections = []
                
                for connection_id, handler in self.active_connections.items():
                    inactive_time = (current_time - handler.last_activity).total_seconds()
                    if inactive_time > settings.mos_timeout * 2:  # Double timeout for cleanup
                        stale_connections.append(connection_id)
                
                # Clean up stale connections
                for connection_id in stale_connections:
                    handler = self.active_connections.get(connection_id)
                    if handler:
                        handler.is_connected = False
                        await handler._cleanup()
                
                if stale_connections:
                    self.logger.info(f"Cleaned up {len(stale_connections)} stale connections")
                
            except Exception as e:
                self.logger.error(f"Error monitoring connections: {str(e)}")
    
    def get_connection_count(self) -> int:
        """Get number of active connections"""
        return len(self.active_connections)
    
    def get_connection_info(self) -> Dict[str, Dict]:
        """Get information about active connections"""
        info = {}
        for connection_id, handler in self.active_connections.items():
            info[connection_id] = {
                'client_address': handler.client_address,
                'nrcs_id': handler.nrcs_id,
                'connected_at': handler.last_activity.isoformat(),
                'is_connected': handler.is_connected
            }
        return info
    
    async def broadcast_message(self, message: str, exclude_connection: Optional[str] = None):
        """Broadcast message to all connected NRCS systems"""
        success_count = 0
        error_count = 0
        
        for connection_id, handler in self.active_connections.items():
            if exclude_connection and connection_id == exclude_connection:
                continue
                
            try:
                if handler.is_connected:
                    await handler._send_message(message)
                    success_count += 1
            except Exception as e:
                self.logger.error(f"Error broadcasting to {connection_id}: {str(e)}")
                error_count += 1
        
        self.logger.info(f"Broadcast complete: {success_count} success, {error_count} errors")
        return success_count, error_count