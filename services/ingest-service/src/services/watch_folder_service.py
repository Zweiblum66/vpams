"""
Watch folder monitoring service for automatic file ingestion
"""

import asyncio
import os
import time
from typing import Dict, List, Optional, Set
from pathlib import Path
from datetime import datetime, timedelta
import structlog
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileMovedEvent

from ..models.schemas import (
    WatchFolderConfig, IngestJobCreate, IngestJob, IngestType,
    FileMetadata, ValidationRule
)
from ..core.config import settings
from ..core.exceptions import WatchFolderError, IngestServiceError
from ..core.logging import get_logger, log_ingest_event
from .ingest_service import IngestService

logger = get_logger(__name__)


class WatchFolderHandler(FileSystemEventHandler):
    """File system event handler for watch folders"""
    
    def __init__(self, config: WatchFolderConfig, watch_service: 'WatchFolderService'):
        self.config = config
        self.watch_service = watch_service
        self.processed_files: Set[str] = set()
        self.file_timestamps: Dict[str, float] = {}
        
    def on_created(self, event):
        """Handle file creation events"""
        if not event.is_directory:
            self._handle_file_event(event.src_path, "created")
    
    def on_moved(self, event):
        """Handle file move events"""
        if not event.is_directory:
            self._handle_file_event(event.dest_path, "moved")
    
    def _handle_file_event(self, file_path: str, event_type: str):
        """Handle file system events"""
        try:
            # Check if file matches filter patterns
            if not self._matches_filters(file_path):
                return
            
            # Avoid duplicate processing
            if file_path in self.processed_files:
                return
            
            # Store timestamp for stability check
            self.file_timestamps[file_path] = time.time()
            
            logger.info(
                "watch_folder_file_detected",
                file_path=file_path,
                event_type=event_type,
                watch_folder_id=self.config.id,
                watch_folder_path=self.config.path
            )
            
            # Schedule processing after stability delay
            asyncio.create_task(
                self._process_file_after_delay(file_path)
            )
            
        except Exception as e:
            logger.error(
                "watch_folder_event_handling_failed",
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
    
    async def _process_file_after_delay(self, file_path: str):
        """Process file after stability delay"""
        try:
            # Wait for file stability
            await asyncio.sleep(self.config.stability_delay)
            
            # Check if file still exists and hasn't been modified
            if not os.path.exists(file_path):
                logger.warning(
                    "watch_folder_file_disappeared",
                    file_path=file_path,
                    watch_folder_id=self.config.id
                )
                return
            
            # Check file stability (not modified recently)
            file_mtime = os.path.getmtime(file_path)
            if time.time() - file_mtime < self.config.stability_delay:
                logger.info(
                    "watch_folder_file_still_changing",
                    file_path=file_path,
                    watch_folder_id=self.config.id
                )
                # Reschedule
                await asyncio.sleep(self.config.stability_delay)
                await self._process_file_after_delay(file_path)
                return
            
            # Mark as processed to avoid duplicates
            self.processed_files.add(file_path)
            
            # Create ingest job
            await self.watch_service._create_ingest_job_for_file(file_path, self.config)
            
        except Exception as e:
            logger.error(
                "watch_folder_file_processing_failed",
                error=str(e),
                file_path=file_path,
                watch_folder_id=self.config.id
            )


class WatchFolderService:
    """Service for managing watch folder monitoring"""
    
    def __init__(self):
        self.ingest_service: Optional[IngestService] = None
        self.watch_folders: Dict[str, WatchFolderConfig] = {}
        self.observers: Dict[str, Observer] = {}
        self.handlers: Dict[str, WatchFolderHandler] = {}
        self._is_monitoring = False
    
    async def initialize(self, ingest_service: IngestService):
        """Initialize the watch folder service"""
        self.ingest_service = ingest_service
        
        # Load existing watch folder configurations
        await self._load_watch_folders()
        
        # Start monitoring for enabled watch folders
        await self.start_monitoring()
        
        logger.info(
            "watch_folder_service_initialized",
            watch_folder_count=len(self.watch_folders)
        )
    
    async def _load_watch_folders(self):
        """Load watch folder configurations from storage"""
        # In a real implementation, this would load from database
        # For now, we'll initialize with empty dict
        pass
    
    async def create_watch_folder(self, config: WatchFolderConfig) -> WatchFolderConfig:
        """Create a new watch folder configuration"""
        try:
            # Validate watch folder path
            if not os.path.exists(config.path):
                raise WatchFolderError(f"Watch folder path does not exist: {config.path}")
            
            if not os.path.isdir(config.path):
                raise WatchFolderError(f"Watch folder path is not a directory: {config.path}")
            
            # Store configuration
            self.watch_folders[config.id] = config
            
            # Start monitoring if enabled
            if config.enabled:
                await self._start_watching_folder(config)
            
            logger.info(
                "watch_folder_created",
                watch_folder_id=config.id,
                path=config.path,
                enabled=config.enabled
            )
            
            return config
            
        except Exception as e:
            logger.error(
                "failed_to_create_watch_folder",
                error=str(e),
                path=config.path
            )
            raise WatchFolderError(f"Failed to create watch folder: {str(e)}")
    
    async def list_watch_folders(self) -> List[WatchFolderConfig]:
        """List all watch folder configurations"""
        return list(self.watch_folders.values())
    
    async def get_watch_folder(self, folder_id: str) -> Optional[WatchFolderConfig]:
        """Get a specific watch folder configuration"""
        return self.watch_folders.get(folder_id)
    
    async def update_watch_folder(
        self,
        folder_id: str,
        config: WatchFolderConfig
    ) -> Optional[WatchFolderConfig]:
        """Update a watch folder configuration"""
        if folder_id not in self.watch_folders:
            return None
        
        old_config = self.watch_folders[folder_id]
        
        try:
            # Stop monitoring old configuration
            if old_config.enabled:
                await self._stop_watching_folder(folder_id)
            
            # Update configuration
            config.id = folder_id  # Ensure ID consistency
            self.watch_folders[folder_id] = config
            
            # Start monitoring new configuration if enabled
            if config.enabled:
                await self._start_watching_folder(config)
            
            logger.info(
                "watch_folder_updated",
                watch_folder_id=folder_id,
                path=config.path,
                enabled=config.enabled
            )
            
            return config
            
        except Exception as e:
            # Restore old configuration on error
            self.watch_folders[folder_id] = old_config
            if old_config.enabled:
                await self._start_watching_folder(old_config)
            
            logger.error(
                "failed_to_update_watch_folder",
                error=str(e),
                folder_id=folder_id
            )
            raise WatchFolderError(f"Failed to update watch folder: {str(e)}")
    
    async def delete_watch_folder(self, folder_id: str) -> bool:
        """Delete a watch folder configuration"""
        if folder_id not in self.watch_folders:
            return False
        
        try:
            # Stop monitoring
            await self._stop_watching_folder(folder_id)
            
            # Remove configuration
            del self.watch_folders[folder_id]
            
            logger.info("watch_folder_deleted", watch_folder_id=folder_id)
            
            return True
            
        except Exception as e:
            logger.error(
                "failed_to_delete_watch_folder",
                error=str(e),
                folder_id=folder_id
            )
            raise WatchFolderError(f"Failed to delete watch folder: {str(e)}")
    
    async def start_monitoring(self):
        """Start monitoring all enabled watch folders"""
        if self._is_monitoring:
            return
        
        try:
            for config in self.watch_folders.values():
                if config.enabled:
                    await self._start_watching_folder(config)
            
            self._is_monitoring = True
            
            logger.info(
                "watch_folder_monitoring_started",
                active_folders=len([c for c in self.watch_folders.values() if c.enabled])
            )
            
        except Exception as e:
            logger.error("failed_to_start_watch_folder_monitoring", error=str(e))
            raise WatchFolderError(f"Failed to start monitoring: {str(e)}")
    
    async def stop_monitoring(self):
        """Stop monitoring all watch folders"""
        if not self._is_monitoring:
            return
        
        try:
            for folder_id in list(self.observers.keys()):
                await self._stop_watching_folder(folder_id)
            
            self._is_monitoring = False
            
            logger.info("watch_folder_monitoring_stopped")
            
        except Exception as e:
            logger.error("failed_to_stop_watch_folder_monitoring", error=str(e))
            raise WatchFolderError(f"Failed to stop monitoring: {str(e)}")
    
    async def _start_watching_folder(self, config: WatchFolderConfig):
        """Start watching a specific folder"""
        try:
            if config.id in self.observers:
                # Already watching
                return
            
            # Create event handler
            handler = WatchFolderHandler(config, self)
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
                "watch_folder_monitoring_started",
                watch_folder_id=config.id,
                path=config.path,
                recursive=config.recursive
            )
            
        except Exception as e:
            logger.error(
                "failed_to_start_watching_folder",
                error=str(e),
                watch_folder_id=config.id,
                path=config.path
            )
            raise WatchFolderError(f"Failed to start watching folder: {str(e)}")
    
    async def _stop_watching_folder(self, folder_id: str):
        """Stop watching a specific folder"""
        try:
            if folder_id in self.observers:
                observer = self.observers[folder_id]
                observer.stop()
                observer.join(timeout=5)  # Wait up to 5 seconds
                del self.observers[folder_id]
            
            if folder_id in self.handlers:
                del self.handlers[folder_id]
            
            logger.info(
                "watch_folder_monitoring_stopped",
                watch_folder_id=folder_id
            )
            
        except Exception as e:
            logger.error(
                "failed_to_stop_watching_folder",
                error=str(e),
                folder_id=folder_id
            )
    
    async def _create_ingest_job_for_file(self, file_path: str, config: WatchFolderConfig):
        """Create an ingest job for a detected file"""
        try:
            if not self.ingest_service:
                raise IngestServiceError("Ingest service not initialized")
            
            # Create ingest job request
            job_request = IngestJobCreate(
                source_path=file_path,
                destination_project_id=config.destination_project_id,
                ingest_type=IngestType.WATCH_FOLDER,
                validation_rules=config.validation_rules,
                metadata_override=config.metadata_template or {},
                tags=config.tags or [],
                priority=config.priority,
                auto_generate_proxies=config.auto_generate_proxies,
                preserve_folder_structure=config.preserve_folder_structure
            )
            
            # Create and start processing job
            job = await self.ingest_service.create_job(job_request)
            
            # Process job immediately (in background)
            asyncio.create_task(
                self.ingest_service.process_job(job.id)
            )
            
            log_ingest_event(
                logger,
                "watch_folder_ingest_triggered",
                file_path,
                job_id=job.id,
                watch_folder_id=config.id,
                watch_folder_path=config.path
            )
            
        except Exception as e:
            logger.error(
                "failed_to_create_ingest_job_for_watch_folder",
                error=str(e),
                file_path=file_path,
                watch_folder_id=config.id
            )
    
    async def get_watch_folder_stats(self, folder_id: str) -> Dict[str, int]:
        """Get statistics for a watch folder"""
        if folder_id not in self.watch_folders:
            return {}
        
        config = self.watch_folders[folder_id]
        handler = self.handlers.get(folder_id)
        
        stats = {
            "is_monitoring": folder_id in self.observers,
            "processed_files": len(handler.processed_files) if handler else 0,
            "pending_files": len(handler.file_timestamps) if handler else 0
        }
        
        return stats
    
    async def scan_watch_folder(self, folder_id: str) -> List[str]:
        """Manually scan a watch folder for existing files"""
        if folder_id not in self.watch_folders:
            raise WatchFolderError(f"Watch folder {folder_id} not found")
        
        config = self.watch_folders[folder_id]
        found_files = []
        
        try:
            for root, _, files in os.walk(config.path):
                for file in files:
                    file_path = os.path.join(root, file)
                    
                    # Create temporary handler for filter checking
                    temp_handler = WatchFolderHandler(config, self)
                    if temp_handler._matches_filters(file_path):
                        found_files.append(file_path)
            
            logger.info(
                "watch_folder_scan_completed",
                watch_folder_id=folder_id,
                files_found=len(found_files)
            )
            
            return found_files
            
        except Exception as e:
            logger.error(
                "watch_folder_scan_failed",
                error=str(e),
                folder_id=folder_id
            )
            raise WatchFolderError(f"Failed to scan watch folder: {str(e)}")
    
    async def process_existing_files(self, folder_id: str) -> List[IngestJob]:
        """Process all existing files in a watch folder"""
        found_files = await self.scan_watch_folder(folder_id)
        config = self.watch_folders[folder_id]
        created_jobs = []
        
        for file_path in found_files:
            try:
                await self._create_ingest_job_for_file(file_path, config)
            except Exception as e:
                logger.error(
                    "failed_to_process_existing_file",
                    error=str(e),
                    file_path=file_path,
                    folder_id=folder_id
                )
        
        return created_jobs


# Dependency injection
_watch_folder_service: Optional[WatchFolderService] = None


async def get_watch_folder_service() -> WatchFolderService:
    """Get watch folder service instance"""
    global _watch_folder_service
    
    if _watch_folder_service is None:
        _watch_folder_service = WatchFolderService()
        # Note: initialization with ingest_service happens in main.py
    
    return _watch_folder_service