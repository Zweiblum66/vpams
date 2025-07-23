"""
Edit-While-Ingest Service for enabling access to media while still being ingested
"""

import os
import asyncio
from typing import Dict, Optional, List, Set, Tuple
from pathlib import Path
from datetime import datetime, timedelta
import aiofiles
import structlog

from ..models.schemas import (
    IngestJob, IngestStatus, FileMetadata, TechnicalMetadata
)
from ..core.exceptions import EditWhileIngestError, FileNotFoundError
from ..core.config import settings
from ..core.logging import get_logger

logger = get_logger(__name__)


class EditWhileIngestService:
    """Service for enabling edit-while-ingest functionality"""
    
    def __init__(self):
        self.active_ingests: Dict[str, 'ActiveIngestSession'] = {}
        self.proxy_cache: Dict[str, str] = {}  # Maps job_id to proxy paths
        self.access_locks: Dict[str, asyncio.Lock] = {}
        
        # Configuration
        self.chunk_size = 1024 * 1024 * 10  # 10MB chunks
        self.proxy_update_interval = 10.0  # seconds
        self.partial_file_extension = ".partial"
        self.metadata_update_interval = 5.0  # seconds
        
    async def register_active_ingest(
        self,
        job: IngestJob,
        source_path: str,
        destination_path: str
    ) -> 'ActiveIngestSession':
        """Register a new active ingest for edit-while-ingest access"""
        try:
            logger.info(
                "registering_active_ingest",
                job_id=job.id,
                source_path=source_path,
                destination_path=destination_path
            )
            
            # Create active ingest session
            session = ActiveIngestSession(
                job_id=job.id,
                source_path=source_path,
                destination_path=destination_path,
                service=self
            )
            
            self.active_ingests[job.id] = session
            self.access_locks[job.id] = asyncio.Lock()
            
            # Start monitoring the ingest
            asyncio.create_task(session.start_monitoring())
            
            return session
            
        except Exception as e:
            logger.error(
                "active_ingest_registration_failed",
                error=str(e),
                job_id=job.id
            )
            raise EditWhileIngestError(f"Failed to register active ingest: {str(e)}")
    
    async def get_partial_file_access(
        self,
        job_id: str,
        byte_range: Optional[Tuple[int, int]] = None
    ) -> Optional[bytes]:
        """Get access to partially ingested file data"""
        try:
            if job_id not in self.active_ingests:
                logger.warning("inactive_ingest_access_attempt", job_id=job_id)
                return None
            
            session = self.active_ingests[job_id]
            
            async with self.access_locks[job_id]:
                return await session.read_partial_file(byte_range)
                
        except Exception as e:
            logger.error(
                "partial_file_access_failed",
                error=str(e),
                job_id=job_id
            )
            return None
    
    async def get_ingest_metadata(self, job_id: str) -> Optional[Dict]:
        """Get current metadata for an active ingest"""
        try:
            if job_id not in self.active_ingests:
                return None
            
            session = self.active_ingests[job_id]
            return await session.get_current_metadata()
            
        except Exception as e:
            logger.error(
                "metadata_retrieval_failed",
                error=str(e),
                job_id=job_id
            )
            return None
    
    async def get_partial_proxy_path(self, job_id: str) -> Optional[str]:
        """Get path to the current partial proxy file"""
        try:
            if job_id not in self.active_ingests:
                return None
            
            session = self.active_ingests[job_id]
            return await session.get_proxy_path()
            
        except Exception as e:
            logger.error(
                "proxy_path_retrieval_failed",
                error=str(e),
                job_id=job_id
            )
            return None
    
    async def request_priority_chunk(
        self,
        job_id: str,
        byte_offset: int,
        chunk_size: int
    ) -> bool:
        """Request priority processing of a specific chunk for editing"""
        try:
            if job_id not in self.active_ingests:
                return False
            
            session = self.active_ingests[job_id]
            return await session.prioritize_chunk(byte_offset, chunk_size)
            
        except Exception as e:
            logger.error(
                "priority_chunk_request_failed",
                error=str(e),
                job_id=job_id,
                byte_offset=byte_offset
            )
            return False
    
    async def unregister_active_ingest(self, job_id: str):
        """Unregister an active ingest when complete or failed"""
        try:
            if job_id in self.active_ingests:
                session = self.active_ingests[job_id]
                await session.stop_monitoring()
                
                del self.active_ingests[job_id]
                
                if job_id in self.access_locks:
                    del self.access_locks[job_id]
                
                if job_id in self.proxy_cache:
                    del self.proxy_cache[job_id]
                
                logger.info("active_ingest_unregistered", job_id=job_id)
                
        except Exception as e:
            logger.error(
                "active_ingest_unregister_failed",
                error=str(e),
                job_id=job_id
            )
    
    async def get_editable_segments(self, job_id: str) -> List[Dict]:
        """Get list of segments that are ready for editing"""
        try:
            if job_id not in self.active_ingests:
                return []
            
            session = self.active_ingests[job_id]
            return await session.get_available_segments()
            
        except Exception as e:
            logger.error(
                "editable_segments_retrieval_failed",
                error=str(e),
                job_id=job_id
            )
            return []
    
    async def create_edit_session(
        self,
        job_id: str,
        start_time: float,
        end_time: float
    ) -> Optional[str]:
        """Create an edit session for a specific time range"""
        try:
            if job_id not in self.active_ingests:
                return None
            
            session = self.active_ingests[job_id]
            edit_session_id = await session.create_edit_session(start_time, end_time)
            
            logger.info(
                "edit_session_created",
                job_id=job_id,
                edit_session_id=edit_session_id,
                start_time=start_time,
                end_time=end_time
            )
            
            return edit_session_id
            
        except Exception as e:
            logger.error(
                "edit_session_creation_failed",
                error=str(e),
                job_id=job_id
            )
            return None


