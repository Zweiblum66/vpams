"""
Hot folder service for immediate file ingestion
"""

import asyncio
import os
import time
from typing import Dict, List, Optional, Set
from pathlib import Path
from datetime import datetime
import structlog
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileMovedEvent

from ..models.schemas import (
    HotFolderConfig, IngestJobCreate, IngestJob, IngestType,
    FileMetadata, ValidationRule, IngestPriority
)
from ..core.config import settings
from ..core.exceptions import HotFolderError, IngestServiceError
from ..core.logging import get_logger, log_ingest_event
from .ingest_service import IngestService

logger = get_logger(__name__)


class HotFolderHandler(FileSystemEventHandler):
    """File system event handler for hot folders with immediate processing"""
    
    def __init__(self, config: HotFolderConfig, hot_folder_service: 'HotFolderService'):
        self.config = config
        self.hot_folder_service = hot_folder_service
        self.processing_files: Set[str] = set()
        self.file_locks: Dict[str, asyncio.Lock] = {}
        
    def on_created(self, event):
        """Handle file creation events"""
        if not event.is_directory:
            self._handle_file_event(event.src_path, "created")
    
    def on_moved(self, event):
        """Handle file move events"""
        if not event.is_directory:
            self._handle_file_event(event.dest_path, "moved")
    
    def _handle_file_event(self, file_path: str, event_type: str):
        """Handle file system events with immediate processing"""
        try:
            # Check if file matches filter patterns
            if not self._matches_filters(file_path):
                return
            
            # Avoid duplicate processing
            if file_path in self.processing_files:
                return
            
            # Add to processing set immediately
            self.processing_files.add(file_path)
            
            logger.info(
                "hot_folder_file_detected",
                file_path=file_path,
                event_type=event_type,
                hot_folder_id=self.config.id,
                hot_folder_path=self.config.path
            )
            
            # Process immediately with minimal delay for file stability
            asyncio.create_task(
                self._process_file_immediately(file_path)
            )
            
        except Exception as e:
            logger.error(
                "hot_folder_event_handling_failed",
                error=str(e),
                file_path=file_path,
                event_type=event_type
            )
    
    def _matches_filters(self, file_path: str) -> bool:
        """Check if file matches include/exclude filters"""
        file_name = Path(file_path).name.lower()
        file_ext = Path(file_path).suffix.lower().lstrip('.')
        
        # Check include patterns
        if self.config.include_patterns:
            include_match = any(
                pattern.lower() in file_name or pattern.lower() == file_ext
                for pattern in self.config.include_patterns
            )
            if not include_match:
                return False
        
        # Check exclude patterns
        if self.config.exclude_patterns:
            exclude_match = any(
                pattern.lower() in file_name or pattern.lower() == file_ext
                for pattern in self.config.exclude_patterns
            )
            if exclude_match:
                return False
        
        return True
    
    async def _process_file_immediately(self, file_path: str):
        """Process file immediately with minimal delay"""
        try:
            # Get or create a lock for this file
            if file_path not in self.file_locks:
                self.file_locks[file_path] = asyncio.Lock()
            
            async with self.file_locks[file_path]:
                # Short stability check (much shorter than watch folders)
                await asyncio.sleep(self.config.immediate_processing_delay)
                
                # Check if file still exists
                if not os.path.exists(file_path):
                    logger.warning(
                        "hot_folder_file_disappeared",
                        file_path=file_path,
                        hot_folder_id=self.config.id
                    )
                    return
                
                # Additional stability check for growing files
                if self.config.check_file_stability:
                    if not await self._is_file_stable(file_path):
                        logger.info(
                            "hot_folder_file_still_growing",
                            file_path=file_path,
                            hot_folder_id=self.config.id
                        )
                        # Wait and check again
                        await asyncio.sleep(self.config.stability_check_interval)
                        if not await self._is_file_stable(file_path):
                            logger.warning(
                                "hot_folder_file_stability_timeout",
                                file_path=file_path,
                                hot_folder_id=self.config.id
                            )
                            return
                
                # Create high-priority ingest job
                await self.hot_folder_service._create_immediate_ingest_job(file_path, self.config)
                
        except Exception as e:
            logger.error(
                "hot_folder_immediate_processing_failed",
                error=str(e),
                file_path=file_path,
                hot_folder_id=self.config.id
            )
        finally:
            # Remove from processing set
            self.processing_files.discard(file_path)
            # Clean up lock if not needed
            if file_path in self.file_locks:
                del self.file_locks[file_path]
    
    async def _is_file_stable(self, file_path: str) -> bool:
        """Check if file is stable (not being written to)"""
        try:
            # Get initial size and modification time
            initial_stat = os.stat(file_path)
            initial_size = initial_stat.st_size
            initial_mtime = initial_stat.st_mtime
            
            # Wait a short period
            await asyncio.sleep(0.5)
            
            # Check again
            current_stat = os.stat(file_path)
            current_size = current_stat.st_size
            current_mtime = current_stat.st_mtime
            
            # File is stable if size and mtime haven't changed
            return initial_size == current_size and initial_mtime == current_mtime
            
        except OSError:
            # File doesn't exist or can't be accessed
            return False


