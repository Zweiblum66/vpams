"""
Live Ingest Service for handling real-time media streams and growing files
"""

import os
import asyncio
import time
from typing import Dict, List, Optional, Set, AsyncGenerator
from pathlib import Path
from datetime import datetime, timedelta
import structlog
from urllib.parse import urlparse

from ..models.schemas import (
    IngestJob, IngestJobCreate, IngestType, IngestStatus, 
    IngestPriority, FileMetadata
)
from ..core.config import settings
from ..core.exceptions import LiveIngestError, ValidationError
from ..core.logging import get_logger

logger = get_logger(__name__)


class LiveIngestService:
    """Service for handling live media ingestion from streams and growing files"""
    
    def __init__(self):
        self.active_streams: Dict[str, 'LiveStreamMonitor'] = {}
        self.growing_files: Dict[str, 'GrowingFileMonitor'] = {}
        self.monitoring_tasks: Set[asyncio.Task] = set()
        
        # Configuration
        self.stream_check_interval = 5.0  # seconds
        self.file_stability_timeout = 30.0  # seconds
        self.max_stream_retry_attempts = 3
        
    async def start_live_stream_ingest(
        self,
        stream_url: str,
        destination_project_id: Optional[str] = None,
        metadata_override: Optional[Dict] = None,
        tags: Optional[List[str]] = None
    ) -> IngestJob:
        """Start ingesting from a live stream"""
        try:
            logger.info("starting_live_stream_ingest", stream_url=stream_url)
            
            # Validate stream URL
            if not self._validate_stream_url(stream_url):
                raise ValidationError(f"Invalid stream URL: {stream_url}")
            
            # Create ingest job
            job_request = IngestJobCreate(
                source_path=stream_url,
                destination_project_id=destination_project_id,
                ingest_type=IngestType.LIVE_STREAM,
                metadata_override=metadata_override or {},
                tags=tags or ["live_stream"],
                priority=IngestPriority.HIGH,
                auto_generate_proxies=True,
                preserve_folder_structure=False,
                stream_url=stream_url
            )
            
            # Create job (would integrate with main ingest service)
            job = IngestJob(
                source_path=stream_url,
                ingest_type=IngestType.LIVE_STREAM,
                status=IngestStatus.PROCESSING,
                current_operation="Connecting to stream",
                metadata_override=job_request.metadata_override,
                tags=job_request.tags,
                priority=job_request.priority,
                auto_generate_proxies=job_request.auto_generate_proxies
            )
            
            # Create stream monitor
            stream_monitor = LiveStreamMonitor(
                job_id=job.id,
                stream_url=stream_url,
                destination_project_id=destination_project_id,
                service=self
            )
            
            self.active_streams[job.id] = stream_monitor
            
            # Start monitoring task
            task = asyncio.create_task(stream_monitor.start_monitoring())
            self.monitoring_tasks.add(task)
            
            # Cleanup completed tasks
            task.add_done_callback(lambda t: self.monitoring_tasks.discard(t))
            
            logger.info(
                "live_stream_ingest_started",
                job_id=job.id,
                stream_url=stream_url
            )
            
            return job
            
        except Exception as e:
            logger.error(
                "live_stream_ingest_start_failed",
                error=str(e),
                stream_url=stream_url
            )
            raise LiveIngestError(f"Failed to start live stream ingest: {str(e)}")
    
    async def start_growing_file_ingest(
        self,
        file_path: str,
        destination_project_id: Optional[str] = None,
        growing_file_timeout: int = 300,  # 5 minutes default
        metadata_override: Optional[Dict] = None,
        tags: Optional[List[str]] = None
    ) -> IngestJob:
        """Start ingesting a growing file (file that's being written to)"""
        try:
            logger.info("starting_growing_file_ingest", file_path=file_path)
            
            # Validate file path
            if not os.path.exists(file_path):
                raise ValidationError(f"File not found: {file_path}")
            
            # Create ingest job
            job_request = IngestJobCreate(
                source_path=file_path,
                destination_project_id=destination_project_id,
                ingest_type=IngestType.LIVE_STREAM,  # Using live stream type for growing files
                metadata_override=metadata_override or {},
                tags=tags or ["growing_file"],
                priority=IngestPriority.HIGH,
                auto_generate_proxies=True,
                preserve_folder_structure=False,
                growing_file_timeout=growing_file_timeout
            )
            
            # Create job
            job = IngestJob(
                source_path=file_path,
                ingest_type=IngestType.LIVE_STREAM,
                status=IngestStatus.PROCESSING,
                current_operation="Monitoring growing file",
                metadata_override=job_request.metadata_override,
                tags=job_request.tags,
                priority=job_request.priority,
                auto_generate_proxies=job_request.auto_generate_proxies
            )
            
            # Create file monitor
            file_monitor = GrowingFileMonitor(
                job_id=job.id,
                file_path=file_path,
                destination_project_id=destination_project_id,
                timeout=growing_file_timeout,
                service=self
            )
            
            self.growing_files[job.id] = file_monitor
            
            # Start monitoring task
            task = asyncio.create_task(file_monitor.start_monitoring())
            self.monitoring_tasks.add(task)
            
            # Cleanup completed tasks
            task.add_done_callback(lambda t: self.monitoring_tasks.discard(t))
            
            logger.info(
                "growing_file_ingest_started",
                job_id=job.id,
                file_path=file_path,
                timeout=growing_file_timeout
            )
            
            return job
            
        except Exception as e:
            logger.error(
                "growing_file_ingest_start_failed",
                error=str(e),
                file_path=file_path
            )
            raise LiveIngestError(f"Failed to start growing file ingest: {str(e)}")
    
    async def stop_live_ingest(self, job_id: str) -> bool:
        """Stop a live ingest operation"""
        try:
            logger.info("stopping_live_ingest", job_id=job_id)
            
            # Stop stream monitoring
            if job_id in self.active_streams:
                await self.active_streams[job_id].stop_monitoring()
                del self.active_streams[job_id]
                return True
            
            # Stop file monitoring
            if job_id in self.growing_files:
                await self.growing_files[job_id].stop_monitoring()
                del self.growing_files[job_id]
                return True
            
            logger.warning("live_ingest_not_found", job_id=job_id)
            return False
            
        except Exception as e:
            logger.error(
                "live_ingest_stop_failed",
                error=str(e),
                job_id=job_id
            )
            return False
    
    async def get_live_ingest_status(self, job_id: str) -> Optional[Dict]:
        """Get status of a live ingest operation"""
        try:
            # Check stream monitoring
            if job_id in self.active_streams:
                return await self.active_streams[job_id].get_status()
            
            # Check file monitoring
            if job_id in self.growing_files:
                return await self.growing_files[job_id].get_status()
            
            return None
            
        except Exception as e:
            logger.error(
                "live_ingest_status_failed",
                error=str(e),
                job_id=job_id
            )
            return None
    
    async def list_active_live_ingests(self) -> List[Dict]:
        """List all active live ingest operations"""
        try:
            active_ingests = []
            
            # Add stream ingests
            for job_id, monitor in self.active_streams.items():
                status = await monitor.get_status()
                if status:
                    active_ingests.append(status)
            
            # Add file ingests
            for job_id, monitor in self.growing_files.items():
                status = await monitor.get_status()
                if status:
                    active_ingests.append(status)
            
            return active_ingests
            
        except Exception as e:
            logger.error("list_active_live_ingests_failed", error=str(e))
            return []
    
    def _validate_stream_url(self, stream_url: str) -> bool:
        """Validate stream URL format"""
        try:
            parsed = urlparse(stream_url)
            
            # Check for supported protocols
            supported_protocols = ['rtmp', 'rtsp', 'http', 'https', 'srt', 'udp', 'tcp']
            
            if parsed.scheme.lower() not in supported_protocols:
                return False
            
            # Basic validation - must have hostname
            if not parsed.hostname:
                return False
            
            return True
            
        except Exception:
            return False
    
    async def cleanup_completed_tasks(self):
        """Clean up completed monitoring tasks"""
        completed_tasks = [task for task in self.monitoring_tasks if task.done()]
        for task in completed_tasks:
            self.monitoring_tasks.discard(task)
        
        logger.debug("cleaned_up_tasks", completed_count=len(completed_tasks))