class ActiveIngestSession:
    """Represents an active ingest session with edit-while-ingest capability"""
    
    def __init__(
        self,
        job_id: str,
        source_path: str,
        destination_path: str,
        service: EditWhileIngestService
    ):
        self.job_id = job_id
        self.source_path = source_path
        self.destination_path = destination_path
        self.service = service
        
        self.is_monitoring = False
        self.last_size = 0
        self.last_modified = None
        self.available_bytes = 0
        self.metadata = {}
        self.segments: List[Dict] = []
        self.priority_chunks: Set[Tuple[int, int]] = set()
        self.edit_sessions: Dict[str, Dict] = {}
        
        # Paths
        self.partial_file_path = f"{destination_path}{service.partial_file_extension}"
        self.proxy_path = None
        self.metadata_path = f"{destination_path}.metadata.json"
        
    async def start_monitoring(self):
        """Start monitoring the ingest progress"""
        try:
            self.is_monitoring = True
            
            logger.info(
                "ingest_monitoring_started",
                job_id=self.job_id,
                source_path=self.source_path
            )
            
            while self.is_monitoring:
                try:
                    # Update available bytes
                    await self._update_available_bytes()
                    
                    # Update metadata
                    await self._update_metadata()
                    
                    # Update segments
                    await self._update_segments()
                    
                    # Process priority chunks if any
                    await self._process_priority_chunks()
                    
                    await asyncio.sleep(self.service.metadata_update_interval)
                    
                except Exception as e:
                    logger.error(
                        "monitoring_error",
                        job_id=self.job_id,
                        error=str(e)
                    )
                    
        except Exception as e:
            logger.error(
                "monitoring_failed",
                job_id=self.job_id,
                error=str(e)
            )
        finally:
            self.is_monitoring = False
    
    async def stop_monitoring(self):
        """Stop monitoring the ingest"""
        self.is_monitoring = False
        logger.info("ingest_monitoring_stopped", job_id=self.job_id)
    
    async def read_partial_file(
        self,
        byte_range: Optional[Tuple[int, int]] = None
    ) -> Optional[bytes]:
        """Read data from the partial file"""
        try:
            if not os.path.exists(self.partial_file_path):
                # Try destination path if partial doesn't exist
                if os.path.exists(self.destination_path):
                    file_path = self.destination_path
                else:
                    return None
            else:
                file_path = self.partial_file_path
            
            async with aiofiles.open(file_path, 'rb') as f:
                if byte_range:
                    start, end = byte_range
                    await f.seek(start)
                    data = await f.read(end - start)
                else:
                    data = await f.read()
                
                return data
                
        except Exception as e:
            logger.error(
                "partial_file_read_error",
                job_id=self.job_id,
                error=str(e)
            )
            return None
    
    async def get_current_metadata(self) -> Dict:
        """Get current metadata including ingest progress"""
        return {
            "job_id": self.job_id,
            "source_path": self.source_path,
            "destination_path": self.destination_path,
            "available_bytes": self.available_bytes,
            "last_modified": self.last_modified,
            "segments": self.segments,
            "metadata": self.metadata,
            "proxy_path": self.proxy_path,
            "active_edit_sessions": len(self.edit_sessions)
        }
    
    async def get_proxy_path(self) -> Optional[str]:
        """Get the current proxy file path"""
        return self.proxy_path
    
    async def prioritize_chunk(self, byte_offset: int, chunk_size: int) -> bool:
        """Add a chunk to priority processing queue"""
        try:
            self.priority_chunks.add((byte_offset, chunk_size))
            
            logger.info(
                "chunk_prioritized",
                job_id=self.job_id,
                byte_offset=byte_offset,
                chunk_size=chunk_size
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "chunk_prioritization_failed",
                job_id=self.job_id,
                error=str(e)
            )
            return False
    
    async def get_available_segments(self) -> List[Dict]:
        """Get segments that are available for editing"""
        return [
            segment for segment in self.segments
            if segment.get('status') == 'available'
        ]
    
    async def create_edit_session(
        self,
        start_time: float,
        end_time: float
    ) -> str:
        """Create a new edit session"""
        import uuid
        
        session_id = str(uuid.uuid4())
        
        self.edit_sessions[session_id] = {
            "id": session_id,
            "start_time": start_time,
            "end_time": end_time,
            "created_at": datetime.utcnow(),
            "status": "active"
        }
        
        return session_id
    
    async def _update_available_bytes(self):
        """Update the number of available bytes"""
        try:
            if os.path.exists(self.partial_file_path):
                stat = os.stat(self.partial_file_path)
                self.available_bytes = stat.st_size
                self.last_modified = datetime.fromtimestamp(stat.st_mtime)
            elif os.path.exists(self.destination_path):
                stat = os.stat(self.destination_path)
                self.available_bytes = stat.st_size
                self.last_modified = datetime.fromtimestamp(stat.st_mtime)
                
        except Exception as e:
            logger.error(
                "available_bytes_update_failed",
                job_id=self.job_id,
                error=str(e)
            )
    
    async def _update_metadata(self):
        """Update metadata from the ingesting file"""
        try:
            # Read metadata file if exists
            if os.path.exists(self.metadata_path):
                async with aiofiles.open(self.metadata_path, 'r') as f:
                    import json
                    content = await f.read()
                    self.metadata = json.loads(content)
            
            # Update with current stats
            self.metadata.update({
                "available_bytes": self.available_bytes,
                "last_updated": datetime.utcnow().isoformat(),
                "is_complete": False  # Will be set to True when ingest completes
            })
            
        except Exception as e:
            logger.error(
                "metadata_update_failed",
                job_id=self.job_id,
                error=str(e)
            )
    
    async def _update_segments(self):
        """Update available segments based on file progress"""
        try:
            # Calculate segments based on available bytes
            # Assume 10 second segments at 10 Mbps (simplified)
            segment_size = 10 * 1024 * 1024 * 10 / 8  # 10 seconds at 10 Mbps
            
            num_segments = int(self.available_bytes / segment_size)
            
            # Update segments list
            for i in range(num_segments):
                if i >= len(self.segments):
                    self.segments.append({
                        "index": i,
                        "start_byte": int(i * segment_size),
                        "end_byte": int(min((i + 1) * segment_size, self.available_bytes)),
                        "duration": 10.0,  # seconds
                        "status": "available"
                    })
                    
        except Exception as e:
            logger.error(
                "segments_update_failed",
                job_id=self.job_id,
                error=str(e)
            )
    
    async def _process_priority_chunks(self):
        """Process any priority chunks requested by editors"""
        try:
            if not self.priority_chunks:
                return
            
            # Process priority chunks (placeholder - would integrate with actual ingest)
            for byte_offset, chunk_size in list(self.priority_chunks):
                logger.info(
                    "processing_priority_chunk",
                    job_id=self.job_id,
                    byte_offset=byte_offset,
                    chunk_size=chunk_size
                )
                
                # Remove from priority queue after processing
                self.priority_chunks.discard((byte_offset, chunk_size))
                
        except Exception as e:
            logger.error(
                "priority_chunks_processing_failed",
                job_id=self.job_id,
                error=str(e)
            )