class HotFolderService:
    """Service for managing hot folder immediate ingestion"""
    
    def __init__(self):
        self.ingest_service: Optional[IngestService] = None
        self.hot_folders: Dict[str, HotFolderConfig] = {}
        self.observers: Dict[str, Observer] = {}
        self.handlers: Dict[str, HotFolderHandler] = {}
        self._is_monitoring = False
        self._processing_stats = {
            "total_processed": 0,
            "total_failed": 0,
            "average_processing_time": 0.0
        }
    
    async def initialize(self, ingest_service: IngestService):
        """Initialize the hot folder service"""
        self.ingest_service = ingest_service
        
        # Load existing hot folder configurations
        await self._load_hot_folders()
        
        # Start monitoring for enabled hot folders
        await self.start_monitoring()
        
        logger.info(
            "hot_folder_service_initialized",
            hot_folder_count=len(self.hot_folders)
        )
    
    async def _load_hot_folders(self):
        """Load hot folder configurations from storage"""
        # In a real implementation, this would load from database
        # For now, we'll initialize with empty dict
        pass
    
    async def create_hot_folder(self, config: HotFolderConfig) -> HotFolderConfig:
        """Create a new hot folder configuration"""
        try:
            # Validate hot folder path
            if not os.path.exists(config.path):
                raise HotFolderError(f"Hot folder path does not exist: {config.path}")
            
            if not os.path.isdir(config.path):
                raise HotFolderError(f"Hot folder path is not a directory: {config.path}")
            
            # Check for write access (hot folders may need to move/delete files)
            if not os.access(config.path, os.R_OK | os.W_OK):
                raise HotFolderError(f"Insufficient permissions for hot folder: {config.path}")
            
            # Store configuration
            self.hot_folders[config.id] = config
            
            # Start monitoring if enabled
            if config.enabled:
                await self._start_monitoring_folder(config)
            
            logger.info(
                "hot_folder_created",
                hot_folder_id=config.id,
                path=config.path,
                enabled=config.enabled,
                immediate_processing=config.immediate_processing
            )
            
            return config
            
        except Exception as e:
            logger.error(
                "failed_to_create_hot_folder",
                error=str(e),
                path=config.path
            )
            raise HotFolderError(f"Failed to create hot folder: {str(e)}")
    
    async def list_hot_folders(self) -> List[HotFolderConfig]:
        """List all hot folder configurations"""
        return list(self.hot_folders.values())
    
    async def get_hot_folder(self, folder_id: str) -> Optional[HotFolderConfig]:
        """Get a specific hot folder configuration"""
        return self.hot_folders.get(folder_id)
    
    async def update_hot_folder(
        self,
        folder_id: str,
        config: HotFolderConfig
    ) -> Optional[HotFolderConfig]:
        """Update a hot folder configuration"""
        if folder_id not in self.hot_folders:
            return None
        
        old_config = self.hot_folders[folder_id]
        
        try:
            # Stop monitoring old configuration
            if old_config.enabled:
                await self._stop_monitoring_folder(folder_id)
            
            # Update configuration
            config.id = folder_id  # Ensure ID consistency
            self.hot_folders[folder_id] = config
            
            # Start monitoring new configuration if enabled
            if config.enabled:
                await self._start_monitoring_folder(config)
            
            logger.info(
                "hot_folder_updated",
                hot_folder_id=folder_id,
                path=config.path,
                enabled=config.enabled
            )
            
            return config
            
        except Exception as e:
            # Restore old configuration on error
            self.hot_folders[folder_id] = old_config
            if old_config.enabled:
                await self._start_monitoring_folder(old_config)
            
            logger.error(
                "failed_to_update_hot_folder",
                error=str(e),
                folder_id=folder_id
            )
            raise HotFolderError(f"Failed to update hot folder: {str(e)}")
    
    async def delete_hot_folder(self, folder_id: str) -> bool:
        """Delete a hot folder configuration"""
        if folder_id not in self.hot_folders:
            return False
        
        try:
            # Stop monitoring
            await self._stop_monitoring_folder(folder_id)
            
            # Remove configuration
            del self.hot_folders[folder_id]
            
            logger.info("hot_folder_deleted", hot_folder_id=folder_id)
            
            return True
            
        except Exception as e:
            logger.error(
                "failed_to_delete_hot_folder",
                error=str(e),
                folder_id=folder_id
            )
            raise HotFolderError(f"Failed to delete hot folder: {str(e)}")
    
    async def start_monitoring(self):
        """Start monitoring all enabled hot folders"""
        if self._is_monitoring:
            return
        
        try:
            for config in self.hot_folders.values():
                if config.enabled:
                    await self._start_monitoring_folder(config)
            
            self._is_monitoring = True
            
            logger.info(
                "hot_folder_monitoring_started",
                active_folders=len([c for c in self.hot_folders.values() if c.enabled])
            )
            
        except Exception as e:
            logger.error("failed_to_start_hot_folder_monitoring", error=str(e))
            raise HotFolderError(f"Failed to start monitoring: {str(e)}")
    
    async def stop_monitoring(self):
        """Stop monitoring all hot folders"""
        if not self._is_monitoring:
            return
        
        try:
            for folder_id in list(self.observers.keys()):
                await self._stop_monitoring_folder(folder_id)
            
            self._is_monitoring = False
            
            logger.info("hot_folder_monitoring_stopped")
            
        except Exception as e:
            logger.error("failed_to_stop_hot_folder_monitoring", error=str(e))
            raise HotFolderError(f"Failed to stop monitoring: {str(e)}")
    
    async def _start_monitoring_folder(self, config: HotFolderConfig):
        """Start monitoring a specific hot folder"""
        try:
            if config.id in self.observers:
                # Already monitoring
                return
            
            # Create event handler
            handler = HotFolderHandler(config, self)
            self.handlers[config.id] = handler
            
            # Create observer
            observer = Observer()
            observer.schedule(
                handler,
                config.path,
                recursive=config.recursive
            )
            
            # Start observer
            observer.start()
            self.observers[config.id] = observer
            
            logger.info(
                "hot_folder_monitoring_started",
                hot_folder_id=config.id,
                path=config.path,
                recursive=config.recursive,
                immediate_processing=config.immediate_processing
            )
            
        except Exception as e:
            logger.error(
                "failed_to_start_monitoring_hot_folder",
                error=str(e),
                hot_folder_id=config.id,
                path=config.path
            )
            raise HotFolderError(f"Failed to start monitoring hot folder: {str(e)}")
    
    async def _stop_monitoring_folder(self, folder_id: str):
        """Stop monitoring a specific hot folder"""
        try:
            if folder_id in self.observers:
                observer = self.observers[folder_id]
                observer.stop()
                observer.join(timeout=5)  # Wait up to 5 seconds
                del self.observers[folder_id]
            
            if folder_id in self.handlers:
                del self.handlers[folder_id]
            
            logger.info(
                "hot_folder_monitoring_stopped",
                hot_folder_id=folder_id
            )
            
        except Exception as e:
            logger.error(
                "failed_to_stop_monitoring_hot_folder",
                error=str(e),
                folder_id=folder_id
            )
    
    async def _create_immediate_ingest_job(self, file_path: str, config: HotFolderConfig):
        """Create an immediate high-priority ingest job for a hot folder file"""
        start_time = time.time()
        
        try:
            if not self.ingest_service:
                raise IngestServiceError("Ingest service not initialized")
            
            # Create high-priority ingest job request
            job_request = IngestJobCreate(
                source_path=file_path,
                destination_project_id=config.destination_project_id,
                ingest_type=IngestType.HOT_FOLDER,
                validation_rules=config.validation_rules,
                metadata_override=config.metadata_template or {},
                tags=config.tags or [],
                priority=IngestPriority.URGENT,  # Hot folders get urgent priority
                auto_generate_proxies=config.auto_generate_proxies,
                preserve_folder_structure=config.preserve_folder_structure
            )
            
            # Create job
            job = await self.ingest_service.create_job(job_request)
            
            # Process job immediately (synchronously for hot folders)
            if config.immediate_processing:
                await self.ingest_service.process_job(job.id)
                
                # Optionally move or delete file after processing
                if config.move_after_processing and config.processed_folder:
                    await self._move_processed_file(file_path, config)
                elif config.delete_after_processing:
                    await self._delete_processed_file(file_path, config)
            else:
                # Just queue for processing (background)
                asyncio.create_task(
                    self.ingest_service.process_job(job.id)
                )
            
            # Update statistics
            processing_time = time.time() - start_time
            self._update_processing_stats(processing_time, success=True)
            
            log_ingest_event(
                logger,
                "hot_folder_immediate_ingest_completed",
                file_path,
                job_id=job.id,
                hot_folder_id=config.id,
                processing_time_ms=processing_time * 1000,
                immediate_processing=config.immediate_processing
            )
            
        except Exception as e:
            # Update statistics
            processing_time = time.time() - start_time
            self._update_processing_stats(processing_time, success=False)
            
            logger.error(
                "failed_to_create_immediate_ingest_job",
                error=str(e),
                file_path=file_path,
                hot_folder_id=config.id,
                processing_time_ms=processing_time * 1000
            )
    
    async def _move_processed_file(self, file_path: str, config: HotFolderConfig):
        """Move processed file to designated folder"""
        try:
            if not config.processed_folder:
                return
            
            os.makedirs(config.processed_folder, exist_ok=True)
            
            file_name = Path(file_path).name
            destination = os.path.join(config.processed_folder, file_name)
            
            # Handle naming conflicts
            counter = 1
            while os.path.exists(destination):
                name_parts = Path(file_name).stem, Path(file_name).suffix
                destination = os.path.join(
                    config.processed_folder,
                    f"{name_parts[0]}_{counter}{name_parts[1]}"
                )
                counter += 1
            
            os.rename(file_path, destination)
            
            logger.info(
                "hot_folder_file_moved",
                source_path=file_path,
                destination_path=destination,
                hot_folder_id=config.id
            )
            
        except Exception as e:
            logger.error(
                "failed_to_move_processed_file",
                error=str(e),
                file_path=file_path,
                hot_folder_id=config.id
            )
    
    async def _delete_processed_file(self, file_path: str, config: HotFolderConfig):
        """Delete processed file"""
        try:
            os.remove(file_path)
            
            logger.info(
                "hot_folder_file_deleted",
                file_path=file_path,
                hot_folder_id=config.id
            )
            
        except Exception as e:
            logger.error(
                "failed_to_delete_processed_file",
                error=str(e),
                file_path=file_path,
                hot_folder_id=config.id
            )
    
    def _update_processing_stats(self, processing_time: float, success: bool):
        """Update processing statistics"""
        if success:
            self._processing_stats["total_processed"] += 1
        else:
            self._processing_stats["total_failed"] += 1
        
        # Update average processing time
        total_jobs = self._processing_stats["total_processed"] + self._processing_stats["total_failed"]
        if total_jobs > 0:
            current_avg = self._processing_stats["average_processing_time"]
            self._processing_stats["average_processing_time"] = (
                (current_avg * (total_jobs - 1) + processing_time) / total_jobs
            )
    
    async def get_hot_folder_stats(self, folder_id: str) -> Dict[str, any]:
        """Get statistics for a hot folder"""
        if folder_id not in self.hot_folders:
            return {}
        
        config = self.hot_folders[folder_id]
        handler = self.handlers.get(folder_id)
        
        stats = {
            "is_monitoring": folder_id in self.observers,
            "currently_processing": len(handler.processing_files) if handler else 0,
            "active_locks": len(handler.file_locks) if handler else 0,
            "immediate_processing": config.immediate_processing,
            "configuration": {
                "path": config.path,
                "recursive": config.recursive,
                "immediate_processing_delay": config.immediate_processing_delay,
                "move_after_processing": config.move_after_processing,
                "delete_after_processing": config.delete_after_processing
            }
        }
        
        return stats
    
    async def get_service_stats(self) -> Dict[str, any]:
        """Get overall service statistics"""
        return {
            "total_hot_folders": len(self.hot_folders),
            "active_hot_folders": len([c for c in self.hot_folders.values() if c.enabled]),
            "monitoring_status": self._is_monitoring,
            "processing_stats": self._processing_stats.copy()
        }
    
    async def trigger_folder_scan(self, folder_id: str) -> List[str]:
        """Manually scan a hot folder for existing files and process them"""
        if folder_id not in self.hot_folders:
            raise HotFolderError(f"Hot folder {folder_id} not found")
        
        config = self.hot_folders[folder_id]
        found_files = []
        
        try:
            for root, _, files in os.walk(config.path):
                for file in files:
                    file_path = os.path.join(root, file)
                    
                    # Create temporary handler for filter checking
                    temp_handler = HotFolderHandler(config, self)
                    if temp_handler._matches_filters(file_path):
                        found_files.append(file_path)
                        # Process each file immediately
                        await self._create_immediate_ingest_job(file_path, config)
            
            logger.info(
                "hot_folder_manual_scan_completed",
                hot_folder_id=folder_id,
                files_processed=len(found_files)
            )
            
            return found_files
            
        except Exception as e:
            logger.error(
                "hot_folder_manual_scan_failed",
                error=str(e),
                folder_id=folder_id
            )
            raise HotFolderError(f"Failed to scan hot folder: {str(e)}")


# Dependency injection
_hot_folder_service: Optional[HotFolderService] = None


async def get_hot_folder_service() -> HotFolderService:
    """Get hot folder service instance"""
    global _hot_folder_service
    
    if _hot_folder_service is None:
        _hot_folder_service = HotFolderService()
        # Note: initialization with ingest_service happens in main.py
    
    return _hot_folder_service