class LiveStreamMonitor:
    """Monitor and capture live streams"""
    
    def __init__(
        self,
        job_id: str,
        stream_url: str,
        destination_project_id: Optional[str],
        service: LiveIngestService
    ):
        self.job_id = job_id
        self.stream_url = stream_url
        self.destination_project_id = destination_project_id
        self.service = service
        
        self.is_monitoring = False
        self.start_time = None
        self.last_update = None
        self.retry_count = 0
        self.captured_segments = []
        self.total_duration = 0.0
        
    async def start_monitoring(self):
        """Start monitoring the live stream"""
        try:
            self.is_monitoring = True
            self.start_time = datetime.utcnow()
            self.last_update = self.start_time
            
            logger.info(
                "stream_monitoring_started",
                job_id=self.job_id,
                stream_url=self.stream_url
            )
            
            while self.is_monitoring:
                try:
                    # Simulate stream capture (in real implementation, would use ffmpeg)
                    await self._capture_stream_segment()
                    
                    self.retry_count = 0  # Reset retry count on success
                    await asyncio.sleep(self.service.stream_check_interval)
                    
                except Exception as e:
                    logger.error(
                        "stream_capture_error",
                        job_id=self.job_id,
                        error=str(e),
                        retry_count=self.retry_count
                    )
                    
                    self.retry_count += 1
                    if self.retry_count >= self.service.max_stream_retry_attempts:
                        logger.error(
                            "stream_max_retries_exceeded",
                            job_id=self.job_id,
                            max_retries=self.service.max_stream_retry_attempts
                        )
                        break
                    
                    # Exponential backoff
                    await asyncio.sleep(min(30, 2 ** self.retry_count))
            
        except Exception as e:
            logger.error(
                "stream_monitoring_failed",
                job_id=self.job_id,
                error=str(e)
            )
        finally:
            self.is_monitoring = False
    
    async def _capture_stream_segment(self):
        """Capture a segment of the stream (placeholder implementation)"""
        # In real implementation, would use ffmpeg to capture stream segments
        # and store them as files or directly stream to storage
        
        segment_info = {
            "timestamp": datetime.utcnow(),
            "duration": self.service.stream_check_interval,
            "size": 1024 * 1024  # Placeholder size
        }
        
        self.captured_segments.append(segment_info)
        self.total_duration += segment_info["duration"]
        self.last_update = segment_info["timestamp"]
        
        logger.debug(
            "stream_segment_captured",
            job_id=self.job_id,
            segment_count=len(self.captured_segments),
            total_duration=self.total_duration
        )
    
    async def stop_monitoring(self):
        """Stop monitoring the stream"""
        self.is_monitoring = False
        logger.info("stream_monitoring_stopped", job_id=self.job_id)
    
    async def get_status(self) -> Dict:
        """Get current status of stream monitoring"""
        return {
            "job_id": self.job_id,
            "type": "live_stream",
            "stream_url": self.stream_url,
            "is_monitoring": self.is_monitoring,
            "start_time": self.start_time,
            "last_update": self.last_update,
            "retry_count": self.retry_count,
            "segments_captured": len(self.captured_segments),
            "total_duration": self.total_duration,
            "destination_project_id": self.destination_project_id
        }


