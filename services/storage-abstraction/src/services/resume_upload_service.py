"""
Resume Upload Service

This module handles resumable upload functionality, allowing uploads to be
paused and resumed from where they left off.
"""

import asyncio
import hashlib
import json
import logging
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List, AsyncIterator, Callable
import aiofiles
from dataclasses import dataclass, asdict

from ..core.interfaces import (
    StorageDriver, StorageObject, UploadProgress,
    InvalidStorageOperationError, StorageOperationError
)
from ..core.config import get_settings


logger = logging.getLogger(__name__)


@dataclass
class ResumableUpload:
    """Represents a resumable upload session"""
    upload_id: str
    key: str
    total_size: int
    uploaded_size: int
    chunk_size: int
    chunks_completed: List[int]
    metadata: Optional[Dict[str, str]]
    content_type: Optional[str]
    created_at: datetime
    updated_at: datetime
    expires_at: datetime
    driver_name: str
    temp_path: str
    checksum: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        data['updated_at'] = self.updated_at.isoformat()
        data['expires_at'] = self.expires_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ResumableUpload':
        """Create from dictionary"""
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        data['expires_at'] = datetime.fromisoformat(data['expires_at'])
        return cls(**data)


class ResumeUploadService:
    """Service for handling resumable uploads"""
    
    def __init__(self):
        self.settings = get_settings()
        self._upload_sessions: Dict[str, ResumableUpload] = {}
        self._session_file = Path(self.settings.temp_directory) / "resume_sessions.json"
        self._cleanup_interval = 3600  # 1 hour
        self._cleanup_task: Optional[asyncio.Task] = None
        
    async def initialize(self) -> None:
        """Initialize the resume upload service"""
        # Load existing sessions
        await self._load_sessions()
        
        # Start cleanup task
        self._cleanup_task = asyncio.create_task(self._cleanup_expired_sessions())
        
    async def shutdown(self) -> None:
        """Shutdown the service"""
        # Cancel cleanup task
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Save sessions
        await self._save_sessions()
    
    async def create_resumable_upload(
        self,
        key: str,
        total_size: int,
        chunk_size: int,
        driver_name: str,
        metadata: Optional[Dict[str, str]] = None,
        content_type: Optional[str] = None,
        ttl_hours: int = 24
    ) -> ResumableUpload:
        """Create a new resumable upload session"""
        # Generate upload ID
        upload_id = self._generate_upload_id(key, total_size)
        
        # Create temp file path
        temp_dir = Path(self.settings.temp_directory) / "uploads" / upload_id
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_path = str(temp_dir / "data")
        
        # Create session
        now = datetime.utcnow()
        session = ResumableUpload(
            upload_id=upload_id,
            key=key,
            total_size=total_size,
            uploaded_size=0,
            chunk_size=chunk_size,
            chunks_completed=[],
            metadata=metadata,
            content_type=content_type,
            created_at=now,
            updated_at=now,
            expires_at=now + timedelta(hours=ttl_hours),
            driver_name=driver_name,
            temp_path=temp_path
        )
        
        # Store session
        self._upload_sessions[upload_id] = session
        await self._save_sessions()
        
        logger.info(f"Created resumable upload session: {upload_id}")
        return session
    
    async def upload_chunk(
        self,
        upload_id: str,
        chunk_index: int,
        data: bytes,
        progress_callback: Optional[Callable[[UploadProgress], None]] = None
    ) -> ResumableUpload:
        """Upload a chunk of data"""
        # Get session
        session = self._upload_sessions.get(upload_id)
        if not session:
            raise InvalidStorageOperationError(f"Upload session not found: {upload_id}")
        
        # Check if expired
        if datetime.utcnow() > session.expires_at:
            raise InvalidStorageOperationError(f"Upload session expired: {upload_id}")
        
        # Check if chunk already uploaded
        if chunk_index in session.chunks_completed:
            logger.info(f"Chunk {chunk_index} already uploaded for session {upload_id}")
            return session
        
        # Calculate chunk position
        chunk_start = chunk_index * session.chunk_size
        chunk_end = min(chunk_start + len(data), session.total_size)
        
        # Validate chunk
        if chunk_start >= session.total_size:
            raise InvalidStorageOperationError(f"Invalid chunk index: {chunk_index}")
        
        # Write chunk to temp file
        async with aiofiles.open(session.temp_path, 'r+b' if os.path.exists(session.temp_path) else 'wb') as f:
            await f.seek(chunk_start)
            await f.write(data)
        
        # Update session
        session.chunks_completed.append(chunk_index)
        session.uploaded_size = await self._calculate_uploaded_size(session)
        session.updated_at = datetime.utcnow()
        
        # Report progress
        if progress_callback:
            progress = UploadProgress(
                bytes_uploaded=session.uploaded_size,
                total_bytes=session.total_size,
                percentage=round((session.uploaded_size / session.total_size) * 100, 2),
                chunks_completed=len(session.chunks_completed),
                total_chunks=(session.total_size + session.chunk_size - 1) // session.chunk_size
            )
            progress_callback(progress)
        
        # Save session state
        await self._save_sessions()
        
        logger.info(
            f"Uploaded chunk {chunk_index} for session {upload_id}, "
            f"progress: {session.uploaded_size}/{session.total_size} bytes"
        )
        
        return session
    
    async def complete_upload(
        self,
        upload_id: str,
        storage_driver: StorageDriver,
        verify_checksum: bool = True
    ) -> StorageObject:
        """Complete a resumable upload"""
        # Get session
        session = self._upload_sessions.get(upload_id)
        if not session:
            raise InvalidStorageOperationError(f"Upload session not found: {upload_id}")
        
        # Check if all chunks uploaded
        total_chunks = (session.total_size + session.chunk_size - 1) // session.chunk_size
        if len(session.chunks_completed) != total_chunks:
            missing_chunks = [
                i for i in range(total_chunks) 
                if i not in session.chunks_completed
            ]
            raise InvalidStorageOperationError(
                f"Upload incomplete. Missing chunks: {missing_chunks}"
            )
        
        # Verify file size
        actual_size = os.path.getsize(session.temp_path)
        if actual_size != session.total_size:
            raise InvalidStorageOperationError(
                f"File size mismatch. Expected: {session.total_size}, "
                f"Actual: {actual_size}"
            )
        
        # Verify checksum if requested
        if verify_checksum and session.checksum:
            calculated_checksum = await self._calculate_file_checksum(session.temp_path)
            if calculated_checksum != session.checksum:
                raise InvalidStorageOperationError(
                    f"Checksum mismatch. Expected: {session.checksum}, "
                    f"Calculated: {calculated_checksum}"
                )
        
        # Upload to storage driver
        async with aiofiles.open(session.temp_path, 'rb') as f:
            content = await f.read()
            
        result = await storage_driver.put_object(
            session.key,
            content,
            session.metadata,
            session.content_type
        )
        
        # Clean up
        await self._cleanup_session(upload_id)
        
        logger.info(f"Completed resumable upload: {upload_id}")
        return result
    
    async def abort_upload(self, upload_id: str) -> None:
        """Abort a resumable upload"""
        await self._cleanup_session(upload_id)
        logger.info(f"Aborted resumable upload: {upload_id}")
    
    async def get_upload_status(self, upload_id: str) -> Optional[ResumableUpload]:
        """Get the status of a resumable upload"""
        session = self._upload_sessions.get(upload_id)
        if session and datetime.utcnow() <= session.expires_at:
            return session
        return None
    
    async def list_uploads(self, key_prefix: Optional[str] = None) -> List[ResumableUpload]:
        """List active resumable uploads"""
        uploads = []
        now = datetime.utcnow()
        
        for session in self._upload_sessions.values():
            if now <= session.expires_at:
                if key_prefix is None or session.key.startswith(key_prefix):
                    uploads.append(session)
        
        return uploads
    
    def _generate_upload_id(self, key: str, total_size: int) -> str:
        """Generate a unique upload ID"""
        data = f"{key}:{total_size}:{time.time()}"
        return hashlib.sha256(data.encode()).hexdigest()[:32]
    
    async def _calculate_uploaded_size(self, session: ResumableUpload) -> int:
        """Calculate actual uploaded size from chunks"""
        if not os.path.exists(session.temp_path):
            return 0
            
        # Get file size
        return os.path.getsize(session.temp_path)
    
    async def _calculate_file_checksum(self, file_path: str) -> str:
        """Calculate file checksum"""
        sha256 = hashlib.sha256()
        
        async with aiofiles.open(file_path, 'rb') as f:
            while chunk := await f.read(8192):
                sha256.update(chunk)
        
        return sha256.hexdigest()
    
    async def _cleanup_session(self, upload_id: str) -> None:
        """Clean up a session and its temporary files"""
        session = self._upload_sessions.get(upload_id)
        if not session:
            return
        
        # Remove temp files
        temp_dir = Path(session.temp_path).parent
        if temp_dir.exists():
            import shutil
            shutil.rmtree(temp_dir)
        
        # Remove session
        del self._upload_sessions[upload_id]
        await self._save_sessions()
    
    async def _cleanup_expired_sessions(self) -> None:
        """Periodically clean up expired sessions"""
        while True:
            try:
                await asyncio.sleep(self._cleanup_interval)
                
                now = datetime.utcnow()
                expired_ids = [
                    upload_id for upload_id, session in self._upload_sessions.items()
                    if now > session.expires_at
                ]
                
                for upload_id in expired_ids:
                    await self._cleanup_session(upload_id)
                    logger.info(f"Cleaned up expired session: {upload_id}")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
    
    async def _save_sessions(self) -> None:
        """Save sessions to disk"""
        try:
            data = {
                upload_id: session.to_dict()
                for upload_id, session in self._upload_sessions.items()
            }
            
            self._session_file.parent.mkdir(parents=True, exist_ok=True)
            
            async with aiofiles.open(self._session_file, 'w') as f:
                await f.write(json.dumps(data, indent=2))
                
        except Exception as e:
            logger.error(f"Failed to save sessions: {e}")
    
    async def _load_sessions(self) -> None:
        """Load sessions from disk"""
        try:
            if not self._session_file.exists():
                return
            
            async with aiofiles.open(self._session_file, 'r') as f:
                data = json.loads(await f.read())
            
            now = datetime.utcnow()
            for upload_id, session_data in data.items():
                session = ResumableUpload.from_dict(session_data)
                # Only load non-expired sessions
                if now <= session.expires_at:
                    self._upload_sessions[upload_id] = session
                    
        except Exception as e:
            logger.error(f"Failed to load sessions: {e}")


# Global instance
_resume_service: Optional[ResumeUploadService] = None


async def get_resume_service() -> ResumeUploadService:
    """Get or create resume upload service instance"""
    global _resume_service
    
    if _resume_service is None:
        _resume_service = ResumeUploadService()
        await _resume_service.initialize()
    
    return _resume_service


async def close_resume_service() -> None:
    """Close resume upload service"""
    global _resume_service
    
    if _resume_service is not None:
        await _resume_service.shutdown()
        _resume_service = None