class EditSession:
    """Represents an edit session on a partially ingested file"""
    
    def __init__(
        self,
        session_id: str,
        job_id: str,
        start_time: float,
        end_time: float
    ):
        self.session_id = session_id
        self.job_id = job_id
        self.start_time = start_time
        self.end_time = end_time
        self.created_at = datetime.utcnow()
        self.last_accessed = self.created_at
        self.status = "active"
        self.edits = []
        
    async def add_edit(self, edit_type: str, parameters: Dict):
        """Add an edit to this session"""
        self.edits.append({
            "type": edit_type,
            "parameters": parameters,
            "timestamp": datetime.utcnow()
        })
        self.last_accessed = datetime.utcnow()
        
    async def export_edl(self) -> str:
        """Export the edit session as EDL"""
        # Simplified EDL export
        edl_content = f"TITLE: Edit Session {self.session_id}\n"
        edl_content += f"FCM: NON-DROP FRAME\n\n"
        
        for i, edit in enumerate(self.edits, 1):
            edl_content += f"{i:03d}  001      V     C        "
            edl_content += f"{self._format_timecode(edit['parameters'].get('in', 0))} "
            edl_content += f"{self._format_timecode(edit['parameters'].get('out', 0))} "
            edl_content += f"{self._format_timecode(edit['parameters'].get('start', 0))} "
            edl_content += f"{self._format_timecode(edit['parameters'].get('end', 0))}\n"
        
        return edl_content
    
    def _format_timecode(self, seconds: float) -> str:
        """Format seconds as timecode"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        frames = int((seconds % 1) * 30)  # Assuming 30fps
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d}:{frames:02d}"


# Dependency injection
_edit_while_ingest_service: Optional[EditWhileIngestService] = None


async def get_edit_while_ingest_service() -> EditWhileIngestService:
    """Get edit-while-ingest service instance"""
    global _edit_while_ingest_service
    
    if _edit_while_ingest_service is None:
        _edit_while_ingest_service = EditWhileIngestService()
    
    return _edit_while_ingest_service