class GrowingFileMonitor:
    """Monitor growing files and trigger ingest when stable"""
    
    def __init__(
        self,
        job_id: str,
        file_path: str,
        destination_project_id: Optional[str],
        timeout: int,
        service: LiveIngestService
    ):
        self.job_id = job_id
        self.file_path = file_path
        self.destination_project_id = destination_project_id
        self.timeout = timeout
        self.service = service
        
        self.is_monitoring = False
        self.start_time = None
        self.last_size = 0
        self.last_modified = None
        self.stable_since = None
        self.stability_confirmed = False
        
    async def start_monitoring(self):
        """Start monitoring the growing file"""
        try:
            self.is_monitoring = True
            self.start_time = datetime.utcnow()
            
            logger.info(
                "file_monitoring_started",
                job_id=self.job_id,
                file_path=self.file_path
            )
            
            timeout_time = self.start_time + timedelta(seconds=self.timeout)
            
            while self.is_monitoring and datetime.utcnow() < timeout_time:
                try:
                    await self._check_file_stability()
                    
                    # If file has been stable for required time, trigger ingest
                    if self.stability_confirmed:
                        await self._trigger_final_ingest()
                        break
                    
                    await asyncio.sleep(self.service.file_stability_timeout / 10)  # Check frequently
                    
                except Exception as e:
                    logger.error(
                        "file_monitoring_error",
                        job_id=self.job_id,
                        error=str(e)
                    )
                    await asyncio.sleep(5)  # Wait before retry
            
            if datetime.utcnow() >= timeout_time:
                logger.warning(
                    "file_monitoring_timeout",
                    job_id=self.job_id,
                    timeout=self.timeout
                )
                # Still trigger ingest even if timeout reached
                await self._trigger_final_ingest()
            
        except Exception as e:
            logger.error(
                "file_monitoring_failed",
                job_id=self.job_id,
                error=str(e)
            )
        finally:
            self.is_monitoring = False
    
    async def _check_file_stability(self):
        """Check if file size and modification time are stable"""
        try:
            if not os.path.exists(self.file_path):
                logger.warning(
                    "monitored_file_disappeared",
                    job_id=self.job_id,
                    file_path=self.file_path
                )
                return
            
            file_stat = os.stat(self.file_path)
            current_size = file_stat.st_size
            current_modified = datetime.fromtimestamp(file_stat.st_mtime)
            
            # Check if file has changed
            if current_size != self.last_size or current_modified != self.last_modified:
                # File has changed, reset stability timer
                self.stable_since = datetime.utcnow()
                self.stability_confirmed = False
                
                logger.debug(
                    "file_changed",
                    job_id=self.job_id,
                    old_size=self.last_size,
                    new_size=current_size,
                    file_path=self.file_path
                )
            else:
                # File hasn't changed, check if it's been stable long enough
                if self.stable_since:
                    stable_duration = (datetime.utcnow() - self.stable_since).total_seconds()
                    if stable_duration >= self.service.file_stability_timeout:
                        self.stability_confirmed = True
                        logger.info(
                            "file_stability_confirmed",
                            job_id=self.job_id,
                            stable_duration=stable_duration,
                            file_path=self.file_path
                        )
            
            self.last_size = current_size
            self.last_modified = current_modified
            
        except Exception as e:
            logger.error(
                "file_stability_check_failed",
                job_id=self.job_id,
                error=str(e)
            )
    
    async def _trigger_final_ingest(self):
        """Trigger the final ingest of the stable file"""
        try:
            logger.info(
                "triggering_final_ingest",
                job_id=self.job_id,
                file_path=self.file_path,
                final_size=self.last_size
            )
            
            # In real implementation, would trigger regular file ingest
            # This is a placeholder for the integration point
            
        except Exception as e:
            logger.error(
                "final_ingest_trigger_failed",
                job_id=self.job_id,
                error=str(e)
            )
    
    async def stop_monitoring(self):
        """Stop monitoring the file"""
        self.is_monitoring = False
        logger.info("file_monitoring_stopped", job_id=self.job_id)
    
    async def get_status(self) -> Dict:
        """Get current status of file monitoring"""
        return {
            "job_id": self.job_id,
            "type": "growing_file",
            "file_path": self.file_path,
            "is_monitoring": self.is_monitoring,
            "start_time": self.start_time,
            "current_size": self.last_size,
            "last_modified": self.last_modified,
            "stable_since": self.stable_since,
            "stability_confirmed": self.stability_confirmed,
            "destination_project_id": self.destination_project_id
        }


# Dependency injection
_live_ingest_service: Optional[LiveIngestService] = None


async def get_live_ingest_service() -> LiveIngestService:
    """Get live ingest service instance"""
    global _live_ingest_service
    
    if _live_ingest_service is None:
        _live_ingest_service = LiveIngestService()
    
    return _live_ingest_service